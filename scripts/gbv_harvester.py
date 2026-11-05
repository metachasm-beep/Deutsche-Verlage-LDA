import argparse
import os
import re
import time
import unicodedata
import urllib3
import requests
import xml.etree.ElementTree as ET
import pandas as pd

# Suppress InsecureRequestWarning when falling back on Windows SSL cert stores
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Namespaces for GBV / K10plus GVK SRU & MARC21 XML
NS = {
    'zs': 'http://www.loc.gov/zing/srw/',
    'marc': 'http://www.loc.gov/MARC21/slim',
    'diag': 'http://www.loc.gov/zing/srw/diagnostic/'
}

# Canonical Basisklassifikation (BKL) Hauptgruppe 11 (Theologie, Religionswissenschaft) mapping
BKL_11_LABELS = {
    "11.00": "Theologie, Religionswissenschaft: Allgemeines",
    "11.01": "Geschichte der Religionswissenschaft und Theologie",
    "11.02": "Philosophie und Theorie der Religion",
    "11.03": "Methoden und Techniken der religiösen Forschung",
    "11.04": "Ausbildung, Beruf, Organisationen",
    "11.05": "Religionssoziologie",
    "11.06": "Religionspsychologie",
    "11.07": "Interreligiöse Beziehungen",
    "11.08": "Religionskritik, Atheismus",
    "11.09": "Religiöse Kunst, religiöse Musik",
    "11.10": "Prähistorische Religionen",
    "11.20": "nichtchristliche Religionen: Allgemeines",
    "11.30": "Judentum",
    "11.40": "Islam",
    "11.50": "Christentum: Allgemeines",
    "11.51": "Kirchengeschichte, Dogmengeschichte",
    "11.52": "Konfessionskunde",
    "11.53": "Katholische Theologie",
    "11.54": "Evangelische Theologie",
    "11.55": "Ostkirchen",
    "11.60": "Systematische Theologie",
    "11.61": "Dogmatik, Konfessionskunde",
    "11.62": "Christliche Ethik",
    "11.70": "Praktische Theologie: Allgemeines",
    "11.71": "Seelsorge, Pastoralpsychologie",
    "11.72": "Kirchenrecht, Kirchenverwaltung",
    "11.73": "Kirchenmusik, Liturgik",
    "11.74": "Homiletik, Katechetik",
    "11.75": "Religionspädagogik",
    "11.76": "Mission, Ökumene, Diakonie",
    "11.99": "Sonstige Religionen, Neue Religiöse Bewegungen, Esoterik"
}


def normalize_german_text(text: str) -> str:
    """
    Normalizes MARC21/PICA NFD combining diacritics into canonical NFC German
    characters ('ä', 'ö', 'ü', 'ß'), strips PICA non-sorting control chars (\x98, \x9c),
    and cleans whitespace.
    """
    if not text:
        return ""
    cleaned = re.sub(r'[\u0080-\u009f˜œ]', '', str(text))
    normalized = unicodedata.normalize('NFC', cleaned)
    return re.sub(r'\s+', ' ', normalized).strip()


def fetch_url_with_ssl_fallback(url: str, params: dict = None, timeout: int = 15):
    """
    Executes a GET request with standard SSL verification first, falling back to
    verify=False if the local Windows certificate store lacks the GBV/DNB issuer CA.
    """
    try:
        return requests.get(url, params=params, timeout=timeout)
    except requests.exceptions.SSLError:
        return requests.get(url, params=params, timeout=timeout, verify=False)


def fetch_blurb_text(blurb_url: str) -> str:
    """
    Fetches and strips HTML from an embedded Inhaltstext (Tag 856) publisher blurb URL.
    """
    if not blurb_url or blurb_url.lower().endswith('.pdf'):
        return ""
    try:
        resp = fetch_url_with_ssl_fallback(blurb_url, timeout=8)
        if resp.status_code == 200 and 'text/html' in resp.headers.get('Content-Type', 'text/html').lower():
            raw_html = resp.text
            p_matches = re.findall(r'<p[^>]*>(.*?)</p>', raw_html, flags=re.DOTALL | re.IGNORECASE)
            content = " ".join(p_matches) if p_matches else raw_html
            clean = re.sub(r'<[^>]+>', ' ', content)
            clean = clean.replace('&#xa0;', ' ').replace('&nbsp;', ' ').replace('&quot;', '"')
            return normalize_german_text(clean)
    except Exception:
        pass
    return ""


