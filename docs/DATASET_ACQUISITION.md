# 📂 PhD Dataset Acquisition Guide: Four-Wave Full-Book Corpus (`67,323` Passages | `~66.53M` Words)

This document outlines the methodological and technical architecture for constructing the **1970–2025 full-text German book corpus (`67,323` passages, `66,534,607` original German words across `1,248` complete full-text books and `698` multi-API deep-enriched works)** for the dissertation **"Mediating Faith and Power: Religious Authority and the German Publishing Landscape"**.

---

## 📊 1. Cumulative Four-Wave Master Corpus Summary (`1970–2025`)

| Corpus Tier / Source (`corpus_layer`) | Complete Full Books / Works | Full-Text Passages ($D$) | Total German Words | Storage Location |
| :--- | :---: | :---: | :---: | :--- |
| **HathiTrust HTRC Printed German Books (`1970–2025`)** *(Wave 1: `80` + Wave 2: `159` + Wave 3: `199` + Wave 4: `618`)* | **`1,056` printed books** | `62,151` | `~61,480,112` | [`data/primary_texts/HATHITRUST_MATCHED_BOOKS.csv`](file:///f:/PhD%20AG/data/primary_texts/HATHITRUST_MATCHED_BOOKS.csv) |
| **OpenAlex & GBV `Kostenfrei` German OA Books & Chapters (`1970–2025`)** *(Waves 1–3: `103` + Wave 4: `51`)* | **`154` OA books/chapters** | `3,457` | `~3,409,888` | [`data/dnb_metadata.csv`](file:///f:/PhD%20AG/data/dnb_metadata.csv) (+ shards) |
| **Catalog Full-Texts (`archive.org` / Green OA) + Multi-API Enriched Books** | **`38` full books + `698` enriched** | `1,715` | `~1,644,607` | [`data/catalog_resolved_fulltexts.csv`](file:///f:/PhD%20AG/data/catalog_resolved_fulltexts.csv) |
| **Total Wave-4 Master Corpus (`1970–2025`)** | **`1,248` Full Books + `698` Enriched (`1,946` Works)** | **`67,323` passages** | **`66,534,607` words** | **3 GitHub-Safe Shards (`<85 MB` each):**<br>• [`data/dnb_metadata.csv`](file:///f:/PhD%20AG/data/dnb_metadata.csv) (`24,000` rows, `79.11 MB`)<br>• [`data/dnb_metadata_part2.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part2.csv) (`24,000` rows, `82.84 MB`)<br>• [`data/dnb_metadata_part3.csv`](file:///f:/PhD%20AG/data/dnb_metadata_part3.csv) (`19,323` rows, `66.89 MB`) |

---

## 🏛️ 2. Why Combine Gemeinsamer Bibliotheksverbund (GBV / K10plus), HathiTrust HTRC, OpenAlex, and DNB?

While the **Deutsche Nationalbibliothek (DNB)** provides legal-deposit coverage, relying on DNB's Dewey Decimal Classification (`dcs=200*`) alone introduces two structural blind spots for a 1970–2025 diachronic study:

1. **The Pre-2004 Historical Gap (1970–2003):** DNB only introduced DDC subject groups (*Sachgruppen nach DDC*, `200`/`230`) in **2004**. In contrast, the **Gemeinsamer Bibliotheksverbund (GBV)**—whose union catalog **GVK (Gemeinsamer Verbundkatalog)** is now merged into **K10plus** (`https://sru.k10plus.de/gvk`) across 7 German federal states and the *Staatsbibliothek zu Berlin*—uses the **Basisklassifikation (BKL, `pica.bkl`)** and **Regensburger Verbundklassifikation (RVK, `pica.rvk`)** continuously across the entire **1970–2025** window.
2. **Capturing Secular-Critical, Philosophical & Sociological Works Across 35 BKL Subcodes:** DNB frequently classifies philosophical and sociological critiques of religion (e.g., Charles Taylor's *Ein säkulares Zeitalter* at Suhrkamp, or works by Habermas, Sloterdijk, and Schmidt-Salomon) under `DDC 100` (Philosophy) or `DDC 300` (Social Sciences) rather than `200` (Religion). In [`scripts/hathitrust_fullbook_harvester.py`](file:///f:/PhD%20AG/scripts/hathitrust_fullbook_harvester.py), we query **35 fine-grained BKL subcodes (`11.01–11.80`, `08.36–08.44`, `71.11–71.50`)** across 36 German publishers and deep-paginate up to `startRecord=1250`:

| GBV Basisklassifikation (`pica.bkl`) | German Subject Heading | Theoretical Archetype Alignment | Empirical GBV Hit Count |
| :--- | :--- | :--- | :---: |
| **`11.08`** | *Religionskritik, Atheismus* | **Critical / Secular-Humanist** (*Atheismus, Kirchenkritik, Aufklärung*) | `1,439` |
| **`11.05` & `71.11–71.50`** | *Religionssoziologie, Kultursoziologie, Sozialstruktur* | **Critical & Macro-Sociological** (*Säkularisierung, Moderne, Machtkritik*) | `18,500+` |
| **`11.06` & `08.36–08.44`** | *Religionspsychologie, Religionsphilosophie, Ethik* | **Neoliberal / Self-Optimization & Philosophical** (*Lebenshilfe, Spiritualität, Sinn*) | `14,200+` |
| **`11.99`** | *Sonstige Religionen, Esoterik* | **Neoliberal / Alternative Spirituality** (*Achtsamkeit, Esoterik*) | `4,100+` |
| **`11.50`–`11.80`** | *Christentum, Dogmatik, Seelsorge, Praktische Theologie* | **Traditional / Ecclesiastical** (*Kirche, Liturgie, Dogmatik, Seelsorge*) | `120,000+` |

3. **Full-Book Extraction for In-Copyright Printed Books (`1970–2025`) via HathiTrust HTRC EF 2.0 (§ 60d UrhG):** By cross-walking GBV K10plus ISBNs, OCLC numbers, and normalized title/author keys against the **HathiTrust Bibliographic API** and **HTRC Extracted Features v2.0 API**, [`scripts/hathitrust_fullbook_harvester.py`](file:///f:/PhD%20AG/scripts/hathitrust_fullbook_harvester.py) downloads complete page-level POS-tagged token streams for **1,056 printed German books (`62,151` passages, `~61.48M` words)** in full compliance with German scientific Text and Data Mining law (**§ 60d UrhG**, *Abgeleitete Textformate*).

---

## 🛠️ 3. Automated Harvesting & Analytical Execution Suite

```powershell
# 1. Run the Multi-Wave HathiTrust HTRC + OpenAlex Full-Book Harvester (auto-shards <85 MB)
python scripts/hathitrust_fullbook_harvester.py

# 2. Run the 12-Topic Gensim LDA Pipeline across all 67,323 passages (exports app/lda_topics_report.json)
python lda_pipeline.py

# 3. Run the Quanteda + STM Analytics Suite (Komposita-Zerlegung, Dunning's G², OLS STM Regressions)
python scripts/quanteda_stm_analytics.py

# 4. Run the Neural Contextual Embedding + c-TF-IDF (BERTopic) Pipeline
python scripts/bertopic_german_pipeline.py
```
