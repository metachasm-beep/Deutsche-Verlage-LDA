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

from scripts.fulltext_ingester import normalize_german_text, chunk_fulltext_words
from scripts.stream_full_books_cloud import stream_entire_pdf_book_in_ram
from scripts.resolve_catalog_fulltexts import is_clean_modern_german

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HEADERS = {
    "User-Agent": "DeutscheVerlageLDA-HTRC-Harvester/4.0 (JNU Centre for German Studies; mailto:paul@jnu.ac.in)"
}
NS = {"zs": "http://www.loc.gov/zing/srw/", "m": "http://www.loc.gov/MARC21/slim"}

# Core 12 dissertation publishers (Wave 4 ultra-deep pagination: startRecord 801..1300 for 11.*, 351..650 for 08.*/71.*)
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

# Extended German theological, philosophical, and sociological imprints (Wave 4: startRecord 501..850 + new imprints)
EXTENDED_GERMAN_RELIGION_PUBLISHERS = [
    ("Herder (Grünewald)", "Grünewald", ["11.*"], 501, 800),
    ("Gütersloher Verlagshaus (Chr. Kaiser)", "Kaiser", ["11.*"], 501, 850),
    ("Herder (Kreuz)", "Kreuz", ["11.*"], 501, 800),
    ("Patmos (Schwabenverlag)", "Schwabenverlag", ["11.*"], 501, 800),
    ("Herder (Benziger)", "Benziger", ["11.*"], 501, 800),
    ("Vandenhoeck & Ruprecht", "Vandenhoeck", ["11.*", "08.*"], 501, 900),
    ("Mohr Siebeck", "Mohr", ["11.*", "08.*"], 501, 900),
    ("Kohlhammer", "Kohlhammer", ["11.*", "08.*"], 501, 900),
    ("C.H. Beck", "Beck", ["11.*", "08.*"], 501, 900),
    ("Schöningh", "Schöningh", ["11.*", "08.*"], 501, 800),
    ("Aschendorff", "Aschendorff", ["11.*"], 501, 800),
    ("Pustet", "Pustet", ["11.*"], 501, 800),
    ("Echter", "Echter", ["11.*"], 501, 800),
    ("Bonifatius", "Bonifatius", ["11.*"], 501, 800),
    ("Neukirchener", "Neukirchener", ["11.*"], 501, 800),
    ("Calwer", "Calwer", ["11.*"], 501, 750),
    ("Campus", "Campus", ["11.*", "71.*"], 501, 800),
    ("Insel", "Insel", ["11.*", "08.*"], 501, 800),
    ("Meiner", "Meiner", ["11.*", "08.*"], 501, 800),
    ("Wallstein", "Wallstein", ["11.*", "08.*"], 501, 800),
    # Brand-new imprints for Wave 4
    ("Nomos / Alber", "Alber", ["11.*", "08.*"], 1, 350),
    ("Wilhelm Fink", "Fink", ["11.*", "08.*"], 1, 350),
    ("Frommann-Holzboog", "Frommann", ["11.*", "08.*"], 1, 300),
    ("Böhlau", "Böhlau", ["11.*"], 1, 350),
    ("Schwabe", "Schwabe", ["11.*", "08.*"], 1, 300),
    ("De Gruyter / Transcript", "Transcript", ["11.*", "71.*"], 1, 350),
    ("De Gruyter / Transcript", "Gruyter", ["11.*"], 1, 400),
]