def fetch_pdf_text_from_url(pdf_url: str, max_pages: int = 15) -> str:
    """
    Streams a PDF from a GBV/DNB MARC 856 URL (e.g., digitized Inhaltsverzeichnis or
    Open-Access publication) into memory using PyMuPDF (fitz), strips dot leaders and
    page numbers, and returns normalized German text without saving raw PDFs to disk.
    """
    if not pdf_url:
        return ""
    try:
        import pymupdf
        resp = fetch_url_with_ssl_fallback(pdf_url, timeout=10)
        if resp.status_code == 200 and (b'%PDF' in resp.content[:1024] or 'pdf' in resp.headers.get('Content-Type', '').lower()):
            doc = pymupdf.open(stream=resp.content, filetype="pdf")
            pages_text = []
            for page_idx in range(min(len(doc), max_pages)):
                raw_page = doc[page_idx].get_text()
                # Strip table-of-contents dot leaders (e.g. '...... 51') and standalone page numbers
                cleaned_page = re.sub(r'\.{2,}\s*\d*', ' ', raw_page)
                cleaned_page = re.sub(r'\b\d+\b', ' ', cleaned_page)
                pages_text.append(cleaned_page)
            doc.close()
            return normalize_german_text(" ".join(pages_text))
    except Exception:
        pass
    return ""


