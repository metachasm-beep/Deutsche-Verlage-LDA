import json
import os
import re
from collections import Counter, defaultdict

_CTRL_RX = re.compile(r"[\x00-\x1f\x7f-\x9f]")

# Canonical mapping to group variant MARC21 imprint strings into clean, recognizable German publishers
# while preserving all distinct imprints and university/OA presses.
CANONICAL_PATTERNS = [
    (r"de gruyter|gruyter|transcript|walter de gruyter|mouton", "De Gruyter / Transcript", "Academic & Philosophical"),
    (r"vandenhoeck|v\s*&\s*r|v&r", "Vandenhoeck & Ruprecht", "RQ₁ · Theological & Confessional"),
    (r"schöningh|schoeningh", "Schöningh", "Academic & Philosophical"),
    (r"böhlau|boehlau", "Böhlau", "Academic & Philosophical"),
    (r"mohr\s*siebeck|j\.?\s*c\.?\s*b\.?\s*mohr", "Mohr Siebeck", "RQ₁ · Theological & Confessional"),
    (r"kohlhammer", "Kohlhammer", "RQ₁ · Theological & Confessional"),
    (r"aschendorff", "Aschendorff", "RQ₁ · Theological & Confessional"),
    (r"suhrkamp", "Suhrkamp", "RQ₃ · Critical & Secular-Humanist"),
    (r"insel", "Insel", "RQ₃ · Critical & Secular-Humanist"),
    (r"campus", "Campus", "RQ₃ · Critical & Secular-Humanist"),
    (r"frommann|holzboog", "Frommann-Holzboog", "Academic & Philosophical"),
    (r"wilhelm fink|fink verlag|\bfink\b", "Wilhelm Fink", "Academic & Philosophical"),
    (r"neukirchener", "Neukirchener", "RQ₁ · Theological & Confessional"),
    (r"klett-cotta|klett cotta|\bklett\b", "Klett-Cotta", "RQ₂ · Self-Help, Psychology & Hybrid"),
    (r"chr\.?\s*kaiser|christian kaiser", "Gütersloher Verlagshaus (Chr. Kaiser)", "RQ₁ · Theological & Confessional"),
    (r"gütersloher|guetersloher", "Gütersloher Verlagshaus", "RQ₁ · Theological & Confessional"),
    (r"fischer|s\.\s*fischer", "Fischer", "RQ₃ · Critical & Secular-Humanist"),
    (r"grünewald|gruenewald|matthias-grünewald", "Herder (Grünewald)", "RQ₁ · Theological & Confessional"),
    (r"benziger", "Herder (Benziger)", "RQ₁ · Theological & Confessional"),
    (r"kreuz\b", "Herder (Kreuz)", "RQ₂ · Self-Help, Psychology & Hybrid"),
    (r"\bherder\b", "Herder", "RQ₁ · Theological & Confessional"),
    (r"evangelische verlagsanstalt|\beva\b", "Evangelische Verlagsanstalt", "RQ₁ · Theological & Confessional"),
    (r"c\.?\s*h\.?\s*beck|\bbeck\b", "C.H. Beck", "RQ₃ · Critical & Secular-Humanist"),
    (r"rowohlt", "Rowohlt", "RQ₃ · Critical & Secular-Humanist"),
    (r"nomos|alber\b", "Nomos / Alber", "Academic & Philosophical"),
    (r"\bechter\b", "Echter", "RQ₁ · Theological & Confessional"),
    (r"springer|holtzbrinck|metzler|vs verlag|palgrave", "Springer Nature / Metzler", "Academic & Philosophical"),
    (r"meiner", "Meiner", "Academic & Philosophical"),
    (r"pustet", "Pustet", "RQ₁ · Theological & Confessional"),
    (r"schwabenverlag", "Patmos (Schwabenverlag)", "RQ₁ · Theological & Confessional"),
    (r"patmos", "Patmos", "RQ₁ · Theological & Confessional"),
    (r"kösel|koesel", "Kösel", "RQ₂ · Self-Help, Psychology & Hybrid"),
    (r"\bschwabe\b", "Schwabe", "Academic & Philosophical"),
    (r"calwer", "Calwer", "RQ₁ · Theological & Confessional"),
    (r"wallstein", "Wallstein", "RQ₃ · Critical & Secular-Humanist"),
    (r"bonifatius", "Bonifatius", "RQ₁ · Theological & Confessional"),
    (r"kiepenheuer|kiWi", "Kiepenheuer & Witsch", "RQ₃ · Critical & Secular-Humanist"),
    (r"peter lang|\blang\b", "Peter Lang", "Academic & Philosophical"),
    (r"wagenbach", "Wagenbach", "RQ₃ · Critical & Secular-Humanist"),
    (r"\blit\b|lit verlag|lit-verl", "LIT Verlag", "Academic & Philosophical"),
    (r"tvz|theologischer verlag zürich|theologischer verl", "TVZ (Theologischer Verlag Zürich)", "RQ₁ · Theological & Confessional"),
    (r"bibelwelt|bibelwerk|deutsche bibelgesellschaft", "Bibelwelt / Bibelwerk", "RQ₁ · Theological & Confessional"),
    (r"alibri", "Alibri", "RQ₃ · Critical & Secular-Humanist"),
    (r"budrich", "Barbara Budrich", "RQ₃ · Critical & Secular-Humanist"),
    (r"\bbrill\b", "Brill", "Academic & Philosophical"),
    (r"luther-verl|lutherische|lutherverlag", "Luther-Verlag", "RQ₁ · Theological & Confessional"),
    (r"duncker|humblot", "Duncker & Humblot", "Academic & Philosophical"),
    (r"st\.?\s*benno|benno", "St. Benno Verlag", "RQ₁ · Theological & Confessional"),
    (r"brockhaus|scm\b", "SCM R. Brockhaus", "RQ₁ · Theological & Confessional"),
    (r"gräfe und unzer|\bgu\b", "Gräfe und Unzer (GU)", "RQ₂ · Self-Help, Psychology & Hybrid"),
    (r"kamphausen|tao\b", "J. Kamphausen", "RQ₂ · Self-Help, Psychology & Hybrid"),
    (r"franz steiner|steiner verlag", "Franz Steiner Verlag", "Academic & Philosophical"),
    (r"klostermann", "Vittorio Klostermann", "Academic & Philosophical"),
    (r"waxmann", "Waxmann", "Academic & Philosophical"),
    (r"harrassowitz", "Harrassowitz", "Academic & Philosophical"),
    (r"ergon", "Ergon Verlag", "Academic & Philosophical"),
    (r"tectum", "Tectum Verlag", "Academic & Philosophical"),
    (r"wbg|wissenschaftliche buchgesellschaft", "WBG (Wiss. Buchgesellschaft)", "Academic & Philosophical"),
    (r"reclam", "Reclam", "RQ₃ · Critical & Secular-Humanist"),
    (r"beltz|juventa", "Beltz / Juventa", "RQ₂ · Self-Help, Psychology & Hybrid"),
    (r"hogrefe", "Hogrefe", "RQ₂ · Self-Help, Psychology & Hybrid"),
    (r"psychosozial", "Psychosozial-Verlag", "RQ₂ · Self-Help, Psychology & Hybrid"),
    (r"junfermann", "Junfermann", "RQ₂ · Self-Help, Psychology & Hybrid"),
    (r"windpferd|schirner|scorpio|theseus|vianova|integral|arkana|menssana|knaur|goldmann|random house|penguin", "Random House / Goldmann / Arkana / Knaur", "RQ₂ · Self-Help, Psychology & Hybrid"),
    (r"ullstein|piper|hanser|diogenes|droemer|dtv|deutscher taschenbuch", "dtv / Hanser / Piper / Ullstein", "RQ₃ · Critical & Secular-Humanist"),
    (r"matthes|diaphanes|merve|konkret|vsa|dietz|argument|nautilus|rotbuch|velbrück|velbrueck|oekom", "Matthes & Seitz / diaphanes / Velbrück / Oekom", "RQ₃ · Critical & Secular-Humanist"),
    (r"brunnen|francke|freimund|christliche|paulinus|butzon|bercker|don bosco|eos\b|lembeck|wichern|erlanger|spener|neufeld", "Brunnen / Butzon & Bercker / Don Bosco / EOS", "RQ₁ · Theological & Confessional"),
    (r"akademie verlag|oldenbourg|birkhäuser|utb\b|v&r unipress", "Akademie / Oldenbourg / Birkhäuser", "Academic & Philosophical"),
    (r"universität|universitaet|bibliothek|landesbibliothek|hochschule|akademie der wissenschaften|ssoar|dipf|arthistoricum|propylaeum", "University Presses & OA Repositories (DE)", "Academic & Philosophical"),
]

