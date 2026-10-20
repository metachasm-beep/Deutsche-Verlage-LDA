# 3-Pane Split-View Research IDE Layout Overhaul Plan

> **For agentic workers:** Follow `superpowers:writing-plans`, `superpowers:verification-before-completion`, `hig-components-layout`, `frontend-ui-dark-ts`, and `baseline-ui` to execute and verify this spatial layout transformation.

**Goal:** Transform the frontend from a vertically stacked single-page layout with hidden tabs into a viewport-locked (`lg:h-dvh lg:overflow-hidden`) **3-Pane Split-View Research IDE** (`AppShell`) where the **Left Docked Bayesian Command Sidebar**, **Center Simultaneous Bento Canvas** (showing Topic Posterior Distribution, Diachronic Timeline, Publisher Matrix, and Coherence Atlas together), and **Right Docked MARC21 & APA 7th Inspector Drawer** operate in synchronized real time.

---

## 1. Spatial Hierarchy (`hig-components-layout` + `baseline-ui`)

```
Root (lg:h-dvh lg:overflow-hidden flex flex-col bg-obsidian-950)
├── Top IDE Command Bar (h-12 shrink-0 border-b border-white/[0.08])
│   ├── Brand & Corpus Telemetry Badge (DNB SRU v1.1 · MARC21)
│   ├── Center Workspace Layout Switcher (Observatory Bento | Topic Deep-Dive | Matrix & Atlas)
│   └── Active Year Filter Chip + CSV Upload + APA 7th Modal + Inspector Collapse Toggle
└── 3-Pane Split-View Body (flex-1 min-h-0 flex flex-col lg:flex-row overflow-y-auto lg:overflow-hidden)
    ├── Pane 1: Left Docked Bayesian Command Sidebar (w-full lg:w-[300px] xl:w-[320px] shrink-0 border-r)
    │   ├── Research Hypotheses & Ideological Archetype Filter (RQ1 Traditional, RQ2 Neoliberal, RQ3 Critical)
    │   ├── Bayesian K-Granularity Slider & Regime Presets (Macro K=6, Meso K=12, Micro K=25)
    │   └── Latent Topic Source List (T01..TK with Archetype Color Dot, Top Lemmas & Confidence %)
    ├── Pane 2: Center Simultaneous Bento Canvas (flex-1 min-w-0 h-full lg:overflow-y-auto p-4 space-y-4)
    │   ├── Row 1: Compact 5-Card Executive KPI Strip (D=160, |V|=3,458, K, Cv, Dominant Discourse)
    │   ├── Row 2: Simultaneous Upper Bento Split (12-col grid)
    │   │   ├── Col 1-7: Topic Posterior Distribution (phi_k,w) + 3-Way Ideological Spectrum Bar
    │   │   └── Col 8-12: Diachronic Publication Trajectory (2005–2026) with Click-to-Filter Year Slice
    │   └── Row 3: Simultaneous Lower Bento Split (12-col grid)
    │       ├── Col 1-7: Institutional Publisher × Ideological Archetype Matrix (8 Publishers)
    │       └── Col 8-12: Röder et al. (2015) Coherence Validation Atlas (Cv vs UMass)
    └── Pane 3: Right Docked MARC21 & APA 7th Inspector Drawer (w-full lg:w-[350px] xl:w-[380px] shrink-0 border-l)
        ├── Sticky Inspector Header (Selected Topic #k + Archetype + Active Year + Batch Copy All APA Citations)
        ├── Institutional Imprint Concentration Bar for Selected Topic
        └── Live MARC21 Inhaltstext & APA 7th Bibliographic Cards with Search & Copy
```

---

## 2. State Synchronization Across Panes
- **Shared `selectedTopicIndex` lifted to `App.tsx`:**
  - Selecting a topic in **Pane 1 (Left Sidebar Source List)** OR **Pane 2 (Center Topic Pill Strip)** immediately updates **Pane 2 (Word-Topic Chart)** AND **Pane 3 (Right MARC21 & APA 7th Inspector Drawer)**.
- **Shared `ideologicalFilter` (`null | 'Traditional' | 'Neoliberal' | 'Critical'`):**
  - Clicking an ideological archetype in **Pane 1** filters/highlights matching topics in both the Left Topic Directory and Center Topic Workbench.
- **Shared `selectedYear` (`number | null`):**
  - Clicking a year point in **Pane 2 (Diachronic Trajectory)** immediately re-slices the LDA posterior in **Pane 2** and updates the MARC21 monographs in **Pane 3** without scrolling or switching tabs.

---

## 3. Files to Modify
1. `frontend/src/components/TopicModelViz.tsx` — Refactor to accept controlled `selectedTopicIndex` and `onSelectTopicIndex` props, plus a clean `compactBento` layout mode where the MARC21 Inspector is delegated to Pane 3 (while preserving an inline fallback if the right inspector is collapsed).
2. `frontend/src/components/TrendsGraph.tsx` — Optimize height and header density so it fits seamlessly inside the Upper-Right Bento Cell alongside the Topic Distribution chart, as well as expanded mode.
3. `frontend/src/App.tsx` — Implement the full 3-Pane Split-View Research IDE (`AppShell`), Top IDE Command Bar, Left Bayesian Sidebar with Topic Source List & Archetype Filter, Center Simultaneous Bento Grid, and Right Docked MARC21 & APA 7th Inspector Drawer (including one-click **Copy All Topic APA Citations**).
