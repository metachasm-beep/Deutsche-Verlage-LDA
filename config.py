import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "app")
MOCK_DATA_PATH = os.path.join(DATA_DIR, "religion_voices_mock.csv")

# NLP Settings
SPACY_MODEL = "de_core_news_sm"
STOPWORDS_FILE = None # Can be a path to a custom txt file

# LDA Hyperparameters
NUM_TOPICS = 10
PASSES = 15
ALPHA = "auto"
ETA = "auto"

# Citation Settings
CITATION_STYLE = "APA" # Enforce APA 7th Edition for all research and writing skills

# POS tags to keep for LDA
ALLOWED_POSTAGS = ["NOUN", "PROPN", "ADJ"]

# Domain-specific German stopwords (Archival & Publishing)
DOMAIN_STOPWORDS = [
    "verlag", "seiten", "isbn", "auflage", "euro", "jahr", "märz", "berlin", "frankfurt",
    "ebd", "vgl", "hrsg", "hg", "abb", "anm", "aufl", "bd", "bde", "bzw", "ca", "dh", 
    "diss", "me", "ua", "usw", "zb", "zt", "ff", "f", "s",
    "dnb", "bibliothek", "deutsche", "nationalbibliothek", "katalog", "reihe"
]

# Specialized keywords for Ph.D. Research weighting (Thematic Focus)
RELIGIOUS_VOICE_KEYWORDS = [
    "glaube", "gott", "spiritualität", "kirche", "ethik", "moral", 
    "erlösung", "sinn", "transzendenz", "gnade", "offenbarung",
    "seelsorge", "predigt", "theologie", "religiös", "christlich",
    "atheismus", "kirchenkritik", "religionskritik", "säkularität", "selbsthilfe"
]
