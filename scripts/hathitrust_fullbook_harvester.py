import argparse
import glob
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

from scripts.fulltext_ingester import (
    normalize_german_text,
    chunk_fulltext_words,
    _reconstruct_openalex_abstract,
)
from scripts.stream_full_books_cloud import stream_entire_pdf_book_in_ram
from scripts.resolve_catalog_fulltexts import is_clean_modern_german
from scripts.gbv_harvester import BKL_11_LABELS, fetch_blurb_text, fetch_pdf_text_from_url

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HEADERS = {
    "User-Agent": "DeutscheVerlageLDA-Wave9-Harvester/9.0 (JNU Centre for German Studies; mailto:paul@jnu.ac.in)"
}
NS = {"zs": "http://www.loc.gov/zing/srw/", "m": "http://www.loc.gov/MARC21/slim"}

# Core 12 dissertation publishers (Wave 9 deep GBV pagination)
CORE_12_PUBLISHERS = [
    ("Suhrkamp", "Suhrkamp", ["11.*", "08.*", "71.*"]),
    ("Wagenbach", "Wagenbach", ["11.*", "08.*", "71.*"]),
    ("Alibri", "Alibri", ["11.*", "08.*"]),
    ("Rowohlt", "Rowohlt", ["11.*", "08.*", "71.*"]),
    ("Fischer", "Fischer", ["11.*", "08.*", "71.*"]),
    ("Kiepenheuer", "Kiepenheuer", ["11.*", "08.*", "71.*"]),
    ("Klett-Cotta", "Klett", ["11.*", "08.*", "71.*"]),
    ("Gütersloher Verlagshaus", "Gütersloher", ["11.*"]),
    ("Herder", "Herder", ["11.*", "08.*"]),
    ("Evangelische Verlagsanstalt", "Evangelische Verlagsanstalt", ["11.*"]),
    ("Kösel", "Kösel", ["11.*", "08.*"]),
    ("Patmos", "Patmos", ["11.*"]),
]

# Extended German theological, philosophical, and sociological imprints (Wave 9 deep pagination + all 38 imprints)
EXTENDED_GERMAN_RELIGION_PUBLISHERS = [
    ("Herder (Grünewald)", "Grünewald", ["11.*"], 1, 900),
    ("Gütersloher Verlagshaus (Chr. Kaiser)", "Kaiser", ["11.*"], 1, 900),
    ("Herder (Kreuz)", "Kreuz", ["11.*"], 1, 800),
    ("Patmos (Schwabenverlag)", "Schwabenverlag", ["11.*"], 1, 800),
    ("Herder (Benziger)", "Benziger", ["11.*"], 1, 800),
    ("Vandenhoeck & Ruprecht", "Vandenhoeck", ["11.*", "08.*"], 1, 1400),
    ("Mohr Siebeck", "Mohr", ["11.*", "08.*"], 1, 1400),
    ("Kohlhammer", "Kohlhammer", ["11.*", "08.*"], 1, 1400),
    ("C.H. Beck", "Beck", ["11.*", "08.*"], 1, 1200),
    ("Schöningh", "Schöningh", ["11.*", "08.*"], 1, 1200),
    ("Aschendorff", "Aschendorff", ["11.*"], 1, 1100),
    ("Pustet", "Pustet", ["11.*"], 1, 900),
    ("Echter", "Echter", ["11.*"], 1, 900),
    ("Bonifatius", "Bonifatius", ["11.*"], 1, 800),
    ("Neukirchener", "Neukirchener", ["11.*"], 1, 1000),
    ("Calwer", "Calwer", ["11.*"], 1, 800),
    ("Campus", "Campus", ["11.*", "71.*"], 1, 900),
    ("Insel", "Insel", ["11.*", "08.*"], 1, 800),
    ("Meiner", "Meiner", ["11.*", "08.*"], 1, 900),
    ("Wallstein", "Wallstein", ["11.*", "08.*"], 1, 800),
    ("Nomos / Alber", "Alber", ["11.*", "08.*"], 1, 800),
    ("Nomos / Alber", "Nomos", ["11.*", "71.*"], 1, 800),
    ("Wilhelm Fink", "Fink", ["11.*", "08.*"], 1, 700),
    ("Frommann-Holzboog", "Frommann", ["11.*", "08.*"], 1, 700),
    ("Böhlau", "Böhlau", ["11.*"], 1, 900),
    ("Schwabe", "Schwabe", ["11.*", "08.*"], 1, 700),
    ("De Gruyter / Transcript", "Transcript", ["11.*", "71.*"], 1, 900),
    ("De Gruyter / Transcript", "Gruyter", ["11.*", "08.*"], 1, 1200),
    ("Springer Nature (Holtzbrinck)", "Springer", ["11.*", "08.*", "71.*"], 1, 900),
    ("Springer Nature (Holtzbrinck)", "Metzler", ["11.*", "08.*"], 1, 600),
    ("Budrich", "Budrich", ["11.*", "71.*"], 1, 500),
    ("Oekom", "Oekom", ["11.*", "71.*"], 1, 400),
    ("TVZ (Theologischer Verlag Zürich)", "TVZ", ["11.*"], 1, 600),
    ("TVZ (Theologischer Verlag Zürich)", "Theologischer Verlag", ["11.*"], 1, 600),
]

# Wave-9 Direct BKL Subject Subcodes (deep pagination across all 35 subcodes)
WAVE9_BKL_SUBCODES = [
    ("11.00", 1, 600),   # Theologie, Religionswissenschaft: Allgemeines
    ("11.01", 1, 600),   # Geschichte der Religionswissenschaft & Theologie
    ("11.02", 1, 600),   # Philosophie und Theorie der Religion
    ("11.03", 1, 400),   # Methoden und Techniken der religiösen Forschung
    ("11.04", 1, 400),   # Ausbildung, Beruf, Organisationen
    ("11.05", 1, 900),   # Religionssoziologie
    ("11.06", 1, 700),   # Religionspsychologie
    ("11.07", 1, 600),   # Interreligiöse Beziehungen / Religionsethnologie
    ("11.08", 1, 900),   # Religionskritik & Atheismus
    ("11.09", 1, 700),   # Systematische Religionswissenschaft
    ("11.20", 1, 700),   # Nichtchristliche Religionen / Judentum
    ("11.30", 1, 700),   # Judentum / Bibelwissenschaft
    ("11.31", 1, 600),   # Bibeltext, Bibelübersetzungen
    ("11.35", 1, 700),   # Altes Testament
    ("11.40", 1, 700),   # Islam / Neues Testament
    ("11.45", 1, 600),   # Biblische Theologie
    ("11.50", 1, 800),   # Christentum / Kirchengeschichte
    ("11.51", 1, 700),   # Kirchengeschichte, Dogmengeschichte
    ("11.52", 1, 700),   # Konfessionskunde / Mittelalter
    ("11.53", 1, 800),   # Katholische Theologie / Reformation
    ("11.54", 1, 800),   # Evangelische Theologie / Aufklärung
    ("11.55", 1, 800),   # Neuzeitliche Kirchengeschichte / Ostkirchen
    ("11.60", 1, 800),   # Systematische Theologie
    ("11.61", 1, 800),   # Dogmatik, Konfessionskunde
    ("11.62", 1, 800),   # Christliche Ethik
    ("11.63", 1, 600),   # Ökumenische Theologie
    ("11.70", 1, 800),   # Praktische Theologie
    ("11.71", 1, 600),   # Seelsorge, Pastoralpsychologie
    ("11.72", 1, 600),   # Kirchenrecht / Liturgik
    ("11.73", 1, 500),   # Kirchenmusik, Liturgik
    ("11.74", 1, 600),   # Homiletik, Katechetik
    ("11.75", 1, 700),   # Religionspädagogik / Seelsorge
    ("11.76", 1, 600),   # Mission, Ökumene, Diakonie
    ("11.77", 1, 700),   # Religionspädagogik
    ("11.79", 1, 600),   # Staatskirchenrecht
    ("11.80", 1, 700),   # Islam
    ("11.99", 1, 600),   # Neue Religiöse Bewegungen, Esoterik
    ("08.36", 1, 600),   # Philosophische Anthropologie
    ("08.37", 1, 800),   # Religionsphilosophie
    ("08.42", 1, 600),   # Kulturphilosophie
    ("08.44", 1, 700),   # Sozialphilosophie & Kritische Theorie
]

