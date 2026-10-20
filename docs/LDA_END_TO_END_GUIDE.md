# End-to-End Guide: Latent Dirichlet Allocation (LDA) for Mapping Religious Voices in the German Publishing Landscape

**Author Attribution:** Paul Marandi, Ph.D. Scholar, Centre for German Studies (CGS), School of Language, Literature and Culture Studies (SLL&CS), Jawaharlal Nehru University (JNU)  
**Repository:** `Deutsche-Verlage-LDA`  
**Citation Standard:** APA 7th Edition

---

## 1. Epistemological & Theoretical Foundation

Contemporary German publishing operates at a critical juncture where traditional theological institutions intersect with market-driven cultural production. Investigating this nexus requires a methodological framework capable of bridging macro-level bibliographic patterns ("distant reading"; Moretti, 2013) with micro-level critical discourse analysis ("close reading") grounded in Critical Theory. Latent Dirichlet Allocation (LDA), introduced by Blei, Ng, and Jordan (2003), provides a generative probabilistic model that uncovers latent thematic structures across heterogeneous corpora without imposing predefined taxonomic boundaries prior to statistical inference.

In the context of analyzing **"Voices on Religion"** within the German publishing landscape, LDA treats each publication record—comprising book titles, subtitles, catalog blurbs, and historical editorial mission statements—as a probabilistic mixture of underlying discursive topics, while simultaneously modeling each topic as a probability distribution over a finite German vocabulary. Rather than assuming that a text published by *Verlag Herder* is exclusively ecclesiastical or that a title from *Suhrkamp* is purely secular-philosophical, LDA quantifies the exact degree to which neoliberal market idioms (e.g., *Selbstoptimierung*, *Achtsamkeit*, *Erfolg*) penetrate traditional religious publishing imprints such as *Gütersloher Verlagshaus* (Bertelsmann).

```mermaid
flowchart LR
    A["Archival & Bibliographic Sources<br/>(DNB SRU & Wayback CDX)"] --> B["German Morphosyntactic NLP<br/>(spaCy Lemmatization & POS)"]
    B --> C["Domain Stopwords &<br/>Theological Token Weighting"]
    C --> D["Collocation Detection<br/>(Gensim Bigram Phraser)"]
    D --> E["Generative Bayesian Inference<br/>(Gensim LdaModel)"]
    E --> F["Coherence Validation<br/>(U_Mass & C_v Metrics)"]
    F --> G["Critical Theory Synthesis<br/>(3 Discursive Archetypes)"]
```

---

## 2. Mathematical & Probabilistic Formulation of LDA

Latent Dirichlet Allocation is a three-level hierarchical Bayesian model. Let the corpus $\mathcal{D} = \{w_1, w_2, \dots, w_M\}$ consist of $M$ documents (e.g., DNB bibliographic records and publisher mission statements), where each document $d \in \mathcal{D}$ is a sequence of $N_d$ tokens $w_d = (w_{d,1}, w_{d,2}, \dots, w_{d,N_d})$ drawn from a vocabulary $V$ of unique German lemmas and collocations.