# Wave-4 Direct BKL Subject Subcodes:
# (a) Pages 251..550 of Wave-3 BKL subcodes
# (b) Pages 1..300 of 22 brand-new BKL subcodes covering Biblical Exegesis, Liturgics, Pastoral Care,
#     Psychology of Religion, Critical Theory, Philosophical Anthropology, and Cultural Philosophy
WAVE4_BKL_SUBCODES = [
    ("11.08", 251, 550),  # Religionskritik & Atheismus
    ("11.05", 251, 550),  # Religionssoziologie
    ("11.09", 251, 500),  # Systematische Religionswissenschaft
    ("08.37", 251, 550),  # Religionsphilosophie
    ("11.60", 251, 550),  # Systematische Theologie
    ("11.61", 251, 550),  # Dogmatik
    ("11.62", 251, 550),  # Christliche Ethik
    ("11.70", 251, 550),  # Praktische Theologie
    ("11.77", 251, 550),  # Religionspädagogik
    ("11.50", 251, 550),  # Kirchengeschichte
    ("11.55", 251, 550),  # Neuzeitliche Kirchengeschichte
    ("11.20", 251, 500),  # Judentum
    ("11.80", 251, 500),  # Islam
    # Brand-new BKL subcodes for Wave 4
    ("11.01", 1, 250),    # Geschichte der Religionswissenschaft & Theologie
    ("11.02", 1, 250),    # Philosophie und Theorie der Religion
    ("11.06", 1, 250),    # Religionspsychologie
    ("11.07", 1, 200),    # Religionsethnologie
    ("11.30", 1, 250),    # Bibelwissenschaft
    ("11.31", 1, 250),    # Bibeltext, Bibelübersetzungen
    ("11.35", 1, 250),    # Altes Testament
    ("11.40", 1, 250),    # Neues Testament
    ("11.45", 1, 250),    # Biblische Theologie
    ("11.51", 1, 250),    # Frühes Christentum
    ("11.52", 1, 250),    # Mittelalterliches Christentum
    ("11.53", 1, 250),    # Reformation
    ("11.54", 1, 250),    # Konfessionalismus & Aufklärung
    ("11.63", 1, 250),    # Ökumenische Theologie
    ("11.72", 1, 250),    # Liturgik & Gottesdienst
    ("11.74", 1, 250),    # Homiletik & Predigt
    ("11.75", 1, 250),    # Seelsorge & Poimenik
    ("11.76", 1, 250),    # Diakonie & Caritas
    ("11.79", 1, 250),    # Kirchenrecht & Staatskirchenrecht
    ("08.36", 1, 250),    # Philosophische Anthropologie
    ("08.42", 1, 250),    # Kulturphilosophie
    ("08.44", 1, 250),    # Sozialphilosophie & Kritische Theorie
]