def parse_gbv_marc_record(
    marc_data,
    canonical_publisher: str = None,
    decade_slice: str = None,
    fetch_blurbs: bool = True
) -> dict:
    """
    Extracts bibliographic, paratextual, PDF table-of-contents, and institutional reception
    fields from a GBV / K10plus MARC21-XML record:
    - Tag 001: GBV PPN (PICA Produktionsnummer)
    - Tag 016 / 035: Cross-referenced DNB ID (DE-101) for lossless deduplication
    - Tag 020 ($a): ISBN
    - Tag 084 ($a, $2='bkl' / 'rvk'): GBV Basisklassifikation & RVK codes
    - Tag 100 / 700 ($a): Primary author or editor
    - Tag 245 ($a, $b): Main title and subtitle
    - Tag 260 / 264 ($b, $c): Publisher imprint and publication year
    - Tag 490 ($a): Publisher series (Reihe, e.g., Suhrkamp Taschenbuch Wissenschaft)
    - Tag 520 ($a): Inline summary / abstract note
    - Tag 650 / 653 / 689 ($a): GND Schlagwörter & subject chains
    - Tag 856 ($u where $3='Inhaltstext' or 'Inhaltsverzeichnis' or Open Access): Blurb & PDF text
    - Tag 924 ($b): Holding libraries count across the GBV network (institutional reception metric)
    """
    ppn = ""
    dnb_id = ""
    isbn = ""
    title_main = ""
    subtitle = ""
    author = ""
    editor = ""
    date = ""
    publisher = ""
    series = ""
    bkl_codes = []
    bkl_labels = []
    rvk_codes = []
    abstracts = []
    keywords = []
    blurb_url = ""
    toc_pdf_url = ""
    oa_pdf_url = ""
    holding_libraries = set()

    for cf in marc_data.findall('marc:controlfield', NS):
        if cf.get('tag') == '001' and cf.text:
            ppn = cf.text.strip()
        elif cf.get('tag') == '008' and cf.text and len(cf.text) >= 11:
            # Fallback publication year from fixed-length controlfield 008 (pos 07-10)
            year_008 = cf.text[7:11]
            if year_008.isdigit():
                date = year_008

    for field in marc_data.findall('marc:datafield', NS):
        tag = field.get('tag')

        if tag == '016':
            sub_a = field.find("marc:subfield[@code='a']", NS)
            sub_2 = field.find("marc:subfield[@code='2']", NS)
            if sub_a is not None and sub_2 is not None and sub_2.text == 'DE-101' and sub_a.text:
                dnb_id = sub_a.text.strip()

        elif tag == '020' and not isbn:
            sub_a = field.find("marc:subfield[@code='a']", NS)
            if sub_a is not None and sub_a.text:
                isbn = normalize_german_text(sub_a.text)

        elif tag == '084':
            sub_a = field.find("marc:subfield[@code='a']", NS)
            sub_2 = field.find("marc:subfield[@code='2']", NS)
            if sub_a is not None and sub_a.text and sub_2 is not None and sub_2.text:
                scheme = sub_2.text.strip().lower()
                code = normalize_german_text(sub_a.text)
                if scheme == 'bkl' and code not in bkl_codes:
                    bkl_codes.append(code)
                    if code in BKL_11_LABELS:
                        bkl_labels.append(BKL_11_LABELS[code])
                elif scheme == 'rvk' and code not in rvk_codes:
                    rvk_codes.append(code)

        elif tag == '245':
            sub_a = field.find("marc:subfield[@code='a']", NS)
            sub_b = field.find("marc:subfield[@code='b']", NS)
            if sub_a is not None and sub_a.text:
                title_main = normalize_german_text(sub_a.text)
            if sub_b is not None and sub_b.text:
                subtitle = normalize_german_text(sub_b.text)

        elif tag == '100':
            sub_a = field.find("marc:subfield[@code='a']", NS)
            if sub_a is not None and sub_a.text:
                author = normalize_german_text(sub_a.text)

        elif tag == '700' and not editor:
            sub_a = field.find("marc:subfield[@code='a']", NS)
            if sub_a is not None and sub_a.text:
                editor = normalize_german_text(sub_a.text)

        elif tag in ('260', '264'):
            sub_c = field.find("marc:subfield[@code='c']", NS)
            sub_b = field.find("marc:subfield[@code='b']", NS)
            if sub_c is not None and sub_c.text:
                year_match = re.search(r'(\d{4})', sub_c.text)
                if year_match:
                    date = year_match.group(1)
            if sub_b is not None and sub_b.text and not publisher:
                publisher = normalize_german_text(sub_b.text)

        elif tag == '490' and not series:
            sub_a = field.find("marc:subfield[@code='a']", NS)
            if sub_a is not None and sub_a.text:
                series = normalize_german_text(sub_a.text)

        elif tag == '520':
            sub_a = field.find("marc:subfield[@code='a']", NS)
            if sub_a is not None and sub_a.text:
                abstracts.append(normalize_german_text(sub_a.text))

        elif tag in ('650', '653', '689'):
            for sub_a in field.findall("marc:subfield[@code='a']", NS):
                if sub_a.text:
                    kw = normalize_german_text(sub_a.text)
                    if kw.startswith("(Produktform)") or kw.startswith("(ISIL)"):
                        continue
                    if kw.startswith("(VLB-WN)"):
                        parts = kw.split(":", 1)
                        if len(parts) > 1:
                            kw = parts[1].replace("Hardcover, Softcover /", "").strip()
                    if kw and kw not in keywords:
                        keywords.append(kw)

        elif tag == '856':
            sub_3 = field.find("marc:subfield[@code='3']", NS)
            sub_u = field.find("marc:subfield[@code='u']", NS)
            sub_z = field.find("marc:subfield[@code='z']", NS)
            if sub_u is not None and sub_u.text:
                u_val = sub_u.text.strip()
                label_3 = sub_3.text.lower() if (sub_3 is not None and sub_3.text) else ""
                note_z = sub_z.text.lower() if (sub_z is not None and sub_z.text) else ""
                if "inhaltstext" in label_3 and not blurb_url:
                    blurb_url = u_val
                elif "inhaltsverzeichnis" in label_3 and not toc_pdf_url:
                    toc_pdf_url = u_val
                elif ("kostenfrei" in note_z or "open access" in note_z) and not oa_pdf_url:
                    oa_pdf_url = u_val

        elif tag == '924':
            sub_b = field.find("marc:subfield[@code='b']", NS)
            if sub_b is not None and sub_b.text:
                holding_libraries.add(sub_b.text.strip())

    # Enrich keywords with human-readable GBV Basisklassifikation labels
    for lbl in bkl_labels:
        if lbl not in keywords:
            keywords.append(lbl)

    full_title = f"{title_main}: {subtitle}" if subtitle else title_main
    creator = author if author else editor
    final_publisher = canonical_publisher if canonical_publisher else (publisher or "Unknown")

    blurb_text = fetch_blurb_text(blurb_url) if (fetch_blurbs and blurb_url) else ""
    toc_text = fetch_pdf_text_from_url(toc_pdf_url, max_pages=8) if (fetch_blurbs and toc_pdf_url) else ""
    oa_text = fetch_pdf_text_from_url(oa_pdf_url, max_pages=25) if (fetch_blurbs and oa_pdf_url) else ""
    abstract_str = " ".join(abstracts)
    keyword_str = ", ".join(keywords)
    bkl_str = ", ".join(bkl_codes)

    # Synthesize dense discursive text for Python Gensim LDA modeling
    text_segments = [
        s for s in [full_title, series, abstract_str, blurb_text, toc_text, oa_text, keyword_str] if s
    ]
    combined_text = ". ".join(text_segments)

    return {
        'ppn': ppn,
        'dnb_id': dnb_id,
        'isbn': isbn,
        'title': full_title,
        'author': creator,
        'date': date,
        'decade': decade_slice or (f"{date[:3]}0s" if (date and len(date) == 4 and date.isdigit()) else ""),
        'publisher': final_publisher,
        'raw_imprint': publisher,
        'series': series,
        'bkl_codes': bkl_str,
        'rvk_codes': ", ".join(rvk_codes),
        'gbv_holdings_count': len(holding_libraries),
        'corpus_layer': 'primary_oa_or_toc' if (oa_text or toc_text) else 'paratext_catalog',
        'keywords': keyword_str,
        'abstract': blurb_text or abstract_str or toc_text[:500],
        'text': combined_text
    }


