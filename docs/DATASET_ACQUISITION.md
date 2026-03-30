# 📂 PhD Dataset Acquisition Guide

This document outlines the strategic steps to acquire the "curated dataset of publisher catalogs, editorial statements, and religious publications" required for the LDA analysis.

## 🎯 1. German National Library (DNB) Harvesting
The DNB is the primary source for book metadata and catalog structures. Access is free under CC0 via their **SRU Interface**.

### Strategy:
- **Scope**: Bibliographic data for Bertelsmann, Suhrkamp, Holtzbrinck, Klett, and Alibri.
- **Protocol**: Use the [SRU (Search/Retrieve via URL)](https://www.dnb.de/EN/Service/Metadatendienste/Schnittstellen/sru.html).
- **Execution**:
  ```python
  # Example DNB Query for Bertelsmann publications
  import requests
  base_url = "https://services.dnb.de/sru/dnb"
  params = {
      'operation': 'searchRetrieve',
      'version': '1.1',
      'query': 'publisher="Bertelsmann"',
      'recordSchema': 'MARC21-xml'
  }
  response = requests.get(base_url, params=params)
  ```

## 🌐 2. Historical Editorial Statements (Wayback Machine)
To capture "discursive institutional mediation" and "neoliberal spirituality" in editorial practices, we must harvest historical "About Us" and "Mission Statement" pages.

### Strategy:
- **Tool**: [Wayback Machine CDX API](https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server).
- **Targets**: `bertelsmann.com`, `suhrkamp.de`, `holtzbrinck.com`.
- **Logic**: Extract snapshots from the late 20th century to the present.

## ⛪ 3. Religious and Spiritual Publications
The synopsis specifies the nexus between religion and economic ventures.

### Strategy:
- **Source**: DNB Subject Group 200 (Religion) filtered by the target publishers.
- **Archive.org**: Searching for digitised "faith narratives" and "neoliberal spirituality" brochures.

---

## 🛠️ Implementation Steps for Antigravity

> [!TIP]
> **Action Plan**:
> 1.  **Phase 1**: Run the DNB Metadata Harvester (I can write this script next).
> 2.  **Phase 2**: Use `deep-research` with your **Gemini API Key** to synthesize the qualitative "Editorial Statements" from the web archive.
> 3.  **Phase 3**: Clean and merge into `corpus_final.csv`.

### How to set your API Key:
1.  Locate `f:\PhD AG\.agent\skills\deep-research\`.
2.  Create a file named `.env`.
3.  Add the line: `GEMINI_API_KEY=your_key_here`.
4.  Optionally, set it in your system environment: `setx GEMINI_API_KEY "your_key_here"` (Windows).
