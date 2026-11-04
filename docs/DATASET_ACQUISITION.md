# 📂 PhD Dataset Acquisition Guide: Eight-Wave Complete DNB + Full-Book Corpus (`300,412` Documents | `~245.98M` Words)

This document outlines the methodological and technical architecture for constructing the **1970–2025 full-text and national-library German book corpus (`300,412` documents/passages, `245,978,061` original German words across `55,605` unique works: `3,421` HTRC printed books, `926` DNB `/34` `$z="kostenfrei"` open-access full books & EPUBs, `155` OpenAlex/GBV open-access full books, `31,992` DNB `/04` digitized `Inhaltsverzeichnis` & reading-sample PDFs/HTMLs, `41,286` DNB `deposit.dnb.de` & `/blurb/` `Inhaltstexte`, `38` Internet Archive books, and `702` multi-API deep-enriched works)** for the dissertation **"Mediating Faith and Power: Religious Authority and the German Publishing Landscape"**.

---

## 📊 1. Cumulative Eight-Wave Master Corpus Summary (`1970–2025`)

| Corpus Tier / Source (`corpus_layer`) | Complete Full Books / Works | Full-Text Passages ($D$) | Total German Words | Storage Location |
| :--- | :---: | :---: | :---: | :--- |
| **HathiTrust HTRC Printed German Books (`1970–2025`)** *(Waves 1–4 GBV: `1,056` + Waves 5–8 DNB ISBNs: `2,365`)* | **`3,421` printed books** | `206,741` | `~208,650,000` | [`data/primary_texts/HATHITRUST_MATCHED_BOOKS.csv`](file:///f:/PhD%20AG/data/primary_texts/HATHITRUST_MATCHED_BOOKS.csv) |
| **Deutsche Nationalbibliothek (`deposit.dnb.de` & `/blurb/` `Inhaltstexte` & `MARC 520` Abstracts, `1970–2025`)** | **`41,286` DNB works** | `41,286` | `~7,150,000` | [`data/dnb_metadata_part5.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part5.csv)–[`part13.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part13.csv) |
| **DNB Digitized `/04` `Inhaltsverzeichnis` & Reading Sample PDFs/HTMLs (`1970–2025`)** | **`31,992` DNB `/04` PDFs/HTMLs** | `31,992` | `~11,480,000` | [`data/dnb_metadata_part7.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part7.csv)–[`part13.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part13.csv) |
| **DNB `/34` Sibling-Matched `$z="kostenfrei"` Open-Access Full Books & EPUBs (`1970–2025`)** | **`926` DNB OA books/EPUBs** | `15,122` | `~14,973,085` | [`data/dnb_metadata_part6.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part6.csv)–[`part13.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part13.csv) |
| **OpenAlex & GBV `Kostenfrei` OA Full Books (`1970–2025`)** | **`155` OA books/chapters** | `3,968` | `~3,190,000` | [`data/dnb_metadata.csv`](file:///f:/PhD%20AG/data/dnb_metadata.csv) (+ shards) |
| **Catalog Full-Texts (`archive.org` / Green OA) + Multi-API Enriched Books** | **`38` full books + `702` enriched** | `1,303` | `~534,976` | [`data/catalog_resolved_fulltexts.csv`](file:///f:/PhD%20AG/data/catalog_resolved_fulltexts.csv) |
| **Total Wave-8 Master Corpus (`1970–2025`)** | **`4,540` Full Books + `73,980` PDFs/Enriched (`55,605` Unique Works)** | **`300,412` documents** | **`245,978,061` words** | **13 GitHub-Safe Shards (`<86 MB` each):**<br>• [`data/dnb_metadata.csv`](file:///f:/PhD%20AG/data/dnb_metadata.csv) (`24,000` rows, `79.52 MB`)<br>• [`data/dnb_metadata_part2.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part2.csv) (`24,000` rows, `83.25 MB`)<br>• [`data/dnb_metadata_part3.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part3.csv) (`24,000` rows, `83.64 MB`)<br>• [`data/dnb_metadata_part4.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part4.csv) (`24,000` rows, `83.22 MB`)<br>• [`data/dnb_metadata_part5.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part5.csv) (`24,000` rows, `65.14 MB`)<br>• [`data/dnb_metadata_part6.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part6.csv) (`24,000` rows, `83.76 MB`)<br>• [`data/dnb_metadata_part7.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part7.csv) (`24,000` rows, `72.26 MB`)<br>• [`data/dnb_metadata_part8.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part8.csv) (`24,000` rows, `80.64 MB`)<br>• [`data/dnb_metadata_part9.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part9.csv) (`24,000` rows, `85.37 MB`)<br>• [`data/dnb_metadata_part10.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part10.csv) (`24,000` rows, `62.45 MB`)<br>• [`data/dnb_metadata_part11.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part11.csv) (`24,000` rows, `84.19 MB`)<br>• [`data/dnb_metadata_part12.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part12.csv) (`24,000` rows, `78.42 MB`)<br>• [`data/dnb_metadata_part13.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part13.csv) (`12,412` rows, `15.05 MB`) |

---

## 🏛️ 2. Why Combine Deutsche Nationalbibliothek (DNB), Gemeinsamer Bibliotheksverbund (GBV / K10plus), HathiTrust HTRC, and OpenAlex?

1. **Complete DNB SRU v1.1 MARC21 Harvesting (`1970–2025`):** In [`scripts/dnb_harvester.py`](file:///f:/PhD%20AG/scripts/dnb_harvester.py), we query deep-paginated SRU result sets (`startRecord=1..3000` across all DNB DDC religion, theology, philosophy, psychology, ethics, and sociology divisions `DDC 200/220/230/240/250/260/270/280/290` and `DDC 100/150/170/300` for `2004–2025` and `startRecord=1..1500` for `1970–2003`, `maximumRecords=100`, `100,000+` unique DNB MARC21 records) across all 38 target German publishers and 57 thematic CQL queries. Because DNB only introduced DDC subject groups in 2004, our harvester combines DDC queries for `2004–2025` with *Gemeinsame Normdatei* (GND) subject headings (`sw=Religion*`, `sw=Theologie*`, `sw=Kirche*`, `sw=Säkular*`, `sw=Atheismus*`, `sw=Spiritualität*`, `sw=Seelsorge*`, `sw=Religionspädagogik*`, `sw=Staatskirchenrecht*`, `sw=Moraltheologie*`, `sw=Fundamentalismus*`, `sw=Lebensführung*`) for `1970–2003`, extracting `2,365` DNB-matched HathiTrust printed books (`146,077` passages), `926` sibling-matched `$z="kostenfrei"` DNB `/34` open-access full books and EPUBs (`15,122` passages), `31,992` digitized DNB `/04` `Inhaltsverzeichnis` & reading-sample PDFs/HTMLs, and `41,286` DNB `deposit.dnb.de` & `/blurb/` `Inhaltstexte`.
2. **Capturing Secular-Critical, Philosophical & Sociological Works Across 35 GBV BKL Subcodes:** In [`scripts/hathitrust_fullbook_harvester.py`](file:///f:/PhD%20AG/scripts/hathitrust_fullbook_harvester.py), we query **35 fine-grained BKL subcodes (`11.01–11.80`, `08.36–08.44`, `71.11–71.50`)** across 36 German publishers and deep-paginate up to `startRecord=1250`.
3. **Full-Book Extraction for In-Copyright Printed Books (`1970–2025`) via HathiTrust HTRC EF 2.0 (§ 60d UrhG):** By cross-walking GBV K10plus and DNB ISBNs against the **HathiTrust Bibliographic API** and **HTRC Extracted Features v2.0 API**, our harvesters stream complete page-level POS-tagged token sequences for **3,421 printed German books (`206,741` passages, `~208.65M` words)** in full compliance with German scientific Text and Data Mining law (**§ 60d UrhG**, *Abgeleitete Textformate*).

---

## 🛠️ 3. Automated Harvesting & Analytical Execution Suite

```powershell
# 1. Run the Wave-8 Complete DNB Harvester (DNB->HTRC + DNB /34 OA PDFs/EPUBs + DNB /04 PDFs + deposit.dnb.de Inhaltstexte)
python scripts/dnb_harvester.py

# 2. Run the Multi-Wave GBV + HathiTrust HTRC + OpenAlex Full-Book Harvester (auto-shards <86 MB)
python scripts/hathitrust_fullbook_harvester.py

# 3. Run the 12-Topic Gensim LDA Pipeline across all 300,412 documents (exports app/lda_topics_report.json)
python lda_pipeline.py

# 4. Run the Quanteda + STM Analytics Suite (Komposita-Zerlegung, Dunning's G², OLS STM Regressions)
python scripts/quanteda_stm_analytics.py

# 5. Run the Neural Contextual Embedding + c-TF-IDF (BERTopic) Pipeline
python scripts/bertopic_german_pipeline.py
```
