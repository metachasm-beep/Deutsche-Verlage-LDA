import argparse
import os
import re
import sys
import time
import urllib3
import requests
import xml.etree.ElementTree as ET
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.gbv_harvester import (
    NS,
    normalize_german_text,
    fetch_url_with_ssl_fallback,
    fetch_blurb_text,
    fetch_pdf_text_from_url
)
from scripts.fulltext_ingester import _reconstruct_openalex_abstract

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {"User-Agent": "DeutscheVerlageLDA-PhDResearch/1.0 (JNU Centre for German Studies)"}


def fetch_gbv_ppn_deep_paratexts(ppn: str) -> dict:
    """
    Given a GBV PPN, fetches its MARC21-XML record and streams any embedded:
    - MARC 520 ($a): Abstract / summary note
    - MARC 856 ($3='Inhaltstext'): Full publisher jacket blurb HTML
    - MARC 856 ($3='Inhaltsverzeichnis'): Digitized Table of Contents PDF (via PyMuPDF in RAM)
    - MARC 856 ($z='kostenfrei'): Open-Access full-text PDF (first 15 pages via PyMuPDF in RAM)
    """
    result = {"abstract_520": "", "blurb_text": "", "toc_text": "", "oa_text": ""}
    if not ppn:
        return result

    try:
        resp = fetch_url_with_ssl_fallback(
            "https://sru.k10plus.de/gvk",
            params={
                "version": "1.1",
                "operation": "searchRetrieve",
                "query": f"pica.ppn={ppn}",
                "maximumRecords": "1",
                "recordSchema": "marcxml"
            },
            timeout=12
        )
        if resp.status_code != 200:
            return result

        root = ET.fromstring(resp.content)
        rec = root.find(".//marc:record", NS)
        if rec is None:
            return result

        abs_list = []
        blurb_url = ""
        toc_url = ""
        oa_url = ""

        for field in rec.findall("marc:datafield", NS):
            tag = field.get("tag")
            if tag == "520":
                sub_a = field.find("marc:subfield[@code='a']", NS)
                if sub_a is not None and sub_a.text:
                    abs_list.append(normalize_german_text(sub_a.text))
            elif tag == "856":
                sub_3 = field.find("marc:subfield[@code='3']", NS)
                sub_u = field.find("marc:subfield[@code='u']", NS)
                sub_z = field.find("marc:subfield[@code='z']", NS)
                if sub_u is not None and sub_u.text:
                    u_val = sub_u.text.strip()
                    l3 = sub_3.text.lower() if (sub_3 is not None and sub_3.text) else ""
                    lz = sub_z.text.lower() if (sub_z is not None and sub_z.text) else ""
                    if "inhaltstext" in l3 and not blurb_url:
                        blurb_url = u_val
                    elif "inhaltsverzeichnis" in l3 and not toc_url:
                        toc_url = u_val
                    elif ("kostenfrei" in lz or "open access" in lz) and not oa_url:
                        oa_url = u_val

        result["abstract_520"] = " ".join(abs_list)
        if blurb_url:
            result["blurb_text"] = fetch_blurb_text(blurb_url)
        if toc_url:
            result["toc_text"] = fetch_pdf_text_from_url(toc_url, max_pages=8)
        if oa_url:
            result["oa_text"] = fetch_pdf_text_from_url(oa_url, max_pages=15)
    except Exception:
        pass

    return result