OPENALEX_WAVE4_QUERIES = [
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
    # RQ1 & Cross-Cutting Theological/Sociological Domains (Pages 3/2)
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


def is_german_passage(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    words = [w.lower() for w in re.findall(r"\b[a-zA-ZäöüÄÖÜß]{3,}\b", text[:6000])]
    if len(words) < 25:
        return False
    en_cnt = sum(1 for w in words if w in EN_MARKERS)
    de_cnt = sum(1 for w in words if w in DE_MARKERS)
    return de_cnt >= max(10, en_cnt * 2)


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


def expand_gbv_wave4_isbn_catalog(
    already_matched_isbns: set[str],
    core_start: int = 801,
    core_end: int = 1250
) -> pd.DataFrame:
    """
    Wave-4 Ultra-Deep GBV K10plus SRU Harvester:
      1. Records 801..1250 for the 12 core publishers (BKL 11.*) and 351..600 (BKL 08.*/71.*)
      2. Records 501..850 for 20 extended publishers + 1..350 for 7 new academic imprints
      3. Direct BKL Subject Subcode harvesting across 35 theological, philosophical, and sociological subcodes
    """
    books = []
    seen_isbns = set(already_matched_isbns)
    seen_ppns = set()

    all_tasks = []
    for canonical_pub, gbv_term, bkl_list in CORE_12_PUBLISHERS:
        for bkl in bkl_list:
            s_start = core_start if bkl == "11.*" else 351
            s_end = core_end if bkl == "11.*" else 600
            for start_rec in range(s_start, s_end + 1, 50):
                all_tasks.append((canonical_pub, f'pica.bkl={bkl} and pica.ver="{gbv_term}"', bkl, start_rec))

    for canonical_pub, gbv_term, bkl_list, s_start, s_end in EXTENDED_GERMAN_RELIGION_PUBLISHERS:
        for bkl in bkl_list:
            for start_rec in range(s_start, s_end + 1, 50):
                all_tasks.append((canonical_pub, f'pica.bkl={bkl} and pica.ver="{gbv_term}"', bkl, start_rec))

    for bkl_code, s_start, s_end in WAVE4_BKL_SUBCODES:
        for start_rec in range(s_start, s_end + 1, 50):
            all_tasks.append((None, f'pica.bkl={bkl_code}', bkl_code, start_rec))

    print(
        f"Wave-4 GBV K10plus Ultra-Deep Harvester: Querying {len(all_tasks)} SRU pages "
        f"(Ultra-Deep Publisher Pagination + 35 Direct BKL Subject Codes)...",
        flush=True
    )

    lock = threading.Lock()

    def _fetch_sru_page(task):
        canonical_pub, q, bkl, start_rec = task
        page_books = []
        try:
            r = requests.get(
                "https://sru.k10plus.de/gvk",
                params={
                    "version": "1.1",
                    "operation": "searchRetrieve",
                    "query": q,
                    "startRecord": str(start_rec),
                    "maximumRecords": "50",
                    "recordSchema": "marcxml"
                },
                headers=HEADERS,
                verify=False,
                timeout=18
            )
            if r.status_code != 200:
                return page_books
            root = ET.fromstring(r.content)
            records = root.findall(".//zs:recordData/m:record", NS)
            for rec in records:
                f001 = rec.find("m:controlfield[@tag='001']", NS)
                ppn = f001.text.strip() if (f001 is not None and f001.text) else ""

                isbn = ""
                for f020 in rec.findall("m:datafield[@tag='020']", NS):
                    sa = f020.find("m:subfield[@code='a']", NS)
                    if sa is not None and sa.text:
                        cand = re.sub(r"[^0-9Xx]", "", sa.text.split()[0]).upper()
                        if len(cand) in (10, 13):
                            isbn = cand
                            break
                if not isbn:
                    continue

                year = ""
                for f264 in rec.findall("m:datafield[@tag='264']", NS) + rec.findall("m:datafield[@tag='260']", NS):
                    sc = f264.find("m:subfield[@code='c']", NS)
                    if sc is not None and sc.text:
                        ym = re.search(r"(19[789]\d|20[012]\d)", sc.text)
                        if ym:
                            year = ym.group(1)
                            break
                if not year:
                    continue

                title_parts = []
                f245 = rec.find("m:datafield[@tag='245']", NS)
                if f245 is not None:
                    for code in ("a", "b"):
                        sub = f245.find(f"m:subfield[@code='{code}']", NS)
                        if sub is not None and sub.text:
                            title_parts.append(sub.text.strip())
                title = normalize_german_text(": ".join(title_parts))
                if not title:
                    continue

                author = "o. V."
                for tag in ("100", "700"):
                    fa = rec.find(f"m:datafield[@tag='{tag}']", NS)
                    if fa is not None:
                        sa = fa.find("m:subfield[@code='a']", NS)
                        if sa is not None and sa.text:
                            author = normalize_german_text(sa.text.strip())
                            break

                pub_name = canonical_pub
                if not pub_name:
                    for f264 in rec.findall("m:datafield[@tag='264']", NS) + rec.findall("m:datafield[@tag='260']", NS):
                        sb = f264.find("m:subfield[@code='b']", NS)
                        if sb is not None and sb.text:
                            pub_name = normalize_german_text(sb.text.strip())
                            break
                if not pub_name:
                    pub_name = "German Academic Monograph (GBV)"

                page_books.append({
                    "title": title,
                    "author": author,
                    "publisher": pub_name,
                    "date": year,
                    "decade": f"{year[:3]}0s",
                    "isbn": isbn,
                    "ppn": ppn,
                    "bkl_codes": bkl.replace(".*", ".00")
                })
        except Exception:
            pass
        return page_books

    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(_fetch_sru_page, t) for t in all_tasks]
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                with lock:
                    for b in res:
                        if b["ppn"] and b["ppn"] in seen_ppns:
                            continue
                        variants = isbn_variants(b["isbn"])
                        if any(v in seen_isbns for v in variants):
                            continue
                        for v in variants:
                            seen_isbns.add(v)
                        if b["ppn"]:
                            seen_ppns.add(b["ppn"])
                        books.append(b)

    df = pd.DataFrame(books)
    print(f"Total Wave-4 NEW 1970-2025 printed books queued for HathiTrust ISBN lookup: {len(df):,}", flush=True)
    return df


def batch_resolve_hathitrust_volumes(
    books_df: pd.DataFrame,
    already_seen_htids: set[str],
    batch_size: int = 15,
    workers: int = 10
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

    print(f"Batch-querying HathiTrust Bibliographic API across {len(valid_rows):,} Wave-4 ISBNs ({len(batches)} batches)...", flush=True)
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

    print(f"  -> Matched {len(matched_books):,} NEW Wave-4 in-copyright 1970-2025 printed German books in HathiTrust!", flush=True)
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
                # Compact repeated HTRC function words so CSV stays compact (<85 MB per shard)
                substantive = [w for w in chunk_str.split() if w.lower() not in HTRC_FUNCTION_STOPWORDS][:330]
                compact_chunk = " ".join(substantive)
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
                    "text": f"{title}. {author}. {publisher}. {compact_chunk}"
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


def harvest_openalex_wave4_books_and_chapters(
    already_seen_urls: set[str],
    books_per_query: int = 10,
    chunk_words: int = 1000,
    max_chunks_per_book: int = 55,
    workers: int = 8
) -> pd.DataFrame:
    """
    Wave-4 OpenAlex Streamer:
      Queries RQ2 (Mindfulness/Self-Optimization), RQ3 (Secularism/Atheism/Humanism),
      and Page 3 of `type:book` + Page 2 of `type:book-chapter` across 32 queries.
    """
    print(
        f"\nWave-4 OpenAlex Harvester: Querying RQ2/RQ3 + Pages 3/2 of German OA Books & Book Chapters...",
        flush=True
    )
    candidates = []
    seen_ids = set()
    seen_urls = set(already_seen_urls)

    for q_idx, q in enumerate(OPENALEX_WAVE4_QUERIES):
        # First 15 queries are brand-new RQ2/RQ3 queries (page 1), remaining 17 are page 3/2
        if q_idx < 15:
            search_configs = [
                ("language:de,is_oa:true,type:book,publication_year:1970-2025", 1),
                ("language:de,is_oa:true,type:book-chapter,publication_year:1970-2025", 1),
            ]
        else:
            search_configs = [
                ("language:de,is_oa:true,type:book,publication_year:1970-2025", 3),
                ("language:de,is_oa:true,type:book-chapter,publication_year:1970-2025", 2),
            ]
        for oa_filter, page_num in search_configs:
            try:
                r = requests.get(
                    "https://api.openalex.org/works",
                    params={
                        "filter": oa_filter,
                        "search": q,
                        "per-page": 35,
                        "page": page_num
                    },
                    headers=HEADERS,
                    verify=False,
                    timeout=15
                )
                if r.status_code != 200:
                    continue
                q_added = 0
                for work in r.json().get("results", []):
                    if q_added >= books_per_query:
                        break
                    wid = work.get("id")
                    if not wid or wid in seen_ids:
                        continue
                    best_oa = work.get("best_oa_location") or {}
                    oa_info = work.get("open_access") or {}
                    pdf_url = best_oa.get("pdf_url") or oa_info.get("oa_url") or ""
                    if not pdf_url or pdf_url in seen_urls:
                        continue

                    title = normalize_german_text(work.get("title") or "")
                    if not title or len(title) < 5:
                        continue
                    year = str(work.get("publication_year") or "2018")[:4]
                    if not year.isdigit() or int(year) < 1970:
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
                    publisher = normalize_german_text(
                        src.get("host_organization_name") or src.get("display_name") or "Open Access Book (DE)"
                    )
                    if "springer" in publisher.lower() or "link.springer.com" in pdf_url.lower():
                        publisher = "Springer Nature (Holtzbrinck)"
                    elif "degruyter" in pdf_url.lower() or "10.1515" in pdf_url.lower():
                        publisher = "De Gruyter / Transcript"
                    elif "vr-elibrary" in pdf_url.lower() or "10.13109" in pdf_url.lower():
                        publisher = "Vandenhoeck & Ruprecht"
                    elif "nomos" in pdf_url.lower() or "10.5771" in pdf_url.lower():
                        publisher = "Nomos / Alber"

                    seen_ids.add(wid)
                    seen_urls.add(pdf_url)
                    q_added += 1
                    candidates.append({
                        "title": title,
                        "author": author,
                        "publisher": publisher,
                        "date": year,
                        "decade": decade,
                        "pdf_url": pdf_url
                    })
            except Exception:
                continue

    print(f"Queued {len(candidates)} NEW Wave-4 OpenAlex German books & book chapters for in-RAM PDF streaming...", flush=True)
    rows = []
    books_ok = 0

    def _stream_oa(c):
        txt, pages = stream_entire_pdf_book_in_ram(c["pdf_url"], max_pages=350)
        if not txt or len(txt.split()) < 1800:
            return []
        if not is_clean_modern_german(txt) or not is_german_passage(txt):
            return []
        words = txt.split()
        max_w = max_chunks_per_book * chunk_words
        if len(words) > max_w:
            txt = " ".join(words[:max_w])
        chunks = [ch for ch in chunk_fulltext_words(txt, chunk_words=chunk_words) if is_german_passage(ch)]
        c_rows = []
        for idx, ch in enumerate(chunks, start=1):
            compact_ch = " ".join(ch.split()[:420])
            c_rows.append({
                "title": f"{c['title']} [OpenAlex-Vollbuch-Abschnitt {idx}/{len(chunks)}]",
                "author": c["author"],
                "date": c["date"],
                "decade": c["decade"],
                "publisher": c["publisher"],
                "corpus_layer": "entire_fulltext_book_cloud",
                "source_file": c["pdf_url"],
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "word_count": len(ch.split()),
                "abstract": compact_ch[:240],
                "text": f"{c['title']}. {c['author']}. {c['publisher']}. {compact_ch}"
            })
        return c_rows

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_stream_oa, c): c for c in candidates}
        for fut in as_completed(futs):
            c = futs[fut]
            res = fut.result()
            if res:
                books_ok += 1
                rows.extend(res)
                w_sum = sum(r["word_count"] for r in res)
                print(
                    f"  + [OPENALEX WAVE-4 #{books_ok}] ({c['date']} | {c['publisher'][:28]}) "
                    f"{c['title'][:48]}... -> {w_sum:,} words ({len(res)} passages)",
                    flush=True
                )

    return pd.DataFrame(rows)


