# 📂 PhD Dataset Acquisition Guide: Six-Wave Ultra-Deep DNB + Full-Book Corpus (`169,756` Documents | `~152.06M` Words)

This document outlines the methodological and technical architecture for constructing the **1970–2025 full-text and national-library German book corpus (`169,756` documents/passages, `152,061,795` original German words across `22,478` unique works: `2,311` HTRC printed books, `455` DNB `/34` `$z="kostenfrei"` & OpenAlex/GBV open-access full books, `574` DNB `/04` digitized `Inhaltsverzeichnis` & reading-sample PDFs, `19,527` DNB `deposit.dnb.de` & `/blurb/` `Inhaltstexte`, `38` Internet Archive books, and `702` multi-API deep-enriched works)** for the dissertation **"Mediating Faith and Power: Religious Authority and the German Publishing Landscape"**.

---

## 📊 1. Cumulative Six-Wave Master Corpus Summary (`1970–2025`)

| Corpus Tier / Source (`corpus_layer`) | Complete Full Books / Works | Full-Text Passages ($D$) | Total German Words | Storage Location |
| :--- | :---: | :---: | :---: | :--- |
| **HathiTrust HTRC Printed German Books (`1970–2025`)** *(Waves 1–4 GBV: `1,056` + Waves 5–6 DNB ISBNs: `1,255`)* | **`2,311` printed books** | `139,538` | `~140,695,000` | [`data/primary_texts/HATHITRUST_MATCHED_BOOKS.csv`](file:///f:/PhD%20AG/data/primary_texts/HATHITRUST_MATCHED_BOOKS.csv) |
| **Deutsche Nationalbibliothek (`deposit.dnb.de` & `/blurb/` `Inhaltstexte` & `MARC 520` Abstracts, `1970–2025`)** | **`19,527` DNB works** | `19,527` | `~3,420,000` | [`data/dnb_metadata_part5.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part5.csv)–[`part8.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part8.csv) |
| **DNB `/34` Sibling-Matched `$z="kostenfrei"` Open-Access Full Books (`1970–2025`)** | **`300` DNB OA books** | `4,846` | `~4,846,000` | [`data/dnb_metadata_part6.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part6.csv)–[`part8.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part8.csv) |
| **OpenAlex & GBV `Kostenfrei` OA Full Books (`1970–2025`)** | **`155` OA books/chapters** | `3,968` | `~3,190,000` | [`data/dnb_metadata.csv`](file:///f:/PhD%20AG/data/dnb_metadata.csv) (+ shards) |
| **DNB Digitized `/04` `Inhaltsverzeichnis` & Reading Sample PDFs (`1970–2025`)** | **`574` DNB `/04` PDFs** | `574` | `~366,000` | [`data/dnb_metadata_part7.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part7.csv)–[`part8.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part8.csv) |
| **Catalog Full-Texts (`archive.org` / Green OA) + Multi-API Enriched Books** | **`38` full books + `702` enriched** | `1,303` | `~544,795` | [`data/catalog_resolved_fulltexts.csv`](file:///f:/PhD%20AG/data/catalog_resolved_fulltexts.csv) |
| **Total Wave-6 Master Corpus (`1970–2025`)** | **`2,804` Full Books + `20,803` Enriched (`22,478` Unique Works)** | **`169,756` documents** | **`152,061,795` words** | **8 GitHub-Safe Shards (`<85 MB` each):**<br>• [`data/dnb_metadata.csv`](file:///f:/PhD%20AG/data/dnb_metadata.csv) (`24,000` rows, `79.52 MB`)<br>• [`data/dnb_metadata_part2.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part2.csv) (`24,000` rows, `83.25 MB`)<br>• [`data/dnb_metadata_part3.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part3.csv) (`24,000` rows, `83.64 MB`)<br>• [`data/dnb_metadata_part4.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part4.csv) (`24,000` rows, `83.22 MB`)<br>• [`data/dnb_metadata_part5.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part5.csv) (`24,000` rows, `65.13 MB`)<br>• [`data/dnb_metadata_part6.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part6.csv) (`24,000` rows, `83.76 MB`)<br>• [`data/dnb_metadata_part7.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part7.csv) (`24,000` rows, `72.25 MB`)<br>• [`data/dnb_metadata_part8.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part8.csv) (`1,756` rows, `3.45 MB`) |

---

## 🏛️ 2. Why Combine Deutsche Nationalbibliothek (DNB), Gemeinsamer Bibliotheksverbund (GBV / K10plus), HathiTrust HTRC, and OpenAlex?

1. **Ultra-Deep DNB SRU v1.1 MARC21 Harvesting (`1970–2025`):** In [`scripts/dnb_harvester.py`](file:///f:/PhD%20AG/scripts/dnb_harvester.py), we query deep-paginated SRU result sets (`startRecord=1..1400` for `2004–2025` and `startRecord=1..700` for `1970–2003`, `maximumRecords=100`, `47,306` unique DNB MARC21 records) across all 38 target German publishers and 32 thematic CQL queries. Because DNB only introduced DDC subject groups (`dcs=200*/230*`) in 2004, our harvester combines DDC queries for `2004–2025` with *Gemeinsame Normdatei* (GND) subject headings (`sw=Religion*`, `sw=Theologie*`, `sw=Kirche*`, `sw=Säkular*`, `sw=Atheismus*`, `sw=Spiritualität*`, `sw=Seelsorge*`, `sw=Religionspädagogik*`, `sw=Staatskirchenrecht*`, `sw=Moraltheologie*`) for `1970–2003`, extracting `1,255` DNB-matched HathiTrust printed books (`77,899` passages), `300` sibling-matched `$z="kostenfrei"` DNB `/34` open-access full books (`4,846` passages), `574` digitized DNB `/04` `Inhaltsverzeichnis` & reading-sample PDFs, and `19,527` DNB `deposit.dnb.de` & `/blurb/` `Inhaltstexte`.
2. **Capturing Secular-Critical, Philosophical & Sociological Works Across 35 GBV BKL Subcodes:** In [`scripts/hathitrust_fullbook_harvester.py`](file:///f:/PhD%20AG/scripts/hathitrust_fullbook_harvester.py), we query **35 fine-grained BKL subcodes (`11.01–11.80`, `08.36–08.44`, `71.11–71.50`)** across 36 German publishers and deep-paginate up to `startRecord=1250`.
3. **Full-Book Extraction for In-Copyright Printed Books (`1970–2025`) via HathiTrust HTRC EF 2.0 (§ 60d UrhG):** By cross-walking GBV K10plus and DNB ISBNs against the **HathiTrust Bibliographic API** and **HTRC Extracted Features v2.0 API**, our harvesters stream complete page-level POS-tagged token sequences for **2,311 printed German books (`139,538` passages, `~140.70M` words)** in full compliance with German scientific Text and Data Mining law (**§ 60d UrhG**, *Abgeleitete Textformate*).

---

## 🛠️ 3. Automated Harvesting & Analytical Execution Suite

```powershell
# 1. Run the Wave-6 Ultra-Deep DNB Harvester (DNB->HTRC + DNB /34 OA + DNB /04 PDFs + deposit.dnb.de Inhaltstexte)
python scripts/dnb_harvester.py

# 2. Run the Multi-Wave GBV + HathiTrust HTRC + OpenAlex Full-Book Harvester (auto-shards <85 MB)
python scripts/hathitrust_fullbook_harvester.py

# 3. Run the 12-Topic Gensim LDA Pipeline across all 169,756 documents (exports app/lda_topics_report.json)
python lda_pipeline.py

# 4. Run the Quanteda + STM Analytics Suite (Komposita-Zerlegung, Dunning's G², OLS STM Regressions)
python scripts/quanteda_stm_analytics.py

# 5. Run the Neural Contextual Embedding + c-TF-IDF (BERTopic) Pipeline
python scripts/bertopic_german_pipeline.py
```