def fetch_wikipedia_de_work_summary(title: str, author: str) -> str:
    """
    Queries the German Wikipedia API (de.wikipedia.org) for an encyclopedic article
    matching the book title (or author + work section), returning detailed German
    summaries of the book's thesis, chapters (Inhalt), and reception (Rezeption).
    """
    if not title:
        return ""
    main_title = title.split(":")[0].strip()
    if len(main_title) < 4:
        return ""

    author_last = (author or "").split(",")[0].strip()
    search_query = f'"{main_title}" {author_last}'.strip()

    try:
        r = requests.get(
            "https://de.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": search_query,
                "srlimit": 2,
                "format": "json"
            },
            headers=HEADERS,
            verify=False,
            timeout=8
        )
        if r.status_code != 200:
            return ""
        hits = r.json().get("query", {}).get("search", [])
        if not hits:
            return ""

        page_title = hits[0]["title"]
        # Ensure the matched page is relevant to the book title or author
        if (
            main_title.lower() not in page_title.lower()
            and (not author_last or author_last.lower() not in page_title.lower())
        ):
            return ""

        r2 = requests.get(
            "https://de.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "prop": "extracts",
                "explaintext": True,
                "titles": page_title,
                "format": "json"
            },
            headers=HEADERS,
            verify=False,
            timeout=8
        )
        pages = r2.json().get("query", {}).get("pages", {})
        if not pages:
            return ""
        extract = list(pages.values())[0].get("extract", "")
        cleaned = normalize_german_text(extract)
        # Cap at ~3,500 chars (~500 dense words) so a single Wikipedia article doesn't skew LDA
        return cleaned[:3500]
    except Exception:
        return ""


def fetch_openalex_book_reviews_and_abstracts(title: str, author: str) -> str:
    """
    Queries OpenAlex for scholarly abstracts, book reviews (Rezensionen), and
    academic discussions matching the book's title and author.
    """
    if not title:
        return ""
    main_title = title.split(":")[0].strip()
    author_last = (author or "").split(",")[0].strip()
    q = f'"{main_title}" {author_last}'.strip()

    try:
        r = requests.get(
            "https://api.openalex.org/works",
            params={
                "search": q,
                "per-page": 3
            },
            verify=False,
            timeout=8
        )
        if r.status_code != 200:
            return ""
        results = r.json().get("results", [])
        snippets = []
        for w in results:
            inv = w.get("abstract_inverted_index")
            if inv:
                abs_str = _reconstruct_openalex_abstract(inv)
                if len(abs_str.split()) >= 15:
                    snippets.append(abs_str)
        return " ".join(snippets)[:3000]
    except Exception:
        return ""


