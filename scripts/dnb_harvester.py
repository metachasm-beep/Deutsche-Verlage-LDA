import argparse
import io
import json
import os
import re
import sys
import time
import threading
import unicodedata
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import fitz

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
    "User-Agent": "DeutscheVerlageLDA-DNB-Harvester/7.0 (JNU Centre for German Studies; mailto:paul@jnu.ac.in)"
}

# Namespaces for DNB SRU & MARC21 XML
NS = {
    "zs": "http://www.loc.gov/zing/srw/",
    "marc": "http://www.loc.gov/MARC21/slim",
}

# All 38 German Target Publishers:
# (Canonical Name, DNB vlg= query token, Wave-7 pages already done for Era 1, Wave-8 total pages to reach)
DNB_TARGET_PUBLISHERS = [
    # Core 12 Publishers (Exhaustive Pagination up to 3,000 records per publisher)
    ("Evangelische Verlagsanstalt", "Evangelische", 24, 30),
    ("Gütersloher Verlagshaus", "Gütersloher", 24, 30),
    ("Herder", "Herder", 24, 30),
    ("Kösel", "Kösel", 18, 24),
    ("Patmos", "Patmos", 18, 24),
    ("Suhrkamp", "Suhrkamp", 22, 28),
    ("Rowohlt", "Rowohlt", 18, 24),
    ("Fischer", "Fischer", 18, 24),
    ("Klett-Cotta", "Klett", 18, 24),
    ("Kiepenheuer", "Kiepenheuer", 13, 18),
    ("Wagenbach", "Wagenbach", 10, 14),
    ("Alibri", "Alibri", 11, 15),
    # 26 Major Extended Academic & Confessional Religion/Philosophy/Sociology Imprints
    ("Vandenhoeck & Ruprecht", "Vandenhoeck", 20, 26),
    ("Mohr Siebeck", "Mohr", 20, 26),
    ("Kohlhammer", "Kohlhammer", 20, 26),
    ("C.H. Beck", "Beck", 18, 24),
    ("De Gruyter / Transcript", "Gruyter", 20, 26),
    ("De Gruyter / Transcript", "Transcript", 18, 24),
    ("Herder (Grünewald)", "Grünewald", 15, 20),
    ("Gütersloher Verlagshaus (Chr. Kaiser)", "Kaiser", 15, 20),
    ("Herder (Kreuz)", "Kreuz", 15, 20),
    ("Patmos (Schwabenverlag)", "Schwabenverlag", 13, 18),
    ("Herder (Benziger)", "Benziger", 13, 18),
    ("Schöningh", "Schöningh", 16, 21),
    ("Aschendorff", "Aschendorff", 16, 21),
    ("Pustet", "Pustet", 15, 20),
    ("Echter", "Echter", 15, 20),
    ("Bonifatius", "Bonifatius", 13, 18),
    ("Neukirchener", "Neukirchener", 15, 20),
    ("Calwer", "Calwer", 13, 18),
    ("Campus", "Campus", 14, 19),
    ("Insel", "Insel", 10, 14),
    ("Meiner", "Meiner", 14, 19),
    ("Wallstein", "Wallstein", 10, 14),
    ("Nomos / Alber", "Alber", 14, 19),
    ("Wilhelm Fink", "Fink", 11, 15),
    ("Frommann-Holzboog", "Frommann", 11, 15),
    ("Böhlau", "Böhlau", 15, 20),
    ("Schwabe", "Schwabe", 10, 14),
]