def harvest_gbv(
    publisher_names=None,
    decades=None,
    bkl_filter: str = "*",
    max_records_per_slice: int = 20,
    fetch_blurbs: bool = True
) -> pd.DataFrame:
    """
    Harvests diachronic bibliographic, paratextual, and library-holdings data from the
    Gemeinsamer Bibliotheksverbund (GBV / K10plus GVK) SRU API v1.1 across 1970–2025
    in German language (`pica.spr=ger`), unrestricted by subject by default.
    """
    base_url = "https://sru.k10plus.de/gvk"
    records = []
    seen_ppns = set()

    if not publisher_names:
        publisher_names = [
            "Suhrkamp",
            "Wagenbach",
            "Alibri",
            "Rowohlt",
            "Fischer",
            "Kiepenheuer",
            "Gütersloher Verlagshaus",
            "Herder",
            "Evangelische Verlagsanstalt",
            "Kösel",
            "Patmos",
            "Klett"
        ]

    if not decades:
        decades = ["197*", "198*", "199*", "200*", "201*", "202*"]

    print(
        f"Harvesting Gemeinsamer Bibliotheksverbund (GBV/GVK) SRU German-language (pica.spr=ger) records "
        f"for BKL={bkl_filter} across {len(publisher_names)} publishers and {len(decades)} decades..."
    )

    for pub in publisher_names:
        pub_total_retrieved = 0
        pub_total_matches = 0

        for dec in decades:
            decade_label = f"{dec[:3]}0s"
            if bkl_filter and bkl_filter not in ("*", "all", "ALL"):
                cql_query = f'pica.vlg="{pub}" and pica.spr=ger and pica.bkl={bkl_filter} and pica.jah={dec}'
            else:
                cql_query = f'pica.vlg="{pub}" and pica.spr=ger and pica.jah={dec}'
            params = {
                'operation': 'searchRetrieve',
                'version': '1.1',
                'query': cql_query,
                'recordSchema': 'marcxml',
                'maximumRecords': max_records_per_slice
            }

            try:
                response = fetch_url_with_ssl_fallback(base_url, params=params)
                response.raise_for_status()

                tree = ET.fromstring(response.content)
                total_hits_el = tree.find('.//zs:numberOfRecords', NS)
                total_hits = int(total_hits_el.text) if (total_hits_el is not None and total_hits_el.text) else 0
                pub_total_matches += total_hits

                srw_records = tree.findall('.//zs:record', NS)
                for srw_rec in srw_records:
                    marc_data = srw_rec.find('.//marc:record', NS)
                    if marc_data is None:
                        continue
                    parsed = parse_gbv_marc_record(
                        marc_data,
                        canonical_publisher=pub,
                        decade_slice=decade_label,
                        fetch_blurbs=fetch_blurbs
                    )
                    if parsed['ppn'] and parsed['ppn'] in seen_ppns:
                        continue
                    if parsed['title'] and parsed['date']:
                        if parsed['ppn']:
                            seen_ppns.add(parsed['ppn'])
                        records.append(parsed)
                        pub_total_retrieved += 1

                time.sleep(0.25)

            except Exception as e:
                print(f"  ! Error harvesting [{pub} | {decade_label}]: {e}")

        print(
            f"  - [{pub:28s}]: Retrieved {pub_total_retrieved:3d} unique records "
            f"(out of {pub_total_matches:5d} total GBV 1970-2025 matches)"
        )

    print(f"Total unique GBV records harvested: {len(records)}")
    return pd.DataFrame(records)


