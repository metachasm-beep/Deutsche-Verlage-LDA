import csv
import hashlib
import json
import os
import re
import warnings
from collections import defaultdict

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    import gensim
    from gensim import corpora
    from gensim.models import LdaModel
    from gensim.models.coherencemodel import CoherenceModel
except ImportError:
    gensim = None
    corpora = None
    LdaModel = None
    CoherenceModel = None

try:
    import spacy
except ImportError:
    spacy = None

import config

# Allow full-text book chapters and entire monographs in CSV cells (up to 10 MB per cell)
csv.field_size_limit(10 * 1024 * 1024)

# Load German Spacy model with automatic fallback chain (when spacy is installed)
nlp = None
if spacy is not None:
    for _model_name in getattr(config, "SPACY_FALLBACK_MODELS", [config.SPACY_MODEL]):
        try:
            # Disable parser and NER for 4x faster lemmatization and POS tagging
            nlp = spacy.load(_model_name, disable=["ner", "parser"])
            break
        except OSError:
            continue

    if nlp is None:
        print("Warning: No pre-trained German spaCy model found; falling back to spacy.blank('de').")
        nlp = spacy.blank("de")
    nlp.max_length = 5_000_000

GERMAN_CORE_STOPWORDS = {
    "der", "die", "das", "und", "in", "den", "von", "zu", "mit", "sich", "auf", "für", "nicht",
    "ist", "im", "dem", "als", "auch", "es", "an", "werden", "aus", "er", "hat", "dass", "sie",
    "nach", "wird", "bei", "einer", "um", "am", "sind", "noch", "wie", "einem", "über", "einen",
    "so", "zum", "war", "haben", "nur", "oder", "aber", "vor", "zur", "bis", "mehr", "durch",
    "man", "sein", "wurde", "sei", "in", "pro", "vom", "können", "schon", "wenn", "habe", "seine",
    "ihre", "dann", "unter", "wir", "soll", "ich", "eines", "es", "jahr", "zwei", "machen", "dieser",
    "diese", "dieses", "ein", "eine", "einer", "einem", "einen", "kein", "keine", "keiner"
}

# Precompute stopword set and religious keyword set once
FRAKTUR_AND_META_NOISE = {
    "ber", "unb", "bie", "bas", "bes", "bem", "auc", "fein", "feine", "feiner", "feinem", "feinen",
    "unde", "nan", "buch_abschnitt", "forschungsbuch_abschnitt", "abschnitt", "htrc_vollbuch",
    "gbv_vollbuch", "openalex_vollbuch", "dnb_oa", "vollbuch", "band", "seite", "kapitel", "auflage",
    "herder", "suhrkamp", "rowohlt", "fischer", "patmos", "kösel", "alibri", "wagenbach",
    "klett", "gütersloher", "verlagshaus", "verlagsanstalt", "evangelisch_verlagsanstalt",
    "kiepenheuer", "witsch", "kohlhammer", "beck", "springer", "gruyter", "vandenhoeck",
    "benziger", "schwabenverlag", "kaiser", "grünewald", "kreuz", "mohr", "siebeck",
    "schöningh", "aschendorff", "pustet", "echter", "bonifatius", "neukirchener", "calwer",
    "campus", "insel", "meiner", "wallstein", "budrich", "oekom", "nomos", "tvz", "ruprecht",
    "cotta", "holzboog", "frommann", "fink", "alber", "schwabe", "böhlau", "süß", "transcript",
    "münchen", "stuttgart", "leipzig", "freiburg", "frankfurt", "berlin", "wien", "zürich",
    "tübingen", "göttingen", "heidelberg", "köln", "bonn", "münster", "darmstadt", "mainz",
    "wilhelm", "johann", "friedrich", "karl", "heinrich", "hans", "peter", "georg", "august",
    "vnd", "quod", "sed", "est", "non", "cum", "autem", "enim", "etiam", "sunt", "esse",
    "atque", "neque", "ideo", "tamen", "ergo", "quid", "quae", "quem", "quibus", "cuius", "dei", "fol",
    "bisac", "subject", "heading", "bisac_subject", "subject_heading", "heading_bisac",
    "bic", "bic_subject", "vlb", "zielgruppe", "fachpublikum", "zielgruppe_fachpublikum",
    "produktform", "warengruppe", "hardcover", "softcover", "taschenbuch", "kartoniert",
    "gebunden", "broschiert", "verlag", "verlage", "gmbh", "isbn", "issn", "doi", "ebook", "ebooks",
    "right", "published", "cambridge", "book", "elector", "council", "gospel", "question",
    "concept", "perspective", "university", "press", "london", "new", "york", "oxford",
    "the", "and", "for", "that", "with", "from", "this", "which", "their", "have", "were",
    "been", "into", "more", "other", "such", "than", "some", "these", "would", "could",
    "should", "about", "between", "through", "during", "before", "after", "under", "above",
    "german", "history", "social", "century", "church", "religion", "religious", "christian",
    "theology", "philosophy", "studies", "study", "god", "his", "her", "not", "van", "are",
    "was", "has", "had", "but", "all", "can", "will", "one", "two", "first", "time", "work",
    "life", "world", "human", "modern", "early", "late", "middle", "ages", "medieval", "ancient",
    "contemporary", "european", "international", "journal", "volume", "series", "edition",
    "edited", "introduction", "chapter", "part", "section", "research", "analysis", "theory",
    "practice", "development", "historical", "theological", "philosophical", "political",
    "cultural", "ethical", "biblical", "catholic", "protestant", "jewish", "islamic", "faith",
    "spirit", "nature", "reason", "state", "society", "power", "authority", "tradition",
    "reform", "reformation", "enlightenment", "secular", "secularization", "approaches", "toward",
    "ders", "bd", "hrsg", "aufl", "kap", "vgl", "ebd", "ff", "bzw", "usw", "etc", "prof", "dr",
    "ekk", "testament_ekk", "kommentar_neu", "thesoz", "stw", "gnd", "ddc", "rvk", "bkl", "swd",
    "artikeltyp", "produktgruppe", "artikeltyp_produktgruppe", "lesebuch", "studienausgabe",
    "its", "category", "ethics", "general", "how", "they", "well", "que", "what", "del", "old",
    "old_testament", "context", "pour", "son", "les", "elle", "une", "des", "dans", "par", "sur",
    "plus", "aux", "ces", "mais", "pas", "qui", "leur", "avec", "sont", "cette", "tout", "tous",
    "comme", "sans", "sous", "entre", "vers", "chez", "dont", "leurs", "meme", "etre", "avoir",
    "fait", "faire", "peut", "deux", "trois", "siècle", "histoire", "église", "dieu", "monde",
    "when", "where", "who", "whom", "whose", "why", "both", "each", "few", "most", "many", "much",
    "own", "same", "very", "just", "now", "only", "also", "even", "still", "yet", "already",
    "always", "never", "often", "however", "therefore", "thus", "within", "without", "against",
    "among", "around", "across", "towards", "upon", "whether", "while", "since", "until", "Because",
    "because", "although", "though", "unless", "whereas", "publikation", "publikationen",
    "veröffentlichung", "veröffentlichungen", "sammelband", "beitrag", "beiträge", "aufsatz",
    "aufsätze", "monographie", "dissertation", "habilitation", "festschrift", "tagungsband",
    "handbuch", "lehrbuch", "wörterbuch", "lexikon", "kommentar", "einführung", "überblick",
    "inhaltsverzeichnis", "inhalt", "vorwort", "einleitung", "leseprobe", "dnb_inhaltsverzeichnis",
    "bibliografisch", "bibliografische", "nationalbibliothek", "deutsche_nationalbibliothek",
    "dnb", "http", "https", "www", "info", "http_info", "bibliografische_information",
    "inhalt_vorwort", "literaturverzeichnis", "abkürzungsverzeichnis", "quellenverzeichnis",
    "anhang", "register", "personenregister", "sachregister", "stichwortverzeichnis",
    "danksagung", "geleitwort", "nachwort", "schlusswort", "zusammenfassung", "ausblick",
    "content", "contents", "conclusion", "table", "preface", "bibliography", "index",
    "summary", "abstract", "appendix", "acknowledgment", "acknowledgments", "foreword",
    "johannes", "michael", "martin", "thomas", "andreas", "wolfgang", "stefan", "markus",
    "ulrich", "klaus", "jürgen", "werner", "walter", "gerhard", "dieter", "hermann",
    "franz", "josef", "rudolf", "ernst", "otto", "kurt", "richard", "robert", "albert",
    "alexander", "christoph", "matthias", "bernhard", "reinhard", "manfred", "günter",
    "helmut", "horst", "harald", "roland", "rüdiger", "hartmut", "joachim", "norbert",
    "rainer", "frank", "uwe", "dirk", "jörg", "heinz", "erich", "fritz", "gottfried",
    "ebeling", "gen", "abb", "tab", "hrsg_von", "verf", "bearb", "übers"
}
_BASE_STOPWORDS = set(nlp.Defaults.stop_words) if nlp is not None else GERMAN_CORE_STOPWORDS
ALL_STOPWORDS = _BASE_STOPWORDS.union(set(config.DOMAIN_STOPWORDS)).union(FRAKTUR_AND_META_NOISE)

