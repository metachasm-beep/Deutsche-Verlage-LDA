# Peer-Reviewed Journal Submission Strategy & Manuscript Blueprints

**Project Title:** *Mediating Faith & Power: A Computational Topic Modeling (LDA, STM, and BERTopic) Analysis of German Theological, Self-Help, and Secular-Academic Publishing (1970–2025)*  
**Author:** Paul Marandi, Ph.D. Scholar  
**Institution:** Centre for German Studies (CGS), School of Language, Literature and Culture Studies (SLL&CS), Jawaharlal Nehru University (JNU), New Delhi  
**Empirical Observatory:** [https://deutscheverlagelda.vercel.app](https://deutscheverlagelda.vercel.app)

---

## 1. Executive Publication Architecture

Because this doctoral project bridges **Computational Literary Studies (*Digitale Literaturwissenschaft*)**, **Book History (*Buchwissenschaft*)**, **Sociology of Religion (*Religionssoziologie*)**, and **German Critical Theory (*Kulturwissenschaft*)**, its empirical findings can be strategically unbundled into **three distinct, non-overlapping peer-reviewed journal articles** (the "Three-Pillar Dissertation Publication Model"):

```mermaid
flowchart TD
    Corpus["Eleven-Wave Complete Multi-Repository Master Corpus (1970–2025)\nD = 461,785 Documents | 385,115,918 German Words | 12,739 Full Books + 97,669 PDFs/Abstracts/Enriched (82,283 Works)\n|V| = 25,000 Lemmas & Bigrams | 38 German Publishing Houses (4,235 Total Imprints)"]
    Pipeline["Three-Model Computational Triangulation (Santana et al., 2025 5-Rule FAIR/DDI)\n1. Bayesian LDA (K=12, U_Mass=-2.4760 / sLDA=-1.9650)\n2. Quanteda + STM Regressions (280,970 Secular vs. 180,812 Confessional)\n3. Neural Doc2Vec + c-TF-IDF (BERTopic)"]
    Corpus --> Pipeline

    Pipeline --> Paper1["Manuscript 1: Computational & Methodological\nTarget: JCLS / ZfdG / Cultural Analytics"]
    Pipeline --> Paper2["Manuscript 2: Sociology of Publishing & Bourdieu\nTarget: Poetics / Publishing Research Quarterly"]
    Pipeline --> Paper3["Manuscript 3: Critical Theory & Secularization Shifts\nTarget: New German Critique / Journal of Contemporary Religion"]
```

---

## 2. Comprehensive Journal Target Matrix (24 Peer-Reviewed Venues)

### Pillar I: Computational Literary Studies, Digital Humanities & Cultural Analytics
*Primary fit for the **Eleven-Wave Complete Multi-Repository Harvesting Architecture (`4,031` HTRC Printed Books under § 60d UrhG + `8,553` DNB `/34` & `MARC 856` `location=onlinefree` & `$z="kostenfrei"` OA Full Books & EPUBs + `32,021` DNB `/04` Digitized PDFs/HTMLs + `47,083` DNB `deposit.dnb.de` & `/blurb/` Inhaltstexte + `17,760` GBV / K10plus Consortial TOC PDFs & `MARC 520` Works + `627` OpenAlex Reconstructed `abstract_inverted_index` Abstracts + `236` OpenAlex/GBV/IA OA Books = `461,785` documents / `385.12M` words across `82,283` unique works and `12,739` complete full-text books)**, **5-Rule FAIR/DDI row-metadata stripping, `PER`/`LOC` filtering, `TfidfModel(smartirs='ntc')` & German compound-noun lemmatization (`de_core_news_lg` + `Komposita-Zerlegung`, Santana et al., 2025)**, **LDA vs. STM vs. BERTopic triangulation**, and **3-Pane Computational Hermeneutics Observatory**.*

| Journal | Publisher / Affiliation | Indexing / Tier | Language | Access Model | Strategic Fit & Submission Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Journal of Computational Literary Studies (JCLS)** | Open Library of Humanities / TU Darmstadt | Scopus / DOAJ | English / German | Diamond OA (No APC) | **Top Priority (Methodological):** The premier European/German venue for computational *Germanistik*, DNB/GBV/HTRC corpora, and topic modeling. |
| **Zeitschrift für digitale Geisteswissenschaften (ZfdG)** | Forschungsverbund Marbach Weimar Wolfenbüttel | Scopus / DOAJ | German / English | Diamond OA (No APC) | **Top Priority (German DH):** Publishes landmark studies on German national bibliography (DNB/GBV) corpora, § 60d UrhG *Abgeleitete Textformate*, and distant reading. |
| **Journal of Cultural Analytics (CA)** | Open Access (Dir. Andrew Piper, McGill) | Web of Science / Scopus (Q1) | English | Diamond OA (No APC) | Ideal for macro-scale cultural sociology of book markets (`385.12M` words) and lexical shifts across 55 years (`1970–2025`). |
| **Digital Scholarship in the Humanities (DSH)** | Oxford University Press (EADH) | AHCI / Scopus (Q1) | English | Hybrid | High-prestige venue for combining Bayesian latent variable models with hermeneutic close reading. |
| **Digital Humanities Quarterly (DHQ)** | Alliance of Digital Humanities Organizations | Scopus / Web of Science | English | Diamond OA (No APC) | Strong fit for papers showcasing FAIR/DDI preprocessing transparency (Santana et al., 2025) and interactive research workbench design. |
| **International Journal of Humanities and Arts Computing (IJHAC)** | Edinburgh University Press | AHCI / Scopus | English | Hybrid | Welcomes corpus-construction and national-catalog metadata studies. |

---

### Pillar II: Book History, Publishing Studies & Sociology of Literature (*Buchwissenschaft*)
*Primary fit for the **38-Publisher × 3-Archetype Matrix** (`280,970` Secular/Critical vs. `180,812` Confessional documents across *Suhrkamp, Rowohlt, S. Fischer, Klett-Cotta, Kiepenheuer & Witsch, Wagenbach, Alibri, Herder, Gütersloher Verlagshaus, EVA, Kösel, Patmos, Vandenhoeck & Ruprecht, Mohr Siebeck, Frommann-Holzboog*, etc.) and **Pierre Bourdieu's theory of the field of cultural production**.*

| Journal | Publisher / Affiliation | Indexing / Tier | Language | Access Model | Strategic Fit & Submission Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Poetics: Journal of Empirical Research on Culture, the Media and the Arts** | Elsevier | SSCI / Scopus (Q1) | English | Hybrid | **Top Priority (Sociology of Culture):** Flagship Bourdieu-tradition journal that privileges quantitative/computational methods (LDA, STM, correspondence analysis) applied to publishing fields. |
| **Archiv für Geschichte des Buchwesens (AGB)** | De Gruyter (Historische Kommission des Börsenvereins) | Scopus / ERIH+ | German / English | Subscription / Green OA | Germany's most authoritative periodical for *Verlagsgeschichte* and structural transformations of the German book trade (`1970–2025`). |
| **Publishing Research Quarterly (PRQ)** | Springer | Scopus (Q2) | English | Hybrid | Focuses on contemporary book industry strategy, imprint repositioning, and the rise of secular-sociological and *Lebenshilfe* publishing. |
| **Book History** | Johns Hopkins University Press (SHARP) | AHCI / Scopus (Q1) | English | Subscription | Flagship international journal for the social, economic, and ideological history of print culture. |
| **Internationales Archiv für Sozialgeschichte der deutschen Literatur (IASL)** | De Gruyter | AHCI / Scopus | German / English | Hybrid | Bridges German literary studies (*Germanistik*) with the institutional sociology of publishers and intellectual milieus. |
| **Logos: Journal of the World Book Community** | Brill | Scopus | English | Hybrid | Examines editorial gatekeeping, trade vs. religious publishing, and global book market shifts. |

---

### Pillar III: Sociology of Religion, Post-Secularism & the Therapeutic Turn
*Primary fit for testing the **three ideological regimes** ($RQ_1$ Ecclesiastical Continuity, $RQ_2$ Neoliberal Self-Optimization, $RQ_3$ Post-Secular Critical Theory) across `461,785` documents.*

| Journal | Publisher / Affiliation | Indexing / Tier | Language | Access Model | Strategic Fit & Submission Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Journal of Contemporary Religion** | Taylor & Francis | AHCI / SSCI (Q1) | English | Hybrid | **Top Priority (Religion & Spirituality):** Leading venue on alternative spirituality, pluralization, and changing Christian institutions in Europe. |
| **Zeitschrift für Religionswissenschaft (ZfR)** | De Gruyter (DVRW) | Scopus / ERIH+ | German / English | Diamond OA | Official journal of the German Association for the Study of Religions; ideal for empirical studies of religion in German print media. |
| **Social Compass** | SAGE (ISSR) | SSCI / Scopus (Q1) | English / French | Hybrid | Strong focus on European secularization, post-secularism, and the commodification of spiritual practices. |
| **Sociology of Religion** | Oxford University Press (ASR) | SSCI (Q1) | English | Hybrid | Premier venue for quantitative and computational sociology of religious vs. secular discourse. |
| **Method & Theory in the Study of Religion (MTSR)** | Brill | AHCI / Scopus (Q1) | English | Hybrid | Ideal for demonstrating how Bayesian topic modeling operationalizes theories by Charles Taylor, Habermas, and Carrette & King. |
| **Culture and Religion** | Taylor & Francis | AHCI / Scopus | English | Hybrid | Explores the mediation of religion through consumer capitalism, lifestyle publishing, and popular culture. |

---

### Pillar IV: German Studies (*Germanistik* / *Kulturwissenschaft*) & Critical Theory
*Primary fit for situating the research within contemporary German intellectual history, **Suhrkamp-Kultur**, **Klett-Cotta / Rowohlt / S. Fischer** humanities publishing, and post-secular subjectivity.*

| Journal | Publisher / Affiliation | Indexing / Tier | Language | Access Model | Strategic Fit & Submission Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **New German Critique (NGC)** | Duke University Press | AHCI / Scopus (Q1) | English | Subscription | **Top Priority (Critical Theory):** Premier venue for Frankfurt School theory, *Suhrkamp* intellectual history, post-secularism (Habermas), and critiques of neoliberalism. |
| **German Studies Review (GSR)** | Johns Hopkins University Press (GSA) | AHCI / SSCI (Q1) | English | Subscription | Flagship interdisciplinary journal of the German Studies Association; welcomes studies on 1970–2025 German cultural institutions. |
| **Deutsche Vierteljahrsschrift für Literaturwissenschaft und Geistesgeschichte (DVjs)** | Springer / J.B. Metzler | AHCI / Scopus (Q1) | German / English | Hybrid | Classic venue for *Geistesgeschichte*, secularization debates, and computational approaches to German intellectual history. |
| **Seminar: A Journal of Germanic Studies** | University of Toronto Press | AHCI / Scopus | English / German | Hybrid | Frequently publishes special issues on Digital German Studies and contemporary German non-fiction (*Sachbuch*). |
| **German Life and Letters (GLL)** | Wiley | AHCI / Scopus | English / German | Hybrid | Strong UK/international venue for contemporary German cultural politics and publishing institutions. |
| **Kölner Zeitschrift für Soziologie und Sozialpsychologie (KZfSS)** | Springer VS | SSCI / Scopus (Q1) | German / English | Hybrid | Germany's leading sociology journal; strong fit for empirical analysis of the $+10.45\%$ expansion of sociological secularization & ethical theory (`Topic 6`) and $+6.82\%$ expansion of applied pedagogy & organizational praxis (`Topic 5`) (`1970–2025`). |

---

## 3. Tailored Manuscript Abstracts & Outlines

### Manuscript 1: Computational & Methodological Article
* **Target Venues:** *Journal of Computational Literary Studies (JCLS)* or *Zeitschrift für digitale Geisteswissenschaften (ZfdG)*
* **Proposed Title:** *Distant Reading the Post-Secular Book Market: A Multi-Model Computational Pipeline (LDA, STM, and BERTopic) on a 385.12-Million-Word German Multi-Repository Corpus (1970–2025)*

#### Abstract (English — Flowing Prose, 250 Words)
While computational literary studies have increasingly turned to national bibliographies to reconstruct macro-historical shifts in print culture, post-1970 German non-fiction (*Sachbuch*) and religious-philosophical publishing have remained constrained by copyright barriers and short-text metadata sparsity. This article introduces an eleven-wave, § 60d UrhG- and FAIR/DDI-compliant full-book and national-library harvesting and multi-model computational hermeneutics pipeline spanning fifty-five years of German publishing (`1970–2025`). By cross-walking the *Deutsche Nationalbibliothek* (DNB SRU v1.1 MARC21 & uncapped `location=onlinefree` + `MARC 856` + `hsg=` year-by-year `1970–2025` full-text index across all religion, theology, philosophy, psychology, ethics, and sociology divisions) and forty-one *Basisklassifikation* (`pica.bkl`) subcodes in the *Gemeinsamer Bibliotheksverbund* (GBV/K10plus, multi-ISBN `MARC 020` resolution) against the HathiTrust Research Center (HTRC) Extracted Features v2.0 API, DNB `/34` open-access deposit servers, DNB `/04` digitized reading samples, OpenAlex (`per-page=200` OA PDFs and reconstructed `abstract_inverted_index` corpus), and the Internet Archive across thirty-eight German publishing houses (`4,235` total imprints), we assemble **$461,785$ documents and full-book passages ($385,115,918$ original German words)** from **$12,739$ complete full-text books** ($4,031$ in-copyright printed HTRC monographs, $8,553$ `location=onlinefree` and sibling-matched `$z="kostenfrei"` DNB `/34` & `MARC 856` open-access books and EPUBs, and $236$ OpenAlex/GBV/Archive.org open-access books) alongside **$32,021$ digitized DNB `/04` `Inhaltsverzeichnis` and reading-sample PDFs/HTMLs**, **$47,083$ DNB `deposit.dnb.de` and `/blurb/` `Inhaltstexte`**, **$17,760$ GBV / K10plus consortial TOC PDFs and `MARC 520` / `BKL` / `GND` enriched works**, and **$627$ OpenAlex scholarly abstracts** ($82,283$ unique works cataloged in `DNB_FULLTEXT_MASTER_MANIFEST.csv`). Following Santana et al. (2025, *DHQ* 19.2) and Jiménez-Badillo et al. (2020, *DHQ* 14.4) five-rule preprocessing (`extract_row_metadata_tokens`, `NON_CANONICAL_LOC_AND_PER_NOISE`, `TfidfModel(smartirs='ntc')`), vectorized morphosyntactic lemmatization via spaCy (`de_core_news_lg`), and unified compound decomposition (*Komposita-Zerlegung*, $|V| = 25,000$ lemmas and bigrams), we triangulate Variational Bayes Latent Dirichlet Allocation ($K = 12, U_{\text{Mass}} = -2.4760$, Supervised sLDA $U_{\text{Mass}} = -1.9650$), Quanteda Dunning's $G^2$ keyness and Structural Topic Model (STM) covariate regressions across $280,970$ secular/critical and $180,812$ confessional documents, and neural `Doc2Vec` + `c-TF-IDF` (BERTopic) clustering.

#### Zusammenfassung (Deutsch — für JCLS / ZfdG)
Obwohl die computergestützte Buch- und Literaturwissenschaft zunehmend Nationalbibliografien nutzt, um makrosoziologische Transformationen des Buchmarktes zu rekonstruieren, blieben Analysen des deutschsprachigen Sach- und Religionsbuchmarktes nach 1970 bislang meist auf kurze Katalogmetadaten beschränkt. Dieser Beitrag präsentiert eine elfstufige, § 60d UrhG- und FAIR/DDI-konforme Volltext- und Nationalbibliografie-Harvesting- sowie *Computational-Hermeneutics*-Pipeline für den Zeitraum `1970–2025`. Durch die Verknüpfung der Deutschen Nationalbibliothek (DNB SRU v1.1 MARC21 sowie `location=onlinefree` + `MARC 856` + `hsg=` für `1970–2025`) und 41 Basisklassifikations-Subcodes (`pica.bkl`) des Gemeinsamen Bibliotheksverbundes (GBV/K10plus inkl. Multi-ISBN-Auflösung) mit den *Extracted Features v2.0* des HathiTrust Research Center (HTRC), den DNB-Langzeitarchivierungsservern (`/34` und `/04`), OpenAlex (`abstract_inverted_index` und Open-Access-Monografien) und dem Internet Archive über 38 deutsche Verlage (`4.235` Imprints insgesamt) hinweg wird ein Korpus von **$461.785$ Dokumenten und Textabschnitten ($385.115.918$ deutschen Wörtern)** aus **$12.739$ vollständigen Büchern** ($4.031$ gedruckten HTRC-Monografien als *Abgeleitete Textformate*, $8.553$ kostenfreien DNB-`/34`- und `MARC-856`-Vollbüchern/EPUBs sowie $236$ OpenAlex/GBV/Archive.org-Open-Access-Monografien), **$32.021$ digitalisierten DNB-`/04`-Inhaltsverzeichnissen/Leseproben**, **$47.083$ DNB-`Inhaltstexten`**, **$17.760$ GBV/K10plus-Inhaltsverzeichnissen und `MARC 520`-Werken** sowie **$627$ rekonstruierten OpenAlex-Abstracts** ($82.283$ eindeutige Werke) erschlossen. Nach fünfstufiger Metadaten- und Entitätenbereinigung (Santana et al., 2025), vektorisierter Lemmatisierung mittels spaCy (`de_core_news_lg`) und morphologischer Komposita-Zerlegung ($|V| = 25.000$ Lemmata und Bigramme) triangulieren wir Variational Bayes LDA ($K = 12, U_{\text{Mass}} = -2,4760$, sLDA $U_{\text{Mass}} = -1,9650$), Quanteda-Keyness ($G^2$) und Structural Topic Models (STM) über $280.970$ säkular-kritische und $180.812$ konfessionelle Dokumente sowie neuronale `Doc2Vec`-`c-TF-IDF`-Cluster (BERTopic).

#### Section Outline (IMRAD Structure)
1. **Introduction:** Overcoming metadata sparsity in post-1970 German book history via § 60d UrhG Derived Text Formats (*Abgeleitete Textformate*), DNB `/34` & `MARC 856` Open-Access full books/EPUBs (`location=onlinefree`), DNB `/04` digitized reading samples, DNB `deposit.dnb.de` `Inhaltstexte`, GBV K10plus consortial TOCs/MARC 520, and OpenAlex reconstructed abstracts.
2. **Eleven-Wave Corpus Architecture (`461,785` Documents | `385.12M` Words):** Cross-walking DNB SRU (`82,283` unique works) and GBV K10plus (`41` BKL codes, `56,241` multi-ISBNs) to HTRC EF v2.0 (`4,031` printed books), DNB `/34` & `MARC 856` OA (`8,553` books/EPUBs), DNB `/04` PDFs (`32,021` works), DNB `Inhaltstexte` (`47,083` works), GBV direct works (`17,760`), OpenAlex OA & abstracts (`863` works), and Internet Archive (`38` books).
3. **FAIR/DDI Preprocessing, Vectorized German Morphosyntactic NLP & Komposita-Zerlegung:** Five-rule dynamic row-level metadata & `PER`/`LOC` stripping (`extract_row_metadata_tokens`, Santana et al., 2025; Jiménez-Badillo et al., 2020), unique-vocabulary spaCy `de_core_news_lg` tagging, compound splitting (`gottesdienst`, `religionsunterricht`, `weltkrieg`, `kirchengeschichte`, `selbstverständnis`, `religionspädagogik`, `religionskritik`), and `TfidfModel(smartirs='ntc')` + bigram detection ($|V| = 25,000$).
4. **Empirical Triangulation (LDA, Quanteda/STM, and BERTopic):** Convergence across $K=12$ Bayesian topics ($U_{\text{Mass}} = -2.4760$), Dunning's $G^2$ keyness, OLS covariate regressions, and neural `c-TF-IDF` clusters.
5. **Discussion & Open-Science Observatory:** Interactive 3-Pane Split-View Research IDE (`deutscheverlagelda.vercel.app`) and `<88 MB` GitHub corpus sharding across 20 shards.

---

### Manuscript 2: Sociology of Publishing & Cultural Production Article
* **Target Venues:** *Poetics: Journal of Empirical Research on Culture, the Media and the Arts* or *Publishing Research Quarterly*
* **Proposed Title:** *Mediating Faith and Power: Mapping Institutional Polarization Across Thirty-Eight German Publishing Houses via Structural Topic Modeling ($D = 461,785$, 1970–2025)*

#### Abstract (Flowing Prose, 235 Words)
Drawing on Pierre Bourdieu's sociology of cultural production and theories of institutional gatekeeping, this study investigates how thirty-eight German publishing houses (`4,235` total imprints) have mediated the boundaries between confessional theology, philosophical idealism, gender critique, and sociology of religion across fifty-five years (`1970–2025`). Analyzing a master corpus of **$461,785$ documents ($385,115,918$ German words across $12,739$ complete books, $32,021$ DNB `/04` PDFs/HTMLs, $47,083$ DNB `Inhaltstexte`, $17,760$ GBV works, and $627$ OpenAlex abstracts; $82,283$ unique works)** partitioned into $280,970$ secular/critical trade and academic documents (*Suhrkamp, Rowohlt, S. Fischer, Klett-Cotta, Kiepenheuer & Witsch, Wagenbach, Alibri, C.H. Beck, Meiner, Wallstein, De Gruyter / Transcript, Campus*) and $180,812$ confessional/theological documents (*Herder, Gütersloher Verlagshaus / Chr. Kaiser, Evangelische Verlagsanstalt, Patmos, Kösel, Vandenhoeck & Ruprecht, Mohr Siebeck, Calwer, Schöningh, Aschendorff*), we combine Dunning's log-likelihood keyness ($G^2$) with Structural Topic Model (STM) covariate regressions. Our findings demonstrate profound lexical and thematic polarization: confessional houses maintain a statistically bounded enclave anchored by `gott` ($G^2 = -169,185.96, p < 10^{-300}$), `theologie` ($G^2 = -94,634.90$), `kirche` ($G^2 = -69,088.21$), `glaube` ($G^2 = -27,024.93$), `jesu` ($G^2 = -25,439.06$), `christlich` ($G^2 = -24,253.20$), `jesus` ($G^2 = -23,235.77$), `paulus` ($G^2 = -20,228.93$), `israel` ($G^2 = -19,857.42$), and `christus` ($G^2 = -17,578.26$), whereas secular trade and academic presses disproportionately drive discourse around `kant` ($G^2 = +9,011.09$), `kultur` ($G^2 = +6,119.60$), `philosophie` ($G^2 = +6,042.90$), `soziologie` ($G^2 = +5,829.65$), `sozial` ($G^2 = +5,287.69$), `foucault` ($G^2 = +4,751.12$), `theorie` ($G^2 = +4,324.81$), `hegel` ($G^2 = +3,967.59$), `akteur` ($G^2 = +3,947.07$), and `moralisch` ($G^2 = +3,929.40$).

---

### Manuscript 3: Critical Theory & Sociology of Religion Article
* **Target Venues:** *New German Critique* or *Journal of Contemporary Religion*
* **Proposed Title:** *From Systematic Dogmatics to Post-Secular Sociology: Diachronic Shifts in German Religious and Critical Publishing (1970–2025)*

#### Abstract (Flowing Prose, 230 Words)
In *A Secular Age* (2007) and *Notes on Post-Secular Society* (2008), Charles Taylor and Jürgen Habermas diagnosed a structural pluralization of religious and secular frameworks in Western modernity. This article tests these diagnoses empirically across fifty-five years (`1970–2025`) of German book production using a $385.12$-million-word corpus ($461,785$ documents across $82,283$ unique works and $12,739$ complete full-text books). Estimating Structural Topic Model (STM) regressions ($\theta_k \sim \text{SecularCamp} + \text{Year}_{1970\to 2025}$) alongside neural `Doc2Vec` + `c-TF-IDF` (BERTopic) clustering, we trace the diachronic trajectory of twelve macro-discursive regimes from the post-Vatican II era to the 2020s. We show that **Conceptual Philosophy of Mind & Subjectivity** (`sinn`, `begriff`, `form`, `grund`, `denken`, Topic 7) declines in relative share by $-16.77\%$ ($t = -213.24, p < 0.0001$) and **Systematic Dogmatics & Christian Anthropology** (`gott`, `mensch`, `leben`, `welt`, `glaube`, Topic 12) shifts by $-3.93\%$ ($t = -59.76, p < 0.0001$), while **Sociology of Religion, Social Ethics & Post-Secular Theory** (`religiös`, `sozial`, `frage`, `gesellschaft`, `perspektive`, `ethik`, Topic 6) expands by $+10.45\%$ ($t = +170.52, p < 0.0001$), **Applied Social Work, Religious Pedagogy & Mindfulness in Education** (`arbeit`, `unterricht`, `gruppe`, `person`, `schule`, Topic 5) grows by $+6.82\%$ ($t = +133.17, p < 0.0001$), and **Academic Historiography & Cultural Studies** (`geschichte`, `jahrhundert`, `historisch`, `studie`, `forschung`, Topic 4) expands by $+5.13\%$ ($t = +109.44, p < 0.0001$).

---

## 4. Cover Letter Template for Journal Submission

```text
[Date]

To the Editorial Board
[Journal Name, e.g., Journal of Computational Literary Studies / Poetics / New German Critique]

Subject: Manuscript Submission — "[Insert Selected Manuscript Title]"

Dear Editors,

I am pleased to submit our original research manuscript, "[Insert Selected Manuscript Title]," for consideration for publication in [Journal Name]. This research forms part of my doctoral dissertation at the Centre for German Studies (CGS), School of Language, Literature and Culture Studies (SLL&CS), Jawaharlal Nehru University (JNU), New Delhi.

[For JCLS / ZfdG / Cultural Analytics:]
Our study presents an eleven-wave, § 60d UrhG- and FAIR/DDI-compliant DNB, GBV/K10plus, HathiTrust HTRC, and OpenAlex harvesting and multi-model computational hermeneutics pipeline spanning 1970–2025 across 38 German publishing houses and 4,235 total imprints (D = 461,785 documents, 385,115,918 original German words across 12,739 complete full-text books [4,031 HathiTrust HTRC printed books, 8,553 DNB /34 & MARC 856 open-access full books and EPUBs, and 236 OpenAlex/GBV/Archive.org open-access books], 32,021 digitized DNB /04 PDFs/HTMLs, 47,083 DNB deposit.dnb.de & /blurb/ Inhaltstexte, 17,760 GBV/K10plus works, and 627 OpenAlex reconstructed abstracts; 82,283 unique works; |V| = 25,000 lemmas and bigrams). Triangulating Variational Bayes LDA (K = 12, U_Mass = -2.4760), Quanteda/STM covariate regressions, and neural Doc2Vec + c-TF-IDF (BERTopic) clustering, we uncover the macro-historical transformation of German theological, philosophical, and sociological publishing.

[For Poetics / New German Critique / Journal of Contemporary Religion:]
Bridging computational distant reading of 461,785 documents (385.12 million German words across 82,283 unique works and 12,739 complete full-text books, 1970–2025) with the critical sociology of Pierre Bourdieu, Jürgen Habermas, Charles Taylor, and Hartmut Rosa, our study empirically maps how thirty-eight German publishing houses (including Suhrkamp, Rowohlt, S. Fischer, Klett-Cotta, Herder, Gütersloher Verlagshaus, EVA, Kösel, Patmos, and Vandenhoeck & Ruprecht) have mediated the shift across systematic dogmatics (-3.93%, p < 0.0001), philosophical critique (+4.95%, p < 0.0001), academic historiography (+5.13%, p < 0.0001), applied pedagogy and organizational praxis (+6.82%, p < 0.0001), and post-secular sociology of religion and social ethics (+10.45%, p < 0.0001).

To ensure full methodological transparency and reproducibility in accordance with open-science standards, we accompany the manuscript with an interactive 3-Pane Computational Hermeneutics Observatory (https://deutscheverlagelda.vercel.app) and open source code repository.

This manuscript is original, has not been published previously, and is not under consideration for publication elsewhere. Thank you for your time and consideration.

Sincerely,

Paul Marandi
Ph.D. Scholar
Centre for German Studies (CGS)
School of Language, Literature and Culture Studies (SLL&CS)
Jawaharlal Nehru University (JNU), New Delhi, India
```

---

## 5. Core APA 7th Edition Reference List for Manuscript Submissions

* Blei, D. M., Ng, A. Y., & Jordan, M. I. (2003). Latent Dirichlet allocation. *Journal of Machine Learning Research*, *3*, 993–1022.
* Bourdieu, P. (1993). *The field of cultural production: Essays on art and literature*. Columbia University Press.
* Carrette, J., & King, R. (2005). *Selling spirituality: The silent takeover of religion*. Routledge.
* Habermas, J. (2008). Notes on post-secular society. *New Perspectives Quarterly*, *25*(4), 17–29.
* Han, B.-C. (2014). *Psychopolitik: Neoliberalismus und die neuen Machttechniken*. S. Fischer Verlag.
* Hoffman, M., Bach, F. R., & Blei, D. M. (2010). Online learning for latent Dirichlet allocation. In *Advances in Neural Information Processing Systems* (Vol. 23, pp. 856–864).
* Illouz, E. (2008). *Saving the modern soul: Therapy, emotions, and the culture of self-help*. University of California Press.
* Mimno, D., Wallach, H., Talley, E., Leenders, M., & McCallum, A. (2011). Optimizing semantic coherence in topic models. In *Proceedings of the 2011 Conference on Empirical Methods in Natural Language Processing* (pp. 262–272). Association for Computational Linguistics.
* Piper, A. (2018). *Enumerations: Data and literary study*. University of Chicago Press.
* Röder, M., Both, A., & Hinneburg, A. (2015). Exploring the space of topic coherence measures. In *Proceedings of the Eighth ACM International Conference on Web Search and Data Mining (WSDM '15)* (pp. 399–408). ACM.
* Rosa, H. (2016). *Resonanz: Eine Soziologie der Weltbeziehung*. Suhrkamp Verlag.
* Taylor, C. (2007). *A secular age*. Harvard University Press.
