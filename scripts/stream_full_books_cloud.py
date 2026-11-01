import argparse
import os
import re
import sys
import time
import urllib3
import requests
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.fulltext_ingester import normalize_german_text, chunk_fulltext_words

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HEADERS = {"User-Agent": "DeutscheVerlageLDA-FullBookStreamer/1.0 (JNU Centre for German Studies)"}


def stream_entire_pdf_book_in_ram(pdf_url: str, max_pages: int = 450) -> tuple[str, int]:
    """
    Streams an entire multi-hundred-page German book PDF into RAM using PyMuPDF (fitz),
    extracts all pages of text without writing any PDF file to disk, and returns
    (normalized_full_book_text, page_count).
    """
    if not pdf_url:
        return "", 0
    try:
        import pymupdf
        resp = requests.get(pdf_url, headers=HEADERS, verify=False, timeout=25)
        if resp.status_code != 200:
            return "", 0
        if b"%PDF" not in resp.content[:1024] and "pdf" not in resp.headers.get("Content-Type", "").lower():
            return "", 0

        doc = pymupdf.open(stream=resp.content, filetype="pdf")
        num_pages = len(doc)
        pages_text = []
        for p_idx in range(min(num_pages, max_pages)):
            raw_page = doc[p_idx].get_text()
            if raw_page and len(raw_page.strip()) > 30:
                pages_text.append(raw_page)
        doc.close()
        return normalize_german_text("\n".join(pages_text)), num_pages
    except Exception:
        return "", 0


def stream_openalex_full_german_books(
    thematic_queries=None,
    books_per_query: int = 5,
    chunk_words: int = 1000,
    min_book_words: int = 5000
) -> pd.DataFrame:
    """
    Queries OpenAlex specifically for FULL-LENGTH GERMAN BOOKS (type:book, language:de,
    is_oa:true, publication_year:1970-2025) out of the 9,780+ Open-Access German books,
    streams the ENTIRE book PDF in RAM (100–450 pages per book), and segments each complete
    book into 1,000-word passages for Gensim LDA.
    """
    if not thematic_queries:
        thematic_queries = [
            "Religion Säkularisierung Moderne",
            "Religionskritik Atheismus Aufklärung",
            "Spiritualität Achtsamkeit Lebenshilfe",
            "Theologie Kirche Seelsorge Gesellschaft"
        ]

    rows = []
    seen_ids = set()
    books_streamed = 0

    print(
        f"Searching OpenAlex Cloud (9,780+ German OA Books, 1970-2025) to stream "
        f"ENTIRE full-text books in RAM..."
    )

    for q in thematic_queries:
        try:
            r = requests.get(
                "https://api.openalex.org/works",
                params={
                    "filter": "language:de,is_oa:true,type:book,publication_year:1970-2025",
                    "search": q,
                    "per-page": books_per_query * 4
                },
                headers=HEADERS,
                verify=False,
                timeout=15
            )
            if r.status_code != 200:
                continue

            results = r.json().get("results", [])
            q_count = 0

            for work in results:
                if q_count >= books_per_query:
                    break
                wid = work.get("id")
                if not wid or wid in seen_ids:
                    continue

                best_oa = work.get("best_oa_location") or {}
                oa_info = work.get("open_access") or {}
                pdf_url = best_oa.get("pdf_url") or oa_info.get("oa_url") or ""
                if not pdf_url:
                    continue

                title = normalize_german_text(work.get("title") or "")
                year = str(work.get("publication_year") or "2020")
                decade = f"{year[:3]}0s" if (len(year) == 4 and year.isdigit()) else ""

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
                # Map Springer Nature to Holtzbrinck conglomerate for dissertation tracking
                if "springer" in publisher.lower() or "link.springer.com" in pdf_url.lower():
                    publisher = "Springer Nature (Holtzbrinck)"
                elif "degruyter" in pdf_url.lower() or "10.1515" in pdf_url.lower():
                    publisher = "De Gruyter / Transcript"
                elif "vr-elibrary" in pdf_url.lower() or "10.13109" in pdf_url.lower():
                    publisher = "Vandenhoeck & Ruprecht"
                elif "nomos" in pdf_url.lower() or "10.5771" in pdf_url.lower():
                    publisher = "Nomos / Alber"

                full_book_text, page_cnt = stream_entire_pdf_book_in_ram(pdf_url, max_pages=450)
                total_words = len(full_book_text.split())
                if total_words < min_book_words:
                    continue

                seen_ids.add(wid)
                q_count += 1
                books_streamed += 1

                chunks = chunk_fulltext_words(full_book_text, chunk_words=chunk_words)
                for idx, chunk_str in enumerate(chunks, start=1):
                    chunk_title = f"{title} [Buch-Abschnitt {idx}/{len(chunks)}]"
                    rows.append({
                        "title": chunk_title,
                        "author": author,
                        "date": year,
                        "decade": decade,
                        "publisher": publisher,
                        "corpus_layer": "entire_fulltext_book_cloud",
                        "source_file": pdf_url,
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                        "word_count": len(chunk_str.split()),
                        "abstract": chunk_str[:420],
                        "text": f"{title}. {chunk_str}"
                    })

                print(
                    f"  + [FULL BOOK #{books_streamed}] ({year} | {publisher}) {title[:55]}... "
                    f"-> {page_cnt} pages | {total_words:,} words | {len(chunks)} LDA passages!"
                )
                time.sleep(0.2)

        except Exception as e:
            print(f"  ! Warning streaming query [{q}]: {e}")

    return pd.DataFrame(rows)


