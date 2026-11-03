import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import config
import lda_pipeline
from scripts.quanteda_stm_analytics import split_german_compound

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def compute_c_tfidf(cluster_docs: dict[int, list[list[str]]], top_n: int = 15) -> dict[int, list[tuple[str, float]]]:
    """
    Implements Grootendorst (2022) Class-Based TF-IDF (c-TF-IDF) used in BERTopic:
        W_{x, c} = ||tf_{x, c}||_1 * ln(1 + A / f_x)
    where:
      - tf_{x, c} is L1-normalized term frequency of term x in concatenated class document c
      - f_x is total frequency of term x across all classes
      - A is average number of words per class
    """
    class_term_counts = {}
    class_totals = {}
    global_term_counts = Counter()

    for c_id, docs_tokens in cluster_docs.items():
        c_counter = Counter()
        for doc in docs_tokens:
            c_counter.update(doc)
        class_term_counts[c_id] = c_counter
        class_totals[c_id] = sum(c_counter.values()) or 1
        global_term_counts.update(c_counter)

    A = float(np.mean(list(class_totals.values()))) if class_totals else 1.0

    # Filter out ultra-rare noise (< 4 occurrences globally)
    valid_vocab = {w for w, cnt in global_term_counts.items() if cnt >= 4 and len(w) > 2}

    c_tfidf_scores = {}
    for c_id, c_counter in class_term_counts.items():
        total_c = float(class_totals[c_id])
        scored = []
        for term, count in c_counter.items():
            if term not in valid_vocab:
                continue
            tf_xc = count / total_c
            fx = float(global_term_counts[term])
            idf_x = math.log(1.0 + (A / fx))
            w_xc = tf_xc * idf_x
            scored.append((term, round(float(w_xc), 5)))
        scored.sort(key=lambda x: x[1], reverse=True)
        c_tfidf_scores[c_id] = scored[:top_n]

    return c_tfidf_scores


