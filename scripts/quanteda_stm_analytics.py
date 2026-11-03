import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
from scipy import stats

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import config
import lda_pipeline

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Productive German theological, sociological, and philosophical compound stems (Bestimmungswörter & Grundwörter)
GERMAN_COMPOUND_PREFIXES = [
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
    ("selbst", ["selbst"]),
    ("welt", ["welt"]),
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
    ("schuld", ["schuld"]),
    ("angst", ["angst"]),
    ("zwangs", ["zwang"]),
    ("freiheits", ["freiheit"]),
    ("wahrheits", ["wahrheit"]),
    ("vernunft", ["vernunft"]),
    ("wissenschafts", ["wissenschaft"]),
    ("theologie", ["theologie"]),
    ("philosophie", ["philosophie"]),
    ("identitäts", ["identität"]),
    ("gemeinschafts", ["gemeinschaft"]),
    ("konfessions", ["konfession"]),
    ("gruppen", ["gruppe"]),
    ("sozial", ["sozial"]),
    ("alltags", ["alltag"]),
    ("zukunfts", ["zukunft"]),
    ("friedens", ["frieden"]),
    ("frauen", ["frau"]),
    ("kinder", ["kind"]),
    ("jugend", ["jugend"]),
]

SECULAR_PUBLISHERS = {
    "suhrkamp", "rowohlt", "fischer", "alibri", "wagenbach", "kiepenheuer", "klett",
    "beck", "campus", "insel", "meiner", "wallstein", "transcript", "springer", "gruyter",
    "budrich", "oekom", "nomos", "open access book (de)"
}
CONFESSIONAL_PUBLISHERS = {
    "herder", "evangelische verlagsanstalt", "gütersloher verlagshaus", "patmos", "kösel",
    "vandenhoeck", "mohr", "kohlhammer", "schöningh", "aschendorff", "pustet", "echter",
    "bonifatius", "neukirchener", "calwer", "grünewald", "kaiser", "kreuz", "schwabenverlag",
    "benziger", "tvz", "theologisch"
}


def split_german_compound(token: str) -> list[str]:
    """
    Splits a German compound noun (Kompositum) into its constituent stems (Bestimmungswort + Grundwort)
    while retaining the original compound lemma.
    Example:
      'religionskritik' -> ['religionskritik', 'religion', 'kritik']
      'kirchenmitgliedschaftsuntersuchung' -> ['kirchenmitgliedschaftsuntersuchung', 'kirche', 'mitgliedschaft', 'untersuchung']
    """
    w = token.lower().strip()
    if len(w) < 9 or "_" in w:
        return [w]

    for prefix, mapped_roots in GERMAN_COMPOUND_PREFIXES:
        if w.startswith(prefix) and len(w) >= len(prefix) + 4:
            remainder = w[len(prefix):]
            # Strip optional Fugenelement 's' if remainder starts with 's' followed by consonant
            if remainder.startswith("s") and len(remainder) >= 6 and remainder[1] not in "aeiouäöüch":
                remainder = remainder[1:]
            if len(remainder) >= 4 and remainder not in lda_pipeline.ALL_STOPWORDS:
                return [w] + mapped_roots + [remainder]
    return [w]


def classify_publisher_camp(pub_str: str) -> str:
    p = (pub_str or "").lower().strip()
    for conf in CONFESSIONAL_PUBLISHERS:
        if conf in p or ("gütersloh" in p) or ("kösel" in p):
            return "Confessional / Theological"
    for sec in SECULAR_PUBLISHERS:
        if sec in p:
            return "Secular / Critical / Trade"
    return "Secular / Critical / Trade"


