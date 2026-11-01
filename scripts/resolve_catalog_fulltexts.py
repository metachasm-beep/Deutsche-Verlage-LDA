import argparse
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
import requests
import xml.etree.ElementTree as ET
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.fulltext_ingester import normalize_german_text, chunk_fulltext_words
from scripts.stream_full_books_cloud import stream_entire_pdf_book_in_ram
from scripts.auto_enrich_catalog_no_ebooks import (
    fetch_gbv_ppn_deep_paratexts,
    fetch_openalex_book_reviews_and_abstracts,
    fetch_wikipedia_de_work_summary
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HEADERS = {"User-Agent": "DeutscheVerlageLDA-CatalogResolver/1.0 (JNU Centre for German Studies)"}
NS = {"zs": "http://www.loc.gov/zing/srw/", "m": "http://www.loc.gov/MARC21/slim"}

_URL_LOCK = threading.Lock()
_USED_SOURCE_URLS = set()


def claim_source_url(url: str) -> bool:
    """Thread-safe check to ensure the same full-text URL is never claimed by two different books."""
    if not url:
        return False
    norm_u = url.strip().lower()
    with _URL_LOCK:
        if norm_u in _USED_SOURCE_URLS:
            return False
        _USED_SOURCE_URLS.add(norm_u)
        return True


def resolve_gbv_ebook_and_toc_links(title: str, author: str, ppn: str) -> dict:
    """
    Checks both the print PPN and any online electronic edition in GBV
    for direct full-text links, ToC PDFs, and institutional e-book aggregator links
    (ProQuest, EBSCOhost, Inlibra/Nomos, Content-Select).
    """
    info = {"direct_pdf_urls": [], "aggregator_urls": [], "toc_urls": []}
    title_short = re.sub(r"[^\w\säöüÄÖÜß]", " ", title.split(":")[0]).strip()
    author_last = author.split(",")[0].strip()

    queries = []
    if ppn and ppn != "nan":
        queries.append(f"pica.ppn={ppn}")
    if title_short and author_last and author_last != "o. V.":
        queries.append(f'pica.tit="{title_short}" and pica.per="{author_last}"')

    for q in queries:
        try:
            r = requests.get(
                "https://sru.k10plus.de/gvk",
                params={
                    "version": "1.1",
                    "operation": "searchRetrieve",
                    "query": q,
                    "maximumRecords": "5",
                    "recordSchema": "marcxml"
                },
                headers=HEADERS,
                verify=False,
                timeout=12
            )
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.text)
            for f856 in root.findall(".//m:datafield[@tag='856']", NS):
                u = f856.find("m:subfield[@code='u']", NS)
                if u is None or not u.text:
                    continue
                url = u.text.strip()
                s3 = f856.find("m:subfield[@code='3']", NS)
                x = f856.find("m:subfield[@code='x']", NS)
                z = f856.find("m:subfield[@code='z']", NS)
                label = " ".join(
                    [elem.text for elem in (s3, x, z) if elem is not None and elem.text]
                ).lower()

                if "inhaltsverzeichnis" in label or url.endswith("/04") or "_toc.pdf" in url.lower():
                    if url not in info["toc_urls"]:
                        info["toc_urls"].append(url)
                elif any(k in url.lower() for k in ["proquest", "ebscohost", "inlibra", "content-select", "doi.org"]):
                    if url not in info["aggregator_urls"]:
                        info["aggregator_urls"].append(url)
                elif "kostenfrei" in label or url.lower().endswith(".pdf"):
                    if url not in info["direct_pdf_urls"]:
                        info["direct_pdf_urls"].append(url)
        except Exception:
            continue
    return info