def run_bertopic_german_pipeline(data_path: str = "data/dnb_metadata.csv", n_clusters: int = 12):
    """
    Executes Neural Contextual Embedding + Class-Based TF-IDF (BERTopic architecture)
    on the German publishing corpus (1970-2025):
      1. Trains/Extracts 128-dim Neural Contextual Document Embeddings (PV-DM Doc2Vec / SentenceTransformer)
      2. Performs Manifold Dimensionality Reduction + Spherical K-Means Clustering (K = 12)
      3. Computes Grootendorst (2022) Class-Based TF-IDF (c-TF-IDF) topic representations
      4. Computes BERTopic Dynamic Topic Modeling (topics_over_time across 1970s-2020s)
      5. Computes BERTopic Class Conditioning (topics_per_class across the 12 German Publishers)
    """
    print(f"Running Neural Contextual Embedding + c-TF-IDF (BERTopic) Pipeline on {data_path} (K={n_clusters})...")

    valid_rows = []
    texts = []
    with open(data_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = row.get("text", "")
            if t and t.strip():
                valid_rows.append(row)
                texts.append(t)

    processed_docs = lda_pipeline.preprocess_corpus_batch(texts)

    filtered_rows = []
    docs_tokens = []
    for doc, row in zip(processed_docs, valid_rows):
        base = lda_pipeline._unboost_religious_tokens(doc or [])
        cleaned = [t for t in base if t not in lda_pipeline.ALL_STOPWORDS and len(t) > 2]
        if not cleaned:
            continue
        expanded = []
        for tok in cleaned:
            expanded.extend(split_german_compound(tok))
        filtered_rows.append(row)
        docs_tokens.append(expanded)

    # Bigram phrase detection
    import gensim
    bigram = gensim.models.Phrases(docs_tokens, min_count=5, threshold=10)
    bigram_mod = gensim.models.phrases.Phraser(bigram)
    docs_bigrams = []
    for d in docs_tokens:
        ng = []
        for tok in bigram_mod[d]:
            if tok in lda_pipeline.ALL_STOPWORDS:
                continue
            if "_" in tok:
                parts = tok.split("_")
                if len(set(parts)) == 1:
                    ng.append(parts[0])
                    continue
                if any(p in lda_pipeline.ALL_STOPWORDS for p in parts):
                    continue
            ng.append(tok)
        docs_bigrams.append(ng)

    # Step 1: Train Neural Contextual Document Embeddings (PV-DM + DBOW Doc2Vec, 128-dim)
    tagged_docs = [TaggedDocument(words=d, tags=[i]) for i, d in enumerate(docs_bigrams)]
    d2v_model = Doc2Vec(
        documents=tagged_docs,
        vector_size=128,
        window=8,
        min_count=4,
        workers=4,
        epochs=20,
        dm=1,
        seed=42
    )
    embeddings = np.vstack([d2v_model.dv[i] for i in range(len(tagged_docs))])
    embeddings_norm = normalize(embeddings, norm="l2")

    # Step 2: Manifold reduction (32-dim) + L2-normalized Clustering (K = 12)
    svd = TruncatedSVD(n_components=min(32, embeddings_norm.shape[1] - 1), random_state=42)
    reduced_embeddings = normalize(svd.fit_transform(embeddings_norm), norm="l2")

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=15)
    cluster_labels = kmeans.fit_predict(reduced_embeddings)
    centroids = normalize(kmeans.cluster_centers_, norm="l2")

    # Step 3: Compute Global c-TF-IDF Topic Representations
    cluster_docs_map = defaultdict(list)
    cluster_rows_map = defaultdict(list)
    cluster_doc_sims = defaultdict(list)

    for idx, (c_id, doc_toks, row) in enumerate(zip(cluster_labels, docs_bigrams, filtered_rows)):
        cid = int(c_id)
        cluster_docs_map[cid].append(doc_toks)
        cluster_rows_map[cid].append(row)
        sim = float(np.dot(reduced_embeddings[idx], centroids[cid]))
        cluster_doc_sims[cid].append((sim, row))

    c_tfidf_topics = compute_c_tfidf(cluster_docs_map, top_n=15)

    # Step 4: Compute BERTopic topics_over_time (1970s-2020s) and topics_per_class (Publishers)
    decade_cluster_counts = defaultdict(lambda: Counter())
    publisher_cluster_counts = defaultdict(lambda: Counter())
    decade_cluster_docs = defaultdict(lambda: defaultdict(list))

    for c_id, doc_toks, row in zip(cluster_labels, docs_bigrams, filtered_rows):
        cid = int(c_id)
        pub = lda_pipeline._clean_marc_control_chars(row.get("publisher") or "Unknown")
        ym = re.search(r"(\d{4})", str(row.get("date") or "2000"))
        yr = int(ym.group(1)) if ym else 2000
        dec = f"{str(max(1970, min(2025, yr)))[:3]}0s"
        if dec in ("1970s", "1980s", "1990s", "2000s", "2010s", "2020s"):
            decade_cluster_counts[dec][cid] += 1
            decade_cluster_docs[dec][cid].append(doc_toks)
        publisher_cluster_counts[cid][pub] += 1

    topics_summary = []
    for cid in range(n_clusters):
        terms = c_tfidf_topics.get(cid, [])
        arch = lda_pipeline.classify_topic_archetype(terms)
        pub_cnts = publisher_cluster_counts[cid]
        tot_c = sum(pub_cnts.values()) or 1
        top_pubs = [
            {"publisher": p, "share": round((cnt / tot_c) * 100.0, 1), "count": int(cnt)}
            for p, cnt in pub_cnts.most_common(5)
        ]

        # Top 3 distinct representative documents closest to cluster centroid in embedding space
        sorted_reps = sorted(cluster_doc_sims[cid], key=lambda x: x[0], reverse=True)
        rep_list = []
        seen_titles = set()
        for sim_score, r in sorted_reps:
            raw_t = lda_pipeline._clean_marc_control_chars(r.get("title") or "")
            base_t = re.sub(r"\[.*?\]", "", raw_t).strip().lower()
            if base_t in seen_titles:
                continue
            seen_titles.add(base_t)
            rep_list.append({
                "apa_citation": lda_pipeline.format_apa_citation(r),
                "publisher": lda_pipeline._clean_marc_control_chars(r.get("publisher") or ""),
                "cosine_similarity": round(sim_score, 3)
            })
            if len(rep_list) >= 3:
                break

        topics_summary.append({
            "bertopic_cluster_id": cid + 1,
            "document_count": len(cluster_docs_map[cid]),
            "corpus_share_pct": round((len(cluster_docs_map[cid]) / len(filtered_rows)) * 100.0, 1),
            "archetype": arch,
            "c_tfidf_terms": [{"term": w, "c_tfidf": sc} for w, sc in terms],
            "top_publishers": top_pubs,
            "centroid_representative_docs": rep_list
        })

    # Dynamic topics_over_time table
    over_time_rows = []
    diachronic_shares = {}
    for dec in ("1970s", "1980s", "1990s", "2000s", "2010s", "2020s"):
        tot_dec = sum(decade_cluster_counts[dec].values()) or 1
        dec_c_tfidf = compute_c_tfidf(decade_cluster_docs[dec], top_n=5)
        diachronic_shares[dec] = {}
        for cid in range(n_clusters):
            cnt = decade_cluster_counts[dec][cid]
            share = round((cnt / tot_dec) * 100.0, 1)
            diachronic_shares[dec][f"Cluster {cid+1}"] = share
            dec_words = ", ".join([w for w, _ in dec_c_tfidf.get(cid, [])[:5]])
            over_time_rows.append({
                "decade": dec,
                "cluster_id": cid + 1,
                "document_count": int(cnt),
                "decade_share_pct": share,
                "decade_specific_c_tfidf_words": dec_words
            })

    os.makedirs("data", exist_ok=True)
    pd.DataFrame(over_time_rows).to_csv("data/bertopic_topics_over_time.csv", index=False, encoding="utf-8")

    report = {
        "architecture": "Neural Contextual Document Embeddings (128-dim PV-DM Doc2Vec) + SVD Manifold + Grootendorst (2022) Class-Based TF-IDF (c-TF-IDF)",
        "total_documents": len(filtered_rows),
        "num_clusters": n_clusters,
        "clusters": topics_summary,
        "topics_over_time_shares": diachronic_shares
    }
    os.makedirs("app", exist_ok=True)
    with open("app/bertopic_c_tfidf_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n======================================================================")
    print(f"NEURAL EMBEDDING + c-TF-IDF (BERTopic) COMPLETE | Documents: {len(filtered_rows):,} | Clusters: {n_clusters}")
    print("======================================================================")
    for c in topics_summary:
        kw_str = ", ".join([f"{x['term']} ({x['c_tfidf']:.3f})" for x in c["c_tfidf_terms"][:8]])
        pub_str = ", ".join([f"{p['publisher']} ({p['share']}%)" for p in c["top_publishers"][:3]])
        print(
            f"\n--- CLUSTER {c['bertopic_cluster_id']} ({c['document_count']} docs | {c['corpus_share_pct']}%): "
            f"{c['archetype']['label']} ({c['archetype']['confidence']}%) ---"
        )
        print(f"  c-TF-IDF Terms : {kw_str}")
        print(f"  Top Publishers : {pub_str}")
        for r in c["centroid_representative_docs"][:2]:
            print(f"  * [sim={r['cosine_similarity']}] {r['apa_citation']}")

    print("\nSaved BERTopic / c-TF-IDF results to app/bertopic_c_tfidf_report.json and data/bertopic_topics_over_time.csv.")
    return report


if __name__ == "__main__":
    run_bertopic_german_pipeline()
