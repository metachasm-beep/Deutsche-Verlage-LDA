import os
import re
import sys
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.gbv_harvester import harvest_gbv


def clean_filename_part(val: str, max_len: int = 55) -> str:
    if not val:
        return "Unbekannt"
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', str(val))
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rsplit(' ', 1)[0]
    return cleaned or "Unbekannt"


def build_comprehensive_acquisition_catalog(
    records_per_slice: int = 10,
    output_csv: str = "data/primary_texts/COMPREHENSIVE_BOOK_CATALOG.csv",
    output_md: str = "data/primary_texts/BOOK_ACQUISITION_CHECKLIST.md"
):
    """
    Harvests a comprehensive, stratified catalog of in-copyright German books (1970–2025)
    from the Gemeinsamer Bibliotheksverbund (GBV / K10plus) across:
    - All 12 target publishers
    - All 6 decades (1970s–2020s)
    - Specialized sub-queries for BKL 11.08 (Religionskritik, Atheismus),
      BKL 11.05 (Religionssoziologie), BKL 11.06 (Religionspsychologie / Lebenshilfe),
      and general BKL 11.* (Theologie, Religionswissenschaft)
    Ranks works by GBV academic library holdings (MARC 924) and generates ISBNs and
    ready-to-use target filenames for data/primary_texts/.
    """
    frames = []

    # 1. Load already-harvested GBV metadata if available
    if os.path.exists("data/gbv_metadata.csv"):
        frames.append(pd.read_csv("data/gbv_metadata.csv", encoding="utf-8"))

    # 2. Harvest targeted sub-corpora from GBV for high-priority dissertation subfields
    for bkl_code, slice_limit in [("11.08", 15), ("11.05", 10), ("11.06", 10), ("11.*", records_per_slice)]:
        df_sub = harvest_gbv(
            bkl_filter=bkl_code,
            max_records_per_slice=slice_limit,
            fetch_blurbs=False
        )
        if not df_sub.empty:
            frames.append(df_sub)

    if not frames:
        print("No records found.")
        return

    df_all = pd.concat(frames, ignore_index=True)

    # Deduplicate by PPN or normalized title
    df_all["_norm_title"] = df_all["title"].fillna("").str.lower().str.strip()
    df_all = df_all.drop_duplicates(subset=["_norm_title"]).drop(columns=["_norm_title"]).copy()

    # Filter out Open-Access records that already have oa_pdf extracted
    if "corpus_layer" in df_all.columns:
        df_all = df_all[df_all["corpus_layer"] != "primary_cloud_oa_fulltext"].copy()

    # Construct target_filename for each book
    target_filenames = []
    priority_tiers = []
    for _, row in df_all.iterrows():
        yr = str(row.get("date") or "2000")[:4]
        pub = clean_filename_part(str(row.get("publisher") or "Verlag"), max_len=25)
        auth_raw = str(row.get("author") or "o. V.").split(",")[0].strip()
        auth = clean_filename_part(auth_raw, max_len=25)
        short_title = clean_filename_part(str(row.get("title") or "Titel").split(":")[0], max_len=45)
        fname = f"{yr}_{pub}_{auth}_{short_title}.pdf"
        target_filenames.append(fname)

        bkl = str(row.get("bkl_codes") or "")
        holdings = int(row.get("gbv_holdings_count") or 0)
        if "11.08" in bkl:
            priority_tiers.append("Tier 1: Explicit Religionskritik & Atheismus (BKL 11.08)")
        elif "11.05" in bkl:
            priority_tiers.append("Tier 2: Religionssoziologie & Säkularisierung (BKL 11.05)")
        elif "11.06" in bkl or "11.99" in bkl:
            priority_tiers.append("Tier 3: Religionspsychologie, Lebenshilfe & Spiritualität (BKL 11.06/11.99)")
        elif holdings >= 15:
            priority_tiers.append("Tier 4: High-Impact Theological & Cultural Monographs (Holdings >= 15)")
        else:
            priority_tiers.append("Tier 5: General Confessional & Publisher Program Corpus (BKL 11.*)")

    df_all["target_filename"] = target_filenames
    df_all["acquisition_tier"] = priority_tiers

    # Sort by priority tier and GBV library holdings count descending
    df_all = df_all.sort_values(
        by=["acquisition_tier", "gbv_holdings_count", "date"],
        ascending=[True, False, True]
    ).reset_index(drop=True)

    os.makedirs(os.path.dirname(output_csv) or "data/primary_texts", exist_ok=True)
    export_cols = [
        "acquisition_tier", "date", "decade", "publisher", "author", "title",
        "series", "isbn", "ppn", "bkl_codes", "gbv_holdings_count", "target_filename"
    ]
    available_cols = [c for c in export_cols if c in df_all.columns]
    df_all[available_cols].to_csv(output_csv, index=False, encoding="utf-8")

    # Also write comprehensive Markdown guide with summary statistics + top books per tier
    with open(output_md, mode="w", encoding="utf-8") as mf:
        mf.write(
            f"# 📚 Comprehensive Master Acquisition Catalog ({len(df_all)} Books, 1970–2025)\n\n"
            f"This catalog contains **{len(df_all)} unique in-copyright German books (1970–2025)** harvested and "
            f"stratified via the **Gemeinsamer Bibliotheksverbund (GBV / K10plus)** across all 12 target publishers "
            f"and 6 decades, ranked by **GBV Academic Library Holdings (`gbv_holdings_count`)**.\n\n"
            f"- **Full Machine-Readable Catalog (with ISBNs, PPNs, Series & Filenames):** "
            f"[`COMPREHENSIVE_BOOK_CATALOG.csv`](file:///f:/PhD%20AG/data/primary_texts/COMPREHENSIVE_BOOK_CATALOG.csv)\n\n"
            f"## 📊 Breakdown by Acquisition Tier\n\n"
        )
        tier_counts = df_all["acquisition_tier"].value_counts().sort_index()
        for t_name, t_cnt in tier_counts.items():
            mf.write(f"- **{t_name}:** `{t_cnt}` books\n")

        mf.write("\n---\n\n")
        for t_name in sorted(df_all["acquisition_tier"].unique()):
            sub = df_all[df_all["acquisition_tier"] == t_name].head(60)
            mf.write(f"## {t_name} (Showing Top {len(sub)} by Library Holdings)\n\n")
            mf.write("| Year | Publisher | Author | Title | ISBN | GBV Holdings | Target Filename for `data/primary_texts/` |\n")
            mf.write("| :-: | :--- | :--- | :--- | :--- | :-: | :--- |\n")
            for _, r in sub.iterrows():
                yr = str(r.get("date") or "")
                pub = str(r.get("publisher") or "")
                auth = str(r.get("author") or "o. V.")
                tit = str(r.get("title") or "").replace("|", "/")[:85]
                isbn = str(r.get("isbn") or "—").split()[0]
                hold = int(r.get("gbv_holdings_count") or 0)
                fn = str(r.get("target_filename") or "")
                mf.write(f"| {yr} | {pub} | {auth} | *{tit}* | `{isbn}` | {hold} | `{fn}` |\n")
            mf.write("\n")

    print(f"Saved {len(df_all)} stratified books to {output_csv} and {output_md}")


if __name__ == "__main__":
    build_comprehensive_acquisition_catalog(records_per_slice=8)
