import argparse
import os
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup


def normalize_german_text(text: str) -> str:
    """
    Normalizes German NFC characters, removes soft hyphens (\\u00ad) and end-of-line
    OCR hyphenation breaks (e.g., 'Religions-\\nkritik' -> 'Religionskritik'), and cleans whitespace.
    """
    if not text:
        return ""
    cleaned = str(text).replace("\u00ad", "")
    cleaned = re.sub(r"[\u0080-\u009f˜œ]", "", cleaned)
    # Rejoin hyphenated German compound words split across line breaks in PDFs/OCR
    cleaned = re.sub(r"([a-zäöüß])-\s*\n\s*([a-zäöüß])", r"\1\2", cleaned)
    normalized = unicodedata.normalize("NFC", cleaned)
    return re.sub(r"\s+", " ", normalized).strip()


def extract_text_from_pdf(file_path: str) -> tuple[str, dict]:
    """
    Extracts full text and embedded PDF metadata from a local .pdf file using PyMuPDF (or PyPDF2 fallback).
    """
    meta = {}
    pages_text = []
    try:
        import pymupdf
        doc = pymupdf.open(file_path)
        pdf_meta = doc.metadata or {}
        if pdf_meta.get("title"):
            meta["title"] = normalize_german_text(pdf_meta["title"])
        if pdf_meta.get("author"):
            meta["author"] = normalize_german_text(pdf_meta["author"])
        if pdf_meta.get("creationDate"):
            ym = re.search(r"(\d{4})", str(pdf_meta["creationDate"]))
            if ym:
                meta["date"] = ym.group(1)

        for page in doc:
            raw_page = page.get_text()
            # Remove standalone running page numbers and ToC dot leaders
            cleaned_page = re.sub(r"\.{3,}\s*\d*", " ", raw_page)
            pages_text.append(cleaned_page)
        doc.close()
    except ImportError:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        for page in reader.pages:
            pages_text.append(page.extract_text() or "")

    return normalize_german_text("\n".join(pages_text)), meta


def extract_text_from_epub(file_path: str) -> tuple[str, dict]:
    """
    Extracts full text and Dublin Core metadata (title, creator, publisher, date)
    from an .epub e-book archive using zipfile and BeautifulSoup.
    """
    meta = {}
    chapters_text = []
    with zipfile.ZipFile(file_path, "r") as zf:
        namelist = zf.namelist()
        # 1. Parse OPF package metadata if present
        opf_files = [f for f in namelist if f.lower().endswith(".opf")]
        if opf_files:
            try:
                opf_xml = zf.read(opf_files[0])
                root = ET.fromstring(opf_xml)
                ns = {"dc": "http://purl.org/dc/elements/1.1/"}
                t_el = root.find(".//dc:title", ns)
                a_el = root.find(".//dc:creator", ns)
                p_el = root.find(".//dc:publisher", ns)
                d_el = root.find(".//dc:date", ns)
                if t_el is not None and t_el.text:
                    meta["title"] = normalize_german_text(t_el.text)
                if a_el is not None and a_el.text:
                    meta["author"] = normalize_german_text(a_el.text)
                if p_el is not None and p_el.text:
                    meta["publisher"] = normalize_german_text(p_el.text)
                if d_el is not None and d_el.text:
                    ym = re.search(r"(\d{4})", d_el.text)
                    if ym:
                        meta["date"] = ym.group(1)
            except Exception:
                pass

        # 2. Extract text from XHTML/HTML content files in reading order
        html_files = sorted(
            [f for f in namelist if f.lower().endswith((".xhtml", ".html", ".htm"))]
        )
        for hf in html_files:
            try:
                raw_bytes = zf.read(hf)
                soup = BeautifulSoup(raw_bytes, "html.parser")
                for script_or_style in soup(["script", "style", "nav"]):
                    script_or_style.decompose()
                text = soup.get_text(separator=" ")
                if text and len(text.strip()) > 50:
                    chapters_text.append(text)
            except Exception:
                continue

    return normalize_german_text(" ".join(chapters_text)), meta


def extract_text_from_docx(file_path: str) -> tuple[str, dict]:
    """
    Extracts full text and core properties from a .docx file.
    """
    import docx
    doc = docx.Document(file_path)
    meta = {}
    if doc.core_properties.title:
        meta["title"] = normalize_german_text(doc.core_properties.title)
    if doc.core_properties.author:
        meta["author"] = normalize_german_text(doc.core_properties.author)
    paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    return normalize_german_text(" ".join(paragraphs)), meta


