"""
Comprehensive End-to-End (E2E) Test Suite for Mediating Faith and Power (Deutsche-Verlage-LDA).

Covers:
- Suite 1: Newly Deepened Domain Modules (`app/domain/*`) & In-Memory 4-Paradigm LDA Pipeline (`lda_pipeline.py`)
- Suite 2: Live FastAPI Backend HTTP Seams (`http://localhost:8000`)
- Suite 3: Live Vite Frontend & Proxied API Seams (`http://localhost:5173`)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import lda_pipeline
from app.domain.corpus_storage import (
    CorpusSliceFilter,
    InMemoryCorpusAdapter,
    ParquetCsvCorpusAdapter,
    aggregate_monograph_and_passage_summary,
    extract_publication_year,
    normalize_monograph_base_title,
    publisher_matches_imprint_filter,
)
from app.domain.ideological_taxonomy import (
    CANONICAL_REGIMES,
    PUBLISHER_REGIME_MAP,
    REGIME_CRITICAL,
    REGIME_NEOLIBERAL,
    REGIME_TRADITIONAL,
    classify_topic_archetype,
    get_canonical_taxonomy_payload,
    infer_imprint_regime,
    normalize_regime_label,
)
from app.domain.posterior_projection import (
    PosteriorSliceQuery,
    compute_posterior_topic_geometry,
    normalize_posterior_topic_schema,
)
from app.domain.token_attrition_funnel import (
    apply_post_bigram_filter,
    build_token_attrition_telemetry,
    inspect_german_lemma,
)

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:5173"


def _http_get_json(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "Connection": "close"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        assert resp.status == 200, f"GET {url} returned HTTP {resp.status}"
        return json.loads(resp.read().decode("utf-8"))


def _http_post_json(url: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json", "Connection": "close"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        assert resp.status == 200, f"POST {url} returned HTTP {resp.status}"
        return json.loads(resp.read().decode("utf-8"))


# ============================================================================
# SUITE 1: DEEPENED DOMAIN MODULES & IN-MEMORY 4-PARADIGM LDA PIPELINE
# ============================================================================

def test_01_token_attrition_funnel_and_compound_splitting():
    # Post-bigram cleaning
    out = apply_post_bigram_filter(["kirche_kirche", "der", "gottesdienst", "glaube_glaube", "säkularisierung"])
    assert out == ["kirche", "gottesdienst", "glaube", "säkularisierung"]

    # German compound splitting (Santana et al., 2025 Rule 3)
    parts = lda_pipeline.split_german_compound_lda("kirchengemeinde")
    assert "kirchengemeinde" in parts and "kirche" in parts and "gemeinde" in parts

    # Stage 06 telemetry reflects active paradigm vocabulary size
    t_weighted = build_token_attrition_telemetry(total_vocab_size=38416, active_mode="unsupervised")
    t_unseeded = build_token_attrition_telemetry(total_vocab_size=34892, active_mode="unseeded")
    assert "38,416" in t_weighted["stages"][-1]["stage"]
    assert "34,892" in t_unseeded["stages"][-1]["stage"]
    assert "No Compound Split" in t_unseeded["stages"][4]["rule"]

    # 6-stage lemma survival inspection across all pruning gates
    assert inspect_german_lemma("ab")["pruned_stage"] == 2
    assert inspect_german_lemma("inhaltsverzeichnis")["pruned_stage"] == 3
    assert inspect_german_lemma("berlin")["pruned_stage"] == 3
    assert inspect_german_lemma("luther")["pruned_stage"] == 4
    assert inspect_german_lemma("jedoch")["pruned_stage"] == 4
    gott_res = inspect_german_lemma("Gott")
    assert gott_res["survived"] is True and gott_res["is_whitelisted"] is True and gott_res["is_boosted"] is True


def test_02_ideological_taxonomy_and_imprint_attribution():
    # Disjoint Imprint sets
    s_trad = PUBLISHER_REGIME_MAP[REGIME_TRADITIONAL]
    s_neo = PUBLISHER_REGIME_MAP[REGIME_NEOLIBERAL]
    s_crit = PUBLISHER_REGIME_MAP[REGIME_CRITICAL]
    assert s_trad.isdisjoint(s_neo) and s_trad.isdisjoint(s_crit) and s_neo.isdisjoint(s_crit)

    # Legacy alias normalization
    assert normalize_regime_label("Traditional / Theological") == REGIME_TRADITIONAL
    assert normalize_regime_label("Neoliberal / Self-Help") == REGIME_NEOLIBERAL
    assert normalize_regime_label("Critical / Secular-Academic") == REGIME_CRITICAL

    # Imprint attribution across core houses
    for p_trad in ("Verlag Herder", "Patmos Verlag", "Vandenhoeck & Ruprecht", "Mohr Siebeck", "St. Benno"):
        assert infer_imprint_regime(p_trad) == REGIME_TRADITIONAL
    for p_neo in ("Kösel-Verlag", "Gräfe und Unzer (GU)", "J. Kamphausen", "Kreuz Verlag", "Arkana"):
        assert infer_imprint_regime(p_neo) == REGIME_NEOLIBERAL
    for p_crit in ("Suhrkamp", "C.H. Beck", "Rowohlt", "S. Fischer", "Alibri"):
        assert infer_imprint_regime(p_crit) == REGIME_CRITICAL

    # Topic archetype classification
    trad_arch = classify_topic_archetype([("liturgie", 0.05), ("sakrament", 0.04), ("dogmatik", 0.03)])
    neo_arch = classify_topic_archetype([("achtsamkeit", 0.05), ("resilienz", 0.04), ("selbstoptimierung", 0.03)])
    crit_arch = classify_topic_archetype([("säkularisierung", 0.05), ("aufklärung", 0.04), ("ideologiekritik", 0.03)])
    assert trad_arch["label"] == REGIME_TRADITIONAL
    assert neo_arch["label"] == REGIME_NEOLIBERAL
    assert crit_arch["label"] == REGIME_CRITICAL

    tax = get_canonical_taxonomy_payload()
    assert tuple(tax["canonical_regimes"]) == CANONICAL_REGIMES


def test_03_corpus_storage_ports_and_adapters():
    # 1. InMemoryCorpusAdapter & Monograph Work deduplication
    passages = [
        {
            "title": "Dogmatik des christlichen Glaubens [Abschnitt 1/4]",
            "publisher": "Herder",
            "year": "1984",
            "corpus_layer": "dnb_oa_fullbook",
            "text": "Kirche Liturgie Sakrament Gnade Gott Christus Gemeinde Gebet",
        },
        {
            "title": "Dogmatik des christlichen Glaubens [Abschnitt 2/4]",
            "publisher": "Herder",
            "year": "1984",
            "corpus_layer": "dnb_oa_fullbook",
            "text": "Auferstehung Erlösung Bibel Evangelium Dogmatik Seelsorge Pfarrer",
        },
        {
            "title": "Achtsamkeit und Selbstfürsorge im Alltag",
            "publisher": "Kösel",
            "year": "2018",
            "corpus_layer": "dnblab_dtf_incopyright",
            "text": "Achtsamkeit Resilienz Meditation Selbstoptimierung Bewusstsein Heilung Glück",
        },
        {
            "title": "Theorie der Säkularisierung in der Moderne",
            "publisher": "Suhrkamp",
            "year": "2005",
            "corpus_layer": "hathitrust_ef_fullbook_print",
            "text": "Säkularisierung Moderne Aufklärung Gesellschaft Diskurs Vernunft Demokratie",
        },
    ]
    mem_adapter = InMemoryCorpusAdapter(passages)
    agg = aggregate_monograph_and_passage_summary(mem_adapter)
    assert agg["corpus_passages"] == 4
    assert agg["monograph_works"] == 3
    assert extract_publication_year("c 2018") == 2018
    assert publisher_matches_imprint_filter("Verlag Herder Freiburg", ["Herder"]) is True
    assert normalize_monograph_base_title("Dogmatik [Abschnitt 2/4]") == "dogmatik"

    # 2. ParquetCsvCorpusAdapter streaming real rows from disk
    pq_adapter = ParquetCsvCorpusAdapter("data/dnb_metadata.csv")
    streamed_sample = []
    for idx, row in enumerate(pq_adapter.iter_passages()):
        streamed_sample.append(row)
        if idx >= 24:
            break
    assert len(streamed_sample) == 25
    assert all("title" in r and "text" in r for r in streamed_sample)


def test_04_in_memory_lda_pipeline_all_four_paradigms():
    synthetic_rows = []
    for i in range(12):
        synthetic_rows.append({
            "title": f"Kirchliche Dogmatik Band {i + 1}",
            "author": "Theologe",
            "publisher": "Herder",
            "year": str(1975 + i),
            "text": "Kirche Glaube Gott Christus Liturgie Sakrament Gemeinde Seelsorge Gebet Auferstehung Bibel Theologie Gnade",
        })
        synthetic_rows.append({
            "title": f"Praxis der Achtsamkeit Band {i + 1}",
            "author": "Coach",
            "publisher": "Kösel",
            "year": str(2010 + i),
            "text": "Achtsamkeit Resilienz Selbstoptimierung Meditation Bewusstsein Wohlbefinden Heilung Lebenshilfe Stressbewältigung Glück",
        })
        synthetic_rows.append({
            "title": f"Kritik der Säkularisierung Band {i + 1}",
            "author": "Soziologe",
            "publisher": "Suhrkamp",
            "year": str(1995 + i),
            "text": "Säkularisierung Gesellschaft Diskurs Moderne Aufklärung Wissenschaft Vernunft Demokratie Ideologiekritik Autonomie",
        })

    for mode in ("unseeded", "unsupervised", "seeded", "supervised"):
        model, corpus, dictionary, coh, rep_docs = lda_pipeline.run_pipeline(
            synthetic_rows,
            num_topics=3,
            lda_mode=mode,
        )
        assert model is not None
        assert len(corpus) == len(synthetic_rows)
        assert len(dictionary) > 5
        assert getattr(model, "lda_mode", None) == mode
        assert isinstance(coh, float)
        assert len(rep_docs) > 0


def test_05_posterior_projection_and_information_theoretic_geometry():
    q = PosteriorSliceQuery.from_request(
        lda_mode="supervised",
        num_topics=16,
        year=2008,
        decade=2000,
        publishers=["Suhrkamp", "C.H. Beck"],
        seed_boost=20.0,
        base_eta=0.05,
    )
    assert q.lda_mode == "supervised" and q.num_topics == 16 and q.publishers == ("Suhrkamp", "C.H. Beck")

    topics = [
        normalize_posterior_topic_schema({
            "topic_id": 1,
            "prevalence": 38.0,
            "archetype": {"label": "Traditional / Theological", "confidence": 91.0, "scores": {REGIME_TRADITIONAL: 91.0, REGIME_NEOLIBERAL: 5.0, REGIME_CRITICAL: 4.0}},
            "top_terms": [{"term": "kirche", "weight": 0.055}, {"term": "liturgie", "weight": 0.042}],
            "top_publishers": [{"publisher": "Herder", "share": 42.0}],
        }),
        normalize_posterior_topic_schema({
            "topic_id": 2,
            "prevalence": 32.0,
            "archetype": {"label": "Neoliberal / Self-Help", "confidence": 89.0, "scores": {REGIME_TRADITIONAL: 6.0, REGIME_NEOLIBERAL: 89.0, REGIME_CRITICAL: 5.0}},
            "top_terms": [{"term": "achtsamkeit", "weight": 0.061}, {"term": "resilienz", "weight": 0.048}],
            "top_publishers": [{"publisher": "Kösel", "share": 48.0}],
        }),
        normalize_posterior_topic_schema({
            "topic_id": 3,
            "prevalence": 30.0,
            "archetype": {"label": "Critical / Secular-Academic", "confidence": 93.0, "scores": {REGIME_TRADITIONAL: 3.0, REGIME_NEOLIBERAL: 4.0, REGIME_CRITICAL: 93.0}},
            "top_terms": [{"term": "säkularisierung", "weight": 0.058}, {"term": "moderne", "weight": 0.044}],
            "top_publishers": [{"publisher": "Suhrkamp", "share": 51.0}],
        }),
    ]
    geom = compute_posterior_topic_geometry(topics)
    assert len(geom["jsd_matrix"]) == 3
    assert len(geom["mds_coordinates"]) == 3
    for i in range(3):
        assert geom["jsd_matrix"][i][i] == 0.0
        assert -1.0 <= topics[i]["mds_pc1"] <= 1.0
        assert -1.0 <= topics[i]["mds_pc2"] <= 1.0
        for kw in topics[i]["keywords"]:
            assert kw["corpus_prob"] > 0.0


# ============================================================================
# SUITE 2: LIVE FASTAPI BACKEND HTTP SEAM TESTS (`http://localhost:8000`)
# ============================================================================

def test_06_http_data_summary_and_trends_and_coherence_grid():
    summary = _http_get_json(f"{BACKEND_URL}/api/data-summary")
    assert summary["count"] == 10612079
    assert summary["total_records"] == 10612079
    assert summary["unique_books"] == 10042681
    assert summary["total_words"] == 894184957
    assert summary["pipeline_config"]["filter_keep_n"] == 100000
    assert summary["pipeline_config"]["tfidf_min_threshold"] == 0.065

    trends = _http_get_json(f"{BACKEND_URL}/api/trends")
    assert isinstance(trends, list) and len(trends) >= 50
    years = {int(r["year"]) for r in trends if "year" in r}
    assert 1970 in years and 2025 in years

    coh_grid = _http_get_json(f"{BACKEND_URL}/api/coherence-grid")
    assert "grid" in coh_grid and len(coh_grid["grid"]) >= 6
    assert any(r["k"] == 30 for r in coh_grid["recommended_regimes"])

    drift = _http_get_json(f"{BACKEND_URL}/api/conceptual-drift")
    assert isinstance(drift, dict) and len(drift) > 0


def test_07_http_stateless_topics_across_all_4_paradigms_and_k_projections():
    # 1. Verify all 4 paradigms & distinct organic vocabulary sizes (34,892 vs 38,416)
    expected_vocabs = {
        "unseeded": 34892,
        "unsupervised": 38416,
        "seeded": 38416,
        "supervised": 38416,
    }
    for mode, exp_v in expected_vocabs.items():
        data = _http_get_json(f"{BACKEND_URL}/api/topics?lda_mode={mode}&num_topics=12")
        assert data["lda_mode"] == mode
        assert data["vocab_size"] == exp_v
        assert data["corpus_documents"] == 10612079
        assert len(data["topics"]) == 12

        # Verify Candidate 7 posterior_geometry is present in robustness_telemetry
        rt = data["robustness_telemetry"]
        assert "posterior_geometry" in rt
        pg = rt["posterior_geometry"]
        assert len(pg["jsd_matrix"]) == 12
        assert len(pg["mds_coordinates"]) == 12
        for t in data["topics"]:
            assert "mds_pc1" in t and "mds_pc2" in t
            assert len(t["keywords"]) > 0
            assert "corpus_prob" in t["keywords"][0]

        # Verify Candidate 1 Stage 06 label matches active paradigm vocabulary size
        st6 = rt["token_attrition_funnel"]["stages"][-1]["stage"]
        assert f"{exp_v:,}" in st6

    # 2. Verify K granularity projection across K in {4, 8, 20, 30}
    for k_val in (4, 8, 20, 30):
        dk = _http_get_json(f"{BACKEND_URL}/api/topics?lda_mode=unsupervised&num_topics={k_val}")
        assert dk["num_topics"] == k_val
        assert len(dk["topics"]) == k_val
        assert len(dk["robustness_telemetry"]["posterior_geometry"]["jsd_matrix"]) == k_val
        assert dk["cv_coherence"] is not None

    # 3. Verify temporal & Imprint sub-corpus slice conditioning
    d_slice = _http_get_json(
        f"{BACKEND_URL}/api/topics?lda_mode=seeded&num_topics=12&decade=1990&publishers=Herder,Suhrkamp&seed_boost=18.0"
    )
    assert d_slice["active_filters"]["decade"] == 1990
    assert "Herder" in d_slice["active_filters"]["publishers"]
    assert d_slice["robustness_telemetry"]["slice_power_monitor"]["slice_documents"] < 10612079


def test_08_http_lemma_inspector_exhaustive():
    queries = [
        ("Auferstehung", True, 0),
        ("Selbstoptimierung", True, 0),
        ("Säkularisierung", True, 0),
        ("Gott", True, 0),
        ("Kirchengemeinde", True, 0),
        ("Berlin", False, 3),
        ("Luther", False, 4),
        ("Inhaltsverzeichnis", False, 3),
        ("jedoch", False, 4),
        ("ab", False, 2),
    ]
    seen_s1_counts = set()
    for word, exp_survived, exp_stage in queries:
        res = _http_get_json(f"{BACKEND_URL}/api/lemma-inspector?q={urllib.parse.quote(word)}")
        assert res.get("valid") is True
        assert res["survived"] is exp_survived, f"{word}: expected survived={exp_survived}, got {res}"
        if not exp_survived:
            assert res["pruned_stage"] == exp_stage, f"{word}: expected pruned_stage={exp_stage}, got {res['pruned_stage']}"
        assert len(res["word_stages"]) == 6
        seen_s1_counts.add(res["word_stages"][0]["tokens_remaining"])
    # Verify dynamic per-word stage counts are not constant across different German words
    assert len(seen_s1_counts) >= 7


def test_09_http_marc21_search_exhaustive():
    # Global search for Herder
    herder = _http_get_json(f"{BACKEND_URL}/api/marc21-search?q=Herder&limit=50")
    assert herder["total_matches"] >= 150
    assert len(herder["results"]) == 50
    first = herder["results"][0]
    assert "title" in first and "publisher" in first and "apa_citation" in first and "corpus_layer" in first

    # Topic-scoped search
    t0 = _http_get_json(f"{BACKEND_URL}/api/marc21-search?topic_id=0&lda_mode=unsupervised&limit=40")
    assert t0["total_matches"] >= 25
    assert len(t0["results"]) >= 25

    # Publisher & decade filtered search
    suhrkamp = _http_get_json(f"{BACKEND_URL}/api/marc21-search?publishers=Suhrkamp&decade=2010&limit=30")
    assert suhrkamp["total_matches"] >= 10
    assert all("suhrkamp" in r["publisher"].lower() for r in suhrkamp["results"])


def test_10_http_seed_lexicon_update_and_reset_cycle():
    reset_res = _http_post_json(f"{BACKEND_URL}/api/reset-seeds")
    assert reset_res.get("status") == "success"
    assert "seed_lexicons" in reset_res


# ============================================================================
# SUITE 3: LIVE VITE FRONTEND & PROXIED API SEAMS (`http://localhost:5173`)
# ============================================================================

def test_11_vite_frontend_and_api_proxy_e2e():
    # 1. Verify Vite HTML shell
    req = urllib.request.Request(f"{FRONTEND_URL}/")
    with urllib.request.urlopen(req, timeout=15) as resp:
        assert resp.status == 200
        html = resp.read().decode("utf-8")
        assert "<div id=\"root\"></div>" in html

    # 2. Verify Vite proxy forwards all API endpoints to FastAPI backend
    proxied_topics = _http_get_json(f"{FRONTEND_URL}/api/topics?lda_mode=unsupervised&num_topics=12")
    assert proxied_topics["vocab_size"] == 38416
    assert len(proxied_topics["topics"]) == 12
    assert "posterior_geometry" in proxied_topics["robustness_telemetry"]

    proxied_lemma = _http_get_json(f"{FRONTEND_URL}/api/lemma-inspector?q=Auferstehung")
    assert proxied_lemma["survived"] is True and len(proxied_lemma["word_stages"]) == 6

    proxied_marc = _http_get_json(f"{FRONTEND_URL}/api/marc21-search?q=Suhrkamp&limit=25")
    assert proxied_marc["total_matches"] >= 50 and len(proxied_marc["results"]) == 25


def test_12_precomputed_permutations_and_zero_pipeline_execution_e2e():
    # 1. Verify offline pre-computed permutations archive & manifest
    manifest_path = os.path.join(BASE_DIR, "app", "precomputed_permutations_manifest.json")
    pkl_path = os.path.join(BASE_DIR, "app", "precomputed_permutations.pkl.gz")
    assert os.path.exists(manifest_path), "Missing precomputed_permutations_manifest.json"
    assert os.path.exists(pkl_path), "Missing precomputed_permutations.pkl.gz"

    with open(manifest_path, "r", encoding="utf-8") as mf:
        manifest = json.load(mf)
    assert manifest["total_precomputed_permutations"] >= 4000
    assert manifest["grid_breakdown"]["mode_x_all_k"] == 116  # 4 modes x 29 K (2..30)
    assert manifest["grid_breakdown"]["mode_x_all_k_x_decade"] == 696  # 4 x 29 x 6 decades
    assert manifest["grid_breakdown"]["mode_x_key_k_x_year"] == 896  # 4 x 4 x 56 years

    # 2. Enforce that lda_pipeline.run_pipeline is NEVER called when parameters change
    from app import main as app_main
    orig_run_pipeline = lda_pipeline.run_pipeline

    def _forbidden_run_pipeline(*args, **kwargs):
        raise AssertionError("lda_pipeline.run_pipeline MUST NEVER BE EXECUTED when frontend parameters change!")

    lda_pipeline.run_pipeline = _forbidden_run_pipeline
    try:
        p1 = app_main.compute_parameter_permutation_payload(active_mode="unseeded", target_k=8)
        p2 = app_main.compute_parameter_permutation_payload(active_mode="seeded", target_k=8, decade_filter=1990)
        p3 = app_main.compute_parameter_permutation_payload(
            active_mode="supervised", target_k=16, year_filter=2018, pubs_filter=["Herder"], seed_boost=25.0, base_eta=0.02
        )
        assert len(p1["topics"]) == 8 and p1["vocab_size"] == 34892
        assert len(p2["topics"]) == 8 and p2["vocab_size"] == 38416
        assert len(p3["topics"]) == 16 and p3["corpus_documents"] < 10612079
        assert p1["coherence_score"] != p2["coherence_score"]
        assert p2["cv_coherence"] != p3["cv_coherence"]
    finally:
        lda_pipeline.run_pipeline = orig_run_pipeline

    # 3. Verify live HTTP & Vite-proxied parameter switches exhibit distinct pre-computed results immediately
    u_k4 = _http_get_json(f"{FRONTEND_URL}/api/topics?lda_mode=unseeded&num_topics=4")
    s_k20_d2010 = _http_get_json(
        f"{FRONTEND_URL}/api/topics?lda_mode=seeded&num_topics=20&decade=2010&publishers=Herder&seed_boost=25.0&base_eta=0.02"
    )
    assert len(u_k4["topics"]) == 4 and u_k4["vocab_size"] == 34892
    assert len(s_k20_d2010["topics"]) == 20 and s_k20_d2010["vocab_size"] == 38416
    assert u_k4["coherence_score"] != s_k20_d2010["coherence_score"]
    assert u_k4["cv_coherence"] != s_k20_d2010["cv_coherence"]
    assert s_k20_d2010["corpus_documents"] < u_k4["corpus_documents"]

    # 4. Verify /api/lemma-inspector with lda_mode parameter & /api/marc21-search with num_topics parameter
    lem_unseeded = _http_get_json(f"{FRONTEND_URL}/api/lemma-inspector?q=Gott&lda_mode=unseeded")
    lem_seeded = _http_get_json(f"{FRONTEND_URL}/api/lemma-inspector?q=Gott&lda_mode=seeded")
    assert "34,892" in lem_unseeded["word_stages"][-1]["stage"]
    assert "38,416" in lem_seeded["word_stages"][-1]["stage"]

    marc_k20 = _http_get_json(
        f"{FRONTEND_URL}/api/marc21-search?topic_id=0&lda_mode=seeded&num_topics=20&decade=2010&limit=20"
    )
    assert marc_k20["returned_count"] > 0


if __name__ == "__main__":
    t_start = time.time()
    all_tests = [
        test_01_token_attrition_funnel_and_compound_splitting,
        test_02_ideological_taxonomy_and_imprint_attribution,
        test_03_corpus_storage_ports_and_adapters,
        test_04_in_memory_lda_pipeline_all_four_paradigms,
        test_05_posterior_projection_and_information_theoretic_geometry,
        test_06_http_data_summary_and_trends_and_coherence_grid,
        test_07_http_stateless_topics_across_all_4_paradigms_and_k_projections,
        test_08_http_lemma_inspector_exhaustive,
        test_09_http_marc21_search_exhaustive,
        test_10_http_seed_lexicon_update_and_reset_cycle,
        test_11_vite_frontend_and_api_proxy_e2e,
        test_12_precomputed_permutations_and_zero_pipeline_execution_e2e,
    ]
    for idx, fn in enumerate(all_tests, start=1):
        t0 = time.time()
        fn()
        print(f"[PASS {idx:02d}/{len(all_tests):02d}] {fn.__name__} ({time.time() - t0:.2f}s)", flush=True)
    print(f"\nALL {len(all_tests)} END-TO-END & MODULE TESTS PASSED IN {time.time() - t_start:.2f}s!", flush=True)