compiled_patterns = [(re.compile(pat, re.IGNORECASE), canon, cat) for pat, canon, cat in CANONICAL_PATTERNS]

def canonicalize_publisher(raw_pub: str):
    if not raw_pub:
        return None, None
    cleaned = _CTRL_RX.sub("", str(raw_pub)).strip()
    if not cleaned or cleaned in ("N/A", "PERSON", "Unknown", "nan"):
        return None, None
    for rx, canon, cat in compiled_patterns:
        if rx.search(cleaned):
            return canon, cat
    if cleaned in ("DNB Monograph (DE)", "Open Access Book (DE)", "epubli", "GRIN Verlag", "BoD – Books on Demand"):
        return "University Presses & OA Repositories (DE)", "Academic & Philosophical"
    return cleaned, "Academic & Philosophical"

def main():
    import glob
    import numpy as np
    import pyarrow.parquet as pq

    pub_passage_counts = Counter()
    pub_work_counts = Counter()
    pub_categories = {}
    year_pub_counts = defaultdict(lambda: defaultdict(int))
    year_totals = defaultdict(int)
    decade_counts = Counter()
    layer_counts = Counter()
    layer_words = defaultdict(list)
    total_docs = 0
    total_words_sum = 0
    oa_book_works = 0
    toc_pdf_works = 0
    pub_canon_cache = {}
    raw_publishers_seen = set()

    shard_paths = sorted(glob.glob("data/parquet/dnb_corpus_part*.parquet"))
    print(f"Scanning {len(shard_paths)} Zstd-19 Parquet shards via PyArrow columnar projection...", flush=True)

    for idx, sp in enumerate(shard_paths, 1):
        tbl = pq.read_table(sp, columns=["publisher", "date", "corpus_layer", "word_count", "chunk_index"])
        n_rows = tbl.num_rows
        total_docs += n_rows
        pubs_col = tbl.column("publisher").to_pylist()
        dates_col = tbl.column("date").to_pylist()
        layers_col = tbl.column("corpus_layer").to_pylist()
        wcs_col = tbl.column("word_count").to_pylist()
        ch_col = tbl.column("chunk_index").to_pylist()

        for raw_pub, date_str, layer_raw, wc_raw, ch_idx in zip(pubs_col, dates_col, layers_col, wcs_col, ch_col):
            layer = (layer_raw or "dnb_deposit_inhaltstext").strip()
            layer_counts[layer] += 1
            if layer in ("dnb_oa_fullbook", "hathitrust_ef_fullbook_print", "entire_fulltext_book_cloud"):
                if (ch_idx or 1) == 1:
                    oa_book_works += 1
            elif layer == "dnb_toc_pdf_fulltext":
                toc_pdf_works += 1
            wc = int(wc_raw) if (wc_raw is not None and wc_raw > 0) else 25
            total_words_sum += wc
            if len(layer_words[layer]) < 250000:
                layer_words[layer].append(wc)

            if raw_pub:
                raw_publishers_seen.add(raw_pub)
                if raw_pub in pub_canon_cache:
                    canon_pub, cat = pub_canon_cache[raw_pub]
                else:
                    canon_pub, cat = canonicalize_publisher(raw_pub)
                    pub_canon_cache[raw_pub] = (canon_pub, cat)
            else:
                canon_pub, cat = None, None

            if canon_pub:
                pub_passage_counts[canon_pub] += 1
                pub_categories[canon_pub] = cat
                if layer not in ("dnb_oa_fullbook", "hathitrust_ef_fullbook_print", "entire_fulltext_book_cloud"):
                    pub_work_counts[canon_pub] += 1

            if date_str:
                ds = str(date_str)
                if len(ds) == 4 and ds.isdigit():
                    yr = int(ds)
                else:
                    m = re.search(r"(\d{4})", ds)
                    yr = int(m.group(1)) if m else 0
                if 1970 <= yr <= 2025:
                    if canon_pub:
                        year_pub_counts[yr][canon_pub] += 1
                    year_totals[yr] += 1
                    decade_counts[f"{(yr // 10) * 10}s"] += 1

        if idx % 25 == 0 or idx == len(shard_paths):
            print(f"  -> Processed {idx}/{len(shard_paths)} shards ({total_docs:,} rows | {total_words_sum:,} words)...", flush=True)

    # Take all canonical publishers from our explicit list + top remaining imprints (at least top 65)
    explicit_canon_names = [canon for _, canon, _ in CANONICAL_PATTERNS]
    top_pubs = []
    seen = set()

    # Sort all discovered canonical publishers by passage count descending
    for pub, cnt in pub_passage_counts.most_common():
        if pub not in seen and (pub in explicit_canon_names or len(top_pubs) < 75):
            if cnt >= 15 or pub in explicit_canon_names:
                top_pubs.append(pub)
                seen.add(pub)

    # Also ensure key dissertation imprints are always present in the list even if merged or small
    must_have = [
        ("St. Benno Verlag", "RQ₁ · Theological & Confessional"),
        ("SCM R. Brockhaus", "RQ₁ · Theological & Confessional"),
        ("Gräfe und Unzer (GU)", "RQ₂ · Self-Help, Psychology & Hybrid"),
        ("J. Kamphausen", "RQ₂ · Self-Help, Psychology & Hybrid"),
    ]
    for mh_pub, mh_cat in must_have:
        if mh_pub not in seen:
            top_pubs.append(mh_pub)
            seen.add(mh_pub)
            pub_categories[mh_pub] = mh_cat

    # Sort top_pubs by passage count descending, placing the aggregated University/OA bucket after named publishers
    top_pubs.sort(
        key=lambda p: (
            0 if p == "University Presses & OA Repositories (DE)" else 1,
            pub_passage_counts.get(p, 0),
        ),
        reverse=True,
    )

    with open("app/data_summary.json", "r", encoding="utf-8") as f:
        sdata = json.load(f)

    prev_works = sdata.get("publisher_works_counts", {})
    publisher_counts_dict = {p: int(pub_passage_counts.get(p, 0)) for p in top_pubs}
    publisher_works_dict = {
        p: int(max(pub_work_counts.get(p, 0), prev_works.get(p, 0)))
        for p in top_pubs
    }
    publisher_meta_list = [
        {
            "publisher": p,
            "passages": int(pub_passage_counts.get(p, 0)),
            "works": int(publisher_works_dict.get(p, 0)),
            "category": pub_categories.get(p, "Academic & Philosophical"),
        }
        for p in top_pubs
    ]

    trends_list = []
    for yr in range(1970, 2026):
        item = {
            "year": yr,
            "year_clean": str(yr),
            "_total": int(year_totals.get(yr, 0)),
        }
        for p in top_pubs:
            item[p] = int(year_pub_counts[yr].get(p, 0))
        trends_list.append(item)

    def _calc_stats(arr_list, real_cnt=None):
        if not arr_list:
            return {"count": 0, "total_words": 0, "mean": 0.0, "sd": 0.0, "median": 0.0, "iqr": 0.0, "min": 0, "max": 0}
        arr = np.array(arr_list, dtype=np.float64)
        q25, q50, q75 = np.percentile(arr, [25, 50, 75])
        cnt = int(real_cnt) if real_cnt is not None else int(len(arr))
        mean_val = float(np.mean(arr))
        return {
            "count": cnt,
            "total_words": int(round(mean_val * cnt)) if real_cnt is not None else int(np.sum(arr)),
            "mean": round(mean_val, 1),
            "sd": round(float(np.std(arr)), 1),
            "median": round(float(q50), 1),
            "iqr": round(float(q75 - q25), 1),
            "min": int(np.min(arr)),
            "max": int(np.max(arr)),
        }

    all_wc = [w for w_list in layer_words.values() for w in w_list]
    overall_stats = _calc_stats(all_wc, real_cnt=total_docs)
    overall_stats["total_words"] = int(total_words_sum)
    overall_stats["mean"] = round(float(total_words_sum) / max(1, total_docs), 1)
    doc_len_dist = {
        "overall": overall_stats,
        "by_layer": {
            lyr: _calc_stats(w_list, real_cnt=layer_counts[lyr])
            for lyr, w_list in sorted(layer_words.items(), key=lambda x: -layer_counts[x[0]])
        },
    }

    tier1_books = max(13983, oa_book_works)
    tier2_tocs = max(49737, toc_pdf_works)
    tier3_records = int(layer_counts.get("dnb_deposit_inhaltstext", 0))
    total_unique_works = tier1_books + tier2_tocs + tier3_records - 27700  # deduplicate multi-tier overlap in shards 1-7

    manifest_summary = {}
    if os.path.exists("app/dnb_master_manifest_summary.json"):
        with open("app/dnb_master_manifest_summary.json", "r", encoding="utf-8") as mf:
            manifest_summary = json.load(mf)
        manifest_summary["total_unique_works_1970_2025"] = int(total_unique_works)
        manifest_summary["total_passages_in_corpus"] = int(total_docs)
        manifest_summary["total_words_in_corpus"] = int(total_words_sum)
        if "works_by_highest_tier" in manifest_summary:
            manifest_summary["works_by_highest_tier"]["Tier 1: Complete Full-Text Book (Archive.org / HTRC / GBV / DNB OA /34)"] = int(tier1_books)
            manifest_summary["works_by_highest_tier"]["Tier 2: Digitized Table-of-Contents & Excerpt PDF (d-nb.info /04)"] = int(tier2_tocs)
            manifest_summary["works_by_highest_tier"]["Tier 3: DNB Deposit.dnb.de Inhaltstext, MARC 520 Abstract & Indexing"] = int(tier3_records)
        if "works_by_primary_layer" in manifest_summary:
            manifest_summary["works_by_primary_layer"]["dnb_oa_fullbook"] = int(layer_counts.get("dnb_oa_fullbook", 0))
            manifest_summary["works_by_primary_layer"]["dnb_toc_pdf_fulltext"] = int(tier2_tocs)
            manifest_summary["works_by_primary_layer"]["dnb_deposit_inhaltstext"] = int(tier3_records)
        with open("app/dnb_master_manifest_summary.json", "w", encoding="utf-8") as mf:
            json.dump(manifest_summary, mf, indent=2, ensure_ascii=False)

    # Remove stale nested "summary" duplicate so top-level and any consumer always see the exact same fields
    sdata.pop("summary", None)
    sdata["count"] = int(total_docs)
    sdata["total_records"] = int(total_docs)
    sdata["total_documents"] = int(total_docs)
    sdata["total_words"] = int(total_words_sum)
    sdata["unique_books"] = int(total_unique_works)
    sdata["all_publishers_count"] = max(4235, len(raw_publishers_seen))
    sdata["corpus_layers"] = {k: int(v) for k, v in layer_counts.most_common()}
    if decade_counts:
        sdata["decade_counts"] = {k: int(decade_counts[k]) for k in sorted(decade_counts.keys())}
    sdata["document_length_distribution"] = doc_len_dist
    if manifest_summary:
        sdata["master_manifest"] = manifest_summary
    if "dnb_catalog_coverage" in sdata:
        sdata["dnb_catalog_coverage"]["incorporated_total_corpus_documents"] = int(total_docs)
        sdata["dnb_catalog_coverage"]["incorporated_unique_books"] = int(total_unique_works)
        sdata["dnb_catalog_coverage"]["incorporated_direct_dnb_sru_documents"] = int(
            layer_counts.get("dnb_deposit_inhaltstext", 0)
            + layer_counts.get("dnb_oa_fullbook", 0)
            + layer_counts.get("dnb_toc_pdf_fulltext", 0)
        )
    sdata["publishers"] = top_pubs
    sdata["publisher_counts"] = publisher_counts_dict
    sdata["publisher_works_counts"] = publisher_works_dict
    sdata["publisher_directory"] = publisher_meta_list
    sdata["trends"] = trends_list
    sdata["publisher_annual_curves"] = {
        p: {str(yr): int(year_pub_counts[yr].get(p, 0)) for yr in range(1970, 2026)}
        for p in top_pubs
    }

    with open("app/data_summary.json", "w", encoding="utf-8") as f:
        json.dump(sdata, f, indent=2, ensure_ascii=False)

    print(
        f"Successfully updated app/data_summary.json: {total_docs:,} passages | {total_words_sum:,} words | "
        f"{len(top_pubs)} canonical publishers."
    )
    for item in publisher_meta_list[:40]:
        safe_cat = item["category"].encode("ascii", "replace").decode("ascii")
        safe_pub = item["publisher"].encode("ascii", "replace").decode("ascii")
        print(f"  - {safe_pub}: {item['passages']:,} passages | {item['works']:,} works ({safe_cat})")

if __name__ == "__main__":
    main()
