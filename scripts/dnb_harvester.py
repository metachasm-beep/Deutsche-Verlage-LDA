import argparse
import os
import re
import sys
import time
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
import requests
import xml.etree.ElementTree as ET
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.fulltext_ingester import chunk_fulltext_words
from scripts.stream_full_books_cloud import stream_entire_pdf_book_in_ram
from scripts.resolve_catalog_fulltexts import is_clean_modern_german
from scripts.hathitrust_fullbook_harvester import (
    isbn_variants,
    batch_resolve_hathitrust_volumes,
    extract_htrc_book_passages,
    is_german_passage,
    load_all_dnb_shards,
    save_sharded_dnb_corpus,
)

# Suppress InsecureRequestWarning when falling back on Windows SSL cert stores
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HEADERS = {
    "User-Agent": "DeutscheVerlageLDA-DNB-Harvester/6.0 (JNU Centre for German Studies; mailto:paul@jnu.ac.in)"
}

# Namespaces for DNB SRU & MARC21 XML
NS = {
    "zs": "http://www.loc.gov/zing/srw/",
    "marc": "http://www.loc.gov/MARC21/slim",
}

# All 38 German Target Publishers:
# (Canonical Name, DNB vlg= query token, Wave-5 pages already done, Wave-6 total pages to reach)
DNB_TARGET_PUBLISHERS = [
    # Core 12 Publishers (Deep Pagination up to 1,400 records per publisher)
    ("Evangelische Verlagsanstalt", "Evangelische", 6, 14),
    ("Gütersloher Verlagshaus", "Gütersloher", 6, 14),
    ("Herder", "Herder", 6, 14),
    ("Kösel", "Kösel", 5, 11),
    ("Patmos", "Patmos", 5, 11),
    ("Suhrkamp", "Suhrkamp", 6, 13),
    ("Rowohlt", "Rowohlt", 5, 11),
    ("Fischer", "Fischer", 5, 11),
    ("Klett-Cotta", "Klett", 5, 11),
    ("Kiepenheuer", "Kiepenheuer", 4, 8),
    ("Wagenbach", "Wagenbach", 3, 6),
    ("Alibri", "Alibri", 4, 7),
    # 26 Major Extended Academic & Confessional Religion/Philosophy/Sociology Imprints
    ("Vandenhoeck & Ruprecht", "Vandenhoeck", 5, 12),
    ("Mohr Siebeck", "Mohr", 5, 12),
    ("Kohlhammer", "Kohlhammer", 5, 12),
    ("C.H. Beck", "Beck", 5, 11),
    ("De Gruyter / Transcript", "Gruyter", 5, 12),
    ("De Gruyter / Transcript", "Transcript", 5, 11),
    ("Herder (Grünewald)", "Grünewald", 4, 9),
    ("Gütersloher Verlagshaus (Chr. Kaiser)", "Kaiser", 4, 9),
    ("Herder (Kreuz)", "Kreuz", 4, 9),
    ("Patmos (Schwabenverlag)", "Schwabenverlag", 4, 8),
    ("Herder (Benziger)", "Benziger", 4, 8),
    ("Schöningh", "Schöningh", 4, 9),
    ("Aschendorff", "Aschendorff", 4, 9),
    ("Pustet", "Pustet", 4, 9),
    ("Echter", "Echter", 4, 9),
    ("Bonifatius", "Bonifatius", 4, 8),
    ("Neukirchener", "Neukirchener", 4, 9),
    ("Calwer", "Calwer", 4, 8),
    ("Campus", "Campus", 4, 8),
    ("Insel", "Insel", 3, 6),
    ("Meiner", "Meiner", 4, 8),
    ("Wallstein", "Wallstein", 3, 6),
    ("Nomos / Alber", "Alber", 4, 8),
    ("Wilhelm Fink", "Fink", 3, 6),
    ("Frommann-Holzboog", "Frommann", 3, 6),
    ("Böhlau", "Böhlau", 3, 8),
    ("Schwabe", "Schwabe", 3, 6),
]