def extract_text_from_txt(file_path: str) -> tuple[str, dict]:
    """
    Reads a UTF-8 (or Latin-1 fallback) plain text file.
    """
    try:
        with open(file_path, mode="r", encoding="utf-8") as f:
            raw = f.read()
    except UnicodeDecodeError:
        with open(file_path, mode="r", encoding="latin-1") as f:
            raw = f.read()
    return normalize_german_text(raw), {}


def infer_metadata_from_path(file_path: Path, embedded_meta: dict) -> dict:
    """
    Infers (date, publisher, author, title) from filename and directory conventions:
    Supported filename patterns:
    1) Year_Publisher_Author_Title.ext  (e.g., 1978_Suhrkamp_Tilmann Moser_Gottesvergiftung.pdf)
    2) Publisher_Year_Author_Title.ext  (e.g., Alibri_2005_Schmidt-Salomon_Manifest.epub)
    3) Year_Publisher_Title.ext         (e.g., 2012_Herder_Kirche in der Krise.txt)
    Also checks parent directory name as fallback Publisher if not in root primary_texts/.
    """
    stem = file_path.stem
    parts = [p.strip() for p in stem.split("_") if p.strip()]
    parent_name = file_path.parent.name

    date = embedded_meta.get("date", "")
    publisher = embedded_meta.get("publisher", "")
    author = embedded_meta.get("author", "o. V.")
    title = embedded_meta.get("title", "")

    if len(parts) >= 4 and re.match(r"^\d{4}$", parts[0]):
        date = parts[0]
        publisher = parts[1]
        author = parts[2]
        title = " - ".join(parts[3:])
    elif len(parts) >= 4 and re.match(r"^\d{4}$", parts[1]):
        publisher = parts[0]
        date = parts[1]
        author = parts[2]
        title = " - ".join(parts[3:])
    elif len(parts) == 3 and re.match(r"^\d{4}$", parts[0]):
        date = parts[0]
        publisher = parts[1]
        title = parts[2]
    elif len(parts) == 3 and re.match(r"^\d{4}$", parts[1]):
        publisher = parts[0]
        date = parts[1]
        title = parts[2]
    else:
        ym = re.search(r"(19[789]\d|20[012]\d)", stem)
        if ym and not date:
            date = ym.group(1)
        if not title:
            title = stem.replace("_", " ")

    if not publisher and parent_name.lower() not in ("primary_texts", "data", "books", "texts"):
        publisher = parent_name

    if not date:
        date = "2020"
    if not publisher:
        publisher = "Unknown"
    if not title:
        title = stem

    decade = f"{date[:3]}0s" if (len(date) == 4 and date.isdigit()) else ""
    return {
        "title": title,
        "author": author,
        "date": date,
        "decade": decade,
        "publisher": publisher
    }


def chunk_fulltext_words(text: str, chunk_words: int = 1000, min_words: int = 80) -> list[str]:
    """
    Segments a book-length full text into fixed-window passages of `chunk_words` words
    (standard Digital Humanities protocol for book-length LDA; Jockers, 2013).
    If chunk_words <= 0, returns the entire book text as a single element.
    """
    words = text.split()
    if not words:
        return []
    if chunk_words <= 0 or len(words) <= chunk_words:
        return [" ".join(words)]

    chunks = []
    for i in range(0, len(words), chunk_words):
        segment = words[i:i + chunk_words]
        if len(segment) >= min_words or not chunks:
            chunks.append(" ".join(segment))
        else:
            # Append trailing short remainder to the final chunk
            chunks[-1] = chunks[-1] + " " + " ".join(segment)
    return chunks


