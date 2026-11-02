# ==============================================================================
# Mediating Faith and Power: Religious Authority and the German Publishing Landscape
# R quanteda + Structural Topic Model (STM) Pipeline (1970-2025)
# ==============================================================================
# Prerequisite:
#   Run `python scripts/quanteda_stm_analytics.py` first to generate
#   `data/quanteda_tokens_export.csv` (pre-lemmatized with spaCy de_core_news_lg
#   and German Komposita-Zerlegung compound splitting).
# ==============================================================================

library(quanteda)
library(quanteda.textstats)
library(quanteda.textplots)
library(stm)
library(readr)

# 1. Load spaCy-Lemmatized & Compound-Split German Corpus (1970-2025)
df <- read_csv("data/quanteda_tokens_export.csv", show_col_types = FALSE)
cat(sprintf("Loaded %d German documents/passages (1970-2025)\n", nrow(df)))

# 2. Construct quanteda Corpus with Document-Level Metadata (docvars)
corp <- corpus(
  df,
  docid_field = "doc_id",
  text_field = "spacy_compound_tokens"
)

# 3. Tokenize & Build Trimmed Document-Feature Matrix (dfm)
toks <- tokens(
  corp,
  remove_punct = TRUE,
  remove_numbers = TRUE,
  remove_symbols = TRUE
)

dfmat <- dfm(toks) |>
  dfm_trim(min_docfreq = 5, max_docfreq = 0.55, docfreq_type = "prop")

cat(sprintf("DFM Dimensions: %d documents x %d features\n", ndoc(dfmat), nfeat(dfmat)))

# 4. Dunning's Log-Likelihood (G^2) Keyness: Secular/Critical vs. Confessional Publishers
dfmat_camp <- dfm_group(dfmat, groups = docvars(dfmat, "publisher_camp"))
keyness_camp <- textstat_keyness(
  dfmat_camp,
  target = "Secular / Critical / Trade",
  measure = "lr"
)
print(head(keyness_camp, 20))
write_csv(keyness_camp, "data/r_quanteda_keyness_publisher_camp.csv")

# 5. Keywords-in-Context (KWIC) Concordancer for Core Signifiers
kwic_religionskritik <- kwic(toks, pattern = "religionskritik*", window = 10)
kwic_saekularisierung <- kwic(toks, pattern = "säkularisierung*", window = 10)
write_csv(as.data.frame(kwic_religionskritik), "data/r_quanteda_kwic_religionskritik.csv")

# 6. Convert quanteda dfm to STM Format and Fit Structural Topic Model (K = 12)
stm_input <- convert(dfmat, to = "stm")

stm_fit <- stm(
  documents = stm_input$documents,
  vocab = stm_input$vocab,
  K = 12,
  prevalence = ~ publisher_camp + s(year),
  data = stm_input$meta,
  init.type = "Spectral",
  max.em.its = 75,
  verbose = TRUE
)

# 7. Estimate Covariate Effects (Publisher Camp & Diachronic 1970-2025 Spline)
prep_effects <- estimateEffect(
  1:12 ~ publisher_camp + s(year),
  stmobj = stm_fit,
  metadata = stm_input$meta,
  uncertainty = "Global"
)

summary(prep_effects)
saveRDS(list(model = stm_fit, effects = prep_effects), file = "data/stm_model_1970_2025.rds")
cat("Completed R quanteda + STM pipeline!\n")