OPENALEX_WAVE9_QUERIES = [
    # RQ2: Neoliberal Self-Optimization, Mindfulness, Spiritual Care & Lifeworld
    "Achtsamkeit Meditation Spiritualität Selbstoptimierung",
    "Lebenskunst Resilienz Selbstsorge Psychologie",
    "Spiritual Care Seelsorge Gesundheit Krankheit",
    "Sinnkrise Burnout Lebenshilfe Ratgeber Religion",
    "Glück Wohlbefinden Positive Psychologie Ethik",
    "Individualisierung Subjektivierung Religion Spätmoderne",
    "Esoterik New Age Alternative Spiritualität",
    "Körper Heilung Ganzheitlichkeit Spiritualität",
    # RQ3: Secularism, Atheism, Humanism, Critique of Religion & Post-Secularism
    "Säkularismus Humanismus Atheismus Religionskritik",
    "Konfessionsfreie Kirchenaustritt Säkularisierung Deutschland",
    "Naturalismus Evolution Wissenschaft Glaube Kritik",
    "Aufklärung Vernunft Ideologiekritik Religion",
    "Postsäkulare Gesellschaft Habermas Öffentliche Religion",
    "Staatskirchenrecht Trennung Staat Kirche Religionsfreiheit",
    "Blasphemie Meinungsfreiheit Kunstfreiheit Religion",
    # RQ1 & Cross-Cutting Theological, Philosophical & Sociological Domains
    "Religion Säkularisierung Moderne",
    "Theologie Kirche Seelsorge Gesellschaft",
    "Katholizismus Evangelische Kirche Deutschland",
    "Religionssoziologie Glauben Wissen",
    "Gottesfrage Christentum Moderne",
    "Ethik Moral Religion Gesellschaft",
    "Islam Judentum Christentum Dialog",
    "Kirchenmitgliedschaft Konfessionslosigkeit",
    "Mystik Kontemplation Frömmigkeit",
    "Religionspädagogik Religionsunterricht Bildung",
    "Fundamentalismus Toleranz Gewalt Religion",
    "Systematische Theologie Dogmatik",
    "Bibel Exegese Hermeneutik",
    "Liturgie Gottesdienst Sakramente",
    "Diakonie Caritas Sozialethik",
    "Reformation Ökumene Kirchengeschichte",
    "Religionsphilosophie Metaphysik Transzendenz",
    # High-Yield Broad Domain Queries (for multi-page abstract & OA PDF harvesting)
    "Theologie OR Religionswissenschaft OR Kirchengeschichte",
    "Religionsphilosophie OR Religionssoziologie OR Säkularisierung",
    "Religionskritik OR Kirchenkritik OR Atheismus OR Säkularismus",
    "Seelsorge OR Religionspädagogik OR Praktische Theologie",
    "Dogmatik OR Christologie OR Ekklesiologie OR Liturgie",
    "Sozialethik OR Medizinethik OR Bioethik OR Wirtschaftsethik",
    "Bibelwissenschaft OR Altes Testament OR Neues Testament",
    "Spiritualität OR Achtsamkeit OR Mystik OR Frömmigkeit",
]

EN_MARKERS = {"the", "and", "for", "that", "with", "from", "this", "which", "their", "have", "were", "been"}
DE_MARKERS = {"der", "die", "das", "und", "nicht", "ist", "von", "mit", "auf", "für", "eine", "einer", "einem", "sich", "auch", "werden"}

HTRC_FUNCTION_STOPWORDS = {
    "der", "die", "das", "und", "in", "von", "mit", "den", "des", "dem", "für", "auf",
    "nicht", "als", "auch", "sich", "aus", "dass", "daß", "er", "es", "sie", "bei", "nach",
    "um", "am", "im", "zum", "zur", "über", "durch", "vor", "wird", "werden", "wurde",
    "wurden", "hat", "haben", "hatte", "hatten", "war", "waren", "sind", "ist", "sein",
    "seine", "seiner", "seinem", "seinen", "ihr", "ihre", "ihrer", "ihrem", "ihren",
    "eine", "einer", "einem", "einen", "eines", "ein", "oder", "aber", "noch", "wie",
    "nur", "so", "wir", "was", "wenn", "man", "kann", "können", "konnte", "muss",
    "müssen", "soll", "sollen", "will", "wollen", "schon", "immer", "wieder", "mehr",
    "bis", "unter", "gegen", "zwischen", "ohne", "seit", "vom", "ins", "ans", "aufs",
    "diese", "dieser", "diesem", "diesen", "dieses", "jede", "jeder", "jedem", "jeden"
}


def is_german_passage(text: str, min_words: int = 25) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    words = [w.lower() for w in re.findall(r"\b[a-zA-ZäöüÄÖÜß]{3,}\b", text[:6000])]
    if len(words) < min_words:
        return False
    en_cnt = sum(1 for w in words if w in EN_MARKERS)
    de_cnt = sum(1 for w in words if w in DE_MARKERS)
    return de_cnt >= max(4 if min_words < 25 else 8, en_cnt * 2)