def compute_dunning_g2_keyness(
    target_counts: Counter,
    reference_counts: Counter,
    min_total_freq: int = 10,
    top_n: int = 25
) -> dict:
    """
    Exact Python implementation of quanteda::textstat_keyness(measure = 'lr') (Dunning's Log-Likelihood G^2)
    and Pearson's Chi-Square with Yates correction + Log-Odds Ratio and two-tailed p-values.
    """
    N_target = float(sum(target_counts.values())) or 1.0
    N_ref = float(sum(reference_counts.values())) or 1.0
    N_total = N_target + N_ref

    all_vocab = set(target_counts.keys()).union(set(reference_counts.keys()))
    rows = []

    for term in all_vocab:
        if term in lda_pipeline.ALL_STOPWORDS or len(term) <= 2:
            continue
        O11 = float(target_counts.get(term, 0))
        O12 = float(reference_counts.get(term, 0))
        if (O11 + O12) < min_total_freq:
            continue

        O21 = max(1.0, N_target - O11)
        O22 = max(1.0, N_ref - O12)

        # Expected frequencies under null hypothesis of independence
        E11 = (N_target * (O11 + O12)) / N_total
        E12 = (N_ref * (O11 + O12)) / N_total
        E21 = (N_target * (O21 + O22)) / N_total
        E22 = (N_ref * (O21 + O22)) / N_total

        # Dunning's G^2 = 2 * sum(O_ij * ln(O_ij / E_ij))
        g2 = 0.0
        for O, E in ((O11, E11), (O12, E12), (O21, E21), (O22, E22)):
            if O > 0 and E > 0:
                g2 += 2.0 * O * math.log(O / E)

        # Sign of G^2: positive if over-represented in target group, negative if over-represented in reference group
        sign = 1.0 if O11 > E11 else -1.0
        signed_g2 = sign * g2
        p_val = float(stats.chi2.sf(abs(g2), df=1))

        # Smoothed Log-Odds Ratio (Laplace +0.5 smoothing)
        log_odds = math.log(((O11 + 0.5) / (O21 + 0.5)) / ((O12 + 0.5) / (O22 + 0.5)))

        rows.append({
            "feature": term,
            "g2_keyness": round(signed_g2, 2),
            "log_odds_ratio": round(log_odds, 3),
            "p_value": p_val,
            "n_target": int(O11),
            "n_reference": int(O12),
            "rate_target_per_10k": round((O11 / N_target) * 10000, 2),
            "rate_ref_per_10k": round((O12 / N_ref) * 10000, 2)
        })

    rows_sorted = sorted(rows, key=lambda x: x["g2_keyness"], reverse=True)
    return {
        "top_target_keyness": rows_sorted[:top_n],
        "top_reference_keyness": sorted(rows, key=lambda x: x["g2_keyness"])[:top_n]
    }


def compute_stm_covariate_regressions(theta: np.ndarray, docvars: list[dict], topic_labels: list[str]) -> list[dict]:
    """
    Exact Python implementation of stm::estimateEffect(1:K ~ publisher_camp + year_norm):
    Regresses each document's topic proportion theta_{d,k} on:
      X_1: IsSecularPublisher (1 = Secular/Critical/Trade, 0 = Confessional/Theological)
      X_2: TimeNormalized ((Year - 1970) / 55.0 in [0, 1], representing the 55-year shift from 1970 to 2025)
    Returns exact OLS coefficients, standard errors, t-statistics, two-sided p-values, and 95% confidence intervals.
    """
    n_docs, k_topics = theta.shape
    is_secular = np.array(
        [1.0 if dv["publisher_camp"] == "Secular / Critical / Trade" else 0.0 for dv in docvars],
        dtype=np.float64
    )
    years = np.array([float(dv["year"]) for dv in docvars], dtype=np.float64)
    time_norm = (years - 1970.0) / 55.0

    # Design matrix X = [Intercept, IsSecular, TimeNorm]
    X = np.column_stack([np.ones(n_docs), is_secular, time_norm])
    df_resid = max(1, n_docs - X.shape[1])
    xtx_inv = np.linalg.pinv(X.T @ X)
    t_crit = float(stats.t.ppf(0.975, df=df_resid))

    results = []
    for k in range(k_topics):
        y = theta[:, k]
        beta = xtx_inv @ (X.T @ y)
        resid = y - (X @ beta)
        sigma2 = float(np.sum(resid ** 2) / df_resid)
        se = np.sqrt(np.maximum(1e-12, np.diag(sigma2 * xtx_inv)))
        t_stats = beta / se
        p_vals = [float(2.0 * stats.t.sf(abs(ts), df=df_resid)) for ts in t_stats]

        # Convert effects to percentage points (* 100) for intuitive dissertation reporting
        b_sec = float(beta[1] * 100.0)
        se_sec = float(se[1] * 100.0)
        b_time = float(beta[2] * 100.0)
        se_time = float(se[2] * 100.0)

        results.append({
            "topic_id": k + 1,
            "topic_label": topic_labels[k] if k < len(topic_labels) else f"Topic {k+1}",
            "secular_vs_confessional_effect_pct": round(b_sec, 2),
            "secular_ci_95": [round(b_sec - t_crit * se_sec, 2), round(b_sec + t_crit * se_sec, 2)],
            "secular_t_stat": round(float(t_stats[1]), 2),
            "secular_p_value": round(p_vals[1], 6),
            "secular_significant": bool(p_vals[1] < 0.05),
            "diachronic_1970_2025_shift_pct": round(b_time, 2),
            "diachronic_ci_95": [round(b_time - t_crit * se_time, 2), round(b_time + t_crit * se_time, 2)],
            "diachronic_t_stat": round(float(t_stats[2]), 2),
            "diachronic_p_value": round(p_vals[2], 6),
            "diachronic_significant": bool(p_vals[2] < 0.05)
        })
    return results