Given $K$ latent topics (configured via [`NUM_TOPICS`](file:///f:/PhD%20AG/config.py#L13) in [config.py](file:///f:/PhD%20AG/config.py)), the generative process for each document $d$ proceeds as follows:

1. **Topic-Word Distribution ($\phi_k$):** For each topic $k \in \{1, \dots, K\}$, draw a multinomial distribution over the vocabulary $V$ from a Dirichlet prior parameterized by $\eta$:
   $$\phi_k \sim \text{Dirichlet}(\eta)$$
2. **Document-Topic Distribution ($\theta_d$):** For each document $d \in \{1, \dots, M\}$, draw a multinomial distribution over the $K$ topics from a Dirichlet prior parameterized by $\alpha$:
   $$\theta_d \sim \text{Dirichlet}(\alpha)$$
3. **Token Generation ($w_{d,n}$):** For each token position $n \in \{1, \dots, N_d\}$ in document $d$:
   - Draw a latent topic assignment $z_{d,n} \sim \text{Multinomial}(\theta_d)$.
   - Draw the observed German lemma $w_{d,n} \sim \text{Multinomial}(\phi_{z_{d,n}})$.

The joint probability distribution of the latent and observed variables for a single document is expressed as:

$$p(\theta_d, \mathbf{z}_d, \mathbf{w}_d \mid \alpha, \eta) = p(\theta_d \mid \alpha) \prod_{n=1}^{N_d} p(z_{d,n} \mid \theta_d) p(w_{d,n} \mid z_{d,n}, \phi)$$

Because exact posterior inference over $\theta_d$ and $\phi_k$ is computationally intractable due to the coupling between $\theta$ and $\phi$ in the summation over latent topic assignments $z_{d,n}$, our pipeline utilizes Online Variational Bayes (Hoffman, Bach, & Blei, 2010) as implemented in [`gensim.models.LdaModel`](file:///f:/PhD%20AG/lda_pipeline.py#L76-L86). Setting `alpha="auto"` and `eta="auto"` in [config.py](file:///f:/PhD%20AG/config.py#L15-L16) allows the model to learn asymmetric Dirichlet priors directly from the German publishing corpus, accommodating the empirical reality that certain discursive themes (such as general ethical commentary) appear more frequently across houses than niche liturgical debates.

---

## 3. Stage 1: Corpus Architecture & Data Acquisition

A rigorous LDA study in book history and sociology of religion depends on a balanced, representative corpus that captures institutional diversity across the German publishing field. In accordance with [docs/DATASET_ACQUISITION.md](file:///f:/PhD%20AG/docs/DATASET_ACQUISITION.md) and [docs/THEORY_FRAMEWORK.md](file:///f:/PhD%20AG/docs/THEORY_FRAMEWORK.md), the corpus is stratified across three institutional categories:

| Institutional Archetype | Representative German Publishers / Imprints | Primary Discursive Orientation |
| :--- | :--- | :--- |
| **1. Traditional / Ecclesiastical** | Verlag Herder, Evangelische Verlagsanstalt (EVA), Butzon & Bercker, Patmos | Dogmatic theology, pastoral care (*Seelsorge*), liturgy, ecclesiology, and institutional continuity. |
| **2. Neoliberal / Entrepreneurial** | Gütersloher Verlagshaus (Bertelsmann), Ariston (Penguin Random House), Scorpio, Goldmann | Self-optimization (*Selbstoptimierung*), secular mindfulness (*Achtsamkeit*), spiritualized management, and therapeutic individualized faith. |
| **3. Critical / Secular-Humanist** | Suhrkamp Verlag, Alibri Verlag, Rowohlt, Mabuse | Secularization theory, Enlightenment critique (*Religionskritik*), sociology of religion, and critiques of capitalist commodification. |

### 3.1 Automated Harvesting via DNB SRU API
The script [`harvest_dnb`](file:///f:/PhD%20AG/scripts/dnb_harvester.py#L7-L85) in [scripts/dnb_harvester.py](file:///f:/PhD%20AG/scripts/dnb_harvester.py) queries the German National Library (*Deutsche Nationalbibliothek*, DNB) via its Search/Retrieve via URL (SRU) v1.1 interface using Contextual Query Language (CQL) and parses the `MARC21-xml` schema.

- **Dewey Decimal Classification (DDC) Filtering:** Using `dcs=200*` (DDC Subject Group 200: Religion) isolates theological, spiritual, and religion-critical monographs.
- **MARC21 Tag Extraction:**
  - `Tag 245 ($a, $b)`: Main title and subtitle (critical for capturing descriptive subtitles in German non-fiction).
  - `Tag 100 ($a)`: Primary author.
  - `Tag 260 / 264 ($b, $c)`: Publisher imprint name and publication year.
  - `Tag 520 ($a)` & `Tag 650 ($a)` *(Recommended Expansion)*: Abstract/summary notes and subject headings (*Schlagwörter*) to enrich document length and reduce sparsity in short-text LDA.

### 3.2 CSV Schema Specification for Custom Uploads
When uploading a custom dataset via the dashboard's **Upload Custom Corpus** feature ([`upload_dataset`](file:///f:/PhD%20AG/app/main.py#L73-L100) in [app/main.py](file:///f:/PhD%20AG/app/main.py)), the CSV file must adhere to the following UTF-8 encoded column structure:

```csv
title,author,date,publisher,text
"Die Rückkehr der Religion in der Moderne",Hans Joas,2017,Suhrkamp,"Analyse der Vitalität religiöser Praktiken in der modernen Gesellschaft. Religion und Säkularisierung."
"Der Gott der Unternehmer",Susanne Schwarz,2022,Gütersloher Verlagshaus,"Spirituelle Führungskräfte und der Markt-Sinn. Neoliberale Spiritualität im Management."
```

> [!IMPORTANT]
> The backend validator in [`upload_dataset`](file:///f:/PhD%20AG/app/main.py#L91-L93) strictly requires the `publisher` and `date` columns for temporal trend aggregation and the `text` column for NLP preprocessing. Ensure all German umlauts (*ä, ö, ü, ß*) are saved in standard `UTF-8` encoding.

---

## 4. Stage 2: German Morphosyntactic NLP & Preprocessing Pipeline

German is a morphologically rich, inflected language characterized by extensive noun compounding (*Komposita*), case-marked adjectives, and separable verb prefixes. Applying naive English-centric whitespace tokenization to German texts fragments semantic units across inflected surface forms (e.g., *Kirche*, *Kirchen*, *kirchlicher*, *kirchlichen*). Our preprocessing function [`preprocess_text`](file:///f:/PhD%20AG/lda_pipeline.py#L20-L43) in [lda_pipeline.py](file:///f:/PhD%20AG/lda_pipeline.py) addresses these linguistic challenges through five sequential operations:

### 4.1 Lemmatization and Part-of-Speech (POS) Filtering
Each document is parsed using `spaCy` ([`SPACY_MODEL`](file:///f:/PhD%20AG/config.py#L9)). Only tokens matching [`ALLOWED_POSTAGS`](file:///f:/PhD%20AG/config.py#L22) (`NOUN`, `PROPN`, `ADJ`) are retained and reduced to their canonical lowercase lemma (`token.lemma_.lower()`). Restricting the vocabulary to nouns, proper nouns, and adjectives eliminates syntactic function words and modal auxiliaries while preserving substantive philosophical and theological concepts (Boyd-Graber, Hu, & Mimno, 2017).

### 4.2 Two-Tier Stopword Removal (Eliminating Bibliographic Noise)
Catalog metadata and academic blurbs contain high-frequency bibliographic boilerplate that can corrupt LDA topics into "citation noise" clusters rather than substantive thematic clusters. In [`DOMAIN_STOPWORDS`](file:///f:/PhD%20AG/config.py#L25-L30), we combine `spaCy`'s default German functional stopwords with a curated list of archival and scholarly abbreviations:
- **Publishing Metadata Noise:** `verlag`, `seiten`, `isbn`, `auflage`, `euro`, `jahr`, `berlin`, `frankfurt`, `dnb`, `bibliothek`, `katalog`, `reihe`.
- **Academic Citation Apparatus:** `ebd` (*ebenda*), `vgl` (*vergleiche*), `hrsg` / `hg` (*Herausgeber*), `abb` (*Abbildung*), `anm` (*Anmerkung*), `bd` / `bde` (*Band/Bände*), `diss` (*Dissertation*), `ff`, `usw`, `bzw`.

### 4.3 Semi-Supervised Discursive Token Weighting
In short-to-medium length bibliographic texts, core theoretical signifiers may suffer from low raw term frequency within individual records. As implemented in [`preprocess_text`](file:///f:/PhD%20AG/lda_pipeline.py#L31-L37), tokens matching [`RELIGIOUS_VOICE_KEYWORDS`](file:///f:/PhD%20AG/config.py#L33-L38) (*glaube, gott, spiritualität, kirche, ethik, moral, erlösung, sinn, transzendenz, gnade, offenbarung, seelsorge, predigt, theologie, religiös, christlich, atheismus, kirchenkritik, religionskritik, säkularität, selbsthilfe*) receive a $2\times$ frequency weight prior to bag-of-words vectorization. Methodologically, this acts as a transparent domain-informed prior (similar in spirit to seeded or anchored topic modeling; Jagarlamudi, Daumé, & Udupa, 2012) that anchors topic formation around religious and secular-critical vocabulary.

### 4.4 Collocation (N-Gram) Detection
Many central concepts in German sociology of religion are multi-word expressions (e.g., *soziale_gerechtigkeit*, *praktische_theologie*, *neoliberale_spiritualität*, *säkularer_humanismus*). In [`run_pipeline`](file:///f:/PhD%20AG/lda_pipeline.py#L61-L67), `gensim.models.Phrases` scans the lemmatized token streams (`min_count=2, threshold=5`) and binds statistically significant bigrams into single compound tokens before dictionary construction.

---

## 5. Stage 3: Model Training, Hyperparameter Tuning & Coherence Validation

Once the lemmatized and bigram-enriched documents are converted into a bag-of-words corpus via `dictionary.doc2bow(doc)`, [`run_pipeline`](file:///f:/PhD%20AG/lda_pipeline.py#L76-L109) trains the `LdaModel` and evaluates its statistical validity.

### 5.1 Selecting the Number of Topics ($K$) and Hyperparameters
The hyperparameter settings in [config.py](file:///f:/PhD%20AG/config.py#L12-L16) govern the granularity of the discovered discourse:

| Parameter | Current Setting | Methodological Role & Tuning Guidance |
| :--- | :--- | :--- |
| [`NUM_TOPICS`](file:///f:/PhD%20AG/config.py#L13) ($K$) | `10` | Defines the number of latent clusters. For small pilot corpora ($<100$ documents), $K \in [5, 10]$ prevents over-fragmentation. For full DNB harvests ($1,000\text{--}10,000$ records), conduct a grid search over $K \in \{10, 15, 20, 25, 30, 40\}$. |
| [`PASSES`](file:///f:/PhD%20AG/config.py#L14) | `15` | Number of full training sweeps through the corpus. Increase to `20–30` for publication-grade runs to guarantee convergence of the variational bound. |
| [`ALPHA`](file:///f:/PhD%20AG/config.py#L15) ($\alpha$) | `"auto"` | Learns an asymmetric document-topic prior from the data. High $\alpha$ implies documents contain many topics; low $\alpha$ forces documents to belong to a single dominant voice. |
| `random_state` | `100` | Fixed random seed in [`LdaModel`](file:///f:/PhD%20AG/lda_pipeline.py#L80) ensuring 100% deterministic reproducibility for doctoral thesis verification. |

### 5.2 Quantitative Validation via Topic Coherence ($U_{\text{Mass}}$ and $C_v$)
Perplexity alone often fails to correlate with human interpretability of topics (Chang et al., 2009). Following Röder, Both, and Hinneburg (2015), our pipeline computes intrinsic **Topic Coherence** using [`CoherenceModel`](file:///f:/PhD%20AG/lda_pipeline.py#L91-L92):

- **$U_{\text{Mass}}$ Coherence (Default in [`lda_pipeline.py`](file:///f:/PhD%20AG/lda_pipeline.py#L91)):** Measures asymmetrical empirical conditional log-probability between top topic words $w_i, w_j$ using document co-occurrence counts $D(w_i, w_j)$ within the corpus itself:
  $$C_{U_{\text{Mass}}} = \frac{2}{N(N-1)} \sum_{i=2}^{N} \sum_{j=1}^{i-1} \log \frac{D(w_i, w_j) + \epsilon}{D(w_j)}$$
  Values closer to $0$ (less negative) indicate higher semantic coherence.
- **Corpus Prevalence Calculation:** In [`get_topics`](file:///f:/PhD%20AG/app/main.py#L214-L226), the backend computes the macro-level weight of each topic $k$ across the entire corpus of $M$ documents:
  $$\text{Prevalence}(k) = \left( \frac{1}{M} \sum_{d=1}^{M} \theta_{d,k} \right) \times 100\%$$
- **Source Evidence Extraction:** To prevent decontextualized misinterpretation of word lists, [`run_pipeline`](file:///f:/PhD%20AG/lda_pipeline.py#L95-L108) ranks all documents by their posterior probability $\theta_{d,k}$ for each topic $k$ and extracts the top 3 representative document snippets (`representative_docs`).

### 5.3 Empirical Grid Search Results on the Harvested DNB Corpus ($N = 160$)
Executing [`scripts/coherence_grid_search.py`](file:///f:/PhD%20AG/scripts/coherence_grid_search.py) on the 160 enriched DNB records (`data/dnb_metadata.csv`, $|V| = 3,712$ unique German lemmas and bigrams across Herder, Evangelische Verlagsanstalt, Gütersloher Verlagshaus, Kösel, Suhrkamp, Alibri, Rowohlt, and Patmos) yields a dual-scale coherence profile (see full report in [COHERENCE_GRID_REPORT.md](file:///f:/PhD%20AG/docs/COHERENCE_GRID_REPORT.md)):

| Number of Topics ($K$) | $C_v$ Coherence | $U_{\text{Mass}}$ Coherence | Log Perplexity Bound | Discursive Resolution Level |
| :---: | :---: | :---: | :---: | :--- |
| **4** | `0.4008` | `-5.0429` | `-7.8819` | **Macro-Archetype Peak** (Optimal $U_{\text{Mass}}$; aligns with the 3–4 broad institutional voices) |
| **6** | `0.3440` | `-7.2369` | `-7.9608` | Transitional split |
| **8** | `0.3160` | `-8.8889` | `-8.0393` | Transitional split |
| **10** | `0.3350` | `-9.4710` | `-8.0833` | Default dashboard baseline |
| **12** | `0.3905` | `-8.9528` | `-8.1008` | **Meso-Level Inflection** (Sub-disciplinary differentiation) |
| **15** | `0.3831` | `-9.7105` | `-9.7275` | Meso-level plateau |
| **20** | `0.4091` | `-9.9323` | `-10.7597` | High-resolution thematic clustering |
| **25** | `0.3887` | `-8.4980` | `-11.5375` | High-resolution plateau |
| **30** | `0.4449` | `-8.1086` | `-12.2390` | **Micro-Thematic Peak** (Optimal $C_v$ NPMI coherence) |

```mermaid
xychart-beta
    title "Empirical C_v Topic Coherence Curve across K (N = 160 DNB Records)"
    x-axis "Number of Topics (K)" ["4", "6", "8", "10", "12", "15", "20", "25", "30"]
    y-axis "C_v Coherence Score" 0.28 --> 0.48
    line [0.4008, 0.344, 0.316, 0.335, 0.3905, 0.3831, 0.4091, 0.3887, 0.4449]
```

> [!TIP]
> **Methodological Interpretation for the Dissertation:** The empirical curve exhibits two theoretically meaningful regimes: a **Macro-Archetype Peak at $K = 4$** ($U_{\text{Mass}} = -5.0429, C_v = 0.4008$), which captures the overarching division between Traditional Ecclesiastical, Neoliberal/Self-Optimization, and Secular-Critical voices, and a **Meso/Micro-Thematic Rebound at $K \in \{12, 20, 30\}$** ($C_v = 0.3905 \rightarrow 0.4449$), which resolves specific sub-debates such as ecological creation theology (*Schöpfungsethik*), liturgical reform (*Synodalität*), and antisemitism-critical pedagogy.

---

## 6. Stage 4: Qualitative Synthesis & Critical Theory Interpretation

Computational output becomes a doctoral contribution only when translated into socio-historical argument. Once the model generates its ranked topic clusters, apply the three-step **Hermeneutic Triangulation Protocol**:

### Step 1: Lexical Inspection & Topic Labeling
Examine the top 15 weighted lemmas for each topic $k$ returned by `/api/topics`. Assign a descriptive scholarly label based on co-occurring signifiers:
- *Example Cluster A:* `kirche (0.082), glaube (0.074), seelsorge (0.051), gemeinde (0.043), hoffnung (0.039)` $\rightarrow$ **Label:** *Pastoral Care & Institutional Ecclesiology* (Archetype 1: Traditional Voice).
- *Example Cluster B:* `spiritualität (0.091), selbst (0.064), achtsamkeit (0.058), markt (0.049), erfolg (0.042)` $\rightarrow$ **Label:** *Therapeutic Self-Optimization & Market Spirituality* (Archetype 2: Neoliberal Voice).
- *Example Cluster C:* `ethik (0.078), säkular (0.062), kritik (0.055), humanismus (0.048), vernunft (0.041)` $\rightarrow$ **Label:** *Secular Humanism & Enlightenment Critique* (Archetype 3: Critical Voice).

### Step 2: Diachronic Trend Filtering (The "Computational Turn")
Using the interactive **Publisher Archetypes** timeline in the dashboard ([`TrendsGraph.tsx`](file:///f:/PhD%20AG/frontend/src/components/TrendsGraph.tsx) and [`run_lda`](file:///f:/PhD%20AG/app/main.py#L125-L165)), isolate specific years or decades (`?year=2021` or `?decade=2010`). Compare how the prevalence of *Cluster B (Neoliberal Spirituality)* shifts relative to *Cluster A (Traditional Ecclesiology)* between the 2000s and the 2020s. This empirically tests the thesis hypothesis that German religious publishing has undergone a structural shift from collective confessional authority toward individualized, market-compatible spirituality (Carrette & King, 2005; Illouz, 2008).

### Step 3: Close Reading of Representative Documents
Inspect the `representative_docs` returned for each topic. Quote the highest-scoring book blurbs and editorial statements directly in your thesis chapters, reporting their topic probability score (e.g., $\theta_{d,k} = 0.78$) alongside qualitative discourse analysis.

---

## 7. Stage 5: End-to-End Operational Execution Guide

Follow this step-by-step workflow to run the complete research pipeline from raw data harvesting to interactive visualization:

### Step 1: Harvest or Prepare the Corpus
To pull fresh records from the German National Library (DNB) for Subject Group 200:
```powershell
python scripts/dnb_harvester.py
```
This saves the harvested records to `data/dnb_metadata.csv`. Alternatively, prepare a custom UTF-8 CSV file with columns `title,author,date,publisher,text`.

### Step 2: Run Standalone CLI Pipeline (Optional Batch Mode)
To execute the preprocessing, bigram detection, LDA training, and coherence calculation directly in the terminal:
```powershell
python lda_pipeline.py
```

### Step 3: Launch the Unified Full-Stack Research Dashboard Locally
To run the FastAPI backend and React frontend locally:
```powershell
uvicorn app.main:app --reload --port 8000
```
Or, for live frontend development against the cloud/local API:
```powershell
cd frontend
npm run dev
```

### Step 4: Interactive Research Workflow on the Webapp
1. Open the dashboard (`https://deutscheverlagelda.vercel.app` or `http://localhost:8000`).
2. **Ingest Corpus:** Click **Upload Custom Corpus** in the *Corpus Overview* card to upload your curated CSV, or use the built-in *Voices on Religion* demonstration corpus.
3. **Train Full Model:** Click **Execute Full Analysis** in the *Neural Engine* panel to train the LDA model across the entire temporal range.
4. **Diachronic Slicing:** Click any year node on the **Publisher Archetypes** line graph to dynamically filter the corpus and re-train the LDA sub-model for that specific year.
5. **Export Findings:** Record the $U_{\text{Mass}}$ coherence score, topic prevalence percentages, top weighted lemmas, and representative document snippets for inclusion in your dissertation chapters.

---

## 8. APA 7th Edition References (Methodological & Theoretical)

- Blei, D. M. (2012). Probabilistic topic models. *Communications of the ACM*, 55(4), 77–84. https://doi.org/10.1145/2133806.2133826
- Blei, D. M., Ng, A. Y., & Jordan, M. I. (2003). Latent Dirichlet allocation. *Journal of Machine Learning Research*, 3, 993–1022.
- Boyd-Graber, J., Hu, Y., & Mimno, D. (2017). Applications of topic models. *Foundations and Trends in Information Retrieval*, 11(2–3), 143–296. https://doi.org/10.1561/1500000030
- Carrette, J., & King, R. (2005). *Selling spirituality: The silent takeover of religion*. Routledge.
- Chang, J., Gerrish, S., Wang, C., Boyd-Graber, J. L., & Blei, D. M. (2009). Reading tea leaves: How humans interpret topic models. In *Advances in Neural Information Processing Systems* (Vol. 22, pp. 288–296).
- Hoffman, M., Bach, F. R., & Blei, D. M. (2010). Online learning for latent Dirichlet allocation. In *Advances in Neural Information Processing Systems* (Vol. 23, pp. 856–864).
- Illouz, E. (2008). *Saving the modern soul: Therapy, emotions, and the culture of self-help*. University of California Press.
- Jagarlamudi, J., Daumé, H., III, & Udupa, R. (2012). Incorporating lexical priors into topic models. In *Proceedings of the 13th Conference of the European Chapter of the Association for Computational Linguistics* (pp. 204–213). Association for Computational Linguistics.
- Joas, H. (2017). *Die Macht des Heiligen: Eine Alternative zur Geschichte von der Entzauberung*. Suhrkamp Verlag.
- Moretti, F. (2013). *Distant reading*. Verso Books.
- Röder, M., Both, A., & Hinneburg, A. (2015). Exploring the space of topic coherence measures. In *Proceedings of the Eighth ACM International Conference on Web Search and Data Mining* (pp. 399–408). https://doi.org/10.1145/2684822.2685324
