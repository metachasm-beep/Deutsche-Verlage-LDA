# Frontend Redesign Specification: "Suhrkamp Archival Brutalism × OLED Observatory"

**Date:** 2026-10-20  
**Author:** Paul Marandi, Ph.D. Scholar, CGS, SLL&CS, JNU  
**Skills Applied:** `superpowers:brainstorming`, `superpowers:writing-plans`, `frontend-design`, `ui-ux-pro-max`, `design-spells`, `kpi-dashboard-design`

---

## 1. Design Direction Summary & DFII Evaluation

- **Aesthetic Stance:** **Suhrkamp Archival Brutalism × OLED Observatory** — marries the austere typographic authority of post-war German intellectual monographs (*edition suhrkamp*, *Verlag Herder*) with a high-contrast OLED computational telemetry console.
- **DFII Score:** `15 / 15` (`Impact: 5 + Context Fit: 5 + Feasibility: 5 + Performance: 4 - Consistency Risk: 1`) $\rightarrow$ **Execute Fully**.
- **Differentiation Callout:** *This avoids generic AI dashboard UI by replacing uniform SaaS cards with an Editorial Monograph Masthead, a 5-Metric Executive Scholarly KPI Ribbon, an Ideological Archetype Color Coding System (Ecclesiastical Gold, Neoliberal Cyan, Critical Rose), and a Multi-Tab Computational Hermeneutics Workbench.*

---

## 2. Design System Snapshot

### 2.1 Typography (Loaded via Google Fonts in `frontend/index.html`)
- **Display & Editorial Headings (`--font-heading`):** `Cormorant Garamond` & `Crimson Pro` (600/700, italic & roman) — evokes German print scholarship and theological folios.
- **UI & Analytical Prose (`--font-body`):** `Plus Jakarta Sans` & `Atkinson Hyperlegible` (400/500/600) — engineered for maximum legibility at dense dashboard scales.
- **Quantitative Telemetry & MARC21 Codes (`--font-mono`):** `JetBrains Mono` (400/600) — tabular numerals for $\theta_{d,k}$ probabilities, $U_{\text{Mass}}$, $C_v$, and MARC21 field tags (`245$a`, `650$a`, `856$u`).

### 2.2 Semantic Color Architecture (Ideological Archetypes)
- **Canvas Surfaces:** Obsidian Ink (`#070709`), Folio Charcoal (`#0E1015`), Hairline Rule (`rgba(255, 255, 255, 0.08)`).
- **Archetype 1 — Traditional / Ecclesiastical:** Liturgical Gold (`#EAB308`, border `rgba(234, 179, 8, 0.35)`).
- **Archetype 2 — Neoliberal / Self-Optimization:** Market Cyan (`#38BDF8`, border `rgba(56, 189, 248, 0.35)`).
- **Archetype 3 — Critical / Secular-Humanist:** Dialectical Rose (`#FB7185`, border `rgba(251, 113, 133, 0.35)`).

---

## 3. Structural & Interactive Architecture

1. **Floating Archival Command Bar (`Navbar`):**
   - Displays monograph edition badge (`EDITION CGS · JNU // DISSERTATION OBSERVATORY`), live corpus status pill, active $K$ indicator, and quick-action buttons (`Ingest CSV`, `Export JSON Dossier`, `Reload DNB SRU`).
2. **Executive Scholarly KPI Ribbon (5 Cards):**
   - **KPI 1 — Corpus Volume ($M$):** Total harvested DNB records (`160` monographs) + temporal span (`2005–2027`).
   - **KPI 2 — Lexical Space ($|V|$):** Unique lemmatized German nouns, proper nouns, adjectives & bigrams (`3,712` tokens).
   - **KPI 3 — Topic Granularity ($K$):** Active latent cluster count (`K = 12` Meso-Inflection) with regime classification.
   - **KPI 4 — Intrinsic & Extrinsic Coherence:** Dual readout of $C_v$ NPMI (`0.3905`) and $U_{\text{Mass}}$ (`-8.95`).
   - **KPI 5 — Hegemonic Discursive Voice:** Displays the dominant ideological archetype across the active temporal slice with percentage share.
3. **Interactive Multi-Tab Hermeneutics Workbench:**
   - **Tab 1: Discursive Cluster & MARC21 Inspector** — Archetype-color-coded topic sidebar, posterior lemma probability bar chart ($\phi_k$), institutional publisher dominance strip, and MARC21 *Inhaltstext* cards with one-click APA 7th citation copy.
   - **Tab 2: Institutional Publisher × Archetype Matrix** — Cross-tabulates how each German publishing house (*Herder*, *Suhrkamp*, *Gütersloher Verlagshaus*, *EVA*, *Alibri*, *Kösel*, *Rowohlt*, *Patmos*) distributes its catalog across the discovered topic clusters and ideological archetypes.
   - **Tab 3: Diachronic Evolution & Coherence Atlas** — Houses the upgraded `TrendsGraph` (with interactive publisher filter pills and area gradients) alongside the full interactive $C_v$ vs. $U_{\text{Mass}}$ Hyperparameter Optimization Atlas.