# Direct DNB Thematic Subject & DDC Queries across RQ1, RQ2, and RQ3 (1970-2025)
# (Query CQL, start_page_idx, end_page_idx)
DNB_THEMATIC_QUERIES = [
    ("sw=Religionskritik*", 4, 8),
    ("sw=Atheismus*", 4, 8),
    ("sw=Säkularisierung*", 4, 8),
    ("sw=Kirchenkritik*", 3, 7),
    ("sw=Kirchenaustritt* or sw=Konfessionslos*", 3, 6),
    ("sw=Religionssoziologie*", 4, 8),
    ("sw=Religionspsychologie*", 3, 7),
    ("sw=Religionsphilosophie*", 4, 8),
    ("sw=Spiritualität* and (dcs=200* or dcs=230*)", 4, 8),
    ("sw=Achtsamkeit* and (dcs=200* or dcs=150*)", 3, 7),
    ("sw=Lebenshilfe* and (dcs=200* or dcs=230*)", 3, 7),
    ("sw=Seelsorge*", 4, 8),
    ("sw=Dogmatik*", 4, 8),
    ("sw=Sozialethik* or sw=Christliche Ethik*", 3, 7),
    ("sw=Ökumene* or sw=Ökumenische*", 3, 7),
    ("sw=Gottesfrage*", 3, 6),
    ("sw=Mystik*", 3, 7),
    ("sw=Fundamentalismus* and sw=Religion*", 3, 6),
    ("sw=Religionspädagogik*", 3, 7),
    ("sw=Kirchenmitgliedschaft*", 2, 5),
    # 12 Brand-New Wave-6 Thematic CQL Queries (Pages 0..4 -> startRecord 1..301)
    ("sw=Kirchenkampf*", 0, 4),
    ("sw=Reformation* and (dcs=200* or dcs=230*)", 0, 4),
    ("sw=Neues Testament*", 0, 4),
    ("sw=Altes Testament*", 0, 4),
    ("sw=Bibelwissenschaft* or sw=Exegese*", 0, 4),
    ("sw=Liturgie* or sw=Gottesdienst*", 0, 4),
    ("sw=Diakonie* or sw=Caritas*", 0, 4),
    ("sw=Religionsunterricht*", 0, 4),
    ("sw=Kirchenrecht* or sw=Staatskirchenrecht*", 0, 4),
    ("sw=Kirchengeschichte*", 0, 4),
    ("sw=Moraltheologie* or sw=Theologische Ethik*", 0, 4),
    ("sw=Christologie* or sw=Ekklesiologie*", 0, 4),
]


def normalize_german_text(text: str) -> str:
    """
    Normalizes MARC21 NFD combining diacritics (e.g., 'a' + '\\u0308') into
    canonical NFC German characters ('ä', 'ö', 'ü', 'ß'), removes MARC21 non-sorting
    markers ('˜', 'œ') and control bytes, and cleans whitespace.
    """
    if not text:
        return ""
    normalized = unicodedata.normalize("NFC", str(text))
    normalized = normalized.replace("˜", "").replace("œ", "")
    normalized = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def fetch_url_with_ssl_fallback(url: str, params: dict = None, timeout: int = 18):
    """
    Executes a GET request with standard SSL verification first, falling back to
    verify=False if the local Windows certificate store lacks the DNB issuer CA.
    """
    try:
        return requests.get(url, params=params, headers=HEADERS, timeout=timeout)
    except requests.exceptions.SSLError:
        return requests.get(url, params=params, headers=HEADERS, timeout=timeout, verify=False)


def map_dnb_imprint_to_canonical(raw_pub: str, fallback: str = None) -> str:
    if fallback:
        return fallback
    p = (raw_pub or "").lower()
    mapping = [
        ("suhrkamp", "Suhrkamp"),
        ("wagenbach", "Wagenbach"),
        ("alibri", "Alibri"),
        ("rowohlt", "Rowohlt"),
        ("fischer", "Fischer"),
        ("kiepenheuer", "Kiepenheuer"),
        ("klett", "Klett-Cotta"),
        ("gütersloher", "Gütersloher Verlagshaus"),
        ("kaiser", "Gütersloher Verlagshaus (Chr. Kaiser)"),
        ("grünewald", "Herder (Grünewald)"),
        ("kreuz", "Herder (Kreuz)"),
        ("benziger", "Herder (Benziger)"),
        ("herder", "Herder"),
        ("evangelische verlagsanstalt", "Evangelische Verlagsanstalt"),
        ("eva", "Evangelische Verlagsanstalt"),
        ("kösel", "Kösel"),
        ("schwabenverlag", "Patmos (Schwabenverlag)"),
        ("patmos", "Patmos"),
        ("vandenhoeck", "Vandenhoeck & Ruprecht"),
        ("mohr", "Mohr Siebeck"),
        ("kohlhammer", "Kohlhammer"),
        ("beck", "C.H. Beck"),
        ("schöningh", "Schöningh"),
        ("aschendorff", "Aschendorff"),
        ("pustet", "Pustet"),
        ("echter", "Echter"),
        ("bonifatius", "Bonifatius"),
        ("neukirchener", "Neukirchener"),
        ("calwer", "Calwer"),
        ("campus", "Campus"),
        ("insel", "Insel"),
        ("meiner", "Meiner"),
        ("wallstein", "Wallstein"),
        ("alber", "Nomos / Alber"),
        ("nomos", "Nomos / Alber"),
        ("fink", "Wilhelm Fink"),
        ("frommann", "Frommann-Holzboog"),
        ("böhlau", "Böhlau"),
        ("schwabe", "Schwabe"),
        ("transcript", "De Gruyter / Transcript"),
        ("gruyter", "De Gruyter / Transcript"),
        ("springer", "Springer Nature (Holtzbrinck)"),
        ("lit", "LIT Verlag"),
    ]
    for needle, canon in mapping:
        if needle in p:
            return canon
    return normalize_german_text(raw_pub) if raw_pub else "DNB Monograph (DE)"


