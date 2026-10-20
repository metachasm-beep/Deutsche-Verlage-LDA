# Superpowers Design Specification: Full-Stack LDA Efficiency & Comprehensiveness Overhaul

**Date:** 2026-10-20  
**Author:** Paul Marandi, Ph.D. Scholar, CGS, SLL&CS, JNU  
**Methodology:** Superpowers (`brainstorming` $\rightarrow$ `writing-plans` $\rightarrow$ `test-driven-development` $\rightarrow$ `verification-before-completion`)

---

## 1. Audit Summary: Was the Frontend Updated?

Prior to this overhaul, the backend data harvest (`data/dnb_metadata.csv`, $N = 160$ enriched DNB records) and the offline coherence grid search (`data/coherence_grid_results.csv`) were completed, **but the React frontend and FastAPI endpoints had not yet been updated** to expose or optimize these capabilities:

1. **Coherence Display Bug in [`TopicModelViz.tsx`](file:///f:/PhD%20AG/frontend/src/components/TopicModelViz.tsx#L143):** The frontend multiplied `coherenceScore` by `100` (`(coherenceScore * 100).toFixed(1)%`), which converted negative $U_{\text{Mass}}$ log-likelihood ratios (e.g., `-5.04`) into invalid negative percentages (`-504.3%`).
2. **Hardcoded Topic Count ($K = 10$):** Neither [`app/main.py`](file:///f:/PhD%20AG/app/main.py#L126) nor [`App.tsx`](file:///f:/PhD%20AG/frontend/src/App.tsx#L240-L280) allowed the researcher to dynamically select the number of topics $K$ (such as switching between the empirically validated $K=4$ Macro-Archetype peak, $K=12$ Meso-Inflection, and $K=20\text{--}30$ Micro-Thematic peak) or inspect the empirical Coherence Curve inside the dashboard.
3. **Unstructured Evidence Snippets:** Representative documents returned only raw concatenated strings rather than structured MARC21 metadata (`title`, `author`, `publisher`, `date`, `keywords`, `probability`, and formatted **APA 7th Edition Citations**).
4. **Uncached $O(N)$ NLP Preprocessing Bottleneck:** Every click on a year, decade, or topic count re-ran `nlp(text)` sequentially for every row without batching (`nlp.pipe`) or token memoization.

---

## 2. System Architecture & Component Design

### 2.1 High-Efficiency NLP & Model Caching Engine ([`lda_pipeline.py`](file:///f:/PhD%20AG/lda_pipeline.py))
- **Content-Addressed Token Memoization:** Compute an MD5/SHA1 digest for each document's raw `text` and cache its lemmatized, POS-filtered, weighted German tokens in memory (`_TOKEN_CACHE`) and on disk (`data/token_cache.json`). Subsequent LDA runs (across different $K$, years, or decades) skip `spaCy` inference entirely for previously seen documents, accelerating interactive slicing by **15x–30x**.
- **Vectorized Batch Processing (`nlp.pipe`):** For uncached documents (such as newly uploaded CSVs), process texts in batches via `nlp.pipe(uncached_texts, batch_size=32, disable=["ner", "parser"])` since only `tagger`, `morphologizer`, and `lemmatizer` are needed for `NOUN/PROPN/ADJ` lemma extraction.
- **Dynamic $K$ (`num_topics`) Parameterization:** Allow `run_pipeline(data_path, num_topics=None)` to accept any $K \in [2, 50]$ dynamically.
- **Structured MARC21 Evidence & Publisher-Topic Cross-Tabulation:** Return structured evidence objects containing:
  - `title`, `author`, `publisher`, `date`, `keywords` (*Schlagwörter*), `snippet` (*Inhaltstext*), `probability` ($\theta_{d,k}$), and an auto-formatted `apa_citation` (`Author (Year). *Title*. Publisher.`).
  - Compute the **Publisher $\times$ Topic Dominance Matrix** (`publisher_topic_matrix`), measuring each publisher's average topic weight across all $K$ clusters, and classify each cluster against the three theoretical archetypes (*Traditional/Ecclesiastical*, *Neoliberal/Entrepreneurial*, *Critical/Secular-Humanist*).

### 2.2 FastAPI Backend Extensions ([`app/main.py`](file:///f:/PhD%20AG/app/main.py))
- **Enhanced `POST /api/run-lda`:** Accept `num_topics: int = Query(None)` alongside `year` and `decade`, with in-memory model result memoization keyed by `(data_path, mtime, num_topics, year, decade)`.
- **Enhanced `GET /api/topics`:** Return `topics` (with archetype affinity badges), `coherence_score` ($U_{\text{Mass}}$), `cv_coherence` (from grid search or model), `representative_docs` (structured MARC21 + APA citation objects), `publisher_matrix` (Publisher $\times$ Topic distribution), and `num_topics`.
- **New `GET /api/coherence-grid`:** Serve the empirical hyperparameter optimization curve (`k`, `c_v`, `u_mass`, `log_perplexity`) from `data/coherence_grid_results.csv` so the React frontend can render an interactive Coherence Optimization Chart.
- **Auto-Sync Harvested DNB Corpus:** Ensure `app/main.py` prioritizes `data/dnb_metadata.csv` (the 160 enriched DNB records) automatically on startup.

### 2.3 React Frontend Overhaul ([`App.tsx`](file:///f:/PhD%20AG/frontend/src/App.tsx), [`TopicModelViz.tsx`](file:///f:/PhD%20AG/frontend/src/components/TopicModelViz.tsx), [`useLDA.ts`](file:///f:/PhD%20AG/frontend/src/hooks/useLDA.ts))
- **Dynamic Topic Granularity ($K$) Selector & Coherence Curve Modal/Panel:**
  - In the *Neural Engine* card of [`App.tsx`](file:///f:/PhD%20AG/frontend/src/App.tsx), add interactive regime presets ($K=4$ *Macro-Archetypes*, $K=10$ *Baseline*, $K=12$ *Meso-Inflection*, $K=20$ *High-Res*, $K=30$ *Micro-Peak*) plus a custom $K$ slider, paired with an interactive **Empirical Coherence Curve ($C_v$ & $U_{\text{Mass}}$)** chart where clicking any $K$ point immediately trains/loads that $K$ resolution.
- **Accurate Coherence & Archetype Telemetry in [`TopicModelViz.tsx`](file:///f:/PhD%20AG/frontend/src/components/TopicModelViz.tsx):**
  - Display $U_{\text{Mass}}$ coherence accurately in log-ratio units (e.g., `U_Mass: -5.04`) alongside the corresponding $C_v$ score (`C_v: 0.401`) and an **Ideological Archetype Badge** (*Traditional Ecclesiastical*, *Neoliberal / Self-Optimization*, or *Critical / Secular-Humanist*).
- **Publisher $\times$ Topic Dominance Breakdown & APA Evidence Cards:**
  - Show which German publishers dominate the currently selected topic cluster (e.g., `Herder: 34%`, `Suhrkamp: 28%`).
  - Upgrade the *Primary Textual Evidence* cards to display the publication's Title, Author, Publisher, Year, Topic Probability ($\theta_{d,k}$), GND *Schlagwörter* pills, and a one-click **Copy APA Citation** button.