# Direct DNB Thematic Subject & DDC Queries across RQ1, RQ2, and RQ3 (1970-2025)
# (Query CQL, start_page_idx, end_page_idx, check_isbns)
DNB_THEMATIC_QUERIES = [
    ("sw=Religionskritik*", 12, 16, True),
    ("sw=Atheismus*", 12, 16, True),
    ("sw=Säkularisierung*", 12, 16, True),
    ("sw=Kirchenkritik*", 11, 15, True),
    ("sw=Kirchenaustritt* or sw=Konfessionslos*", 10, 14, True),
    ("sw=Religionssoziologie*", 12, 16, True),
    ("sw=Religionspsychologie*", 11, 15, True),
    ("sw=Religionsphilosophie*", 12, 16, True),
    ("sw=Spiritualität* and (dcs=200* or dcs=230* or dcs=240*)", 12, 16, True),
    ("sw=Achtsamkeit* and (dcs=200* or dcs=150*)", 11, 15, True),
    ("sw=Lebenshilfe* and (dcs=200* or dcs=230* or dcs=150*)", 11, 15, True),
    ("sw=Seelsorge*", 12, 16, True),
    ("sw=Dogmatik*", 12, 16, True),
    ("sw=Sozialethik* or sw=Christliche Ethik*", 11, 15, True),
    ("sw=Ökumene* or sw=Ökumenische*", 11, 15, True),
    ("sw=Gottesfrage*", 10, 14, True),
    ("sw=Mystik*", 11, 15, True),
    ("sw=Fundamentalismus* and sw=Religion*", 10, 14, True),
    ("sw=Religionspädagogik*", 11, 15, True),
    ("sw=Kirchenmitgliedschaft*", 8, 12, True),
    ("sw=Kirchenkampf*", 8, 12, True),
    ("sw=Reformation* and (dcs=200* or dcs=230* or dcs=270*)", 8, 12, True),
    ("sw=Neues Testament*", 8, 13, True),
    ("sw=Altes Testament*", 8, 13, True),
    ("sw=Bibelwissenschaft* or sw=Exegese*", 8, 13, True),
    ("sw=Liturgie* or sw=Gottesdienst*", 8, 13, True),
    ("sw=Diakonie* or sw=Caritas*", 8, 13, True),
    ("sw=Religionsunterricht*", 8, 13, True),
    ("sw=Kirchenrecht* or sw=Staatskirchenrecht*", 8, 12, True),
    ("sw=Kirchengeschichte*", 8, 13, True),
    ("sw=Moraltheologie* or sw=Theologische Ethik*", 8, 12, True),
    ("sw=Christologie* or sw=Ekklesiologie*", 8, 12, True),
    ("sw=Religionsgeschichte*", 5, 10, True),
    ("sw=Kirchenreform* or sw=Synodaler*", 5, 10, True),
    ("sw=Missbrauch* and sw=Kirche*", 4, 8, True),
    ("sw=Befreiungstheologie* or sw=Politische Theologie*", 5, 10, True),
    ("sw=Feministische Theologie*", 5, 10, True),
    ("sw=Interreligiös* or sw=Christlich-jüdisch* or sw=Christlich-islamisch*", 5, 10, True),
    ("sw=Aufklärung* and (sw=Religion* or sw=Theologie* or dcs=200*)", 5, 10, True),
    ("sw=Idealismus* and (sw=Religion* or sw=Gott* or dcs=100* or dcs=200*)", 5, 10, True),
    ("sw=Phänomenologie* and (sw=Religion* or dcs=100* or dcs=200*)", 5, 10, True),
    ("sw=Existenzphilosophie* or sw=Hermeneutik*", 5, 10, True),
    ("sw=Wertewandel* or sw=Individualisierung*", 5, 10, True),
    ("sw=Esoterik* or sw=New Age* or sw=Anthroposophie*", 5, 10, True),
    ("sw=Buddhismus* or sw=Hinduismus* or sw=Weltreligion*", 5, 10, True),
    ("sw=Judentum* and (dcs=200* or dcs=290* or dcs=900*)", 5, 10, True),
    ("sw=Islam* and (dcs=200* or dcs=290* or dcs=300*)", 5, 10, True),
    ("sw=Bibel* or sw=Evangelium* or sw=Paulus*", 5, 10, True),
    # Wave-8 Complete DNB DDC Sachgruppen (220, 240, 250, 260, 270, 280, 290, 150, 170)
    ("dcs=220*", 0, 10, True),
    ("dcs=240*", 0, 10, True),
    ("dcs=250*", 0, 10, True),
    ("dcs=260*", 0, 10, True),
    ("dcs=270*", 0, 10, True),
    ("dcs=280*", 0, 10, True),
    ("dcs=290*", 0, 10, True),
    ("dcs=150* and (sw=Lebenshilfe* or sw=Spiritualität* or sw=Achtsamkeit* or sw=Sinn* or sw=Seele* or sw=Trauer*)", 0, 8, True),
    ("dcs=170* and (sw=Ethik* or sw=Moral* or sw=Religion* or sw=Gewissen* or sw=Werte*)", 0, 8, True),
]