def fetch_dnb_blurb(blurb_url: str) -> str:
    """
    Fetches and strips HTML from a DNB Inhaltstext (Tag 856) publisher blurb URL
    (deposit.dnb.de/cgi-bin/dokserv or services.dnb.de/plus/idn/.../blurb/).
    """
    if not blurb_url:
        return ""
    try:
        resp = requests.get(blurb_url, headers=HEADERS, timeout=10, verify=False)
        if resp.status_code == 200:
            raw_html = resp.text
            p_matches = re.findall(r"<p[^>]*>(.*?)</p>", raw_html, flags=re.DOTALL | re.IGNORECASE)
            content = " ".join(p_matches) if p_matches else raw_html
            clean = re.sub(r"<[^>]+>", " ", content)
            clean = (
                clean.replace("&#xa0;", " ")
                .replace("&nbsp;", " ")
                .replace("&quot;", '"')
                .replace("&amp;", "&")
            )
            return normalize_german_text(clean)
    except Exception:
        pass
    return ""


def parse_marc_record(marc_data, canonical_publisher: str = None, fetch_blurbs: bool = False) -> dict:
    """
    Extracts rich bibliographic, ISBN, Open-Access PDF, TOC PDF, and discursive fields from a DNB MARC21 XML record:
    - Tag 001: DNB IDN (Unique Record Identifier)
    - Tag 020 ($a, $9): 10- or 13-digit ISBNs for HathiTrust cross-walk
    - Tag 245 ($a, $b): Main title and subtitle
    - Tag 100 / 700 ($a): Primary author or editor
    - Tag 260 / 264 ($b, $c): Publisher imprint and publication year
    - Tag 520 ($a): Embedded abstract / summary note
    - Tag 650 / 653 / 689 ($a): Controlled GND Schlagwörter & VLB subject paths
    - Tag 856 ($u where $3='Inhaltstext' or '/blurb/'): DNB deposit.dnb.de / services.dnb.de publisher blurb URL
    - Tag 856 ($u where $3='Inhaltsverzeichnis' or '/04'): DNB B:DE-101 digitized TOC & excerpt PDF URL
    - Tag 856 ($u 'd-nb.info/.../34' paired with sibling $z='kostenfrei'): True DNB Open-Access Full-Book PDF URL
    """
    idn_el = marc_data.find("marc:controlfield[@tag='001']", NS)
    idn = idn_el.text.strip() if (idn_el is not None and idn_el.text) else ""

    title_main = ""
    subtitle = ""
    author = ""
    editor = ""
    date = ""
    publisher = ""
    isbn = ""
    abstracts = []
    keywords = []
    blurb_url = ""
    toc_pdf_url = ""
    dnb_34_url = ""
    is_kostenfrei = False

    for field in marc_data.findall("marc:datafield", NS):
        tag = field.get("tag")

        if tag == "020" and not isbn:
            for code in ("a", "9"):
                sub = field.find(f"marc:subfield[@code='{code}']", NS)
                if sub is not None and sub.text:
                    cand = re.sub(r"[^0-9Xx]", "", sub.text.split()[0]).upper()
                    if len(cand) in (10, 13):
                        isbn = cand
                        break

        elif tag == "245":
            sub_a = field.find("marc:subfield[@code='a']", NS)
            sub_b = field.find("marc:subfield[@code='b']", NS)
            if sub_a is not None and sub_a.text:
                title_main = normalize_german_text(sub_a.text)
            if sub_b is not None and sub_b.text:
                subtitle = normalize_german_text(sub_b.text)

        elif tag == "100":
            sub_a = field.find("marc:subfield[@code='a']", NS)
            if sub_a is not None and sub_a.text:
                author = normalize_german_text(sub_a.text)

        elif tag == "700" and not editor:
            sub_a = field.find("marc:subfield[@code='a']", NS)
            if sub_a is not None and sub_a.text:
                editor = normalize_german_text(sub_a.text)

        elif tag in ("260", "264"):
            sub_c = field.find("marc:subfield[@code='c']", NS)
            sub_b = field.find("marc:subfield[@code='b']", NS)
            if sub_c is not None and sub_c.text and not date:
                year_match = re.search(r"(19[789]\d|20[012]\d)", sub_c.text)
                if year_match:
                    date = year_match.group(1)
            if sub_b is not None and sub_b.text and not publisher:
                publisher = normalize_german_text(sub_b.text)

        elif tag == "520":
            sub_a = field.find("marc:subfield[@code='a']", NS)
            if sub_a is not None and sub_a.text:
                abstracts.append(normalize_german_text(sub_a.text))

        elif tag in ("650", "653", "689"):
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

        elif tag == "856":
            sub_3 = field.find("marc:subfield[@code='3']", NS)
            sub_u = field.find("marc:subfield[@code='u']", NS)
            sub_z = field.find("marc:subfield[@code='z']", NS)
            u_str = sub_u.text.strip() if (sub_u is not None and sub_u.text) else ""
            s3_str = sub_3.text.strip().lower() if (sub_3 is not None and sub_3.text) else ""
            sz_str = sub_z.text.strip().lower() if (sub_z is not None and sub_z.text) else ""

            if "kostenfrei" in sz_str or "open access" in sz_str:
                is_kostenfrei = True

            if u_str:
                if (
                    "inhaltstext" in s3_str
                    or "deposit.dnb.de/cgi-bin/dokserv" in u_str
                    or "/blurb/" in u_str
                ) and not blurb_url:
                    blurb_url = u_str
                elif (
                    "inhaltsverzeichnis" in s3_str or u_str.endswith("/04")
                ) and "d-nb.info" in u_str and not toc_pdf_url:
                    toc_pdf_url = u_str
                elif u_str.endswith("/34") and "d-nb.info" in u_str and not dnb_34_url:
                    dnb_34_url = u_str

    # Pair sibling $z='kostenfrei' with the record's d-nb.info/{idn}/34 direct download URL
    oa_pdf_url = dnb_34_url if (is_kostenfrei and dnb_34_url) else ""

    full_title = f"{title_main}: {subtitle}" if subtitle else title_main
    creator = author if author else (editor or "o. V.")
    final_publisher = map_dnb_imprint_to_canonical(publisher, fallback=canonical_publisher)

    blurb_text = fetch_dnb_blurb(blurb_url) if (fetch_blurbs and blurb_url) else ""
    abstract_str = " ".join(abstracts)
    keyword_str = ", ".join(keywords)

    text_segments = [s for s in [full_title, abstract_str, blurb_text, keyword_str] if s]
    combined_text = ". ".join(text_segments)

    return {
        "idn": idn,
        "isbn": isbn,
        "title": full_title,
        "author": creator,
        "date": date,
        "decade": f"{date[:3]}0s" if (date and len(date) == 4) else "2010s",
        "publisher": final_publisher,
        "raw_imprint": publisher,
        "keywords": keyword_str,
        "abstract_note": abstract_str,
        "blurb_url": blurb_url,
        "toc_pdf_url": toc_pdf_url,
        "oa_pdf_url": oa_pdf_url,
        "abstract": blurb_text or abstract_str,
        "text": combined_text,
    }


