import glob
import gzip
import json
import os
import re
import sys
import time
import pyarrow.parquet as pq

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import lda_pipeline


def clean_base_title(title: str) -> str:
    return re.sub(r"\[.*?\]", "", str(title or "")).strip().lower()


def build_marc21_fulltext_store():
    t0 = time.time()
    pool_path = os.path.join(ROOT_DIR, "app", "marc21_catalog_pool_cache.json")
    modes_path = os.path.join(ROOT_DIR, "app", "lda_modes_report.json")
    out_path = os.path.join(ROOT_DIR, "app", "marc21_fulltext_store.json.gz")

    targets = {}
    if os.path.exists(pool_path):
        with open(pool_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                bt = clean_base_title(item.get("title", ""))
                if bt and bt not in targets:
                    targets[bt] = item

    if os.path.exists(modes_path):
        with open(modes_path, "r", encoding="utf-8") as f:
            modes_data = json.load(f)
            for rep in (modes_data.get("modes") or {}).values():
                for t in rep.get("topics", []):
                    for d in t.get("representative_docs", []):
                        bt = clean_base_title(d.get("title", ""))
                        if bt and bt not in targets:
                            targets[bt] = d

    print(f"Target unique MARC21 works to index: {len(targets):,}", flush=True)

    store = {}
    parquet_files = sorted(glob.glob(os.path.join(ROOT_DIR, "data", "parquet", "dnb_corpus_part*.parquet")))
    print(f"Scanning {len(parquet_files)} Parquet shards...", flush=True)

    for sp in parquet_files:
        m = re.search(r"part(\d+)\.parquet$", sp)
        shard_num = int(m.group(1)) if m else 0
        tbl = pq.read_table(
            sp,
            columns=[
                "title",
                "author",
                "date",
                "publisher",
                "corpus_layer",
                "source_file",
                "chunk_index",
                "total_chunks",
                "word_count",
                "abstract",
                "text",
            ],
        )
        titles = tbl.column("title").to_pylist()
        # Quick pre-filter indices that match targets
        matched_indices = []
        for idx, tl in enumerate(titles):
            if not tl:
                continue
            bt = clean_base_title(tl)
            if bt in targets:
                matched_indices.append((idx, bt))

        if not matched_indices:
            continue

        authors = tbl.column("author").to_pylist()
        dates = tbl.column("date").to_pylist()
        pubs = tbl.column("publisher").to_pylist()
        layers = tbl.column("corpus_layer").to_pylist()
        sources = tbl.column("source_file").to_pylist()
        c_idxs = tbl.column("chunk_index").to_pylist()
        wc_col = tbl.column("word_count").to_pylist()
        abs_col = tbl.column("abstract").to_pylist()
        txt_col = tbl.column("text").to_pylist()

        for idx, bt in matched_indices:
            tl = lda_pipeline._clean_marc_control_chars(titles[idx] or "")
            txt = lda_pipeline._clean_marc_control_chars(txt_col[idx] or "")
            abs_t = lda_pipeline._clean_marc_control_chars(abs_col[idx] or "")
            src = str(sources[idx] or "").strip()
            layer = str(layers[idx] or "").strip()
            wc = int(wc_col[idx] or len(txt.split()))
            ci = int(c_idxs[idx] or 1)

            if bt not in store:
                store[bt] = {
                    "title": tl,
                    "base_title": re.sub(r"\[.*?\]", "", tl).strip(),
                    "author": lda_pipeline._clean_marc_control_chars(authors[idx] or "o. V."),
                    "publisher": lda_pipeline._clean_marc_control_chars(pubs[idx] or ""),
                    "year": lda_pipeline._clean_marc_control_chars(dates[idx] or "o. J."),
                    "corpus_layer": layer,
                    "source_file": src,
                    "abstract": abs_t[:1200],
                    "parquet_shards": [shard_num],
                    "total_chunks_available": 0,
                    "total_book_words": 0,
                    "chunks": [],
                }
            entry = store[bt]
            if shard_num not in entry["parquet_shards"]:
                entry["parquet_shards"].append(shard_num)
            if src and not entry["source_file"]:
                entry["source_file"] = src
            entry["total_chunks_available"] += 1
            entry["total_book_words"] += wc

            # Store up to 2 complete untruncated passages inline in the compressed serverless store
            # (for single-doc TOCs, blurbs, abstracts this is 100% of the entire document;
            #  for multi-chunk books locally, parquet_shards unlocks ALL 100% of chapters on demand)
            if len(entry["chunks"]) < 2 and txt:
                if not any(c["text"] == txt for c in entry["chunks"]):
                    entry["chunks"].append({
                        "chunk_index": ci,
                        "title": tl,
                        "text": txt,
                        "word_count": wc,
                        "corpus_layer": layer,
                    })

    # Sort embedded chunks by chunk_index
    for entry in store.values():
        entry["chunks"].sort(key=lambda c: c.get("chunk_index", 0))
        entry["parquet_shards"].sort()

    raw_bytes = json.dumps(store, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with gzip.open(out_path, "wb", compresslevel=9) as gz:
        gz.write(raw_bytes)

    gz_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(
        f"Built {out_path} in {time.time() - t0:.1f}s!\n"
        f"  Matched {len(store):,} / {len(targets):,} unique MARC21 works.\n"
        f"  Uncompressed: {len(raw_bytes) / (1024 * 1024):.2f} MB | Gzipped: {gz_mb:.2f} MB",
        flush=True,
    )


if __name__ == "__main__":
    build_marc21_fulltext_store()