def normalize_german_text(text: str) -> str:
    """
    Normalizes MARC21 NFD combining diacritics (e.g., 'a' + '\\u0308') into
    canonical NFC UTF-8 characters ('ä', 'ö', 'ü', 'ß') and strips MARC21
    non-sorting control markers ('˜', 'œ') and ASCII control characters.
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


_THREAD_LOCAL = threading.local()


def _get_thread_session() -> requests.Session:
    sess = getattr(_THREAD_LOCAL, "session", None)
    if sess is None:
        sess = requests.Session()
        sess.headers.update(HEADERS)
        adapter = requests.adapters.HTTPAdapter(pool_connections=64, pool_maxsize=64, max_retries=1)
        sess.mount("https://", adapter)
        sess.mount("http://", adapter)
        _THREAD_LOCAL.session = sess
    return sess


def stream_dnb_34_pdf_or_epub_in_ram(url: str, max_pages: int = 90, max_bytes: int = 20 * 1024 * 1024):
    """
    Downloads a DNB `/34` Open-Access archive stream (`https://d-nb.info/{idn}/34`)
    entirely in RAM using thread-local keep-alive connection pooling and supports:
      1. Direct PDF (`%PDF`) via PyMuPDF (`fitz`)
      2. EPUB (`application/epub+zip`, `PK\\x03\\x04`) or ZIP-wrapped PDF/XHTML chapters
      3. Direct HTML/XML full-text deposits
    Returns (extracted_text, page_or_chapter_count).
    """
    if not url:
        return "", 0
    try:
        sess = _get_thread_session()
        with sess.get(url, timeout=(6, 14), verify=False, stream=True) as resp:
            if resp.status_code != 200:
                return "", 0
            cl = resp.headers.get("Content-Length")
            if cl and cl.isdigit() and int(cl) > max_bytes:
                return "", 0
            buf = io.BytesIO()
            read_bytes = 0
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    break
                buf.write(chunk)
                read_bytes += len(chunk)
                if read_bytes > max_bytes:
                    break
            raw = buf.getvalue()
        if not raw:
            return "", 0

        # Case 1: Direct PDF
        if raw[:4] == b"%PDF":
            with fitz.open(stream=raw, filetype="pdf") as doc:
                n_pages = min(len(doc), max_pages)
                pages_txt = [doc[i].get_text("text") for i in range(n_pages)]
            return normalize_german_text(" ".join(pages_txt)), n_pages

        # Case 2: EPUB or ZIP container (PK\x03\x04)
        if raw[:4] == b"PK\x03\x04":
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                names = zf.namelist()
                # Check if ZIP contains an embedded PDF
                pdf_names = [n for n in names if n.lower().endswith(".pdf")]
                if pdf_names:
                    pdf_bytes = zf.read(pdf_names[0])
                    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                        n_pages = min(len(doc), max_pages)
                        pages_txt = [doc[i].get_text("text") for i in range(n_pages)]
                    return normalize_german_text(" ".join(pages_txt)), n_pages

                # Otherwise parse EPUB XHTML/HTML chapters in spine/alphabetical order
                html_names = sorted(
                    [
                        n for n in names
                        if n.lower().endswith((".xhtml", ".html", ".htm", ".xml"))
                        and not os.path.basename(n).lower().startswith(("toc", "nav", "container", "content.opf"))
                    ]
                )
                chapters = []
                for hn in html_names[:max_pages]:
                    try:
                        ch_raw = zf.read(hn).decode("utf-8", errors="ignore")
                        ch_raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", ch_raw, flags=re.DOTALL | re.IGNORECASE)
                        ch_clean = re.sub(r"<[^>]+>", " ", ch_raw)
                        ch_clean = (
                            ch_clean.replace("&#xa0;", " ")
                            .replace("&nbsp;", " ")
                            .replace("&quot;", '"')
                            .replace("&amp;", "&")
                        )
                        if len(ch_clean.split()) >= 20:
                            chapters.append(ch_clean)
                    except Exception:
                        pass
                return normalize_german_text(" ".join(chapters)), len(chapters)

        # Case 3: HTML/Plain-text full text
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "html" in ctype or "text" in ctype or b"<html" in raw[:500].lower():
            html_str = raw.decode("utf-8", errors="ignore")
            html_str = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html_str, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r"<[^>]+>", " ", html_str)
            return normalize_german_text(clean), 1
    except Exception:
        pass
    return "", 0


def parse_marc_record(
    marc_data,
    canonical_publisher: str = None,
    fetch_blurbs: bool = False,
    force_onlinefree: bool = False,
) -> dict:
    """
    Extracts rich bibliographic, multi-ISBN ($a, $z, $9), Open-Access PDF/EPUB, TOC PDF/HTML,
    and discursive fields from a DNB MARC21 XML record.
    """
    idn = ""
    f001 = marc_data.find("marc:controlfield[@tag='001']", NS)
    if f001 is not None and f001.text:
        idn = f001.text.strip()

    title_main = ""
    subtitle = ""
    author = ""
    editor = ""
    date = ""
    publisher = ""
    isbn_list = []
    abstracts = []
    keywords = []
    blurb_url = ""
    toc_htm_url = ""
    toc_pdf_url = ""
    dnb_34_url = ""
    is_kostenfrei = bool(force_onlinefree)

    for field in marc_data.findall("marc:datafield", NS):
        tag = field.get("tag")

        if tag == "020":
            for code in ("a", "z", "9"):
                for sub in field.findall(f"marc:subfield[@code='{code}']", NS):
                    if sub is not None and sub.text:
                        clean_i = re.sub(r"[^0-9Xx]", "", sub.text).upper()
                        if len(clean_i) in (10, 13) and clean_i not in isbn_list:
                            isbn_list.append(clean_i)

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
                if "inhaltsverzeichnis" in s3_str:
                    if "d-nb.info" in u_str and not toc_pdf_url:
                        toc_pdf_url = u_str
                    elif "deposit.dnb.de" in u_str and not toc_htm_url:
                        toc_htm_url = u_str
                elif u_str.endswith("/04") and "d-nb.info" in u_str and not toc_pdf_url:
                    toc_pdf_url = u_str
                elif (
                    "inhaltstext" in s3_str
                    or "/blurb/" in u_str
                    or ("deposit.dnb.de/cgi-bin/dokserv" in u_str and "inhaltsverzeichnis" not in s3_str)
                ) and not blurb_url:
                    blurb_url = u_str
                elif u_str.endswith("/34") and "d-nb.info" in u_str and not dnb_34_url:
                    dnb_34_url = u_str

    if is_kostenfrei and not dnb_34_url and idn:
        dnb_34_url = f"https://d-nb.info/{idn}/34"

    # Pair sibling $z='kostenfrei' or location=onlinefree with the record's d-nb.info/{idn}/34 direct download URL
    oa_pdf_url = dnb_34_url if (is_kostenfrei and dnb_34_url) else ""

    full_title = f"{title_main}: {subtitle}" if subtitle else title_main
    creator = author if author else (editor or "o. V.")
    final_publisher = map_dnb_imprint_to_canonical(publisher, fallback=canonical_publisher)

    blurb_text = fetch_dnb_blurb(blurb_url) if (fetch_blurbs and blurb_url) else ""
    abstract_str = " ".join(abstracts)
    keyword_str = ", ".join(keywords)

    text_segments = [s for s in [full_title, abstract_str, blurb_text, keyword_str] if s]
    combined_text = ". ".join(text_segments)

    decade = f"{date[:3]}0s" if (date and len(date) == 4) else "Unknown"

    return {
        "idn": idn,
        "title": full_title,
        "author": creator,
        "date": date,
        "decade": decade,
        "publisher": final_publisher,
        "raw_publisher": publisher,
        "isbn": isbn_list[0] if isbn_list else "",
        "all_isbns": isbn_list,
        "oa_pdf_url": oa_pdf_url,
        "toc_pdf_url": toc_pdf_url,
        "toc_htm_url": toc_htm_url,
        "blurb_url": blurb_url,
        "abstract_note": abstract_str,
        "keywords": keyword_str,
        "text": combined_text,
        "is_priority_publisher": bool(canonical_publisher),
    }


def harvest_dnb(
    query: str = "dcs=200* and jhr>=1970 and jhr<=2025",
    max_records: int = 150,
    output_file: str = "data/dnb_live_harvest.csv",
    fetch_blurbs: bool = True,
):
    """
    Backwards-compatible single-query harvester used by FastAPI `/api/harvest` endpoint.
    """
    base_url = "https://services.dnb.de/sru/dnb"
    records_data = []
    start_record = 1
    batch_size = 50

    while len(records_data) < max_records:
        params = {
            "operation": "searchRetrieve",
            "version": "1.1",
            "query": query,
            "recordSchema": "MARC21-xml",
            "maximumRecords": str(min(batch_size, max_records - len(records_data))),
            "startRecord": str(start_record),
        }
        try:
            response = fetch_url_with_ssl_fallback(base_url, params=params, timeout=20)
            if response.status_code != 200:
                break
            tree = ET.fromstring(response.content)
            records = tree.findall(".//zs:record", NS)
            if not records:
                break
            for record in records:
                marc_data = record.find(".//marc:record", NS)
                if marc_data is None:
                    continue
                parsed = parse_marc_record(marc_data, fetch_blurbs=fetch_blurbs)
                if parsed["title"] and parsed["date"]:
                    records_data.append({
                        "title": parsed["title"],
                        "author": parsed["author"],
                        "date": parsed["date"],
                        "publisher": parsed["publisher"],
                        "text": parsed["text"],
                    })
            start_record += len(records)
            time.sleep(0.25)
        except Exception:
            break

    df = pd.DataFrame(records_data)
    if not df.empty and output_file:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        df.to_csv(output_file, index=False, encoding="utf-8")
    return df


def harvest_dnb_wave7_exhaustive(
    already_seen_htids: set,
    already_matched_isbns: set,
    already_seen_urls: set,
    already_seen_titles: set,
    workers: int = 36,
    chunk_words: int = 1000,
    max_chunks_per_book: int = 55,
    max_toc_pdfs: int = 50000,
    max_oa_books: int = 4000,
):
    """
    Wave-10 Complete DNB `location=onlinefree` + `hsg=` Year-by-Year (1970–2025) Full-Text Harvester:
      1. Dynamically paginates DNB SRU (`https://services.dnb.de/sru/dnb`) across:
         - Group 1: All 38 Target Publishers (`vlg=`) with `location=onlinefree and spr=ger` (1970–2025)
         - Group 2: Year-by-Year (`jhr=1970..2025`) across `hsg=200`, `hsg=220`, `hsg=230`, `hsg=290`,
           `hsg=100` (religion/ethics/philosophy), `hsg=150` (spirituality/mindfulness/psychology), and
           `hsg=300` (sociology of religion/secularization) with `location=onlinefree and spr=ger`
         - Group 3: Deep `hsg=200/220/230/290` print + online pages across all 38 Target Publishers
           for multi-ISBN (`MARC 020 $a/$z/$9`) HTRC resolution, `/04` TOC PDFs, and `Inhaltstexte`
      2. Stream A (Multi-ISBN `MARC 020 $a/$z/$9` DNB -> HathiTrust HTRC Full Books)
      3. Stream B (All Unharvested `location=onlinefree` DNB `/34` Open-Access Full-Text PDFs & EPUBs)
      4. Stream C (All Remaining Unharvested DNB Digitized `/04` `Inhaltsverzeichnis` & Excerpt PDFs + HTML TOCs)
      5. Stream D (All Remaining Unharvested DNB `deposit.dnb.de` `Inhaltstexte`, `MARC 520` Abstracts & `MARC 650` Keywords)
    """
    base_url = "https://services.dnb.de/sru/dnb"

    pub_oa_domain_cql = (
        "(hsg=200 or hsg=220 or hsg=230 or hsg=290 or hsg=100 or hsg=150 or hsg=300 or "
        "sw=Religion* or sw=Theologie* or sw=Kirche* or sw=Glaube* or sw=Gott* or sw=Christ* or "
        "sw=Bibel* or sw=Ethik* or sw=Moral* or sw=Säkular* or sw=Atheismus* or sw=Spiritualität* or "
        "sw=Achtsamkeit* or sw=Lebenshilfe* or sw=Seelsorge* or sw=Islam* or sw=Judentum* or "
        "sw=Philosophie* or sw=Gesellschaft* or sw=Kultur* or sw=Sinn*)"
    )

    # Phase 1: Seed Queries (startRecord=1) with dynamic pagination limit (max_records_per_query)
    # Tuple: (canon_pub, cql_query, start_rec, is_deep_page, force_onlinefree, max_rec_cap)
    phase1_queries = []

    # Group 1: All 38 Target Publishers with location=onlinefree (1970-2025)
    for canon_pub, vlg_term, _, _ in DNB_TARGET_PUBLISHERS:
        q_pub_oa = f'vlg="{vlg_term}" and location=onlinefree and spr=ger and {pub_oa_domain_cql} and jhr>=1970 and jhr<=2025'
        phase1_queries.append((canon_pub, q_pub_oa, 1, True, True, 1200))

    # Group 2: Year-by-Year (1970-2025) across hsg=200, 220, 230, 290, 100, 150, 300 with location=onlinefree
    hsg_oa_templates = [
        ("hsg=230", 800),
        ("hsg=200", 600),
        ("hsg=290", 500),
        ("hsg=220", 500),
        ("hsg=100 and (sw=Religion* or sw=Gott* or sw=Ethik* or sw=Moral* or sw=Aufklärung* or sw=Sinn* or sw=Philosophie*)", 400),
        ("hsg=300 and (sw=Religion* or sw=Kirche* or sw=Säkular* or sw=Islam* or sw=Judentum* or sw=Wertewandel*)", 400),
        ("hsg=150 and (sw=Spiritualität* or sw=Achtsamkeit* or sw=Lebenshilfe* or sw=Seele* or sw=Trauer* or sw=Religion*)", 300),
    ]
    for yr in range(2025, 1969, -1):
        for hsg_expr, cap in hsg_oa_templates:
            q_yr = f"({hsg_expr}) and location=onlinefree and spr=ger and jhr={yr}"
            phase1_queries.append((None, q_yr, 1, True, True, cap))

    # Group 3: hsg=200/220/230/290 across All 38 Target Publishers (print + online for multi-ISBN $z & /04 PDFs)
    for canon_pub, vlg_term, _, wave8_end_pages in DNB_TARGET_PUBLISHERS:
        q_hsg_pub = f'(hsg=200 or hsg=220 or hsg=230 or hsg=290) and vlg="{vlg_term}" and jhr>=1970 and jhr<=2025'
        phase1_queries.append((canon_pub, q_hsg_pub, 1, True, False, min(1500, wave8_end_pages * 60)))

    print(
        f"Wave-10 Complete DNB `location=onlinefree` + `hsg=` Harvester: Probing {len(phase1_queries):,} "
        f"year-by-year & publisher SRU queries (1970-2025)...",
        flush=True,
    )

    unique_records = {}
    continuation_tasks = []
    lock = threading.Lock()

    def _fetch_dnb_sru_page(task):
        canon_pub, cql_query, start_rec, is_deep_page, force_oa, max_cap = task
        parsed_list = []
        total_avail = 0
        try:
            sess = _get_thread_session()
            resp = sess.get(
                base_url,
                params={
                    "operation": "searchRetrieve",
                    "version": "1.1",
                    "query": cql_query,
                    "recordSchema": "MARC21-xml",
                    "maximumRecords": "100",
                    "startRecord": str(start_rec),
                },
                verify=False,
                timeout=20,
            )
            if resp.status_code != 200:
                return parsed_list, 0
            tree = ET.fromstring(resp.content)
            num_txt = tree.findtext(".//zs:numberOfRecords", namespaces=NS)
            if num_txt and num_txt.isdigit():
                total_avail = int(num_txt)
            for srw_rec in tree.findall(".//zs:record", NS):
                marc_data = srw_rec.find(".//marc:record", NS)
                if marc_data is None:
                    continue
                rec = parse_marc_record(
                    marc_data,
                    canonical_publisher=canon_pub,
                    fetch_blurbs=False,
                    force_onlinefree=force_oa,
                )
                if rec["title"] and rec["date"]:
                    rec["is_deep_page"] = is_deep_page
                    parsed_list.append(rec)
        except Exception:
            pass
        return parsed_list, total_avail

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_fetch_dnb_sru_page, t): t for t in phase1_queries}
        for fut in as_completed(futs):
            t = futs[fut]
            canon_pub, cql_query, start_rec, is_deep_page, force_oa, max_cap = t
            res, total_avail = fut.result()
            if res:
                with lock:
                    for r in res:
                        key = r["idn"] or f"{r['title'].lower()}_{r['date']}"
                        if key not in unique_records:
                            unique_records[key] = r
                        else:
                            if r.get("oa_pdf_url") and not unique_records[key].get("oa_pdf_url"):
                                unique_records[key]["oa_pdf_url"] = r["oa_pdf_url"]
                            if r.get("is_priority_publisher"):
                                unique_records[key]["is_priority_publisher"] = True
                                unique_records[key]["publisher"] = r["publisher"]
                            if r.get("is_deep_page"):
                                unique_records[key]["is_deep_page"] = True
            if total_avail > 100:
                upper = min(total_avail, max_cap)
                for next_start in range(101, upper + 1, 100):
                    continuation_tasks.append((canon_pub, cql_query, next_start, is_deep_page, force_oa, max_cap))

    if continuation_tasks:
        print(
            f"  -> Paginating {len(continuation_tasks):,} continuation SRU pages (`startRecord=101..N`) discovered via `<zs:numberOfRecords>`...",
            flush=True,
        )
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_fetch_dnb_sru_page, t) for t in continuation_tasks]
            for fut in as_completed(futs):
                res, _ = fut.result()
                if res:
                    with lock:
                        for r in res:
                            key = r["idn"] or f"{r['title'].lower()}_{r['date']}"
                            if key not in unique_records:
                                unique_records[key] = r
                            else:
                                if r.get("oa_pdf_url") and not unique_records[key].get("oa_pdf_url"):
                                    unique_records[key]["oa_pdf_url"] = r["oa_pdf_url"]
                                if r.get("is_priority_publisher"):
                                    unique_records[key]["is_priority_publisher"] = True
                                    unique_records[key]["publisher"] = r["publisher"]
                                if r.get("is_deep_page"):
                                    unique_records[key]["is_deep_page"] = True

    all_dnb_records = list(unique_records.values())
    deep_records = [r for r in all_dnb_records if r.get("is_deep_page")]
    print(
        f"  -> Retrieved {len(all_dnb_records):,} unique DNB MARC21 records "
        f"({sum(1 for r in all_dnb_records if r.get('oa_pdf_url')):,} with `location=onlinefree` `/34` Full-Text streams)!",
        flush=True,
    )

    # =========================================================================
    # STREAM A: Wave-10 Multi-ISBN (`MARC 020 $a/$z/$9`) DNB -> HathiTrust Full Books
    # =========================================================================
    dnb_isbn_candidates = []
    seen_isbns_local = set(already_matched_isbns)
    for r in deep_records:
        all_isbns = r.get("all_isbns") or ([r["isbn"]] if r.get("isbn") else [])
        for raw_isbn in all_isbns:
            if not raw_isbn:
                continue
            variants = isbn_variants(raw_isbn)
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
                "isbn": raw_isbn,
                "ppn": r["idn"],
                "bkl_codes": "DNB-Wave10-MultiISBN",
            })

    print(
        f"\n[Stream A] Wave-10 DNB Multi-ISBN ($a/$z/$9) -> HathiTrust Cross-Walk: Queued {len(dnb_isbn_candidates):,} unharvested DNB ISBNs...",
        flush=True,
    )
    htrc_passages = []
    htrc_summaries = []
    if dnb_isbn_candidates:
        dnb_isbn_df = pd.DataFrame(dnb_isbn_candidates)
        matched_ht_books = batch_resolve_hathitrust_volumes(
            dnb_isbn_df,
            already_seen_htids=already_seen_htids,
            batch_size=20,
            workers=workers,
        )
        if matched_ht_books:
            print(
                f"Streaming full-book page-by-page tokens from HTRC EF-API for {len(matched_ht_books)} Wave-10 DNB-matched books...",
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
                            f"  + [WAVE-10 DNB->HTRC BOOK #{len(htrc_summaries)}] ({summ['date']} | {summ['publisher'][:28]}) "
                            f"{summ['title'][:45]}... [{summ['htid']}] -> {summ['pages']} pages | "
                            f"{summ['extracted_words']:,} words ({summ['passages']} passages)",
                            flush=True,
                        )

    # =========================================================================
    # STREAM B: All Unharvested `location=onlinefree` DNB `/34` Open-Access Full-Text Books (PDF + EPUB)
    # =========================================================================
    oa_candidates = [
        r for r in all_dnb_records
        if r["oa_pdf_url"]
        and r["oa_pdf_url"] not in already_seen_urls
        and f"{r['title']} [dnb-oa-vollbuch-abschnitt 1/".lower() not in already_seen_titles
    ]
    # Prioritize target-publisher monographs first, then sort chronologically
    oa_candidates.sort(
        key=lambda x: (
            0 if x.get("is_priority_publisher") else 1,
            0 if x.get("publisher") != "DNB Monograph (DE)" else 1,
            str(x.get("date") or "2000"),
        )
    )
    selected_oa = oa_candidates[:max_oa_books]
    print(
        f"\n[Stream B] DNB `location=onlinefree` Open-Access Full-Text PDFs & EPUBs (`d-nb.info/.../34`): "
        f"Discovered {len(oa_candidates):,} unharvested OA works -> Streaming {len(selected_oa):,} works with 48 threads!",
        flush=True,
    )
    dnb_oa_passages = []
    oa_books_ok = 0

    def _stream_dnb_oa(r):
        txt, pages = stream_dnb_34_pdf_or_epub_in_ram(r["oa_pdf_url"], max_pages=90)
        if not txt or len(txt.split()) < 120:
            return []
        if not is_clean_modern_german(txt) or not is_german_passage(txt):
            return []
        words = txt.split()
        max_w = max_chunks_per_book * chunk_words
        if len(words) > max_w:
            txt = " ".join(words[:max_w])
        chunks = [ch for ch in chunk_fulltext_words(txt, chunk_words=chunk_words, min_words=120) if is_german_passage(ch)]
        if not chunks and len(words) >= 120:
            chunks = [" ".join(words[:1000])]
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

    if selected_oa:
        with ThreadPoolExecutor(max_workers=48) as ex:
            futs = {ex.submit(_stream_dnb_oa, r): r for r in selected_oa}
            for fut in as_completed(futs):
                r = futs[fut]
                res = fut.result()
                if res:
                    oa_books_ok += 1
                    dnb_oa_passages.extend(res)
                    w_sum = sum(x["word_count"] for x in res)
                    if oa_books_ok <= 30 or oa_books_ok % 50 == 0:
                        print(
                            f"  + [DNB OA BOOK/EPUB #{oa_books_ok}] ({r['date']} | {r['publisher'][:28]}) "
                            f"{r['title'][:45]}... -> {w_sum:,} words ({len(res)} passages | total OA passages: {len(dnb_oa_passages):,})",
                            flush=True,
                        )

    print(
        f"  -> Streamed {oa_books_ok:,} NEW DNB `/34` Open-Access Full-Text Books/Works ({len(dnb_oa_passages):,} passages)!",
        flush=True,
    )

    # =========================================================================
    # STREAM C: ALL Remaining Unharvested DNB Digitized `/04` `Inhaltsverzeichnis` & Reading-Sample PDFs + HTML TOCs
    # =========================================================================
    toc_candidates = [
        r for r in all_dnb_records
        if (r["toc_pdf_url"] or r["toc_htm_url"])
        and (r["toc_pdf_url"] or r["toc_htm_url"]) not in already_seen_urls
        and f"{r['title']} [dnb-inhaltsverzeichnis & leseprobe]".lower() not in already_seen_titles
    ]
    print(
        f"\n[Stream C] DNB Digitized `/04` `Inhaltsverzeichnis` & Excerpt PDFs/HTMLs: "
        f"Streaming ALL {min(len(toc_candidates), max_toc_pdfs):,} unharvested `/04` TOCs...",
        flush=True,
    )
    dnb_toc_passages = []

    def _stream_dnb_toc(r):
        txt = ""
        src_u = r["toc_pdf_url"] or r["toc_htm_url"]
        if r["toc_pdf_url"]:
            txt, _ = stream_entire_pdf_book_in_ram(r["toc_pdf_url"], max_pages=10)
        if not txt and r["toc_htm_url"]:
            txt = fetch_dnb_blurb(r["toc_htm_url"])
            src_u = r["toc_htm_url"]
        if not txt:
            return None
        clean_toc = re.sub(r"\.{3,}", " ", txt)
        clean_toc = normalize_german_text(clean_toc)
        words = clean_toc.split()
        if len(words) < 65:
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
            "source_file": src_u,
            "chunk_index": 1,
            "total_chunks": 1,
            "word_count": len(words),
            "abstract": compact_toc[:240],
            "text": full_txt,
        }

    if toc_candidates:
        with ThreadPoolExecutor(max_workers=36) as ex:
            futs = [ex.submit(_stream_dnb_toc, r) for r in toc_candidates[:max_toc_pdfs]]
            for fut in as_completed(futs):
                res = fut.result()
                if res:
                    dnb_toc_passages.append(res)
                    if len(dnb_toc_passages) % 1000 == 0:
                        print(
                            f"    ... [Stream C Progress] Extracted {len(dnb_toc_passages):,} DNB `/04` TOC PDFs so far...",
                            flush=True,
                        )

    print(
        f"  -> Extracted {len(dnb_toc_passages):,} rich DNB `/04` `Inhaltsverzeichnis` & Leseprobe documents!",
        flush=True,
    )

    # =========================================================================
    # STREAM D: All Remaining Unharvested DNB `deposit.dnb.de` & `/blurb/` Inhaltstexte, Abstracts & Keywords
    # =========================================================================
    blurb_candidates = [
        r for r in all_dnb_records
        if (r["blurb_url"] or r["abstract_note"] or len((r["keywords"] or "").split()) >= 6)
        and r["title"].lower().strip() not in already_seen_titles
        and (not r["blurb_url"] or r["blurb_url"] not in already_seen_urls)
    ]
    print(
        f"\n[Stream D] Wave-10 DNB `deposit.dnb.de` & `/blurb/` Inhaltstexte, Abstracts & Keywords: "
        f"Fetching {len(blurb_candidates):,} NEW DNB deposit & catalog texts...",
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
        if wc < 30:
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

    with ThreadPoolExecutor(max_workers=36) as ex:
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
        description="Wave-10 Complete Deutsche Nationalbibliothek (DNB) Full-Text Harvester (1970-2025)"
    )
    parser.add_argument("--workers", type=int, default=36)
    parser.add_argument("--chunk-words", type=int, default=1000)
    parser.add_argument("--max-chunks-per-book", type=int, default=55)
    parser.add_argument("--max-toc-pdfs", type=int, default=50000)
    parser.add_argument("--max-oa-books", type=int, default=4000)
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
            tl = str(t).lower().strip()
            already_seen_titles.add(tl)
            # Also record prefix up to chunk number for fast OA book deduplication
            if "[dnb-oa-vollbuch-abschnitt 1/" in tl:
                already_seen_titles.add(tl.split("/")[0] + "/")

    print(
        f"Starting Wave-10 Complete DNB `location=onlinefree` + `hsg=` Full-Text Harvest (1970-2025)\n"
        f"  (Existing Corpus: {len(dnb_prev):,} documents | {len(already_seen_htids):,} HTRC books)...",
        flush=True,
    )

    new_passages, new_ht_summaries = harvest_dnb_wave7_exhaustive(
        already_seen_htids=already_seen_htids,
        already_matched_isbns=already_matched_isbns,
        already_seen_urls=already_seen_urls,
        already_seen_titles=already_seen_titles,
        workers=args.workers,
        chunk_words=args.chunk_words,
        max_chunks_per_book=args.max_chunks_per_book,
        max_toc_pdfs=args.max_toc_pdfs,
        max_oa_books=args.max_oa_books,
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
    print(f"WAVE-10 COMPLETE DNB FULL-TEXT HARVEST FINISHED in {elapsed:.1f}s!", flush=True)
    print(f"  - Stream A (Multi-ISBN $a/$z/$9 DNB -> HTRC Full Books): {len(new_ht_summaries)} books ({sum(1 for p in new_passages if p['corpus_layer']=='hathitrust_ef_fullbook_print'):,} passages)", flush=True)
    print(f"  - Stream B (`location=onlinefree` DNB `/34` OA PDFs & EPUBs): {sum(1 for p in new_passages if p['corpus_layer']=='dnb_oa_fullbook'):,} passages", flush=True)
    print(f"  - Stream C (Remaining DNB Digitized `/04` `Inhaltsverzeichnis` & Excerpt PDFs/HTMLs): {sum(1 for p in new_passages if p['corpus_layer']=='dnb_toc_pdf_fulltext'):,} documents", flush=True)
    print(f"  - Stream D (Remaining DNB `Inhaltstexte`, Abstracts & Keywords): {sum(1 for p in new_passages if p['corpus_layer']=='dnb_deposit_inhaltstext'):,} documents", flush=True)
    print(f"  - TOTAL NEW UNIQUE DNB DOCUMENTS ADDED IN WAVE 10: {len(new_df):,} ({int(total_new_words):,} German words!)", flush=True)
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