def auto_enrich_catalog_without_ebooks(
    catalog_csv: str = "data/primary_texts/COMPREHENSIVE_BOOK_CATALOG.csv",
    max_books: int = 80,
    output_csv: str = "data/enriched_no_ebook_corpus.csv",
    merge_dnb: bool = True
) -> pd.DataFrame:
    """
    Automates multi-source full-text & deep-paratext enrichment for the books in
    COMPREHENSIVE_BOOK_CATALOG.csv WITHOUT downloading copyrighted e-books:
    1. GBV MARC 520 Abstract + MARC 856 Inhaltstext Blurb + MARC 856 Inhaltsverzeichnis PDF (via PyMuPDF)
    2. OpenAlex Scholarly Abstracts & Book Reviews (Rezensionen)
    3. German Wikipedia Work-Level Content & Reception Summaries
    4. Controlled GND Schlagwörter & BKL 11.* Semantic Classifications
    """
    if not os.path.exists(catalog_csv):
        print(f"Catalog {catalog_csv} not found. Run scripts/generate_acquisition_catalog.py first.")
        return pd.DataFrame()

    df_cat = pd.read_csv(catalog_csv, encoding="utf-8")
    # Load existing GBV metadata to preserve existing keywords/abstracts
    gbv_lookup = {}
    if os.path.exists("data/gbv_metadata.csv"):
        df_gbv = pd.read_csv("data/gbv_metadata.csv", encoding="utf-8")
        for _, r in df_gbv.iterrows():
            gbv_lookup[str(r.get("ppn") or "")] = r.to_dict()

    subset = df_cat.head(max_books).copy()
    enriched_rows = []

    print(
        f"Auto-enriching top {len(subset)} books from {catalog_csv} via Cloud APIs "
        f"(GBV ToC PDFs + Blurbs + OpenAlex Reviews + Wikipedia DE Work Summaries)..."
    )

    for idx, row in subset.iterrows():
        ppn = str(row.get("ppn") or "").strip()
        title = str(row.get("title") or "").strip()
        author = str(row.get("author") or "o. V.").strip()
        date = str(row.get("date") or "2000").strip()
        decade = str(row.get("decade") or "").strip()
        publisher = str(row.get("publisher") or "Unknown").strip()
        series = str(row.get("series") or "") if pd.notna(row.get("series")) else ""
        bkl = str(row.get("bkl_codes") or "") if pd.notna(row.get("bkl_codes")) else ""
        holdings = int(row.get("gbv_holdings_count") or 0)

        base_gbv = gbv_lookup.get(ppn, {})
        keywords = str(base_gbv.get("keywords") or "") if pd.notna(base_gbv.get("keywords")) else ""

        # 1. Deep GBV Paratexts & Digitized Table of Contents PDF
        gbv_deep = fetch_gbv_ppn_deep_paratexts(ppn)
        # 2. OpenAlex Scholarly Reviews & Abstracts
        oa_reviews = fetch_openalex_book_reviews_and_abstracts(title, author)
        # 3. German Wikipedia Work/Author Discourse Summary
        wiki_summary = fetch_wikipedia_de_work_summary(title, author)

        segments = [
            s for s in [
                title,
                series,
                gbv_deep["abstract_520"],
                gbv_deep["blurb_text"],
                gbv_deep["toc_text"],
                gbv_deep["oa_text"],
                oa_reviews,
                wiki_summary,
                keywords
            ]
            if s and str(s).strip()
        ]
        composite_text = ". ".join(segments)
        word_cnt = len(composite_text.split())

        best_abstract = (
            gbv_deep["blurb_text"]
            or gbv_deep["abstract_520"]
            or oa_reviews
            or wiki_summary
            or gbv_deep["toc_text"]
            or composite_text
        )[:450]

        enriched_rows.append({
            "ppn": ppn,
            "title": title,
            "author": author,
            "date": date,
            "decade": decade,
            "publisher": publisher,
            "series": series,
            "bkl_codes": bkl,
            "gbv_holdings_count": holdings,
            "corpus_layer": "composite_no_ebook_enriched",
            "word_count": word_cnt,
            "keywords": keywords,
            "abstract": best_abstract,
            "text": composite_text
        })

        if (idx + 1) % 10 == 0 or (idx + 1) == len(subset):
            print(f"  - Enriched {idx + 1}/{len(subset)} books (Latest: [{publisher} {date}] {title[:45]}... -> {word_cnt} words)")
        time.sleep(0.15)

    df_out = pd.DataFrame(enriched_rows)
    os.makedirs(os.path.dirname(output_csv) or "data", exist_ok=True)
    df_out.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"Saved {len(df_out)} multi-API enriched book records to {output_csv}")

    if merge_dnb and not df_out.empty:
        dnb_path = "data/dnb_metadata.csv"
        if os.path.exists(dnb_path):
            dnb_df = pd.read_csv(dnb_path, encoding="utf-8")
            # Replace or append enriched records by normalized title
            dnb_df["_norm"] = dnb_df["title"].fillna("").str.lower().str.strip()
            df_out["_norm"] = df_out["title"].fillna("").str.lower().str.strip()
            dnb_filtered = dnb_df[~dnb_df["_norm"].isin(set(df_out["_norm"]))].drop(columns=["_norm"])
            df_out_clean = df_out.drop(columns=["_norm"])
            combined = pd.concat([dnb_filtered, df_out_clean], ignore_index=True)
            combined.to_csv(dnb_path, index=False, encoding="utf-8")
            print(f"Updated master corpus {dnb_path} with enriched records (Total rows: {len(combined)})")

    return df_out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automate rich text enrichment for the 731-book catalog without downloading e-books"
    )
    parser.add_argument("--max-books", type=int, default=40, help="Number of catalog books to deep-enrich per run (use 731 for all)")
    parser.add_argument("--output", default="data/enriched_no_ebook_corpus.csv", help="Output CSV path")
    parser.add_argument("--no-merge", action="store_true", help="Do not merge into data/dnb_metadata.csv")
    args = parser.parse_args()

    auto_enrich_catalog_without_ebooks(
        max_books=args.max_books,
        output_csv=args.output,
        merge_dnb=not args.no_merge
    )
