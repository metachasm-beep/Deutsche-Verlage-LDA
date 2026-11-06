import json
import os
import re
from collections import Counter, defaultdict
import lda_pipeline

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
    cleaned = lda_pipeline._clean_marc_control_chars(raw_pub).strip()
    if not cleaned or cleaned in ("N/A", "PERSON", "Unknown", "nan"):
        return None, None
    for rx, canon, cat in compiled_patterns:
        if rx.search(cleaned):
            return canon, cat
    if cleaned in ("DNB Monograph (DE)", "Open Access Book (DE)", "epubli", "GRIN Verlag", "BoD – Books on Demand"):
        return "University Presses & OA Repositories (DE)", "Academic & Philosophical"
    return cleaned, "Academic & Philosophical"

def main():
    import numpy as np

    pub_passage_counts = Counter()
    pub_work_sets = defaultdict(set)
    pub_categories = {}
    year_pub_counts = defaultdict(lambda: defaultdict(int))
    year_totals = defaultdict(int)
    layer_counts = Counter()
    layer_words = defaultdict(list)
    total_docs = 0
    total_words_sum = 0

    for row in lda_pipeline.iter_corpus_rows("data/dnb_metadata.csv", include_shards=True):
        total_docs += 1
        layer = str(row.get("corpus_layer") or "dnb_deposit_inhaltstext").strip()
        layer_counts[layer] += 1
        try:
            wc = int(float(row.get("word_count") or 250))
        except Exception:
            wc = 250
        total_words_sum += wc
        layer_words[layer].append(wc)

        raw_pub = row.get("publisher") or ""
        canon_pub, cat = canonicalize_publisher(raw_pub)
        if not canon_pub:
            continue

        pub_passage_counts[canon_pub] += 1
        pub_categories[canon_pub] = cat

        raw_title = lda_pipeline._clean_marc_control_chars(row.get("title") or "")
        base_t = re.sub(r"\[.*?\]", "", raw_title).strip().lower()
        dnb_id = str(row.get("dnb_id") or "").strip()
        ppn = str(row.get("ppn") or "").strip()
        if dnb_id and dnb_id not in ("N/A", "nan", "None", "0"):
            work_key = f"dnb:{dnb_id}"
        elif ppn and ppn not in ("N/A", "nan", "None", "0"):
            work_key = f"ppn:{ppn}"
        else:
            work_key = f"title:{base_t}"
        if work_key:
            pub_work_sets[canon_pub].add(work_key)

        date_str = str(row.get("year") or row.get("date") or "")
        m = re.search(r"(\d{4})", date_str)
        if m:
            yr = int(m.group(1))
            if 1970 <= yr <= 2025:
                year_pub_counts[yr][canon_pub] += 1
                year_totals[yr] += 1

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

    publisher_counts_dict = {p: int(pub_passage_counts.get(p, 0)) for p in top_pubs}
    publisher_works_dict = {p: int(len(pub_work_sets.get(p, set()))) for p in top_pubs}
    publisher_meta_list = [
        {
            "publisher": p,
            "passages": int(pub_passage_counts.get(p, 0)),
            "works": int(len(pub_work_sets.get(p, set()))),
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

    with open("app/data_summary.json", "r", encoding="utf-8") as f:
        sdata = json.load(f)

    def _calc_stats(arr_list):
        if not arr_list:
            return {"count": 0, "total_words": 0, "mean": 0.0, "sd": 0.0, "median": 0.0, "iqr": 0.0, "min": 0, "max": 0}
        arr = np.array(arr_list, dtype=np.float64)
        q25, q50, q75 = np.percentile(arr, [25, 50, 75])
        return {
            "count": int(len(arr)),
            "total_words": int(np.sum(arr)),
            "mean": round(float(np.mean(arr)), 1),
            "sd": round(float(np.std(arr)), 1),
            "median": round(float(q50), 1),
            "iqr": round(float(q75 - q25), 1),
            "min": int(np.min(arr)),
            "max": int(np.max(arr)),
        }

    all_wc = [w for w_list in layer_words.values() for w in w_list]
    doc_len_dist = {
        "overall": _calc_stats(all_wc),
        "by_layer": {lyr: _calc_stats(w_list) for lyr, w_list in sorted(layer_words.items(), key=lambda x: -len(x[1]))},
    }

    manifest_summary = {}
    if os.path.exists("app/dnb_master_manifest_summary.json"):
        with open("app/dnb_master_manifest_summary.json", "r", encoding="utf-8") as mf:
            manifest_summary = json.load(mf)

    # Remove stale nested "summary" duplicate so top-level and any consumer always see the exact same fields
    sdata.pop("summary", None)
    sdata["count"] = int(total_docs)
    sdata["total_records"] = int(total_docs)
    sdata["total_documents"] = int(total_docs)
    sdata["total_words"] = int(total_words_sum)
    if manifest_summary and ("total_unique_works_1970_2025" in manifest_summary or "total_unique_works" in manifest_summary):
        sdata["unique_books"] = int(manifest_summary.get("total_unique_works_1970_2025") or manifest_summary.get("total_unique_works"))
    sdata["corpus_layers"] = {k: int(v) for k, v in layer_counts.most_common()}
    sdata["document_length_distribution"] = doc_len_dist
    if manifest_summary:
        sdata["master_manifest"] = manifest_summary
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
