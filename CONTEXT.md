# Mediating Faith and Power (Deutsche-Verlage-LDA)

A computational topic modeling (Bayesian LDA, STM, and BERTopic) observatory analyzing ideological discourse across German theological, self-help, and secular-critical book publishing (`1970–2025`) over the complete Deutsche Nationalbibliothek (DNB) corpus (`10,042,681` works / `10,612,079` passages / `894,184,957` German words).

## Language

### Corpus & Bibliographic Domain

**Monograph Work**:
A single distinct book title (`10,042,681` unique works in the `1970–2025` DNB Master Manifest) identified by its normalized MARC21 `245$a` title and DNB identifier (`001`).
_Avoid_: document (ambiguous between work and passage), record, item

**Corpus Passage**:
A single modeled text unit (`10,612,079` passages across 127 Zstd-19 Apache Parquet shards) — either a 1,000-word sliding chapter window from a multi-chapter book (`27,587` deep-windowed books yielding `596,985` chapters) or a single-unit work deposit.
_Avoid_: row, chunk, doc

**Corpus Layer**:
The archival provenance tier supplying a **Corpus Passage**'s text — e.g., `dnb_oa_fullbook` (`/34` complete OA digital books), `hathitrust_ef_fullbook_print` (HTRC 1,000-word page-aggregated windows), `dnblab_dtf_incopyright` (DNBLab DTF/KorAP-XML in-copyright token profiles), `dnb_toc_pdf_fulltext` (`/04` digitized tables of contents), or `dnb_deposit_inhaltstext` (publisher blurbs).
_Avoid_: source type, data tier, bucket

**Imprint**:
A canonical German publishing house (`109` active imprints and `33` core houses mapped to **Ideological Regimes** out of `713,838` raw MARC21 `264$b` strings) whose institutional editorial policy mediates religious and secular discourse.
_Avoid_: vendor, brand, company

**Token Attrition Funnel**:
The 6-stage deterministic preprocessing pipeline (`Stage 01 Raw Tokens` → `Stage 02 Length Gate |w|>=3` → `Stage 03 Fraktur & Meta Filter` → `Stage 04 DHQ 2025 PER/LOC & Stopwords` → `Stage 05 spaCy POS Lemmatizer & Compound Splitter` → `Stage 06 Extremes & Sublinear TF-IDF Gate`) that reduces `894,184,957` raw words to the active dictionary (`|V| = 38,416` lemmas/bigrams).
_Avoid_: text cleaner, tokenizer pipeline

### Bayesian Topic Modeling Domain

**Ideological Regime**:
One of the three theoretical voices defined in `docs/THEORY_FRAMEWORK.md`: `Traditional / Ecclesiastical` ($\text{RQ}_1$), `Neoliberal / Self-Optimization` ($\text{RQ}_2$), or `Critical / Secular-Humanist` ($\text{RQ}_3$).
_Avoid_: category, class, sentiment

**LDA Paradigm**:
One of the four Bayesian prior and token-weighting configurations supported by the engine:
- `unseeded`: `1×` raw natural lemma counts (no `RELIGIOUS_VOICE_KEYWORDS` boost, no compound-root duplication) with symmetric/learned `eta='auto'`.
- `unsupervised`: `2×` salience weight on `RELIGIOUS_VOICE_KEYWORDS` + German compound root splitting (`Komposita -> Bestimmungswort + Grundwort`) with symmetric/learned `eta='auto'`.
- `seeded`: Asymmetric $K \times |V|$ conjugate Dirichlet prior matrix $\eta$ anchored to $\text{RQ}_1, \text{RQ}_2, \text{RQ}_3$ seed lexicons, scaled by token document frequency $df(w)$.
- `supervised`: Empirical document-label log-odds $\eta$ prior paired with a 5-fold cross-validated L2 Ridge discriminative head $\hat{y}_d = \arg\max(\theta_d W + b)$.
_Avoid_: model type, training mode, algorithm

**Posterior Topic**:
A latent multinomial word distribution $\phi_k$ over the active dictionary (`|V| = 38,416` or `34,892`), projected onto an **Ideological Regime** with lift-normalized **Imprint** dominance shares and ranked MARC21 **Monograph Works**.
_Avoid_: cluster, group, bucket

## Relationships

- A **Monograph Work** belongs to one **Imprint** and yields one or more **Corpus Passages** (1 for single-unit works; ~20–25 for deep-windowed multi-chapter works).
- Each **Corpus Passage** originates from one **Corpus Layer** and is transformed by the **Token Attrition Funnel** into a sparse bag-of-words vector.
- An **LDA Paradigm** estimates $K$ **Posterior Topics** across all `10,612,079` **Corpus Passages**.
- Each **Posterior Topic** maps to one primary **Ideological Regime** ($\text{RQ}_1, \text{RQ}_2, \text{RQ}_3$) and attributes salient dominance shares to canonical **Imprints**.

## Example dialogue

> **Dev:** "When a user switches the **LDA Paradigm** from `unsupervised` to `unseeded`, why does the active dictionary size change from `38,416` to `34,892`?"
> **Domain expert:** "Because `unseeded` strips the `2×` religious salience weight and skips German compound-root splitting in the **Token Attrition Funnel**, whereas `unsupervised` decomposes compounds into root lemmas before applying the sublinear TF-IDF filter."
> **Dev:** "And when they filter by an **Imprint** like `Herder` in the **MARC21 & APA 7th Inspector**, are we counting **Corpus Passages** or **Monograph Works**?"
> **Domain expert:** "The inspector deduplicates continuation chapters so every card represents a distinct **Monograph Work**, while the streaming Variational Bayes updates operate over all `10,612,079` **Corpus Passages**."

## Flagged ambiguities

- `"document"` / `"record"` was previously used interchangeably for both a **Monograph Work** (`10,042,681` unique books) and a **Corpus Passage** (`10,612,079` modeled passages including multi-chapter windows) — resolved: use **Monograph Work** for book-level counts and **Corpus Passage** for passage/chunk-level counts.
- `"unseeded"` vs. `"unsupervised"` — resolved: `unseeded` uses `1×` raw natural counts without compound root duplication; `unsupervised` applies `2×` domain keyword weighting and compound root splitting while keeping the Dirichlet prior $\eta$ unseeded (`'auto'`).
- `"25,000 lemmas"` — previously a hard `keep_n=25000` cap in `filter_extremes` masked the sublinear TF-IDF filter — resolved: `keep_n=100000` with `min_tfidf=0.065` yields the organic vocabulary (`38,416` weighted / `34,892` unseeded).