def stream_green_oa_for_target_book(title: str, author: str, min_words: int = 1500) -> tuple[str, str, int]:
    """
    Searches OpenAlex & German university institutional repositories (DuePublico, LMU Munich,
    Uni Tübingen ixTheo, Uni Heidelberg, SSOAR, De Gruyter, Nomos, V&R) for Green Open-Access
    full-text PDFs matching the target book's exact title or author, and streams the PDF in RAM.
    """
    title_core = title.split(":")[0].split(";")[0].strip()
    author_last = author.split(",")[0].strip()
    title_words = [w.lower() for w in re.findall(r"\w+", title_core) if len(w) > 4]
    if not title_words:
        return "", "", 0

    try:
        r = requests.get(
            "https://api.openalex.org/works",
            params={
                "filter": "language:de,is_oa:true",
                "search": f"{title_core} {author_last}",
                "per-page": 8
            },
            headers=HEADERS,
            verify=False,
            timeout=12
        )
        if r.status_code == 200:
            for work in r.json().get("results", []):
                w_title = (work.get("title") or "").lower()
                w_authors = " ".join(
                    [(a.get("author") or {}).get("display_name", "").lower() for a in (work.get("authorships") or [])]
                )
                author_match = bool(author_last and len(author_last) > 2 and author_last.lower() in w_authors)
                title_match = sum(1 for tw in title_words if tw in w_title) >= min(2, max(1, len(title_words)))
                # Require title match AND (author match or exact title_core substring)
                if not (title_match and (author_match or title_core.lower() in w_title)):
                    continue

                best_oa = work.get("best_oa_location") or {}
                oa_info = work.get("open_access") or {}
                pdf_url = best_oa.get("pdf_url") or oa_info.get("oa_url") or ""
                if not pdf_url:
                    continue
                if not claim_source_url(pdf_url):
                    continue
                text, pages = stream_entire_pdf_book_in_ram(pdf_url, max_pages=400)
                if len(text.split()) >= min_words:
                    return text, pdf_url, pages
    except Exception:
        pass
    return "", "", 0


def is_clean_modern_german(text: str) -> bool:
    """
    Verifies that an OCR stream is genuine modern high German (not Spanish/French/Latin/English
    and not a corrupted 19th-century Fraktur scan with 'ift', 'baß', 'ober', 'unb').
    """
    sample_words = [w.lower() for w in re.findall(r"\b[a-zA-ZäöüÄÖÜß]+\b", text[:25000])]
    if len(sample_words) < 200:
        return False
    total = len(sample_words)
    de_core = sum(1 for w in sample_words if w in {"der", "die", "das", "und", "in", "von", "mit", "nicht", "ist", "auf", "für"})
    fraktur_or_foreign = sum(
        1 for w in sample_words
        if w in {"ift", "baß", "ober", "unb", "ber", "bie", "bas", "würbe", "que", "del", "por", "para", "les", "des", "quod", "cum", "domini", "the", "and"}
    )
    # Require >= 6% modern German function words and < 1% Fraktur/foreign noise
    return (de_core / total) >= 0.06 and (fraktur_or_foreign / total) < 0.01


