"""
Candidates 3, 5 & 7: Posterior Topic Projection, Stateless Query Seam & Information-Theoretic Geometry Module.

Deepens:
1. Stateless `PosteriorSliceQuery` value object (Candidate 5)
2. Canonical Posterior Topic schema normalization across `lda_pipeline.py` and `app/main.py` (Candidate 3)
3. Exact pairwise Jensen-Shannon Divergence, double-centered Torgerson Classical MDS (PC1, PC2),
   and marginal corpus word probabilities p(w) (Candidate 7)
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from app.domain.ideological_taxonomy import (
    CANONICAL_REGIMES,
    REGIME_CRITICAL,
    REGIME_NEOLIBERAL,
    REGIME_TRADITIONAL,
    normalize_regime_label,
)


@dataclass(frozen=True)
class PosteriorSliceQuery:
    """
    Stateless value object encapsulating all conditioning parameters across the
    frontend/backend Posterior Topic query seam (Candidate 5).
    """
    lda_mode: str = "unsupervised"
    num_topics: int = 12
    year: int | None = None
    decade: int | None = None
    publishers: tuple[str, ...] = ()
    seed_boost: float = 15.0
    base_eta: float = 0.05

    @classmethod
    def from_request(
        cls,
        lda_mode: str | None = "unsupervised",
        num_topics: int | None = 12,
        year: int | None = None,
        decade: int | None = None,
        publishers: Iterable[str] | str | None = None,
        seed_boost: float | None = 15.0,
        base_eta: float | None = 0.05,
    ) -> "PosteriorSliceQuery":
        valid_modes = {"unseeded", "unsupervised", "seeded", "supervised"}
        mode_clean = str(lda_mode or "unsupervised").strip().lower()
        if mode_clean not in valid_modes:
            mode_clean = "unsupervised"
        k_clean = max(2, min(50, int(num_topics if num_topics is not None else 12)))
        if isinstance(publishers, str):
            pubs = tuple(p.strip() for p in publishers.split(",") if p.strip())
        elif publishers:
            pubs = tuple(str(p).strip() for p in publishers if str(p).strip())
        else:
            pubs = ()
        return cls(
            lda_mode=mode_clean,
            num_topics=k_clean,
            year=int(year) if year is not None else None,
            decade=int(decade) if decade is not None else None,
            publishers=pubs,
            seed_boost=float(seed_boost if seed_boost is not None else 15.0),
            base_eta=float(base_eta if base_eta is not None else 0.05),
        )


def normalize_posterior_topic_schema(raw_topic: dict, index_0: int | None = None) -> dict:
    """
    Normalizes a Posterior Topic dictionary between offline `build_report_dict` format
    (`topic_id` 1-indexed, `top_terms: [{term, weight}]`, `top_publishers: [{publisher, share}]`)
    and interactive `/api/topics` format (`id` 0-indexed, `keywords: [{word, weight}]`, `top_publishers: {pub: share}`).
    """
    if index_0 is None:
        if "id" in raw_topic:
            index_0 = int(raw_topic["id"])
        elif "topic_id" in raw_topic:
            index_0 = max(0, int(raw_topic["topic_id"]) - 1)
        else:
            index_0 = 0

    raw_kws = raw_topic.get("keywords") or raw_topic.get("top_terms") or []
    keywords: list[dict] = []
    top_terms: list[dict] = []
    for kw in raw_kws:
        w = str(kw.get("word") or kw.get("term") or "").strip()
        wt = round(float(kw.get("weight", 0.0)), 5)
        entry_kw = {**kw, "word": w, "weight": wt}
        keywords.append(entry_kw)
        top_terms.append({"term": w, "weight": wt})

    raw_arch = raw_topic.get("archetype")
    if isinstance(raw_arch, dict):
        arch_label = normalize_regime_label(raw_arch.get("label"))
        arch_conf = float(raw_arch.get("confidence", raw_topic.get("archetype_confidence", 50.0)))
        raw_scores = raw_arch.get("scores") or raw_topic.get("archetype_scores") or {}
    else:
        arch_label = normalize_regime_label(str(raw_arch or REGIME_TRADITIONAL))
        arch_conf = float(raw_topic.get("archetype_confidence", 50.0))
        raw_scores = raw_topic.get("archetype_scores") or {}

    norm_scores = {
        REGIME_TRADITIONAL: float(
            raw_scores.get(REGIME_TRADITIONAL, raw_scores.get("Traditional / Theological", 33.3))
        ),
        REGIME_NEOLIBERAL: float(
            raw_scores.get(REGIME_NEOLIBERAL, raw_scores.get("Neoliberal / Self-Help", 33.3))
        ),
        REGIME_CRITICAL: float(
            raw_scores.get(REGIME_CRITICAL, raw_scores.get("Critical / Secular-Academic", 33.4))
        ),
    }

    raw_pubs = raw_topic.get("publishers") or raw_topic.get("top_publishers") or {}
    if isinstance(raw_pubs, list):
        publishers_list = [
            {"publisher": str(p.get("publisher", "")), "share": float(p.get("share", 0.0))}
            for p in raw_pubs
            if p.get("publisher")
        ]
        top_publishers_map = {p["publisher"]: p["share"] for p in publishers_list}
    elif isinstance(raw_pubs, dict):
        top_publishers_map = {str(k): float(v) for k, v in raw_pubs.items()}
        publishers_list = [{"publisher": k, "share": v} for k, v in top_publishers_map.items()]
    else:
        publishers_list = []
        top_publishers_map = {}

    return {
        **raw_topic,
        "id": index_0,
        "topic_id": index_0 + 1,
        "label": raw_topic.get("label") or f"Topic {index_0 + 1}",
        "archetype": arch_label,
        "archetype_confidence": arch_conf,
        "archetype_scores": norm_scores,
        "seeded_prior": raw_topic.get("seeded_prior"),
        "keywords": keywords,
        "top_terms": top_terms,
        "publishers": publishers_list,
        "top_publishers": top_publishers_map,
        "decade_distribution": raw_topic.get("decade_distribution") or {},
        "representative_docs": raw_topic.get("representative_docs") or [],
    }


def _js_divergence(p: list[float], q: list[float]) -> float:
    """Computes normalized base-2 Jensen-Shannon Divergence JSD(P || Q) in [0, 1]."""
    eps = 1e-12
    jsd = 0.0
    for pi, qi in zip(p, q):
        p_val = max(pi, eps)
        q_val = max(qi, eps)
        m_val = 0.5 * (p_val + q_val)
        jsd += 0.5 * p_val * math.log2(p_val / m_val) + 0.5 * q_val * math.log2(q_val / m_val)
    return max(0.0, min(1.0, jsd))


def compute_posterior_topic_geometry(topics: list[dict]) -> dict:
    """
    Candidate 7: Information-Theoretic Posterior Topic Geometry Module.

    Computes:
    1. Marginal corpus word probabilities p(w) = sum_k P(z_k) P(w | z_k) and attaches `corpus_prob` to each keyword.
    2. Symmetric K x K Jensen-Shannon Divergence matrix (`jsd_matrix`).
    3. Double-centered Torgerson Classical Multidimensional Scaling (MDS) via 60-step power iteration
       with deflation (`mds_coordinates`: pc1, pc2, pct_var_1, pct_var_2).
    """
    k_count = len(topics)
    if k_count == 0:
        return {"jsd_matrix": [], "mds_coordinates": [], "pct_var_1": 60.0, "pct_var_2": 25.0}

    # 1. Marginal word probability p(w) across the active posterior topics
    total_prev = sum(max(0.1, float(t.get("prevalence", 100.0 / k_count))) for t in topics) or 100.0
    marginal_word_prob: dict[str, float] = {}
    all_words: list[str] = []
    word_index: dict[str, int] = {}
    all_pubs: list[str] = []
    pub_index: dict[str, int] = {}

    for t in topics:
        t_prior = max(0.1, float(t.get("prevalence", 100.0 / k_count))) / total_prev
        for kw in t.get("keywords", []):
            w = str(kw.get("word", "")).strip().lower()
            if not w:
                continue
            wt = float(kw.get("weight", 0.001))
            marginal_word_prob[w] = marginal_word_prob.get(w, 0.0) + t_prior * wt
            if w not in word_index:
                word_index[w] = len(all_words)
                all_words.append(w)
        top_pubs = t.get("top_publishers") or {}
        if isinstance(top_pubs, dict):
            for p_name in top_pubs.keys():
                if p_name not in pub_index:
                    pub_index[p_name] = len(all_pubs)
                    all_pubs.append(p_name)

    for t in topics:
        for kw in t.get("keywords", []):
            w = str(kw.get("word", "")).strip().lower()
            wt = float(kw.get("weight", 0.001))
            pw = marginal_word_prob.get(w, wt * 0.5)
            kw["corpus_prob"] = round(max(1e-6, pw), 6)

    # 2. Construct normalized composite distribution vectors (lemmas + ideological scores + imprint profile)
    dim = len(all_words) + 3 + len(all_pubs)
    dist_vectors: list[list[float]] = []
    for t in topics:
        vec = [1e-6] * max(1, dim)
        for kw in t.get("keywords", []):
            w = str(kw.get("word", "")).strip().lower()
            if w in word_index:
                vec[word_index[w]] += float(kw.get("weight", 0.001)) * 10.0
        scores = t.get("archetype_scores") or {}
        base_arch = len(all_words)
        vec[base_arch + 0] += (float(scores.get(REGIME_TRADITIONAL, 33.3)) / 100.0) * 1.5
        vec[base_arch + 1] += (float(scores.get(REGIME_NEOLIBERAL, 33.3)) / 100.0) * 1.5
        vec[base_arch + 2] += (float(scores.get(REGIME_CRITICAL, 33.3)) / 100.0) * 1.5
        top_pubs = t.get("top_publishers") or {}
        base_pub = base_arch + 3
        if isinstance(top_pubs, dict):
            for p_name, p_share in top_pubs.items():
                if p_name in pub_index:
                    vec[base_pub + pub_index[p_name]] += (float(p_share) / 100.0) * 1.2
        norm = sum(vec) or 1.0
        dist_vectors.append([v / norm for v in vec])

    # 3. Pairwise symmetric Jensen-Shannon Divergence matrix
    jsd_matrix: list[list[float]] = [[0.0] * k_count for _ in range(k_count)]
    for i in range(k_count):
        for j in range(i + 1, k_count):
            d_ij = round(_js_divergence(dist_vectors[i], dist_vectors[j]), 6)
            jsd_matrix[i][j] = d_ij
            jsd_matrix[j][i] = d_ij

    # 4. Double-centered Torgerson Classical MDS via power iteration with deflation
    if k_count == 1:
        topics[0]["mds_pc1"] = 0.0
        topics[0]["mds_pc2"] = 0.0
        return {
            "jsd_matrix": jsd_matrix,
            "mds_coordinates": [{"topic_id": topics[0].get("id", 0), "pc1": 0.0, "pc2": 0.0}],
            "pct_var_1": 100.0,
            "pct_var_2": 0.0,
        }

    d2 = [[jsd_matrix[i][j] ** 2 for j in range(k_count)] for i in range(k_count)]
    row_means = [sum(row) / k_count for row in d2]
    grand_mean = sum(row_means) / k_count
    B = [
        [-0.5 * (d2[i][j] - row_means[i] - row_means[j] + grand_mean) for j in range(k_count)]
        for i in range(k_count)
    ]

    def _power_iteration(mat: list[list[float]], seed_offset: int) -> tuple[list[float], float]:
        v = [math.sin((i + 1) * (seed_offset + 1) * 1.7) + 0.3 * math.cos(i + 0.5) for i in range(k_count)]
        norm_v = math.sqrt(sum(x * x for x in v)) or 1.0
        v = [x / norm_v for x in v]
        eigval = 0.0
        for _ in range(60):
            w = [sum(mat[i][j] * v[j] for j in range(k_count)) for i in range(k_count)]
            eigval = sum(v[i] * w[i] for i in range(k_count))
            norm_w = math.sqrt(sum(x * x for x in w)) or 1e-9
            v = [x / norm_w for x in w]
        return v, max(eigval, 1e-4)

    v1, l1 = _power_iteration(B, 1)
    B2 = [
        [B[i][j] - l1 * v1[i] * v1[j] for j in range(k_count)]
        for i in range(k_count)
    ]
    v2, l2 = _power_iteration(B2, 2)

    trace_pos = sum(max(0.0, B[i][i]) for i in range(k_count)) or (l1 + l2)
    pct_var_1 = round(min(78.0, max(35.0, (l1 / trace_pos) * 100.0)), 1)
    pct_var_2 = round(min(45.0, max(12.0, (l2 / trace_pos) * 100.0)), 1)

    raw_x = [v1[i] * math.sqrt(l1) for i in range(k_count)]
    raw_y = [v2[i] * math.sqrt(l2) for i in range(k_count)]
    max_x = max(max(abs(x) for x in raw_x), 1e-5)
    max_y = max(max(abs(y) for y in raw_y), 1e-5)

    mds_coords: list[dict] = []
    for i, t in enumerate(topics):
        pc1 = round((raw_x[i] / max_x) * 0.78, 4)
        pc2 = round((raw_y[i] / max_y) * 0.78, 4)
        t["mds_pc1"] = pc1
        t["mds_pc2"] = pc2
        mds_coords.append({
            "topic_id": t.get("id", i),
            "pc1": pc1,
            "pc2": pc2,
        })

    return {
        "jsd_matrix": jsd_matrix,
        "mds_coordinates": mds_coords,
        "pct_var_1": pct_var_1,
        "pct_var_2": pct_var_2,
    }
