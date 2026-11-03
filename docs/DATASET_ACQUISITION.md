# 📂 PhD Dataset Acquisition Guide: Five-Wave DNB + Full-Book Corpus (`114,624` Documents | `~104.79M` Words)

This document outlines the methodological and technical architecture for constructing the **1970–2025 full-text and national-library German book corpus (`114,624` documents/passages, `104,789,406` original German words across `1,841` complete full-text books, `10,760` DNB `deposit.dnb.de` `Inhaltstexte`, and `698` multi-API deep-enriched works)** for the dissertation **"Mediating Faith and Power: Religious Authority and the German Publishing Landscape"**.

---

## 📊 1. Cumulative Five-Wave Master Corpus Summary (`1970–2025`)

| Corpus Tier / Source (`corpus_layer`) | Complete Full Books / Works | Full-Text Passages ($D$) | Total German Words | Storage Location |
| :--- | :---: | :---: | :---: | :--- |
| **HathiTrust HTRC Printed German Books (`1970–2025`)** *(Waves 1–4 GBV: `1,056` + Wave 5 DNB ISBNs: `592`)* | **`1,648` printed books** | `98,576` | `~99,220,000` | [`data/primary_texts/HATHITRUST_MATCHED_BOOKS.csv`](file:///f:/PhD%20AG/data/primary_texts/HATHITRUST_MATCHED_BOOKS.csv) |
| **Deutsche Nationalbibliothek (`deposit.dnb.de` `Inhaltstexte` & `MARC 520` Abstracts, `1970–2025`)** | **`10,760` DNB works** | `10,760` | `~1,835,000` | [`data/dnb_metadata_part5.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part5.csv) |
| **OpenAlex, GBV `Kostenfrei` & DNB OA Full Books (`1970–2025`)** | **`155` OA books/chapters** | `4,069` | `~3,190,000` | [`data/dnb_metadata.csv`](file:///f:/PhD%20AG/data/dnb_metadata.csv) (+ shards) |
| **Catalog Full-Texts (`archive.org` / Green OA) + Multi-API Enriched Books** | **`38` full books + `698` enriched** | `1,219` | `~544,406` | [`data/catalog_resolved_fulltexts.csv`](file:///f:/PhD%20AG/data/catalog_resolved_fulltexts.csv) |
| **Total Wave-5 Master Corpus (`1970–2025`)** | **`1,841` Full Books + `11,458` Enriched (`13,299` Works)** | **`114,624` documents** | **`104,789,406` words** | **5 GitHub-Safe Shards (`<85 MB` each):**<br>• [`data/dnb_metadata.csv`](file:///f:/PhD%20AG/data/dnb_metadata.csv) (`24,000` rows, `79.52 MB`)<br>• [`data/dnb_metadata_part2.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part2.csv) (`24,000` rows, `83.25 MB`)<br>• [`data/dnb_metadata_part3.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part3.csv) (`24,000` rows, `83.64 MB`)<br>• [`data/dnb_metadata_part4.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part4.csv) (`24,000` rows, `83.22 MB`)<br>• [`data/dnb_metadata_part5.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part5.csv) (`18,624` rows, `46.72 MB`) |

---

## 🏛️ 2. Why Combine Deutsche Nationalbibliothek (DNB), Gemeinsamer Bibliotheksverbund (GBV / K10plus), HathiTrust HTRC, and OpenAlex?

1. **Full-Scale DNB SRU v1.1 MARC21 Harvesting (`1970–2025`):** In [`scripts/dnb_harvester.py`](file:///f:/PhD%20AG/scripts/dnb_harvester.py), we query `317` paginated SRU result sets (`maximumRecords=100`, `24,910` unique DNB MARC21 records) across all 38 target German publishers and 20 thematic CQL queries. Because DNB only introduced DDC subject groups (`dcs=200*/230*`) in 2004, our harvester combines DDC queries for `2004–2025` with *Gemeinsame Normdatei* (GND) subject headings (`sw=Religion*`, `sw=Theologie*`, `sw=Kirche*`, `sw=Säkular*`, `sw=Atheismus*`, `sw=Spiritualität*`, `sw=Seelsorge*`) for `1970–2003`, extracting `592` new DNB-matched HathiTrust printed books (`36,425` passages), DNB open-access PDFs (`d-nb.info/.../34`), and `10,760` DNB `deposit.dnb.de` `Inhaltstexte`.
2. **Capturing Secular-Critical, Philosophical & Sociological Works Across 35 GBV BKL Subcodes:** In [`scripts/hathitrust_fullbook_harvester.py`](file:///f:/PhD%20AG/scripts/hathitrust_fullbook_harvester.py), we query **35 fine-grained BKL subcodes (`11.01–11.80`, `08.36–08.44`, `71.11–71.50`)** across 36 German publishers and deep-paginate up to `startRecord=1250`.
3. **Full-Book Extraction for In-Copyright Printed Books (`1970–2025`) via HathiTrust HTRC EF 2.0 (§ 60d UrhG):** By cross-walking GBV K10plus and DNB ISBNs against the **HathiTrust Bibliographic API** and **HTRC Extracted Features v2.0 API**, our harvesters stream complete page-level POS-tagged token sequences for **1,648 printed German books (`98,576` passages, `~99.22M` words)** in full compliance with German scientific Text and Data Mining law (**§ 60d UrhG**, *Abgeleitete Textformate*).

---

## 🛠️ 3. Automated Harvesting & Analytical Execution Suite

```powershell
# 1. Run the Wave-5 DNB Full-Scale Harvester (DNB->HTRC + DNB OA + deposit.dnb.de Inhaltstexte)
python scripts/dnb_harvester.py

# 2. Run the Multi-Wave GBV + HathiTrust HTRC + OpenAlex Full-Book Harvester (auto-shards <85 MB)
python scripts/hathitrust_fullbook_harvester.py

# 3. Run the 12-Topic Gensim LDA Pipeline across all 114,624 documents (exports app/lda_topics_report.json)
python lda_pipeline.py

# 4. Run the Quanteda + STM Analytics Suite (Komposita-Zerlegung, Dunning's G², OLS STM Regressions)
python scripts/quanteda_stm_analytics.py

# 5. Run the Neural Contextual Embedding + c-TF-IDF (BERTopic) Pipeline
python scripts/bertopic_german_pipeline.py
```
