import pandas as pd
import gensim
from gensim import corpora
from gensim.models import LdaModel
import spacy
from tqdm import tqdm
import config
import os

# Load German Spacy model
try:
    nlp = spacy.load(config.SPACY_MODEL)
except OSError:
    print(f"Spacy model {config.SPACY_MODEL} not found. Please run: python -m spacy download {config.SPACY_MODEL}")
    exit(1)

def preprocess_text(text, allowed_postags=config.ALLOWED_POSTAGS):
    """
    Tokenize, lemmatize, remove stopwords and filter by POS tags for German text.
    Includes weighting for 'Religious Voices' keywords.
    """
    doc = nlp(text)
    # Lemmatization & POS Filtering
    tokens = [token.lemma_.lower() for token in doc if token.pos_ in allowed_postags]
    
    # Weighting: Duplicate tokens if they match the Religious whitelist
    weighted_tokens = []
    for t in tokens:
        weighted_tokens.append(t)
        if t in config.RELIGIOUS_VOICE_KEYWORDS:
            weighted_tokens.append(t) # Weight: 2x
            
    # Stopword removal (NLTK/Spacy defaults + Custom)
    all_stop = nlp.Defaults.stop_words.union(set(config.DOMAIN_STOPWORDS))
    tokens = [t for t in weighted_tokens if t not in all_stop]
    # Remove short tokens
    tokens = [t for t in tokens if len(t) > 2]
    return tokens

def run_pipeline(data_path):
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    
    # Filter out empty rows if any
    df = df.dropna(subset=['text'])
    
    print("Preprocessing texts...")
    processed_docs = []
    for text in tqdm(df['text']):
        processed_docs.append(preprocess_text(text))
    
    # --- PHASE 1: N-Gram Detection ---
    print("Detecting common collocations (N-Grams)...")
    bigram = gensim.models.Phrases(processed_docs, min_count=2, threshold=5) # Adjust threshold for sensitivity
    bigram_mod = gensim.models.phrases.Phraser(bigram)
    
    # Update docs with N-grams
    processed_n_grams = [bigram_mod[doc] for doc in tqdm(processed_docs)]
    
    # Create Dictionary
    dictionary = corpora.Dictionary(processed_n_grams)
    
    # Filter extreme tokens (optional but recommended for large corpora)
    # dictionary.filter_extremes(no_below=2, no_above=0.5)
    
    # Create Corpus
    corpus = [dictionary.doc2bow(doc) for doc in processed_n_grams]
    
    print(f"Training LDA model with {config.NUM_TOPICS} topics...")
    lda_model = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=config.NUM_TOPICS,
        random_state=100,
        update_every=1,
        chunksize=100,
        passes=config.PASSES,
        alpha=config.ALPHA,
        per_word_topics=True
    )
    
    return lda_model, corpus, dictionary

import pyLDAvis
import pyLDAvis.gensim_models as gensimvis

import json

def get_viz_html(lda_model, corpus, dictionary):
    """
    Generates the pyLDAvis HTML string for the given model.
    """
    print("Preparing topic visualization (this may take a moment)...")
    vis_data = gensimvis.prepare(lda_model, corpus, dictionary)
    return pyLDAvis.prepared_data_to_html(vis_data)

def export_results(model, corpus, dictionary, data_path):
    """
    Exports static visualization and data summary for the frontend.
    """
    if not os.path.exists('app'): os.makedirs('app')
    
    # 1. Visualization
    html = get_viz_html(model, corpus, dictionary)
    with open("app/lda_viz.html", "w", encoding='utf-8') as f:
        f.write(html)
        
    # 2. Data Summary
    df = pd.read_csv(data_path)
    summary = {
        "count": len(df),
        "source": os.path.basename(data_path),
        "publishers": df['publisher'].unique().tolist() if 'publisher' in df.columns else ["N/A"]
    }
    with open("app/data_summary.json", "w", encoding='utf-8') as f:
        json.dump(summary, f)
        
    print("✅ Results exported to app/ folder.")

if __name__ == "__main__":
    data_path = config.MOCK_DATA_PATH
    
    # Priority: Real harvest if it exists and is not empty
    real_path = "data/dnb_metadata.csv"
    if os.path.exists(real_path) and os.path.getsize(real_path) > 100:
        data_path = real_path
        print(f"Using REAL HARVEST data from {data_path}")
    else:
        print(f"Using MOCK 'Voices on Religion' data from {data_path}")
        
    model, corp, dict_ = run_pipeline(data_path)
    export_results(model, corp, dict_, data_path)