def merge_gbv_with_dnb(gbv_df: pd.DataFrame, dnb_csv_path: str = "data/dnb_metadata.csv") -> pd.DataFrame:
    """
    Deduplicates and merges the GBV 1970–2025 diachronic dataset with the DNB dataset,
    preserving the exact core columns required by lda_pipeline.py while retaining GBV enrichment.
    """
    if not os.path.exists(dnb_csv_path) or gbv_df.empty:
        return gbv_df

    dnb_df = pd.read_csv(dnb_csv_path, encoding="utf-8")
    existing_titles = set(
        dnb_df["title"].dropna().apply(lambda s: s.lower().strip())
    )

    new_gbv_rows = gbv_df[
        ~gbv_df["title"].fillna("").apply(lambda s: s.lower().strip()).isin(existing_titles)
    ]
    combined = pd.concat([dnb_df, new_gbv_rows], ignore_index=True)
    return combined


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Harvest 1970-2025 Comprehensive German-Language Corpus from Gemeinsamer Bibliotheksverbund (GBV/GVK)"
    )
    parser.add_argument("--bkl", default="*", help="GBV Basisklassifikation filter ('*' for all subjects in German language, or e.g. 11.*, 08.*, 71.*)")
    parser.add_argument("--max-per-slice", type=int, default=15, help="Max records per publisher-decade slice")
    parser.add_argument("--no-blurbs", action="store_true", help="Skip fetching external Inhaltstext HTML blurbs")
    parser.add_argument("--output", default="data/gbv_metadata.csv", help="Output CSV path")
    parser.add_argument("--merge-dnb", action="store_true", help="Also merge new records into data/dnb_metadata.csv")
    args = parser.parse_args()

    df_gbv = harvest_gbv(
        bkl_filter=args.bkl,
        max_records_per_slice=args.max_per_slice,
        fetch_blurbs=not args.no_blurbs
    )

    os.makedirs(os.path.dirname(args.output) or "data", exist_ok=True)
    df_gbv.to_csv(args.output, index=False, encoding="utf-8")
    print(f"Saved {len(df_gbv)} enriched GBV records to {args.output}")

    if args.merge_dnb and not df_gbv.empty:
        merged_df = merge_gbv_with_dnb(df_gbv, "data/dnb_metadata.csv")
        merged_df.to_csv("data/dnb_metadata.csv", index=False, encoding="utf-8")
        print(f"Merged corpus saved to data/dnb_metadata.csv (Total records: {len(merged_df)})")