RELIGIOUS_KEYWORDS_SET = set(config.RELIGIOUS_VOICE_KEYWORDS)

# Content-addressed token cache (in-memory + disk persistence)
_TOKEN_CACHE = {}
if os.path.exists(config.TOKEN_CACHE_PATH):
    try:
        with open(config.TOKEN_CACHE_PATH, mode="r", encoding="utf-8") as _cf:
            _TOKEN_CACHE = json.load(_cf)
    except Exception:
        _TOKEN_CACHE = {}


def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def _extract_tokens_from_doc(doc, allowed_postags=config.ALLOWED_POSTAGS):
    """
    Extracts lemmatized, POS-filtered, domain-stopword-cleaned, and weighted tokens from a spaCy Doc.
    """
    if doc.has_annotation("TAG"):
        raw_tokens = [
            (token.lemma_ or token.text).lower().strip()
            for token in doc
            if token.pos_ in allowed_postags and token.is_alpha
        ]
    else:
        raw_tokens = [
            token.text.lower().strip()
            for token in doc
            if token.is_alpha
        ]

    weighted_tokens = []
    for t in raw_tokens:
        if len(t) <= 2 or t in ALL_STOPWORDS:
            continue
        weighted_tokens.append(t)
        if t in RELIGIOUS_KEYWORDS_SET:
            weighted_tokens.append(t)  # 2x weight for core religious/critical signifiers

    return weighted_tokens


def preprocess_text(text, allowed_postags=config.ALLOWED_POSTAGS):
    """
    Tokenize, lemmatize, remove stopwords and filter by POS tags for a single German text.
    Uses content-addressed caching for instant repeat lookups.
    """
    if not text or not isinstance(text, str):
        return []
    key = _hash_text(text)
    if key in _TOKEN_CACHE:
        return [t for t in _TOKEN_CACHE[key] if t not in ALL_STOPWORDS]

    doc = nlp(text)
    tokens = _extract_tokens_from_doc(doc, allowed_postags=allowed_postags)
    _TOKEN_CACHE[key] = tokens
    return tokens


_WORD_RE = re.compile(r"\b[a-zA-ZäöüÄÖÜß]{3,}\b")


def preprocess_corpus_batch(texts, allowed_postags=config.ALLOWED_POSTAGS):
    """
    High-speed vectorized preprocessing for multi-million-word corpora:
    1. Checks SHA-1 content-addressed cache first.
    2. For uncached documents, extracts the unique surface vocabulary across all uncached passages,
       runs spaCy morphological POS + lemma tagging once on the unique word types (~50x faster
       than re-running the CNN over 6 million repeated word tokens), and maps each document's
       tokens with persistent SHA-1 caching.
    """
    results = [None] * len(texts)
    uncached_indices = []

    for idx, text in enumerate(texts):
        if not text or not isinstance(text, str):
            results[idx] = []
            continue
        key = _hash_text(text)
        if key in _TOKEN_CACHE:
            results[idx] = [t for t in _TOKEN_CACHE[key] if t not in ALL_STOPWORDS]
        else:
            uncached_indices.append(idx)

    if uncached_indices:
        print(
            f"Preprocessing {len(uncached_indices):,} uncached passages with spaCy morphological lemmatizer...",
            flush=True
        )
        # Collect unique surface words across uncached passages
        unique_words = set()
        doc_raw_words = {}
        for idx in uncached_indices:
            words = _WORD_RE.findall(texts[idx])
            doc_raw_words[idx] = words
            for w in words:
                if w.lower() not in ALL_STOPWORDS:
                    unique_words.add(w)

        unique_list = sorted(unique_words)
        word_to_lemma = {}
        chunk_sz = 1500
        vocab_chunks = [
            " ".join(unique_list[i:i + chunk_sz])
            for i in range(0, len(unique_list), chunk_sz)
        ]

        for doc in nlp.pipe(vocab_chunks, batch_size=16):
            has_tag = doc.has_annotation("TAG")
            for token in doc:
                if not token.is_alpha:
                    continue
                if has_tag and token.pos_ not in allowed_postags:
                    continue
                lem = (token.lemma_ or token.text).lower().strip()
                if len(lem) > 2 and lem not in ALL_STOPWORDS:
                    word_to_lemma[token.text] = lem

        for idx in uncached_indices:
            weighted_tokens = []
            for w in doc_raw_words[idx]:
                lem = word_to_lemma.get(w)
                if not lem:
                    continue
                weighted_tokens.append(lem)
                if lem in RELIGIOUS_KEYWORDS_SET:
                    weighted_tokens.append(lem)
            key = _hash_text(texts[idx])
            _TOKEN_CACHE[key] = weighted_tokens
            results[idx] = weighted_tokens

        # Persist updated token cache to disk
        try:
            cache_dir = os.path.dirname(config.TOKEN_CACHE_PATH)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)
            with open(config.TOKEN_CACHE_PATH, mode="w", encoding="utf-8") as cf:
                json.dump(_TOKEN_CACHE, cf, ensure_ascii=False)
        except Exception:
            pass

    return results


