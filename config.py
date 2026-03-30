import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MOCK_DATA_PATH = os.path.join(BASE_DIR, "mock_data.csv")

# NLP Settings
SPACY_MODEL = "de_core_news_lg"
STOPWORDS_FILE = None # Can be a path to a custom txt file

# LDA Hyperparameters
NUM_TOPICS = 10
PASSES = 15
ALPHA = "auto"
ETA = "auto"

# Citation Settings
CITATION_STYLE = "APA" # Enforce APA 7th Edition for all research and writing skills

# POS tags to keep for LDA
ALLOWED_POSTAGS = ["NOUN", "PROPN", "ADJ", "VERB"]

# Domain-specific German stopwords (Academic & Publishing)
DOMAIN_STOPWORDS = [
    "verlag", "seiten", "isbn", "auflage", "euro", "jahr", "märz", "berlin", "frankfurt",
    "ebd", "vgl", "hrsg", "hg", "abb", "anm", "aufl", "bd", "bde", "bzw", "ca", "dh", 
    "diss", "me", "ua", "usw", "zb", "zt", "ff", "f", "s"
]
