# 📂 PhD Dataset Acquisition Guide: Seven-Wave Exhaustive DNB + Full-Book Corpus (`233,589` Documents | `~203.78M` Words)

This document outlines the methodological and technical architecture for constructing the **1970–2025 full-text and national-library German book corpus (`233,589` documents/passages, `203,783,976` original German words across `36,434` unique works: `3,009` HTRC printed books, `675` DNB `/34` `$z="kostenfrei"` open-access full books & EPUBs, `155` OpenAlex/GBV open-access full books, `5,570` DNB `/04` digitized `Inhaltsverzeichnis` & reading-sample PDFs/HTMLs, `30,316` DNB `deposit.dnb.de` & `/blurb/` `Inhaltstexte`, `38` Internet Archive books, and `702` multi-API deep-enriched works)** for the dissertation **"Mediating Faith and Power: Religious Authority and the German Publishing Landscape"**.

---

## 📊 1. Cumulative Seven-Wave Master Corpus Summary (`1970–2025`)

| Corpus Tier / Source (`corpus_layer`) | Complete Full Books / Works | Full-Text Passages ($D$) | Total German Words | Storage Location |
| :--- | :---: | :---: | :---: | :--- |
| **HathiTrust HTRC Printed German Books (`1970–2025`)** *(Waves 1–4 GBV: `1,056` + Waves 5–7 DNB ISBNs: `1,953`)* | **`3,009` printed books** | `181,330` | `~183,240,000` | [`data/primary_texts/HATHITRUST_MATCHED_BOOKS.csv`](file:///f:/PhD%20AG/data/primary_texts/HATHITRUST_MATCHED_BOOKS.csv) |
| **Deutsche Nationalbibliothek (`deposit.dnb.de` & `/blurb/` `Inhaltstexte` & `MARC 520` Abstracts, `1970–2025`)** | **`30,316` DNB works** | `30,316` | `~5,480,000` | [`data/dnb_metadata_part5.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part5.csv)–[`part10.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part10.csv) |
| **DNB `/34` Sibling-Matched `$z="kostenfrei"` Open-Access Full Books & EPUBs (`1970–2025`)** | **`675` DNB OA books/EPUBs** | `11,102` | `~10,950,000` | [`data/dnb_metadata_part6.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part6.csv)–[`part10.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part10.csv) |
| **DNB Digitized `/04` `Inhaltsverzeichnis` & Reading Sample PDFs/HTMLs (`1970–2025`)** | **`5,570` DNB `/04` PDFs/HTMLs** | `5,570` | `~389,000` | [`data/dnb_metadata_part7.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part7.csv)–[`part10.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part10.csv) |
| **OpenAlex & GBV `Kostenfrei` OA Full Books (`1970–2025`)** | **`155` OA books/chapters** | `3,968` | `~3,190,000` | [`data/dnb_metadata.csv`](file:///f:/PhD%20AG/data/dnb_metadata.csv) (+ shards) |
| **Catalog Full-Texts (`archive.org` / Green OA) + Multi-API Enriched Books** | **`38` full books + `702` enriched** | `1,303` | `~534,976` | [`data/catalog_resolved_fulltexts.csv`](file:///f:/PhD%20AG/data/catalog_resolved_fulltexts.csv) |
| **Total Wave-7 Master Corpus (`1970–2025`)** | **`3,877` Full Books + `36,588` PDFs/Enriched (`36,434` Unique Works)** | **`233,589` documents** | **`203,783,976` words** | **10 GitHub-Safe Shards (`<86 MB` each):**<br>• [`data/dnb_metadata.csv`](file:///f:/PhD%20AG/data/dnb_metadata.csv) (`24,000` rows, `79.52 MB`)<br>• [`data/dnb_metadata_part2.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part2.csv) (`24,000` rows, `83.25 MB`)<br>• [`data/dnb_metadata_part3.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part3.csv) (`24,000` rows, `83.64 MB`)<br>• [`data/dnb_metadata_part4.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part4.csv) (`24,000` rows, `83.22 MB`)<br>• [`data/dnb_metadata_part5.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part5.csv) (`24,000` rows, `65.13 MB`)<br>• [`data/dnb_metadata_part6.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part6.csv) (`24,000` rows, `83.76 MB`)<br>• [`data/dnb_metadata_part7.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part7.csv) (`24,000` rows, `72.25 MB`)<br>• [`data/dnb_metadata_part8.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part8.csv) (`24,000` rows, `80.64 MB`)<br>• [`data/dnb_metadata_part9.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part9.csv) (`24,000` rows, `85.37 MB`)<br>• [`data/dnb_metadata_part10.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part10.csv) (`17,589` rows, `40.16 MB`) |

---

## 🏛️ 2. Why Combine Deutsche Nationalbibliothek (DNB), Gemeinsamer Bibliotheksverbund (GBV / K10plus), HathiTrust HTRC, and OpenAlex?

1. **Exhaustive DNB SRU v1.1 MARC21 Harvesting (`1970–2025`):** In [`scripts/dnb_harvester.py`](file:///f:/PhD%20AG/scripts/dnb_harvester.py), we query deep-paginated SRU result sets (`startRecord=1..2400` across `DDC 200/230` and `DDC 100/170/300` for `2004–2025` and `startRecord=1..1200` for `1970–2003`, `maximumRecords=100`, `82,535` unique DNB MARC21 records) across all 38 target German publishers and 48 thematic CQL queries. Because DNB only introduced DDC subject groups (`dcs=200*/230*`, `dcs=100*/170*/300*`) in 2004, our harvester combines DDC queries for `2004–2025` with *Gemeinsame Normdatei* (GND) subject headings (`sw=Religion*`, `sw=Theologie*`, `sw=Kirche*`, `sw=Säkular*`, `sw=Atheismus*`, `sw=Spiritualität*`, `sw=Seelsorge*`, `sw=Religionspädagogik*`, `sw=Staatskirchenrecht*`, `sw=Moraltheologie*`, `sw=Fundamentalismus*`, `sw=Lebensführung*`) for `1970–2003`, extracting `1,953` DNB-matched HathiTrust printed books (`119,691` passages), `675` sibling-matched `$z="kostenfrei"` DNB `/34` open-access full books and EPUBs (`11,102` passages), `5,570` digitized DNB `/04` `Inhaltsverzeichnis` & reading-sample PDFs/HTMLs, and `30,316` DNB `deposit.dnb.de` & `/blurb/` `Inhaltstexte`.
2. **Capturing Secular-Critical, Philosophical & Sociological Works Across 35 GBV BKL Subcodes:** In [`scripts/hathitrust_fullbook_harvester.py`](file:///f:/PhD%20AG/scripts/hathitrust_fullbook_harvester.py), we query **35 fine-grained BKL subcodes (`11.01–11.80`, `08.36–08.44`, `71.11–71.50`)** across 36 German publishers and deep-paginate up to `startRecord=1250`.
3. **Full-Book Extraction for In-Copyright Printed Books (`1970–2025`) via HathiTrust HTRC EF 2.0 (§ 60d UrhG):** By cross-walking GBV K10plus and DNB ISBNs against the **HathiTrust Bibliographic API** and **HTRC Extracted Features v2.0 API**, our harvesters stream complete page-level POS-tagged token sequences for **3,009 printed German books (`181,330` passages, `~183.24M` words)** in full compliance with German scientific Text and Data Mining law (**§ 60d UrhG**, *Abgeleitete Textformate*).

---

## 🛠️ 3. Automated Harvesting & Analytical Execution Suite

```powershell
# 1. Run the Wave-7 Exhaustive DNB Harvester (DNB->HTRC + DNB /34 OA PDFs/EPUBs + DNB /04 PDFs + deposit.dnb.de Inhaltstexte)
python scripts/dnb_harvester.py

# 2. Run the Multi-Wave GBV + HathiTrust HTRC + OpenAlex Full-Book Harvester (auto-shards <86 MB)
python scripts/hathitrust_fullbook_harvester.py

# 3. Run the 12-Topic Gensim LDA Pipeline across all 233,589 documents (exports app/lda_topics_report.json)
python lda_pipeline.py

# 4. Run the Quanteda + STM Analytics Suite (Komposita-Zerlegung, Dunning's G², OLS STM Regressions)
python scripts/quanteda_stm_analytics.py

# 5. Run the Neural Contextual Embedding + c-TF-IDF (BERTopic) Pipeline
python scripts/bertopic_german_pipeline.py
```