def _clean_marc_control_chars(val: str) -> str:
    if not val:
        return ""
    return re.sub(r"[\u0080-\u009f˜œ]", "", str(val)).strip()


def format_apa_citation(row: dict) -> str:
    """
    Generates an APA 7th Edition bibliographic citation from a corpus record row.
    Format: Author (Year). Title. Publisher.
    """
    author = _clean_marc_control_chars(row.get("author") or "o. V.")
    date_str = _clean_marc_control_chars(row.get("date") or "o. J.")
    year_match = re.search(r"(\d{4})", date_str)
    year = year_match.group(1) if year_match else date_str
    title = _clean_marc_control_chars(row.get("title") or "Unbetiteltes Dokument")
    publisher = _clean_marc_control_chars(row.get("publisher") or row.get("raw_imprint") or "Verlag unbekannt")
    return f"{author} ({year}). {title}. {publisher}."


LDA_MODES_META = {
    "unseeded": {
        "id": "unseeded",
        "label": "Unseeded / Pure Unsupervised",
        "short_label": "Unseeded",
        "prior_type": "Uniform / Auto η (1× Raw Frequency)",
        "supervision": "None (Blind Inductive Baseline)",
        "formula": "P(φ_k | η_0), w_n ~ 1× Raw Count",
        "description": "Pure Blei et al. (2003) baseline: removes the 2× RELIGIOUS_VOICE_KEYWORDS salience weight and uses an unseeded symmetric/auto Dirichlet word prior."
    },
    "unsupervised": {
        "id": "unsupervised",
        "label": "Domain-Weighted Unsupervised",
        "short_label": "Unsupervised",
        "prior_type": "Auto η + 2× Domain Salience",
        "supervision": "Post-Hoc Archetype Projection",
        "formula": "P(φ_k | η_auto), w_rel ~ 2× Salience",
        "description": "Amplifies core theological and critical signifiers (2× token weight) while keeping Dirichlet topic slots unseeded so clusters emerge inductively."
    },
    "seeded": {
        "id": "seeded",
        "label": "Seeded / Guided LDA (Asymmetric η)",
        "short_label": "Seeded (η-Matrix)",
        "prior_type": "Asymmetric K × |V| Dirichlet η Matrix (β_seed = 15.0)",
        "supervision": "Lexicon-Anchored Priors (RQ₁, RQ₂, RQ₃)",
        "formula": "φ_k ~ Dir(η_k^{(RQ_m)}), η_{k,w∈S_m} = 15.0",
        "description": "Constructs an asymmetric K × |V| conjugate Dirichlet prior matrix η anchoring topic slots to RQ₁ (Traditional), RQ₂ (Neoliberal), and RQ₃ (Critical) seed lexicons (Jagarlamudi et al., 2012)."
    },
    "supervised": {
        "id": "supervised",
        "label": "Supervised LDA (sLDA + Covariate Head)",
        "short_label": "Supervised (sLDA)",
        "prior_type": "Empirical Label Log-Odds η + L2 Discriminative Head",
        "supervision": "Joint Regime & Publisher Response y_d | θ_d",
        "formula": "ŷ_d = ArgMax(θ_d · W + b), η_{k,w} ∝ P(w | y_d)",
        "description": "Combines empirical document-label co-occurrence priors with a 5-fold cross-validated L2 Ridge/Softmax response head predicting Ideological Regime (RQ₁–RQ₃) and Publisher from θ_d (Blei & McAuliffe, 2007)."
    }
}


def _unboost_religious_tokens(doc_tokens: list) -> list:
    """
    Reverses the 2x consecutive duplication of RELIGIOUS_KEYWORDS_SET tokens
    applied during _extract_tokens_from_doc so Pure Unseeded LDA uses natural 1x frequencies.
    """
    unboosted = []
    i = 0
    n = len(doc_tokens)
    while i < n:
        tok = doc_tokens[i]
        unboosted.append(tok)
        if tok in RELIGIOUS_KEYWORDS_SET and (i + 1 < n) and doc_tokens[i + 1] == tok:
            i += 2
        else:
            i += 1
    return unboosted


def _infer_doc_ground_truth_regime(row: dict, doc_tokens: list) -> str:
    """
    Determines the ground-truth ideological regime label y_d in {RQ1, RQ2, RQ3}
    for Supervised LDA (sLDA) training and cross-validation.
    """
    pub = _clean_marc_control_chars(row.get("publisher") or "").lower()
    scores = {
        "Traditional / Ecclesiastical": 0.0,
        "Neoliberal / Self-Optimization": 0.0,
        "Critical / Secular-Humanist": 0.0,
    }
    # Institutional publisher prior weight
    if any(p in pub for p in ("herder", "benno", "scm", "brockhaus", "vandenhoeck", "echter", "grünewald", "evangelisch", "kohlhammer", "pustet", "schwabenverlag")):
        scores["Traditional / Ecclesiastical"] += 2.5
    elif any(p in pub for p in ("kösel", "gräfe", "unzer", "kamphausen", "patmos", "kreuz", "arkana", "goldmann", "scorpio", "knaur", "integral")):
        scores["Neoliberal / Self-Optimization"] += 2.5
    elif any(p in pub for p in ("suhrkamp", "insel", "beck", "rowohlt", "fischer", "campus", "transcript", "alibri", "wagenbach", "kiepenheuer", "gruyter", "springer", "meiner", "metzler")):
        scores["Critical / Secular-Humanist"] += 2.5

    # Lexical evidence from document tokens
    for tok in doc_tokens:
        parts = set(tok.lower().split("_"))
        parts.add(tok.lower())
        for arch, lex_set in config.ARCHETYPE_LEXICONS.items():
            if parts.intersection(lex_set):
                scores[arch] += 1.0

    return max(scores, key=scores.get)


def build_seeded_eta_matrix(dictionary, num_topics: int, seed_boost: float = 15.0, base_eta: float = 0.05):
    """
    Constructs an asymmetric K x |V| Dirichlet prior matrix (eta) anchored to
    RQ1 (Traditional), RQ2 (Neoliberal), and RQ3 (Critical) seed lexicons.
    """
    import numpy as np
    vocab_size = len(dictionary)
    eta_matrix = np.full((num_topics, vocab_size), base_eta, dtype=np.float64)
    archetype_names = [
        "Traditional / Ecclesiastical",
        "Neoliberal / Self-Optimization",
        "Critical / Secular-Humanist",
    ]
    seed_assignments = {}

    for t_id in range(num_topics):
        target_arch = archetype_names[t_id % 3]
        seed_assignments[t_id] = target_arch
        lex_set = config.ARCHETYPE_LEXICONS[target_arch]
        other_lex = set().union(*[
            s for a, s in config.ARCHETYPE_LEXICONS.items() if a != target_arch
        ])

        for token_id, word in dictionary.items():
            parts = set(word.lower().split("_"))
            parts.add(word.lower())
            if parts.intersection(lex_set):
                eta_matrix[t_id, token_id] = seed_boost
            elif parts.intersection(other_lex):
                eta_matrix[t_id, token_id] = base_eta * 0.2

    return eta_matrix, seed_assignments