def harvest_dnb(
    publisher_names=None,
    start_year: int = 2005,
    max_records_per_publisher: int = 25,
    fetch_blurbs: bool = True,
) -> pd.DataFrame:
    """
    Legacy-compatible helper for quick single-page DNB SRU sampling.
    """
    base_url = "https://services.dnb.de/sru/dnb"
    records = []
    subject_cql = "(dcs=200* or dcs=230* or hsg=200 or hsg=230)"
    year_cql = f"jhr>={start_year}"

    if not publisher_names:
        publisher_names = [
            "Herder",
            "Evangelische Verlagsanstalt",
            "Gütersloher Verlagshaus",
            "Suhrkamp",
            "Alibri",
            "Rowohlt",
            "Patmos",
            "Kösel",
        ]

    for pub in publisher_names:
        cql_query = f'{subject_cql} and vlg="{pub}" and {year_cql}'
        params = {
            "operation": "searchRetrieve",
            "version": "1.1",
            "query": cql_query,
            "recordSchema": "MARC21-xml",
            "maximumRecords": max_records_per_publisher,
        }
        try:
            response = fetch_url_with_ssl_fallback(base_url, params=params)
            response.raise_for_status()
            tree = ET.fromstring(response.content)
            for srw_rec in tree.findall(".//zs:record", NS):
                marc_data = srw_rec.find(".//marc:record", NS)
                if marc_data is None:
                    continue
                parsed = parse_marc_record(marc_data, canonical_publisher=pub, fetch_blurbs=fetch_blurbs)
                if parsed["title"] and parsed["date"]:
                    records.append(parsed)
        except Exception:
            pass
    return pd.DataFrame(records)


