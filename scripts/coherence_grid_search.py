"""
Hyperparameter Grid Search & Coherence Optimization for LDA Topic Modeling
Author: Paul Marandi, Ph.D. Scholar, CGS, SLL&CS, JNU
"""

import os
import sys
import csv
import json
from gensim import corpora
from gensim.models import LdaModel, Phrases
from gensim.models.phrases import Phraser
from gensim.models.coherencemodel import CoherenceModel

# Add parent directory to path so we can import config and lda_pipeline
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from lda_pipeline import preprocess_text


def prepare_corpus(data_path: str):
    """
    Loads and preprocesses the German corpus with lemmatization, POS filtering,
    domain stopword removal, religious keyword weighting, and bigram detection.
    """
    processed_docs = []
    with open(data_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get('text', '')
            if text:
                tokens = preprocess_text(text)
                if tokens:
                    processed_docs.append(tokens)

    bigram = Phrases(processed_docs, min_count=2, threshold=5)
    bigram_mod = Phraser(bigram)
    processed_n_grams = [bigram_mod[doc] for doc in processed_docs]

    dictionary = corpora.Dictionary(processed_n_grams)
    corpus = [dictionary.doc2bow(doc) for doc in processed_n_grams]
    return processed_n_grams, dictionary, corpus


def run_coherence_grid_search(
    data_path: str,
    k_values=(4, 6, 8, 10, 12, 15, 20, 25, 30),
    passes: int = 15,
    random_state: int = 100
):
    """
    Evaluates LDA models across a grid of topic counts K, computing both U_Mass
    and C_v coherence scores (Röder, Both, & Hinneburg, 2015).
    """
    print(f"Preparing corpus from: {data_path}")
    texts, dictionary, corpus = prepare_corpus(data_path)
    print(f"Corpus prepared: {len(corpus)} documents | {len(dictionary)} unique German lemmas/bigrams.\n")

    results = []
    print(f"{'K (Topics)':<12} | {'C_v Coherence':<16} | {'U_Mass Coherence':<18} | {'Log Perplexity':<16}")
    print("-" * 70)

    for k in k_values:
        lda_model = LdaModel(
            corpus=corpus,
            id2word=dictionary,
            num_topics=k,
            random_state=random_state,
            update_every=1,
            chunksize=100,
            passes=passes,
            alpha=config.ALPHA,
            eta=config.ETA,
            per_word_topics=True
        )

        # U_Mass Coherence (intrinsic document co-occurrence)
        cm_umass = CoherenceModel(
            model=lda_model,
            corpus=corpus,
            dictionary=dictionary,
            coherence='u_mass'
        )
        umass_score = float(cm_umass.get_coherence())

        # C_v Coherence (sliding window NPMI + cosine similarity; processes=1 for Windows safety)
        cm_cv = CoherenceModel(
            model=lda_model,
            texts=texts,
            dictionary=dictionary,
            coherence='c_v',
            processes=1
        )
        cv_score = float(cm_cv.get_coherence())

        log_perplexity = float(lda_model.log_perplexity(corpus))

        row = {
            'k': k,
            'c_v': round(cv_score, 4),
            'u_mass': round(umass_score, 4),
            'log_perplexity': round(log_perplexity, 4)
        }
        results.append(row)
        print(f"{k:<12} | {row['c_v']:<16.4f} | {row['u_mass']:<18.4f} | {row['log_perplexity']:<16.4f}")

    return results, len(corpus), len(dictionary)


def export_grid_search_outputs(results, doc_count: int, vocab_size: int, data_path: str):
    """
    Saves the grid search metrics to CSV, Markdown report, and generates a
    publication-ready dual-axis plot if matplotlib is installed.
    """
    os.makedirs('data', exist_ok=True)
    os.makedirs('docs/figures', exist_ok=True)

    csv_path = 'data/coherence_grid_results.csv'
    with open(csv_path, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['k', 'c_v', 'u_mass', 'log_perplexity'])
        writer.writeheader()
        writer.writerows(results)

    best_cv = max(results, key=lambda x: x['c_v'])
    best_umass = max(results, key=lambda x: x['u_mass'])

    # Generate publication-ready plot if matplotlib is available
    plot_generated = False
    plot_path = 'docs/figures/coherence_optimization_curve.png'
    try:
        import matplotlib.pyplot as plt
        ks = [r['k'] for r in results]
        cvs = [r['c_v'] for r in results]
        umasses = [r['u_mass'] for r in results]

        fig, ax1 = plt.subplots(figsize=(9, 5), dpi=300)
        color_cv = '#CA8A04'  # Academic Gold
        color_um = '#1E293B'  # Slate Midnight

        ax1.set_xlabel('Number of Latent Topics ($K$)', fontsize=11, fontweight='bold')
        ax1.set_ylabel('$C_v$ Coherence Score (Higher is Better)', color=color_cv, fontsize=11, fontweight='bold')
        line1 = ax1.plot(ks, cvs, marker='o', linewidth=2.5, color=color_cv, label='$C_v$ Coherence')
        ax1.tick_params(axis='y', labelcolor=color_cv)
        ax1.set_xticks(ks)
        ax1.grid(True, linestyle='--', alpha=0.4)

        ax2 = ax1.twinx()
        ax2.set_ylabel('$U_{\\mathrm{Mass}}$ Coherence Score (Closer to 0 is Better)', color=color_um, fontsize=11, fontweight='bold')
        line2 = ax2.plot(ks, umasses, marker='s', linestyle='--', linewidth=2.0, color=color_um, label='$U_{\\mathrm{Mass}}$ Coherence')
        ax2.tick_params(axis='y', labelcolor=color_um)

        plt.title(
            f'LDA Hyperparameter Optimization: Topic Coherence across K (n = {doc_count} docs)',
            fontsize=12,
            fontweight='bold',
            pad=14
        )
        fig.tight_layout()
        plt.savefig(plot_path, dpi=300)
        plt.close(fig)
        plot_generated = True
    except Exception as e:
        print(f"Note: Could not render matplotlib PNG ({e}). Markdown & Mermaid charts will be generated.")

    # Write scholarly Markdown report with embedded table & Mermaid XY chart
    md_path = 'docs/COHERENCE_GRID_REPORT.md'
    k_labels = ", ".join([f'"{r["k"]}"' for r in results])
    cv_vals = ", ".join([str(r["c_v"]) for r in results])

    md_content = f"""# Empirical Hyperparameter Optimization Report: Selecting Optimal Topic Count ($K$)

**Author:** Paul Marandi, Ph.D. Scholar, CGS, SLL&CS, JNU  
**Corpus Evaluated:** `{os.path.basename(data_path)}` ($N = {doc_count}$ documents, $|V| = {vocab_size}$ German lemmas & bigrams)  
**Inference Settings:** Online Variational Bayes (`passes=15`, `alpha="auto"`, `eta="auto"`, `random_state=100`)

---

## 1. Summary of Optimal Topic Granularity ($K^*$)

- **Optimal $K$ by $C_v$ Coherence (Sliding-Window NPMI):** **$K^* = {best_cv['k']}$** ($C_v = {best_cv['c_v']:.4f}$)
- **Optimal $K$ by $U_{{\\text{{Mass}}}}$ Coherence (Document Co-occurrence):** **$K^* = {best_umass['k']}$** ($U_{{\\text{{Mass}}}} = {best_umass['u_mass']:.4f}$)

In accordance with Röder, Both, and Hinneburg (2015), $C_v$ coherence exhibits the strongest correlation with human expert ratings of semantic interpretability because it combines normalized pointwise mutual information (NPMI) with cosine similarity over sliding context windows.

---

## 2. Empirical Coherence & Perplexity Table

| Number of Topics ($K$) | $C_v$ Coherence | $U_{{\\text{{Mass}}}}$ Coherence | Log Perplexity Bound | Methodological Assessment |
| :---: | :---: | :---: | :---: | :--- |
"""
    for r in results:
        note = "Optimal $C_v$ peak" if r['k'] == best_cv['k'] else (
            "Optimal $U_{\\text{Mass}}$ peak" if r['k'] == best_umass['k'] else "Evaluated candidate"
        )
        md_content += f"| **{r['k']}** | `{r['c_v']:.4f}` | `{r['u_mass']:.4f}` | `{r['log_perplexity']:.4f}` | {note} |\n"

    md_content += f"""
---

## 3. $C_v$ Coherence Optimization Curve

```mermaid
xychart-beta
    title "C_v Topic Coherence Curve across Number of Topics (K)"
    x-axis "Number of Topics (K)" [{k_labels}]
    y-axis "C_v Coherence Score" 0.20 --> 0.80
    line [{cv_vals}]
```
"""
    with open(md_path, mode='w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"\nSaved CSV metrics to: {csv_path}")
    print(f"Saved scholarly Markdown report to: {md_path}")
    if plot_generated:
        print(f"Saved publication-grade 300-DPI plot to: {plot_path}")


if __name__ == "__main__":
    real_path = os.path.join("data", "dnb_metadata.csv")
    if os.path.exists(real_path) and os.path.getsize(real_path) > 200:
        target_path = real_path
    else:
        target_path = config.MOCK_DATA_PATH

    res, n_docs, n_vocab = run_coherence_grid_search(target_path)
    export_grid_search_outputs(res, n_docs, n_vocab, target_path)