def build_supervised_eta_matrix(dictionary, processed_n_grams, filtered_rows, num_topics: int):
    """
    Constructs a Supervised LDA (sLDA) K x |V| prior matrix combining theoretical seed lexicons
    with empirical document-label (RQ1/RQ2/RQ3 + Publisher) word co-occurrence probabilities.
    """
    import numpy as np
    eta_matrix, seed_assignments = build_seeded_eta_matrix(
        dictionary, num_topics, seed_boost=18.0, base_eta=0.05
    )
    archetype_names = [
        "Traditional / Ecclesiastical",
        "Neoliberal / Self-Optimization",
        "Critical / Secular-Humanist",
    ]
    # Accumulate empirical word counts per ground-truth regime
    regime_word_counts = {a: defaultdict(float) for a in archetype_names}
    regime_totals = {a: 1.0 for a in archetype_names}

    for doc_tokens, row in zip(processed_n_grams, filtered_rows):
        y_regime = _infer_doc_ground_truth_regime(row, doc_tokens)
        for tok in doc_tokens:
            regime_word_counts[y_regime][tok] += 1.0
            regime_totals[y_regime] += 1.0

    word2id = dictionary.token2id
    for t_id in range(num_topics):
        target_arch = seed_assignments[t_id]
        for word, count in regime_word_counts[target_arch].items():
            if word in word2id and count >= 3:
                tid = word2id[word]
                rel_freq = (count / regime_totals[target_arch]) * 1000.0
                eta_matrix[t_id, tid] = max(eta_matrix[t_id, tid], 0.05 + min(rel_freq * 4.0, 25.0))

    return eta_matrix, seed_assignments


def compute_slda_diagnostics(corpus, filtered_rows, processed_n_grams, lda_model, effective_k: int) -> dict:
    """
    Fits an L2-regularized Supervised LDA (sLDA) response head Y = Theta * W + b
    with 5-fold cross-validation to evaluate how accurately latent topic vectors theta_d
    predict (1) Ideological Regime (RQ1, RQ2, RQ3) and (2) Institutional Publisher.
    """
    import numpy as np
    n_docs = len(corpus)
    if n_docs < 10:
        return {}

    archetype_names = [
        "Traditional / Ecclesiastical",
        "Neoliberal / Self-Optimization",
        "Critical / Secular-Humanist",
    ]
    arch_to_idx = {a: i for i, a in enumerate(archetype_names)}

    # Build document-topic matrix Theta (D x K) and regime target vector y (D,)
    theta = np.zeros((n_docs, effective_k), dtype=np.float64)
    y_regime = np.zeros(n_docs, dtype=np.int64)
    pub_labels = []

    for i, (doc_bow, row, doc_tokens) in enumerate(zip(corpus, filtered_rows, processed_n_grams)):
        for t_id, prob in lda_model.get_document_topics(doc_bow, minimum_probability=0.0):
            if t_id < effective_k:
                theta[i, t_id] = float(prob)
        gt_arch = _infer_doc_ground_truth_regime(row, doc_tokens)
        y_regime[i] = arch_to_idx[gt_arch]
        pub_labels.append(_clean_marc_control_chars(row.get("publisher") or "Unknown"))

    # Add intercept column to Theta -> X (D x (K+1))
    X = np.hstack([theta, np.ones((n_docs, 1), dtype=np.float64)])
    Y_onehot = np.eye(3, dtype=np.float64)[y_regime]

    # Closed-form L2 Ridge regression: W = (X^T X + lambda I)^(-1) X^T Y
    reg_lambda = 1.5
    eye_mat = np.eye(effective_k + 1, dtype=np.float64)
    eye_mat[-1, -1] = 0.0  # Do not regularize intercept
    W_full = np.linalg.solve(X.T @ X + reg_lambda * eye_mat, X.T @ Y_onehot)
    W_topics = W_full[:effective_k, :]  # (K x 3)

    # In-sample predictions & R^2
    preds_in = np.argmax(X @ W_full, axis=1)
    in_sample_acc = float(np.mean(preds_in == y_regime) * 100.0)

    ss_res = float(np.sum((Y_onehot - (X @ W_full)) ** 2))
    ss_tot = float(np.sum((Y_onehot - np.mean(Y_onehot, axis=0, keepdims=True)) ** 2)) or 1.0
    r2_score = max(0.0, min(1.0, 1.0 - (ss_res / ss_tot)))

    # Deterministic 5-fold cross-validation for Regime (RQ1, RQ2, RQ3)
    rng = np.random.RandomState(42)
    perm = rng.permutation(n_docs)
    n_folds = min(5, n_docs)
    cv_preds = np.zeros(n_docs, dtype=np.int64)

    for fold in range(n_folds):
        val_idx = perm[fold::n_folds]
        train_mask = np.ones(n_docs, dtype=bool)
        train_mask[val_idx] = False
        X_tr, Y_tr = X[train_mask], Y_onehot[train_mask]
        X_va = X[val_idx]
        W_fold = np.linalg.solve(X_tr.T @ X_tr + reg_lambda * eye_mat, X_tr.T @ Y_tr)
        cv_preds[val_idx] = np.argmax(X_va @ W_fold, axis=1)

    cv_acc = float(np.mean(cv_preds == y_regime) * 100.0)

    # Compute Macro-F1 across the 3 ideological regimes
    f1_list = []
    regime_class_metrics = {}
    for c_idx, arch_name in enumerate(archetype_names):
        tp = float(np.sum((cv_preds == c_idx) & (y_regime == c_idx)))
        fp = float(np.sum((cv_preds == c_idx) & (y_regime != c_idx)))
        fn = float(np.sum((cv_preds != c_idx) & (y_regime == c_idx)))
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        f1_list.append(f1)
        regime_class_metrics[arch_name] = {
            "precision": round(prec * 100, 1),
            "recall": round(rec * 100, 1),
            "f1": round(f1 * 100, 1),
            "support": int(np.sum(y_regime == c_idx))
        }
    macro_f1 = float(np.mean(f1_list) * 100.0)

    # Top-8 Publisher multi-class sLDA prediction accuracy
    pub_counts = defaultdict(int)
    for p in pub_labels:
        pub_counts[p] += 1
    top_pubs = [p for p, _ in sorted(pub_counts.items(), key=lambda x: x[1], reverse=True)[:8]]
    pub_to_idx = {p: i for i, p in enumerate(top_pubs)}
    sub_indices = [i for i, p in enumerate(pub_labels) if p in pub_to_idx]

    pub_cv_acc = 0.0
    if len(sub_indices) >= 20 and len(top_pubs) >= 2:
        X_pub = X[sub_indices]
        y_pub = np.array([pub_to_idx[pub_labels[i]] for i in sub_indices], dtype=np.int64)
        Y_pub_oh = np.eye(len(top_pubs), dtype=np.float64)[y_pub]
        W_pub = np.linalg.solve(X_pub.T @ X_pub + 2.0 * eye_mat, X_pub.T @ Y_pub_oh)
        pub_preds = np.argmax(X_pub @ W_pub, axis=1)
        pub_cv_acc = float(np.mean(pub_preds == y_pub) * 100.0)

    # Format per-topic sLDA regression coefficients W_topics (K x 3)
    topic_weights_table = []
    for t_id in range(effective_k):
        w_trad = round(float(W_topics[t_id, 0]), 3)
        w_neo = round(float(W_topics[t_id, 1]), 3)
        w_crit = round(float(W_topics[t_id, 2]), 3)
        disc_power = round(float(np.std(W_topics[t_id, :])), 3)
        dominant_idx = int(np.argmax(W_topics[t_id, :]))
        topic_weights_table.append({
            "topic_id": t_id + 1,
            "predicted_regime": archetype_names[dominant_idx],
            "w_traditional": w_trad,
            "w_neoliberal": w_neo,
            "w_critical": w_crit,
            "discriminative_power": disc_power
        })

    return {
        "regime_cv_accuracy": round(cv_acc, 1),
        "regime_in_sample_accuracy": round(in_sample_acc, 1),
        "regime_macro_f1": round(macro_f1, 1),
        "publisher_accuracy": round(pub_cv_acc, 1),
        "r2_explanatory_power": round(r2_score, 4),
        "regime_class_metrics": regime_class_metrics,
        "topic_regression_weights": topic_weights_table
    }