def harvest_dnb_wave6_deep(
    already_seen_htids: set[str],
    already_matched_isbns: set[str],
    already_seen_urls: set[str],
    already_seen_titles: set[str],
    workers: int = 16,
    chunk_words: int = 1000,
    max_chunks_per_book: int = 75,
    max_toc_pdfs: int = 800,
) -> tuple[list[dict], list[dict]]:
    """
    Wave-6 Ultra-Deep Deutsche Nationalbibliothek (DNB) SRU v1.1 Harvester (1970-2025):
      1. Queries deep SRU pagination (startRecord=601..1400 for 2004-2025 & startRecord=301..700 for 1970-2003)
         across all 38 target German publishers + 32 thematic CQL queries, AND scans Wave-5 pages for
         sibling-matched `$z='kostenfrei'` `/34` Open-Access books and `/04` TOC/excerpt PDFs.
      2. Stream A (Deep-Page DNB ISBNs -> HathiTrust HTRC Full Printed Books): Resolves all new 10/13-digit
         DNB ISBNs against HathiTrust and streams complete page-by-page books via HTRC EF v2.0.
      3. Stream B (Sibling-Matched `$z='kostenfrei'` DNB `/34` Open-Access Full Books): Streams 100% free
         full-text PDF monographs hosted on `d-nb.info/{idn}/34`.
      4. Stream C (DNB Digitized `/04` `Inhaltsverzeichnis` & Excerpt PDFs): Concurrently streams multi-page
         DNB digitized tables of contents, prefaces, and reading samples (`d-nb.info/{idn}/04`).
      5. Stream D (Deep-Page DNB `deposit.dnb.de` & `/plus/idn/.../blurb/` `Inhaltstexte` & `MARC 520` Abstracts).
    """
    base_url = "https://services.dnb.de/sru/dnb"

    modern_subj_cql = (
        "(dcs=200* or dcs=230* or hsg=200 or hsg=230 or "
        "sw=Religion* or sw=Theologie* or sw=Kirche* or sw=Glaube* or "
        "sw=Säkular* or sw=Atheismus* or sw=Spiritualität* or sw=Seelsorge* or sw=Ethik*)"
    )
    hist_subj_cql = (
        "(sw=Religion* or sw=Theologie* or sw=Kirche* or sw=Glaube* or sw=Christentum* or "
        "sw=Gott* or sw=Säkular* or sw=Atheismus* or sw=Spiritualität* or sw=Seelsorge* or "
        "sw=Ethik* or sw=Bibel* or sw=Kathol* or sw=Evangelisch*)"
    )

    sru_tasks = []
    for canon_pub, vlg_term, wave5_pages, wave6_end_pages in DNB_TARGET_PUBLISHERS:
        # Era 1: 2004-2025 (Include pages 0..wave6_end_pages so we capture sibling-matched kostenfrei /34 & /04 TOCs
        # from pages 0..wave5_pages AND brand-new ISBNs/blurbs from wave5_pages..wave6_end_pages)
        q_mod = f'{modern_subj_cql} and vlg="{vlg_term}" and jhr>=2004 and jhr<=2025'
        for p_idx in range(0, wave6_end_pages):
            sru_tasks.append((canon_pub, q_mod, p_idx * 100 + 1, p_idx >= wave5_pages))

        # Era 2: 1970-2003 (Deep pages from wave5_hist_pages to wave6_hist_pages)
        w5_hist = max(2, wave5_pages // 2)
        w6_hist = max(4, wave6_end_pages // 2)
        q_hist = f'{hist_subj_cql} and vlg="{vlg_term}" and jhr>=1970 and jhr<=2003'
        for p_idx in range(w5_hist, w6_hist):
            sru_tasks.append((canon_pub, q_hist, p_idx * 100 + 1, True))

    for theme_cql, start_p, end_p in DNB_THEMATIC_QUERIES:
        q_theme = f"({theme_cql}) and jhr>=1970 and jhr<=2025"
        for p_idx in range(start_p, end_p):
            sru_tasks.append((None, q_theme, p_idx * 100 + 1, True))

    print(
        f"Wave-6 Deep DNB SRU Harvester: Querying {len(sru_tasks)} SRU pages "
        f"(maximumRecords=100 per page -> up to {len(sru_tasks)*100:,} DNB MARC21 records across 1970-2025)...",
        flush=True,
    )

    unique_records = {}
    lock = threading.Lock()

    def _fetch_dnb_sru_page(task):
        canon_pub, cql_query, start_rec, is_deep_page = task
        parsed_list = []
        try:
            resp = requests.get(
                base_url,
                params={
                    "operation": "searchRetrieve",
                    "version": "1.1",
                    "query": cql_query,
                    "recordSchema": "MARC21-xml",
                    "maximumRecords": "100",
                    "startRecord": str(start_rec),
                },
                headers=HEADERS,
                verify=False,
                timeout=20,
            )
            if resp.status_code != 200:
                return parsed_list
            tree = ET.fromstring(resp.content)
            for srw_rec in tree.findall(".//zs:record", NS):
                marc_data = srw_rec.find(".//marc:record", NS)
                if marc_data is None:
                    continue
                rec = parse_marc_record(marc_data, canonical_publisher=canon_pub, fetch_blurbs=False)
                if rec["title"] and rec["date"]:
                    rec["is_deep_page"] = is_deep_page
                    parsed_list.append(rec)
        except Exception:
            pass
        return parsed_list

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_fetch_dnb_sru_page, t) for t in sru_tasks]
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                with lock:
                    for r in res:
                        key = r["idn"] or f"{r['title'].lower()}_{r['date']}"
                        if key not in unique_records:
                            unique_records[key] = r
                        elif r.get("is_deep_page"):
                            unique_records[key]["is_deep_page"] = True

    all_dnb_records = list(unique_records.values())
    deep_records = [r for r in all_dnb_records if r.get("is_deep_page")]
    print(
        f"  -> Retrieved {len(all_dnb_records):,} unique DNB MARC21 records "
        f"({len(deep_records):,} from brand-new Wave-6 deep SRU pages)!",
        flush=True,
    )

    # =========================================================================
    # STREAM A: Wave-6 Deep-Page DNB ISBNs -> HathiTrust HTRC Full Printed Books
    # =========================================================================
    dnb_isbn_candidates = []
    seen_isbns_local = set(already_matched_isbns)
    for r in deep_records:
        if not r["isbn"]:
            continue
        variants = isbn_variants(r["isbn"])
        if any(v in seen_isbns_local for v in variants):
            continue
        for v in variants:
            seen_isbns_local.add(v)
        dnb_isbn_candidates.append({
            "title": r["title"],
            "author": r["author"],
            "publisher": r["publisher"],
            "date": r["date"],
            "decade": r["decade"],
            "isbn": r["isbn"],
            "ppn": r["idn"],
            "bkl_codes": "DNB-Wave6-200/230",
        })

    print(
        f"\n[Stream A] Wave-6 DNB -> HathiTrust Cross-Walk: Queued {len(dnb_isbn_candidates):,} NEW deep-page DNB ISBNs...",
        flush=True,
    )
    dnb_isbn_df = pd.DataFrame(dnb_isbn_candidates)
    matched_ht_books = batch_resolve_hathitrust_volumes(
        dnb_isbn_df,
        already_seen_htids=already_seen_htids,
        batch_size=15,
        workers=workers,
    )

    htrc_passages = []
    htrc_summaries = []
    if matched_ht_books:
        print(
            f"Streaming full-book page-by-page tokens from HTRC EF-API for {len(matched_ht_books)} Wave-6 DNB-matched books...",
            flush=True,
        )
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {
                ex.submit(extract_htrc_book_passages, b, chunk_words, max_chunks_per_book): b
                for b in matched_ht_books
            }
            for fut in as_completed(futs):
                p_list, summ = fut.result()
                if p_list:
                    htrc_passages.extend(p_list)
                    htrc_summaries.append(summ)
                    print(
                        f"  + [WAVE-6 DNB->HTRC BOOK #{len(htrc_summaries)}] ({summ['date']} | {summ['publisher'][:28]}) "
                        f"{summ['title'][:45]}... [{summ['htid']}] -> {summ['pages']} pages | "
                        f"{summ['extracted_words']:,} words ({summ['passages']} passages)",
                        flush=True,
                    )

    # =========================================================================
    # STREAM B: Sibling-Matched `$z='kostenfrei'` DNB `/34` Open-Access Full Books
    # =========================================================================
    oa_candidates = [
        r for r in all_dnb_records
        if r["oa_pdf_url"] and r["oa_pdf_url"] not in already_seen_urls
    ]
    print(
        f"\n[Stream B] True `$z='kostenfrei'` DNB Open-Access Full-Book PDFs (`d-nb.info/.../34`): "
        f"Found {len(oa_candidates):,} verified OA books!",
        flush=True,
    )
    dnb_oa_passages = []
    oa_books_ok = 0

    def _stream_dnb_oa(r):
        txt, pages = stream_entire_pdf_book_in_ram(r["oa_pdf_url"], max_pages=320)
        if not txt or len(txt.split()) < 1000:
            return []
        if not is_clean_modern_german(txt) or not is_german_passage(txt):
            return []
        words = txt.split()
        max_w = 55 * chunk_words
        if len(words) > max_w:
            txt = " ".join(words[:max_w])
        chunks = [ch for ch in chunk_fulltext_words(txt, chunk_words=chunk_words) if is_german_passage(ch)]
        out = []
        for idx, ch in enumerate(chunks, start=1):
            compact_ch = " ".join(ch.split()[:420])
            out.append({
                "title": f"{r['title']} [DNB-OA-Vollbuch-Abschnitt {idx}/{len(chunks)}]",
                "author": r["author"],
                "date": r["date"],
                "decade": r["decade"],
                "publisher": r["publisher"],
                "corpus_layer": "dnb_oa_fullbook",
                "source_file": r["oa_pdf_url"],
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "word_count": len(ch.split()),
                "abstract": compact_ch[:240],
                "text": f"{r['title']}. {r['author']}. {r['publisher']}. {compact_ch}",
            })
        return out

    if oa_candidates:
        with ThreadPoolExecutor(max_workers=min(workers, 10)) as ex:
            futs = {ex.submit(_stream_dnb_oa, r): r for r in oa_candidates}
            for fut in as_completed(futs):
                r = futs[fut]
                res = fut.result()
                if res:
                    oa_books_ok += 1
                    dnb_oa_passages.extend(res)
                    w_sum = sum(x["word_count"] for x in res)
                    print(
                        f"  + [DNB OA FULL BOOK #{oa_books_ok}] ({r['date']} | {r['publisher'][:28]}) "
                        f"{r['title'][:45]}... -> {w_sum:,} words ({len(res)} passages)",
                        flush=True,
                    )

    # =========================================================================
    # STREAM C: DNB Digitized `/04` `Inhaltsverzeichnis` & Reading-Sample PDFs
    # =========================================================================
    toc_candidates = [
        r for r in all_dnb_records
        if r["toc_pdf_url"]
        and r["toc_pdf_url"] not in already_seen_urls
        and f"{r['title']} [dnb-inhaltsverzeichnis & leseprobe]".lower() not in already_seen_titles
    ]
    print(
        f"\n[Stream C] DNB Digitized `/04` `Inhaltsverzeichnis` & Excerpt PDFs: "
        f"Streaming top {min(len(toc_candidates), max_toc_pdfs):,} (out of {len(toc_candidates):,} available `/04` PDFs)...",
        flush=True,
    )
    dnb_toc_passages = []

    def _stream_dnb_toc(r):
        txt, pages = stream_entire_pdf_book_in_ram(r["toc_pdf_url"], max_pages=12)
        if not txt:
            return None
        # Strip repetitive dot leaders (".....") from tables of contents
        clean_toc = re.sub(r"\.{3,}", " ", txt)
        clean_toc = normalize_german_text(clean_toc)
        words = clean_toc.split()
        if len(words) < 90:
            return None
        compact_toc = " ".join(words[:650])
        kw_str = r["keywords"] or ""
        abs_str = r["abstract_note"] or ""
        full_txt = f"{r['title']}. {r['author']}. {r['publisher']}. {compact_toc} {abs_str} {kw_str}".strip()
        return {
            "title": f"{r['title']} [DNB-Inhaltsverzeichnis & Leseprobe]",
            "author": r["author"],
            "date": r["date"],
            "decade": r["decade"],
            "publisher": r["publisher"],
            "corpus_layer": "dnb_toc_pdf_fulltext",
            "source_file": r["toc_pdf_url"],
            "chunk_index": 1,
            "total_chunks": 1,
            "word_count": len(words),
            "abstract": compact_toc[:240],
            "text": full_txt,
        }

    if toc_candidates:
        with ThreadPoolExecutor(max_workers=20) as ex:
            futs = [ex.submit(_stream_dnb_toc, r) for r in toc_candidates[:max_toc_pdfs]]
            for fut in as_completed(futs):
                res = fut.result()
                if res:
                    dnb_toc_passages.append(res)

    print(
        f"  -> Extracted {len(dnb_toc_passages):,} rich DNB `/04` `Inhaltsverzeichnis` & Leseprobe PDF documents!",
        flush=True,
    )

    # =========================================================================
    # STREAM D: Deep-Page DNB `deposit.dnb.de` & `/blurb/` Inhaltstexte & Abstracts
    # =========================================================================
    blurb_candidates = [
        r for r in all_dnb_records
        if (r["blurb_url"] or r["abstract_note"])
        and r["title"].lower().strip() not in already_seen_titles
        and (not r["blurb_url"] or r["blurb_url"] not in already_seen_urls)
    ]
    print(
        f"\n[Stream D] Wave-6 DNB `deposit.dnb.de` & `/blurb/` Inhaltstexte & Abstracts: "
        f"Fetching {len(blurb_candidates):,} NEW DNB deposit texts...",
        flush=True,
    )

    dnb_deposit_passages = []

    def _enrich_dnb_deposit(r):
        blurb_txt = fetch_dnb_blurb(r["blurb_url"]) if r["blurb_url"] else ""
        abs_txt = r["abstract_note"] or ""
        kw_txt = r["keywords"] or ""
        body_parts = [p for p in [blurb_txt, abs_txt, kw_txt] if p]
        body_str = " ".join(body_parts).strip()
        full_txt = f"{r['title']}. {r['author']}. {r['publisher']}. {body_str}".strip()
        wc = len(full_txt.split())
        if wc < 45:
            return None
        src_url = r["blurb_url"] or (f"https://d-nb.info/{r['idn']}" if r["idn"] else "https://portal.dnb.de")
        return {
            "title": r["title"],
            "author": r["author"],
            "date": r["date"],
            "decade": r["decade"],
            "publisher": r["publisher"],
            "corpus_layer": "dnb_deposit_inhaltstext",
            "source_file": src_url,
            "chunk_index": 1,
            "total_chunks": 1,
            "word_count": wc,
            "abstract": (blurb_txt or abs_txt or kw_txt)[:240],
            "text": full_txt,
        }

    with ThreadPoolExecutor(max_workers=28) as ex:
        futs = [ex.submit(_enrich_dnb_deposit, r) for r in blurb_candidates]
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                dnb_deposit_passages.append(res)

    print(
        f"  -> Extracted {len(dnb_deposit_passages):,} NEW DNB `Inhaltstext` & abstract documents!",
        flush=True,
    )

    all_new_passages = htrc_passages + dnb_oa_passages + dnb_toc_passages + dnb_deposit_passages
    return all_new_passages, htrc_summaries