def load_all_dnb_shards(base_path: str = "data/dnb_metadata.csv") -> pd.DataFrame:
    """Loads data/dnb_metadata.csv plus any data/dnb_metadata_part*.csv shards."""
    dfs = []
    if os.path.exists(base_path):
        dfs.append(pd.read_csv(base_path, encoding="utf-8", low_memory=False))
    for p in sorted(glob.glob("data/dnb_metadata_part*.csv")):
        dfs.append(pd.read_csv(p, encoding="utf-8", low_memory=False))
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def save_sharded_dnb_corpus(merged_df: pd.DataFrame, rows_per_shard: int = 24000):
    """
    Saves the master corpus across data/dnb_metadata.csv (first 24,000 rows, ~80 MB)
    and data/dnb_metadata_part2.csv (and part3+ if needed) so EVERY single file stays
    safely under GitHub's 100 MB per-file limit!
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
        description="Wave-4 Ultra-Deep Full-Book German Corpus Harvester (HTRC + OpenAlex RQ2/RQ3 + Auto-Sharding)"
    )
    parser.add_argument("--oa-books-per-query", type=int, default=10)
    parser.add_argument("--chunk-words", type=int, default=1000)
    parser.add_argument("--max-chunks-per-book", type=int, default=75)
    parser.add_argument("--workers", type=int, default=10)
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
    if not dnb_prev.empty:
        for u in dnb_prev["source_file"].dropna().unique():
            already_seen_urls.add(str(u).strip())

    print(
        f"Starting Wave-4 Ultra-Deep Expansion (Skipping {len(already_seen_htids)} existing HTRC books "
        f"and {len(already_seen_urls)} existing URLs)...",
        flush=True
    )

    new_dfs = []

    # 1. Wave-4 Ultra-Deep GBV Publisher Pagination + 35 Direct BKL Subject Subcodes -> HathiTrust HTRC
    expanded_books_df = expand_gbv_wave4_isbn_catalog(
        already_matched_isbns=already_matched_isbns
    )
    matched_ht_books = batch_resolve_hathitrust_volumes(
        expanded_books_df,
        already_seen_htids=already_seen_htids,
        batch_size=15,
        workers=args.workers
    )

    print(f"\nStreaming full-book page-by-page tokens from HTRC EF-API for {len(matched_ht_books)} NEW Wave-4 printed books...", flush=True)
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
                    f"  + [WAVE-4 HTRC PRINTED BOOK #{len(htrc_summaries)}] ({summ['date']} | {summ['publisher'][:28]}) "
                    f"{summ['title'][:45]}... [{summ['htid']}] -> {summ['pages']} pages | "
                    f"{summ['extracted_words']:,} words ({summ['passages']} passages)",
                    flush=True
                )

    if htrc_passages:
        new_dfs.append(pd.DataFrame(htrc_passages))
        all_summaries = existing_ht_summaries + htrc_summaries
        pd.DataFrame(all_summaries).to_csv(ht_csv, index=False, encoding="utf-8")

    # 2. Wave-4 OpenAlex Books & Chapters (RQ2/RQ3 + Pages 3/2)
    df_oa = harvest_openalex_wave4_books_and_chapters(
        already_seen_urls=already_seen_urls,
        books_per_query=args.oa_books_per_query,
        chunk_words=args.chunk_words,
        max_chunks_per_book=55,
        workers=min(args.workers, 8)
    )
    if not df_oa.empty:
        new_dfs.append(df_oa)

    if not new_dfs:
        print("No additional full-book passages found beyond existing harvest.", flush=True)
        return

    new_combined = pd.concat(new_dfs, ignore_index=True)

    if os.path.exists(args.output):
        prev_ht = pd.read_csv(args.output, encoding="utf-8", low_memory=False)
        full_ht = pd.concat([prev_ht, new_combined], ignore_index=True)
    else:
        full_ht = new_combined
    full_ht.to_csv(args.output, index=False, encoding="utf-8")

    total_new_words = pd.to_numeric(new_combined["word_count"], errors="coerce").fillna(1000).sum()
    elapsed = time.time() - start_t
    print("\n======================================================================", flush=True)
    print(f"WAVE-4 ULTRA-DEEP FULL-BOOK EXPANSION COMPLETE in {elapsed:.1f}s!", flush=True)
    print(f"  - NEW Wave-4 HTRC In-Copyright Printed Books: {len(htrc_summaries)} full books ({len(htrc_passages):,} passages)", flush=True)
    print(f"  - Cumulative HTRC Printed Books in Corpus: {len(existing_ht_summaries) + len(htrc_summaries)} full books", flush=True)
    print(f"  - NEW OpenAlex German OA Books & Chapters Passages: {len(df_oa):,}", flush=True)
    print(f"  - TOTAL NEW PASSAGES ADDED IN WAVE 4: {len(new_combined):,} ({int(total_new_words):,} German words!)", flush=True)
    print("======================================================================", flush=True)

    if not args.no_merge:
        existing_titles = set(dnb_prev["title"].dropna().str.lower().str.strip()) if not dnb_prev.empty else set()
        new_rows = new_combined[~new_combined["title"].fillna("").str.lower().str.strip().isin(existing_titles)]
        merged = pd.concat([dnb_prev, new_rows], ignore_index=True)
        save_sharded_dnb_corpus(merged, rows_per_shard=24000)
        total_est_words = pd.to_numeric(merged.get("word_count"), errors="coerce").fillna(950).sum()
        print(
            f"Total Master Corpus Across Shards = {len(merged):,} documents "
            f"(~{int(total_est_words):,} original German words!)",
            flush=True
        )


if __name__ == "__main__":
    main()