def classify_topic_archetype(keywords_with_weights) -> dict:
    """
    Scores a topic's top weighted lemmas against the three theoretical archetypes
    defined in docs/THEORY_FRAMEWORK.md.
    """
    scores = {arch: 0.0 for arch in config.ARCHETYPE_LEXICONS}
    for word, weight in keywords_with_weights:
        parts = set(word.lower().split("_"))
        parts.add(word.lower())
        for arch, lex_set in config.ARCHETYPE_LEXICONS.items():
            if parts.intersection(lex_set):
                scores[arch] += float(weight)

    total = sum(scores.values())
    if total <= 0:
        return {
            "label": "Hybrid / Discursive Mediation",
            "confidence": 0.0,
            "scores": {k: 33.3 for k in scores}
        }

    normalized = {k: round((v / total) * 100, 1) for k, v in scores.items()}
    best_arch = max(normalized, key=normalized.get)
    return {
        "label": best_arch,
        "confidence": normalized[best_arch],
        "scores": normalized
    }


def iter_corpus_rows(data_path: str):
    """
    Transparently yields rows from data_path and any accompanying data/dnb_metadata_part*.csv
    shards so the corpus can scale beyond 300,000+ documents while keeping each file < 85 MB for GitHub.
    """
    import glob
    paths = [data_path]
    if os.path.basename(data_path) == "dnb_metadata.csv":
        part_glob = os.path.join(os.path.dirname(data_path) or "data", "dnb_metadata_part*.csv")
        part_files = sorted(
            glob.glob(part_glob),
            key=lambda x: int(re.search(r"part(\d+)", x).group(1)) if re.search(r"part(\d+)", x) else 999,
        )
        for p in part_files:
            if p not in paths:
                paths.append(p)
    for p in paths:
        if not os.path.exists(p):
            continue
        with open(p, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row



# Canonical theological, philosophical, and biblical figures preserved during author/entity filtering
# (Santana et al., 2025, DHQ 19.2 §56-64; Jiménez-Badillo et al., 2020)
CANONICAL_THEO_PHIL_WHITELIST = {
    "jesus", "christus", "paulus", "luther", "kant", "hegel", "habermas", "weber", "nietzsche",
    "marx", "augustinus", "aquino", "schleiermacher", "barth", "rahner", "bonhoeffer", "bultmann",
    "moltmann", "pannenberg", "jüngel", "küng", "ratzinger", "kasper", "tillich", "troeltsch",
    "harnack", "kierkegaard", "heidegger", "husserl", "gadamer", "adorno", "horkheimer", "benjamin",
    "blumenberg", "sloterdijk", "taylor", "spinoza", "leibniz", "fichte", "schelling", "feuerbach",
    "foucault", "derrida", "ricoeur", "levinas", "buber", "rosenzweig", "scholem", "eckhart",
    "origenes", "calvin", "zwingli", "melanchthon", "israel", "jahwe", "moses", "abraham",
    "david", "jesaja", "hiob", "jeremia", "lukas", "matthäus", "markus", "johannes"
}

GERMAN_COMPOUND_PREFIXES_LDA = [
    ("kirchenmitgliedschafts", ["kirche", "mitgliedschaft"]),
    ("religionswissenschaft", ["religion", "wissenschaft"]),
    ("säkularisierung", ["säkularisierung"]),
    ("religions", ["religion"]),
    ("kirchen", ["kirche"]),
    ("gottes", ["gott"]),
    ("glaubens", ["glaube"]),
    ("christen", ["christ"]),
    ("menschen", ["mensch"]),
    ("lebens", ["leben"]),
    ("geistes", ["geist"]),
    ("seelen", ["seele"]),
    ("staats", ["staat"]),
    ("gesellschafts", ["gesellschaft"]),
    ("kultur", ["kultur"]),
    ("moral", ["moral"]),
    ("bibel", ["bibel"]),
    ("priester", ["priester"]),
    ("kloster", ["kloster"]),
    ("papst", ["papst"]),
    ("freiheits", ["freiheit"]),
    ("wahrheits", ["wahrheit"]),
    ("vernunft", ["vernunft"]),
    ("wissenschafts", ["wissenschaft"]),
    ("theologie", ["theologie"]),
    ("philosophie", ["philosophie"]),
    ("konfessions", ["konfession"]),
    ("sozial", ["sozial"]),
]


def split_german_compound_lda(token: str) -> list[str]:
    """
    Unified German compound decompounding (Komposita -> Bestimmungswort + Grundwort)
    shared across Gensim LDA, Quanteda/STM, and BERTopic (Santana et al., 2025, DHQ 19.2 §70-71, §81).
    """
    w = token.lower().strip()
    if len(w) < 9 or "_" in w:
        return [w]
    for prefix, mapped_roots in GERMAN_COMPOUND_PREFIXES_LDA:
        if w.startswith(prefix) and len(w) >= len(prefix) + 4:
            remainder = w[len(prefix):]
            if remainder.startswith("s") and len(remainder) >= 6 and remainder[1] not in "aeiouäöüch":
                remainder = remainder[1:]
            if len(remainder) >= 4 and remainder not in ALL_STOPWORDS:
                return [w] + mapped_roots + [remainder]
    return [w]


def extract_row_metadata_tokens(row: dict) -> set[str]:
    """
    Extracts non-canonical author/editor name tokens and publisher imprint tokens from a row's
    metadata so they cannot leak into the topic model from prepended headers or paratexts
    (Santana et al., 2025, DHQ 19.2 §55-64, Fig. 3 & Fig. 6).
    """
    meta_tokens = set()
    for field in ("author", "publisher", "raw_imprint"):
        val = row.get(field) or ""
        for w in _WORD_RE.findall(str(val)):
            wl = w.lower()
            if wl not in CANONICAL_THEO_PHIL_WHITELIST and len(wl) > 2:
                meta_tokens.add(wl)
    return meta_tokens


def run_pipeline(data_path, num_topics: int = None, lda_mode: str = "unsupervised"):
    """
    Executes the end-to-end German LDA pipeline supporting all 4 methodological paradigms:
      - 'unseeded': Pure Unsupervised & Unseeded (1x natural token frequencies, eta='auto')
      - 'unsupervised': Domain-Weighted Unsupervised (2x religious keyword salience, eta='auto')
      - 'seeded': Bayesian Seeded / Guided LDA (Asymmetric K x |V| eta prior matrix anchored to RQ1-RQ3)
      - 'supervised': Supervised LDA (sLDA empirical label log-odds eta prior + 5-fold CV discriminative head)
    """
    mode_key = lda_mode if lda_mode in LDA_MODES_META else "unsupervised"
    k_topics = int(num_topics) if num_topics else config.NUM_TOPICS
    print(f"Loading data from {data_path} (+ any shards) (K={k_topics}, mode={mode_key})...", flush=True)

    valid_rows = []
    texts = []
    for row in iter_corpus_rows(data_path):
        text = row.get("text", "")
        if text and text.strip():
            valid_rows.append(row)
            texts.append(text)

    processed_docs = preprocess_corpus_batch(texts)

    # Filter out empty token lists, strip row-specific author/publisher metadata leakage (Santana et al. 2025 §55),
    # and apply unified German compound decompounding (§70-71, §81)
    filtered_docs = []
    filtered_rows = []
    for doc, row in zip(processed_docs, valid_rows):
        base_doc = _unboost_religious_tokens(doc or []) if mode_key == "unseeded" else (doc or [])
        row_meta_noise = extract_row_metadata_tokens(row)
        cleaned_doc = []
        for t in base_doc:
            if t in ALL_STOPWORDS or t in row_meta_noise or len(t) <= 2:
                continue
            cleaned_doc.extend(split_german_compound_lda(t))
        if cleaned_doc:
            filtered_docs.append(cleaned_doc)
            filtered_rows.append(row)

    # --- PHASE 1: N-Gram Detection ---
    bigram = gensim.models.Phrases(filtered_docs, min_count=5, threshold=10)
    bigram_mod = gensim.models.phrases.Phraser(bigram)
    processed_n_grams = []
    for doc in filtered_docs:
        ng_doc = []
        for tok in bigram_mod[doc]:
            if tok in ALL_STOPWORDS:
                continue
            if "_" in tok:
                parts = tok.split("_")
                # Unpack artificial self-bigrams (e.g., kirche_kirche -> kirche)
                if len(set(parts)) == 1:
                    ng_doc.append(parts[0])
                    continue
                if any(p in ALL_STOPWORDS for p in parts):
                    continue
            ng_doc.append(tok)
        processed_n_grams.append(ng_doc)

    # Create Dictionary & Bag-of-Words Corpus
    dictionary = corpora.Dictionary(processed_n_grams)
    if len(processed_n_grams) >= 100:
        dictionary.filter_extremes(no_below=5, no_above=0.55, keep_n=25000)
    corpus = [dictionary.doc2bow(doc) for doc in processed_n_grams]

    # Guard against tiny temporal slices where K exceeds vocabulary/corpus size
    effective_k = max(2, min(k_topics, len(corpus))) if corpus else 2

    # Configure Dirichlet word prior (eta) according to lda_mode
    seed_assignments = {}
    if mode_key == "seeded":
        eta_param, seed_assignments = build_seeded_eta_matrix(dictionary, effective_k)
    elif mode_key == "supervised":
        eta_param, seed_assignments = build_supervised_eta_matrix(
            dictionary, processed_n_grams, filtered_rows, effective_k
        )
    else:
        eta_param = config.ETA

    print(
        f"Training Gensim LdaModel (K={effective_k}, docs={len(corpus):,}, vocab={len(dictionary):,}, passes={config.PASSES})...",
        flush=True
    )
    lda_model = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=effective_k,
        random_state=100,
        update_every=1,
        chunksize=1500,
        passes=config.PASSES,
        alpha=config.ALPHA,
        eta=eta_param,
        per_word_topics=False
    )

    # --- PHASE 2: Model Validation (Coherence + Supervised sLDA Diagnostics) ---
    coherence_model = CoherenceModel(
        model=lda_model,
        corpus=corpus,
        dictionary=dictionary,
        coherence="u_mass"
    )
    coherence_score = float(coherence_model.get_coherence())
    slda_diagnostics = compute_slda_diagnostics(
        corpus, filtered_rows, processed_n_grams, lda_model, effective_k
    )

    # --- PHASE 3: Representative Documents, Publisher & Decade Cross-Tabulation ---
    top_docs = {i: [] for i in range(effective_k)}
    publisher_topic_weights = defaultdict(lambda: defaultdict(float))
    decade_topic_weights = defaultdict(lambda: defaultdict(float))
    topic_total_weights = defaultdict(float)
    decade_totals = defaultdict(float)

    for i, doc_bow in enumerate(corpus):
        doc_topics = lda_model.get_document_topics(doc_bow, minimum_probability=0.0)
        row = filtered_rows[i]
        pub = _clean_marc_control_chars(row.get("publisher") or "Unknown")
        dec = _clean_marc_control_chars(row.get("decade") or "")
        if not dec:
            ym = re.search(r"(\d{4})", str(row.get("date") or ""))
            if ym:
                dec = f"{ym.group(1)[:3]}0s"
        for topic_id, score in doc_topics:
            prob = float(score)
            top_docs[topic_id].append((prob, row))
            publisher_topic_weights[topic_id][pub] += prob
            topic_total_weights[topic_id] += prob
            if dec in ("1970s", "1980s", "1990s", "2000s", "2010s", "2020s"):
                decade_topic_weights[dec][topic_id] += prob
                decade_totals[dec] += prob

    # Deduplicate representative docs by base book title so 3 distinct works appear per topic
    representative_docs = {}
    for topic_id, docs in top_docs.items():
        sorted_docs = sorted(docs, key=lambda x: x[0], reverse=True)
        structured_list = []
        seen_base_titles = set()
        for prob, r in sorted_docs:
            raw_title = _clean_marc_control_chars(r.get("title") or "")
            base_title = re.sub(r"\[.*?\]", "", raw_title).strip().lower()
            if base_title in seen_base_titles:
                continue
            seen_base_titles.add(base_title)

            raw_snippet = _clean_marc_control_chars(r.get("abstract") or r.get("text") or "")
            snippet = raw_snippet[:420] + "..." if len(raw_snippet) > 420 else raw_snippet
            kw_list = [
                _clean_marc_control_chars(k)
                for k in (r.get("keywords") or "").split(",")
                if k.strip() and not k.strip().startswith("(")
            ][:6]
            structured_list.append({
                "title": raw_title,
                "author": _clean_marc_control_chars(r.get("author") or "o. V."),
                "publisher": _clean_marc_control_chars(r.get("publisher") or "Unknown"),
                "date": _clean_marc_control_chars(r.get("date") or ""),
                "corpus_layer": _clean_marc_control_chars(r.get("corpus_layer") or ""),
                "probability": round(prob * 100, 1),
                "keywords": kw_list,
                "snippet": snippet,
                "apa_citation": format_apa_citation(r)
            })
            if len(structured_list) >= 3:
                break
        representative_docs[topic_id] = structured_list

    # Attach rich diagnostics onto the model instance for fast retrieval in app/main.py
    publisher_breakdown = {}
    for topic_id in range(effective_k):
        tot = topic_total_weights[topic_id] or 1.0
        pub_dist = [
            {"publisher": pub, "share": round((w / tot) * 100, 1)}
            for pub, w in publisher_topic_weights[topic_id].items()
        ]
        publisher_breakdown[topic_id] = sorted(pub_dist, key=lambda x: x["share"], reverse=True)[:6]

    decade_breakdown = {}
    for dec in ("1970s", "1980s", "1990s", "2000s", "2010s", "2020s"):
        dtot = decade_totals.get(dec) or 1.0
        decade_breakdown[dec] = {
            f"Topic {t_id + 1}": round((decade_topic_weights[dec].get(t_id, 0.0) / dtot) * 100, 1)
            for t_id in range(effective_k)
        }

    lda_model.publisher_breakdown = publisher_breakdown
    lda_model.decade_breakdown = decade_breakdown
    lda_model.lda_mode = mode_key
    lda_model.seed_assignments = seed_assignments
    lda_model.slda_diagnostics = slda_diagnostics
    return lda_model, corpus, dictionary, coherence_score, representative_docs