def main():
    parser = argparse.ArgumentParser(
        description="Wave-6 Ultra-Deep Deutsche Nationalbibliothek (DNB) Harvester (1970-2025)"
    )
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--chunk-words", type=int, default=1000)
    parser.add_argument("--max-chunks-per-book", type=int, default=75)
    parser.add_argument("--max-toc-pdfs", type=int, default=800)
    parser.add_argument("--no-merge", action="store_true")
    args = parser.parse_args()

    start_t = time.time()

    ht_csv = "data/primary_texts/HATHITRUST_MATCHED_BOOKS.csv"
    already_seen_htids = set()
    already_matched_isbns = set()
    existing_ht_summaries = []
    if os.path.exists(ht_csv):
        ht_df = pd.read_csv(ht_csv, encoding="utf-8")
        existing_ht_summaries = ht_df.to_dict(orient="records")
        for _, r in ht_df.iterrows():
            if pd.notna(r.get("htid")):
                already_seen_htids.add(str(r["htid"]).strip())
            if pd.notna(r.get("isbn")):
                for v in isbn_variants(str(r["isbn"])):
                    already_matched_isbns.add(v)

    dnb_prev = load_all_dnb_shards("data/dnb_metadata.csv")
    already_seen_urls = set()
    already_seen_titles = set()
    if not dnb_prev.empty:
        for u in dnb_prev["source_file"].dropna().unique():
            already_seen_urls.add(str(u).strip())
        for t in dnb_prev["title"].dropna().unique():
            already_seen_titles.add(str(t).lower().strip())

    print(
        f"Starting Wave-6 Ultra-Deep DNB Harvest (1970-2025) across 38 German Publishers & 32 Thematic CQL Queries\n"
        f"  (Existing Corpus: {len(dnb_prev):,} documents | {len(already_seen_htids):,} HTRC books)...",
        flush=True,
    )

    new_passages, new_ht_summaries = harvest_dnb_wave6_deep(
        already_seen_htids=already_seen_htids,
        already_matched_isbns=already_matched_isbns,
        already_seen_urls=already_seen_urls,
        already_seen_titles=already_seen_titles,
        workers=args.workers,
        chunk_words=args.chunk_words,
        max_chunks_per_book=args.max_chunks_per_book,
        max_toc_pdfs=args.max_toc_pdfs,
    )

    if not new_passages:
        print("No new DNB passages discovered beyond existing dataset.", flush=True)
        return

    if new_ht_summaries:
        all_summaries = existing_ht_summaries + new_ht_summaries
        pd.DataFrame(all_summaries).to_csv(ht_csv, index=False, encoding="utf-8")

    new_df = pd.DataFrame(new_passages)
    new_df["_t_key"] = new_df["title"].fillna("").str.lower().str.strip()
    new_df = new_df.drop_duplicates(subset=["_t_key"]).drop(columns=["_t_key"])
    new_df = new_df[~new_df["title"].fillna("").str.lower().str.strip().isin(already_seen_titles)]

    total_new_words = pd.to_numeric(new_df["word_count"], errors="coerce").fillna(250).sum()
    elapsed = time.time() - start_t

    print("\n======================================================================", flush=True)
    print(f"WAVE-6 ULTRA-DEEP DNB HARVEST COMPLETE in {elapsed:.1f}s!", flush=True)
    print(f"  - Stream A (Deep DNB ISBN -> HTRC Full Printed Books): {len(new_ht_summaries)} books ({sum(1 for p in new_passages if p['corpus_layer']=='hathitrust_ef_fullbook_print'):,} passages)", flush=True)
    print(f"  - Stream B (True `$z='kostenfrei'` DNB `/34` OA Full Books): {sum(1 for p in new_passages if p['corpus_layer']=='dnb_oa_fullbook'):,} passages", flush=True)
    print(f"  - Stream C (DNB Digitized `/04` `Inhaltsverzeichnis` & Excerpt PDFs): {sum(1 for p in new_passages if p['corpus_layer']=='dnb_toc_pdf_fulltext'):,} documents", flush=True)
    print(f"  - Stream D (Deep-Page DNB `Inhaltstexte` & Abstracts): {sum(1 for p in new_passages if p['corpus_layer']=='dnb_deposit_inhaltstext'):,} documents", flush=True)
    print(f"  - TOTAL NEW UNIQUE DNB DOCUMENTS ADDED IN WAVE 6: {len(new_df):,} ({int(total_new_words):,} German words!)", flush=True)
    print("======================================================================", flush=True)

    if not args.no_merge:
        merged = pd.concat([dnb_prev, new_df], ignore_index=True)
        save_sharded_dnb_corpus(merged, rows_per_shard=24000)
        total_est_words = pd.to_numeric(merged.get("word_count"), errors="coerce").fillna(950).sum()
        print(
            f"Total Master Corpus Across Shards = {len(merged):,} documents "
            f"(~{int(total_est_words):,} original German words!)",
            flush=True,
        )


if __name__ == "__main__":
    main()