def stream_archive_org_full_german_books(
    max_books: int = 5,
    chunk_words: int = 1000,
    min_book_words: int = 5000
) -> pd.DataFrame:
    """
    Queries Internet Archive (archive.org) for digitized full-length German books
    (mediatype:texts, language:ger) on Religion, Theology, Religionskritik, and Philosophy,
    and streams their plain-text OCR (_djvu.txt) directly in RAM without downloading PDFs.
    """
    rows = []
    q = (
        'language:(ger OR deu) AND mediatype:texts AND '
        '(title:(Religion OR Theologie OR Religionskritik OR Atheismus OR Kirche OR Glaube OR Säkularisierung))'
    )
    print("Searching Internet Archive (archive.org) for full-text German books (_djvu.txt stream)...")
    try:
        r = requests.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": q,
                "fl[]": ["identifier", "title", "creator", "year", "publisher"],
                "rows": max_books * 5,
                "output": "json"
            },
            headers=HEADERS,
            verify=False,
            timeout=15
        )
        if r.status_code != 200:
            return pd.DataFrame()

        docs = r.json().get("response", {}).get("docs", [])
        count = 0
        for d in docs:
            if count >= max_books:
                break
            ident = d.get("identifier")
            if not ident:
                continue

            # Check metadata for _djvu.txt file
            meta_r = requests.get(f"https://archive.org/metadata/{ident}", headers=HEADERS, verify=False, timeout=10)
            if meta_r.status_code != 200:
                continue
            files = meta_r.json().get("files", [])
            djvu_txt_files = [f["name"] for f in files if f.get("name", "").endswith("_djvu.txt")]
            if not djvu_txt_files:
                continue

            txt_url = f"https://archive.org/download/{ident}/{djvu_txt_files[0]}"
            txt_r = requests.get(txt_url, headers=HEADERS, verify=False, timeout=20)
            if txt_r.status_code != 200:
                continue

            full_text = normalize_german_text(txt_r.text)
            total_words = len(full_text.split())
            if total_words < min_book_words:
                continue

            title = normalize_german_text(str(d.get("title") or ident))
            creator_raw = d.get("creator")
            if isinstance(creator_raw, list):
                author = normalize_german_text(creator_raw[0])
            else:
                author = normalize_german_text(str(creator_raw or "o. V."))

            year = str(d.get("year") or "1990")[:4]
            if not year.isdigit():
                year = "1990"
            decade = f"{year[:3]}0s"

            pub_raw = d.get("publisher")
            if isinstance(pub_raw, list):
                publisher = normalize_german_text(pub_raw[0])
            else:
                publisher = normalize_german_text(str(pub_raw or "Archive.org (DE)"))

            chunks = chunk_fulltext_words(full_text, chunk_words=chunk_words)
            for idx, chunk_str in enumerate(chunks, start=1):
                rows.append({
                    "title": f"{title} [Buch-Abschnitt {idx}/{len(chunks)}]",
                    "author": author,
                    "date": year,
                    "decade": decade,
                    "publisher": publisher,
                    "corpus_layer": "entire_fulltext_book_archive_org",
                    "source_file": txt_url,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "word_count": len(chunk_str.split()),
                    "abstract": chunk_str[:420],
                    "text": f"{title}. {chunk_str}"
                })

            count += 1
            print(
                f"  + [ARCHIVE.ORG FULL BOOK #{count}] ({year} | {publisher}) {title[:50]}... "
                f"-> {total_words:,} words | {len(chunks)} LDA passages!"
            )
            time.sleep(0.2)

    except Exception as e:
        print(f"  ! Archive.org stream warning: {e}")

    return pd.DataFrame(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stream ENTIRE multi-hundred-page German full-text books in RAM without saving e-book files"
    )
    parser.add_argument("--oa-books-per-query", type=int, default=2, help="Full books per thematic query from OpenAlex")
    parser.add_argument("--archive-books", type=int, default=2, help="Full books from Internet Archive (_djvu.txt)")
    parser.add_argument("--chunk-words", type=int, default=1000, help="Words per LDA passage chunk")
    parser.add_argument("--output", default="data/fulltext_books_streamed.csv", help="Output CSV path")
    parser.add_argument("--merge-dnb", action="store_true", help="Also merge full-book passages into data/dnb_metadata.csv")
    args = parser.parse_args()

    dfs = []
    df_oa = stream_openalex_full_german_books(
        books_per_query=args.oa_books_per_query,
        chunk_words=args.chunk_words
    )
    if not df_oa.empty:
        dfs.append(df_oa)

    if args.archive_books > 0:
        df_arch = stream_archive_org_full_german_books(
            max_books=args.archive_books,
            chunk_words=args.chunk_words
        )
        if not df_arch.empty:
            dfs.append(df_arch)

    if dfs:
        combined_books = pd.concat(dfs, ignore_index=True)
        os.makedirs(os.path.dirname(args.output) or "data", exist_ok=True)
        combined_books.to_csv(args.output, index=False, encoding="utf-8")
        total_w = combined_books["word_count"].sum()
        print(
            f"\nSaved {len(combined_books)} full-book passages ({total_w:,} total German words!) "
            f"to {args.output} with ZERO PDF/EPUB files saved to disk."
        )

        if args.merge_dnb:
            dnb_path = "data/dnb_metadata.csv"
            if os.path.exists(dnb_path):
                dnb_df = pd.read_csv(dnb_path, encoding="utf-8")
                existing = set(dnb_df["title"].dropna().str.lower().str.strip())
                new_rows = combined_books[~combined_books["title"].fillna("").str.lower().str.strip().isin(existing)]
                merged = pd.concat([dnb_df, new_rows], ignore_index=True)
                merged.to_csv(dnb_path, index=False, encoding="utf-8")
                print(f"Merged into {dnb_path} (Total master corpus rows: {len(merged)})")