def isbn_variants(raw_isbn: str) -> list[str]:
    clean = re.sub(r"[^0-9Xx]", "", str(raw_isbn)).upper()
    if not clean:
        return []
    out = [clean]
    if len(clean) == 10:
        core = "978" + clean[:9]
        if core.isdigit():
            s = sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(core))
            chk = (10 - (s % 10)) % 10
            out.append(core + str(chk))
    elif len(clean) == 13 and clean.startswith("978"):
        core = clean[3:12]
        if core.isdigit():
            s = sum((10 - i) * int(d) for i, d in enumerate(core))
            rem = (11 - (s % 11)) % 11
            chk = "X" if rem == 10 else str(rem)
            out.append(core + chk)
    return list(dict.fromkeys(out))


def canonicalize_gbv_publisher(raw_pub: str, fallback: str = None) -> str:
    if fallback:
        return fallback
    p = (raw_pub or "").lower()
    mapping = [
        ("suhrkamp", "Suhrkamp"),
        ("insel", "Insel"),
        ("herder", "Herder"),
        ("grünewald", "Herder (Grünewald)"),
        ("kreuz", "Herder (Kreuz)"),
        ("benziger", "Herder (Benziger)"),
        ("gütersloher", "Gütersloher Verlagshaus"),
        ("kaiser", "Gütersloher Verlagshaus (Chr. Kaiser)"),
        ("kösel", "Kösel"),
        ("patmos", "Patmos"),
        ("schwabenverlag", "Patmos (Schwabenverlag)"),
        ("evangelische verlagsanstalt", "Evangelische Verlagsanstalt"),
        ("rowohlt", "Rowohlt"),
        ("fischer", "Fischer"),
        ("kiepenheuer", "Kiepenheuer"),
        ("klett", "Klett-Cotta"),
        ("wagenbach", "Wagenbach"),
        ("alibri", "Alibri"),
        ("vandenhoeck", "Vandenhoeck & Ruprecht"),
        ("mohr", "Mohr Siebeck"),
        ("siebeck", "Mohr Siebeck"),
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
        ("meiner", "Meiner"),
        ("wallstein", "Wallstein"),
        ("nomos", "Nomos / Alber"),
        ("alber", "Nomos / Alber"),
        ("fink", "Wilhelm Fink"),
        ("frommann", "Frommann-Holzboog"),
        ("böhlau", "Böhlau"),
        ("schwabe", "Schwabe"),
        ("transcript", "De Gruyter / Transcript"),
        ("gruyter", "De Gruyter / Transcript"),
        ("springer", "Springer Nature (Holtzbrinck)"),
        ("metzler", "Springer Nature (Holtzbrinck)"),
        ("budrich", "Budrich"),
        ("oekom", "Oekom"),
        ("tvz", "TVZ (Theologischer Verlag Zürich)"),
        ("theologischer verlag", "TVZ (Theologischer Verlag Zürich)"),
    ]
    for needle, canon in mapping:
        if needle in p:
            return canon
    return normalize_german_text(raw_pub) if raw_pub else "German Academic Monograph (GBV)"


