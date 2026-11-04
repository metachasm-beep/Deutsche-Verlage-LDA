# 📂 PhD Dataset Acquisition Guide: Nine-Wave Complete DNB + GBV/K10plus + HTRC + OpenAlex Corpus (`354,801` Documents | `~286.24M` Words)

This document outlines the methodological, archival, and FAIR/DDI-compliant technical architecture for constructing the **1970–2025 full-text and national-library German book corpus (`354,801` documents/passages, `~286,242,495` original German words across `4,002` HTRC printed books, `926` DNB `/34` `$z="kostenfrei"` open-access full books & EPUBs, `211` OpenAlex/GBV open-access full books, `31,992` DNB `/04` digitized `Inhaltsverzeichnis` & reading-sample PDFs/HTMLs, `41,286` DNB `deposit.dnb.de` & `/blurb/` `Inhaltstexte`, `17,458` GBV / K10plus consortial TOC PDFs, OA passages & `MARC 520` / `BKL` / `GND` enriched records, `618` OpenAlex reconstructed `abstract_inverted_index` scholarly abstracts, `38` Internet Archive books, and `702` multi-API deep-enriched works)** for the dissertation **"Mediating Faith and Power: Religious Authority and the German Publishing Landscape"**.

---

## 📊 1. Cumulative Nine-Wave Master Corpus Summary (`1970–2025`)