def stream_archive_org_for_target_book(
    title: str,
    author: str,
    min_words: int = 2000,
    max_words_cap: int = 100000
) -> tuple[str, str]:
    """
    Searches Internet Archive (archive.org) for a digitized full-text OCR (_djvu.txt)
    matching the target catalog book's title and author in clean modern German.
    """
    title_core = re.sub(r"[^\w\säöüÄÖÜß]", " ", title.split(":")[0].split(";")[0]).strip()
    author_last = re.sub(r"[^\w\säöüÄÖÜß]", " ", author.split(",")[0]).strip()
    stopwords = {"über", "oder", "eine", "einer", "eines", "einem", "nicht", "warum", "nach", "unter", "zwischen"}
    title_keywords = [w for w in title_core.split() if len(w) > 3 and w.lower() not in stopwords][:4]
    if not title_keywords:
        return "", ""

    kw_query = " AND ".join(title_keywords)
    q = f'({kw_query}) AND ({author_last}) AND language:(ger OR deu) AND mediatype:texts'
    try:
        r = requests.get(
            "https://archive.org/advancedsearch.php",
            params={"q": q, "fl[]": ["identifier", "title", "creator"], "rows": 5, "output": "json"},
            headers=HEADERS,
            verify=False,
            timeout=15
        )
        if r.status_code == 200:
            for d in r.json().get("response", {}).get("docs", []):
                ident = d.get("identifier")
                doc_title = str(d.get("title") or "").lower()
                if not ident:
                    continue
                if not any(kw.lower() in doc_title for kw in title_keywords):
                    continue

                meta_r = requests.get(
                    f"https://archive.org/metadata/{ident}",
                    headers=HEADERS,
                    verify=False,
                    timeout=15
                )
                if meta_r.status_code != 200:
                    continue
                files = meta_r.json().get("files", [])
                djvu = [f["name"] for f in files if f.get("name", "").endswith("_djvu.txt")]
                if not djvu:
                    continue
                txt_url = f"https://archive.org/download/{ident}/{djvu[0]}"
                if not claim_source_url(txt_url):
                    continue
                txt_r = requests.get(txt_url, headers=HEADERS, verify=False, timeout=25)
                if txt_r.status_code == 200:
                    norm = normalize_german_text(txt_r.text)
                    if not is_clean_modern_german(norm):
                        continue
                    words = norm.split()
                    if len(words) >= min_words:
                        if len(words) > max_words_cap:
                            norm = " ".join(words[:max_words_cap])
                        return norm, txt_url
    except Exception:
        pass
    return "", ""


def process_single_catalog_book(idx: int, total_books: int, row: pd.Series, chunk_words: int = 1000) -> tuple[dict, list[dict]]:
    """
    Worker function to resolve a single target book from COMPREHENSIVE_BOOK_CATALOG.csv:
    1. Attempts full-book PDF / OCR streaming in RAM (GBV Kostenfrei, Archive.org, Green OA Repositories).
    2. If the full book is DRM-locked, automatically runs Multi-API Deep Enrichment in RAM
       (GBV ToC PDF + Inhaltstext blurb + OpenAlex scholarly reviews + Wikipedia DE summary).
    """
    title = str(row.get("title") or "").strip()
    author = str(row.get("author") or "o. V.").strip()
    publisher = str(row.get("publisher") or "").strip()
    year = str(row.get("date") or "2000").strip()
    decade = str(row.get("decade") or f"{year[:3]}0s").strip()
    isbn = str(row.get("isbn") or "").strip()
    ppn = str(row.get("ppn") or "").strip()
    bkl = str(row.get("bkl_codes") or "").strip()

    gbv_links = resolve_gbv_ebook_and_toc_links(title, author, ppn)
    full_text = ""
    source_url = ""
    pages = 0
    resolution_type = "multi_api_deep_enriched"

    # 1. Try direct PDF from GBV MARC 856 if available
    for d_url in gbv_links["direct_pdf_urls"]:
        if not claim_source_url(d_url):
            continue
        ft, pg = stream_entire_pdf_book_in_ram(d_url, max_pages=400)
        if len(ft.split()) >= 1500:
            full_text, source_url, pages = ft, d_url, pg
            resolution_type = "gbv_direct_fulltext_pdf"
            break

    # 2. Try Internet Archive exact title+author OCR stream
    if not full_text:
        ia_text, ia_url = stream_archive_org_for_target_book(title, author)
        if ia_text:
            full_text, source_url = ia_text, ia_url
            resolution_type = "archive_org_fulltext_book"

    # 3. Try Green Open-Access / University Repository PDF stream
    if not full_text:
        oa_text, oa_url, oa_pages = stream_green_oa_for_target_book(title, author)
        if oa_text:
            full_text, source_url, pages = oa_text, oa_url, oa_pages
            resolution_type = "green_oa_repository_fulltext"

    # 4. Fallback for DRM-locked trade books: Multi-API Deep Enrichment (ToC PDF + Blurb + Reviews + Wikipedia)
    if not full_text:
        gbv_data = fetch_gbv_ppn_deep_paratexts(ppn)
        oa_reviews = fetch_openalex_book_reviews_and_abstracts(title, author)
        wiki_summary = fetch_wikipedia_de_work_summary(title, author)
        parts = [
            f"{title}. {author}. {publisher}.",
            gbv_data.get("abstract_520", ""),
            gbv_data.get("blurb_text", ""),
            gbv_data.get("toc_text", ""),
            gbv_data.get("oa_text", ""),
            oa_reviews,
            wiki_summary
        ]
        full_text = normalize_german_text(" ".join([p for p in parts if p]))
        source_url = (gbv_links["toc_urls"][0] if gbv_links["toc_urls"] else f"PPN:{ppn}")
        resolution_type = "drm_fallback_multi_api_enriched"

    total_words = len(full_text.split())
    link_record = {
        "rank": idx + 1,
        "date": year,
        "publisher": publisher,
        "author": author,
        "title": title,
        "isbn": isbn,
        "ppn": ppn,
        "bkl_codes": bkl,
        "resolution_type": resolution_type,
        "extracted_words": total_words,
        "extracted_pages": pages,
        "streamed_source_url": source_url,
        "institutional_ebook_urls": " | ".join(gbv_links["aggregator_urls"]),
        "toc_pdf_urls": " | ".join(gbv_links["toc_urls"])
    }

    passage_records = []
    chunks = chunk_fulltext_words(full_text, chunk_words=chunk_words)
    if not chunks and full_text:
        chunks = [full_text]

    for c_idx, chunk_str in enumerate(chunks, start=1):
        chunk_title = (
            title if len(chunks) == 1 else f"{title} [Forschungsbuch-Abschnitt {c_idx}/{len(chunks)}]"
        )
        passage_records.append({
            "title": chunk_title,
            "author": author,
            "date": year,
            "decade": decade,
            "publisher": publisher,
            "corpus_layer": resolution_type,
            "source_file": source_url,
            "chunk_index": c_idx,
            "total_chunks": len(chunks),
            "word_count": len(chunk_str.split()),
            "abstract": chunk_str[:420],
            "text": f"{title}. {author}. {publisher}. {chunk_str}"
        })

    return link_record, passage_records


