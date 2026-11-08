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
    "ebeling", "gen", "abb", "tab", "hrsg_von", "verf", "bearb", "übers",
    "open", "access", "open_access", "creative", "commons", "creative_commons", "creativecommons",
    "creativecommon", "creativecommons_org", "creativecommon_org", "org_licenses", "license",
    "licenses", "lizenz", "org", "com", "net", "edu", "gov", "de", "html", "htm", "pdf", "epub",
    "xml", "url", "urn", "nbn", "hdl", "handle", "orcid", "ror", "heft", "akte", "akten",
    "handschrift", "handschriften", "jahrgang", "signatur", "bestand", "wiesbaden", "main",
    "frankfurt_main", "ten", "isch", "ische", "ischen", "ischer", "isches", "ung", "ungen",
    "keit", "keiten", "heit", "heiten", "lich", "liche", "lichen", "licher", "liches", "ver", "ent", "zer",
    "rrb", "lrb", "lcub", "rcub", "lsb", "rsb", "sachgruppe", "sachgruppen",
    "vii", "viii", "xii", "xiii", "xiv", "xvi", "xvii", "xviii", "xix",
    "science", "culture", "christianity", "judaism", "bible", "history", "philosophy", "society",
    "sociology", "knowledge", "self", "law", "john", "europe", "contribution", "american", "germany",
    "ssoar", "veröffentlichungsversion_version", "ssoar_nutzungsbedingung", "nutzungsbedingung",
    "veröffentlichungsversion", "citation", "dat", "text_deposit", "persönlich_kommerziell",
    "übertragbar_persönlich", "gebrauch_kopie", "dokument", "sektion", "media"
}

# Canonical sacred/theological terms preserved during entity filtering
# All personal names (PER), philosopher/author surnames, and geographic locations (LOC) are stripped
# per Santana et al. (2025, DHQ 19.2 §56-64) and Jiménez-Badillo et al. (2020)
CANONICAL_THEO_PHIL_WHITELIST = {
    "jesus", "christus", "jesu", "gott", "bibel", "kirche", "christentum",
    "judentum", "islam", "buddhismus", "hinduismus", "evangelium", "koran", "torah"
}

# Non-canonical geographic locations (LOC) and person/author/philosopher names (PER) filtered per
# Santana et al. (2025, DHQ 19.2 §56-64, Figs. 4-6) to prevent author, biography, and homonym conflation
NON_CANONICAL_LOC_AND_PER_NOISE = {
    # Author, philosopher, theologian & historical person names (PER) including Steiner, Grandt, etc.
    "steiner", "rudolf", "rudolf_steiner", "grandt", "anthroposophe_grandt", "archiv_grandt",
    "edelmann", "dietlind", "charles", "taylor", "charles_taylor", "kippenberg", "hans_kippenberg",
    "jacques", "hans_joachim", "udo", "drewermann", "eugen", "drewermann_eugen", "annebelle",
    "pithan", "vielfalt_pithan", "mauthner", "mauthner_fritz", "weizsäcker", "freud", "voltaire",
    "holbach", "rousseau", "wittgenstein", "sartre", "nietzsche", "nietzsch", "luther", "kant",
    "hegel", "habermas", "weber", "marx", "augustinus", "aquino", "schleiermacher", "barth",
    "rahner", "bonhoeffer", "bultmann", "moltmann", "pannenberg", "jüngel", "küng", "ratzinger",
    "kasper", "tillich", "troeltsch", "harnack", "kierkegaard", "heidegger", "husserl", "gadamer",
    "adorno", "horkheimer", "benjamin", "blumenberg", "sloterdijk", "spinoza", "leibniz", "fichte",
    "schelling", "feuerbach", "foucault", "derrida", "ricoeur", "levinas", "buber", "rosenzweig",
    "scholem", "eckhart", "origenes", "calvin", "zwingli", "melanchthon", "lessing", "paulus",
    "moses", "abraham", "david", "jesaja", "hiob", "jeremia", "lukas", "matthäus", "markus",
    "johannes", "mohammed", "januar", "februar", "märz", "april", "mai", "juni", "juli", "august",
    "september", "oktober", "november", "dezember", "daf", "dafi", "daz", "tiber", "bjp", "kmu",
    "item", "abbildung", "befragter", "indien", "indisch", "chinesisch", "türkisch",
    # German federal states, historical regions, European countries & diocesan/university cities
    "bayern", "bayerisch", "württemberg", "baden", "westfalen", "westfälisch", "rheinland",
    "rheinisch", "sachsen", "sächsisch", "thüringen", "hessen", "hessisch", "niedersachsen",
    "brandenburg", "preußen", "preußisch", "pfalz", "franken", "schwaben", "schlesien", "pommern",
    "österreich", "österreichisch", "schweiz", "schweizerisch", "deutschland", "italien",
    "frankreich", "england", "großbritannien", "polen", "spanien", "niederlande", "belgien",
    "rom", "paris", "basel", "bern", "genf", "luzern", "konstanz", "augsburg", "regensburg",
    "bamberg", "würzburg", "passau", "eichstätt", "rottenburg", "hildesheim", "osnabrück",
    "paderborn", "fulda", "trier", "speyer", "limburg", "erfurt", "magdeburg", "greifswald",
    "rostock", "kiel", "hamburg", "bremen", "hannover", "braunschweig", "bielefeld", "bochum",
    "dortmund", "duisburg", "essen", "kassel", "marburg", "gießen", "mannheim", "karlsruhe",
    "ulm", "erlangen", "nürnberg", "salzburg", "innsbruck", "graz", "linz", "aachen", "halle",
    "jena", "oldenburg", "detmold", "koblenz", "lübeck", "flensburg", "chemnitz", "dresden",
    "potsdam", "cottbus", "neubrandenburg", "schwerin", "stralsund", "wittenberg", "weimar",
    "gotha", "eisenach", "altenburg", "meiningen", "coburg", "bayreuth", "ansbach", "ingolstadt",
    "landshut", "freising", "kempten", "ravensburg", "reutlingen", "esslingen", "heilbronn",
    "pforzheim", "offenburg", "lörrach", "baden_baden", "worms", "kaiserslautern", "saarbrücken",
    "siegen", "hagen", "wuppertal", "solingen", "remscheid", "krefeld", "mönchengladbach",
    "neuss", "leverkusen", "gelsenkirchen", "recklinghausen", "hamm", "herne", "mülheim",
    "oberhausen", "bottrop", "gütersloh", "minden", "herford", "lippstadt", "soest", "arnsberg",
    "meschede", "brilon", "kleve", "wesel", "bocholt", "borken", "coesfeld", "steinfurt",
    "warendorf", "celle", "lüneburg", "stade", "verden", "aurich", "emden", "leer", "wilhelmshaven",
    "delmenhorst", "hameln", "göttingen", "goslar", "wolfenbüttel", "salzgitter", "peine",
    "gifhorn", "wolfsburg", "helmstedt", "northeim", "holzminden", "einbeck", "hann_münden",
    # Frequent German given names causing homonym conflation (Santana et al., 2025 §56: e.g., 'Maria')
    "maria", "anna", "elisabeth", "ursula", "monika", "brigitte", "renate", "helga", "ingrid",
    "gisela", "christine", "christa", "barbara", "sabine", "petra", "claudia", "susanne", "katrin",
    "julia", "katharina", "margarete", "hildegard", "dorothea", "angelika", "gabriele", "heidrun",
    "irmgard", "gudrun", "mechthild", "sigrid", "waltraud", "anne", "birgit", "cornelia", "dagmar",
    "edith", "elke", "eva", "gertrud", "hanna", "hannelore", "hedwig", "heike", "helene", "ilse",
    "ines", "irene", "johanna", "karin", "kerstin", "kristina", "lotte", "luise", "magdalena",
    "margit", "margot", "marianne", "marlies", "martha", "martina", "nadine", "nicole", "regina",
    "rita", "rosemarie", "ruth", "silke", "simone", "sonja", "stephanie", "sylvia", "theresia",
    "ulrike", "ute", "vera", "veronika", "yvonne",
    # Frequent modern German contributor/editor surnames in DNB/GBV headers
    "müller", "schmidt", "schneider", "meyer", "wagner", "becker", "schulz", "hoffmann", "schäfer",
    "koch", "bauer", "richter", "klein", "schröder", "neumann", "zimmermann", "braun", "krüger",
    "hofmann", "hartmann", "lange", "schmitt", "schmitz", "krause", "meier", "lehmann", "maier",
    "köhler", "herrmann", "mayer", "huber", "fuchs", "peters", "scholz", "möller", "hahn",
    "schubert", "vogel", "keller", "günther", "berger", "winkler", "roth", "lorenz", "baumann",
    "franke", "albrecht", "schuster", "böhm", "kraus", "schumacher", "krämer", "vogt", "jäger",
    "sommer", "seidel", "brandt", "haas", "schreiber", "schulte", "dietrich", "ziegler", "kuhn",
    "kühn", "pohl", "busch", "bergmann", "voigt", "sauer", "arnold", "wolff", "pfeiffer"
} - CANONICAL_THEO_PHIL_WHITELIST

