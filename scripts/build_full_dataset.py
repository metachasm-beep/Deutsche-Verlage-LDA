import argparse
import os
import sys
import pandas as pd

# Ensure project root and scripts/ are importable
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.gbv_harvester import harvest_gbv
from scripts.dnb_harvester import harvest_dnb
from scripts.fulltext_ingester import (
    seed_sample_primary_texts,
    ingest_local_directory,
    harvest_cloud_fulltexts_openalex
)
from scripts.auto_enrich_catalog_no_ebooks import auto_enrich_catalog_without_ebooks
from scripts.stream_full_books_cloud import (
    stream_openalex_full_german_books,
    stream_archive_org_full_german_books
)


def build_master_dataset(
    gbv_per_slice: int = 15,
    dnb_per_pub: int = 20,
    cloud_oa_per_query: int = 15,
    oa_full_books_per_query: int = 3,
    archive_full_books: int = 3,
    enrich_books_count: int = 50,
    chunk_words: int = 1000,
    fetch_blurbs: bool = True,
    output_path: str = "data/dnb_metadata.csv"
) -> pd.DataFrame:
    """
    Master automated pipeline that constructs the multi-layer 1970–2025 PhD dataset
    with both full-text books (streamed in RAM without saving e-book files) and multi-API metadata:
    1. Stage 1: Gemeinsamer Bibliotheksverbund (GBV / K10plus GVK) 1970–2025 diachronic harvest (BKL 11.*)
    2. Stage 2: Gemeinsamer Bibliotheksverbund targeted harvest for BKL 11.08 (Religionskritik, Atheismus)
    3. Stage 3: Deutsche Nationalbibliothek (DNB) DDC 200/230 harvest + Inhaltstext blurbs
    4. Stage 4: Zero-Disk Full-Book RAM Streaming (OpenAlex 150-450 page German OA Books + Internet Archive _djvu.txt)
    5. Stage 5: OpenAlex Cloud Open-Access German full-text PDFs & scholarly articles (1970–2025)
    6. Stage 6: Zero-Ebook Multi-API Deep Enrichment (GBV ToC PDFs + OpenAlex Reviews + Wikipedia DE Work Summaries)
    7. Stage 7: Any local full-text books (.pdf, .epub, .docx, .txt) in data/primary_texts/
    """
    frames = []

    print("\n======================================================================")
    print("STAGE 1/7: Harvesting GBV / K10plus (1970-2025 Comprehensive German-Language Corpus)")
    print("======================================================================")
    df_gbv_main = harvest_gbv(
        bkl_filter="*",
        max_records_per_slice=gbv_per_slice,
        fetch_blurbs=fetch_blurbs
    )
    if not df_gbv_main.empty:
        frames.append(df_gbv_main)

    print("\n======================================================================")
    print("STAGE 2/7: Harvesting GBV Targeted Sub-Corpus (BKL 11.* / 11.08)")
    print("======================================================================")
    df_gbv_crit = harvest_gbv(
        bkl_filter="11.08",
        max_records_per_slice=max(10, gbv_per_slice),
        fetch_blurbs=fetch_blurbs
    )
    if not df_gbv_crit.empty:
        frames.append(df_gbv_crit)

    print("\n======================================================================")
    print("STAGE 3/7: Harvesting DNB SRU (1970-2025 Comprehensive German-Language spr=ger)")
    print("======================================================================")
    df_dnb = harvest_dnb(
        start_year=1970,
        max_records_per_publisher=dnb_per_pub,
        fetch_blurbs=fetch_blurbs
    )
    if not df_dnb.empty:
        if "corpus_layer" not in df_dnb.columns:
            df_dnb["corpus_layer"] = "paratext_catalog_dnb"
        frames.append(df_dnb)

    print("\n======================================================================")
    print("STAGE 4/7: Zero-Disk Full-Book RAM Streaming (OpenAlex Books + Archive.org)")
    print("======================================================================")
    if oa_full_books_per_query > 0:
        df_oa_books = stream_openalex_full_german_books(
            books_per_query=oa_full_books_per_query,
            chunk_words=chunk_words
        )
        if not df_oa_books.empty:
            frames.append(df_oa_books)

    if archive_full_books > 0:
        df_ia_books = stream_archive_org_full_german_books(
            max_books=archive_full_books,
            chunk_words=chunk_words
        )
        if not df_ia_books.empty:
            frames.append(df_ia_books)

    print("\n======================================================================")
    print("STAGE 5/7: Streaming Cloud Open-Access Full-Text PDFs (OpenAlex DE)")
    print("======================================================================")
    df_cloud_oa = harvest_cloud_fulltexts_openalex(
        per_query=cloud_oa_per_query,
        chunk_words=chunk_words
    )
    if not df_cloud_oa.empty:
        frames.append(df_cloud_oa)

    print("\n======================================================================")
    print("STAGE 6/7: Zero-Ebook Multi-API Deep Enrichment (731-Book Catalog)")
    print("======================================================================")
    if enrich_books_count > 0 and os.path.exists("data/primary_texts/COMPREHENSIVE_BOOK_CATALOG.csv"):
        df_enriched = auto_enrich_catalog_without_ebooks(
            catalog_csv="data/primary_texts/COMPREHENSIVE_BOOK_CATALOG.csv",
            max_books=enrich_books_count,
            merge_dnb=False
        )
        if not df_enriched.empty:
            frames.insert(0, df_enriched)  # Place first so rich records win deduplication

    print("\n======================================================================")
    print("STAGE 7/7: Ingesting Optional Local Books (data/primary_texts/)")
    print("======================================================================")
    seed_sample_primary_texts("data/primary_texts")
    df_local = ingest_local_directory(
        input_dir="data/primary_texts",
        chunk_words=chunk_words
    )
    if not df_local.empty:
        frames.append(df_local)

    if not frames:
        print("Warning: No records were harvested.")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)

    # Deduplicate by normalized (title, publisher)
    combined["_norm_key"] = (
        combined["title"].fillna("").str.lower().str.strip()
        + "||"
        + combined["publisher"].fillna("").str.lower().str.strip()
    )
    deduped = combined.drop_duplicates(subset=["_norm_key"]).drop(columns=["_norm_key"]).reset_index(drop=True)

    os.makedirs(os.path.dirname(output_path) or "data", exist_ok=True)
    deduped.to_csv(output_path, index=False, encoding="utf-8")
    print("\n======================================================================")
    print(f"MASTER CORPUS COMPLETE: {len(deduped)} unique records/passages saved to {output_path}")
    print("======================================================================")
    return deduped


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automated Master Builder for the 1970-2025 German Publishing & Religion LDA Dataset"
    )
    parser.add_argument("--gbv-per-slice", type=int, default=15, help="Max GBV records per (publisher, decade) slice")
    parser.add_argument("--dnb-per-pub", type=int, default=20, help="Max DNB records per publisher")
    parser.add_argument("--cloud-per-query", type=int, default=15, help="Max OpenAlex OA full texts per query")
    parser.add_argument("--oa-full-books", type=int, default=3, help="Full German books per query to stream in RAM from OpenAlex")
    parser.add_argument("--archive-full-books", type=int, default=3, help="Full German books to stream in RAM from Internet Archive")
    parser.add_argument("--chunk-words", type=int, default=1000, help="Words per passage chunk for full texts")
    parser.add_argument("--fast", action="store_true", help="Skip external HTML blurb requests for faster harvesting")
    parser.add_argument("--run-lda", action="store_true", help="Automatically run lda_pipeline.py after building dataset")
    parser.add_argument("--output", default="data/dnb_metadata.csv", help="Output master CSV path")
    args = parser.parse_args()

    build_master_dataset(
        gbv_per_slice=args.gbv_per_slice,
        dnb_per_pub=args.dnb_per_pub,
        cloud_oa_per_query=args.cloud_per_query,
        oa_full_books_per_query=args.oa_full_books,
        archive_full_books=args.archive_full_books,
        chunk_words=args.chunk_words,
        fetch_blurbs=not args.fast,
        output_path=args.output
    )

    if args.run_lda:
        import lda_pipeline
        model, corp, dict_, coh, docs = lda_pipeline.run_pipeline(args.output)
        lda_pipeline.export_results(model, corp, dict_, args.output)