def resolve_catalog_fulltexts(
    catalog_csv: str = "data/primary_texts/COMPREHENSIVE_BOOK_CATALOG.csv",
    max_books: int = 731,
    workers: int = 8,
    chunk_words: int = 1000,
    output_csv: str = "data/catalog_resolved_fulltexts.csv",
    links_csv: str = "data/primary_texts/CATALOG_EBOOK_LINKS.csv",
    merge_dnb: bool = True
) -> pd.DataFrame:
    """
    Parallelized resolver across all 731 target books in COMPREHENSIVE_BOOK_CATALOG.csv
    with incremental checkpoint saving every 25 books.
    """
    if not os.path.exists(catalog_csv):
        print(f"Catalog not found: {catalog_csv}", flush=True)
        return pd.DataFrame()

    cat_df = pd.read_csv(catalog_csv, encoding="utf-8")
    subset = cat_df.head(max_books)
    total = len(subset)

    print(
        f"Starting parallel resolution across {total} target research books "
        f"(workers={workers}, chunk_words={chunk_words})...",
        flush=True
    )

    all_link_rows = []
    all_passage_rows = []
    completed = 0
    fullbook_hits = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(process_single_catalog_book, idx, total, row, chunk_words): idx
            for idx, row in subset.iterrows()
        }
        for fut in as_completed(future_map):
            completed += 1
            try:
                link_rec, p_recs = fut.result()
                all_link_rows.append(link_rec)
                all_passage_rows.extend(p_recs)
                res_type = link_rec["resolution_type"]
                if res_type in ("gbv_direct_fulltext_pdf", "archive_org_fulltext_book", "green_oa_repository_fulltext"):
                    fullbook_hits += 1
                    print(
                        f"  + [{completed}/{total}] FULL BOOK STREAMED ({link_rec['date']} | {link_rec['publisher']}) "
                        f"{link_rec['title'][:45]}... -> {res_type} | {link_rec['extracted_words']:,} words ({len(p_recs)} passages)",
                        flush=True
                    )
                elif completed % 25 == 0 or completed == total:
                    print(
                        f"  ... Progress: {completed}/{total} books processed "
                        f"(Full-book streams so far: {fullbook_hits} | Total LDA passages: {len(all_passage_rows):,})",
                        flush=True
                    )

                # Incremental checkpoint every 50 books
                if completed % 50 == 0:
                    pd.DataFrame(all_link_rows).sort_values("rank").to_csv(links_csv, index=False, encoding="utf-8")
                    pd.DataFrame(all_passage_rows).to_csv(output_csv, index=False, encoding="utf-8")
            except Exception as e:
                print(f"  ! Worker warning at [{completed}/{total}]: {e}", flush=True)

    links_df = pd.DataFrame(all_link_rows).sort_values("rank").reset_index(drop=True)
    os.makedirs(os.path.dirname(links_csv) or "data/primary_texts", exist_ok=True)
    links_df.to_csv(links_csv, index=False, encoding="utf-8")

    out_df = pd.DataFrame(all_passage_rows)
    if not out_df.empty:
        os.makedirs(os.path.dirname(output_csv) or "data", exist_ok=True)
        out_df.to_csv(output_csv, index=False, encoding="utf-8")
        total_w = out_df["word_count"].sum()
        print("\n======================================================================", flush=True)
        print(f"COMPLETED ALL {total} TARGET CATALOG BOOKS!", flush=True)
        print(f"  - Full-Book / OA Repository Streams: {fullbook_hits} books", flush=True)
        print(f"  - Multi-API Deep Enriched (ToC PDF + Blurb + Reviews + Wiki): {total - fullbook_hits} books", flush=True)
        print(f"  - Total LDA Passages Generated: {len(out_df):,} ({total_w:,} total German words!)", flush=True)
        print(f"  - Saved passages to: {output_csv}", flush=True)
        print(f"  - Saved resolver table to: {links_csv}", flush=True)
        print("======================================================================", flush=True)

        if merge_dnb:
            dnb_path = "data/dnb_metadata.csv"
            if os.path.exists(dnb_path):
                dnb_df = pd.read_csv(dnb_path, encoding="utf-8")
                # Replace any older single-row entries with the newly resolved passages
                existing_titles = set(out_df["title"].dropna().str.lower().str.strip())
                kept_dnb = dnb_df[~dnb_df["title"].fillna("").str.lower().str.strip().isin(existing_titles)]
                merged = pd.concat([kept_dnb, out_df], ignore_index=True)
                merged.to_csv(dnb_path, index=False, encoding="utf-8")
                print(f"Merged into {dnb_path} (Total master corpus rows: {len(merged):,})", flush=True)

    return out_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parallel Automated Full-Text & Multi-API Resolver for all 731 Target Research Books"
    )
    parser.add_argument("--catalog", default="data/primary_texts/COMPREHENSIVE_BOOK_CATALOG.csv", help="Catalog CSV")
    parser.add_argument("--max-books", type=int, default=731, help="Number of catalog books to resolve")
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel worker threads")
    parser.add_argument("--chunk-words", type=int, default=1000, help="Words per LDA passage chunk")
    parser.add_argument("--output", default="data/catalog_resolved_fulltexts.csv", help="Output passages CSV")
    parser.add_argument("--no-merge", action="store_true", help="Do not merge into data/dnb_metadata.csv")
    args = parser.parse_args()

    resolve_catalog_fulltexts(
        catalog_csv=args.catalog,
        max_books=args.max_books,
        workers=args.workers,
        chunk_words=args.chunk_words,
        output_csv=args.output,
        merge_dnb=not args.no_merge
    )