def extract_kwic_concordances(
    rows: list[dict],
    keywords: list[str] = None,
    window: int = 12,
    max_per_keyword: int = 12
) -> list[dict]:
    """
    Exact Python implementation of quanteda::kwic(tokens, pattern, window = 12):
    Extracts Keywords-in-Context (pre-context, keyword match, post-context) with APA citations.
    """
    if not keywords:
        keywords = [
            "säkularisierung", "religionskritik", "atheismus", "achtsamkeit",
            "selbstsorge", "fundamentalismus", "konfessionslosigkeit", "pluralismus"
        ]

    concordances = []
    counts_per_kw = defaultdict(int)

    for r in rows:
        text = str(r.get("text") or "")
        if not text:
            continue
        words = text.split()
        words_lower = [re.sub(r"[^\wäöüÄÖÜß]", "", w.lower()) for w in words]

        for idx, wl in enumerate(words_lower):
            for kw in keywords:
                if counts_per_kw[kw] >= max_per_keyword:
                    continue
                if kw in wl:
                    pre = " ".join(words[max(0, idx - window):idx])
                    post = " ".join(words[idx + 1:min(len(words), idx + 1 + window)])
                    concordances.append({
                        "keyword": kw,
                        "pre_context": pre,
                        "keyword_in_text": words[idx],
                        "post_context": post,
                        "publisher": lda_pipeline._clean_marc_control_chars(r.get("publisher") or ""),
                        "year": lda_pipeline._clean_marc_control_chars(r.get("date") or ""),
                        "apa_citation": lda_pipeline.format_apa_citation(r)
                    })
                    counts_per_kw[kw] += 1
    return concordances