def ingest_local_directory(
    input_dir: str = "data/primary_texts",
    chunk_words: int = 1000
) -> pd.DataFrame:
    """
    Recursively scans `input_dir` for .pdf, .epub, .docx, and .txt full-text primary works,
    extracts and normalizes German text, chunks long books into passages, and returns a DataFrame.
    """
    base_path = Path(input_dir)
    if not base_path.exists():
        print(f"Directory {input_dir} does not exist yet.")
        return pd.DataFrame()

    supported_exts = {".pdf", ".epub", ".docx", ".txt"}
    files = sorted([
        p for p in base_path.rglob("*")
        if p.is_file() and p.suffix.lower() in supported_exts and p.name.lower() != "readme.txt"
    ])

    rows = []
    print(f"Scanning {input_dir}: found {len(files)} full-text document(s)...")

    for fpath in files:
        ext = fpath.suffix.lower()
        try:
            if ext == ".pdf":
                full_text, emb_meta = extract_text_from_pdf(str(fpath))
            elif ext == ".epub":
                full_text, emb_meta = extract_text_from_epub(str(fpath))
            elif ext == ".docx":
                full_text, emb_meta = extract_text_from_docx(str(fpath))
            else:
                full_text, emb_meta = extract_text_from_txt(str(fpath))

            if not full_text or len(full_text.split()) < 15:
                print(f"  ! Skipping {fpath.name} (insufficient extractable text)")
                continue

            meta = infer_metadata_from_path(fpath, emb_meta)
            chunks = chunk_fulltext_words(full_text, chunk_words=chunk_words)
            total_words = len(full_text.split())

            for idx, chunk_str in enumerate(chunks, start=1):
                chunk_title = (
                    f"{meta['title']} [Abschnitt {idx}/{len(chunks)}]"
                    if len(chunks) > 1 else meta["title"]
                )
                rows.append({
                    "title": chunk_title,
                    "author": meta["author"],
                    "date": meta["date"],
                    "decade": meta["decade"],
                    "publisher": meta["publisher"],
                    "corpus_layer": "primary_fulltext",
                    "source_file": fpath.name,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "word_count": len(chunk_str.split()),
                    "abstract": chunk_str[:420],
                    "text": f"{meta['title']}. {chunk_str}"
                })

            print(
                f"  + [{meta['publisher']} | {meta['date']}] {meta['title']} "
                f"({total_words:,} words -> {len(chunks)} LDA passage(s))"
            )

        except Exception as e:
            print(f"  ! Error extracting {fpath.name}: {e}")

    return pd.DataFrame(rows)


def seed_sample_primary_texts(target_dir: str = "data/primary_texts"):
    """
    Creates `data/primary_texts/` with a README guide and 3 representative primary-text
    excerpts across the three theoretical archetypes (Critical, Neoliberal, Traditional)
    so the full-text ingestion pipeline can be verified immediately.
    """
    os.makedirs(target_dir, exist_ok=True)
    readme_path = os.path.join(target_dir, "README.md")
    with open(readme_path, mode="w", encoding="utf-8") as rf:
        rf.write(
            "# Layer 1: Primary Full-Text Corpus Directory (`data/primary_texts/`)\n\n"
            "Place full-length German books, chapters, pamphlets, or articles (`.pdf`, `.epub`, `.docx`, `.txt`) "
            "in this folder.\n\n"
            "## Recommended Filename Convention\n"
            "`Year_Publisher_Author_Title.ext`\n"
            "- Example 1: `1978_Suhrkamp_Tilmann Moser_Gottesvergiftung.pdf`\n"
            "- Example 2: `2005_Alibri_Michael Schmidt-Salomon_Manifest des evolutionären Humanismus.epub`\n"
            "- Example 3: `2012_Gütersloher Verlagshaus_Achtsamkeit und Selbstoptimierung.txt`\n\n"
            "Then run:\n"
            "```powershell\n"
            "python scripts/fulltext_ingester.py --chunk-words 1000 --merge-dnb\n"
            "```\n"
        )

    samples = [
        (
            "2005_Alibri_Michael Schmidt-Salomon_Manifest des evolutionären Humanismus.txt",
            "Der evolutionäre Humanismus vertritt eine konsequente Religionskritik und Kirchenkritik im Geiste "
            "der wissenschaftlichen Aufklärung. Wo traditionelle Religionen und kirchliche Institutionen Dogmatik, "
            "Sündenbewusstsein und klerikale Herrschaftsstrukturen verteidigen, setzt der säkulare Humanismus auf "
            "menschliche Vernunft, Selbstbestimmung, empirische Wissenschaft und eine offene demokratische Gesellschaft. "
            "Die historische Allianz von Staatsmacht, Kapital und kirchlicher Moralautorität hat über Jahrhunderte "
            "hinweg emanzipatorische Philosophie, Atheismus und freie Meinungsäußerung unterdrückt. Auch in der "
            "modernen Bundesrepublik wirken religiöse Privilegien im Staatskirchenrecht, in Bildungseinrichtungen "
            "und in medialen Aufmerksamkeitsökonomien fort. Eine kritische Theorie der Säkularisierung muss daher "
            "nicht nur theologische Dogmen hinterfragen, sondern auch die institutionellen Filtermechanismen "
            "analysieren, durch die religionskritische Literatur im Buchmarkt marginalisiert wird."
        ),
        (
            "2018_Gütersloher Verlagshaus_Sinn und Achtsamkeit_Spirituelle Selbstführung im Alltag.txt",
            "In einer beschleunigten Arbeitswelt suchen moderne Menschen nach Achtsamkeit, innerer Resilienz, "
            "Gelassenheit und persönlicher Sinnerfüllung. Spirituelle Lebenshilfe und ganzheitliches Selbstmanagement "
            "verbinden alte Weisheitstraditionen mit moderner Psychologie und Coaching. Wer sein inneres Potenzial "
            "entfalten und beruflichen Erfolg mit seelischer Gesundheit in Einklang bringen möchte, findet in der "
            "Praxis der Meditation und Selbstoptimierung einen wirksamen Weg zur Heilung und Lebensführung. "
            "Spiritualität wird hier nicht als starre kirchliche Dogmatik verstanden, sondern als individuelle "
            "Ressource für Wohlbefinden, Authentizität, Glück und kreative Führungskompetenz in Zeiten der Krise."
        ),
        (
            "1985_Herder_Karl Rahner_Praxis des Glaubens und kirchliche Seelsorge.txt",
            "Die katholische Theologie und die kirchliche Seelsorge stehen vor der Aufgabe, das Geheimnis der "
            "göttlichen Gnade, der Erlösung durch Jesus Christus und der sakramentalen Gemeinschaft der Kirche "
            "in der heutigen Zeit zu verkünden. Liturgie, Eucharistie, Gebet und die Feier des Gottesdienstes "
            "bilden die unaufgebbare Mitte der christlichen Gemeinde. Dogmatik und Pastoraltheologie dürfen "
            "nicht auseinanderfallen: Wo die Verkündigung des Evangeliums und die Treue zum biblischen Zeugnis "
            "gelebt werden, stiftet der christliche Glaube Versöhnung, Ökumene und moralische Orientierung."
        )
    ]

    for fname, content in samples:
        fpath = os.path.join(target_dir, fname)
        if not os.path.exists(fpath):
            with open(fpath, mode="w", encoding="utf-8") as sf:
                sf.write(content)


