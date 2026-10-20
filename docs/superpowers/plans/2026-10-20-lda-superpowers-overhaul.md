# Full-Stack LDA Superpowers Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the German Publishing LDA platform with `nlp.pipe` batch token caching, dynamic topic granularity ($K$) selection, an interactive Coherence Optimization Curve viewer, Publisher $\times$ Topic dominance cross-tabulation, and MARC21 APA 7th Edition evidence cards.

**Architecture:** A content-addressed NLP token cache and batch `spaCy` pipeline (`disable=["ner", "parser"]`) in `lda_pipeline.py` feeds a memoized FastAPI backend (`app/main.py`) that exposes `/api/coherence-grid`, dynamic `num_topics` on `/api/run-lda`, and rich MARC21/publisher-topic telemetry on `/api/topics`. The React frontend (`useLDA.ts`, `App.tsx`, `TopicModelViz.tsx`) renders interactive $K$-regime controls, the empirical $C_v$/$U_{\text{Mass}}$ coherence curve, publisher dominance bars, and copyable APA 7th citations.

**Tech Stack:** Python 3.10, FastAPI, Gensim, spaCy (`de_core_news_lg`), React 18, TypeScript, Vite, Tailwind CSS, Recharts, Framer Motion.

---

### Task 1: Upgrade `lda_pipeline.py` with Batch `nlp.pipe`, Token Caching, Dynamic $K$, Archetype Scoring, and Structured APA Evidence

**Files:**
- Modify: `config.py`
- Modify: `lda_pipeline.py`
- Test: `tests/test_lda_pipeline.py`

- [ ] **Step 1: Add archetype lexical dictionaries in `config.py` and implement batch caching + structured outputs in `lda_pipeline.py`**
- [ ] **Step 2: Run pipeline verification test to confirm >10x speedup on cached runs and structured MARC21/APA output**

### Task 2: Extend FastAPI Backend (`app/main.py`) with Dynamic $K$, Model Memoization, and `/api/coherence-grid`

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Update `DEFAULT_DATA_SOURCE` to load `data/dnb_metadata.csv`, add `num_topics` parameter to `/api/run-lda`, add `/api/coherence-grid`, and expose `publisher_distribution` & `archetype` in `/api/topics`**
- [ ] **Step 2: Verify FastAPI endpoints via Python `TestClient` or direct handler invocation**

### Task 3: Upgrade React Frontend (`useLDA.ts`, `App.tsx`, `TopicModelViz.tsx`) & Build Production Bundle

**Files:**
- Modify: `frontend/src/hooks/useLDA.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/TopicModelViz.tsx`

- [ ] **Step 1: Extend `useLDA.ts` with `numTopics`, `coherenceGrid`, `fetchCoherenceGrid`, and `runLDA(year, decade, numTopics)`**
- [ ] **Step 2: Add Dynamic $K$ Regime Selector and interactive Coherence Optimization Curve chart to `App.tsx`**
- [ ] **Step 3: Fix $U_{\text{Mass}}$ coherence formatting, add Theoretical Archetype badge, Publisher Dominance breakdown, and APA 7th Citation Evidence cards in `TopicModelViz.tsx`**
- [ ] **Step 4: Run `npm run build` in `frontend/` and verify zero TypeScript or bundler errors**