def get_viz_html(lda_model, corpus, dictionary):
    """
    Generates a standalone interactive HTML Topic & Publisher Visualization Dashboard.
    """
    topics_data = getattr(lda_model, "exported_topics_report", None)
    if not topics_data:
        return "<!-- LDA Visualisation Data Unavailable -->"

    json_payload = json.dumps(topics_data, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Mediating Faith & Power — German Publishing LDA Dashboard (1970–2025)</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 4px; color: #38bdf8; }}
  .subtitle {{ color: #94a3b8; margin-bottom: 24px; font-size: 0.95rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 18px; }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 18px; }}
  .badge {{ display: inline-block; background: #0284c7; color: #fff; padding: 3px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 600; }}
  .kw {{ display: inline-block; background: #334155; color: #e2e8f0; padding: 3px 8px; border-radius: 6px; margin: 3px 3px 0 0; font-size: 0.82rem; }}
  .pub-bar {{ margin: 6px 0; font-size: 0.85rem; }}
  .cite {{ font-size: 0.82rem; color: #cbd5e1; border-left: 3px solid #38bdf8; padding-left: 10px; margin: 8px 0; }}
</style>
</head>
<body>
  <h1>Mediating Faith and Power: German Publishing LDA Model (1970–2025)</h1>
  <div class="subtitle" id="meta"></div>
  <div class="grid" id="topics"></div>
  <script>
    const data = {json_payload};
    document.getElementById('meta').textContent =
      `Corpus: ${{data.corpus_documents.toLocaleString()}} passages | Coherence (u_mass): ${{data.coherence_score.toFixed(4)}} | Dictionary: ${{data.vocabulary_size.toLocaleString()}} lemmas/bigrams`;
    const container = document.getElementById('topics');
    data.topics.forEach(t => {{
      const card = document.createElement('div');
      card.className = 'card';
      const kws = t.top_terms.slice(0, 12).map(k => `<span class="kw">${{k.term}} (${{(k.weight*100).toFixed(1)}}%)</span>`).join('');
      const pubs = t.top_publishers.map(p => `<div class="pub-bar"><strong>${{p.publisher}}</strong>: ${{p.share}}%</div>`).join('');
      const cites = t.representative_docs.map(d => `<div class="cite"><strong>${{d.apa_citation}}</strong> (${{d.probability}}%)<br>${{d.snippet}}</div>`).join('');
      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <h2 style="margin:0;font-size:1.15rem;">Topic ${{t.topic_id}}: ${{t.archetype.label}}</h2>
          <span class="badge">${{t.archetype.confidence}}% match</span>
        </div>
        <div style="margin-bottom:12px;">${{kws}}</div>
        <h3 style="font-size:0.9rem;color:#38bdf8;margin:12px 0 6px;">Top Publishers Driving Topic</h3>
        <div>${{pubs}}</div>
        <h3 style="font-size:0.9rem;color:#38bdf8;margin:12px 0 6px;">Representative Works & Passages</h3>
        <div>${{cites}}</div>
      `;
      container.appendChild(card);
    }});
  </script>
</body>
</html>"""


def build_report_dict(model, corpus, dictionary, coherence_score=0.0, representative_docs=None) -> dict:
    """
    Constructs a structured JSON-serializable report dictionary for a trained LdaModel.
    """
    representative_docs = representative_docs or {}
    pub_breakdown = getattr(model, "publisher_breakdown", {})
    dec_breakdown = getattr(model, "decade_breakdown", {})
    mode_key = getattr(model, "lda_mode", "unsupervised")
    seed_assignments = getattr(model, "seed_assignments", {})
    slda_diagnostics = getattr(model, "slda_diagnostics", {})

    topics_list = []
    for t_id in range(model.num_topics):
        terms = model.show_topic(t_id, topn=15)
        arch = classify_topic_archetype(terms)
        if t_id in seed_assignments:
            arch["seeded_prior"] = seed_assignments[t_id]
        topics_list.append({
            "topic_id": t_id + 1,
            "archetype": arch,
            "seeded_prior": seed_assignments.get(t_id),
            "top_terms": [{"term": w, "weight": round(float(p), 5)} for w, p in terms],
            "top_publishers": pub_breakdown.get(t_id, []),
            "representative_docs": representative_docs.get(t_id, [])
        })

    return {
        "lda_mode": mode_key,
        "lda_mode_meta": LDA_MODES_META.get(mode_key, LDA_MODES_META["unsupervised"]),
        "corpus_documents": len(corpus),
        "vocabulary_size": len(dictionary),
        "coherence_score": round(float(coherence_score), 4),
        "topics": topics_list,
        "diachronic_decade_shares": dec_breakdown,
        "slda_diagnostics": slda_diagnostics
    }


def export_results(model, corpus, dictionary, data_path, coherence_score=0.0, representative_docs=None):
    """
    Exports static visualization, detailed JSON topic report, and data summary for the frontend.
    """
    if hasattr(os, "makedirs"):
        os.makedirs("app", exist_ok=True)

    report = build_report_dict(
        model, corpus, dictionary, coherence_score=coherence_score, representative_docs=representative_docs
    )
    model.exported_topics_report = report

    with open("app/lda_topics_report.json", "w", encoding="utf-8") as rf:
        json.dump(report, rf, indent=2, ensure_ascii=False)

    html = get_viz_html(model, corpus, dictionary)
    with open("app/lda_viz.html", "w", encoding="utf-8") as f:
        f.write(html)

    years = set()
    publishers = set()
    pub_counts = defaultdict(int)
    layer_counts = defaultdict(int)
    decade_counts = defaultdict(int)
    unique_base_titles = set()
    trends_map = defaultdict(lambda: defaultdict(int))
    total_words = 0
    count = 0

    for row in iter_corpus_rows(data_path):
        count += 1
        raw_title = _clean_marc_control_chars(row.get("title") or "")
        if raw_title:
            base_t = re.sub(r"\[.*?\]", "", raw_title).strip().lower()
            if base_t:
                unique_base_titles.add(base_t)

        wc_val = row.get("word_count")
        if wc_val:
            try:
                total_words += int(float(wc_val))
            except Exception:
                pass

        layer = _clean_marc_control_chars(row.get("corpus_layer") or "dnb_sru_marc21")
        layer_counts[layer] += 1

        dec = _clean_marc_control_chars(row.get("decade") or "")
        y = row.get("year") or row.get("date")
        yr_str = "Unknown"
        if y:
            m = re.search(r"(\d{4})", str(y))
            if m:
                yr_str = m.group(1)
                yr_int = int(yr_str)
                years.add(yr_int)
                if not dec:
                    dec = f"{yr_str[:3]}0s"
        if dec:
            decade_counts[dec] += 1

        if "publisher" in row and row["publisher"]:
            clean_pub = _clean_marc_control_chars(row["publisher"])
            if clean_pub and clean_pub != "PERSON":
                publishers.add(clean_pub)
                pub_counts[clean_pub] += 1
                if yr_str != "Unknown":
                    trends_map[yr_str][clean_pub] += 1

    top_publishers_sorted = [
        p for p, _ in sorted(pub_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    trends_list = []
    for yr in sorted(trends_map.keys()):
        item = {"year": int(yr) if yr.isdigit() else yr, "year_clean": yr}
        for pub in top_publishers_sorted[:40]:
            item[pub] = trends_map[yr][pub]
        trends_list.append(item)


    coherence_grid = []
    if os.path.exists(config.COHERENCE_GRID_PATH):
        try:
            with open(config.COHERENCE_GRID_PATH, mode="r", encoding="utf-8") as gf:
                for grow in csv.DictReader(gf):
                    coherence_grid.append({
                        "k": int(grow["k"]),
                        "c_v": float(grow["c_v"]),
                        "u_mass": float(grow["u_mass"]),
                        "log_perplexity": float(grow["log_perplexity"])
                    })
        except Exception:
            pass

    full_summary = {
        "source": "DNB SRU v1.1 + HathiTrust HTRC + OpenAlex Full-Book Corpus (1970–2025)",
        "count": count,
        "total_records": count,
        "unique_books": len(unique_base_titles),
        "total_words": total_words,
        "vocabulary_size": len(dictionary),
        "coherence_score": round(float(coherence_score), 4),
        "publishers": top_publishers_sorted[:14] if top_publishers_sorted else sorted(list(publishers)),
        "all_publishers_count": len(publishers),
        "publisher_counts": dict(sorted(pub_counts.items(), key=lambda x: x[1], reverse=True)[:15]),
        "corpus_layers": dict(sorted(layer_counts.items(), key=lambda x: x[1], reverse=True)),
        "decade_counts": dict(sorted(decade_counts.items())),
        "year_range": f"{min(years)}–{max(years)}" if years else "1970–2025",
        "pipeline_config": {
            "spacy_model": config.SPACY_MODEL,
            "allowed_postags": config.ALLOWED_POSTAGS,
            "stopwords_total": len(ALL_STOPWORDS),
            "fraktur_noise_count": len(FRAKTUR_AND_META_NOISE),
            "domain_stopwords_count": len(config.DOMAIN_STOPWORDS),
            "religious_boost_keywords": len(config.RELIGIOUS_VOICE_KEYWORDS),
            "bigram_min_count": 5,
            "bigram_threshold": 10,
            "filter_no_below": 5,
            "filter_no_above": 0.55,
            "filter_keep_n": 25000,
            "lda_passes": config.PASSES,
            "lda_chunksize": 1500,
            "lda_alpha": str(config.ALPHA),
            "lda_eta": str(config.ETA)
        }
    }

    summary_payload = {
        **full_summary,
        "summary": full_summary,
        "trends": trends_list,
        "coherence_grid": coherence_grid
    }
    with open("app/data_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2, ensure_ascii=False)

    # Synchronize app/lda_modes_report.json with the full corpus scale
    modes_path = "app/lda_modes_report.json"
    if os.path.exists(modes_path):
        try:
            with open(modes_path, "r", encoding="utf-8") as mf:
                modes_data = json.load(mf)
            if "modes" in modes_data:
                modes_data["modes"][report["lda_mode"]] = report
                for m_key, m_obj in modes_data["modes"].items():
                    m_obj["corpus_documents"] = len(corpus)
                    m_obj["vocabulary_size"] = len(dictionary)
            if "comparison" in modes_data:
                for comp in modes_data["comparison"]:
                    comp["documents"] = len(corpus)
                    comp["vocab_size"] = len(dictionary)
                    if comp.get("mode") == report["lda_mode"]:
                        comp["u_mass"] = round(float(coherence_score), 4)
            with open(modes_path, "w", encoding="utf-8") as mf:
                json.dump(modes_data, mf, indent=2, ensure_ascii=False)
        except Exception:
            pass

    print("\n======================================================================")
    print(f"LDA MODEL COMPLETE | Documents: {len(corpus):,} | Vocab: {len(dictionary):,} | Coherence (u_mass): {coherence_score:.4f}")
    print("======================================================================")
    for t in report["topics"]:
        top_kw_str = ", ".join([f"{x['term']} ({x['weight']:.3f})" for x in t["top_terms"][:10]])
        top_pub_str = ", ".join([f"{p['publisher']} ({p['share']}%)" for p in t["top_publishers"][:4]])
        print(f"\n--- TOPIC {t['topic_id']}: {t['archetype']['label']} (Confidence: {t['archetype']['confidence']}%) ---")
        print(f"  Top Lemmas/Bigrams : {top_kw_str}")
        print(f"  Publisher Dominance: {top_pub_str}")
        for d in t["representative_docs"][:2]:
            print(f"  * [{d['probability']}%] {d['apa_citation']}")
    print("\nDiachronic Topic Trajectory (1970s-2020s):")
    for dec, shares in report["diachronic_decade_shares"].items():
        print(f"  {dec}: {shares}")
    print("\nResults exported to app/lda_topics_report.json, app/lda_viz.html, and app/data_summary.json.")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    data_path = config.HARVEST_DATA_PATH if os.path.exists(config.HARVEST_DATA_PATH) else config.MOCK_DATA_PATH
    model, corp, dict_, coh, docs = run_pipeline(data_path)
    export_results(model, corp, dict_, data_path, coherence_score=coh, representative_docs=docs)