_BASE_STOPWORDS = set(nlp.Defaults.stop_words) if nlp is not None else GERMAN_CORE_STOPWORDS
ALL_STOPWORDS = (
    _BASE_STOPWORDS
    .union(set(config.DOMAIN_STOPWORDS))
    .union(FRAKTUR_AND_META_NOISE)
    .union(NON_CANONICAL_LOC_AND_PER_NOISE)
) - CANONICAL_THEO_PHIL_WHITELIST

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


def build_seeded_eta_matrix(
    dictionary,
    num_topics: int,
    seed_boost: float = 15.0,
    base_eta: float = 0.05,
    custom_seed_lexicons: dict = None,
):
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
    active_lexicons = {}
    for arch in archetype_names:
        if custom_seed_lexicons and arch in custom_seed_lexicons and custom_seed_lexicons[arch]:
            active_lexicons[arch] = {str(w).strip().lower() for w in custom_seed_lexicons[arch] if str(w).strip()}
        else:
            active_lexicons[arch] = set(config.ARCHETYPE_LEXICONS[arch])

    seed_assignments = {}

    for t_id in range(num_topics):
        target_arch = archetype_names[t_id % 3]
        seed_assignments[t_id] = target_arch
        lex_set = active_lexicons[target_arch]
        other_lex = set().union(*[
            s for a, s in active_lexicons.items() if a != target_arch
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


def ensure_parquet_shards_from_github_release(
    parquet_dir: str = "data/parquet",
    release_tag: str = "v12.0-dnb-parquet-shards",
    repo: str = "metachasm-beep/Deutsche-Verlage-LDA",
) -> list[str]:
    """
    Ensures local Zstd-19 Parquet shards (`data/parquet/dnb_corpus_part*.parquet`) exist,
    downloading missing shards from GitHub Release Assets (`https://github.com/{repo}/releases/download/{release_tag}/`)
    when running on a fresh machine or cloud worker.
    """
    existing = get_parquet_shard_paths(parquet_dir)
    if existing:
        return existing

    import requests

    os.makedirs(parquet_dir, exist_ok=True)
    base_dl = f"https://github.com/{repo}/releases/download/{release_tag}"
    manifest_path = os.path.join(parquet_dir, "parquet_manifest.json")
    if not os.path.exists(manifest_path):
        try:
            r = requests.get(f"{base_dl}/parquet_manifest.json", timeout=25, verify=False)
            if r.status_code == 200:
                with open(manifest_path, "wb") as mf:
                    mf.write(r.content)
        except Exception:
            return []

    if not os.path.exists(manifest_path):
        return []

    try:
        with open(manifest_path, "r", encoding="utf-8") as mf:
            manifest = json.load(mf)
        for s_info in manifest.get("shards", []):
            sname = s_info["shard"]
            target_p = os.path.join(parquet_dir, sname)
            if not os.path.exists(target_p):
                print(f"  -> Hydrating Zstd Parquet shard `{sname}` from GitHub Release `{release_tag}`...", flush=True)
                with requests.get(f"{base_dl}/{sname}", stream=True, timeout=180, verify=False) as sr:
                    if sr.status_code == 200:
                        with open(target_p, "wb") as out_f:
                            for chunk in sr.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    out_f.write(chunk)
    except Exception:
        pass
    return get_parquet_shard_paths(parquet_dir)


def get_parquet_shard_paths(parquet_dir: str = "data/parquet") -> list[str]:
    """
    Returns sorted paths to all Zstd-compressed Apache Parquet corpus shards in `parquet_dir`.
    """
    import glob
    if not os.path.exists(parquet_dir):
        return []
    if os.path.isfile(parquet_dir) and parquet_dir.endswith(".parquet"):
        return [parquet_dir]
    pattern = os.path.join(parquet_dir, "dnb_corpus_part*.parquet")
    files = sorted(
        glob.glob(pattern),
        key=lambda x: int(re.search(r"part(\d+)", x).group(1)) if re.search(r"part(\d+)", x) else 9999,
    )
    return files


def iter_parquet_rows(parquet_dir: str = "data/parquet", batch_size: int = 8192):
    """
    Streams rows from Zstd-compressed Apache Parquet shards (`data/parquet/dnb_corpus_part*.parquet`)
    in constant low RAM using `pyarrow.parquet.ParquetFile.iter_batches`, transparently reconstructing
    deduplicated `abstract` and header fields.
    """
    import pyarrow.parquet as pq
    shard_paths = get_parquet_shard_paths(parquet_dir)
    for p in shard_paths:
        pf = pq.ParquetFile(p)
        for record_batch in pf.iter_batches(batch_size=batch_size):
            col_names = record_batch.schema.names
            cols = {name: record_batch.column(i).to_pylist() for i, name in enumerate(col_names)}
            n_rows = record_batch.num_rows
            for idx in range(n_rows):
                row = {name: (cols[name][idx] if cols[name][idx] is not None else "") for name in col_names}
                t_val = str(row.get("text") or "")
                title_val = str(row.get("title") or "")
                if title_val and title_val[:40] not in t_val:
                    row["text"] = f"{title_val}. {t_val}".strip() if t_val else title_val
                if not row.get("abstract") and row.get("text"):
                    row["abstract"] = str(row["text"])[:240]
                yield row


def save_corpus_to_zstd_parquet(
    data_source="data/dnb_metadata.csv",
    parquet_dir: str = "data/parquet",
    rows_per_shard: int = 85000,
    compression_level: int = 19,
) -> dict:
    """
    Compresses the DNB corpus into Zstandard (level 19, dictionary-encoded, prefix-deduplicated)
    Apache Parquet shards (`data/parquet/dnb_corpus_part001.parquet`, ...) and writes
    `data/parquet/parquet_manifest.json` with SHA-256 checksums for GitHub Release Assets.
    """
    import glob
    import pyarrow as pa
    import pyarrow.parquet as pq

    os.makedirs(parquet_dir, exist_ok=True)
    for old_f in glob.glob(os.path.join(parquet_dir, "dnb_corpus_part*.parquet")):
        try:
            os.remove(old_f)
        except Exception:
            pass

    schema_fields = [
        ("title", pa.string()),
        ("author", pa.string()),
        ("date", pa.string()),
        ("decade", pa.string()),
        ("publisher", pa.string()),
        ("corpus_layer", pa.string()),
        ("source_file", pa.string()),
        ("chunk_index", pa.int32()),
        ("total_chunks", pa.int32()),
        ("word_count", pa.int32()),
        ("abstract", pa.string()),
        ("text", pa.string()),
    ]
    pa_schema = pa.schema(schema_fields)

    row_iter = (
        iter_corpus_rows(data_source, include_shards=True, prefer_parquet=False)
        if isinstance(data_source, str)
        else iter(data_source)
    )

    shard_idx = 0
    total_rows = 0
    total_words = 0
    total_parquet_bytes = 0
    shard_summaries = []
    batch_buf = []

    def _flush_shard(buf, s_idx):
        nonlocal total_parquet_bytes
        shard_name = f"dnb_corpus_part{s_idx:03d}.parquet"
        shard_path = os.path.join(parquet_dir, shard_name)
        # Sort by (corpus_layer, publisher, author) to maximize Zstd dictionary & run-length window compression
        buf.sort(key=lambda r: (str(r.get("corpus_layer") or ""), str(r.get("publisher") or ""), str(r.get("author") or "")))
        arrays = {}
        for col_name, col_type in schema_fields:
            if pa.types.is_integer(col_type):
                vals = []
                for r in buf:
                    try:
                        vals.append(int(float(r.get(col_name) or 1)))
                    except Exception:
                        vals.append(1)
                arrays[col_name] = pa.array(vals, type=col_type)
            elif col_name == "abstract":
                # Omit redundant abstract string when it is already contained in `text`
                abs_vals = []
                for r in buf:
                    a_str = str(r.get("abstract") or "")
                    t_str = str(r.get("text") or "")
                    if a_str and a_str[:80] in t_str:
                        abs_vals.append("")
                    else:
                        abs_vals.append(a_str)
                arrays[col_name] = pa.array(abs_vals, type=col_type)
            elif col_name == "text":
                txt_vals = []
                for r in buf:
                    t_str = str(r.get("text") or "")
                    prefix = f"{r.get('title', '')}. {r.get('author', '')}. {r.get('publisher', '')}. "
                    if prefix and t_str.startswith(prefix):
                        t_str = t_str[len(prefix):]
                    txt_vals.append(t_str)
                arrays[col_name] = pa.array(txt_vals, type=col_type)
            else:
                arrays[col_name] = pa.array([str(r.get(col_name) or "") for r in buf], type=col_type)

        table = pa.Table.from_pydict(arrays, schema=pa_schema)
        pq.write_table(
            table,
            shard_path,
            compression="zstd",
            compression_level=compression_level,
            use_dictionary=["author", "date", "decade", "publisher", "corpus_layer", "source_file"],
            write_statistics=True,
        )
        sz_bytes = os.path.getsize(shard_path)
        total_parquet_bytes += sz_bytes
        h = hashlib.sha256()
        with open(shard_path, "rb") as bf:
            for chunk in iter(lambda: bf.read(1024 * 1024), b""):
                h.update(chunk)
        info = {
            "shard": shard_name,
            "path": shard_path.replace("\\", "/"),
            "rows": len(buf),
            "size_bytes": sz_bytes,
            "size_mb": round(sz_bytes / (1024 * 1024), 2),
            "sha256": h.hexdigest(),
        }
        shard_summaries.append(info)
        print(
            f"  -> Wrote Zstd-{compression_level} Parquet shard `{shard_name}`: {len(buf):,} rows ({info['size_mb']:.2f} MB)",
            flush=True,
        )

    for row in row_iter:
        batch_buf.append(row)
        total_rows += 1
        try:
            total_words += int(float(row.get("word_count") or 250))
        except Exception:
            total_words += 250
        if len(batch_buf) >= rows_per_shard:
            shard_idx += 1
            _flush_shard(batch_buf, shard_idx)
            batch_buf = []

    if batch_buf:
        shard_idx += 1
        _flush_shard(batch_buf, shard_idx)
        batch_buf = []

    csv_shards = glob.glob("data/dnb_metadata*.csv")
    raw_csv_bytes = sum(os.path.getsize(p) for p in csv_shards if os.path.exists(p))
    compression_ratio = round(raw_csv_bytes / max(1, total_parquet_bytes), 2) if raw_csv_bytes else 0.0

    manifest = {
        "format": "Apache Parquet 2.6 + Zstandard (level 9) + Dictionary Encoding",
        "total_rows": total_rows,
        "total_words": total_words,
        "total_shards": len(shard_summaries),
        "total_parquet_bytes": total_parquet_bytes,
        "total_parquet_mb": round(total_parquet_bytes / (1024 * 1024), 2),
        "raw_csv_bytes": raw_csv_bytes,
        "raw_csv_mb": round(raw_csv_bytes / (1024 * 1024), 2),
        "compression_ratio_vs_csv": f"{compression_ratio}x",
        "shards": shard_summaries,
    }
    manifest_path = os.path.join(parquet_dir, "parquet_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)

    print(
        f"Zstd Parquet Export Complete: {total_rows:,} passages across {len(shard_summaries)} shards "
        f"({manifest['total_parquet_mb']:.2f} MB vs {manifest['raw_csv_mb']:.2f} MB CSV = {compression_ratio}x compression)!",
        flush=True,
    )
    return manifest


def iter_corpus_rows(data_path: str, include_shards: bool = False, prefer_parquet: bool = True):
    """
    Transparently yields rows from Zstd Apache Parquet shards (`data/parquet/dnb_corpus_part*.parquet`)
    when available and `include_shards=True`, or from `data_path` and accompanying `data/dnb_metadata_part*.csv`
    shards so offline batch jobs can scale to 10,000,000+ DNB documents in constant RAM.
    """
    import glob

    if data_path and (data_path.endswith(".parquet") or os.path.isdir(data_path)):
        yield from iter_parquet_rows(data_path)
        return

    if include_shards and prefer_parquet and os.path.basename(data_path) == "dnb_metadata.csv":
        pq_dir = os.path.join(os.path.dirname(data_path) or "data", "parquet")
        pq_shards = get_parquet_shard_paths(pq_dir)
        if pq_shards:
            try:
                import pyarrow.parquet as _pq  # noqa: F401
                yield from iter_parquet_rows(pq_dir)
                return
            except ImportError:
                pass

    paths = [data_path]
    if include_shards and os.path.basename(data_path) == "dnb_metadata.csv":
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



_ARCHIVAL_BRACKET_RE = re.compile(
    r"\[(?:HTRC|DNB|GBV|OpenAlex|Vollbuch|Abschnitt|Forschungsbuch)[^\]]*\]",
    re.IGNORECASE,
)
_CHUNK_INDEX_RE = re.compile(r"Abschnitt\s+(\d+)\s*/\s*\d+", re.IGNORECASE)


def strip_archival_headers_from_text(text: str, row: dict = None) -> str:
    """
    Strips bracketed provenance tags ([HTRC-Vollbuch-Abschnitt X/Y], [DNB-Inhaltsverzeichnis ...],
    [GBV-K10plus-Volltext ...], [OpenAlex-Vollbuch-OA ...]) and, on continuation passages (chunk_index > 1),
    removes the repeated '{title}. {author}. {publisher}.' prefix from raw text
    (Santana et al., 2025, DHQ 19.2 §55, Fig. 3).
    """
    if not text:
        return ""
    cleaned = _ARCHIVAL_BRACKET_RE.sub(" ", str(text))
    if row:
        title_str = str(row.get("title") or "")
        m_chunk = _CHUNK_INDEX_RE.search(title_str)
        if m_chunk and int(m_chunk.group(1)) > 1:
            base_title = _ARCHIVAL_BRACKET_RE.sub("", title_str).strip()
            if base_title and cleaned.lstrip().startswith(base_title):
                cleaned = cleaned.lstrip()[len(base_title):].lstrip(" .,-;:")
    return re.sub(r"\s+", " ", cleaned).strip()


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


def clean_row_tokens_for_modeling(doc_tokens: list, row: dict, unboost: bool = False) -> list[str]:
    """
    Unified per-document token cleaning pipeline shared across Gensim LDA, Quanteda/STM, and BERTopic
    (Santana et al., 2025, DHQ 19.2 §55-71, §81; Jiménez-Badillo et al., 2020):
      1. Optional unboosting of 2x domain salience weights (for pure unseeded LDA & neural embeddings).
      2. Strips row-specific author/editor and publisher metadata tokens (Rule 1, §55, Fig. 3).
      3. On continuation chunks (Abschnitt K/N where K > 1), strips the leading repeated book-title
         prefix tokens so each book's title words are included only once per work (chunk_index == 1).
      4. Filters out ALL_STOPWORDS (including NON_CANONICAL_LOC_AND_PER_NOISE while preserving
         CANONICAL_THEO_PHIL_WHITELIST; Rule 2 & Rule 4, §56-67, Figs. 4-7).
      5. Applies unified German compound decompounding (Rule 3, §70-71, §81).
    """
    base_doc = _unboost_religious_tokens(doc_tokens or []) if unboost else list(doc_tokens or [])
    if not base_doc:
        return []

    # Rule 1 continuation-chunk title deduplication: strip leading title words on chunk K > 1
    title_str = str((row or {}).get("title") or "")
    m_chunk = _CHUNK_INDEX_RE.search(title_str)
    if m_chunk and int(m_chunk.group(1)) > 1:
        base_title = _ARCHIVAL_BRACKET_RE.sub(" ", title_str)
        title_word_count = len(_WORD_RE.findall(base_title))
        if title_word_count > 0 and len(base_doc) > title_word_count + 5:
            # Account for 2x religious keyword weighting in the leading title slice
            skip_idx = min(len(base_doc) // 3, title_word_count * (1 if unboost else 2))
            base_doc = base_doc[skip_idx:]

    row_meta_noise = extract_row_metadata_tokens(row or {})
    cleaned_doc = []
    for t in base_doc:
        if t in ALL_STOPWORDS or t in row_meta_noise or len(t) <= 2:
            continue
        cleaned_doc.extend(split_german_compound_lda(t))
    return cleaned_doc


def apply_tfidf_low_info_filter(corpus: list, dictionary, min_tfidf: float = 0.015) -> tuple[list, dict]:
    """
    Applies Gensim TfidfModel sublinear/normalized TF-IDF scoring (smartirs='ntc') to identify and
    prune ultra-low-information ubiquity tokens before LdaModel estimation
    (Santana et al., 2025, DHQ 19.2 §72-73).
    """
    if not corpus or len(dictionary) == 0 or gensim is None:
        return corpus, {"tfidf_min_threshold": min_tfidf, "tfidf_pruned_tokens_count": 0}

    tfidf_model = gensim.models.TfidfModel(corpus, id2word=dictionary, smartirs="ntc")
    max_weight_by_id = defaultdict(float)
    for bow in corpus:
        for token_id, weight in tfidf_model[bow]:
            if weight > max_weight_by_id[token_id]:
                max_weight_by_id[token_id] = float(weight)

    low_info_ids = [
        tid for tid in dictionary.keys()
        if max_weight_by_id.get(tid, 0.0) < min_tfidf
        and dictionary[tid] not in RELIGIOUS_KEYWORDS_SET
        and dictionary[tid] not in CANONICAL_THEO_PHIL_WHITELIST
    ]
    pruned_count = len(low_info_ids)
    if low_info_ids and len(dictionary) - pruned_count >= 50:
        dictionary.filter_tokens(bad_ids=low_info_ids)
        dictionary.compactify()

    return corpus, {
        "tfidf_smartirs": "ntc",
        "tfidf_min_threshold": min_tfidf,
        "tfidf_pruned_tokens_count": pruned_count,
        "post_tfidf_vocab_size": len(dictionary)
    }


def run_pipeline(
    data_path,
    num_topics: int = None,
    lda_mode: str = "unsupervised",
    seed_boost: float = 15.0,
    base_eta: float = 0.05,
    custom_seed_lexicons: dict = None,
):
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

    # Filter out empty token lists, strip row-specific author/publisher metadata leakage & continuation-chunk
    # title duplication (Santana et al. 2025 §55), filter non-canonical PER/LOC entities (§56-64),
    # and apply unified German compound decompounding (§70-71, §81)
    filtered_docs = []
    filtered_rows = []
    for doc, row in zip(processed_docs, valid_rows):
        cleaned_doc = clean_row_tokens_for_modeling(doc, row, unboost=(mode_key == "unseeded"))
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

    # Create Dictionary, apply Extremes + Sublinear TF-IDF Low-Information Filter (Santana et al., 2025 §72-73)
    dictionary = corpora.Dictionary(processed_n_grams)
    if len(processed_n_grams) >= 100:
        dictionary.filter_extremes(no_below=5, no_above=0.55, keep_n=25000)
    pre_tfidf_corpus = [dictionary.doc2bow(doc) for doc in processed_n_grams]
    _, tfidf_audit = apply_tfidf_low_info_filter(pre_tfidf_corpus, dictionary, min_tfidf=0.015)
    corpus = [dictionary.doc2bow(doc) for doc in processed_n_grams]

    # Guard against tiny temporal slices where K exceeds vocabulary/corpus size
    effective_k = max(2, min(k_topics, len(corpus))) if corpus else 2

    # Configure Dirichlet word prior (eta) according to lda_mode
    seed_assignments = {}
    if mode_key == "seeded":
        eta_param, seed_assignments = build_seeded_eta_matrix(
            dictionary,
            effective_k,
            seed_boost=seed_boost,
            base_eta=base_eta,
            custom_seed_lexicons=custom_seed_lexicons,
        )
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
    lda_model.tfidf_audit = tfidf_audit
    return lda_model, corpus, dictionary, coherence_score, representative_docs


def run_streaming_online_lda_pipeline(
    data_path: str = "data/parquet",
    num_topics: int = None,
    lda_mode: str = "unsupervised",
    batch_size: int = 15000,
    seed_boost: float = 15.0,
    base_eta: float = 0.05,
    export_to_app: bool = True,
):
    """
    Unlimited-scale Hoffman, Blei & Bach (2010) Online Variational Bayes Streaming LDA (`lda_model.update()`)
    operating over all 126 Zstd-19 Apache Parquet shards (`data/parquet/dnb_corpus_part*.parquet`,
    10,519,923 passages, 778.02M German words) in bounded mini-batches with constant `<1.2 GB` RAM footprint.
    """
    import gc
    import random
    import pyarrow.parquet as pq

    mode_key = lda_mode if lda_mode in LDA_MODES_META else "unsupervised"
    k_topics = int(num_topics) if num_topics else config.NUM_TOPICS
    shard_paths = get_parquet_shard_paths(data_path) if os.path.isdir(data_path) else []

    print(
        f"[Online Streaming LDA] Initializing 126-shard stream over `{data_path}` "
        f"({len(shard_paths)} Zstd-19 Parquet shards, K={k_topics}, mode={mode_key}, batch_size={batch_size:,})...",
        flush=True,
    )

    try:
        from scripts.update_comprehensive_publishers import canonicalize_publisher as _canon_pub
    except Exception:
        _canon_pub = lambda p: (_clean_marc_control_chars(p or "Unknown"), "")

    # 1. Stream all 126 Zstd-19 Parquet shards (10,519,923 passages) in constant RAM:
    #    - Shards 1..6 (461,782 core passages): balanced multi-layer sampling with 100% _TOKEN_CACHE hit reconstruction
    #    - Shards 7..126 (10,058,141 OpenData + hydrated passages): incorporate newly hydrated /34 OA full-text books, /04/text TOCs, and /blurb/ blurbs
    valid_rows = []
    texts = []
    total_streamed_docs = 0
    hydrated_layers = {
        "dnb_oa_fulltext_pdf_epub",
        "dnb_toc_ocr_04",
        "dnb_publisher_blurb",
        "dnb_oa_fullbook",
        "dnb_toc_pdf_fulltext",
        "dnblab_dtf_incopyright",
    }
    domain_lex = RELIGIOUS_KEYWORDS_SET | CANONICAL_THEO_PHIL_WHITELIST
    hydrated_added = 0

    if shard_paths:
        for s_idx, sp in enumerate(shard_paths, start=1):
            tbl = pq.read_table(
                sp,
                columns=["title", "author", "date", "decade", "publisher", "corpus_layer", "text", "abstract", "word_count"],
                memory_map=False,
            )
            n_rows = tbl.num_rows
            total_streamed_docs += n_rows
            layers = tbl.column("corpus_layer").to_pylist()
            wcs = tbl.column("word_count").to_pylist()
            titles = tbl.column("title").to_pylist()
            authors = tbl.column("author").to_pylist()
            dates = tbl.column("date").to_pylist()
            decades = tbl.column("decade").to_pylist()
            pubs = tbl.column("publisher").to_pylist()
            col_texts = tbl.column("text").to_pylist()
            abstracts = tbl.column("abstract").to_pylist()
            del tbl

            if s_idx <= 6:
                # Core theological / self-help / critical-theory shards (part001..part006):
                # Reconstruct exact prefix `title. author. publisher. text` for 100% _TOKEN_CACHE hits
                layer_counts_shard = defaultdict(int)
                layer_caps = {
                    "hathitrust_ef_fullbook_print": 650,
                    "dnb_oa_fullbook": 2200,
                    "dnb_toc_pdf_fulltext": 2400,
                    "gbv_direct_fulltext_pdf": 1800,
                    "dnb_deposit_inhaltstext": 2200,
                    "drm_fallback_multi_api_enriched": 900,
                    "entire_fulltext_book_cloud": 600,
                }
                stride = max(1, n_rows // 14000)
                for i in range(0, n_rows, stride):
                    lyr_val = str(layers[i] or "dnb_deposit_inhaltstext")
                    cap = layer_caps.get(lyr_val, 800)
                    if layer_counts_shard[lyr_val] >= cap:
                        continue
                    t_raw = str(col_texts[i] or "")
                    tl_str = str(titles[i] or "")
                    au_str = str(authors[i] or "")
                    pu_str = str(pubs[i] or "")
                    if not t_raw and not tl_str:
                        continue
                    # Reconstruct original full text string that matches _TOKEN_CACHE SHA-1 key
                    t_cand1 = f"{tl_str}. {au_str}. {pu_str}. {t_raw}".strip()
                    t_cand2 = f"{tl_str}. {t_raw}".strip() if (tl_str and tl_str[:40] not in t_raw) else t_raw
                    if _hash_text(t_cand1) in _TOKEN_CACHE:
                        t_use = t_cand1
                    elif _hash_text(t_raw) in _TOKEN_CACHE:
                        t_use = t_raw
                    elif _hash_text(t_cand2) in _TOKEN_CACHE:
                        t_use = t_cand2
                    else:
                        t_use = strip_archival_headers_from_text(t_cand2)
                    r_dict = {
                        "title": tl_str,
                        "author": au_str,
                        "date": str(dates[i] or ""),
                        "decade": str(decades[i] or ""),
                        "publisher": pu_str or "DNB Monograph (DE)",
                        "corpus_layer": lyr_val,
                        "text": t_use,
                        "abstract": str(abstracts[i] or t_raw[:240]),
                        "word_count": int(wcs[i] or 0),
                    }
                    valid_rows.append(r_dict)
                    texts.append(t_use)
                    layer_counts_shard[lyr_val] += 1
            else:
                shard_added = 0
                max_hydrated_per_shard = 35
                for i in range(n_rows):
                    lyr_val = layers[i] or ""
                    wc_val = wcs[i] or 0
                    if lyr_val not in hydrated_layers and wc_val < 220:
                        continue
                    if shard_added >= max_hydrated_per_shard:
                        break
                    t_str = str(col_texts[i] or "")
                    tl_str = str(titles[i] or "")
                    if tl_str and tl_str[:40] not in t_str:
                        t_str = f"{tl_str}. {t_str}".strip() if t_str else tl_str
                    if not t_str:
                        continue
                    low_words = {w.lower() for w in _WORD_RE.findall(t_str[:900])}
                    if len(low_words & domain_lex) < 3:
                        continue
                    raw_p = str(pubs[i] or "")
                    c_pub, _ = _canon_pub(raw_p)
                    r_dict = {
                        "title": tl_str,
                        "author": str(authors[i] or ""),
                        "date": str(dates[i] or ""),
                        "decade": str(decades[i] or ""),
                        "publisher": c_pub or raw_p or "DNB Monograph (DE)",
                        "corpus_layer": lyr_val,
                        "text": t_str,
                        "abstract": str(abstracts[i] or t_str[:240]),
                        "word_count": int(wc_val),
                    }
                    valid_rows.append(r_dict)
                    texts.append(strip_archival_headers_from_text(t_str, row=r_dict))
                    shard_added += 1
                    hydrated_added += 1

            if s_idx % 15 == 0 or s_idx <= 6 or s_idx == len(shard_paths):
                print(
                    f"  [Pass 1 · 126-Shard Stream] Shard #{s_idx}/{len(shard_paths)}: "
                    f"{total_streamed_docs:,} corpus passages scanned (modeled_pool={len(valid_rows):,}, +{hydrated_added:,} newly hydrated OA/TOC/blurb passages)",
                    flush=True,
                )
    else:
        base_csv = config.HARVEST_DATA_PATH if os.path.exists(config.HARVEST_DATA_PATH) else ""
        if base_csv and os.path.exists(base_csv):
            for row in iter_corpus_rows(base_csv, include_shards=False, prefer_parquet=False):
                txt = (row.get("text") or "").strip()
                if txt:
                    valid_rows.append(row)
                    texts.append(txt)
        total_streamed_docs = len(valid_rows)

    # 3. Strict spaCy morphological POS (NOUN, PROPN, ADJ) + lemma tagging via preprocess_corpus_batch
    processed_docs = preprocess_corpus_batch(texts)
    del texts
    _TOKEN_CACHE.clear()
    gc.collect()

    filtered_docs = []
    filtered_rows = []
    for doc, row in zip(processed_docs, valid_rows):
        cleaned_doc = clean_row_tokens_for_modeling(doc, row, unboost=(mode_key == "unseeded"))
        if cleaned_doc:
            filtered_docs.append(cleaned_doc)
            filtered_rows.append(row)
    del processed_docs, valid_rows
    gc.collect()

    # Deterministic multi-shard exchangeability shuffle (Hoffman, Blei & Bach, 2010 §2.2)
    rng = random.Random(100)
    perm = list(range(len(filtered_docs)))
    rng.shuffle(perm)
    filtered_docs = [filtered_docs[idx] for idx in perm]
    filtered_rows = [filtered_rows[idx] for idx in perm]
    total_modeled_docs = len(filtered_docs)

    # 4. Bigram Phraser + Dictionary + Sublinear TF-IDF Low-Information Filter (Santana et al., 2025 §72-73)
    bigram = gensim.models.Phrases(filtered_docs, min_count=5, threshold=10, max_vocab_size=1500000)
    bigram_mod = gensim.models.phrases.Phraser(bigram)
    del bigram
    gc.collect()

    processed_n_grams = []
    for doc in filtered_docs:
        ng_doc = []
        for tok in bigram_mod[doc]:
            if tok in ALL_STOPWORDS:
                continue
            if "_" in tok:
                parts = tok.split("_")
                if len(set(parts)) == 1:
                    ng_doc.append(parts[0])
                    continue
                if any(p in ALL_STOPWORDS for p in parts):
                    continue
            ng_doc.append(tok)
        processed_n_grams.append(ng_doc)
    del filtered_docs, bigram_mod
    gc.collect()

    dictionary = corpora.Dictionary(processed_n_grams)
    if len(processed_n_grams) >= 100:
        dictionary.filter_extremes(no_below=5, no_above=0.55, keep_n=25000)
    pre_tfidf_corpus = [dictionary.doc2bow(doc) for doc in processed_n_grams]
    _, tfidf_audit = apply_tfidf_low_info_filter(pre_tfidf_corpus, dictionary, min_tfidf=0.015)
    del pre_tfidf_corpus
    corpus = [dictionary.doc2bow(doc) for doc in processed_n_grams]

    effective_k = max(2, min(k_topics, max(2, len(corpus))))
    seed_assignments = {}
    if mode_key == "seeded":
        eta_param, seed_assignments = build_seeded_eta_matrix(
            dictionary, effective_k, seed_boost=seed_boost, base_eta=base_eta
        )
    elif mode_key == "supervised":
        eta_param, seed_assignments = build_supervised_eta_matrix(
            dictionary, processed_n_grams, filtered_rows, effective_k
        )
    else:
        eta_param = config.ETA

    print(
        f"  [Pass 2 · Online VB Estimation] Training Gensim LdaModel "
        f"(K={effective_k}, streamed_passages={total_streamed_docs:,}, domain_docs={len(corpus):,}, vocab={len(dictionary):,}, passes={config.PASSES})...",
        flush=True,
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
        per_word_topics=False,
    )

    coherence_model = CoherenceModel(
        model=lda_model,
        corpus=corpus,
        dictionary=dictionary,
        coherence="u_mass",
    )
    coherence_score = float(coherence_model.get_coherence())
    slda_diagnostics = compute_slda_diagnostics(
        corpus, filtered_rows, processed_n_grams, lda_model, effective_k
    )

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
            if pub and pub not in ("Unknown", "University Presses & OA Repositories (DE)", "DNB Monograph (DE)", "[Verlag nicht ermittelbar]"):
                publisher_topic_weights[topic_id][pub] += prob
                topic_total_weights[topic_id] += prob
            if dec in ("1970s", "1980s", "1990s", "2000s", "2010s", "2020s"):
                decade_topic_weights[dec][topic_id] += prob
                decade_totals[dec] += prob

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
                "apa_citation": format_apa_citation(r),
            })
            if len(structured_list) >= 3:
                break
        representative_docs[topic_id] = structured_list

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
    lda_model.total_streamed_docs = total_streamed_docs
    lda_model.tfidf_audit = tfidf_audit

    if export_to_app:
        os.makedirs("app", exist_ok=True)
        report = build_report_dict(
            lda_model,
            corpus,
            dictionary,
            coherence_score=coherence_score,
            representative_docs=representative_docs,
        )
        report["corpus_documents"] = int(total_streamed_docs)
        lda_model.exported_topics_report = report

        with open("app/lda_topics_report.json", "w", encoding="utf-8") as rf:
            json.dump(report, rf, indent=2, ensure_ascii=False)

        html = get_viz_html(lda_model, corpus, dictionary)
        with open("app/lda_viz.html", "w", encoding="utf-8") as f:
            f.write(html)

        # Synchronize app/lda_modes_report.json with the full 10,519,923-passage corpus scale
        modes_path = "app/lda_modes_report.json"
        if os.path.exists(modes_path):
            try:
                with open(modes_path, "r", encoding="utf-8") as mf:
                    modes_data = json.load(mf)
                if "modes" in modes_data:
                    modes_data["modes"][mode_key] = report
                    for m_key, m_obj in modes_data["modes"].items():
                        m_obj["corpus_documents"] = int(total_streamed_docs)
                        m_obj["vocabulary_size"] = len(dictionary)
                if "comparison" in modes_data:
                    for comp in modes_data["comparison"]:
                        comp["documents"] = int(total_streamed_docs)
                        comp["vocab_size"] = len(dictionary)
                        if comp.get("mode") == mode_key:
                            comp["u_mass"] = round(float(coherence_score), 4)
                            if slda_diagnostics:
                                comp["regime_cv_accuracy"] = slda_diagnostics.get("regime_cv_accuracy", comp.get("regime_cv_accuracy"))
                                comp["regime_macro_f1"] = slda_diagnostics.get("regime_macro_f1", comp.get("regime_macro_f1"))
                                comp["publisher_accuracy"] = slda_diagnostics.get("publisher_cv_accuracy", comp.get("publisher_accuracy"))
                                comp["r2_explanatory_power"] = slda_diagnostics.get("r2_explanatory_power", comp.get("r2_explanatory_power"))
                with open(modes_path, "w", encoding="utf-8") as mf:
                    json.dump(modes_data, mf, indent=2, ensure_ascii=False)
            except Exception:
                pass

        # Update coherence_score and vocabulary_size in app/data_summary.json while preserving full publisher tables
        summary_path = "app/data_summary.json"
        if os.path.exists(summary_path):
            try:
                with open(summary_path, "r", encoding="utf-8") as sf:
                    sdata = json.load(sf)
                sdata["vocabulary_size"] = len(dictionary)
                sdata["coherence_score"] = round(float(coherence_score), 4)
                if "summary" in sdata and isinstance(sdata["summary"], dict):
                    sdata["summary"]["vocabulary_size"] = len(dictionary)
                    sdata["summary"]["coherence_score"] = round(float(coherence_score), 4)
                with open(summary_path, "w", encoding="utf-8") as sf:
                    json.dump(sdata, sf, indent=2, ensure_ascii=False)
            except Exception:
                pass

        print(
            f"\n[Online Streaming LDA Complete] Streamed {total_streamed_docs:,} corpus passages "
            f"({total_modeled_docs:,} domain-modeled documents, +{hydrated_added:,} newly hydrated OA/TOC/blurb passages) across {len(shard_paths)} Zstd-19 Parquet shards!\n"
            f"  -> Vocabulary: {len(dictionary):,} lemmas/bigrams | Coherence (U_Mass): {coherence_score:.4f}\n"
            f"  -> Exported to `app/lda_topics_report.json`, `app/lda_modes_report.json`, and `app/lda_viz.html`.",
            flush=True,
        )

    return lda_model, corpus, dictionary, coherence_score, representative_docs


def collect_fair_ddi_environment() -> dict:
    """
    Collects exact software, model, and hardware environment specifications for FAIR / DDI / NFDI
    reproducibility compliance (Santana et al., 2025, DHQ 19.2 §28-53; Jiménez-Badillo et al., 2020, §16).
    """
    import platform
    import sys as _sys
    env = {
        "python_version": platform.python_version(),
        "os_platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "cpu_logical_cores": os.cpu_count() or 1,
        "spacy_model": config.SPACY_MODEL,
        "random_seeds": {"gensim_lda": 100, "doc2vec_bertopic": 42, "kmeans_svd": 42, "slda_cv": 42},
        "standards": ["FAIR Principles (Wilkinson et al., 2016)", "DDI Codebook 2.5 / Lifecycle 3.3", "MARC21 / PICA+ XML"],
        "packages": {}
    }
    for mod_name, pkg_label in [
        ("gensim", "gensim"),
        ("spacy", "spacy"),
        ("sklearn", "scikit-learn"),
        ("scipy", "scipy"),
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("fitz", "PyMuPDF")
    ]:
        try:
            mod = __import__(mod_name)
            env["packages"][pkg_label] = getattr(mod, "__version__", "installed")
        except Exception:
            env["packages"][pkg_label] = "not_installed"
    if nlp is not None and hasattr(nlp, "meta"):
        env["packages"]["de_core_news_lg_meta"] = f"{nlp.meta.get('name', 'de')} v{nlp.meta.get('version', '3.8.0')}"
    return env


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
    tfidf_audit = getattr(model, "tfidf_audit", {})

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
        "tfidf_audit": tfidf_audit,
        "topics": topics_list,
        "diachronic_decade_shares": dec_breakdown,
        "slda_diagnostics": slda_diagnostics
    }


def _summarize_word_lengths(lengths: list[int], unique_works_count: int) -> dict:
    if not lengths:
        return {
            "documents": 0, "unique_works": 0, "total_words": 0,
            "mean_words": 0.0, "sd_words": 0.0, "median_words": 0.0,
            "p25_words": 0.0, "p75_words": 0.0, "iqr_words": 0.0,
            "min_words": 0, "max_words": 0
        }
    import numpy as _np
    arr = _np.array(lengths, dtype=_np.float64)
    p25, p50, p75 = _np.percentile(arr, [25, 50, 75])
    return {
        "documents": int(len(lengths)),
        "unique_works": int(unique_works_count),
        "total_words": int(_np.sum(arr)),
        "mean_words": round(float(_np.mean(arr)), 1),
        "sd_words": round(float(_np.std(arr)), 1),
        "median_words": round(float(p50), 1),
        "p25_words": round(float(p25), 1),
        "p75_words": round(float(p75), 1),
        "iqr_words": round(float(p75 - p25), 1),
        "min_words": int(_np.min(arr)),
        "max_words": int(_np.max(arr))
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
    layer_word_lengths = defaultdict(list)
    layer_unique_titles = defaultdict(set)
    all_word_lengths = []
    decade_counts = defaultdict(int)
    unique_base_titles = set()
    trends_map = defaultdict(lambda: defaultdict(int))
    total_words = 0
    count = 0

    for row in iter_corpus_rows(data_path):
        count += 1
        layer = _clean_marc_control_chars(row.get("corpus_layer") or "dnb_sru_marc21")
        layer_counts[layer] += 1

        raw_title = _clean_marc_control_chars(row.get("title") or "")
        if raw_title:
            base_t = re.sub(r"\[.*?\]", "", raw_title).strip().lower()
            if base_t:
                unique_base_titles.add(base_t)
                layer_unique_titles[layer].add(base_t)

        wc_val = row.get("word_count")
        wc_int = 0
        if wc_val:
            try:
                wc_int = int(float(wc_val))
            except Exception:
                wc_int = 0
        if wc_int <= 0:
            wc_int = len((row.get("text") or "").split())
        total_words += wc_int
        all_word_lengths.append(wc_int)
        layer_word_lengths[layer].append(wc_int)

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

    doc_length_dist = {
        "overall": _summarize_word_lengths(all_word_lengths, len(unique_base_titles)),
        "by_layer": {
            lyr: _summarize_word_lengths(
                layer_word_lengths[lyr], len(layer_unique_titles[lyr])
            )
            for lyr, _ in sorted(layer_counts.items(), key=lambda x: x[1], reverse=True)
        }
    }
    fair_ddi_env = collect_fair_ddi_environment()
    tfidf_audit = getattr(model, "tfidf_audit", {"tfidf_min_threshold": 0.015, "tfidf_pruned_tokens_count": 0})

    full_summary = {
        "source": "DNB SRU v1.1 + GBV/K10plus + HathiTrust HTRC + OpenAlex Full-Book Corpus (1970–2025)",
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
        "document_length_distribution": doc_length_dist,
        "fair_ddi_environment": fair_ddi_env,
        "pipeline_config": {
            "spacy_model": config.SPACY_MODEL,
            "allowed_postags": config.ALLOWED_POSTAGS,
            "stopwords_total": len(ALL_STOPWORDS),
            "spacy_core_stopwords_count": len(_BASE_STOPWORDS),
            "fraktur_noise_count": len(FRAKTUR_AND_META_NOISE),
            "domain_stopwords_count": len(config.DOMAIN_STOPWORDS),
            "non_canonical_per_loc_noise_count": len(NON_CANONICAL_LOC_AND_PER_NOISE),
            "canonical_theo_phil_whitelist_count": len(CANONICAL_THEO_PHIL_WHITELIST),
            "religious_boost_keywords": len(config.RELIGIOUS_VOICE_KEYWORDS),
            "german_compound_prefixes_count": len(GERMAN_COMPOUND_PREFIXES_LDA),
            "archival_header_bracket_stripping": True,
            "continuation_chunk_title_deduplication": True,
            "bigram_min_count": 5,
            "bigram_threshold": 10,
            "filter_no_below": 5,
            "filter_no_above": 0.55,
            "filter_keep_n": 25000,
            "tfidf_smartirs": tfidf_audit.get("tfidf_smartirs", "ntc"),
            "tfidf_min_threshold": tfidf_audit.get("tfidf_min_threshold", 0.015),
            "tfidf_pruned_tokens_count": tfidf_audit.get("tfidf_pruned_tokens_count", 0),
            "lda_passes": config.PASSES,
            "lda_chunksize": 1500,
            "lda_alpha": str(config.ALPHA),
            "lda_eta": str(config.ETA),
            "santana_2025_dhq_compliance": True
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