def harvest_gbv_wave9_and_multi_isbns(
    already_matched_isbns: set[str],
    already_seen_urls: set[str],
    existing_titles: set[str],
    workers: int = 12
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Wave-9 Complete GBV / K10plus SRU Harvester:
      1. Queries deep pagination (maximumRecords=100) across all 38 publishers and 41 BKL subject subcodes.
      2. Extracts ALL MARC 020 ($a, $z, $9) ISBNs per record (multi-ISBN resolution) for HathiTrust HTRC.
      3. Preserves and harvests ALL unseen GBV K10plus records containing:
         - Stream GBV-OA: MARC 856 $z='kostenfrei' / 'Open Access' PDFs (`gbv_kostenfrei_fullbook_pdf`)
         - Stream GBV-TOC/Blurb: MARC 856 $3='Inhaltsverzeichnis' / 'Inhaltstext' (`gbv_direct_fulltext_pdf`)
         - Stream GBV-Paratext: MARC 520 Abstracts + Series + BKL + RVK + Schlagwörter (`gbv_k10plus_paratext`)
    """
    books_for_htrc = []
    gbv_oa_candidates = []
    gbv_toc_blurb_candidates = []
    gbv_paratext_rows = []

    seen_isbns = set(already_matched_isbns)
    seen_ppns = set()
    seen_urls = set(already_seen_urls)
    seen_titles = set(existing_titles)

    all_tasks = []
    # Comprehensive German-language (pica.spr=ger) queries across all 38 target publishers (unrestricted by BKL subject)
    for canonical_pub, gbv_term, bkl_list in CORE_12_PUBLISHERS:
        for start_rec in range(1, 1501, 100):
            all_tasks.append((canonical_pub, f'pica.ver="{gbv_term}" and pica.spr=ger', "all", start_rec))
        for bkl in bkl_list:
            s_start = 1
            s_end = 1500 if bkl == "11.*" else 700
            for start_rec in range(s_start, s_end + 1, 100):
                all_tasks.append((canonical_pub, f'pica.bkl={bkl} and pica.ver="{gbv_term}" and pica.spr=ger', bkl, start_rec))

    for canonical_pub, gbv_term, bkl_list, s_start, s_end in EXTENDED_GERMAN_RELIGION_PUBLISHERS:
        for start_rec in range(1, min(1000, s_end) + 1, 100):
            all_tasks.append((canonical_pub, f'pica.ver="{gbv_term}" and pica.spr=ger', "all", start_rec))
        for bkl in bkl_list:
            for start_rec in range(s_start, s_end + 1, 100):
                all_tasks.append((canonical_pub, f'pica.bkl={bkl} and pica.ver="{gbv_term}" and pica.spr=ger', bkl, start_rec))

    for bkl_code, s_start, s_end in WAVE9_BKL_SUBCODES:
        for start_rec in range(s_start, s_end + 1, 100):
            all_tasks.append((None, f'pica.bkl={bkl_code} and pica.spr=ger', bkl_code, start_rec))

    print(
        f"Wave-9 GBV K10plus Complete Harvester: Querying {len(all_tasks)} SRU pages (maximumRecords=100) "
        f"across 38 publishers & 41 BKL subject codes...",
        flush=True
    )

    lock = threading.Lock()

    def _fetch_sru_page(task):
        canonical_pub, q, bkl, start_rec = task
        page_htrc = []
        page_oa = []
        page_toc = []
        page_para = []
        try:
            r = requests.get(
                "https://sru.k10plus.de/gvk",
                params={
                    "version": "1.1",
                    "operation": "searchRetrieve",
                    "query": q,
                    "startRecord": str(start_rec),
                    "maximumRecords": "100",
                    "recordSchema": "marcxml"
                },
                headers=HEADERS,
                verify=False,
                timeout=18
            )
            if r.status_code != 200:
                return page_htrc, page_oa, page_toc, page_para
            root = ET.fromstring(r.content)
            records = root.findall(".//zs:recordData/m:record", NS)
            for rec in records:
                f001 = rec.find("m:controlfield[@tag='001']", NS)
                ppn = f001.text.strip() if (f001 is not None and f001.text) else ""

                # Publication year (1970-2025)
                year = ""
                for f264 in rec.findall("m:datafield[@tag='264']", NS) + rec.findall("m:datafield[@tag='260']", NS):
                    sc = f264.find("m:subfield[@code='c']", NS)
                    if sc is not None and sc.text:
                        ym = re.search(r"(19[789]\d|20[012]\d)", sc.text)
                        if ym:
                            year = ym.group(1)
                            break
                if not year:
                    f008 = rec.find("m:controlfield[@tag='008']", NS)
                    if f008 is not None and f008.text and len(f008.text) >= 11:
                        y08 = f008.text[7:11]
                        if re.match(r"^(19[789]\d|20[012]\d)$", y08):
                            year = y08
                if not year:
                    continue

                # Title & Subtitle
                title_parts = []
                f245 = rec.find("m:datafield[@tag='245']", NS)
                if f245 is not None:
                    for code in ("a", "b"):
                        sub = f245.find(f"m:subfield[@code='{code}']", NS)
                        if sub is not None and sub.text:
                            title_parts.append(sub.text.strip())
                title = normalize_german_text(": ".join(title_parts))
                if not title or len(title) < 4:
                    continue

                # Author / Editor
                author = "o. V."
                for tag in ("100", "700"):
                    fa = rec.find(f"m:datafield[@tag='{tag}']", NS)
                    if fa is not None:
                        sa = fa.find("m:subfield[@code='a']", NS)
                        if sa is not None and sa.text:
                            author = normalize_german_text(sa.text.strip())
                            break

                # Publisher
                raw_pub = ""
                for f264 in rec.findall("m:datafield[@tag='264']", NS) + rec.findall("m:datafield[@tag='260']", NS):
                    sb = f264.find("m:subfield[@code='b']", NS)
                    if sb is not None and sb.text:
                        raw_pub = normalize_german_text(sb.text.strip())
                        break
                pub_name = canonicalize_gbv_publisher(raw_pub, fallback=canonical_pub)

                # Extract ALL MARC 020 ISBNs ($a, $z, $9) for multi-ISBN HTRC resolution
                record_isbns = []
                for f020 in rec.findall("m:datafield[@tag='020']", NS):
                    for code in ("a", "z", "9"):
                        for sub in f020.findall(f"m:subfield[@code='{code}']", NS):
                            if sub is not None and sub.text:
                                cand = re.sub(r"[^0-9Xx]", "", sub.text.split()[0]).upper()
                                if len(cand) in (10, 13) and cand not in record_isbns:
                                    record_isbns.append(cand)

                for isbn_val in record_isbns:
                    page_htrc.append({
                        "title": title,
                        "author": author,
                        "publisher": pub_name,
                        "date": year,
                        "decade": f"{year[:3]}0s",
                        "isbn": isbn_val,
                        "ppn": ppn,
                        "bkl_codes": bkl.replace(".*", ".00")
                    })

                # Extract Series (490), Abstracts (520), BKL/RVK (084), Keywords (650/653/689), and URLs (856)
                series = ""
                f490 = rec.find("m:datafield[@tag='490']/m:subfield[@code='a']", NS)
                if f490 is not None and f490.text:
                    series = normalize_german_text(f490.text)

                abstracts_520 = []
                for f520 in rec.findall("m:datafield[@tag='520']", NS):
                    sa = f520.find("m:subfield[@code='a']", NS)
                    if sa is not None and sa.text:
                        abstracts_520.append(normalize_german_text(sa.text))

                bkl_labels = []
                bkl_codes = []
                for f084 in rec.findall("m:datafield[@tag='084']", NS):
                    sa = f084.find("m:subfield[@code='a']", NS)
                    s2 = f084.find("m:subfield[@code='2']", NS)
                    if sa is not None and sa.text and s2 is not None and s2.text:
                        if s2.text.strip().lower() == "bkl":
                            c_val = sa.text.strip()
                            bkl_codes.append(c_val)
                            if c_val in BKL_11_LABELS:
                                bkl_labels.append(BKL_11_LABELS[c_val])

                keywords = []
                for tag in ("650", "653", "689"):
                    for fk in rec.findall(f"m:datafield[@tag='{tag}']", NS):
                        for sa in fk.findall("m:subfield[@code='a']", NS):
                            if sa is not None and sa.text:
                                kw = normalize_german_text(sa.text)
                                if kw.startswith(("(", "ISIL", "Produktform")):
                                    continue
                                if kw and kw not in keywords:
                                    keywords.append(kw)
                for lbl in bkl_labels:
                    if lbl not in keywords:
                        keywords.append(lbl)

                blurb_url = ""
                toc_url = ""
                oa_url = ""
                for f856 in rec.findall("m:datafield[@tag='856']", NS):
                    su = f856.find("m:subfield[@code='u']", NS)
                    s3 = f856.find("m:subfield[@code='3']", NS)
                    sz = f856.find("m:subfield[@code='z']", NS)
                    if su is not None and su.text:
                        u_val = su.text.strip()
                        # Skip DNB links since DNB was already exhaustively harvested in Wave 8
                        if "d-nb.info" in u_val.lower() or "deposit.dnb.de" in u_val.lower():
                            continue
                        l3 = s3.text.lower() if (s3 is not None and s3.text) else ""
                        lz = sz.text.lower() if (sz is not None and sz.text) else ""
                        if ("kostenfrei" in lz or "open access" in lz or "kostenfrei" in l3) and not oa_url:
                            oa_url = u_val
                        elif "inhaltsverzeichnis" in l3 and not toc_url:
                            toc_url = u_val
                        elif ("inhaltstext" in l3 or "klappentext" in l3 or "beschreibung" in l3) and not blurb_url:
                            blurb_url = u_val

                base_meta = {
                    "ppn": ppn,
                    "title": title,
                    "author": author,
                    "publisher": pub_name,
                    "date": year,
                    "decade": f"{year[:3]}0s",
                    "series": series,
                    "keywords": ", ".join(keywords),
                    "abstract_520": " ".join(abstracts_520),
                }

                if oa_url:
                    c_oa = dict(base_meta)
                    c_oa["oa_url"] = oa_url
                    page_oa.append(c_oa)
                if toc_url or blurb_url:
                    c_toc = dict(base_meta)
                    c_toc["toc_url"] = toc_url
                    c_toc["blurb_url"] = blurb_url
                    page_toc.append(c_toc)

                # Paratextual record if it has MARC 520 or rich German semantic descriptors
                para_segments = [s for s in [title, series, " ".join(abstracts_520), ", ".join(keywords)] if s]
                para_text = ". ".join(para_segments)
                if abstracts_520 or (len(keywords) >= 2 and is_german_passage(para_text, min_words=10)):
                    page_para.append({
                        "title": title,
                        "author": author,
                        "date": year,
                        "decade": f"{year[:3]}0s",
                        "publisher": pub_name,
                        "corpus_layer": "gbv_direct_fulltext_pdf" if abstracts_520 else "drm_fallback_multi_api_enriched",
                        "source_file": f"https://opac.k10plus.de/DB=2.299/PPNSET?PPN={ppn}",
                        "chunk_index": 1,
                        "total_chunks": 1,
                        "word_count": len(para_text.split()),
                        "keywords": ", ".join(keywords),
                        "abstract": (" ".join(abstracts_520) or para_text)[:420],
                        "text": para_text,
                        "ppn": ppn,
                    })
        except Exception:
            pass
        return page_htrc, page_oa, page_toc, page_para

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_fetch_sru_page, t) for t in all_tasks]
        for fut in as_completed(futs):
            p_htrc, p_oa, p_toc, p_para = fut.result()
            with lock:
                for b in p_htrc:
                    variants = isbn_variants(b["isbn"])
                    if any(v in seen_isbns for v in variants):
                        continue
                    for v in variants:
                        seen_isbns.add(v)
                    books_for_htrc.append(b)
                for c in p_oa:
                    if c["oa_url"] not in seen_urls:
                        seen_urls.add(c["oa_url"])
                        gbv_oa_candidates.append(c)
                for c in p_toc:
                    u_key = c["toc_url"] or c["blurb_url"]
                    if u_key and u_key not in seen_urls:
                        seen_urls.add(u_key)
                        gbv_toc_blurb_candidates.append(c)
                for r in p_para:
                    t_norm = r["title"].lower().strip()
                    if r["ppn"] not in seen_ppns and t_norm not in seen_titles:
                        seen_ppns.add(r["ppn"])
                        seen_titles.add(t_norm)
                        r_clean = {k: v for k, v in r.items() if k != "ppn"}
                        gbv_paratext_rows.append(r_clean)

    print(
        f"  -> GBV K10plus Harvest Summary:\n"
        f"     * {len(books_for_htrc):,} NEW multi-ISBN candidates queued for HathiTrust HTRC lookup\n"
        f"     * {len(gbv_oa_candidates):,} NEW GBV Open-Access PDFs queued for in-RAM streaming\n"
        f"     * {len(gbv_toc_blurb_candidates):,} NEW GBV Consortial TOC PDFs / Blurbs queued\n"
        f"     * {len(gbv_paratext_rows):,} NEW GBV K10plus MARC 520 & BKL/GND enriched records extracted",
        flush=True
    )

    gbv_streamed_rows = list(gbv_paratext_rows)

    # Stream GBV Open-Access PDFs in RAM
    def _process_gbv_oa(c):
        txt, _ = stream_entire_pdf_book_in_ram(c["oa_url"], max_pages=180)
        if not txt or len(txt.split()) < 250 or not is_german_passage(txt, min_words=25):
            return []
        chunks = [ch for ch in chunk_fulltext_words(txt, chunk_words=1000) if is_german_passage(ch, min_words=25)]
        out = []
        for idx, ch in enumerate(chunks[:45], start=1):
            compact_ch = " ".join(ch.split()[:420])
            out.append({
                "title": f"{c['title']} [GBV-OA-Vollbuch Abschnitt {idx}/{min(len(chunks), 45)}]",
                "author": c["author"],
                "date": c["date"],
                "decade": c["decade"],
                "publisher": c["publisher"],
                "corpus_layer": "gbv_kostenfrei_fullbook_pdf",
                "source_file": c["oa_url"],
                "chunk_index": idx,
                "total_chunks": min(len(chunks), 45),
                "word_count": len(ch.split()),
                "keywords": c.get("keywords", ""),
                "abstract": compact_ch[:240],
                "text": f"{c['title']}. {compact_ch}" if idx == 1 else compact_ch,
            })
        return out

    if gbv_oa_candidates:
        print(f"Streaming {len(gbv_oa_candidates):,} GBV K10plus Open-Access PDFs in RAM...", flush=True)
        with ThreadPoolExecutor(max_workers=min(workers, 10)) as ex:
            for fut in as_completed([ex.submit(_process_gbv_oa, c) for c in gbv_oa_candidates[:600]]):
                res = fut.result()
                if res:
                    gbv_streamed_rows.extend(res)

    # Stream GBV Consortial TOC PDFs and Blurbs in RAM
    def _process_gbv_toc(c):
        toc_txt = fetch_pdf_text_from_url(c["toc_url"], max_pages=12) if c.get("toc_url") else ""
        blurb_txt = fetch_blurb_text(c["blurb_url"]) if c.get("blurb_url") else ""
        combined = " ".join(s for s in [c.get("abstract_520", ""), blurb_txt, toc_txt, c.get("keywords", "")] if s).strip()
        if len(combined.split()) < 20 or not is_german_passage(combined, min_words=15):
            return None
        return {
            "title": f"{c['title']} [GBV-Inhaltsverzeichnis & Paratext]",
            "author": c["author"],
            "date": c["date"],
            "decade": c["decade"],
            "publisher": c["publisher"],
            "corpus_layer": "gbv_direct_fulltext_pdf",
            "source_file": c.get("toc_url") or c.get("blurb_url"),
            "chunk_index": 1,
            "total_chunks": 1,
            "word_count": len(combined.split()),
            "keywords": c.get("keywords", ""),
            "abstract": combined[:360],
            "text": f"{c['title']}. {combined}",
        }

    if gbv_toc_blurb_candidates:
        print(f"Streaming {len(gbv_toc_blurb_candidates):,} GBV Consortial TOC PDFs & Blurbs in RAM...", flush=True)
        with ThreadPoolExecutor(max_workers=min(workers, 12)) as ex:
            for fut in as_completed([ex.submit(_process_gbv_toc, c) for c in gbv_toc_blurb_candidates[:2500]]):
                res = fut.result()
                if res:
                    gbv_streamed_rows.append(res)

    return pd.DataFrame(books_for_htrc), pd.DataFrame(gbv_streamed_rows)


def batch_resolve_hathitrust_volumes(
    books_df: pd.DataFrame,
    already_seen_htids: set[str],
    batch_size: int = 15,
    workers: int = 12
) -> list[dict]:
    if books_df.empty:
        return []
    valid_rows = [row for _, row in books_df.iterrows() if str(row.get("isbn") or "").strip()]
    batches = [valid_rows[i:i + batch_size] for i in range(0, len(valid_rows), batch_size)]

    matched_books = []
    seen_htids = set(already_seen_htids)
    lock = threading.Lock()

    def _query_batch(batch_rows):
        local_matches = []
        isbn_map = {}
        query_parts = []
        for row in batch_rows:
            for v in isbn_variants(row["isbn"]):
                isbn_map[f"isbn:{v}"] = row
                query_parts.append(f"isbn:{v}")
        if not query_parts:
            return local_matches

        url = "https://catalog.hathitrust.org/api/volumes/brief/json/" + "|".join(query_parts)
        try:
            r = requests.get(url, headers=HEADERS, verify=False, timeout=20)
            if r.status_code != 200:
                return local_matches
            data = r.json()
            matched_titles_in_batch = set()
            for key, val in data.items():
                if not val or not val.get("items"):
                    continue
                row = isbn_map.get(key)
                if row is None:
                    continue
                row_key = f"{row['title']}_{row['date']}"
                if row_key in matched_titles_in_batch:
                    continue
                htids = [it.get("htid") for it in val.get("items", []) if it.get("htid")]
                if htids:
                    matched_titles_in_batch.add(row_key)
                    rec = dict(row)
                    rec["htids"] = htids
                    local_matches.append(rec)
        except Exception:
            pass
        return local_matches

    print(f"Batch-querying HathiTrust Bibliographic API across {len(valid_rows):,} Wave-9 multi-ISBNs ({len(batches)} batches)...", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_query_batch, b) for b in batches]
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                with lock:
                    for item in res:
                        unique_htids = [h for h in item["htids"] if h not in seen_htids]
                        if unique_htids:
                            for h in unique_htids:
                                seen_htids.add(h)
                            item["htids"] = unique_htids
                            matched_books.append(item)

    print(f"  -> Matched {len(matched_books):,} NEW Wave-9 in-copyright 1970-2025 printed German books in HathiTrust!", flush=True)
    return matched_books


def extract_htrc_book_passages(
    book_meta: dict,
    chunk_words: int = 1000,
    max_chunks_per_book: int = 75
) -> tuple[list[dict], dict]:
    title = book_meta["title"]
    author = book_meta["author"]
    publisher = book_meta["publisher"]
    year = str(book_meta["date"])
    decade = book_meta["decade"]

    for htid in book_meta.get("htids", []):
        url = f"https://data.htrc.illinois.edu/ef-api/volumes/{htid}"
        try:
            r = requests.get(url, headers=HEADERS, verify=False, timeout=25)
            if r.status_code != 200:
                continue
            payload = r.json()
            pages = payload.get("data", {}).get("features", {}).get("pages", [])
            if not pages or len(pages) < 15:
                continue

            book_words = []
            for pg in pages:
                body = pg.get("body") or {}
                tpc = body.get("tokenPosCount") or {}
                if not tpc:
                    continue
                page_tokens = []
                for tok, pos_dict in tpc.items():
                    clean_tok = tok.strip()
                    if len(clean_tok) < 3 or not re.match(r"^[a-zA-ZäöüÄÖÜß\-]+$", clean_tok):
                        continue
                    total_cnt = sum(int(c) for c in pos_dict.values() if isinstance(c, (int, float)))
                    for _ in range(min(total_cnt, 10)):
                        page_tokens.append(clean_tok)
                if len(page_tokens) >= 20:
                    book_words.extend(page_tokens)

            if len(book_words) < 2500:
                continue

            max_words = max_chunks_per_book * chunk_words
            if len(book_words) > max_words:
                step = len(book_words) / max_words
                book_words = [book_words[int(i * step)] for i in range(max_words)]

            full_text = " ".join(book_words)
            if not is_german_passage(full_text):
                continue

            chunks = [c for c in chunk_fulltext_words(full_text, chunk_words=chunk_words) if is_german_passage(c)]
            if not chunks:
                continue

            passages = []
            source_link = f"https://babel.hathitrust.org/cgi/pt?id={htid}"
            for idx, chunk_str in enumerate(chunks, start=1):
                substantive = [w for w in chunk_str.split() if w.lower() not in HTRC_FUNCTION_STOPWORDS][:330]
                compact_chunk = " ".join(substantive)
                # Santana et al. (2025, DHQ 19.2 §55): Do not inject author/publisher metadata into text body
                passages.append({
                    "title": f"{title} [HTRC-Vollbuch-Abschnitt {idx}/{len(chunks)}]",
                    "author": author,
                    "date": year,
                    "decade": decade,
                    "publisher": publisher,
                    "corpus_layer": "hathitrust_ef_fullbook_print",
                    "source_file": source_link,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "word_count": len(chunk_str.split()),
                    "abstract": compact_chunk[:240],
                    "text": f"{title}. {compact_chunk}" if idx == 1 else compact_chunk
                })

            summary = {
                "htid": htid,
                "title": title,
                "author": author,
                "publisher": publisher,
                "date": year,
                "isbn": book_meta.get("isbn", ""),
                "pages": len(pages),
                "extracted_words": sum(p["word_count"] for p in passages),
                "passages": len(passages),
                "source_url": source_link
            }
            return passages, summary
        except Exception:
            continue

    return [], {}


def harvest_openalex_wave9_corpus(
    already_seen_urls: set[str],
    existing_titles: set[str],
    chunk_words: int = 1000,
    max_chunks_per_book: int = 55,
    workers: int = 10
) -> pd.DataFrame:
    """
    Wave-9 Complete OpenAlex Harvester (within OpenAlex's 100-request / $0.10 free daily budget):
      Uses `per-page=200` across 80 high-yield requests (`has_abstract:true` and `is_oa:true`)
      to harvest:
        1. Reconstructed German scholarly abstracts (`abstract_inverted_index` -> `primary_cloud_oa_abstract`)
        2. Uncapped Open-Access German PDFs (`pdf_url` -> `entire_fulltext_book_cloud` / `primary_cloud_oa_fulltext`)
    """
    print(
        f"\nWave-9 OpenAlex Complete Harvester: Querying 80 high-density `per-page=200` pages "
        f"(Reconstructed German `abstract_inverted_index` + Uncapped OA PDFs)...",
        flush=True
    )
    abstract_rows = []
    pdf_candidates = []
    seen_ids = set()
    seen_urls = set(already_seen_urls)
    seen_titles = set(existing_titles)

    # Build 80 high-yield OpenAlex API calls (each returning 200 German works = up to 16,000 works)
    api_calls = []
    for q_idx, q in enumerate(OPENALEX_WAVE9_QUERIES):
        # 1 page of has_abstract:true (200 abstracts) for all 40 queries = 40 calls
        api_calls.append(("language:de,publication_year:1970-2025,has_abstract:true", q, 1))
        # Pages 2..4 for the 8 broad high-yield domain queries = 24 calls
        if q_idx >= 32:
            for p_num in (2, 3, 4):
                api_calls.append(("language:de,publication_year:1970-2025,has_abstract:true", q, p_num))
        # Direct OA book/chapter PDF queries for the first 16 queries = 16 calls
        if q_idx < 16:
            api_calls.append(("language:de,is_oa:true,type:book|book-chapter,publication_year:1970-2025", q, 1))

    for oa_filter, q, page_num in api_calls[:82]:
        try:
            r = requests.get(
                "https://api.openalex.org/works",
                params={
                    "filter": oa_filter,
                    "search": q,
                    "per-page": 200,
                    "page": page_num
                },
                headers=HEADERS,
                verify=False,
                timeout=15
            )
            if r.status_code != 200:
                continue
            for work in r.json().get("results", []):
                wid = work.get("id")
                if not wid or wid in seen_ids:
                    continue

                title = normalize_german_text(work.get("title") or "")
                if not title or len(title) < 5:
                    continue
                t_norm = title.lower().strip()
                year = str(work.get("publication_year") or "2018")[:4]
                if not year.isdigit() or int(year) < 1970 or int(year) > 2025:
                    continue
                decade = f"{year[:3]}0s"

                authorships = work.get("authorships") or []
                author = "o. V."
                if authorships:
                    a_name = (authorships[0].get("author") or {}).get("display_name")
                    if a_name:
                        author = normalize_german_text(a_name)

                loc = work.get("primary_location") or {}
                src = loc.get("source") or {}
                raw_pub = normalize_german_text(
                    src.get("host_organization_name") or src.get("display_name") or "Open Access (DE)"
                )
                best_oa = work.get("best_oa_location") or {}
                oa_info = work.get("open_access") or {}
                pdf_url = best_oa.get("pdf_url") or oa_info.get("oa_url") or ""

                publisher = canonicalize_gbv_publisher(raw_pub)
                if publisher == "German Academic Monograph (GBV)":
                    publisher = raw_pub or "Open Access (DE)"
                if "springer" in publisher.lower() or "link.springer.com" in pdf_url.lower():
                    publisher = "Springer Nature (Holtzbrinck)"
                elif "degruyter" in pdf_url.lower() or "10.1515" in pdf_url.lower():
                    publisher = "De Gruyter / Transcript"
                elif "vr-elibrary" in pdf_url.lower() or "10.13109" in pdf_url.lower():
                    publisher = "Vandenhoeck & Ruprecht"
                elif "nomos" in pdf_url.lower() or "10.5771" in pdf_url.lower():
                    publisher = "Nomos / Alber"

                seen_ids.add(wid)

                # Extract concepts/topics as keywords
                concepts = [
                    normalize_german_text(c.get("display_name"))
                    for c in (work.get("concepts") or [])[:6]
                    if c.get("display_name")
                ]
                kw_str = ", ".join(concepts)

                # 1. Reconstruct German scholarly abstract from abstract_inverted_index
                inv_idx = work.get("abstract_inverted_index")
                if inv_idx and wid not in seen_urls and t_norm not in seen_titles:
                    abs_text = _reconstruct_openalex_abstract(inv_idx)
                    if len(abs_text.split()) >= 25 and is_german_passage(abs_text, min_words=20):
                        seen_urls.add(wid)
                        seen_titles.add(t_norm)
                        abstract_rows.append({
                            "title": title,
                            "author": author,
                            "date": year,
                            "decade": decade,
                            "publisher": publisher,
                            "corpus_layer": "primary_cloud_oa_abstract",
                            "source_file": wid,
                            "chunk_index": 1,
                            "total_chunks": 1,
                            "word_count": len(abs_text.split()),
                            "keywords": kw_str,
                            "abstract": abs_text[:420],
                            "text": f"{title}. {abs_text}"
                        })

                # 2. Queue Open-Access PDF for full-text streaming
                if pdf_url and pdf_url not in seen_urls and pdf_url.lower().endswith(".pdf"):
                    seen_urls.add(pdf_url)
                    pdf_candidates.append({
                        "title": title,
                        "author": author,
                        "publisher": publisher,
                        "date": year,
                        "decade": decade,
                        "pdf_url": pdf_url,
                        "keywords": kw_str
                    })
        except Exception:
            continue

    print(
        f"  -> OpenAlex Harvest Summary:\n"
        f"     * {len(abstract_rows):,} NEW German scholarly abstracts reconstructed from `abstract_inverted_index`\n"
        f"     * {len(pdf_candidates):,} NEW OpenAlex German OA PDFs queued for in-RAM streaming...",
        flush=True
    )

    streamed_pdf_rows = []
    books_ok = 0

    def _stream_oa(c):
        txt, _ = stream_entire_pdf_book_in_ram(c["pdf_url"], max_pages=220)
        if not txt or len(txt.split()) < 600:
            return []
        if not is_clean_modern_german(txt) or not is_german_passage(txt):
            return []
        words = txt.split()
        max_w = max_chunks_per_book * chunk_words
        if len(words) > max_w:
            txt = " ".join(words[:max_w])
        chunks = [ch for ch in chunk_fulltext_words(txt, chunk_words=chunk_words) if is_german_passage(ch)]
        if not chunks:
            return []
        layer = "entire_fulltext_book_cloud" if len(chunks) >= 3 else "primary_cloud_oa_fulltext"
        c_rows = []
        for idx, ch in enumerate(chunks, start=1):
            compact_ch = " ".join(ch.split()[:420])
            c_rows.append({
                "title": f"{c['title']} [OpenAlex-Vollbuch-Abschnitt {idx}/{len(chunks)}]",
                "author": c["author"],
                "date": c["date"],
                "decade": c["decade"],
                "publisher": c["publisher"],
                "corpus_layer": layer,
                "source_file": c["pdf_url"],
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "word_count": len(ch.split()),
                "keywords": c.get("keywords", ""),
                "abstract": compact_ch[:240],
                "text": f"{c['title']}. {compact_ch}" if idx == 1 else compact_ch
            })
        return c_rows

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_stream_oa, c): c for c in pdf_candidates[:550]}
        for fut in as_completed(futs):
            c = futs[fut]
            res = fut.result()
            if res:
                books_ok += 1
                streamed_pdf_rows.extend(res)
                w_sum = sum(r["word_count"] for r in res)
                print(
                    f"  + [OPENALEX WAVE-9 #{books_ok}] ({c['date']} | {c['publisher'][:28]}) "
                    f"{c['title'][:48]}... -> {w_sum:,} words ({len(res)} passages)",
                    flush=True
                )

    all_oa_rows = abstract_rows + streamed_pdf_rows
    return pd.DataFrame(all_oa_rows)


def load_all_dnb_shards(base_path: str = "data/dnb_metadata.csv") -> pd.DataFrame:
    """Loads data/dnb_metadata.csv plus any data/dnb_metadata_part*.csv shards in numerical part order."""
    dfs = []
    if os.path.exists(base_path):
        dfs.append(pd.read_csv(base_path, encoding="utf-8", low_memory=False))
    part_files = sorted(
        glob.glob("data/dnb_metadata_part*.csv"),
        key=lambda x: int(re.search(r"part(\d+)", x).group(1)) if re.search(r"part(\d+)", x) else 999,
    )
    for p in part_files:
        dfs.append(pd.read_csv(p, encoding="utf-8", low_memory=False))
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def save_sharded_dnb_corpus(merged_df: pd.DataFrame, rows_per_shard: int = 24000):
    """
    Saves the master corpus across data/dnb_metadata.csv (first 24,000 rows, ~80 MB)
    and data/dnb_metadata_part2.csv+ so EVERY single file stays safely under GitHub's 100 MB per-file limit!
    """
    clean_df = merged_df.copy()
    for col in clean_df.select_dtypes(include=["object"]).columns:
        clean_df[col] = (
            clean_df[col]
            .astype(str)
            .str.replace(r"[\x00-\x1f\x7f-\x9f]", " ", regex=True)
        )

    first_chunk = clean_df.iloc[:rows_per_shard]
    first_chunk.to_csv("data/dnb_metadata.csv", index=False, encoding="utf-8", escapechar="\\")
    mb1 = os.path.getsize("data/dnb_metadata.csv") / (1024 * 1024)
    print(f"  -> Saved shard 1: data/dnb_metadata.csv ({len(first_chunk):,} rows, {mb1:.2f} MB)", flush=True)

    rem = clean_df.iloc[rows_per_shard:]
    part_idx = 2
    while not rem.empty:
        part_df = rem.iloc[:rows_per_shard]
        part_path = f"data/dnb_metadata_part{part_idx}.csv"
        part_df.to_csv(part_path, index=False, encoding="utf-8", escapechar="\\")
        mb_p = os.path.getsize(part_path) / (1024 * 1024)
        print(f"  -> Saved shard {part_idx}: {part_path} ({len(part_df):,} rows, {mb_p:.2f} MB)", flush=True)
        rem = rem.iloc[rows_per_shard:]
        part_idx += 1


def main():
    parser = argparse.ArgumentParser(
        description="Wave-9 Complete Multi-Repository Corpus Harvester (GBV/K10plus + HTRC Multi-ISBN + OpenAlex)"
    )
    parser.add_argument("--chunk-words", type=int, default=1000)
    parser.add_argument("--max-chunks-per-book", type=int, default=75)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--output", default="data/hathitrust_fullbooks_passages.csv")
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
    existing_titles = set()
    if not dnb_prev.empty:
        for u in dnb_prev["source_file"].dropna().unique():
            already_seen_urls.add(str(u).strip())
        existing_titles = set(dnb_prev["title"].dropna().astype(str).str.lower().str.strip())

    print(
        f"Starting Wave-9 Complete GBV/K10plus + HTRC Multi-ISBN + OpenAlex Harvest "
        f"(Skipping {len(already_seen_htids):,} existing HTRC books and {len(already_seen_urls):,} existing URLs)...",
        flush=True
    )

    new_dfs = []

    # 1. Wave-9 Complete GBV / K10plus Harvest (Multi-ISBNs for HTRC + Direct GBV OA/TOC/Paratext Records)
    expanded_books_df, gbv_direct_df = harvest_gbv_wave9_and_multi_isbns(
        already_matched_isbns=already_matched_isbns,
        already_seen_urls=already_seen_urls,
        existing_titles=existing_titles,
        workers=args.workers
    )
    if not gbv_direct_df.empty:
        new_dfs.append(gbv_direct_df)

    # 2. Resolve Multi-ISBNs against HathiTrust Bibliographic API & Stream HTRC EF 2.0 Full Books
    matched_ht_books = batch_resolve_hathitrust_volumes(
        expanded_books_df,
        already_seen_htids=already_seen_htids,
        batch_size=15,
        workers=args.workers
    )

    print(f"\nStreaming full-book page-by-page tokens from HTRC EF-API for {len(matched_ht_books)} NEW Wave-9 printed books...", flush=True)
    htrc_passages = []
    htrc_summaries = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {
            ex.submit(extract_htrc_book_passages, b, args.chunk_words, args.max_chunks_per_book): b
            for b in matched_ht_books
        }
        for fut in as_completed(futs):
            p_list, summ = fut.result()
            if p_list:
                htrc_passages.extend(p_list)
                htrc_summaries.append(summ)
                print(
                    f"  + [WAVE-9 HTRC PRINTED BOOK #{len(htrc_summaries)}] ({summ['date']} | {summ['publisher'][:28]}) "
                    f"{summ['title'][:45]}... [{summ['htid']}] -> {summ['pages']} pages | "
                    f"{summ['extracted_words']:,} words ({summ['passages']} passages)",
                    flush=True
                )

    if htrc_passages:
        new_dfs.append(pd.DataFrame(htrc_passages))
        all_summaries = existing_ht_summaries + htrc_summaries
        pd.DataFrame(all_summaries).to_csv(ht_csv, index=False, encoding="utf-8")

    # 3. Wave-9 OpenAlex Complete Harvest (Reconstructed `abstract_inverted_index` + Uncapped OA PDFs)
    df_oa = harvest_openalex_wave9_corpus(
        already_seen_urls=already_seen_urls,
        existing_titles=existing_titles,
        chunk_words=args.chunk_words,
        max_chunks_per_book=55,
        workers=min(args.workers, 10)
    )
    if not df_oa.empty:
        new_dfs.append(df_oa)

    if not new_dfs:
        print("No additional documents found beyond existing harvest.", flush=True)
        return

    new_combined = pd.concat(new_dfs, ignore_index=True)

    total_new_words = pd.to_numeric(new_combined["word_count"], errors="coerce").fillna(500).sum()
    elapsed = time.time() - start_t
    print("\n======================================================================", flush=True)
    print(f"WAVE-9 COMPLETE MULTI-REPOSITORY EXPANSION FINISHED in {elapsed:.1f}s!", flush=True)
    print(f"  - NEW Wave-9 HTRC In-Copyright Printed Books: {len(htrc_summaries)} full books ({len(htrc_passages):,} passages)", flush=True)
    print(f"  - Cumulative HTRC Printed Books in Corpus: {len(existing_ht_summaries) + len(htrc_summaries)} full books", flush=True)
    print(f"  - NEW GBV / K10plus Direct Documents (OA PDFs, TOCs & MARC 520 Paratexts): {len(gbv_direct_df):,}", flush=True)
    print(f"  - NEW OpenAlex German Documents (Reconstructed Abstracts + OA Full Books): {len(df_oa):,}", flush=True)
    print(f"  - TOTAL NEW DOCUMENTS ADDED IN WAVE 9: {len(new_combined):,} ({int(total_new_words):,} German words!)", flush=True)
    print("======================================================================", flush=True)

    if not args.no_merge:
        new_rows = new_combined[~new_combined["title"].fillna("").astype(str).str.lower().str.strip().isin(existing_titles)]
        merged = pd.concat([dnb_prev, new_rows], ignore_index=True)
        save_sharded_dnb_corpus(merged, rows_per_shard=24000)
        total_est_words = pd.to_numeric(merged.get("word_count"), errors="coerce").fillna(800).sum()
        print(
            f"Total Master Corpus Across Shards = {len(merged):,} documents "
            f"(~{int(total_est_words):,} original German words!)",
            flush=True
        )


if __name__ == "__main__":
    main()