| Corpus Tier / Source (`corpus_layer`) | Complete Full Books / Works | Full-Text Passages ($D$) | Total German Words | Storage Location |
| :--- | :---: | :---: | :---: | :--- |
| **HathiTrust HTRC Printed German Books (`1970–2025`)** *(Waves 1–4 GBV: `1,056` + Waves 5–8 DNB ISBNs: `2,365` + Wave 9 Multi-ISBN GBV/K10plus: `581`)* | **`4,002` printed books** | `243,596` | `~244,450,000` | [`data/primary_texts/HATHITRUST_MATCHED_BOOKS.csv`](file:///f:/PhD%20AG/data/primary_texts/HATHITRUST_MATCHED_BOOKS.csv) |
| **Deutsche Nationalbibliothek (`deposit.dnb.de` & `/blurb/` `Inhaltstexte` & `MARC 520` Abstracts, `1970–2025`)** | **`41,286` DNB works** | `41,286` | `~7,150,000` | [`data/dnb_metadata_part5.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part5.csv)–[`part15.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part15.csv) |
| **DNB Digitized `/04` `Inhaltsverzeichnis` & Reading Sample PDFs/HTMLs (`1970–2025`)** | **`31,992` DNB `/04` PDFs/HTMLs** | `31,992` | `~11,480,000` | [`data/dnb_metadata_part7.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part7.csv)–[`part15.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part15.csv) |
| **GBV / K10plus Consortial TOC PDFs, Blurbs & `MARC 520` / `BKL` / `GND` Enriched Works (`1970–2025`)** | **`17,031` GBV works** | `17,031` | `~3,650,000` | [`data/dnb_metadata_part13.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part13.csv)–[`part15.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part15.csv) |
| **DNB `/34` Sibling-Matched `$z="kostenfrei"` Open-Access Full Books & EPUBs (`1970–2025`)** | **`926` DNB OA books/EPUBs** | `15,122` | `~14,973,085` | [`data/dnb_metadata_part6.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part6.csv)–[`part13.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part13.csv) |
| **OpenAlex & GBV `Kostenfrei` OA Full Books + Reconstructed `abstract_inverted_index` Corpus (`1970–2025`)** | **`211` OA books + `618` OA abstracts** | `5,594` | `~4,004,434` | [`data/dnb_metadata.csv`](file:///f:/PhD%20AG/data/dnb_metadata.csv)–[`part15.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part15.csv) |
| **Catalog Full-Texts (`archive.org` / Green OA) + Multi-API Enriched Books** | **`38` full books + `702` enriched** | `1,303` | `~534,976` | [`data/catalog_resolved_fulltexts.csv`](file:///f:/PhD%20AG/data/catalog_resolved_fulltexts.csv) |
| **Total Wave-9 Master Corpus (`1970–2025`)** | **`5,177` Full Books + `91,629` PDFs/Abstracts/Enriched** | **`354,801` documents** | **`~286,242,495` words** | **15 GitHub-Safe Shards (`<86 MB` each):**<br>• [`data/dnb_metadata.csv`](file:///f:/PhD%20AG/data/dnb_metadata.csv) (`24,000` rows, `79.52 MB`)<br>• [`data/dnb_metadata_part2.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part2.csv) (`24,000` rows, `83.25 MB`)<br>• [`data/dnb_metadata_part3.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part3.csv) (`24,000` rows, `83.64 MB`)<br>• [`data/dnb_metadata_part4.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part4.csv) (`24,000` rows, `83.22 MB`)<br>• [`data/dnb_metadata_part5.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part5.csv) (`24,000` rows, `65.14 MB`)<br>• [`data/dnb_metadata_part6.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part6.csv) (`24,000` rows, `83.76 MB`)<br>• [`data/dnb_metadata_part7.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part7.csv) (`24,000` rows, `72.26 MB`)<br>• [`data/dnb_metadata_part8.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part8.csv) (`24,000` rows, `80.64 MB`)<br>• [`data/dnb_metadata_part9.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part9.csv) (`24,000` rows, `85.37 MB`)<br>• [`data/dnb_metadata_part10.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part10.csv) (`24,000` rows, `62.45 MB`)<br>• [`data/dnb_metadata_part11.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part11.csv) (`24,000` rows, `84.19 MB`)<br>• [`data/dnb_metadata_part12.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part12.csv) (`24,000` rows, `78.42 MB`)<br>• [`data/dnb_metadata_part13.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part13.csv) (`24,000` rows, `38.13 MB`)<br>• [`data/dnb_metadata_part14.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part14.csv) (`24,000` rows, `76.70 MB`)<br>• [`data/dnb_metadata_part15.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part15.csv) (`18,801` rows, `62.60 MB`) |

---

## 🏛️ 2. Why Combine Deutsche Nationalbibliothek (DNB), Gemeinsamer Bibliotheksverbund (GBV / K10plus), HathiTrust HTRC, and OpenAlex?

1. **Complete DNB SRU v1.1 MARC21 Harvesting (`1970–2025`):** In [`scripts/dnb_harvester.py`](file:///f:/PhD%20AG/scripts/dnb_harvester.py), we query deep-paginated SRU result sets (`startRecord=1..3000` across all DNB DDC religion, theology, philosophy, psychology, ethics, and sociology divisions `DDC 200/220/230/240/250/260/270/280/290` and `DDC 100/150/170/300` for `2004–2025` and `startRecord=1..1500` for `1970–2003`, `maximumRecords=100`, `100,000+` unique DNB MARC21 records) across all 38 target German publishers and 57 thematic CQL queries. Because DNB only introduced DDC subject groups in 2004, our harvester combines DDC queries for `2004–2025` with *Gemeinsame Normdatei* (GND) subject headings (`sw=Religion*`, `sw=Theologie*`, `sw=Kirche*`, `sw=Säkular*`, `sw=Atheismus*`, `sw=Spiritualität*`, `sw=Seelsorge*`, `sw=Religionspädagogik*`, `sw=Staatskirchenrecht*`, `sw=Moraltheologie*`, `sw=Fundamentalismus*`, `sw=Lebensführung*`) for `1970–2003`, extracting `2,365` DNB-matched HathiTrust printed books (`146,077` passages), `926` sibling-matched `$z="kostenfrei"` DNB `/34` open-access full books and EPUBs (`15,122` passages), `31,992` digitized DNB `/04` `Inhaltsverzeichnis` & reading-sample PDFs/HTMLs, and `41,286` DNB `deposit.dnb.de` & `/blurb/` `Inhaltstexte`.
2. **Complete GBV / K10plus SRU Harvesting Across 41 BKL Subcodes (`maximumRecords=100`):** In [`scripts/hathitrust_fullbook_harvester.py`](file:///f:/PhD%20AG/scripts/hathitrust_fullbook_harvester.py), we query **41 fine-grained `Basisklassifikation` subcodes (`11.00–11.99`, `08.36–08.44`, `71.00–71.50`)** across all 38 German publishers (`1,053` SRU pages at `maximumRecords=100`), extracting all `MARC 020` (`$a`, `$z`, `$9`) edition/print/online ISBNs (`56,241` multi-ISBN candidates) plus `17,458` direct GBV Open-Access PDFs (`gbv_kostenfrei_fullbook_pdf`), consortial TOC PDFs/blurbs (`gbv_direct_fulltext_pdf`), and `MARC 520` / `BKL` / `GND` enriched works (`drm_fallback_multi_api_enriched`).
3. **Full-Book Extraction for In-Copyright Printed Books (`1970–2025`) via HathiTrust HTRC EF 2.0 (§ 60d UrhG):** By cross-walking all GBV K10plus and DNB multi-ISBNs (`ISBN-10` and `ISBN-13` variants) against the **HathiTrust Bibliographic API** and **HTRC Extracted Features v2.0 API**, our harvesters stream complete page-level POS-tagged token sequences for **4,002 printed German books (`243,596` passages, `~244.45M` words)** in full compliance with German scientific Text and Data Mining law (**§ 60d UrhG**, *Abgeleitete Textformate*).
4. **OpenAlex Reconstructed `abstract_inverted_index` & OA Monograph Streaming (`1970–2025`):** Querying `api.openalex.org/works` (`per-page=200`, `has_abstract:true` and `is_oa:true`) reconstructs `618` German scholarly abstracts directly from `abstract_inverted_index` (`primary_cloud_oa_abstract`) and streams Open-Access German PDFs in RAM (`entire_fulltext_book_cloud` / `primary_cloud_oa_fulltext`).
5. **FAIR / DDI Preprocessing & Metadata Separation Protocol (Santana et al., 2025; Jiménez-Badillo et al., 2020):** Following Santana, Vasques Filho, Bojanowski, & Błoch (2025, *DHQ* 19.2 [`000788.html`](https://dhq.digitalhumanities.org/vol/19/2/000788/000788.html), §55–71, §81), primary `text` fields exclude synthetic `{author}. {publisher}.` metadata headers, and [`extract_row_metadata_tokens`](file:///f:/PhD%20AG/lda_pipeline.py#L657-L683) dynamically strips row-level author/publisher/imprint tokens while preserving [`CANONICAL_THEO_PHIL_WHITELIST`](file:///f:/PhD%20AG/lda_pipeline.py#L645-L654) across LDA, Quanteda/STM, and BERTopic.

---

## 🛠️ 3. Automated Harvesting & Analytical Execution Suite

```powershell
# 1. Run the Complete DNB Harvester (DNB->HTRC + DNB /34 OA PDFs/EPUBs + DNB /04 PDFs + deposit.dnb.de Inhaltstexte)
python scripts/dnb_harvester.py

# 2. Run the Wave-9 Complete GBV/K10plus + HTRC Multi-ISBN + OpenAlex Harvester (auto-shards <86 MB across 15 shards)
python scripts/hathitrust_fullbook_harvester.py --workers 12

# 3. Run the 12-Topic Gensim LDA Pipeline across all 354,801 documents (exports app/lda_topics_report.json)
python lda_pipeline.py

# 4. Run the Quanteda + STM Analytics Suite (Komposita-Zerlegung, Dunning's G², OLS STM Regressions)
python scripts/quanteda_stm_analytics.py

# 5. Run the Neural Contextual Embedding + c-TF-IDF (BERTopic) Pipeline
python scripts/bertopic_german_pipeline.py
```