def _reconstruct_openalex_abstract(inv_index: dict) -> str:
    if not inv_index or not isinstance(inv_index, dict):
        return ""
    pos_map = {}
    for word, positions in inv_index.items():
        for pos in positions:
            pos_map[pos] = word
    ordered_words = [pos_map[k] for k in sorted(pos_map.keys())]
    return normalize_german_text(" ".join(ordered_words))


def harvest_cloud_fulltexts_openalex(
    queries=None,
    per_query: int = 10,
    chunk_words: int = 1000,
    max_pdf_pages: int = 15
) -> pd.DataFrame:
    """
    Streams German-language Open-Access full-text publications (1970–2025) from the
    OpenAlex API (https://api.openalex.org/works) across the dissertation's core themes,
    extracting in-memory PDF full texts via PyMuPDF and reconstructed abstracts without
    downloading raw PDF files to local storage.
    """
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if not queries:
        queries = [
            "Religionskritik OR Kirchenkritik OR Atheismus",
            "Säkularisierung OR Säkularität OR Religionssoziologie",
            "Spiritualität OR Achtsamkeit OR Lebenshilfe",
            "Seelsorge OR Katholische Theologie OR Evangelische Theologie"
        ]

    rows = []
    seen_ids = set()
    print(f"Streaming German Open-Access full texts from OpenAlex Cloud API across {len(queries)} thematic queries...")

    for q in queries:
        try:
            resp = requests.get(
                "https://api.openalex.org/works",
                params={
                    "filter": "language:de,is_oa:true,publication_year:1970-2025",
                    "search": q,
                    "per-page": per_query
                },
                verify=False,
                timeout=15
            )
            if resp.status_code != 200:
                continue
            results = resp.json().get("results", [])

            for work in results:
                wid = work.get("id")
                if not wid or wid in seen_ids:
                    continue
                seen_ids.add(wid)

                title = normalize_german_text(work.get("title") or "")
                year = str(work.get("publication_year") or "2020")
                decade = f"{year[:3]}0s" if (len(year) == 4 and year.isdigit()) else ""

                # Extract first author
                authorships = work.get("authorships") or []
                author = "o. V."
                if authorships:
                    a_name = (authorships[0].get("author") or {}).get("display_name")
                    if a_name:
                        author = normalize_german_text(a_name)

                # Extract publisher / journal host organization
                loc = work.get("primary_location") or {}
                src = loc.get("source") or {}
                publisher = normalize_german_text(
                    src.get("host_organization_name") or src.get("display_name") or "Open Access (DE)"
                )

                abstract_text = _reconstruct_openalex_abstract(work.get("abstract_inverted_index"))
                oa_info = work.get("open_access") or {}
                best_oa = work.get("best_oa_location") or {}
                pdf_url = best_oa.get("pdf_url") or oa_info.get("oa_url") or ""

                pdf_text = ""
                if pdf_url:
                    try:
                        import pymupdf
                        pdf_resp = requests.get(pdf_url, verify=False, timeout=10)
                        if pdf_resp.status_code == 200 and b"%PDF" in pdf_resp.content[:1024]:
                            doc = pymupdf.open(stream=pdf_resp.content, filetype="pdf")
                            pages = [
                                doc[p].get_text()
                                for p in range(min(len(doc), max_pdf_pages))
                            ]
                            doc.close()
                            pdf_text = normalize_german_text(" ".join(pages))
                    except Exception:
                        pass

                full_body = " ".join([s for s in [abstract_text, pdf_text] if s]).strip()
                if not title or len(full_body.split()) < 20:
                    continue

                chunks = chunk_fulltext_words(full_body, chunk_words=chunk_words)
                for idx, chunk_str in enumerate(chunks, start=1):
                    chunk_title = f"{title} [Abschnitt {idx}/{len(chunks)}]" if len(chunks) > 1 else title
                    rows.append({
                        "title": chunk_title,
                        "author": author,
                        "date": year,
                        "decade": decade,
                        "publisher": publisher,
                        "corpus_layer": "primary_cloud_oa_fulltext" if pdf_text else "primary_cloud_oa_abstract",
                        "source_file": wid,
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                        "word_count": len(chunk_str.split()),
                        "abstract": (abstract_text or chunk_str)[:420],
                        "text": f"{title}. {chunk_str}"
                    })

        except Exception as e:
            print(f"  ! Cloud query warning [{q}]: {e}")

    print(f"  + Streamed {len(rows)} cloud Open-Access German passage(s) in memory.")
    return pd.DataFrame(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest Full-Text German Books & Articles (.pdf, .epub, .docx, .txt, & Cloud OA) into LDA Corpus"
    )
    parser.add_argument("--input-dir", default="data/primary_texts", help="Folder containing full-text files")
    parser.add_argument("--chunk-words", type=int, default=1000, help="Words per passage chunk (0 = no chunking)")
    parser.add_argument("--seed-samples", action="store_true", help="Seed sample primary texts in data/primary_texts")
    parser.add_argument("--fetch-cloud-fulltexts", action="store_true", help="Stream German OA full-text PDFs/articles from OpenAlex Cloud API")
    parser.add_argument("--cloud-per-query", type=int, default=8, help="Max OpenAlex OA works per thematic query")
    parser.add_argument("--output", default="data/fulltext_corpus.csv", help="Output CSV path for Layer 1 full texts")
    parser.add_argument("--merge-dnb", action="store_true", help="Also append full-text chunks into data/dnb_metadata.csv")
    args = parser.parse_args()

    if args.seed_samples or not os.path.exists(args.input_dir):
        seed_sample_primary_texts(args.input_dir)

    dfs = []
    df_local = ingest_local_directory(input_dir=args.input_dir, chunk_words=args.chunk_words)
    if not df_local.empty:
        dfs.append(df_local)

    if args.fetch_cloud_fulltexts:
        df_cloud = harvest_cloud_fulltexts_openalex(
            per_query=args.cloud_per_query,
            chunk_words=args.chunk_words
        )
        if not df_cloud.empty:
            dfs.append(df_cloud)

    if dfs:
        df_full = pd.concat(dfs, ignore_index=True)
        os.makedirs(os.path.dirname(args.output) or "data", exist_ok=True)
        df_full.to_csv(args.output, index=False, encoding="utf-8")
        print(f"Saved {len(df_full)} primary full-text passage(s) to {args.output}")

        if args.merge_dnb:
            dnb_path = "data/dnb_metadata.csv"
            if os.path.exists(dnb_path):
                dnb_df = pd.read_csv(dnb_path, encoding="utf-8")
                existing_titles = set(dnb_df["title"].dropna().apply(lambda s: s.lower().strip()))
                new_rows = df_full[~df_full["title"].fillna("").apply(lambda s: s.lower().strip()).isin(existing_titles)]
                combined = pd.concat([dnb_df, new_rows], ignore_index=True)
                combined.to_csv(dnb_path, index=False, encoding="utf-8")
                print(f"Merged primary full texts into {dnb_path} (Total corpus rows: {len(combined)})")
            else:
                df_full.to_csv(dnb_path, index=False, encoding="utf-8")
                print(f"Created {dnb_path} with {len(df_full)} full-text rows")
