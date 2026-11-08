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
        ("reclam", "Reclam"),
        ("dtv", "dtv Verlagsgesellschaft"),
        ("deutscher taschenbuch", "dtv Verlagsgesellschaft"),
        ("hanser", "Carl Hanser Verlag"),
        ("piper", "Piper Verlag"),
        ("ullstein", "Ullstein Verlag"),
        ("aufbau", "Aufbau Verlag"),
        ("luchterhand", "Luchterhand"),
        ("beltz", "Beltz / Juventa"),
        ("juventa", "Beltz / Juventa"),
        ("hogrefe", "Hogrefe Verlag"),
        ("duncker", "Duncker & Humblot"),
        ("narr", "Narr Francke Attempto"),
        ("francke", "Narr Francke Attempto"),
        ("matthes", "Matthes & Seitz"),
        ("merve", "Merve Verlag"),
        ("junius", "Junius Verlag"),
        ("felix meiner", "Meiner"),
        ("klostermann", "Vittorio Klostermann"),
        ("metzler", "Springer Nature (Holtzbrinck)"),
        ("vs verlag", "Springer Nature (Holtzbrinck)"),
        ("gabler", "Springer Nature (Holtzbrinck)"),
        ("vieweg", "Springer Nature (Holtzbrinck)"),
        ("teubner", "Springer Nature (Holtzbrinck)"),
        ("palgrave", "Springer Nature (Holtzbrinck)"),
        ("oldenbourg", "De Gruyter / Transcript"),
        ("akademie verlag", "De Gruyter / Transcript"),
        ("niemeyer", "De Gruyter / Transcript"),
        ("saur", "De Gruyter / Transcript"),
        ("birkhäuser", "De Gruyter / Transcript"),
        ("peter lang", "Peter Lang"),
        ("lang,", "Peter Lang"),
        ("ergon", "Nomos / Alber"),
        ("tectum", "Nomos / Alber"),
        ("rombach", "Nomos / Alber"),
        ("utb", "UTB (Uni-Taschenbücher)"),
        ("steiner", "Franz Steiner Verlag"),
        ("harrassowitz", "Harrassowitz Verlag"),
        ("olms", "Georg Olms Verlag"),
        ("winter", "Universitätsverlag Winter"),
        ("königshausen", "Königshausen & Neumann"),
        ("passagen", "Passagen Verlag"),
        ("turia", "Turia + Kant"),
        ("diaphanes", "diaphanes"),
        ("konstanz university", "Konstanz University Press"),
        ("velbrück", "Velbrück Wissenschaft"),
        ("waxmann", "Waxmann Verlag"),
        ("budrich", "Verlag Barbara Budrich"),
        ("transcript", "De Gruyter / Transcript"),
        ("logos", "Logos Verlag Berlin"),
        ("shaker", "Shaker Verlag"),
        ("cuvillier", "Cuvillier Verlag"),
        ("utz", "Herbert Utz Verlag"),
        ("kovac", "Verlag Dr. Kovač"),
        ("grin", "GRIN Verlag"),
        ("bod", "Books on Demand (BoD)"),
        ("books on demand", "Books on Demand (BoD)"),
        ("tredition", "tredition"),
        ("epubli", "epubli"),
    ]
    for needle, canon in mapping:
        if needle in p:
            return canon
    return normalize_german_text(raw_pub) if raw_pub else "DNB Monograph (DE)"


# Complete 102 Official DNB DDC & Literary Sachgruppen (`hsg=000..990`, `B`, `K`, `S`)
ALL_DNB_SACHGRUPPEN_102 = [
    # 000 Allgemeines, Informatik, Informationswissenschaft
    "000", "004", "010", "020", "030", "050", "060", "070", "080", "090",
    # 100 Philosophie, Parapsychologie, Psychologie
    "100", "130", "150",
    # 200 Religion, Bibel, Theologie, Andere Religionen
    "200", "220", "230", "290",
    # 300 Sozialwissenschaften, Politik, Wirtschaft, Recht, Pädagogik
    "300", "310", "320", "330", "333.7", "340", "350", "355", "360", "370", "380", "390",
    # 400 Sprache, Linguistik, Einzelne Philologien
    "400", "420", "430", "439", "440", "450", "460", "470", "480", "490", "491.8",
    # 500 Naturwissenschaften und Mathematik
    "500", "510", "520", "530", "540", "550", "560", "570", "580", "590",
    # 600 Technik, Medizin, angewandte Wissenschaften, Management
    "600", "610", "620", "624", "630", "640", "650", "660", "670", "690",
    # 700 Künste, Architektur, Musik, Film, Theater, Sport
    "700", "710", "720", "730", "740", "741.5", "750", "760", "770", "780", "790", "791", "792", "793", "796",
    # 800 Literatur, Rhetorik, Literaturwissenschaft
    "800", "810", "820", "830", "839", "840", "850", "860", "870", "880", "890", "891.8",
    # 900 Geschichte und Geografie
    "900", "910", "914.3", "920", "930", "940", "943", "950", "960", "970", "980", "990",
    # DNB Literarische & Pädagogische Sondersachgruppen (Belletristik, Kinder-/Jugendliteratur, Schulbücher)
    "B", "K", "S",
]

WAVE11_HARVESTED_HSG_14 = {
    "000", "100", "150", "200", "220", "230", "290",
    "300", "400", "500", "600", "700", "800", "900",
}


def fetch_dnb_blurb(blurb_url: str) -> str:
    """
    Fetches and strips HTML from a DNB Inhaltstext (Tag 856) publisher blurb URL
    (deposit.dnb.de/cgi-bin/dokserv or services.dnb.de/plus/idn/.../blurb/)
    using thread-local keep-alive connection pooling.
    """
    if not blurb_url:
        return ""
    try:
        sess = _get_thread_session()
        resp = sess.get(blurb_url, headers=HEADERS, timeout=(4, 8), verify=False)
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
_FITZ_LOCK = threading.Lock()
try:
    fitz.TOOLS.mupdf_display_errors(False)
except Exception:
    pass


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


from urllib.parse import urljoin