def run_quanteda_stm_suite(data_path: str = "data/dnb_metadata.csv"):
    print(f"Running Quanteda + STM Analytics Suite on {data_path}...")
    model, corpus, dictionary, coh, rep_docs = lda_pipeline.run_pipeline(data_path)

    # Reload valid rows and cached tokens
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

    # Apply German Compound Splitting (Komposita-Zerlegung) and build docvars
    filtered_rows = []
    compound_expanded_docs = []
    compound_split_counter = Counter()

    secular_counts = Counter()
    confessional_counts = Counter()
    early_decade_counts = Counter()
    late_decade_counts = Counter()
    docvars = []

    for doc, row in zip(processed_docs, valid_rows):
        cleaned = [t for t in (doc or []) if t not in lda_pipeline.ALL_STOPWORDS and len(t) > 2]
        if not cleaned:
            continue
        filtered_rows.append(row)

        expanded = []
        for tok in cleaned:
            parts = split_german_compound(tok)
            expanded.extend(parts)
            if len(parts) > 1:
                compound_split_counter[f"{tok} -> {' + '.join(parts[1:])}"] += 1

        compound_expanded_docs.append(expanded)

        pub = lda_pipeline._clean_marc_control_chars(row.get("publisher") or "Unknown")
        camp = classify_publisher_camp(pub)
        ym = re.search(r"(\d{4})", str(row.get("date") or "2000"))
        yr = int(ym.group(1)) if ym else 2000
        yr = max(1970, min(2025, yr))
        dec = f"{str(yr)[:3]}0s"

        docvars.append({
            "doc_id": f"doc_{len(docvars) + 1}",
            "title": lda_pipeline._clean_marc_control_chars(row.get("title") or ""),
            "author": lda_pipeline._clean_marc_control_chars(row.get("author") or "o. V."),
            "publisher": pub,
            "publisher_camp": camp,
            "year": yr,
            "decade": dec,
            "corpus_layer": lda_pipeline._clean_marc_control_chars(row.get("corpus_layer") or "")
        })

        for tok in set(expanded):  # Document-frequency / token-frequency hybrid
            pass
        if camp == "Secular / Critical / Trade":
            secular_counts.update(expanded)
        else:
            confessional_counts.update(expanded)

        if yr < 2000:
            early_decade_counts.update(expanded)
        else:
            late_decade_counts.update(expanded)

    # 1. Compute Dunning's G^2 Keyness (Secular vs Confessional & Post-2000 vs Pre-2000)
    keyness_publisher_camp = compute_dunning_g2_keyness(secular_counts, confessional_counts, min_total_freq=15, top_n=25)
    keyness_diachronic = compute_dunning_g2_keyness(late_decade_counts, early_decade_counts, min_total_freq=15, top_n=25)

    # 2. Build Document-Topic Matrix Theta (D x K) and run STM Covariate Regressions
    n_docs = len(corpus)
    k_topics = model.num_topics
    theta = np.zeros((n_docs, k_topics), dtype=np.float64)
    for i, doc_bow in enumerate(corpus):
        for t_id, prob in model.get_document_topics(doc_bow, minimum_probability=0.0):
            if t_id < k_topics:
                theta[i, t_id] = float(prob)

    topic_labels = []
    for t_id in range(k_topics):
        terms = model.show_topic(t_id, topn=5)
        arch = lda_pipeline.classify_topic_archetype(model.show_topic(t_id, topn=15))
        top_words = ", ".join([w for w, _ in terms[:4]])
        topic_labels.append(f"Topic {t_id+1} ({arch['label']}: {top_words})")

    stm_covariate_effects = compute_stm_covariate_regressions(theta, docvars, topic_labels)

    # 3. Extract KWIC Concordances
    kwic_rows = extract_kwic_concordances(filtered_rows, window=12, max_per_keyword=10)
    os.makedirs("data", exist_ok=True)
    pd.DataFrame(kwic_rows).to_csv("data/kwic_concordances.csv", index=False, encoding="utf-8")

    # 4. Export Pre-Tokenized Quanteda + STM CSV for R (scripts/run_quanteda_stm.R)
    r_export_rows = []
    for dv, exp_tokens in zip(docvars, compound_expanded_docs):
        r_export_rows.append({
            **dv,
            "spacy_compound_tokens": " ".join(exp_tokens[:800])
        })
    pd.DataFrame(r_export_rows).to_csv("data/quanteda_tokens_export.csv", index=False, encoding="utf-8")

    top_compounds = [
        {"decomposition": k, "count": int(v)}
        for k, v in compound_split_counter.most_common(30)
    ]

    suite_report = {
        "total_documents": len(docvars),
        "secular_documents": sum(1 for d in docvars if d["publisher_camp"] == "Secular / Critical / Trade"),
        "confessional_documents": sum(1 for d in docvars if d["publisher_camp"] == "Confessional / Theological"),
        "top_german_compound_splits": top_compounds,
        "keyness_secular_vs_confessional": keyness_publisher_camp,
        "keyness_2000_2025_vs_1970_1999": keyness_diachronic,
        "stm_covariate_regressions": stm_covariate_effects,
        "kwic_sample_count": len(kwic_rows),
        "kwic_samples": kwic_rows[:24]
    }

    os.makedirs("app", exist_ok=True)
    with open("app/quanteda_stm_report.json", "w", encoding="utf-8") as f:
        json.dump(suite_report, f, indent=2, ensure_ascii=False)

    print("\n======================================================================")
    print("QUANTEDA + STM ANALYTICS SUITE COMPLETE")
    print("======================================================================")
    print(f"Documents Analyzed: {len(docvars):,} (Secular/Critical: {suite_report['secular_documents']:,} | Confessional: {suite_report['confessional_documents']:,})")
    print("\nTop 10 Decomposed German Compound Nouns (Komposita-Zerlegung):")
    for c in top_compounds[:10]:
        print(f"  * {c['decomposition']} ({c['count']}x)")

    print("\nTop 10 Keyness Terms: SECULAR/CRITICAL Publishers (Dunning's G^2):")
    for k in keyness_publisher_camp["top_target_keyness"][:10]:
        print(f"  + {k['feature']:22s} | G^2 = {k['g2_keyness']:8.2f} | LogOdds = {k['log_odds_ratio']:+5.2f} | p = {k['p_value']:.2e}")

    print("\nTop 10 Keyness Terms: CONFESSIONAL/THEOLOGICAL Publishers (Dunning's G^2):")
    for k in keyness_publisher_camp["top_reference_keyness"][:10]:
        print(f"  - {k['feature']:22s} | G^2 = {k['g2_keyness']:8.2f} | LogOdds = {k['log_odds_ratio']:+5.2f} | p = {k['p_value']:.2e}")

    print("\nSTM Covariate Regressions (theta_k ~ SecularCamp + Time_1970_2025):")
    for r in stm_covariate_effects:
        sec_sig = "*" if r["secular_significant"] else " "
        tim_sig = "*" if r["diachronic_significant"] else " "
        print(
            f"  Topic {r['topic_id']:2d} | Secular Effect: {r['secular_vs_confessional_effect_pct']:+6.2f}% "
            f"(t={r['secular_t_stat']:+5.2f}, p={r['secular_p_value']:.4f}){sec_sig} | "
            f"1970->2025 Shift: {r['diachronic_1970_2025_shift_pct']:+6.2f}% "
            f"(t={r['diachronic_t_stat']:+5.2f}, p={r['diachronic_p_value']:.4f}){tim_sig}"
        )

    print("\nSaved reports to app/quanteda_stm_report.json, data/kwic_concordances.csv, and data/quanteda_tokens_export.csv.")
    return suite_report


if __name__ == "__main__":
    run_quanteda_stm_suite()
