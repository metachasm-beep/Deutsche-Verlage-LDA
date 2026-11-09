import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "app")
MOCK_DATA_PATH = os.path.join(DATA_DIR, "religion_voices_mock.csv")
HARVEST_DATA_PATH = os.path.join(BASE_DIR, "data", "dnb_metadata.csv")
TOKEN_CACHE_PATH = os.path.join(BASE_DIR, "data", "token_cache.json")
COHERENCE_GRID_PATH = os.path.join(BASE_DIR, "data", "coherence_grid_results.csv")

# NLP Settings
SPACY_MODEL = "de_core_news_lg"
SPACY_FALLBACK_MODELS = ["de_core_news_lg", "de_core_news_md", "de_core_news_sm"]
STOPWORDS_FILE = None  # Can be a path to a custom txt file

# LDA Hyperparameters (Default K=12 corresponds to Meso-Level C_v Inflection)
NUM_TOPICS = 12
PASSES = 15
ALPHA = "auto"
ETA = "auto"

# Citation Settings
CITATION_STYLE = "APA"  # Enforce APA 7th Edition for all research and writing skills

# POS tags to keep for LDA
ALLOWED_POSTAGS = ["NOUN", "PROPN", "ADJ"]

# Domain-specific German stopwords (Archival, MARC21 & Publishing Noise + Generic Ubiquity Nouns)
DOMAIN_STOPWORDS = [
    "verlag", "seiten", "isbn", "auflage", "euro", "jahr", "märz", "berlin", "frankfurt",
    "ebd", "vgl", "hrsg", "hg", "abb", "anm", "aufl", "bd", "bde", "bzw", "ca", "dh",
    "diss", "me", "ua", "usw", "zb", "zt", "ff", "f", "s",
    "dnb", "bibliothek", "deutsche", "nationalbibliothek", "katalog", "reihe",
    "produktform", "spezifisch", "paperback", "hardback", "schutzumschlag", "with", "dust", "jacket",
    "sachbücher", "sachbuch", "band", "bände", "ausgabe", "neuausgabe", "beitrag", "buch", "werk",
    "fall", "stelle", "tatsache", "name", "frage", "wort", "begriff", "bedeutung", "problem",
    "form", "art", "weise", "seite", "teil", "zeit", "mensch", "leben", "welt", "land", "stadt",
    "hand", "auge", "tag", "weg", "ort", "bild", "raum", "arbeit", "text", "autor", "beispiel",
    "grund", "folge", "sicht", "rahmen", "zusammenhang", "blick", "anfang", "ende", "mitte",
    "zahl", "punkt", "ebene", "bereich", "gebiet", "feld", "schrift", "brief", "person", "leute",
    "volk", "frau", "mann", "kind", "mädchen", "junge", "eltern", "mutter", "vater", "sohn", "tochter"
]

# Specialized keywords for Ph.D. Research weighting (Thematic Focus)
RELIGIOUS_VOICE_KEYWORDS = [
    "glaube", "gott", "spiritualität", "kirche", "ethik", "moral",
    "erlösung", "sinn", "transzendenz", "gnade", "offenbarung",
    "seelsorge", "predigt", "theologie", "religiös", "christlich",
    "atheismus", "kirchenkritik", "religionskritik", "säkularität", "selbsthilfe"
]

# Theoretical Archetype Lexicons for Automated Discursive Classification
ARCHETYPE_LEXICONS = {
    "Traditional / Ecclesiastical": {
        "kirche", "gott", "seelsorge", "liturgie", "gemeinde", "glaube", "christlich",
        "dogmatik", "sakrament", "gottesdienst", "bibel", "bischof", "ökumene",
        "gebet", "erlösung", "gnade", "christus", "jesus", "jesu", "katholisch", "evangelisch",
        "theologie", "theologisch", "pfarrer", "eucharistie", "messfeier", "kirchenjahr", "christentum",
        "christ", "religionspädagogik", "religionsunterricht", "diakonie", "caritas", "exegese",
        "testament", "psalm", "schöpfung", "auferstehung", "verkündigung", "konfession", "kloster",
        "mönch", "papst", "konzil", "taufe", "frömmigkeit", "heilig", "predigt", "mission",
        "katechismus", "synode", "trinität", "offenbarung", "kirchengeschichte", "kirchenrecht"
    },
    "Neoliberal / Self-Optimization": {
        "selbstoptimierung", "erfolg", "achtsamkeit", "markt", "selbsthilfe", "lebenshilfe",
        "glück", "resilienz", "gesundheit", "führung", "management", "gelingen",
        "heilung", "spiritualität", "potenzial", "erfüllung", "spirituell", "alltag",
        "lebensführung", "coaching", "wohlbefinden", "krise", "sinn", "meditation",
        "burnout", "selbstliebe", "gelassenheit", "lebenskunst", "selbstfürsorge",
        "stressbewältigung", "therapie", "psychologie", "psychologisch", "psychotherapie",
        "beratung", "bewusstsein", "seele", "körper", "lebenspraxis", "erfahrung",
        "identität", "pädagogik", "erziehung", "anthroposophie", "waldorfschule",
        "ganzheitlich", "harmonie", "trauma", "biografiearbeit", "sinnkrise"
    },
    "Critical / Secular-Humanist": {
        "atheismus", "atheist", "atheistisch", "aufklärung", "machtkritik", "säkularismus",
        "säkularisierung", "säkularität", "humanismus", "humanistisch", "religionskritik",
        "kirchenkritik", "wissenschaft", "wissenschaftlich", "vernunft", "säkular",
        "demokratie", "demokratisch", "politik", "politisch", "ideologie", "ideologiekritik",
        "herrschaft", "diktatur", "antisemitismus", "kritik", "kritisch", "machtmissbrauch",
        "klerikalismus", "philosophie", "philosoph", "philosophisch", "gesellschaft",
        "gesellschaftlich", "staat", "staatlich", "recht", "rechtlich", "gesetz",
        "freiheit", "autonomie", "emanzipation", "moderne", "modernisierung", "pluralismus",
        "diskurs", "öffentlichkeit", "soziologie", "religionssoziologie", "systemtheorie",
        "ethik", "ethisch", "moral", "moralisch", "kultur", "kulturell", "freidenker",
        "materialismus", "naturalismus", "laizismus", "toleranz", "menschenrechte"
    }
}