def _extract_pdf_url_from_html(html_str: str, base_url: str) -> str:
    """
    Extracts direct PDF download URLs from repository landing pages (OPUS, DSpace, MyCoRe,
    EPrints, SSOAR, Zenodo, De Gruyter, Transcript, Nomos, V&R, Springer) when a DNB
    MARC 856 URN/DOI/Resolving-System link resolves to an HTML splash page.
    """
    if not html_str:
        return ""
    patterns = [
        r'<meta[^>]+name=["\'](?:citation_pdf_url|eprints\.document_url|bepress_citation_pdf_url|wkhealth_pdf_url)["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\'](?:citation_pdf_url|eprints\.document_url|bepress_citation_pdf_url|wkhealth_pdf_url)["\']',
        r'<link[^>]+type=["\']application/pdf["\'][^>]+href=["\']([^"\']+)["\']',
        r'<link[^>]+href=["\']([^"\']+)["\'][^>]+type=["\']application/pdf["\']',
        r'href=["\']([^"\']+(?:/bitstream/[^"\']+\.pdf|/files/\d+/[^"\']+\.pdf|/frontdoor/deliver/index/docId/\d+/file/[^"\']+|/download/[^"\']+\.pdf))["\']',
        r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html_str, flags=re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().replace("&amp;", "&")
            if candidate and not candidate.lower().endswith(("_toc.pdf", "inhaltsverzeichnis.pdf")):
                return urljoin(base_url, candidate)
    return ""


def stream_dnb_34_pdf_or_epub_in_ram(
    url: str,
    max_pages: int = 90,
    max_bytes: int = 90 * 1024 * 1024,
    _allow_html_redirect: bool = True,
):
    """
    Downloads a DNB `/34` Open-Access archive stream (`https://d-nb.info/{idn}/34`)
    or sibling `MARC 856 $u` repository/URN/DOI stream entirely in RAM using thread-local
    keep-alive connection pooling and thread-safe MuPDF C serialization:
      1. Direct PDF (`%PDF`) up to 90 MB via PyMuPDF (`fitz`)
      2. EPUB (`application/epub+zip`, `PK\\x03\\x04`) or ZIP-wrapped PDF/XHTML chapters
      3. Repository HTML landing pages (`citation_pdf_url` / bitstream `.pdf` extraction)
      4. Direct HTML/XML full-text deposits
    Returns (extracted_text, page_or_chapter_count).
    """
    if not url:
        return "", 0
    try:
        sess = _get_thread_session()
        with sess.get(url, timeout=(4, 11), verify=False, stream=True, allow_redirects=True) as resp:
            if resp.status_code != 200:
                return "", 0
            final_url = resp.url or url
            ctype = (resp.headers.get("Content-Type") or "").lower()
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
                    return "", 0
            raw = buf.getvalue()
        if not raw:
            return "", 0

        # Case 1: Direct PDF (thread-safe C-context serialization via _FITZ_LOCK)
        if raw[:4] == b"%PDF" or b"%PDF-" in raw[:1024]:
            pdf_start = raw.find(b"%PDF")
            pdf_bytes = raw[pdf_start:] if pdf_start > 0 else raw
            with _FITZ_LOCK:
                with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                    n_pages = min(len(doc), max_pages)
                    pages_txt = [doc[i].get_text("text") for i in range(n_pages)]
            return normalize_german_text(" ".join(pages_txt)), n_pages

        # Case 2: EPUB or ZIP container (PK\x03\x04)
        if raw[:4] == b"PK\x03\x04":
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                names = zf.namelist()
                pdf_names = [n for n in names if n.lower().endswith(".pdf")]
                if pdf_names:
                    pdf_bytes = zf.read(pdf_names[0])
                    if len(pdf_bytes) <= max_bytes:
                        with _FITZ_LOCK:
                            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                                n_pages = min(len(doc), max_pages)
                                pages_txt = [doc[i].get_text("text") for i in range(n_pages)]
                        return normalize_german_text(" ".join(pages_txt)), n_pages

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

        # Case 3: HTML landing page (extract citation_pdf_url or bitstream PDF link first) or HTML full text
        if "html" in ctype or "text" in ctype or b"<html" in raw[:1000].lower():
            html_str = raw.decode("utf-8", errors="ignore")
            if _allow_html_redirect:
                embedded_pdf_url = _extract_pdf_url_from_html(html_str, final_url)
                if embedded_pdf_url and embedded_pdf_url != url:
                    txt_pdf, pages_pdf = stream_dnb_34_pdf_or_epub_in_ram(
                        embedded_pdf_url,
                        max_pages=max_pages,
                        max_bytes=max_bytes,
                        _allow_html_redirect=False,
                    )
                    if txt_pdf and len(txt_pdf.split()) >= 90:
                        return txt_pdf, pages_pdf
            html_str = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", html_str, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r"<[^>]+>", " ", html_str)
            clean_norm = normalize_german_text(clean)
            if len(clean_norm.split()) >= 180:
                return clean_norm, 1
    except Exception:
        pass
    return "", 0


def stream_dnb_oa_multi_url_in_ram(
    candidate_urls: list[str],
    max_pages: int = 90,
    max_bytes: int = 90 * 1024 * 1024,
) -> tuple[str, int, str]:
    """
    Cascades across all candidate Open-Access URLs for a DNB work:
      1. `https://d-nb.info/{idn}/34` (DNB native Netzpublikation PDF/EPUB)
      2. Sibling `MARC 856 $u` direct repository/publisher OA URLs
      3. `MARC 024` / `856` `nbn-resolving.org/urn:nbn:de:...` and `doi.org/...` links
    Returns (extracted_text, page_count, winning_url).
    """
    seen = set()
    for u in candidate_urls or []:
        if not u or u in seen:
            continue
        seen.add(u)
        txt, pages = stream_dnb_34_pdf_or_epub_in_ram(u, max_pages=max_pages, max_bytes=max_bytes)
        if txt and len(txt.split()) >= 90:
            return txt, pages, u
    return "", 0, ""


def parse_marc_record(
    marc_data,
    canonical_publisher: str = None,
    fetch_blurbs: bool = False,
    force_onlinefree: bool = False,
) -> dict:
    """
    Extracts rich bibliographic, multi-ISBN ($a, $z, $9), URN/DOI ($024), DDC/Sachgruppe ($082/$084),
    multi-URL Open-Access PDF/EPUB (`d-nb.info/{idn}/34` + all `MARC 856 $u` repository/publisher links),
    TOC PDF/HTML, and discursive fields from a DNB MARC21 XML record.
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
    urn = ""
    doi = ""
    ddc_list = []
    abstracts = []
    keywords = []
    blurb_url = ""
    toc_htm_url = ""
    toc_pdf_url = ""
    dnb_34_url = ""
    external_oa_urls = []
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

        elif tag == "024":
            sub_a = field.find("marc:subfield[@code='a']", NS)
            sub_2 = field.find("marc:subfield[@code='2']", NS)
            val_a = sub_a.text.strip() if (sub_a is not None and sub_a.text) else ""
            val_2 = sub_2.text.strip().lower() if (sub_2 is not None and sub_2.text) else ""
            if val_a:
                if (val_2 == "urn" or val_a.lower().startswith("urn:nbn:")) and not urn:
                    urn = val_a
                elif (val_2 == "doi" or val_a.startswith("10.")) and not doi:
                    doi = val_a

        elif tag in ("082", "084"):
            for sub_a in field.findall("marc:subfield[@code='a']", NS):
                if sub_a is not None and sub_a.text:
                    c_val = sub_a.text.strip()
                    if c_val and c_val not in ddc_list:
                        ddc_list.append(c_val)

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
            sub_x = field.find("marc:subfield[@code='x']", NS)
            sub_z = field.find("marc:subfield[@code='z']", NS)
            u_str = sub_u.text.strip() if (sub_u is not None and sub_u.text) else ""
            s3_str = sub_3.text.strip().lower() if (sub_3 is not None and sub_3.text) else ""
            sx_str = sub_x.text.strip().lower() if (sub_x is not None and sub_x.text) else ""
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
                elif u_str.endswith("/34") and "d-nb.info" in u_str:
                    if not dnb_34_url:
                        dnb_34_url = u_str
                else:
                    # Sibling MARC 856 $u full-text link (URN resolving, DOI, university repository, publisher OA)
                    if u_str not in external_oa_urls and "deposit.dnb.de" not in u_str:
                        if "nbn-resolving" in u_str or "urn:nbn:" in u_str or "hdl.handle.net" in u_str:
                            external_oa_urls.insert(0, u_str)
                        else:
                            external_oa_urls.append(u_str)

    oa_candidate_urls = []
    if is_kostenfrei or dnb_34_url:
        if dnb_34_url:
            oa_candidate_urls.append(dnb_34_url)
        for ext_u in external_oa_urls:
            if ext_u not in oa_candidate_urls:
                oa_candidate_urls.append(ext_u)
        if urn:
            urn_u = f"https://nbn-resolving.org/{urn}" if not urn.startswith("http") else urn
            if urn_u not in oa_candidate_urls:
                oa_candidate_urls.append(urn_u)
        if doi:
            doi_u = f"https://doi.org/{doi}" if not doi.startswith("http") else doi
            if doi_u not in oa_candidate_urls:
                oa_candidate_urls.append(doi_u)
        if not dnb_34_url and idn:
            synth_34 = f"https://d-nb.info/{idn}/34"
            if synth_34 not in oa_candidate_urls:
                oa_candidate_urls.append(synth_34)

    oa_pdf_url = dnb_34_url or (oa_candidate_urls[0] if oa_candidate_urls else "")

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
        "urn": urn,
        "doi": doi,
        "ddc": ";".join(ddc_list),
        "oa_pdf_url": oa_pdf_url,
        "oa_candidate_urls": oa_candidate_urls,
        "toc_pdf_url": toc_pdf_url,
        "toc_htm_url": toc_htm_url,
        "blurb_url": blurb_url,
        "abstract_note": abstract_str,
        "keywords": keyword_str,
        "text": combined_text,
        "is_priority_publisher": bool(canonical_publisher),
    }


def harvest_dnb(
    query: str = "spr=ger and jhr>=1970 and jhr<=2025",
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


def _round_robin_stratify(records: list, max_items: int) -> list:
    """
    Stratifies candidate DNB records across `(hsg_bucket, decade)` in round-robin order
    (prioritizing canonical publishers within each bucket) so that all 102 DNB Sachgruppen
    (`000-990`, `B`, `K`, `S`) and all decades (`1970s-2020s`) receive balanced coverage.
    """
    from collections import defaultdict, deque

    buckets = defaultdict(list)
    for r in records:
        ddc_val = str(r.get("ddc") or r.get("query_hsg") or "GEN").split(";")[0].strip() or "GEN"
        dec_val = str(r.get("decade") or "2000s")
        buckets[(ddc_val, dec_val)].append(r)

    for k in buckets:
        buckets[k].sort(
            key=lambda x: (
                0 if x.get("is_priority_publisher") else 1,
                0 if x.get("publisher") != "DNB Monograph (DE)" else 1,
                str(x.get("date") or "2000"),
            )
        )
        buckets[k] = deque(buckets[k])

    sorted_keys = sorted(buckets.keys())
    out = []
    while len(out) < max_items and sorted_keys:
        next_keys = []
        for k in sorted_keys:
            if buckets[k]:
                out.append(buckets[k].popleft())
                if len(out) >= max_items:
                    break
            if buckets[k]:
                next_keys.append(k)
        sorted_keys = next_keys
    return out


def harvest_dnb_wave7_exhaustive(
    already_seen_htids: set,
    already_matched_isbns: set,
    already_seen_urls: set,
    already_seen_titles: set,
    already_seen_oa_urls: set = None,
    already_seen_oa_titles: set = None,
    workers: int = 48,
    chunk_words: int = 1000,
    max_chunks_per_book: int = 55,
    max_toc_pdfs: int = 6500,
    max_oa_books: int = 1800,
    max_blurbs: int = 15000,
    full_rescan: bool = False,
):
    """
    Wave-12 Unfiltered All-Sachgruppen DNB Full-Text Harvester (1970–2025):
      1. Dynamically queries all 102 official DNB DDC & Literary Sachgruppen (`000–990`, `B`, `K`, `S`):
         - Group 1 (All-Sachgruppen Open-Access Sweep): All 88 newly added DNB Sachgruppen (`004..990`, `B`, `K`, `S`;
           or all 102 when `full_rescan=True`) across 6 decade slices (`1970–1979` .. `2020–2025`) with `location=onlinefree and spr=ger`
         - Group 2 (All-Sachgruppen Print + `/04` TOC + `Inhaltstext` Catalog Sweep): All 88 newly added DNB Sachgruppen
           across 6 decade slices (`1970–2025`) with `spr=ger`
         - Group 3 (Unfiltered Pre-2004 Open-Access Sweep): Year-by-year (`1970–2003`) `location=onlinefree and spr=ger and jhr={yr}`
           with zero `hsg` restriction (capturing all pre-2004 DNB Sachgruppen `01–65` and unindexed works)
         - Group 4 (Decade-Partitioned 38 Target Publishers): `vlg="{vlg_term}" and spr=ger` partitioned across 6 decades (`1970–2025`)
      2. Stream A (Multi-ISBN `MARC 020 $a/$z/$9` DNB -> HathiTrust HTRC Full Books)
      3. Stream B (Stratified All-Sachgruppen `location=onlinefree` DNB `/34` + `MARC 856 $u` Open-Access Full-Text PDFs & EPUBs)
      4. Stream C (Stratified All-Sachgruppen DNB Digitized `/04` `Inhaltsverzeichnis` & Excerpt PDFs + HTML TOCs)
      5. Stream D (Stratified All-Sachgruppen DNB `deposit.dnb.de` `Inhaltstexte`, `MARC 520` Abstracts & `MARC 650` Keywords)
    """
    if already_seen_oa_urls is None:
        already_seen_oa_urls = already_seen_urls
    if already_seen_oa_titles is None:
        already_seen_oa_titles = already_seen_titles

    base_url = "https://services.dnb.de/sru/dnb"

    # Tuple: (canon_pub, cql_query, start_rec, is_deep_page, force_onlinefree, max_rec_cap, query_hsg)
    phase1_queries = []
    decade_slices = [
        (1970, 1979),
        (1980, 1989),
        (1990, 1999),
        (2000, 2009),
        (2010, 2019),
        (2020, 2025),
    ]

    target_sachgruppen = (
        ALL_DNB_SACHGRUPPEN_102
        if full_rescan
        else [h for h in ALL_DNB_SACHGRUPPEN_102 if h not in WAVE11_HARVESTED_HSG_14]
    )

    # Group 1: All-Sachgruppen (`004..990`, `B`, `K`, `S`) Open-Access Sweep across 6 decades (1970-2025)
    for hsg_code in target_sachgruppen:
        for d_start, d_end in decade_slices:
            q_hsg_oa = f"hsg={hsg_code} and location=onlinefree and spr=ger and jhr>={d_start} and jhr<={d_end}"
            phase1_queries.append((None, q_hsg_oa, 1, True, True, 200, hsg_code))

    # Group 2: All-Sachgruppen (`004..990`, `B`, `K`, `S`) Print + `/04` TOC + `Inhaltstext` Sweep across 6 decades (1970-2025)
    for hsg_code in target_sachgruppen:
        for d_start, d_end in decade_slices:
            q_hsg_cat = f"hsg={hsg_code} and spr=ger and jhr>={d_start} and jhr<={d_end}"
            phase1_queries.append((None, q_hsg_cat, 1, True, False, 100, hsg_code))

    # Group 3: Unfiltered Year-by-Year (1970-2025) Open-Access + Catalog Sweep (`spr=ger`, zero `hsg` restriction)
    for yr in range(2025, 1969, -1):
        q_unfiltered_oa_yr = f"location=onlinefree and spr=ger and jhr={yr}"
        phase1_queries.append((None, q_unfiltered_oa_yr, 1, True, True, 300, f"UNFILTERED_OA_{yr}"))
        q_unfiltered_cat_yr = f"spr=ger and jhr={yr}"
        phase1_queries.append((None, q_unfiltered_cat_yr, 1, True, False, 200, f"UNFILTERED_CAT_{yr}"))

    # Group 4: Decade-Partitioned 38 Target Publishers (1970-2025) so large houses are never truncated by a single 3,000 cap
    for canon_pub, vlg_term, _, _ in DNB_TARGET_PUBLISHERS:
        for d_start, d_end in decade_slices:
            q_pub_dec = f'vlg="{vlg_term}" and spr=ger and jhr>={d_start} and jhr<={d_end}'
            phase1_queries.append((canon_pub, q_pub_dec, 1, True, False, 200, f"PUB_{canon_pub}"))

    print(
        f"Wave-12 Unfiltered All-Sachgruppen (`000-990`, `B`, `K`, `S` | `spr=ger`, 1970-2025) DNB Harvester:\n"
        f"  -> Probing {len(phase1_queries):,} SRU queries across {len(target_sachgruppen)} active Sachgruppen, "
        f"34 unfiltered pre-DDC years (1970-2003), and 38 decade-sliced publishers...",
        flush=True,
    )

    unique_records = {}
    continuation_tasks = []
    lock = threading.Lock()

    def _merge_rec_into_unique(r):
        key = r["idn"] or f"{r['title'].lower()}_{r['date']}"
        if key not in unique_records:
            unique_records[key] = r
        else:
            existing = unique_records[key]
            if r.get("oa_pdf_url") and not existing.get("oa_pdf_url"):
                existing["oa_pdf_url"] = r["oa_pdf_url"]
            if r.get("oa_candidate_urls"):
                cur_urls = existing.get("oa_candidate_urls") or []
                for u in r["oa_candidate_urls"]:
                    if u not in cur_urls:
                        cur_urls.append(u)
                existing["oa_candidate_urls"] = cur_urls
                if not existing.get("oa_pdf_url") and cur_urls:
                    existing["oa_pdf_url"] = cur_urls[0]
            if r.get("is_priority_publisher"):
                existing["is_priority_publisher"] = True
                existing["publisher"] = r["publisher"]
            if r.get("is_deep_page"):
                existing["is_deep_page"] = True
            if r.get("query_hsg") and not existing.get("query_hsg"):
                existing["query_hsg"] = r["query_hsg"]

    def _fetch_dnb_sru_page(task):
        canon_pub, cql_query, start_rec, is_deep_page, force_oa, max_cap, query_hsg = task
        parsed_list = []
        total_avail = 0
        for attempt in range(3):
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
                    timeout=22,
                )
                if resp.status_code != 200:
                    time.sleep(0.5 * (attempt + 1))
                    continue
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
                        rec["query_hsg"] = query_hsg
                        if not rec.get("ddc") and query_hsg and not str(query_hsg).startswith(("UNFILTERED", "PUB_")):
                            rec["ddc"] = str(query_hsg)
                        parsed_list.append(rec)
                break
            except Exception:
                time.sleep(0.5 * (attempt + 1))
        return parsed_list, total_avail

    sru_workers = min(24, workers)
    done_p1 = 0
    with ThreadPoolExecutor(max_workers=sru_workers) as ex:
        futs = {ex.submit(_fetch_dnb_sru_page, t): t for t in phase1_queries}
        for fut in as_completed(futs):
            done_p1 += 1
            t = futs[fut]
            canon_pub, cql_query, start_rec, is_deep_page, force_oa, max_cap, query_hsg = t
            res, total_avail = fut.result()
            if res:
                with lock:
                    for r in res:
                        _merge_rec_into_unique(r)
            if total_avail > 100 and max_cap > 100:
                upper = min(total_avail, max_cap)
                for next_start in range(101, upper + 1, 100):
                    continuation_tasks.append((canon_pub, cql_query, next_start, is_deep_page, force_oa, max_cap, query_hsg))
            if done_p1 % 250 == 0:
                print(
                    f"    ... [Phase 1 SRU Progress] {done_p1:,}/{len(phase1_queries):,} queries | "
                    f"{len(unique_records):,} unique DNB records discovered...",
                    flush=True,
                )

    if continuation_tasks:
        print(
            f"  -> Paginating {len(continuation_tasks):,} continuation SRU pages (`startRecord=101..N`) discovered via `<zs:numberOfRecords>`...",
            flush=True,
        )
        with ThreadPoolExecutor(max_workers=sru_workers) as ex:
            futs = [ex.submit(_fetch_dnb_sru_page, t) for t in continuation_tasks]
            for fut in as_completed(futs):
                res, _ = fut.result()
                if res:
                    with lock:
                        for r in res:
                            _merge_rec_into_unique(r)

    all_dnb_records = list(unique_records.values())
    deep_records = [r for r in all_dnb_records if r.get("is_deep_page")]
    print(
        f"  -> Retrieved {len(all_dnb_records):,} unique DNB MARC21 records across all Sachgruppen "
        f"({sum(1 for r in all_dnb_records if r.get('oa_candidate_urls')):,} with `location=onlinefree` `/34` & `MARC 856` Full-Text streams)!",
        flush=True,
    )

    # =========================================================================
    # STREAM A: Wave-12 Multi-ISBN (`MARC 020 $a/$z/$9`) DNB -> HathiTrust Full Books
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
                "bkl_codes": f"DNB-Wave12-{r.get('query_hsg') or 'AllHSG'}",
            })

    # Cap HTRC ISBN resolution batch to top 8,000 priority ISBNs so Stream A finishes in ~45 seconds
    dnb_isbn_candidates = dnb_isbn_candidates[:8000]
    print(
        f"\n[Stream A] Wave-12 DNB Multi-ISBN ($a/$z/$9) -> HathiTrust Cross-Walk: Queued {len(dnb_isbn_candidates):,} unharvested DNB ISBNs...",
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
                f"Streaming full-book page-by-page tokens from HTRC EF-API for {len(matched_ht_books)} Wave-12 DNB-matched books...",
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
                            f"  + [WAVE-12 DNB->HTRC BOOK #{len(htrc_summaries)}] ({summ['date']} | {summ['publisher'][:28]}) "
                            f"{summ['title'][:45]}... [{summ['htid']}] -> {summ['pages']} pages | "
                            f"{summ['extracted_words']:,} words ({summ['passages']} passages)",
                            flush=True,
                        )

    # =========================================================================
    # STREAM B: Stratified All-Sachgruppen `location=onlinefree` DNB `/34` + `MARC 856 $u` Open-Access Full-Text Books
    # =========================================================================
    ckpt_jsonl = "data/primary_texts/dnb_wave12_oa_checkpoint.jsonl"
    os.makedirs(os.path.dirname(ckpt_jsonl), exist_ok=True)
    dnb_oa_passages = []
    oa_books_ok = 0
    if os.path.exists(ckpt_jsonl):
        with open(ckpt_jsonl, "r", encoding="utf-8") as cf:
            for line in cf:
                line = line.strip()
                if not line:
                    continue
                try:
                    row_obj = json.loads(line)
                    dnb_oa_passages.append(row_obj)
                    if row_obj.get("source_file"):
                        already_seen_oa_urls.add(str(row_obj["source_file"]).strip())
                    tl = str(row_obj.get("title") or "").lower().strip()
                    if "[dnb-oa-vollbuch-abschnitt 1/" in tl:
                        already_seen_oa_titles.add(tl.split("/")[0] + "/")
                        oa_books_ok += 1
                except Exception:
                    pass
        if dnb_oa_passages:
            print(
                f"  -> Resumed {oa_books_ok:,} checkpointed Wave-12 DNB OA books ({len(dnb_oa_passages):,} passages) from `{ckpt_jsonl}`!",
                flush=True,
            )

    oa_candidates = [
        r for r in all_dnb_records
        if r.get("oa_candidate_urls")
        and not any(u in already_seen_oa_urls for u in r["oa_candidate_urls"])
        and f"{r['title']} [dnb-oa-vollbuch-abschnitt 1/".lower() not in already_seen_oa_titles
    ]
    selected_oa = _round_robin_stratify(oa_candidates, max_oa_books)
    print(
        f"\n[Stream B] Stratified All-Sachgruppen DNB `location=onlinefree` Open-Access Full-Text PDFs & EPUBs (`/34` + `MARC 856 $u`): "
        f"Discovered {len(oa_candidates):,} unharvested OA works -> Streaming {len(selected_oa):,} stratified works across all Sachgruppen with 48 threads!",
        flush=True,
    )
    oa_done_count = 0

    def _stream_dnb_oa(r):
        cand_urls = (r.get("oa_candidate_urls") or [r["oa_pdf_url"]])[:3]
        txt, pages, winning_url = stream_dnb_oa_multi_url_in_ram(cand_urls, max_pages=90)
        if not txt or len(txt.split()) < 90:
            return []
        if not is_clean_modern_german(txt):
            return []
        words = txt.split()
        max_w = max_chunks_per_book * chunk_words
        if len(words) > max_w:
            txt = " ".join(words[:max_w])
        # Filter chunk-by-chunk so a front-matter English abstract never rejects a 300-page German dissertation
        chunks = [
            ch for ch in chunk_fulltext_words(txt, chunk_words=chunk_words, min_words=90)
            if is_german_passage(ch, min_words=20)
        ]
        if not chunks and len(words) >= 90 and is_german_passage(txt[-6000:], min_words=20):
            chunks = [" ".join(words[:1000])]
        if not chunks:
            return []
        src_u = winning_url or r["oa_pdf_url"]
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
                "source_file": src_u,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "word_count": len(ch.split()),
                "abstract": compact_ch[:240],
                "text": f"{r['title']}. {r['author']}. {r['publisher']}. {compact_ch}",
            })
        return out

    if selected_oa:
        with open(ckpt_jsonl, "a", encoding="utf-8") as ckpt_out:
            with ThreadPoolExecutor(max_workers=48) as ex:
                futs = {ex.submit(_stream_dnb_oa, r): r for r in selected_oa}
                for fut in as_completed(futs):
                    oa_done_count += 1
                    r = futs[fut]
                    res = fut.result()
                    if res:
                        oa_books_ok += 1
                        dnb_oa_passages.extend(res)
                        for row_obj in res:
                            ckpt_out.write(json.dumps(row_obj, ensure_ascii=False) + "\n")
                        if oa_books_ok % 25 == 0:
                            ckpt_out.flush()
                        w_sum = sum(x["word_count"] for x in res)
                        if oa_books_ok <= 25 or oa_books_ok % 75 == 0:
                            print(
                                f"  + [DNB OA BOOK #{oa_books_ok:,} | scanned {oa_done_count:,}/{len(selected_oa):,} | HSG={r.get('query_hsg')}] "
                                f"({r['date']} | {r['publisher'][:26]}) {r['title'][:42]}... -> "
                                f"{w_sum:,} words ({len(res)} passages | total OA passages: {len(dnb_oa_passages):,})",
                                flush=True,
                            )

    print(
        f"  -> Streamed {oa_books_ok:,} NEW DNB Open-Access Full-Text Books/Works ({len(dnb_oa_passages):,} passages)!",
        flush=True,
    )

    # =========================================================================
    # STREAM C: Stratified All-Sachgruppen DNB Digitized `/04` `Inhaltsverzeichnis` & Reading-Sample PDFs + HTML TOCs
    # =========================================================================
    toc_candidates = [
        r for r in all_dnb_records
        if (r["toc_pdf_url"] or r["toc_htm_url"])
        and (r["toc_pdf_url"] or r["toc_htm_url"]) not in already_seen_urls
        and f"{r['title']} [dnb-inhaltsverzeichnis & leseprobe]".lower() not in already_seen_titles
    ]
    selected_tocs = _round_robin_stratify(toc_candidates, max_toc_pdfs)
    print(
        f"\n[Stream C] Stratified All-Sachgruppen DNB Digitized `/04` `Inhaltsverzeichnis` & Excerpt PDFs/HTMLs: "
        f"Discovered {len(toc_candidates):,} unharvested `/04` TOCs -> Streaming {len(selected_tocs):,} stratified `/04` TOCs...",
        flush=True,
    )
    dnb_toc_passages = []

    def _stream_dnb_toc(r):
        txt = ""
        src_u = r["toc_pdf_url"] or r["toc_htm_url"]
        if r["toc_pdf_url"]:
            txt, _ = stream_dnb_34_pdf_or_epub_in_ram(
                r["toc_pdf_url"],
                max_pages=10,
                max_bytes=15 * 1024 * 1024,
                _allow_html_redirect=False,
            )
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

    if selected_tocs:
        with ThreadPoolExecutor(max_workers=48) as ex:
            futs = [ex.submit(_stream_dnb_toc, r) for r in selected_tocs]
            for fut in as_completed(futs):
                res = fut.result()
                if res:
                    dnb_toc_passages.append(res)
                    if len(dnb_toc_passages) % 500 == 0:
                        print(
                            f"    ... [Stream C Progress] Extracted {len(dnb_toc_passages):,} DNB `/04` TOC PDFs so far...",
                            flush=True,
                        )

    print(
        f"  -> Extracted {len(dnb_toc_passages):,} rich DNB `/04` `Inhaltsverzeichnis` & Leseprobe documents!",
        flush=True,
    )

    # =========================================================================
    # STREAM D: All-Sachgruppen DNB `deposit.dnb.de` & `/blurb/` Inhaltstexte + 100% Uncapped MARC21 Catalog Incorporation
    # =========================================================================
    blurb_url_candidates = [
        r for r in all_dnb_records
        if r.get("blurb_url")
        and r["title"].lower().strip() not in already_seen_titles
        and r["blurb_url"] not in already_seen_urls
    ]
    selected_blurbs = _round_robin_stratify(blurb_url_candidates, max_blurbs)
    print(
        f"\n[Stream D1] All-Sachgruppen DNB `deposit.dnb.de` & `/blurb/` Remote Inhaltstexte: "
        f"Discovered {len(blurb_url_candidates):,} remote blurb URLs -> Fetching {len(selected_blurbs):,} stratified blurbs with 64 threads...",
        flush=True,
    )

    dnb_deposit_passages = []
    captured_titles_d1 = set()

    def _enrich_dnb_deposit(r):
        blurb_txt = fetch_dnb_blurb(r["blurb_url"]) if r.get("blurb_url") else ""
        abs_txt = r.get("abstract_note") or ""
        kw_txt = r.get("keywords") or ""
        ddc_txt = f"DDC Sachgruppe {r.get('ddc') or r.get('query_hsg') or ''}"
        body_parts = [p for p in [blurb_txt, abs_txt, kw_txt, ddc_txt] if p and p.strip()]
        body_str = " ".join(body_parts).strip()
        full_txt = f"{r['title']}. {r['author']}. {r['publisher']}. {body_str}".strip()
        wc = len(full_txt.split())
        if wc < 12:
            return None
        src_url = r.get("blurb_url") or (f"https://d-nb.info/{r['idn']}" if r.get("idn") else "https://portal.dnb.de")
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
            "abstract": (blurb_txt or abs_txt or kw_txt or r["title"])[:240],
            "text": full_txt,
        }

    with ThreadPoolExecutor(max_workers=64) as ex:
        futs = [ex.submit(_enrich_dnb_deposit, r) for r in selected_blurbs]
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                dnb_deposit_passages.append(res)
                captured_titles_d1.add(res["title"].lower().strip())

    # Stage D2: Incorporate 100% of ALL remaining unharvested DNB records in `all_dnb_records` (zero cap)
    d2_count = 0
    for r in all_dnb_records:
        tl = r["title"].lower().strip()
        if (
            tl in already_seen_titles
            or tl in captured_titles_d1
            or f"{tl} [dnb-inhaltsverzeichnis & leseprobe]" in already_seen_titles
            or f"{tl} [dnb-oa-vollbuch-abschnitt 1/" in already_seen_oa_titles
        ):
            continue
        abs_txt = r.get("abstract_note") or ""
        kw_txt = r.get("keywords") or ""
        ddc_val = r.get("ddc") or r.get("query_hsg") or "000"
        body_parts = [p for p in [abs_txt, kw_txt, f"DNB Sachgruppe {ddc_val}"] if p and p.strip()]
        body_str = " ".join(body_parts).strip()
        full_txt = f"{r['title']}. {r['author']}. {r['publisher']}. {body_str}".strip()
        wc = len(full_txt.split())
        if wc < 8:
            continue
        src_url = (
            r.get("oa_pdf_url")
            or r.get("toc_pdf_url")
            or r.get("blurb_url")
            or (f"https://d-nb.info/{r['idn']}" if r.get("idn") else "https://portal.dnb.de")
        )
        if src_url in already_seen_urls:
            continue
        dnb_deposit_passages.append({
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
            "abstract": (abs_txt or kw_txt or r["title"])[:240],
            "text": full_txt,
        })
        captured_titles_d1.add(tl)
        d2_count += 1

    print(
        f"  -> Extracted {len(dnb_deposit_passages):,} NEW DNB `Inhaltstext`, abstract & complete MARC21 works "
        f"(including {d2_count:,} uncapped Stage-D2 works across all 102 Sachgruppen & 1970-2025 years)!",
        flush=True,
    )

    all_new_passages = htrc_passages + dnb_oa_passages + dnb_toc_passages + dnb_deposit_passages
    return all_new_passages, htrc_summaries


def build_exhaustive_dnb_master_manifest(
    merged_df: pd.DataFrame,
    manifest_csv_path: str = "data/primary_texts/DNB_FULLTEXT_MASTER_MANIFEST.csv",
    fullbooks_csv_path: str = "data/primary_texts/DNB_OPEN_ACCESS_FULLBOOKS_INVENTORY.csv",
    summary_json_path: str = "app/dnb_master_manifest_summary.json",
):
    """
    Compiles and exports the comprehensive, exhaustive work-level master catalog manifest
    (`data/primary_texts/DNB_FULLTEXT_MASTER_MANIFEST.csv`) and complete full-text book inventory
    (`data/primary_texts/DNB_OPEN_ACCESS_FULLBOOKS_INVENTORY.csv`) across the 1970–2025 master dataset.
    """
    print("\nBuilding Exhaustive Work-Level Master Manifest (`DNB_FULLTEXT_MASTER_MANIFEST.csv`)...", flush=True)
    df = merged_df.copy()
    df["clean_title"] = (
        df["title"]
        .fillna("")
        .astype(str)
        .str.replace(
            r"\s*\[[^\[\]]*(?:Abschnitt|Inhaltsverzeichnis|Leseprobe|Kapitel|Teil|Chunk)[^\[\]]*\]\s*$",
            "",
            regex=True,
            flags=re.IGNORECASE,
        )
        .str.strip()
    )
    df["work_key"] = df["clean_title"].str.lower() + "||" + df["date"].fillna("").astype(str).str[:4]
    df["wc_num"] = pd.to_numeric(df["word_count"], errors="coerce").fillna(250).astype(int)

    tier_priority = {
        "dnb_oa_fullbook": (1, "Tier 1A: DNB Open-Access Full-Text Monograph/Dissertation (/34 & MARC 856)"),
        "hathitrust_ef_fullbook_print": (2, "Tier 1B: DNB/GBV Multi-ISBN Matched HathiTrust Full-Book Stream"),
        "gbv_kostenfrei_fullbook_pdf": (3, "Tier 1C: Direct Publisher / Repository Open-Access Full-Text Monograph"),
        "direct_publisher_oa_pdf": (3, "Tier 1C: Direct Publisher / Repository Open-Access Full-Text Monograph"),
        "openalex_oa_fulltext_pdf": (3, "Tier 1C: Direct Publisher / Repository Open-Access Full-Text Monograph"),
        "open_access_monograph_stream": (3, "Tier 1C: Direct Publisher / Repository Open-Access Full-Text Monograph"),
        "calibrated_fullbook_stream": (3, "Tier 1C: Direct Publisher / Repository Open-Access Full-Text Monograph"),
        "entire_fulltext_book_cloud": (3, "Tier 1C: Direct Publisher / Repository Open-Access Full-Text Monograph"),
        "archive_org_fulltext_book": (3, "Tier 1C: Direct Publisher / Repository Open-Access Full-Text Monograph"),
        "primary_cloud_oa_fulltext": (3, "Tier 1C: Direct Publisher / Repository Open-Access Full-Text Monograph"),
        "primary_fulltext": (3, "Tier 1C: Direct Publisher / Repository Open-Access Full-Text Monograph"),
        "dnb_toc_pdf_fulltext": (4, "Tier 2: DNB Digitized /04 Inhaltsverzeichnis & Reading-Sample PDF"),
        "gbv_direct_fulltext_pdf": (4, "Tier 2: DNB/GBV Digitized /04 Inhaltsverzeichnis & Reading-Sample PDF"),
        "dnb_deposit_inhaltstext": (5, "Tier 3: DNB Deposit.dnb.de Inhaltstext, MARC 520 Abstract & Indexing"),
    }

    def _map_priority(layer_str):
        return tier_priority.get(str(layer_str), (6, f"Tier 3B: Extended Paratext & Abstract ({layer_str})"))[0]

    df["tier_rank"] = df["corpus_layer"].map(_map_priority)
    df_sorted = df.sort_values("tier_rank", ascending=True)

    grouped = df_sorted.groupby("work_key", sort=False)
    first_rows = grouped.first().reset_index()
    agg_stats = (
        df.groupby("work_key", sort=False)
        .agg(
            passages_in_corpus=("wc_num", "count"),
            total_words_in_corpus=("wc_num", "sum"),
            all_layers_present=("corpus_layer", lambda s: "|".join(sorted(set(str(x) for x in s if pd.notna(x))))),
        )
        .reset_index()
    )

    manifest = pd.merge(
        first_rows[["work_key", "clean_title", "author", "date", "decade", "publisher", "corpus_layer", "source_file", "tier_rank"]],
        agg_stats,
        on="work_key",
        how="left",
    )

    def _extract_idn(src):
        s = str(src or "")
        m = re.search(r"d-nb\.info/(\d+[0-9Xx]?)", s)
        if m:
            return m.group(1)
        m2 = re.search(r"id=(\d+[0-9Xx]?)", s)
        if m2:
            return m2.group(1)
        return ""

    manifest["dnb_idn"] = manifest["source_file"].map(_extract_idn)
    manifest["highest_fulltext_tier"] = manifest["corpus_layer"].map(
        lambda x: tier_priority.get(str(x), (6, f"Tier 3B: Extended Paratext & Abstract ({x})"))[1]
    )
    manifest = manifest.rename(
        columns={
            "clean_title": "title",
            "corpus_layer": "primary_corpus_layer",
            "source_file": "primary_source_url",
        }
    )
    cols = [
        "dnb_idn",
        "title",
        "author",
        "date",
        "decade",
        "publisher",
        "highest_fulltext_tier",
        "primary_corpus_layer",
        "all_layers_present",
        "primary_source_url",
        "passages_in_corpus",
        "total_words_in_corpus",
    ]
    manifest = manifest.sort_values(["tier_rank", "date", "publisher", "title"], ascending=[True, True, True, True])[cols]

    os.makedirs(os.path.dirname(manifest_csv_path), exist_ok=True)
    manifest.to_csv(manifest_csv_path, index=False, encoding="utf-8")

    fullbooks_df = manifest[
        manifest["primary_corpus_layer"].isin(
            {
                "dnb_oa_fullbook",
                "hathitrust_ef_fullbook_print",
                "gbv_kostenfrei_fullbook_pdf",
                "direct_publisher_oa_pdf",
                "openalex_oa_fulltext_pdf",
                "open_access_monograph_stream",
                "calibrated_fullbook_stream",
                "entire_fulltext_book_cloud",
                "archive_org_fulltext_book",
                "primary_cloud_oa_fulltext",
                "primary_fulltext",
            }
        )
    ].copy()
    fullbooks_df.to_csv(fullbooks_csv_path, index=False, encoding="utf-8")

    summary = {
        "total_unique_works_1970_2025": int(len(manifest)),
        "total_complete_fulltext_books": int(len(fullbooks_df)),
        "total_dnb_oa_fulltext_books": int((manifest["primary_corpus_layer"] == "dnb_oa_fullbook").sum()),
        "total_hathitrust_fulltext_books": int((manifest["primary_corpus_layer"] == "hathitrust_ef_fullbook_print").sum()),
        "total_passages_in_corpus": int(manifest["passages_in_corpus"].sum()),
        "total_words_in_corpus": int(manifest["total_words_in_corpus"].sum()),
        "works_by_highest_tier": {
            str(k): int(v) for k, v in manifest["highest_fulltext_tier"].value_counts().items()
        },
        "works_by_primary_layer": {
            str(k): int(v) for k, v in manifest["primary_corpus_layer"].value_counts().items()
        },
        "fulltext_books_by_decade": {
            str(k): int(v) for k, v in fullbooks_df["decade"].value_counts().sort_index().items()
        },
    }
    os.makedirs(os.path.dirname(summary_json_path), exist_ok=True)
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(
        f"  -> Exported `{manifest_csv_path}` ({len(manifest):,} unique works) and "
        f"`{fullbooks_csv_path}` ({len(fullbooks_df):,} complete full-text books | "
        f"{summary['total_dnb_oa_fulltext_books']:,} DNB OA full books + "
        f"{summary['total_hathitrust_fulltext_books']:,} HTRC full books)!",
        flush=True,
    )
    return summary


def append_rows_to_zstd_parquet(
    rows: list[dict],
    parquet_dir: str = "data/parquet",
    compression_level: int = 19,
) -> str:
    """
    Writes a streaming batch of DNB corpus rows to a new Zstd-19 Apache Parquet shard
    in `parquet_dir` (`dnb_corpus_partNNN.parquet`) and updates `parquet_manifest.json`.
    """
    import glob
    import pyarrow as pa
    import pyarrow.parquet as pq

    if not rows:
        return ""
    os.makedirs(parquet_dir, exist_ok=True)
    existing = sorted(
        glob.glob(os.path.join(parquet_dir, "dnb_corpus_part*.parquet")),
        key=lambda x: int(re.search(r"part(\d+)", x).group(1)) if re.search(r"part(\d+)", x) else 0,
    )
    max_idx = 0
    last_path = ""
    for p in existing:
        m = re.search(r"part(\d+)", os.path.basename(p))
        if m:
            idx_num = int(m.group(1))
            if idx_num >= max_idx:
                max_idx = idx_num
                last_path = p

    # If the trailing continuation shard (>= 126) has < 75,000 rows, merge into it instead of creating tiny shards
    if max_idx >= 126 and last_path and os.path.exists(last_path):
        try:
            old_tbl = pq.read_table(last_path, memory_map=False)
            if old_tbl.num_rows + len(rows) <= 95000:
                old_rows = old_tbl.to_pylist()
                del old_tbl
                rows = old_rows + list(rows)
                next_idx = max_idx
            else:
                del old_tbl
                next_idx = max_idx + 1
        except Exception:
            next_idx = max_idx + 1
    else:
        next_idx = max_idx + 1

    shard_name = f"dnb_corpus_part{next_idx:03d}.parquet"
    shard_path = os.path.join(parquet_dir, shard_name)

    rows_sorted = sorted(
        rows,
        key=lambda r: (
            str(r.get("corpus_layer") or ""),
            str(r.get("publisher") or ""),
            str(r.get("author") or ""),
        ),
    )

    schema_fields = [
        ("title", pa.string()),
        ("author", pa.string()),
        ("date", pa.string()),
        ("decade", pa.string()),
        ("publisher", pa.string()),
        ("corpus_layer", pa.string()),
        ("source_file", pa.string()),
        ("chunk_index", pa.int32()),
        ("total_chunks", pa.int32()),
        ("word_count", pa.int32()),
        ("abstract", pa.string()),
        ("text", pa.string()),
    ]
    pa_schema = pa.schema(schema_fields)
    arrays = {}
    for col_name, col_type in schema_fields:
        if pa.types.is_integer(col_type):
            vals = []
            for r in rows_sorted:
                try:
                    vals.append(int(float(r.get(col_name) or 1)))
                except Exception:
                    vals.append(1)
            arrays[col_name] = pa.array(vals, type=col_type)
        else:
            arrays[col_name] = pa.array([str(r.get(col_name) or "") for r in rows_sorted], type=col_type)

    table = pa.Table.from_pydict(arrays, schema=pa_schema)
    tmp_path = shard_path + ".tmp"
    pq.write_table(
        table,
        tmp_path,
        compression="zstd",
        compression_level=compression_level,
        use_dictionary=["author", "date", "decade", "publisher", "corpus_layer", "source_file"],
        write_statistics=True,
    )
    import gc
    gc.collect()
    for _att in range(5):
        try:
            os.replace(tmp_path, shard_path)
            break
        except PermissionError:
            gc.collect()
            time.sleep(0.25)
    sz_mb = os.path.getsize(shard_path) / (1024 * 1024)
    print(f"  -> [Zstd-{compression_level} Parquet Stream] Wrote `{shard_path}` ({len(rows_sorted):,} rows | {sz_mb:.2f} MB)", flush=True)

    # Update parquet_manifest.json incrementally so live readers see the new shard immediately
    manifest_path = os.path.join(parquet_dir, "parquet_manifest.json")
    try:
        mdata = {}
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as mf:
                mdata = json.load(mf)
        shards_list = [s for s in mdata.get("shards", []) if (s.get("shard") or s.get("file")) != shard_name]
        shards_list.append({
            "shard": shard_name,
            "file": shard_name,
            "rows": len(rows_sorted),
            "bytes": os.path.getsize(shard_path),
            "size_bytes": os.path.getsize(shard_path),
            "size_mb": round(sz_mb, 2),
        })
        total_r = sum(int(s.get("rows", 0)) for s in shards_list)
        total_b = sum(int(s.get("bytes", 0)) for s in shards_list)
        mdata["format"] = "Apache Parquet (Zstandard level 19)"
        mdata["total_rows"] = total_r
        mdata["total_shards"] = len(shards_list)
        mdata["parquet_total_mb"] = round(total_b / (1024 * 1024), 2)
        mdata["shards"] = shards_list
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(mdata, mf, indent=2, ensure_ascii=False)
    except Exception:
        pass

    return shard_path


DNB_OPENDATA_ALL_URLS = [
    "https://data.dnb.de/DNB/dnb_all_dnbmarc.1.mrc.xml.gz",
    "https://data.dnb.de/DNB/dnb_all_dnbmarc.2.mrc.xml.gz",
    "https://data.dnb.de/DNB/dnb_all_dnbmarc.3.mrc.xml.gz",
    "https://data.dnb.de/DNB/dnb_all_dnbmarc.4.mrc.xml.gz",
    "https://data.dnb.de/DNB/dnb_all_dnbmarc.5.mrc.xml.gz",
]


def stream_dnb_opendata_marc_dump(
    dump_path_or_url: str,
    parquet_dir: str = "data/parquet",
    batch_size: int = 85000,
    fetch_remote_blurbs: bool = False,
    upload_incremental: bool = True,
    release_tag: str = "v12.0-dnb-parquet-shards",
    skip_records: int = 0,
) -> int:
    """
    Streams official DNB Open-Data MARC21-XML bulk dumps (`.mrc.xml.gz` from `https://data.dnb.de/DNB/`)
    in constant `<500 MB` RAM using `gzip` + `ET.iterparse`, filtering to German-language (`spr=ger`)
    records published 1970–2025 across all 102 DNB Sachgruppen without any SRU pagination ceiling,
    and writing Zstd-19 Parquet shards (`data/parquet/`).
    Pass `dump_path_or_url="all"` to stream all 5 official DNB OpenData packages (`40.1M` total records).
    """
    import glob
    import gzip
    import pyarrow.parquet as pq

    if dump_path_or_url.strip().lower() == "all":
        urls_to_stream = DNB_OPENDATA_ALL_URLS
    else:
        urls_to_stream = [u.strip() for u in dump_path_or_url.split(",") if u.strip()]

    # Pre-load existing IDNs and titles from current Parquet shards using C++ columnar projection
    seen_idns = set()
    seen_titles = set()
    existing_total_rows = 0
    print(f"[DNB OpenData Bulk Streamer] Indexing existing corpus in `{parquet_dir}` for fast deduplication...", flush=True)
    for p in sorted(glob.glob(os.path.join(parquet_dir, "dnb_corpus_part*.parquet"))):
        tbl = pq.read_table(p, columns=["source_file", "title"])
        existing_total_rows += tbl.num_rows
        for sf in tbl.column("source_file").to_pylist():
            if sf and "d-nb.info/" in sf:
                idn_part = sf.split("d-nb.info/")[-1].split("/")[0].strip()
                if idn_part:
                    seen_idns.add(idn_part)
        for t in tbl.column("title").to_pylist():
            if t:
                seen_titles.add(t.lower().strip())
    print(f"  -> Indexed {existing_total_rows:,} existing rows ({len(seen_idns):,} DNB IDNs | {len(seen_titles):,} unique titles).", flush=True)

    batch_rows = []
    created_shards = []
    total_scanned = 0
    total_ingested = 0

    for pkg_idx, target_url in enumerate(urls_to_stream, 1):
        print(
            f"\n[DNB OpenData Package {pkg_idx}/{len(urls_to_stream)}] Streaming `{target_url}` -> `{parquet_dir}` (batch_size={batch_size:,}, skip_records={skip_records:,})...",
            flush=True,
        )
        try:
            if target_url.startswith(("http://", "https://")):
                resp = None
                for attempt in range(4):
                    try:
                        resp = requests.get(target_url, headers=HEADERS, stream=True, timeout=(60, 600), verify=False)
                        resp.raise_for_status()
                        break
                    except Exception as conn_err:
                        if attempt == 3:
                            raise conn_err
                        print(f"  [!] Retry {attempt+1}/3 connecting to `{target_url}`...", flush=True)
                        time.sleep(5 * (attempt + 1))
                raw_stream = resp.raw
                xml_stream = gzip.GzipFile(fileobj=raw_stream) if target_url.endswith(".gz") else raw_stream
            else:
                xml_stream = (
                    gzip.open(target_url, "rb")
                    if target_url.endswith(".gz")
                    else open(target_url, "rb")
                )

            context = iter(ET.iterparse(xml_stream, events=("start", "end")))
            _, root = next(context)
            for event, elem in context:
                if event != "end":
                    continue
                tag_local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if tag_local != "record":
                    continue
                total_scanned += 1
                if skip_records and total_scanned <= skip_records:
                    if total_scanned % 250000 == 0:
                        print(f"  ... [Fast-Forwarding Pkg {pkg_idx}] Skipped {total_scanned:,}/{skip_records:,} already-scanned records...", flush=True)
                    elem.clear()
                    root.clear()
                    continue
                try:
                    # Fast check on 001 (IDN), 008 (Year & Language), and 041 (Language)
                    f001 = elem.find("marc:controlfield[@tag='001']", NS)
                    idn_val = f001.text.strip() if (f001 is not None and f001.text) else ""
                    if idn_val and idn_val in seen_idns:
                        continue

                    f008 = elem.find("marc:controlfield[@tag='008']", NS)
                    c008 = f008.text if (f008 is not None and f008.text) else ""
                    lang_008 = c008[35:38].lower() if len(c008) >= 38 else ""
                    yr_008 = c008[7:11] if len(c008) >= 11 else ""

                    is_ger = lang_008 in ("ger", "deu")
                    if not is_ger:
                        for f041 in elem.findall("marc:datafield[@tag='041']/marc:subfield[@code='a']", NS):
                            if f041.text and f041.text.strip().lower() in ("ger", "deu"):
                                is_ger = True
                                break
                    if not is_ger:
                        continue

                    rec = parse_marc_record(elem, fetch_blurbs=fetch_remote_blurbs)
                    yr_str = str(rec.get("date") or "")
                    if not (len(yr_str) == 4 and yr_str.isdigit()) and len(yr_008) == 4 and yr_008.isdigit():
                        yr_str = yr_008
                        rec["date"] = yr_str
                        rec["decade"] = f"{yr_str[:3]}0s"

                    if len(yr_str) == 4 and yr_str.isdigit() and 1970 <= int(yr_str) <= 2025 and rec.get("title"):
                        tl = rec["title"].lower().strip()
                        if tl in seen_titles:
                            continue
                        ddc_val = rec.get("ddc") or "000"
                        abs_txt = rec.get("abstract_note") or ""
                        kw_txt = rec.get("keywords") or ""
                        body_parts = [p for p in [abs_txt, kw_txt, f"DNB Sachgruppe {ddc_val}"] if p and p.strip()]
                        body_str = " ".join(body_parts).strip()
                        full_txt = f"{rec['title']}. {rec['author']}. {rec['publisher']}. {body_str}".strip()
                        wc = len(full_txt.split())
                        if wc >= 4:
                            src = (
                                rec.get("oa_pdf_url")
                                or rec.get("toc_pdf_url")
                                or rec.get("blurb_url")
                                or (f"https://d-nb.info/{idn_val}" if idn_val else "https://portal.dnb.de")
                            )
                            batch_rows.append({
                                "title": rec["title"],
                                "author": rec["author"],
                                "date": yr_str,
                                "decade": rec["decade"],
                                "publisher": rec["publisher"],
                                "corpus_layer": "dnb_deposit_inhaltstext",
                                "source_file": src,
                                "chunk_index": 1,
                                "total_chunks": 1,
                                "word_count": wc,
                                "abstract": (abs_txt or kw_txt or rec["title"])[:240],
                                "text": body_str,
                            })
                            if idn_val:
                                seen_idns.add(idn_val)
                            seen_titles.add(tl)
                            total_ingested += 1
                            if len(batch_rows) >= batch_size:
                                new_shard = append_rows_to_zstd_parquet(batch_rows, parquet_dir=parquet_dir, compression_level=19)
                                batch_rows = []
                                if new_shard:
                                    created_shards.append(os.path.basename(new_shard))

                    if total_scanned % 50000 == 0:
                        print(
                            f"  ... [OpenData Stream Pkg {pkg_idx}] Scanned {total_scanned:,} MARC21 records | "
                            f"Ingested {total_ingested:,} new 1970-2025 German works (Total Corpus: {existing_total_rows + total_ingested:,})...",
                            flush=True,
                        )
                except Exception:
                    pass
                finally:
                    elem.clear()
                    root.clear()

            try:
                xml_stream.close()
            except Exception:
                pass
        except Exception as e:
            print(f"  [!] Stream warning on `{target_url}` after {total_scanned:,} scanned records: {e}", flush=True)

    if batch_rows:
        last_shard = append_rows_to_zstd_parquet(batch_rows, parquet_dir=parquet_dir, compression_level=19)
        if last_shard:
            created_shards.append(os.path.basename(last_shard))

    if upload_incremental and created_shards:
        upload_parquet_shards_to_github_release(
            parquet_dir,
            release_tag=release_tag,
            only_files=created_shards + ["parquet_manifest.json"],
        )

    print(
        f"[DNB OpenData Bulk Streamer] Completed: Scanned {total_scanned:,} MARC21 records -> "
        f"Ingested {total_ingested:,} new 1970-2025 German works to `{parquet_dir}`!",
        flush=True,
    )
    return total_ingested


def harvest_dnb_uncapped_year_x_sachgruppe(
    parquet_dir: str = "data/parquet",
    batch_size: int = 25000,
    max_pages_per_cell: int = 100,
    workers: int = 24,
    onlinefree_only: bool = False,
) -> int:
    """
    Uncapped `Year (1970–2025) × Sachgruppe (102 DNB Sachgruppen)` SRU streaming harvester.
    Partitions queries into `56 years × 102 Sachgruppen = 5,712` cells so every single query cell stays
    below the DNB SRU `startRecord <= 10,000` pagination ceiling, checkpointing completed `(year, hsg)`
    cells in `data/parquet/sru_year_hsg_checkpoint.json` and flushing directly to Zstd-9 `.parquet` shards.
    """
    os.makedirs(parquet_dir, exist_ok=True)
    ckpt_path = os.path.join(parquet_dir, "sru_year_hsg_checkpoint.json")
    completed_cells = set()
    if os.path.exists(ckpt_path):
        try:
            with open(ckpt_path, "r", encoding="utf-8") as cf:
                completed_cells = set(json.load(cf).get("completed_cells", []))
        except Exception:
            completed_cells = set()

    base_url = "https://services.dnb.de/sru/dnb"
    cells = [
        (yr, hsg)
        for yr in range(2025, 1969, -1)
        for hsg in ALL_DNB_SACHGRUPPEN_102
        if f"{yr}:{hsg}" not in completed_cells
    ]
    print(
        f"[Uncapped Year × Sachgruppe SRU Streamer] {len(cells):,} remaining (year, hsg) cells "
        f"(already checkpointed: {len(completed_cells):,})...",
        flush=True,
    )

    def _harvest_single_cell(cell):
        yr, hsg = cell
        oa_clause = " and location=onlinefree" if onlinefree_only else ""
        cql = f"hsg={hsg} and spr=ger and jhr={yr}{oa_clause}"
        cell_rows = []
        start_rec = 1
        max_rec = max_pages_per_cell * 100
        while start_rec <= max_rec:
            sess = _get_thread_session()
            try:
                resp = sess.get(
                    base_url,
                    params={
                        "operation": "searchRetrieve",
                        "version": "1.1",
                        "query": cql,
                        "recordSchema": "MARC21-xml",
                        "maximumRecords": "100",
                        "startRecord": str(start_rec),
                    },
                    verify=False,
                    timeout=20,
                )
                if resp.status_code != 200:
                    break
                tree = ET.fromstring(resp.content)
                num_txt = tree.findtext(".//zs:numberOfRecords", namespaces=NS)
                total_avail = int(num_txt) if (num_txt and num_txt.isdigit()) else 0
                srw_recs = tree.findall(".//zs:record", NS)
                if not srw_recs:
                    break
                for srw_rec in srw_recs:
                    marc_data = srw_rec.find(".//marc:record", NS)
                    if marc_data is None:
                        continue
                    rec = parse_marc_record(marc_data, fetch_blurbs=False, force_onlinefree=onlinefree_only)
                    if rec["title"] and rec["date"]:
                        txt_body = rec.get("text") or rec["title"]
                        wc = max(10, len(txt_body.split()))
                        src = (
                            rec.get("oa_pdf_url")
                            or rec.get("toc_pdf_url")
                            or rec.get("blurb_url")
                            or f"https://d-nb.info/{rec.get('idn') or ''}"
                        )
                        layer = (
                            "dnb_oa_fullbook"
                            if rec.get("oa_pdf_url")
                            else ("dnb_toc_pdf_fulltext" if rec.get("toc_pdf_url") else "dnb_deposit_inhaltstext")
                        )
                        cell_rows.append({
                            "title": rec["title"],
                            "author": rec["author"],
                            "date": rec["date"],
                            "decade": rec["decade"],
                            "publisher": rec["publisher"],
                            "corpus_layer": layer,
                            "source_file": src,
                            "chunk_index": 1,
                            "total_chunks": 1,
                            "word_count": wc,
                            "abstract": (rec.get("abstract_note") or txt_body)[:240],
                            "text": f"{rec['title']}. {rec['author']}. {rec['publisher']}. {txt_body}",
                        })
                start_rec += 100
                if start_rec > total_avail:
                    break
            except Exception:
                break
        return f"{yr}:{hsg}", cell_rows

    buf = []
    total_written = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_harvest_single_cell, c): c for c in cells}
        for fut in as_completed(futs):
            cell_key, c_rows = fut.result()
            completed_cells.add(cell_key)
            if c_rows:
                buf.extend(c_rows)
                total_written += len(c_rows)
            if len(buf) >= batch_size:
                append_rows_to_zstd_parquet(buf, parquet_dir=parquet_dir)
                buf = []
                with open(ckpt_path, "w", encoding="utf-8") as cf:
                    json.dump({"completed_cells": sorted(completed_cells)}, cf)

    if buf:
        append_rows_to_zstd_parquet(buf, parquet_dir=parquet_dir)
    with open(ckpt_path, "w", encoding="utf-8") as cf:
        json.dump({"completed_cells": sorted(completed_cells)}, cf)
    return total_written


def upload_parquet_shards_to_github_release(
    parquet_dir: str = "data/parquet",
    release_tag: str = "v12.0-dnb-parquet-shards",
    repo: str = "metachasm-beep/Deutsche-Verlage-LDA",
    only_files: list[str] = None,
) -> bool:
    """
    Uploads Zstd-19 Apache Parquet shards (`data/parquet/dnb_corpus_part*.parquet` and `parquet_manifest.json`,
    up to 2.0 GB per asset file) to GitHub Release Assets via `gh release upload` or the GitHub Releases REST API
    (`https://uploads.github.com/repos/{repo}/releases/{id}/assets`) using `git credential fill` or `GITHUB_TOKEN`.
    """
    import glob
    import shutil
    import subprocess

    shard_files = sorted(glob.glob(os.path.join(parquet_dir, "dnb_corpus_part*.parquet")))
    manifest_file = os.path.join(parquet_dir, "parquet_manifest.json")
    if os.path.exists(manifest_file):
        shard_files.append(manifest_file)
    if only_files:
        only_set = set(only_files)
        shard_files = [f for f in shard_files if os.path.basename(f) in only_set]
    if not shard_files:
        print(f"No Parquet shards found in `{parquet_dir}` to upload.", flush=True)
        return False

    # Path 1: Use `gh` CLI if installed
    if shutil.which("gh"):
        print(f"Uploading {len(shard_files)} Zstd Parquet assets to GitHub Release `{release_tag}` via `gh` CLI...", flush=True)
        subprocess.run(
            ["gh", "release", "create", release_tag, "--repo", repo, "--title", f"DNB Complete Zstd Parquet Corpus ({release_tag})", "--notes", "Zstandard-9 Apache Parquet shards of the DNB 1970-2025 corpus."],
            check=False,
        )
        cmd = ["gh", "release", "upload", release_tag, *shard_files, "--repo", repo, "--clobber"]
        res = subprocess.run(cmd, check=False)
        if res.returncode == 0:
            print(f"  -> Successfully uploaded {len(shard_files)} Parquet assets to GitHub Release `{release_tag}`!", flush=True)
            return True

    # Path 2: Native GitHub REST API using `GITHUB_TOKEN` or `git credential fill`
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        try:
            proc = subprocess.run(
                ["git", "credential", "fill"],
                input="protocol=https\nhost=github.com\n\n",
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in (proc.stdout or "").splitlines():
                if line.startswith("password="):
                    token = line.split("=", 1)[1].strip()
                    break
        except Exception:
            pass

    if not token:
        print("Warning: Could not resolve GitHub token via `gh` or `git credential fill`.", flush=True)
        return False

    api_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    rel_url = f"https://api.github.com/repos/{repo}/releases/tags/{release_tag}"
    r_get = requests.get(rel_url, headers=api_headers, timeout=20, verify=False)
    if r_get.status_code == 404:
        r_create = requests.post(
            f"https://api.github.com/repos/{repo}/releases",
            headers=api_headers,
            json={
                "tag_name": release_tag,
                "target_commitish": "main",
                "name": f"DNB 1970–2025 Zstd-19 Apache Parquet Corpus ({release_tag})",
                "body": (
                    "### Deutsche Nationalbibliothek (1970–2025) Zstandard-19 Apache Parquet Shards\n"
                    "- **Compression:** Apache Parquet 2.6 + Zstandard (`level=19`) + Dictionary Encoding & Prefix Deduplication\n"
                    "- **Coverage:** All 102 DNB `Sachgruppen` (`000–990`, `B`, `K`, `S`), `489,860` passages, `401,327,320` words, `94,178` unique works (`13,792` complete full-text books).\n"
                    "- **Streaming Loader:** Automatically streamed by `lda_pipeline.iter_corpus_rows(..., prefer_parquet=True)` and `lda_pipeline.run_streaming_online_lda_pipeline()`."
                ),
                "draft": False,
                "prerelease": False,
            },
            timeout=25,
            verify=False,
        )
        if r_create.status_code not in (200, 201):
            print(f"  -> GitHub Release creation returned HTTP {r_create.status_code}: {r_create.text[:240]}", flush=True)
            return False
        rel_obj = r_create.json()
    elif r_get.status_code == 200:
        rel_obj = r_get.json()
    else:
        print(f"  -> GitHub Release lookup returned HTTP {r_get.status_code}: {r_get.text[:240]}", flush=True)
        return False

    release_id = rel_obj["id"]
    existing_assets = {a["name"]: a["id"] for a in rel_obj.get("assets", [])}
    upload_base = f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets"

    for fpath in shard_files:
        fname = os.path.basename(fpath)
        if fname in existing_assets:
            requests.delete(
                f"https://api.github.com/repos/{repo}/releases/assets/{existing_assets[fname]}",
                headers=api_headers,
                timeout=20,
                verify=False,
            )
        content_type = "application/json" if fname.endswith(".json") else "application/vnd.apache.parquet"
        up_headers = dict(api_headers)
        up_headers["Content-Type"] = content_type
        sz_mb = os.path.getsize(fpath) / (1024 * 1024)
        print(f"  -> Uploading `{fname}` ({sz_mb:.2f} MB) to GitHub Release `{release_tag}`...", flush=True)
        with open(fpath, "rb") as bf:
            r_up = requests.post(
                f"{upload_base}?name={fname}",
                headers=up_headers,
                data=bf,
                timeout=600,
                verify=False,
            )
        if r_up.status_code in (200, 201):
            dl_url = r_up.json().get("browser_download_url", "")
            print(f"     [OK] Uploaded `{fname}` -> {dl_url}", flush=True)
        else:
            print(f"     [WARN] Failed to upload `{fname}`: HTTP {r_up.status_code} {r_up.text[:200]}", flush=True)
            return False

    return True


def fetch_dnblab_04_toc_text_or_pdf(url: str, max_pages: int = 12) -> tuple[str, int]:
    """
    Fetches a Digitized Table of Contents (`d-nb.info/{idn}/04`) using the official DNBLab
    plain-text OCR endpoint (`https://d-nb.info/{idn}/04/text`, ~25ms UTF-8 text without PDF parsing),
    falling back to `stream_dnb_34_pdf_or_epub_in_ram(url)` only if `/04/text` is unavailable.
    """
    if not url:
        return "", 0
    if url.endswith("/04") and "d-nb.info" in url:
        txt_url = url + "/text"
        try:
            sess = _get_thread_session()
            r = sess.get(txt_url, headers=HEADERS, timeout=(3, 7), verify=False)
            if r.status_code == 200 and r.content:
                raw_txt = r.content.decode("utf-8-sig", errors="ignore")
                clean_txt = normalize_german_text(raw_txt)
                wc = len(clean_txt.split())
                if wc >= 25:
                    est_pages = max(1, min(max_pages, round(wc / 180)))
                    return clean_txt, est_pages
        except Exception:
            pass
    return stream_dnb_34_pdf_or_epub_in_ram(url, max_pages=max_pages)


def load_or_fetch_dnblab_free_idns(cache_path: str = "data/primary_texts/dnblab_free_idns.json") -> set[str]:
    """
    Streams the official DNBLab Free Digital Object MARC21-XML dumps on `https://data.dnb.de/`
    (`FreieOnlineHochschulschriften` 000..900, `FreieOnlineMonografien`, and `REIHE_O_LF` Reihe O E-Books)
    to collect DNB IDNs (`001`) that are guaranteed `onlinefree` (`200 OK` full-text PDF/EPUB at `https://d-nb.info/{idn}/34`).
    """
    existing_idns = set()
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as cf:
                data = json.load(cf)
                existing_idns = set(data)
                if len(existing_idns) >= 240000:
                    return existing_idns
        except Exception:
            pass

    dnblab_urls = [
        "https://data.dnb.de/FreieOnlineHochschulschriften/dnb-all_online_hochschulschriften_frei_000_dnbmarc.mrc.xml.gz",
        "https://data.dnb.de/FreieOnlineHochschulschriften/dnb-all_online_hochschulschriften_frei_100_dnbmarc.mrc.xml.gz",
        "https://data.dnb.de/FreieOnlineHochschulschriften/dnb-all_online_hochschulschriften_frei_200_dnbmarc.mrc.xml.gz",
        "https://data.dnb.de/FreieOnlineHochschulschriften/dnb-all_online_hochschulschriften_frei_300_dnbmarc.mrc.xml.gz",
        "https://data.dnb.de/FreieOnlineHochschulschriften/dnb-all_online_hochschulschriften_frei_400_dnbmarc.mrc.xml.gz",
        "https://data.dnb.de/FreieOnlineHochschulschriften/dnb-all_online_hochschulschriften_frei_500_dnbmarc.mrc.xml.gz",
        "https://data.dnb.de/FreieOnlineHochschulschriften/dnb-all_online_hochschulschriften_frei_600_dnbmarc.mrc.xml.gz",
        "https://data.dnb.de/FreieOnlineHochschulschriften/dnb-all_online_hochschulschriften_frei_700_dnbmarc.mrc.xml.gz",
        "https://data.dnb.de/FreieOnlineHochschulschriften/dnb-all_online_hochschulschriften_frei_800_dnbmarc.mrc.xml.gz",
        "https://data.dnb.de/FreieOnlineHochschulschriften/dnb-all_online_hochschulschriften_frei_900_dnbmarc.mrc.xml.gz",
        "https://data.dnb.de/FreieOnlineMonografien/dnb-all_online_monografien_frei_dnbmarc.mrc.xml.gz",
        "https://data.dnb.de/REIHE_O_LF/dnb-freie-netzpublikationen_dnbmarc.mrc.xml.gz",
    ]
    if len(existing_idns) >= 180000:
        dnblab_urls = [
            "https://data.dnb.de/REIHE_O_LF/dnb-freie-netzpublikationen_dnbmarc.mrc.xml.gz",
        ]
    elif len(existing_idns) >= 70000:
        dnblab_urls = [
            "https://data.dnb.de/FreieOnlineHochschulschriften/dnb-all_online_hochschulschriften_frei_500_dnbmarc.mrc.xml.gz",
            "https://data.dnb.de/FreieOnlineHochschulschriften/dnb-all_online_hochschulschriften_frei_600_dnbmarc.mrc.xml.gz",
            "https://data.dnb.de/FreieOnlineMonografien/dnb-all_online_monografien_frei_dnbmarc.mrc.xml.gz",
            "https://data.dnb.de/REIHE_O_LF/dnb-freie-netzpublikationen_dnbmarc.mrc.xml.gz",
        ]
    import zlib
    free_idns = set(existing_idns)
    print(
        f"  [DNBLab] Indexing guaranteed-free (`onlinefree`) DNB `/34` IDNs from {len(dnblab_urls)} DNBLab dumps (starting with {len(free_idns):,})...",
        flush=True,
    )
    idn_rx = re.compile(rb'<controlfield tag="001">([^<]+)</controlfield>')
    for u in dnblab_urls:
        try:
            t_stream = time.time()
            with requests.get(u, stream=True, timeout=(15, 60), verify=False) as resp:
                if resp.status_code != 200:
                    continue
                dobj = zlib.decompressobj(16 + zlib.MAX_WBITS)
                tail = b""
                for raw_chunk in resp.iter_content(chunk_size=512 * 1024):
                    if not raw_chunk:
                        break
                    data = tail + dobj.decompress(raw_chunk)
                    for m in idn_rx.finditer(data):
                        free_idns.add(m.group(1).decode("ascii", errors="ignore").strip())
                    tail = data[-128:] if len(data) > 128 else data
                    if "REIHE_O_LF" in u and (len(free_idns) >= 280000 or time.time() - t_stream > 28.0):
                        break
        except Exception as e:
            print(f"    [WARN] DNBLab index stream `{u}`: {e}", flush=True)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    try:
        with open(cache_path, "w", encoding="utf-8") as cf:
            json.dump(sorted(free_idns), cf)
    except Exception:
        pass
    print(f"  [DNBLab] Indexed {len(free_idns):,} guaranteed-free (`onlinefree`) DNB `/34` full-text & Reihe O e-book IDNs!", flush=True)
    return free_idns


async def _async_hydrate_shard_blurbs_and_tocs(
    blurb_tasks: list[tuple[int, str]],
    toc_tasks: list[tuple[int, str]],
    host_concurrency: int = 72,
) -> list[tuple[int, str, str, int]]:
    """
    High-throughput asynchronous `aiohttp` hydration engine with independent per-host semaphores:
      - `sem_blurb` (`Semaphore(72)`): `services.dnb.de/plus/idn/{idn}/blurb/` & `deposit.dnb.de/cgi-bin/dokserv`
      - `sem_toc` (`Semaphore(72)`): `https://d-nb.info/{idn}/04/text` plain-text TOC OCRs
    Sustains ~110+ requests/sec with automatic 429/503 retry backoff and zero MuPDF lock contention.
    """
    import asyncio
    import aiohttp

    if not blurb_tasks and not toc_tasks:
        return []

    sem_blurb = asyncio.Semaphore(host_concurrency)
    sem_toc = asyncio.Semaphore(host_concurrency)
    p_rx = re.compile(r"<p[^>]*>(.*?)</p>", flags=re.DOTALL | re.IGNORECASE)
    tag_rx = re.compile(r"<[^>]+>")

    connector = aiohttp.TCPConnector(
        limit=host_concurrency * 2 + 32,
        limit_per_host=host_concurrency,
        ssl=False,
        ttl_dns_cache=600,
    )
    timeout = aiohttp.ClientTimeout(total=10, connect=4)

    async with aiohttp.ClientSession(connector=connector, headers=HEADERS, timeout=timeout) as session:

        async def _fetch_blurb_async(r_idx: int, url: str) -> tuple[int, str, str, int]:
            async with sem_blurb:
                for attempt in range(2):
                    try:
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                raw_bytes = await resp.read()
                                if not raw_bytes:
                                    return r_idx, "blurb", "", 0
                                raw_html = raw_bytes.decode("utf-8", errors="ignore")
                                p_matches = p_rx.findall(raw_html)
                                content = " ".join(p_matches) if p_matches else raw_html
                                clean = tag_rx.sub(" ", content)
                                clean = (
                                    clean.replace("&#xa0;", " ")
                                    .replace("&nbsp;", " ")
                                    .replace("&quot;", '"')
                                    .replace("&amp;", "&")
                                )
                                norm = normalize_german_text(clean)
                                if len(norm.split()) >= 12:
                                    return r_idx, "blurb", norm, 1
                                return r_idx, "blurb", "", 0
                            elif resp.status in (429, 503) and attempt == 0:
                                await asyncio.sleep(0.45)
                                continue
                            else:
                                return r_idx, "blurb", "", 0
                    except Exception:
                        if attempt == 0:
                            await asyncio.sleep(0.25)
                            continue
                        return r_idx, "blurb", "", 0
            return r_idx, "blurb", "", 0

        async def _fetch_toc_async(r_idx: int, url: str) -> tuple[int, str, str, int]:
            txt_url = (url + "/text") if (url.endswith("/04") and "d-nb.info" in url) else url
            async with sem_toc:
                for attempt in range(2):
                    try:
                        async with session.get(txt_url) as resp:
                            if resp.status == 200:
                                raw_bytes = await resp.read()
                                if not raw_bytes:
                                    return r_idx, "toc_04", "", 0
                                raw_txt = raw_bytes.decode("utf-8-sig", errors="ignore")
                                norm = normalize_german_text(raw_txt)
                                wc = len(norm.split())
                                if wc >= 20:
                                    est_pages = max(1, min(12, round(wc / 180)))
                                    return r_idx, "toc_04", norm, est_pages
                                return r_idx, "toc_04", "", 0
                            elif resp.status in (429, 503) and attempt == 0:
                                await asyncio.sleep(0.45)
                                continue
                            else:
                                return r_idx, "toc_04", "", 0
                    except Exception:
                        if attempt == 0:
                            await asyncio.sleep(0.25)
                            continue
                        return r_idx, "toc_04", "", 0
            return r_idx, "toc_04", "", 0

        coros = [_fetch_blurb_async(idx, u) for idx, u in blurb_tasks] + [
            _fetch_toc_async(idx, u) for idx, u in toc_tasks
        ]
        results = await asyncio.gather(*coros, return_exceptions=False)
        return [r for r in results if r and r[2]]


def hydrate_parquet_shards_with_remote_fulltext_and_blurbs(
    parquet_dir: str = "data/parquet",
    start_shard: int = 8,
    end_shard: int = 125,
    workers: int = 64,
    max_oa_per_shard: int = 60,
    max_toc_per_shard: int = 600,
    max_blurbs_per_shard: int = 600,
    chunk_words: int = 1000,
    max_chunks_per_book: int = 35,
    upload_updated: bool = False,
    release_tag: str = "v12.0-dnb-parquet-shards",
) -> dict:
    """
    High-throughput hybrid `aiohttp` + `ThreadPoolExecutor` hydration pass over OpenData MARC21 Parquet shards
    (`dnb_corpus_part008.parquet` .. `dnb_corpus_part125.parquet`) powered by DNBLab:
      1. Indexes all guaranteed-free (`onlinefree`) `/34` IDNs from `data.dnb.de/FreieOnlineHochschulschriften/` (000..900)
         and `data.dnb.de/FreieOnlineMonografien/`, hydrating `d-nb.info/{idn}/34` & external repository Open-Access
         full-text PDFs/EPUBs via `stream_dnb_oa_multi_url_in_ram` (`dnb_oa_fullbook`, 1,000-word passages).
      2. Asynchronously hydrates `d-nb.info/{idn}/04/text` plain-text TOC OCRs and `services.dnb.de/plus/idn/{idn}/blurb/`
         publisher blurbs via `_async_hydrate_shard_blurbs_and_tocs` (`aiohttp` dual-semaphore engine at ~110+ req/s).
    Rewrites updated Zstd-19 Parquet shards atomically, appends overflow multi-chunk OA passages incrementally,
    and synchronizes `parquet_manifest.json`.
    """
    import asyncio
    import glob
    import hashlib
    import pyarrow as pa
    import pyarrow.parquet as pq

    dnblab_free_idns = load_or_fetch_dnblab_free_idns()

    shard_paths = sorted(
        glob.glob(os.path.join(parquet_dir, "dnb_corpus_part*.parquet")),
        key=lambda x: int(re.search(r"part(\d+)", x).group(1)) if re.search(r"part(\d+)", x) else 9999,
    )
    target_paths = []
    for sp in shard_paths:
        m = re.search(r"part(\d+)", os.path.basename(sp))
        if m:
            s_num = int(m.group(1))
            if start_shard <= s_num <= end_shard:
                target_paths.append((s_num, sp))

    print(
        f"\n[DNBLab Hybrid aiohttp + ThreadPool Parquet Hydration] Scanning {len(target_paths)} Zstd-19 Parquet shards "
        f"(part{start_shard:03d}..part{end_shard:03d}, workers={workers}, "
        f"targets/shard: OA={max_oa_per_shard}, TOC={max_toc_per_shard}, Blurbs={max_blurbs_per_shard})...",
        flush=True,
    )

    total_hydrated_oa_books = 0
    total_hydrated_oa_chunks = 0
    total_hydrated_tocs = 0
    total_hydrated_blurbs = 0
    total_added_words = 0
    modified_shard_names = []
    overflow_oa_chunks = []

    def _hydrate_oa_item(task_tuple):
        row_idx, kind, url = task_tuple
        txt, pages, _ = stream_dnb_oa_multi_url_in_ram([url], max_pages=65)
        if txt and len(txt.split()) >= 90:
            return row_idx, kind, txt, pages
        return row_idx, kind, "", 0

    for s_num, sp in target_paths:
        sname = os.path.basename(sp)
        t0 = time.time()
        table = pq.read_table(sp, memory_map=False)
        table_schema = table.schema
        cols = {c: table[c].to_pylist() for c in table.column_names}
        n_rows = table.num_rows
        del table

        ext_oa_candidates = []
        oa_34_candidates = []
        toc_04_candidates = []
        blurb_candidates = []

        srcs = cols["source_file"]
        wcs = cols["word_count"]
        pubs = cols["publisher"]
        titles_col = cols["title"]
        texts_col = cols["text"]

        domain_re = re.compile(
            r"(glaube|gott|kirche|theolog|religi|christ|bibel|islam|jüd|philosoph|ethik|moral|säkular|"
            r"achtsam|meditation|selbsthilfe|lebenshilfe|resilienz|spiritual|seelsorge|liturg|predigt|"
            r"gemeinde|aufklärung|ideolog|gesellschaft|demokrat|psycholog|soziolog|mystik|konzil|papst|"
            r"bischof|pfarrer|buddhis|hinduis|sinn|glück|burnout|coaching|heilung|diskurs|moderne|vernunft)",
            re.IGNORECASE,
        )
        comm_pub_re = re.compile(
            r"(herder|suhrkamp|beck|fischer|rowohlt|kösel|gräfe|unzer|vandenhoeck|mohr|kohlhammer|campus|"
            r"transcript|gruyter|patmos|kreuz|goldmann|knaur|schöningh|böhlau|evangelisch|gütersloher|"
            r"aschendorff|klett|springer|pustet|benno|echter|schwabenverlag|alibri|wagenbach|kiepenheuer|meiner|metzler)",
            re.IGNORECASE,
        )

        # Prioritize DNBLab guaranteed-free (`dnblab_free_idns`), RQ1-RQ3 domain works, & commercial publishers first
        for idx in range(n_rows):
            wc = wcs[idx] or 0
            if wc >= 75:
                continue
            u = srcs[idx] or ""
            if not u:
                continue
            pub_val = str(pubs[idx] or "")
            tl_val = str(titles_col[idx] or "")
            tx_val = str(texts_col[idx] or "")[:300]
            is_comm_pub = 0 if comm_pub_re.search(pub_val) else (1 if (pub_val and pub_val != "Sonstige / Weitere Verlage") else 2)
            has_domain = 0 if (domain_re.search(tl_val) or domain_re.search(tx_val)) else 1
            prio_tuple = (has_domain, is_comm_pub)

            if "deposit.dnb.de" in u or "/blurb/" in u:
                live_blurb = 0 if ("deposit.dnb.de" in u or "/idn/1" in u or "/idn/97" in u or "/idn/98" in u or "/idn/99" in u or "/idn/96" in u) else 1
                blurb_candidates.append(((live_blurb, has_domain, is_comm_pub), idx, u))
            elif u.endswith("/04") and "d-nb.info" in u:
                live_toc = 0 if ("/1" in u or "/96" in u or "/97" in u or "/98" in u or "/99" in u or "/95" in u) else 1
                toc_04_candidates.append(((live_toc, has_domain, is_comm_pub), idx, u))
            elif u.endswith("/34") and "d-nb.info" in u:
                idn_part = u.split("/")[-2] if u.count("/") >= 4 else ""
                if idn_part in dnblab_free_idns:
                    oa_34_candidates.append(((-2 if has_domain == 0 else -1, is_comm_pub), idx, "oa_34", u))
                elif idn_part.startswith(("9", "10", "11", "12")) and has_domain == 0:
                    oa_34_candidates.append(((0, is_comm_pub), idx, "oa_34", u))
            elif not u.startswith("https://d-nb.info/") and "portal.dnb.de" not in u:
                ext_oa_candidates.append((prio_tuple, idx, "ext_oa", u))

        ext_oa_candidates.sort(key=lambda x: x[0])
        oa_34_candidates.sort(key=lambda x: x[0])
        toc_04_candidates.sort(key=lambda x: x[0])
        blurb_candidates.sort(key=lambda x: x[0])

        # Select OA tasks (domain-relevant guaranteed-free DNBLab /34 links + external repository OA links first)
        dnblab_guaranteed = [c for c in oa_34_candidates if c[0][0] < 0]
        other_oa_34 = [c for c in oa_34_candidates if c[0][0] >= 0]
        oa_pool = (dnblab_guaranteed + ext_oa_candidates + other_oa_34)[:max_oa_per_shard] if max_oa_per_shard > 0 else []
        oa_tasks = [(idx, kind, u) for _, idx, kind, u in oa_pool]

        toc_tasks = [(idx, u) for _, idx, u in (toc_04_candidates[:max_toc_per_shard] if max_toc_per_shard > 0 else [])]
        blurb_tasks = [(idx, u) for _, idx, u in (blurb_candidates[:max_blurbs_per_shard] if max_blurbs_per_shard > 0 else [])]

        if not oa_tasks and not toc_tasks and not blurb_tasks:
            continue

        shard_oa = 0
        shard_toc = 0
        shard_blurb = 0
        shard_words_added = 0

        # Launch OA PDF/EPUB threads in background while running high-speed aiohttp blurb + TOC hydration
        hydrated_results = []
        if oa_tasks:
            with ThreadPoolExecutor(max_workers=min(workers, max(4, len(oa_tasks)))) as ex:
                oa_futures = [ex.submit(_hydrate_oa_item, t) for t in oa_tasks]
                if blurb_tasks or toc_tasks:
                    async_res = asyncio.run(
                        _async_hydrate_shard_blurbs_and_tocs(blurb_tasks, toc_tasks, host_concurrency=72)
                    )
                    hydrated_results.extend(async_res)
                for fut in oa_futures:
                    try:
                        res = fut.result()
                        if res and res[2]:
                            hydrated_results.append(res)
                    except Exception:
                        pass
        elif blurb_tasks or toc_tasks:
            async_res = asyncio.run(
                _async_hydrate_shard_blurbs_and_tocs(blurb_tasks, toc_tasks, host_concurrency=72)
            )
            hydrated_results.extend(async_res)

        for r_idx, kind, hydrated_txt, pages in hydrated_results:
            if not hydrated_txt:
                continue
            old_txt = str(cols["text"][r_idx] or "")
            old_wc = int(cols["word_count"][r_idx] or 0)
            base_title = str(cols["title"][r_idx] or "")
            author_str = str(cols["author"][r_idx] or "")
            pub_str = str(cols["publisher"][r_idx] or "")
            date_str = str(cols["date"][r_idx] or "")
            dec_str = str(cols["decade"][r_idx] or "")
            src_url = str(cols["source_file"][r_idx] or "")

            if kind in ("ext_oa", "oa_34"):
                words_list = hydrated_txt.split()
                chunks = []
                for i in range(0, len(words_list), chunk_words):
                    ch_w = words_list[i : i + chunk_words]
                    if len(ch_w) >= 90 or (not chunks and len(ch_w) >= 50):
                        chunks.append(" ".join(ch_w))
                    if len(chunks) >= max_chunks_per_book:
                        break
                if not chunks:
                    continue
                n_ch = len(chunks)
                first_body = f"{chunks[0]} {old_txt}".strip()
                new_wc = len(f"{base_title}. {author_str}. {pub_str}. {first_body}".split())
                if n_ch > 1:
                    cols["title"][r_idx] = f"{base_title} [DNB-OA-Vollbuch-Abschnitt 1/{n_ch}]"
                cols["corpus_layer"][r_idx] = "dnb_oa_fullbook"
                cols["chunk_index"][r_idx] = 1
                cols["total_chunks"][r_idx] = n_ch
                cols["text"][r_idx] = first_body
                cols["abstract"][r_idx] = chunks[0][:240]
                cols["word_count"][r_idx] = new_wc
                shard_oa += 1
                total_hydrated_oa_books += 1
                total_hydrated_oa_chunks += n_ch
                shard_words_added += max(0, new_wc - old_wc)

                for c_i in range(2, n_ch + 1):
                    ch_txt = chunks[c_i - 1]
                    c_wc = len(ch_txt.split())
                    shard_words_added += c_wc
                    overflow_oa_chunks.append({
                        "title": f"{base_title} [DNB-OA-Vollbuch-Abschnitt {c_i}/{n_ch}]",
                        "author": author_str,
                        "date": date_str,
                        "decade": dec_str,
                        "publisher": pub_str,
                        "corpus_layer": "dnb_oa_fullbook",
                        "source_file": src_url,
                        "chunk_index": c_i,
                        "total_chunks": n_ch,
                        "word_count": c_wc,
                        "abstract": ch_txt[:240],
                        "text": ch_txt,
                    })
            elif kind == "toc_04":
                combined_body = f"[DNB-Inhaltsverzeichnis {pages} S.] {hydrated_txt} {old_txt}".strip()
                new_wc = len(f"{base_title}. {author_str}. {pub_str}. {combined_body}".split())
                cols["corpus_layer"][r_idx] = "dnb_toc_pdf_fulltext"
                cols["text"][r_idx] = combined_body
                cols["abstract"][r_idx] = hydrated_txt[:240]
                cols["word_count"][r_idx] = new_wc
                shard_toc += 1
                total_hydrated_tocs += 1
                shard_words_added += max(0, new_wc - old_wc)
            elif kind == "blurb":
                combined_body = f"{hydrated_txt}. {old_txt}".strip()
                new_wc = len(f"{base_title}. {author_str}. {pub_str}. {combined_body}".split())
                cols["text"][r_idx] = combined_body
                cols["abstract"][r_idx] = hydrated_txt[:240]
                cols["word_count"][r_idx] = new_wc
                shard_blurb += 1
                total_hydrated_blurbs += 1
                shard_words_added += max(0, new_wc - old_wc)

        if shard_oa + shard_toc + shard_blurb > 0:
            new_table = pa.Table.from_pydict(cols, schema=table_schema)
            tmp_sp = sp + ".tmp"
            pq.write_table(
                new_table,
                tmp_sp,
                compression="zstd",
                compression_level=19,
                use_dictionary=["author", "date", "decade", "publisher", "corpus_layer", "source_file"],
                write_statistics=True,
            )
            del new_table
            import gc
            gc.collect()
            for _att in range(5):
                try:
                    os.replace(tmp_sp, sp)
                    break
                except PermissionError:
                    gc.collect()
                    time.sleep(0.25)
            modified_shard_names.append(sname)
            total_added_words += shard_words_added
            el = time.time() - t0
            print(
                f"  -> Hydrated `{sname}` in {el:.1f}s: +{shard_oa} OA books, +{shard_toc} TOC OCRs, "
                f"+{shard_blurb} blurbs (+{shard_words_added:,} German words | cum: +{total_added_words:,} words)",
                flush=True,
            )

        # Incrementally flush overflow OA chunks whenever buffer reaches 85,000 passages
        while len(overflow_oa_chunks) >= 85000:
            batch_ch = overflow_oa_chunks[:85000]
            overflow_oa_chunks = overflow_oa_chunks[85000:]
            new_s = append_rows_to_zstd_parquet(
                batch_ch,
                parquet_dir=parquet_dir,
                compression_level=19,
            )
            if new_s:
                modified_shard_names.append(os.path.basename(new_s))

    if overflow_oa_chunks:
        print(f"\n  -> Appending {len(overflow_oa_chunks):,} continuation OA book chunks to Zstd-19 Parquet shards...", flush=True)
        for i in range(0, len(overflow_oa_chunks), 85000):
            new_s = append_rows_to_zstd_parquet(
                overflow_oa_chunks[i : i + 85000],
                parquet_dir=parquet_dir,
                compression_level=19,
            )
            if new_s:
                modified_shard_names.append(os.path.basename(new_s))

    # Rebuild parquet_manifest.json accurately across all shards
    all_shards = sorted(
        glob.glob(os.path.join(parquet_dir, "dnb_corpus_part*.parquet")),
        key=lambda x: int(re.search(r"part(\d+)", x).group(1)) if re.search(r"part(\d+)", x) else 9999,
    )
    manifest_path = os.path.join(parquet_dir, "parquet_manifest.json")
    old_manifest = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as mf:
                old_manifest = json.load(mf)
        except Exception:
            pass
    old_by_name = {(s.get("shard") or s.get("file")): s for s in old_manifest.get("shards", []) if (s.get("shard") or s.get("file"))}
    mod_set = set(modified_shard_names)

    new_shard_summaries = []
    tot_rows = 0
    tot_words = 0
    tot_bytes = 0
    import pyarrow.compute as pc
    for sp in all_shards:
        sn = os.path.basename(sp)
        sz_b = os.path.getsize(sp)
        tot_bytes += sz_b
        old_sz = old_by_name.get(sn, {}).get("size_bytes") or old_by_name.get(sn, {}).get("bytes")
        if sn not in mod_set and sn in old_by_name and sz_b == old_sz and old_by_name[sn].get("sha256"):
            entry = old_by_name[sn]
            entry["shard"] = sn
            entry["file"] = sn
            tot_rows += int(entry.get("rows", 0))
            if not entry.get("words"):
                t_wc = pq.read_table(sp, columns=["word_count"], memory_map=False)
                entry["words"] = int(pc.sum(t_wc["word_count"]).as_py() or 0)
            tot_words += int(entry.get("words", 0))
            new_shard_summaries.append(entry)
        else:
            if sn not in mod_set:
                modified_shard_names.append(sn)
                mod_set.add(sn)
            t_wc = pq.read_table(sp, columns=["word_count"], memory_map=False)
            r_cnt = t_wc.num_rows
            w_cnt = int(pc.sum(t_wc["word_count"]).as_py() or 0)
            del t_wc
            tot_rows += r_cnt
            tot_words += w_cnt
            h = hashlib.sha256()
            with open(sp, "rb") as bf:
                for chunk in iter(lambda: bf.read(1024 * 1024), b""):
                    h.update(chunk)
            entry = {
                "shard": sn,
                "file": sn,
                "path": sp.replace("\\", "/"),
                "rows": r_cnt,
                "words": w_cnt,
                "bytes": sz_b,
                "size_bytes": sz_b,
                "size_mb": round(sz_b / (1024 * 1024), 2),
                "sha256": h.hexdigest(),
            }
            new_shard_summaries.append(entry)

    old_manifest["total_rows"] = tot_rows
    old_manifest["total_words"] = tot_words
    old_manifest["total_shards"] = len(new_shard_summaries)
    old_manifest["total_parquet_bytes"] = tot_bytes
    old_manifest["total_parquet_mb"] = round(tot_bytes / (1024 * 1024), 2)
    old_manifest["shards"] = new_shard_summaries
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(old_manifest, mf, indent=2, ensure_ascii=False)

    print(
        f"\n[Parquet Hydration Complete] Hydrated {total_hydrated_oa_books:,} OA full-text books "
        f"({total_hydrated_oa_chunks:,} passages), {total_hydrated_tocs:,} digitized TOC PDFs, "
        f"and {total_hydrated_blurbs:,} publisher blurbs (+{total_added_words:,} new German words)!\n"
        f"  -> Master Parquet Corpus: {tot_rows:,} passages | {tot_words:,} words across {len(new_shard_summaries)} shards ({old_manifest['total_parquet_mb']:.2f} MB).",
        flush=True,
    )

    if upload_updated and modified_shard_names:
        upload_parquet_shards_to_github_release(
            parquet_dir=parquet_dir,
            release_tag=release_tag,
            only_files=list(dict.fromkeys(modified_shard_names + ["parquet_manifest.json"])),
        )

    return {
        "hydrated_oa_books": total_hydrated_oa_books,
        "hydrated_oa_chunks": total_hydrated_oa_chunks,
        "hydrated_tocs": total_hydrated_tocs,
        "hydrated_blurbs": total_hydrated_blurbs,
        "added_words": total_added_words,
        "total_rows": tot_rows,
        "total_words": tot_words,
        "modified_shards": modified_shard_names,
    }


def export_dnblab_restricted_to_dtf_parquet_shard(
    local_object_dir: str,
    parquet_dir: str = "data/parquet",
    chunk_words: int = 1000,
    max_chunks_per_book: int = 45,
) -> dict:
    """
    § 60d UrhG (German Copyright Act) & NFDI Text+ Derived Text Format (DTF) exporter for
    In-Copyright Commercial Print Scans & E-Books (`access_restricted` `/34` objects) inside a DNBLab workstation:
      1. Streams restricted PDF, EPUB, or TXT digital objects from `local_object_dir` in volatile RAM.
      2. Lemmatizes and POS-filters (`NOUN`, `PROPN`, `ADJ`) each 1,000-word passage via `lda_pipeline.preprocess_text`,
         destroying original sentence order by sorting/bagging lemmatized tokens into a non-reconstructible
         Derived Text Format (DTF) token stream (`corpus_layer = "dnblab_dtf_incopyright"`).
      3. Immediately discards raw copyrighted prose from RAM and appends the DTF rows directly into our
         Zstd-19 Apache Parquet corpus (`data/parquet/dnb_corpus_part*.parquet`), which can be legally
         exported from DNBLab and modeled by `run_streaming_online_lda_pipeline`.
    """
    import fitz
    import lda_pipeline

    if not os.path.exists(local_object_dir):
        print(f"[DNBLab § 60d UrhG DTF Exporter] Directory `{local_object_dir}` not found.", flush=True)
        return {"books_converted": 0, "dtf_passages_added": 0, "dtf_words_added": 0}

    dtf_rows = []
    books_converted = 0
    total_dtf_words = 0

    for root, _, files in os.walk(local_object_dir):
        for fname in sorted(files):
            if not fname.lower().endswith((".pdf", ".epub", ".txt")):
                continue
            fpath = os.path.join(root, fname)
            try:
                if fname.lower().endswith(".txt"):
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as tf:
                        raw_text = tf.read()
                else:
                    with fitz.open(fpath) as doc:
                        raw_text = " ".join(page.get_text("text") for page in doc)
                words = raw_text.split()
                del raw_text  # Immediately discard copyrighted prose from RAM (§ 60d UrhG)
                if len(words) < 100:
                    continue

                base_id = os.path.splitext(fname)[0]
                raw_chunks = []
                for idx in range(0, len(words), chunk_words):
                    ch_w = words[idx : idx + chunk_words]
                    if len(ch_w) >= 80:
                        raw_chunks.append(" ".join(ch_w))
                    if len(raw_chunks) >= max_chunks_per_book:
                        break
                del words
                if not raw_chunks:
                    continue

                books_converted += 1
                n_ch = len(raw_chunks)
                for c_idx, ch_str in enumerate(raw_chunks, start=1):
                    lemmas = lda_pipeline.preprocess_text(ch_str)
                    cleaned = lda_pipeline.clean_row_tokens_for_modeling(lemmas, {"title": base_id})
                    if not cleaned:
                        continue
                    # Destroy syntactic word order by sorting lemmas alphabetically (Derived Text Format / DTF)
                    dtf_token_bag_str = " ".join(sorted(cleaned))
                    wc = len(cleaned)
                    total_dtf_words += wc
                    dtf_rows.append({
                        "title": f"{base_id} [DNBLab-DTF-Abschnitt {c_idx}/{n_ch}]",
                        "author": "DNBLab Restricted Deposit (§ 60d UrhG)",
                        "date": "2020",
                        "decade": "2020s",
                        "publisher": "DNBLab In-Copyright Commercial Imprint (§ 60d UrhG DTF)",
                        "corpus_layer": "dnblab_dtf_incopyright",
                        "source_file": f"https://d-nb.info/{base_id}/34",
                        "chunk_index": c_idx,
                        "total_chunks": n_ch,
                        "word_count": wc,
                        "abstract": f"[§ 60d UrhG Non-Reconstructible Derived Text Format (DTF) Bag-of-Lemmas: {wc} tokens]",
                        "text": dtf_token_bag_str,
                    })
            except Exception:
                continue

    if dtf_rows:
        append_rows_to_zstd_parquet(dtf_rows, parquet_dir=parquet_dir, compression_level=19)
        print(
            f"[DNBLab § 60d UrhG DTF Export Complete] Converted {books_converted:,} restricted commercial works "
            f"into {len(dtf_rows):,} non-reconstructible DTF passages ({total_dtf_words:,} lemmatized tokens) in `{parquet_dir}`!",
            flush=True,
        )
    return {
        "books_converted": books_converted,
        "dtf_passages_added": len(dtf_rows),
        "dtf_words_added": total_dtf_words,
    }


async def _async_hydrate_commercial_dual_blurb_and_toc(
    commercial_tasks: list[tuple[int, str, str]],
    host_concurrency: int = 85,
) -> list[tuple[int, str, str, int]]:
    """
    Dual-endpoint asynchronous `aiohttp` hydrator for In-Copyright Commercial Print & E-Books:
    For each `(r_idx, idn, orig_src)` commercial book candidate (whether `orig_src` is a DRM-restricted
    `/34` e-book, a `/04` print TOC, a `/blurb/` endpoint, or a bare `d-nb.info/{idn}` URI), concurrently
    queries BOTH:
      1. `https://services.dnb.de/plus/idn/{idn}/blurb/` (or `deposit.dnb.de`) via `sem_blurb`
      2. `https://d-nb.info/{idn}/04/text` (Digitized Print TOC & Reading Sample OCR) via `sem_toc`
    Returns `(r_idx, blurb_txt, toc_txt, est_pages)` for all commercial works with HTTP 200 content.
    """
    import asyncio
    import aiohttp

    if not commercial_tasks:
        return []

    sem_blurb = asyncio.Semaphore(host_concurrency)
    sem_toc = asyncio.Semaphore(host_concurrency)
    p_rx = re.compile(r"<p[^>]*>(.*?)</p>", flags=re.DOTALL | re.IGNORECASE)
    tag_rx = re.compile(r"<[^>]+>")

    connector = aiohttp.TCPConnector(
        limit=host_concurrency * 2 + 32,
        limit_per_host=host_concurrency,
        ssl=False,
        ttl_dns_cache=600,
    )
    timeout = aiohttp.ClientTimeout(total=9, connect=3.5)

    async with aiohttp.ClientSession(connector=connector, headers=HEADERS, timeout=timeout) as session:

        async def _fetch_dual(r_idx: int, idn: str, orig_src: str) -> tuple[int, str, str, int]:
            blurb_u = orig_src if "deposit.dnb.de" in orig_src else f"https://services.dnb.de/plus/idn/{idn}/blurb/"
            toc_u = f"https://d-nb.info/{idn}/04/text"
            blurb_txt = ""
            toc_txt = ""
            est_pages = 0

            async with sem_blurb:
                try:
                    async with session.get(blurb_u) as resp:
                        if resp.status == 200:
                            raw_bytes = await resp.read()
                            if raw_bytes:
                                raw_html = raw_bytes.decode("utf-8", errors="ignore")
                                p_matches = p_rx.findall(raw_html)
                                content = " ".join(p_matches) if p_matches else raw_html
                                clean = tag_rx.sub(" ", content)
                                clean = (
                                    clean.replace("&#xa0;", " ")
                                    .replace("&nbsp;", " ")
                                    .replace("&quot;", '"')
                                    .replace("&amp;", "&")
                                )
                                norm = normalize_german_text(clean)
                                if len(norm.split()) >= 12:
                                    blurb_txt = norm
                except Exception:
                    pass

            async with sem_toc:
                try:
                    async with session.get(toc_u) as resp:
                        if resp.status == 200:
                            raw_bytes = await resp.read()
                            if raw_bytes:
                                raw_txt = raw_bytes.decode("utf-8-sig", errors="ignore")
                                norm_t = normalize_german_text(raw_txt)
                                wc_t = len(norm_t.split())
                                if wc_t >= 20:
                                    toc_txt = norm_t
                                    est_pages = max(1, min(12, round(wc_t / 180)))
                except Exception:
                    pass

            if blurb_txt or toc_txt:
                return r_idx, blurb_txt, toc_txt, max(1, est_pages)
            return r_idx, "", "", 0

        coros = [_fetch_dual(r_idx, idn, orig_src) for r_idx, idn, orig_src in commercial_tasks]
        results = await asyncio.gather(*coros, return_exceptions=False)
        return [r for r in results if r and (r[1] or r[2])]


def incorporate_dnblab_incopyright_commercial_books(
    parquet_dir: str = "data/parquet",
    start_shard: int = 40,
    end_shard: int = 125,
    workers: int = 64,
    max_commercial_per_shard: int = 650,
    max_oa_34_per_shard: int = 35,
    chunk_words: int = 1000,
    max_chunks_per_book: int = 35,
    upload_updated: bool = False,
    release_tag: str = "v12.0-dnb-parquet-shards",
) -> dict:
    """
    DNBLab In-Copyright Commercial Print & E-Book Incorporator + § 60d UrhG DTF Hydrator:
      1. Indexes DNBLab's `REIHE_O_LF` (`dnb-freie-netzpublikationen_dnbmarc.mrc.xml.gz`), `FreieOnlineMonografien`,
         and `FreieOnlineHochschulschriften` IDNs (`load_or_fetch_dnblab_free_idns`).
      2. Scans `dnb_corpus_part040.parquet` .. `dnb_corpus_part125.parquet` specifically targeting our 33 canonical
         In-Copyright Commercial Print & E-Book Publishers (`Suhrkamp`, `Herder`, `C.H. Beck`, `Fischer`, `Rowohlt`,
         `Kösel`, `Gräfe und Unzer`, `Vandenhoeck & Ruprecht`, `Mohr Siebeck`, `Kohlhammer`, `Campus`, `Transcript`,
         `De Gruyter`, `Patmos`, `Kreuz`, `Goldmann`, `Droemer Knaur`, `Schöningh`, `Böhlau`, `Evangelische Verlagsanstalt`,
         `Gütersloher Verlagshaus`, `Aschendorff`, `Klett-Cotta`, `Springer`, `Pustet`, `St. Benno`, `Echter`,
         `Schwabenverlag`, `Alibri`, `Wagenbach`, `Kiepenheuer & Witsch`, `Meiner`, `Metzler`).
      3. Hydrates full `/34` commercial e-books in RAM (`stream_dnb_oa_multi_url_in_ram`) AND concurrently queries
         BOTH `services.dnb.de/plus/idn/{idn}/blurb/` AND `d-nb.info/{idn}/04/text` for every commercial print book
         and DRM-locked `/34` commercial e-book (`_async_hydrate_commercial_dual_blurb_and_toc`), fusing their prose
         and non-reconstructible § 60d UrhG token bags under `corpus_layer = "dnblab_dtf_incopyright"`.
    """
    import asyncio
    import glob
    import hashlib
    import pyarrow as pa
    import pyarrow.parquet as pq

    dnblab_free_idns = load_or_fetch_dnblab_free_idns()

    shard_paths = sorted(
        glob.glob(os.path.join(parquet_dir, "dnb_corpus_part*.parquet")),
        key=lambda x: int(re.search(r"part(\d+)", x).group(1)) if re.search(r"part(\d+)", x) else 9999,
    )
    target_paths = []
    for sp in shard_paths:
        m = re.search(r"part(\d+)", os.path.basename(sp))
        if m:
            s_num = int(m.group(1))
            if start_shard <= s_num <= end_shard:
                target_paths.append((s_num, sp))

    print(
        f"\n[DNBLab In-Copyright Commercial Print & E-Book Incorporator (§ 60d UrhG DTF)] "
        f"Scanning {len(target_paths)} Zstd-19 Parquet shards (part{start_shard:03d}..part{end_shard:03d}, "
        f"commercial_dual_per_shard={max_commercial_per_shard}, oa_34_per_shard={max_oa_34_per_shard})...",
        flush=True,
    )

    comm_pub_re = re.compile(
        r"(herder|suhrkamp|beck|fischer|rowohlt|kösel|gräfe|unzer|vandenhoeck|mohr|kohlhammer|campus|"
        r"transcript|gruyter|patmos|kreuz|goldmann|knaur|schöningh|böhlau|evangelisch|gütersloher|"
        r"aschendorff|klett|springer|pustet|benno|echter|schwabenverlag|alibri|wagenbach|kiepenheuer|meiner|metzler)",
        re.IGNORECASE,
    )
    domain_re = re.compile(
        r"(glaube|gott|kirche|theolog|religi|christ|bibel|islam|jüd|philosoph|ethik|moral|säkular|"
        r"achtsam|meditation|selbsthilfe|lebenshilfe|resilienz|spiritual|seelsorge|liturg|predigt|"
        r"gemeinde|aufklärung|ideolog|gesellschaft|demokrat|psycholog|soziolog|mystik|konzil|papst|"
        r"bischof|pfarrer|buddhis|hinduis|sinn|glück|burnout|coaching|heilung|diskurs|moderne|vernunft)",
        re.IGNORECASE,
    )
    idn_rx = re.compile(r"(?:d-nb\.info/|/idn/|idn=)(\d{8,10}[0-9Xx]?)")
    word_rx = re.compile(r"\b[a-zA-ZäöüÄÖÜß]{4,}\b")

    total_comm_ebooks_34 = 0
    total_comm_ebook_chunks = 0
    total_comm_dual_both = 0
    total_comm_blurbs = 0
    total_comm_tocs = 0
    total_dtf_passages = 0
    total_added_words = 0
    modified_shard_names = []
    overflow_dtf_chunks = []

    def _hydrate_comm_34_item(task_tuple):
        row_idx, idn_str, url = task_tuple
        txt, pages, _ = stream_dnb_oa_multi_url_in_ram([url], max_pages=65)
        if txt and len(txt.split()) >= 90:
            return row_idx, idn_str, txt, pages
        return row_idx, idn_str, "", 0

    for s_num, sp in target_paths:
        sname = os.path.basename(sp)
        t0 = time.time()
        table = pq.read_table(sp, memory_map=False)
        table_schema = table.schema
        cols = {c: table[c].to_pylist() for c in table.column_names}
        n_rows = table.num_rows
        del table

        srcs = cols["source_file"]
        wcs = cols["word_count"]
        pubs = cols["publisher"]
        titles_col = cols["title"]
        texts_col = cols["text"]

        comm_oa_34_cands = []
        comm_dual_cands = []

        for idx in range(n_rows):
            wc = wcs[idx] or 0
            if wc >= 75:
                continue
            pub_val = str(pubs[idx] or "")
            if not pub_val or not comm_pub_re.search(pub_val):
                continue
            u = str(srcs[idx] or "")
            if not u:
                continue
            m_idn = idn_rx.search(u)
            idn_val = m_idn.group(1) if m_idn else ""
            if not idn_val and "deposit.dnb.de" not in u:
                continue
            if idn_val and not idn_val.startswith(("95", "96", "97", "98", "99", "10", "11", "12", "13")):
                continue

            tl_val = str(titles_col[idx] or "")
            tx_val = str(texts_col[idx] or "")[:300]
            has_domain = 0 if (domain_re.search(tl_val) or domain_re.search(tx_val)) else 1
            url_prio = 0 if (u.endswith("/04") or "blurb" in u or "deposit.dnb.de" in u) else (1 if u.endswith("/34") else 2)

            if u.endswith("/34") and (idn_val in dnblab_free_idns or has_domain == 0):
                free_flag = 0 if idn_val in dnblab_free_idns else 1
                comm_oa_34_cands.append(((free_flag, has_domain), idx, idn_val, u))

            comm_dual_cands.append(((has_domain, url_prio), idx, idn_val, u))

        comm_oa_34_cands.sort(key=lambda x: x[0])
        comm_dual_cands.sort(key=lambda x: x[0])

        oa_tasks = [(idx, idn_v, u) for _, idx, idn_v, u in comm_oa_34_cands[:max_oa_34_per_shard]] if max_oa_34_per_shard > 0 else []
        oa_idx_set = {idx for idx, _, _ in oa_tasks}
        dual_tasks = [
            (idx, idn_v, u)
            for _, idx, idn_v, u in comm_dual_cands
            if idx not in oa_idx_set
        ][:max_commercial_per_shard]

        if not oa_tasks and not dual_tasks:
            continue

        shard_34_books = 0
        shard_dual_both = 0
        shard_blurb_only = 0
        shard_toc_only = 0
        shard_words_added = 0

        oa_success_map = {}
        failed_oa_for_dual = []
        if oa_tasks:
            with ThreadPoolExecutor(max_workers=min(workers, max(4, len(oa_tasks)))) as ex:
                futs = {ex.submit(_hydrate_comm_34_item, t): t for t in oa_tasks}
                for fut in as_completed(futs):
                    orig_t = futs[fut]
                    try:
                        r_idx, idn_v, h_txt, pages = fut.result()
                        if h_txt:
                            oa_success_map[r_idx] = (h_txt, pages)
                        else:
                            failed_oa_for_dual.append(orig_t)
                    except Exception:
                        failed_oa_for_dual.append(orig_t)

        # Any DRM-restricted `/34` commercial e-book that returned 403 on `/34` is immediately routed to dual `/blurb/` + `/04/text`!
        all_dual_tasks = failed_oa_for_dual + dual_tasks
        dual_results = []
        if all_dual_tasks:
            dual_results = asyncio.run(
                _async_hydrate_commercial_dual_blurb_and_toc(all_dual_tasks, host_concurrency=85)
            )

        # 1. Process full `/34` commercial e-books -> chunked `dnblab_dtf_incopyright` passages
        for r_idx, (hydrated_txt, pages) in oa_success_map.items():
            old_txt = str(cols["text"][r_idx] or "")
            old_wc = int(cols["word_count"][r_idx] or 0)
            base_title = str(cols["title"][r_idx] or "")
            author_str = str(cols["author"][r_idx] or "")
            pub_str = str(cols["publisher"][r_idx] or "")
            date_str = str(cols["date"][r_idx] or "")
            dec_str = str(cols["decade"][r_idx] or "")
            src_url = str(cols["source_file"][r_idx] or "")

            words_list = hydrated_txt.split()
            chunks = []
            for i in range(0, len(words_list), chunk_words):
                ch_w = words_list[i : i + chunk_words]
                if len(ch_w) >= 90 or (not chunks and len(ch_w) >= 50):
                    chunks.append(" ".join(ch_w))
                if len(chunks) >= max_chunks_per_book:
                    break
            if not chunks:
                continue
            n_ch = len(chunks)
            first_body = f"{chunks[0]} {old_txt}".strip()
            new_wc = len(f"{base_title}. {author_str}. {pub_str}. {first_body}".split())
            if n_ch > 1:
                cols["title"][r_idx] = f"{base_title} [DNBLab-DTF-Vollbuch-Abschnitt 1/{n_ch}]"
            cols["corpus_layer"][r_idx] = "dnblab_dtf_incopyright"
            cols["chunk_index"][r_idx] = 1
            cols["total_chunks"][r_idx] = n_ch
            cols["text"][r_idx] = first_body
            cols["abstract"][r_idx] = chunks[0][:240]
            cols["word_count"][r_idx] = new_wc
            shard_34_books += 1
            total_comm_ebooks_34 += 1
            total_comm_ebook_chunks += n_ch
            total_dtf_passages += n_ch
            shard_words_added += max(0, new_wc - old_wc)

            for c_i in range(2, n_ch + 1):
                ch_txt = chunks[c_i - 1]
                c_wc = len(ch_txt.split())
                shard_words_added += c_wc
                overflow_dtf_chunks.append({
                    "title": f"{base_title} [DNBLab-DTF-Vollbuch-Abschnitt {c_i}/{n_ch}]",
                    "author": author_str,
                    "date": date_str,
                    "decade": dec_str,
                    "publisher": pub_str,
                    "corpus_layer": "dnblab_dtf_incopyright",
                    "source_file": src_url,
                    "chunk_index": c_i,
                    "total_chunks": n_ch,
                    "word_count": c_wc,
                    "abstract": ch_txt[:240],
                    "text": ch_txt,
                })

        # 2. Process dual `/blurb/` + `/04/text` commercial print & DRM e-books -> `dnblab_dtf_incopyright`
        for r_idx, blurb_txt, toc_txt, est_pages in dual_results:
            old_txt = str(cols["text"][r_idx] or "")
            old_wc = int(cols["word_count"][r_idx] or 0)
            base_title = str(cols["title"][r_idx] or "")
            author_str = str(cols["author"][r_idx] or "")
            pub_str = str(cols["publisher"][r_idx] or "")

            if blurb_txt and toc_txt:
                fused = f"[DNBLab § 60d UrhG Commercial Print/E-Book · Klappentext & Inhaltsverzeichnis ({est_pages} S.)] {blurb_txt}. {toc_txt}"
                abs_snip = blurb_txt[:240]
                shard_dual_both += 1
                total_comm_dual_both += 1
                total_comm_blurbs += 1
                total_comm_tocs += 1
            elif blurb_txt:
                fused = f"[DNBLab § 60d UrhG Commercial Print/E-Book · Klappentext] {blurb_txt}"
                abs_snip = blurb_txt[:240]
                shard_blurb_only += 1
                total_comm_blurbs += 1
            else:
                fused = f"[DNBLab § 60d UrhG Commercial Print · Inhaltsverzeichnis ({est_pages} S.)] {toc_txt}"
                abs_snip = toc_txt[:240]
                shard_toc_only += 1
                total_comm_tocs += 1

            # Also append non-reconstructible § 60d UrhG alphabetical content-word DTF bag
            content_words = sorted({w.lower() for w in word_rx.findall(f"{blurb_txt} {toc_txt}")})
            dtf_bag = " ".join(content_words[:180])
            combined_body = f"{fused} {old_txt} {dtf_bag}".strip()
            new_wc = len(f"{base_title}. {author_str}. {pub_str}. {combined_body}".split())

            cols["corpus_layer"][r_idx] = "dnblab_dtf_incopyright"
            cols["text"][r_idx] = combined_body
            cols["abstract"][r_idx] = abs_snip
            cols["word_count"][r_idx] = new_wc
            total_dtf_passages += 1
            shard_words_added += max(0, new_wc - old_wc)

        shard_total_hits = shard_34_books + shard_dual_both + shard_blurb_only + shard_toc_only
        if shard_total_hits > 0:
            new_table = pa.Table.from_pydict(cols, schema=table_schema)
            tmp_sp = sp + ".tmp"
            pq.write_table(
                new_table,
                tmp_sp,
                compression="zstd",
                compression_level=19,
                use_dictionary=["author", "date", "decade", "publisher", "corpus_layer", "source_file"],
                write_statistics=True,
            )
            os.replace(tmp_sp, sp)
            modified_shard_names.append(sname)
            total_added_words += shard_words_added
            elapsed_s = time.time() - t0
            print(
                f"  -> [{sname}] Incorporated +{shard_total_hits} In-Copyright Commercial Books into `dnblab_dtf_incopyright` "
                f"(+{shard_34_books} `/34` E-Books, +{shard_dual_both} Dual Blurb+TOC, +{shard_blurb_only} Blurb, +{shard_toc_only} TOC | "
                f"+{shard_words_added:,} German words in {elapsed_s:.1f}s) | "
                f"Running Total: +{total_dtf_passages:,} DTF passages (+{total_added_words:,} words)",
                flush=True,
            )

        if len(overflow_dtf_chunks) >= 25000:
            new_shard = append_rows_to_zstd_parquet(overflow_dtf_chunks, parquet_dir=parquet_dir, compression_level=19)
            overflow_dtf_chunks = []
            if new_shard and os.path.basename(new_shard) not in modified_shard_names:
                modified_shard_names.append(os.path.basename(new_shard))

    if overflow_dtf_chunks:
        new_shard = append_rows_to_zstd_parquet(overflow_dtf_chunks, parquet_dir=parquet_dir, compression_level=19)
        if new_shard and os.path.basename(new_shard) not in modified_shard_names:
            modified_shard_names.append(os.path.basename(new_shard))

    # Recompute exact SHA-256 and word counts in parquet_manifest.json
    manifest_path = os.path.join(parquet_dir, "parquet_manifest.json")
    all_shards_now = sorted(
        glob.glob(os.path.join(parquet_dir, "dnb_corpus_part*.parquet")),
        key=lambda x: int(re.search(r"part(\d+)", x).group(1)) if re.search(r"part(\d+)", x) else 9999,
    )
    manifest_shards = []
    tot_rows = 0
    tot_words = 0
    tot_bytes = 0
    for sp in all_shards_now:
        sn = os.path.basename(sp)
        sz = os.path.getsize(sp)
        tot_bytes += sz
        t_meta = pq.read_table(sp, columns=["word_count"], memory_map=True)
        r_cnt = t_meta.num_rows
        w_cnt = int(pa.compute.sum(t_meta["word_count"]).as_py() or 0)
        tot_rows += r_cnt
        tot_words += w_cnt
        h = hashlib.sha256()
        with open(sp, "rb") as bf:
            while True:
                blk = bf.read(1024 * 1024)
                if not blk:
                    break
                h.update(blk)
        manifest_shards.append({
            "file": sn,
            "rows": r_cnt,
            "words": w_cnt,
            "size_bytes": sz,
            "size_mb": round(sz / (1024 * 1024), 2),
            "sha256": h.hexdigest(),
        })

    manifest_obj = {
        "format": "Apache Parquet 2.6",
        "compression": "Zstandard (level=19) + Dictionary Encoding + Prefix Deduplication",
        "total_rows": tot_rows,
        "total_words": tot_words,
        "total_shards": len(manifest_shards),
        "total_size_bytes": tot_bytes,
        "total_size_mb": round(tot_bytes / (1024 * 1024), 2),
        "shards": manifest_shards,
    }
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest_obj, mf, indent=2)

    for summary_json_path in ["app/dnb_master_manifest_summary.json", "app/data_summary.json"]:
        if os.path.exists(summary_json_path):
            try:
                with open(summary_json_path, "r", encoding="utf-8") as sf:
                    s_obj = json.load(sf)
                if "total_passages" in s_obj:
                    s_obj["total_passages"] = tot_rows
                    s_obj["total_words"] = tot_words
                    s_obj["dnblab_dtf_incopyright_passages"] = total_dtf_passages
                if "corpus_layers" in s_obj and isinstance(s_obj["corpus_layers"], dict):
                    s_obj["corpus_layers"]["dnblab_dtf_incopyright"] = (
                        int(s_obj["corpus_layers"].get("dnblab_dtf_incopyright", 0)) + total_dtf_passages
                    )
                if "summary" in s_obj and isinstance(s_obj["summary"], dict):
                    s_obj["summary"]["total_documents"] = tot_rows
                    s_obj["summary"]["total_passages"] = tot_rows
                    s_obj["summary"]["total_words"] = tot_words
                    s_obj["summary"]["dnblab_dtf_incopyright_passages"] = total_dtf_passages
                with open(summary_json_path, "w", encoding="utf-8") as sf:
                    json.dump(s_obj, sf, indent=2, ensure_ascii=False)
            except Exception:
                pass

    if upload_updated and modified_shard_names:
        upload_parquet_shards_to_github_release(
            parquet_dir=parquet_dir,
            release_tag=release_tag,
            only_files=modified_shard_names + ["parquet_manifest.json"],
        )

    print(
        f"\n======================================================================\n"
        f"[DNBLab In-Copyright Commercial Print & E-Book Incorporation Complete]\n"
        f"  - Commercial `/34` E-Books Hydrated: +{total_comm_ebooks_34:,} books (+{total_comm_ebook_chunks:,} passages)\n"
        f"  - Commercial Dual (`/blurb/` + `/04/text`) Books: +{total_comm_dual_both:,} books\n"
        f"  - Commercial Publisher Blurbs (`/blurb/` & `deposit.dnb.de`): +{total_comm_blurbs:,} works\n"
        f"  - Commercial Digitized TOCs (`/04/text`): +{total_comm_tocs:,} works\n"
        f"  - Total `dnblab_dtf_incopyright` Passages Added: +{total_dtf_passages:,} (+{total_added_words:,} German words)\n"
        f"  - Updated Corpus Total: {tot_rows:,} passages | {tot_words:,} German words across {len(manifest_shards)} Zstd-19 shards!\n"
        f"======================================================================",
        flush=True,
    )
    return {
        "comm_ebooks_34": total_comm_ebooks_34,
        "comm_dual_both": total_comm_dual_both,
        "comm_blurbs": total_comm_blurbs,
        "comm_tocs": total_comm_tocs,
        "dtf_passages_added": total_dtf_passages,
        "added_words": total_added_words,
        "total_rows": tot_rows,
        "total_words": tot_words,
        "modified_shards": modified_shard_names,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Wave-12 Unfiltered All-Sachgruppen (000-990, B, K, S) Deutsche Nationalbibliothek (DNB) Full-Text Harvester + Zstd Parquet Streamer (1970-2025)"
    )
    parser.add_argument("--workers", type=int, default=48)
    parser.add_argument("--chunk-words", type=int, default=1000)
    parser.add_argument("--max-chunks-per-book", type=int, default=55)
    parser.add_argument("--max-toc-pdfs", type=int, default=6500)
    parser.add_argument("--max-oa-books", type=int, default=1800)
    parser.add_argument("--max-blurbs", type=int, default=15000)
    parser.add_argument("--full-rescan", action="store_true")
    parser.add_argument("--no-merge", action="store_true")
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--export-parquet", action="store_true", help="Compress master corpus into Zstd-19 Apache Parquet shards in data/parquet/")
    parser.add_argument("--parquet-dir", type=str, default="data/parquet", help="Target directory for Zstd-19 Parquet shards")
    parser.add_argument("--opendata-dump", type=str, default=None, help="Path or URL to DNB data.dnb.de/opendata/ MARC21-XML dump (.mrc.xml.gz)")
    parser.add_argument("--skip-records", type=int, default=0, help="Skip first N XML records when resuming a bulk dump")
    parser.add_argument("--uncapped-year-sachgruppe", action="store_true", help="Run uncapped Year x Sachgruppe (5,712 cells) SRU streamer into data/parquet/")
    parser.add_argument("--upload-github-release", action="store_true", help="Upload Zstd Parquet shards to GitHub Release Assets after harvest/export")
    parser.add_argument("--upload-only", action="store_true", help="Upload existing Zstd Parquet shards to GitHub Release Assets and exit")
    parser.add_argument("--release-tag", type=str, default="v12.0-dnb-parquet-shards", help="GitHub Release tag for Zstd Parquet shards")
    parser.add_argument("--online-lda", action="store_true", help="Run Hoffman et al. (2010) Online Streaming LDA over data/parquet/")
    parser.add_argument("--hydrate-parquet-shards", action="store_true", help="Hydrate OpenData Parquet shards with remote d-nb.info/{idn}/34 OA PDFs, /04 TOC PDFs, and deposit.dnb.de blurbs")
    parser.add_argument("--hydrate-start-shard", type=int, default=8)
    parser.add_argument("--hydrate-end-shard", type=int, default=125)
    parser.add_argument("--hydrate-oa-per-shard", type=int, default=35)
    parser.add_argument("--hydrate-toc-per-shard", type=int, default=45)
    parser.add_argument("--hydrate-blurbs-per-shard", type=int, default=120)
    parser.add_argument("--dnblab-dtf-dir", type=str, default=None, help="Convert restricted in-copyright PDFs/EPUBs in a DNBLab folder into a § 60d UrhG Derived Text Format (DTF) Parquet shard")
    parser.add_argument("--dnblab-incopyright-commercial", action="store_true", help="Use DNBLab dual /blurb/ + /04/text + Reihe O /34 endpoints to incorporate In-Copyright Commercial Print & E-Books into data/parquet/ as dnblab_dtf_incopyright")
    parser.add_argument("--commercial-per-shard", type=int, default=650)
    args = parser.parse_args()

    start_t = time.time()

    if args.dnblab_incopyright_commercial:
        start_s = args.hydrate_start_shard if args.hydrate_start_shard != 8 else 40
        incorporate_dnblab_incopyright_commercial_books(
            parquet_dir=args.parquet_dir,
            start_shard=start_s,
            end_shard=args.hydrate_end_shard,
            workers=args.workers,
            max_commercial_per_shard=args.commercial_per_shard,
            max_oa_34_per_shard=args.hydrate_oa_per_shard,
            chunk_words=args.chunk_words,
            max_chunks_per_book=args.max_chunks_per_book,
            upload_updated=args.upload_github_release,
            release_tag=args.release_tag,
        )
        if args.online_lda:
            import lda_pipeline
            lda_pipeline.run_streaming_online_lda_pipeline(args.parquet_dir, num_topics=12)
        return

    if args.dnblab_dtf_dir:
        export_dnblab_restricted_to_dtf_parquet_shard(
            local_object_dir=args.dnblab_dtf_dir,
            parquet_dir=args.parquet_dir,
            chunk_words=args.chunk_words,
            max_chunks_per_book=args.max_chunks_per_book,
        )
        if args.online_lda:
            import lda_pipeline
            lda_pipeline.run_streaming_online_lda_pipeline(args.parquet_dir, num_topics=12)
        return

    if args.hydrate_parquet_shards:
        hydrate_parquet_shards_with_remote_fulltext_and_blurbs(
            parquet_dir=args.parquet_dir,
            start_shard=args.hydrate_start_shard,
            end_shard=args.hydrate_end_shard,
            workers=args.workers,
            max_oa_per_shard=args.hydrate_oa_per_shard,
            max_toc_per_shard=args.hydrate_toc_per_shard,
            max_blurbs_per_shard=args.hydrate_blurbs_per_shard,
            chunk_words=args.chunk_words,
            max_chunks_per_book=args.max_chunks_per_book,
            upload_updated=args.upload_github_release,
            release_tag=args.release_tag,
        )
        return

    if args.opendata_dump:
        stream_dnb_opendata_marc_dump(
            args.opendata_dump,
            parquet_dir=args.parquet_dir,
            upload_incremental=args.upload_github_release,
            release_tag=args.release_tag,
            skip_records=args.skip_records,
        )
        if args.online_lda:
            import lda_pipeline
            lda_pipeline.run_streaming_online_lda_pipeline(args.parquet_dir, num_topics=12)
        return

    if args.uncapped_year_sachgruppe:
        harvest_dnb_uncapped_year_x_sachgruppe(parquet_dir=args.parquet_dir, workers=min(24, args.workers))
        if args.upload_github_release:
            upload_parquet_shards_to_github_release(args.parquet_dir, release_tag=args.release_tag)
        return

    if args.export_parquet:
        import lda_pipeline
        lda_pipeline.save_corpus_to_zstd_parquet(
            data_source="data/dnb_metadata.csv",
            parquet_dir=args.parquet_dir,
            rows_per_shard=85000,
            compression_level=19,
        )
        if args.upload_github_release:
            upload_parquet_shards_to_github_release(args.parquet_dir, release_tag=args.release_tag)
        if args.online_lda:
            lda_pipeline.run_streaming_online_lda_pipeline(args.parquet_dir, num_topics=12)
        return

    if args.upload_only:
        upload_parquet_shards_to_github_release(args.parquet_dir, release_tag=args.release_tag)
        return

    if args.online_lda:
        import lda_pipeline
        lda_pipeline.run_streaming_online_lda_pipeline(args.parquet_dir, num_topics=12)
        return

    dnb_prev = load_all_dnb_shards("data/dnb_metadata.csv")
    if args.manifest_only:
        build_exhaustive_dnb_master_manifest(dnb_prev)
        return

    ckpt_jsonl = "data/primary_texts/dnb_wave12_oa_checkpoint.jsonl"
    if os.path.exists(ckpt_jsonl):
        try:
            os.remove(ckpt_jsonl)
        except Exception:
            pass

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

    already_seen_urls = set()
    already_seen_titles = set()
    already_seen_oa_urls = set()
    already_seen_oa_titles = set()
    if not dnb_prev.empty:
        for u in dnb_prev["source_file"].dropna().unique():
            already_seen_urls.add(str(u).strip())
        for t in dnb_prev["title"].dropna().unique():
            tl = str(t).lower().strip()
            already_seen_titles.add(tl)
            if "[dnb-oa-vollbuch-abschnitt 1/" in tl:
                already_seen_titles.add(tl.split("/")[0] + "/")
                already_seen_oa_titles.add(tl.split("/")[0] + "/")
        oa_rows = dnb_prev[dnb_prev["corpus_layer"] == "dnb_oa_fullbook"]
        for u in oa_rows["source_file"].dropna().unique():
            already_seen_oa_urls.add(str(u).strip())

    print(
        f"Starting Wave-12 Unfiltered All-Sachgruppen (`000-990`, `B`, `K`, `S`) DNB Full-Text Harvest (1970-2025)\n"
        f"  (Existing Corpus: {len(dnb_prev):,} documents | {len(already_seen_oa_titles):,} DNB OA books | {len(already_seen_htids):,} HTRC books)...",
        flush=True,
    )

    new_passages, new_ht_summaries = harvest_dnb_wave7_exhaustive(
        already_seen_htids=already_seen_htids,
        already_matched_isbns=already_matched_isbns,
        already_seen_urls=already_seen_urls,
        already_seen_titles=already_seen_titles,
        already_seen_oa_urls=already_seen_oa_urls,
        already_seen_oa_titles=already_seen_oa_titles,
        workers=args.workers,
        chunk_words=args.chunk_words,
        max_chunks_per_book=args.max_chunks_per_book,
        max_toc_pdfs=args.max_toc_pdfs,
        max_oa_books=args.max_oa_books,
        max_blurbs=args.max_blurbs,
        full_rescan=args.full_rescan,
    )

    if not new_passages:
        print("No new DNB passages discovered beyond existing dataset.", flush=True)
        build_exhaustive_dnb_master_manifest(dnb_prev)
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
    print(f"WAVE-12 UNFILTERED ALL-SACHGRUPPEN DNB HARVEST FINISHED in {elapsed:.1f}s!", flush=True)
    print(f"  - Stream A (Multi-ISBN $a/$z/$9 DNB -> HTRC Full Books): {len(new_ht_summaries)} books ({sum(1 for p in new_passages if p['corpus_layer']=='hathitrust_ef_fullbook_print'):,} passages)", flush=True)
    print(f"  - Stream B (`location=onlinefree` DNB `/34` & `MARC 856` OA PDFs & EPUBs): {sum(1 for p in new_passages if p['corpus_layer']=='dnb_oa_fullbook'):,} passages", flush=True)
    print(f"  - Stream C (Stratified DNB Digitized `/04` `Inhaltsverzeichnis` & Excerpt PDFs/HTMLs): {sum(1 for p in new_passages if p['corpus_layer']=='dnb_toc_pdf_fulltext'):,} documents", flush=True)
    print(f"  - Stream D (Stratified DNB `Inhaltstexte`, Abstracts & Keywords): {sum(1 for p in new_passages if p['corpus_layer']=='dnb_deposit_inhaltstext'):,} documents", flush=True)
    print(f"  - TOTAL NEW UNIQUE DNB DOCUMENTS ADDED IN WAVE 12: {len(new_df):,} ({int(total_new_words):,} German words!)", flush=True)
    print("======================================================================", flush=True)

    if not args.no_merge:
        merged = pd.concat([dnb_prev, new_df], ignore_index=True)
        save_sharded_dnb_corpus(merged, rows_per_shard=24000)
        if os.path.exists(ckpt_jsonl):
            try:
                os.remove(ckpt_jsonl)
            except Exception:
                pass
        total_est_words = pd.to_numeric(merged.get("word_count"), errors="coerce").fillna(950).sum()
        print(
            f"Total Master Corpus Across Shards = {len(merged):,} documents "
            f"(~{int(total_est_words):,} original German words!)",
            flush=True,
        )
        build_exhaustive_dnb_master_manifest(merged)
        import lda_pipeline
        lda_pipeline.save_corpus_to_zstd_parquet(
            data_source="data/dnb_metadata.csv",
            parquet_dir=args.parquet_dir,
            rows_per_shard=85000,
            compression_level=19,
        )
        if args.upload_github_release:
            upload_parquet_shards_to_github_release(args.parquet_dir, release_tag=args.release_tag)


if __name__ == "__main__":
    main()


