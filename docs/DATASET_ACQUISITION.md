# 📂 PhD Dataset Acquisition Guide: DNB & Gemeinsamer Bibliotheksverbund (GBV / K10plus)

This document outlines the methodological and technical architecture for constructing the 1970–2025 text and metadata corpus required for the dissertation **"Mediating Faith and Power: Religious Authority and the German Publishing Landscape"**.

---

## 🏛️ 1. Why Combine Gemeinsamer Bibliotheksverbund (GBV) with DNB?

While the **Deutsche Nationalbibliothek (DNB)** provides legal-deposit coverage, relying on DNB's Dewey Decimal Classification (`dcs=200*`) alone introduces two structural blind spots for a 1970–2025 diachronic study:

1. **The Pre-2004 Historical Gap (1970–2003):** DNB only introduced DDC subject groups (*Sachgruppen nach DDC*, `200`/`230`) in **2004**. In contrast, the **Gemeinsamer Bibliotheksverbund (GBV)**—whose union catalog **GVK (Gemeinsamer Verbundkatalog)** is now merged into **K10plus** (`https://sru.k10plus.de/gvk`) across 7 German federal states and the *Staatsbibliothek zu Berlin*—uses the **Basisklassifikation (BKL, `pica.bkl`)** and **Regensburger Verbundklassifikation (RVK, `pica.rvk`)** continuously across the entire **1970–2025** window.
2. **Capturing Secular-Critical & Sociological Works Missed by DDC 200:** DNB frequently classifies philosophical and sociological critiques of religion (e.g., Charles Taylor's *Ein säkulares Zeitalter* at Suhrkamp, or works by Habermas, Sloterdijk, and Schmidt-Salomon) under `DDC 100` (Philosophy) or `DDC 300` (Social Sciences) rather than `200` (Religion). In GBV, academic subject librarians assign **multiple fine-grained BKL classes (`tag 084 $2 bkl`)** under **Hauptgruppe `11` (*Theologie, Religionswissenschaft*)** that map directly onto the three theoretical archetypes of the dissertation:

| GBV Basisklassifikation (`pica.bkl`) | German Subject Heading | Theoretical Archetype Alignment | Empirical GBV Hit Count |
| :--- | :--- | :--- | :---: |
| **`11.08`** | *Religionskritik, Atheismus* | **Critical / Secular-Humanist** (*Atheismus, Kirchenkritik, Aufklärung*) | `1,439` |
| **`11.05`** | *Religionssoziologie* | **Critical & Macro-Sociological** (*Säkularisierung, Moderne, Machtkritik*) | `6,517` |
| **`11.06`** | *Religionspsychologie* | **Neoliberal / Self-Optimization** (*Lebenshilfe, Spiritualität, Krise, Sinn*) | `3,442` |
| **`11.99`** | *Sonstige Religionen, Esoterik* | **Neoliberal / Alternative Spirituality** (*Achtsamkeit, Esoterik*) | `4,100+` |
| **`11.50`–`11.76`** | *Christentum, Dogmatik, Seelsorge* | **Traditional / Ecclesiastical** (*Kirche, Liturgie, Dogmatik, Seelsorge*) | `120,000+` |

3. **Institutional Reception Metric via Library Holdings (`MARC Tag 924`):** Every GBV MARC21-XML record contains `<datafield tag="924">` blocks listing each member university or state library (`DE-7` SUB Göttingen, `DE-1` Staatsbibliothek zu Berlin, `DE-18` SUB Hamburg, `DE-27` ThULB Jena, etc.) that acquired the book. Counting unique `924 $b` library identifiers (`gbv_holdings_count`) provides a quantifiable measure of **academic/institutional dissemination** to triangulate against commercial visibility (*Spiegel* / *Börsenblatt* bestseller lists).

---

## 🔎 2. Querying the GBV / K10plus GVK SRU Interface

The Verbundzentrale des GBV (VZG Göttingen) provides open, unauthenticated SRU v1.1 access to the GVK/K10plus union catalog:

- **Endpoint:** `https://sru.k10plus.de/gvk`
- **Schema:** `recordSchema=marcxml` (MARC21-XML) or `picaxml` (PICA+ XML)
- **Key PICA CQL Search Indexes:**
  - `pica.vlg` — Publisher name (*Verlag*, e.g., `pica.vlg="Suhrkamp"`, `pica.vlg="Alibri"`, `pica.vlg="Herder"`)
  - `pica.bkl` — Basisklassifikation (e.g., `pica.bkl=11.*` for all Religion/Theology, or `pica.bkl=11.08` specifically for *Religionskritik, Atheismus*)
  - `pica.rvk` — Regensburger Verbundklassifikation (e.g., `pica.rvk="BE*"` for Religionswissenschaft)
  - `pica.jah` — Publication year or decade wildcard (`pica.jah=197*`, `198*`, `199*`, `200*`, `201*`, `202*`)
  - `pica.tit` / `pica.all` — Title or full-record keyword search

### Empirical Publisher × BKL `11.*` Coverage in GBV (1970–2025)
- **Herder:** `7,876` records
- **Gütersloher Verlagshaus (Bertelsmann):** `3,331` records
- **S. Fischer (Holtzbrinck):** `762` records
- **Klett / Klett-Cotta:** `459` records
- **Rowohlt (Holtzbrinck):** `432` records
- **Suhrkamp:** `381` records (`1970s`: 30, `1980s`: 47, `1990s`: 61, `2000s`: 82, `2010s`: 106, `2020s`: 41)
- **Alibri Verlag (Secular/Religion-Critical):** `66` records
- **Wagenbach (Independent Left):** `39` records

---

## 🛠️ 3. Automated Harvesting Scripts (`scripts/gbv_harvester.py` & `scripts/dnb_harvester.py`)

### A. Harvesting the 1970–2025 Diachronic Corpus from GBV
Run [`scripts/gbv_harvester.py`](file:///f:/PhD%20AG/scripts/gbv_harvester.py) to harvest stratified decade slices (`1970s`–`2020s`) across all target publishers, extract `MARC 245` titles/subtitles, `490` publisher series (*Reihe*), `520` abstracts, `856` publisher blurbs (*Inhaltstext*), `650`/`689` GND *Schlagwörter*, `084` BKL/RVK classifications, and `924` library holding counts:

```powershell
# Harvest across all 1970-2025 decades for BKL 11.* (Religion & Critique)
python scripts/gbv_harvester.py --bkl "11.*" --max-per-slice 20 --output data/gbv_metadata.csv

# Harvest specifically BKL 11.08 (Religionskritik, Atheismus) across publishers
python scripts/gbv_harvester.py --bkl "11.08" --max-per-slice 50 --output data/gbv_religionskritik.csv

# Harvest GBV and automatically deduplicate + merge into data/dnb_metadata.csv for the LDA web dashboard
python scripts/gbv_harvester.py --bkl "11.*" --max-per-slice 15 --merge-dnb
```

### B. Harvesting Contemporary Records from DNB
Run [`scripts/dnb_harvester.py`](file:///f:/PhD%20AG/scripts/dnb_harvester.py) to harvest DNB Subject Group `200`/`230` records with embedded `Inhaltstext` blurbs:

```powershell
python scripts/dnb_harvester.py
```

### C. Running the Python Gensim LDA Pipeline on the Harvested Dataset
Once `data/gbv_metadata.csv` or `data/dnb_metadata.csv` is populated, run [`lda_pipeline.py`](file:///f:/PhD%20AG/lda_pipeline.py) to execute `spaCy` German lemmatization, POS filtering (`NOUN`, `PROPN`, `ADJ`), domain stopword removal, bigram detection, and Gensim LDA topic modeling:

```powershell
python lda_pipeline.py
```
