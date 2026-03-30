# Phase 1: Advanced Preprocessing Refinement (GSD)

## 🎯 Goal
Refine the `lda_pipeline.py` script to handle high-fidelity German NLP, including N-gram (bigram/trigram) detection and specialized POS weighting (Prioritizing Nouns/PROPN).

---

## 🌊 Wave 1: N-Gram & POS Logic

<task type="auto">
  <name>Implement N-Gram detection</name>
  <files>lda_pipeline.py</files>
  <action>
    Use `gensim.models.Phrases` and `Phraser` to detect common bigrams/trigrams in the German corpus (e.g., "Verlagsgruppe_Georg_von_Holtzbrinck").
    Integrate these into the preprocessing loop.
  </action>
  <verify>Run the script on mock data and check tokens for "_" underscore separators.</verify>
  <done>Bigrams like "Bertelsmann_Verlag" are detected and tokenized as single units.</done>
</task>

<task type="auto">
  <name>Refine POS Filtering & Domain Stopwords</name>
  <files>lda_pipeline.py, config.py</files>
  <action>
    Update `config.ALLOWED_POSTAGS` to include `PROPN` (Proper Nouns) for publisher names.
    Add a domain-specific stopword list (e.g., "ISBN", "Seiten", "Auflage").
  </action>
  <verify>Check processed tokens for generic administrative words.</verify>
  <done>Tokens only contain high-value thematic and institutional nouns.</done>
</task>

---

## ✅ Phase Verification
- [ ] Successful training run with N-grams.
- [ ] Qualitative check of top 10 keywords per topic.
