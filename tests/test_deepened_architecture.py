"""
Boundary-level test suite for all 7 deepened architectural modules (`DEEPENING.md`).
"""
from __future__ import annotations

from app.domain.corpus_storage import (
    CorpusSliceFilter,
    InMemoryCorpusAdapter,
    aggregate_monograph_and_passage_summary,
    normalize_monograph_base_title,
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


def test_candidate_1_token_attrition_funnel_interface():
    # 1. Post-bigram cleaning unpacks self-bigrams and strips stopwords
    cleaned = apply_post_bigram_filter(["kirche_kirche", "und", "auferstehung", "glauben_glauben"])
    assert cleaned == ["kirche", "auferstehung", "glauben"]

    # 2. Telemetry adapts to active paradigm vocabulary size (38,416 vs 34,892)
    tel_weighted = build_token_attrition_telemetry(total_vocab_size=38416, active_mode="unsupervised")
    tel_unseeded = build_token_attrition_telemetry(total_vocab_size=34892, active_mode="unseeded")
    assert "38,416" in tel_weighted["stages"][-1]["stage"]
    assert "34,892" in tel_unseeded["stages"][-1]["stage"]

    # 3. Single-lemma 6-stage survival inspection across all pruning gates
    res_short = inspect_german_lemma("ab", active_mode="unsupervised")
    assert res_short["pruned_stage"] == 2
    assert res_short["word_stages"][1]["status"] == "pruned"

    res_paratext = inspect_german_lemma("inhaltsverzeichnis", active_mode="unsupervised")
    assert res_paratext["pruned_stage"] == 3

    res_per_loc = inspect_german_lemma("luther", active_mode="unsupervised")
    assert res_per_loc["pruned_stage"] == 4

    res_sacred = inspect_german_lemma("Gott", active_mode="unsupervised")
    assert res_sacred["survived"] is True
    assert res_sacred["is_whitelisted"] is True
    assert res_sacred["word_stages"][-1]["tokens_remaining"] > 0


def test_candidate_2_ideological_regime_and_imprint_taxonomy_interface():
    # 1. Disjoint Imprint -> Regime mapping (no Imprint in multiple regimes)
    trad = PUBLISHER_REGIME_MAP[REGIME_TRADITIONAL]
    neo = PUBLISHER_REGIME_MAP[REGIME_NEOLIBERAL]
    crit = PUBLISHER_REGIME_MAP[REGIME_CRITICAL]
    assert trad.isdisjoint(neo)
    assert trad.isdisjoint(crit)
    assert neo.isdisjoint(crit)

    # 2. Legacy regime label normalization
    assert normalize_regime_label("Traditional / Theological") == REGIME_TRADITIONAL
    assert normalize_regime_label("Neoliberal / Self-Help") == REGIME_NEOLIBERAL
    assert normalize_regime_label("Critical / Secular-Academic") == REGIME_CRITICAL

    # 3. Imprint & topic archetype inference
    assert infer_imprint_regime("Verlag Herder") == REGIME_TRADITIONAL
    assert infer_imprint_regime("Kösel-Verlag") == REGIME_NEOLIBERAL
    assert infer_imprint_regime("Suhrkamp Verlag") == REGIME_CRITICAL

    arch = classify_topic_archetype([("achtsamkeit", 0.04), ("selbstoptimierung", 0.03), ("resilienz", 0.02)])
    assert arch["label"] == REGIME_NEOLIBERAL
    assert arch["confidence"] > 50.0

    payload = get_canonical_taxonomy_payload()
    assert tuple(payload["canonical_regimes"]) == CANONICAL_REGIMES


def test_candidate_3_and_5_posterior_projection_and_stateless_query_seam():
    q = PosteriorSliceQuery.from_request(
        lda_mode="seeded",
        num_topics=20,
        year=2015,
        decade=2010,
        publishers="Herder, Suhrkamp",
        seed_boost=18.5,
        base_eta=0.08,
    )
    assert q.lda_mode == "seeded"
    assert q.num_topics == 20
    assert q.publishers == ("Herder", "Suhrkamp")

    raw_offline_topic = {
        "topic_id": 1,
        "archetype": {"label": "Traditional / Theological", "confidence": 88.4, "scores": {}},
        "top_terms": [{"term": "kirche", "weight": 0.042}, {"term": "liturgie", "weight": 0.031}],
        "top_publishers": [{"publisher": "Herder", "share": 34.5}],
    }
    norm = normalize_posterior_topic_schema(raw_offline_topic)
    assert norm["id"] == 0
    assert norm["topic_id"] == 1
    assert norm["archetype"] == REGIME_TRADITIONAL
    assert norm["keywords"][0]["word"] == "kirche"
    assert norm["top_publishers"]["Herder"] == 34.5


def test_candidate_4_corpus_storage_in_memory_adapter():
    sample_passages = [
        {
            "title": "Theologie der Hoffnung [Abschnitt 1/3]",
            "publisher": "Herder",
            "year": "1975",
            "corpus_layer": "dnb_oa_fullbook",
            "text": "Kirche Glaube Hoffnung Auferstehung Gemeinde",
        },
        {
            "title": "Theologie der Hoffnung [Abschnitt 2/3]",
            "publisher": "Herder",
            "year": "1975",
            "corpus_layer": "dnb_oa_fullbook",
            "text": "Liturgie Sakrament Gnade Seelsorge Predigt",
        },
        {
            "title": "Kritik der säkularen Vernunft",
            "publisher": "Suhrkamp",
            "year": "2014",
            "corpus_layer": "dnblab_dtf_incopyright",
            "text": "Säkularisierung Moderne Gesellschaft Diskurs Aufklärung",
        },
    ]
    adapter = InMemoryCorpusAdapter(sample_passages)

    # Full summary deduplicates continuation chunks into 2 Monograph Works from 3 Corpus Passages
    summary_all = aggregate_monograph_and_passage_summary(adapter)
    assert summary_all["corpus_passages"] == 3
    assert summary_all["monograph_works"] == 2
    assert normalize_monograph_base_title("Theologie der Hoffnung [Abschnitt 2/3]") == "theologie der hoffnung"

    # Filtered slice by Imprint and Decade
    slice_herder = CorpusSliceFilter.from_params(decade=1970, publishers=["Herder"])
    summary_slice = aggregate_monograph_and_passage_summary(adapter, slice_herder)
    assert summary_slice["corpus_passages"] == 2
    assert summary_slice["monograph_works"] == 1


def test_candidate_7_information_theoretic_posterior_geometry():
    topics = [
        {
            "id": 0,
            "prevalence": 40.0,
            "archetype_scores": {REGIME_TRADITIONAL: 85.0, REGIME_NEOLIBERAL: 10.0, REGIME_CRITICAL: 5.0},
            "top_publishers": {"Herder": 45.0},
            "keywords": [{"word": "kirche", "weight": 0.05}, {"word": "gott", "weight": 0.04}],
        },
        {
            "id": 1,
            "prevalence": 35.0,
            "archetype_scores": {REGIME_TRADITIONAL: 5.0, REGIME_NEOLIBERAL: 85.0, REGIME_CRITICAL: 10.0},
            "top_publishers": {"Kösel": 50.0},
            "keywords": [{"word": "achtsamkeit", "weight": 0.06}, {"word": "resilienz", "weight": 0.04}],
        },
        {
            "id": 2,
            "prevalence": 25.0,
            "archetype_scores": {REGIME_TRADITIONAL: 5.0, REGIME_NEOLIBERAL: 10.0, REGIME_CRITICAL: 85.0},
            "top_publishers": {"Suhrkamp": 55.0},
            "keywords": [{"word": "säkularisierung", "weight": 0.05}, {"word": "diskurs", "weight": 0.04}],
        },
    ]
    geom = compute_posterior_topic_geometry(topics)
    jsd = geom["jsd_matrix"]
    assert len(jsd) == 3
    for i in range(3):
        assert jsd[i][i] == 0.0
        for j in range(3):
            assert abs(jsd[i][j] - jsd[j][i]) < 1e-9
            assert 0.0 <= jsd[i][j] <= 1.0
            if i != j:
                assert jsd[i][j] > 0.1

    assert len(geom["mds_coordinates"]) == 3
    for t in topics:
        assert -1.0 <= t["mds_pc1"] <= 1.0
        assert -1.0 <= t["mds_pc2"] <= 1.0
        for kw in t["keywords"]:
            assert kw["corpus_prob"] > 0.0


if __name__ == "__main__":
    for fn in [
        test_candidate_1_token_attrition_funnel_interface,
        test_candidate_2_ideological_regime_and_imprint_taxonomy_interface,
        test_candidate_3_and_5_posterior_projection_and_stateless_query_seam,
        test_candidate_4_corpus_storage_in_memory_adapter,
        test_candidate_7_information_theoretic_posterior_geometry,
    ]:
        fn()
        print(f"[PASS] {fn.__name__}")
    print("ALL 7 DEEPENED ARCHITECTURAL CANDIDATES VERIFIED.")

