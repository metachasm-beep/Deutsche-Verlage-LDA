from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import csv
import re
import shutil
from collections import defaultdict
import lda_pipeline
import config

app = FastAPI(title="The Computational Turn: LDA Dashboard")

# CORS config to allow the Vercel deployed frontend and localhost testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000", "https://deutscheverlagelda.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to store the active model state
current_model = None
current_corpus = None
current_dictionary = None
current_coherence = 0.0
current_top_docs = {}
current_num_topics = config.NUM_TOPICS
current_lda_mode = "unsupervised"
current_year_filter = None
current_decade_filter = None
current_publishers_filter = []
current_custom_seeds = None
current_seed_boost = 15.0
current_base_eta = 0.05
current_viz_html = ""

# In-memory memoization cache for instant switching across (dataset, K, year, decade)
_MODEL_RUN_CACHE = {}

# Storage directory (uses /tmp/data on Vercel serverless, or data/ locally)
DATA_STORAGE_DIR = "/tmp/data" if os.environ.get("VERCEL") else os.path.join(config.BASE_DIR, "data")
os.makedirs(DATA_STORAGE_DIR, exist_ok=True)
REAL_DATA_PATH = os.path.join(DATA_STORAGE_DIR, "dnb_metadata.csv")

# Copy harvested DNB data to /tmp/data if running in Vercel serverless and not yet copied
if not os.path.exists(REAL_DATA_PATH) and os.path.exists(config.HARVEST_DATA_PATH):
    try:
        shutil.copy(config.HARVEST_DATA_PATH, REAL_DATA_PATH)
    except Exception:
        pass


def _get_active_data_path() -> str:
    if os.path.exists(REAL_DATA_PATH) and os.path.getsize(REAL_DATA_PATH) > 100:
        return REAL_DATA_PATH
    if os.path.exists(config.HARVEST_DATA_PATH) and os.path.getsize(config.HARVEST_DATA_PATH) > 100:
        return config.HARVEST_DATA_PATH
    return config.MOCK_DATA_PATH


def _load_coherence_grid():
    grid = []
    if os.path.exists(config.COHERENCE_GRID_PATH):
        try:
            with open(config.COHERENCE_GRID_PATH, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    grid.append({
                        "k": int(row["k"]),
                        "c_v": float(row["c_v"]),
                        "u_mass": float(row["u_mass"]),
                        "log_perplexity": float(row["log_perplexity"])
                    })
        except Exception:
            pass
    if not grid:
        summary_json_path = os.path.join(config.BASE_DIR, "app", "data_summary.json")
        if os.path.exists(summary_json_path):
            try:
                import json
                with open(summary_json_path, "r", encoding="utf-8") as sf:
                    sdata = json.load(sf)
                    grid = sdata.get("coherence_grid", [])
            except Exception:
                pass
    return grid


@app.get("/api/health")
async def health():
    return {"status": "ok", "mode": "PhD Research API Active"}


@app.get("/api/coherence-grid")
async def get_coherence_grid():
    """
    Returns the empirical hyperparameter optimization metrics (C_v, U_Mass, Log Perplexity)
    across K topics for rendering the interactive Coherence Optimization Curve.
    """
    grid = _load_coherence_grid()
    best_cv = max(grid, key=lambda x: x["c_v"])["k"] if grid else 30
    best_umass = max(grid, key=lambda x: x["u_mass"])["k"] if grid else 4
    return {
        "grid": grid,
        "recommended_regimes": [
            {"k": 4, "label": "Macro-Archetypes", "description": "Optimal U_Mass peak (3–4 Institutional Voices)"},
            {"k": 12, "label": "Meso-Inflection", "description": "Sub-disciplinary C_v inflection point"},
            {"k": 20, "label": "High-Resolution", "description": "Granular thematic differentiation"},
            {"k": 30, "label": "Micro-Thematic", "description": "Global C_v NPMI coherence peak"}
        ],
        "best_cv_k": best_cv,
        "best_umass_k": best_umass
    }


@app.post("/api/upload-dataset")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Receives a custom CSV dataset from the researcher.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        file_location = REAL_DATA_PATH
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

        with open(file_location, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            if not headers or "publisher" not in headers or "date" not in headers:
                os.remove(file_location)
                raise HTTPException(status_code=400, detail="CSV must contain 'publisher' and 'date' columns.")
            count = sum(1 for _ in reader)

        _MODEL_RUN_CACHE.clear()
        return {
            "status": "success",
            "message": f"Dataset {file.filename} ingested successfully, containing {count} records."
        }
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(REAL_DATA_PATH):
            os.remove(REAL_DATA_PATH)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reset-to-mock")
async def reset_to_mock():
    """
    Resets the model state and reloads the default DNB Harvest / Demo Corpus.
    """
    global current_model, current_corpus, current_dictionary, current_viz_html, current_coherence, current_top_docs, current_lda_mode, current_year_filter, current_decade_filter, current_publishers_filter

    try:
        current_model = None
        current_corpus = None
        current_dictionary = None
        current_coherence = 0.0
        current_top_docs = {}
        current_lda_mode = "unsupervised"
        current_year_filter = None
        current_decade_filter = None
        current_publishers_filter = []
        current_viz_html = ""
        _MODEL_RUN_CACHE.clear()
        return {"status": "success", "message": "Reverted to Default Research Corpus."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _load_modes_report_cache() -> dict:
    modes_path = os.path.join(config.BASE_DIR, "app", "lda_modes_report.json")
    if os.path.exists(modes_path):
        try:
            import json
            with open(modes_path, mode="r", encoding="utf-8") as mf:
                return json.load(mf)
        except Exception:
            pass
    return {}


def _publisher_matches_filter(pub_name: str, selected_pubs: list) -> bool:
    if not selected_pubs:
        return True
    p_low = (pub_name or "").lower().strip()
    for target in selected_pubs:
        t_low = target.lower().strip()
        if t_low and (t_low in p_low or p_low in t_low):
            return True
    return False


@app.post("/api/update-seeds")
async def update_seeds(payload: dict = Body(...)):
    global current_custom_seeds, current_seed_boost, current_base_eta
    if "seed_lexicons" in payload and isinstance(payload["seed_lexicons"], dict):
        current_custom_seeds = {
            k: [str(w).strip().lower() for w in v if str(w).strip()]
            for k, v in payload["seed_lexicons"].items()
            if isinstance(v, list)
        }
    if "seed_boost" in payload and payload["seed_boost"] is not None:
        current_seed_boost = float(payload["seed_boost"])
    if "base_eta" in payload and payload["base_eta"] is not None:
        current_base_eta = float(payload["base_eta"])
    return {
        "status": "success",
        "seed_lexicons": current_custom_seeds or {k: sorted(list(v)) for k, v in config.ARCHETYPE_LEXICONS.items()},
        "seed_boost": current_seed_boost,
        "base_eta": current_base_eta,
    }


@app.post("/api/reset-seeds")
async def reset_seeds():
    global current_custom_seeds, current_seed_boost, current_base_eta
    current_custom_seeds = None
    current_seed_boost = 15.0
    current_base_eta = 0.05
    return {
        "status": "success",
        "seed_lexicons": {k: sorted(list(v)) for k, v in config.ARCHETYPE_LEXICONS.items()},
        "seed_boost": current_seed_boost,
        "base_eta": current_base_eta,
    }


@app.post("/api/run-lda")
async def run_lda(
    year: int = Query(None),
    decade: int = Query(None),
    publishers: str = Query(None),
    num_topics: int = Query(None),
    lda_mode: str = Query("unsupervised"),
    seed_boost: float = Query(None),
    base_eta: float = Query(None),
):
    global current_model, current_corpus, current_dictionary, current_viz_html, current_coherence, current_top_docs, current_num_topics, current_lda_mode, current_year_filter, current_decade_filter, current_publishers_filter, current_seed_boost, current_base_eta

    mode_key = lda_mode if lda_mode in lda_pipeline.LDA_MODES_META else "unsupervised"
    current_lda_mode = mode_key
    current_year_filter = year
    current_decade_filter = decade
    parsed_pubs = [p.strip() for p in (publishers or "").split(",") if p.strip()]
    current_publishers_filter = parsed_pubs
    if seed_boost is not None:
        current_seed_boost = float(seed_boost)
    if base_eta is not None:
        current_base_eta = float(base_eta)

    data_path = _get_active_data_path()
    k_target = int(num_topics) if num_topics else config.NUM_TOPICS
    current_num_topics = k_target

    # Fast-path if full-corpus K=12 mode is precomputed in app/lda_modes_report.json (no filters) or running on Vercel serverless without gensim
    modes_cache = _load_modes_report_cache()
    if (
        (not year and not decade and not parsed_pubs and k_target == config.NUM_TOPICS and mode_key in modes_cache.get("modes", {}))
        or lda_pipeline.gensim is None
        or data_path == config.MOCK_DATA_PATH
        or not os.path.exists(data_path)
    ):
        current_model = None
        current_corpus = None
        return {
            "status": "success",
            "year_filtered": year,
            "decade_filtered": decade,
            "publishers_filtered": parsed_pubs,
            "num_topics": k_target,
            "lda_mode": mode_key,
            "seed_boost": current_seed_boost,
            "base_eta": current_base_eta,
            "cached": True
        }

    try:
        if year or decade or parsed_pubs:
            rows = []
            headers = None
            for row in lda_pipeline.iter_corpus_rows(data_path):
                if headers is None:
                    headers = list(row.keys())

                if parsed_pubs:
                    row_pub = lda_pipeline._clean_marc_control_chars(row.get("publisher") or "")
                    if not _publisher_matches_filter(row_pub, parsed_pubs):
                        continue

                if year or decade:
                    date_val = str(row.get("date", "") or row.get("year", ""))
                    match = re.search(r"(\d{4})", date_val)
                    if not match:
                        continue
                    r_year = int(match.group(1))

                    if year and r_year != year:
                        continue
                    if decade and not (decade <= r_year < decade + 10):
                        continue

                rows.append(row)

            if not rows:
                target_parts = []
                if year:
                    target_parts.append(f"year {year}")
                if decade:
                    target_parts.append(f"decade {decade}s")
                if parsed_pubs:
                    target_parts.append(f"publishers [{', '.join(parsed_pubs)}]")
                raise HTTPException(status_code=404, detail=f"No records found for {' & '.join(target_parts)}")

            import hashlib
            filter_sig = f"y{year}_d{decade}_p{'_'.join(sorted(parsed_pubs))}"
            sig_hash = hashlib.md5(filter_sig.encode("utf-8")).hexdigest()[:10]
            filtered_path = os.path.join(DATA_STORAGE_DIR, f"filtered_{sig_hash}.csv")
            with open(filtered_path, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            data_path = filtered_path

        mtime = os.path.getmtime(data_path) if os.path.exists(data_path) else 0
        seeds_sig = str(sorted((k, tuple(sorted(v))) for k, v in (current_custom_seeds or {}).items()))
        cache_key = (
            data_path,
            mtime,
            year,
            decade,
            tuple(sorted(parsed_pubs)),
            k_target,
            mode_key,
            current_seed_boost,
            current_base_eta,
            seeds_sig,
        )

        if cache_key in _MODEL_RUN_CACHE:
            current_model, current_corpus, current_dictionary, current_coherence, current_top_docs = _MODEL_RUN_CACHE[cache_key]
        else:
            current_model, current_corpus, current_dictionary, current_coherence, current_top_docs = lda_pipeline.run_pipeline(
                data_path,
                num_topics=k_target,
                lda_mode=mode_key,
                seed_boost=current_seed_boost,
                base_eta=current_base_eta,
                custom_seed_lexicons=current_custom_seeds,
            )
            _MODEL_RUN_CACHE[cache_key] = (
                current_model,
                current_corpus,
                current_dictionary,
                current_coherence,
                current_top_docs
            )

        current_num_topics = current_model.num_topics
        current_viz_html = lda_pipeline.get_viz_html(current_model, current_corpus, current_dictionary)
        return {
            "status": "success",
            "year_filtered": year,
            "decade_filtered": decade,
            "publishers_filtered": parsed_pubs,
            "num_topics": current_num_topics,
            "lda_mode": mode_key,
            "seed_boost": current_seed_boost,
            "base_eta": current_base_eta,
            "cached": cache_key in _MODEL_RUN_CACHE
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends")
async def get_trends():
    """
    Returns year-by-year counts for the 'Live Graph'.
    """
    summary_json_path = os.path.join(config.BASE_DIR, "app", "data_summary.json")
    if os.path.exists(summary_json_path):
        try:
            import json
            with open(summary_json_path, "r", encoding="utf-8") as sf:
                sdata = json.load(sf)
                if sdata.get("trends"):
                    return sdata["trends"]
        except Exception:
            pass

    data_path = _get_active_data_path()
    if not os.path.exists(data_path):
        return []

    data_map = defaultdict(lambda: defaultdict(int))
    publishers = set()

    try:
        for row in lda_pipeline.iter_corpus_rows(data_path):
            date_str = str(row.get("date", "") or row.get("year", ""))
            match = re.search(r"(\d{4})", date_str)
            year = match.group(1) if match else "Unknown"

            pub = lda_pipeline._clean_marc_control_chars(row.get("publisher") or "N/A")
            if not pub or pub == "PERSON":
                continue
            data_map[year][pub] += 1
            publishers.add(pub)

        result = []
        for year in sorted(data_map.keys()):
            if year == "Unknown":
                continue
            item = {
                "year": int(year) if year.isdigit() else year,
                "year_clean": year
            }
            for pub in sorted(publishers):
                item[pub] = data_map[year][pub]
            result.append(item)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/topic-viz", response_class=HTMLResponse)
async def get_viz():
    if not current_viz_html or "Disabled" in current_viz_html:
        return (
            "<html><body style='color: white; background: #0f172a; font-family: sans-serif; "
            "display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;'>"
            "<div><h3>Visualization optimized for React</h3>"
            "<p>pyLDAvis is disabled to reduce server load. Switching to native React components.</p>"
            "</div></body></html>"
        )
    return current_viz_html


@app.get("/api/topics")
async def get_topics(lda_mode: str = Query(None)):
    global current_model, current_corpus, current_dictionary, current_coherence, current_top_docs, current_lda_mode, current_year_filter, current_decade_filter, current_publishers_filter

    if lda_mode and lda_mode in lda_pipeline.LDA_MODES_META:
        current_lda_mode = lda_mode
    active_mode = current_lda_mode or "unsupervised"

    modes_cache = _load_modes_report_cache()
    modes_comparison = modes_cache.get("comparison", [])
    available_modes = list(lda_pipeline.LDA_MODES_META.values())
    seed_lexicons_payload = (
        current_custom_seeds
        if current_custom_seeds
        else {k: sorted(list(v)) for k, v in config.ARCHETYPE_LEXICONS.items()}
    )
    boost_words_payload = sorted(list(config.RELIGIOUS_VOICE_KEYWORDS))
    active_filters_payload = {
        "year": current_year_filter,
        "decade": current_decade_filter,
        "publishers": current_publishers_filter,
        "seed_boost": current_seed_boost,
        "base_eta": current_base_eta,
    }

    # Fast-path if current_model is None (cold start, Vercel serverless, or precomputed full-corpus K=12 mode switch)
    report_path = os.path.join(config.BASE_DIR, "app", "lda_topics_report.json")
    if not current_model or not current_corpus:
        rep = None
        if active_mode in modes_cache.get("modes", {}):
            rep = modes_cache["modes"][active_mode]
        elif os.path.exists(report_path):
            try:
                import json
                with open(report_path, mode="r", encoding="utf-8") as rf:
                    rep = json.load(rf)
            except Exception:
                rep = None

        if rep:
            rep_topics = []
            pub_arch_accum = defaultdict(lambda: defaultdict(float))
            rep_docs_map = {}

            for idx, t in enumerate(rep.get("topics", [])):
                t_id = int(t.get("topic_id", idx + 1)) - 1
                raw_t_pubs = t.get("top_publishers", [])
                if current_publishers_filter:
                    t_pubs = [
                        p for p in raw_t_pubs
                        if _publisher_matches_filter(p.get("publisher", ""), current_publishers_filter)
                    ] or raw_t_pubs
                else:
                    t_pubs = raw_t_pubs

                top_pubs_dict = {p["publisher"]: p["share"] for p in t_pubs}
                arch_info = t.get("archetype", {})
                arch_label = arch_info.get("label", "Hybrid / Discursive Mediation")

                # Weight prevalence by selected publisher share or decade share if filtered on serverless
                base_prev = round(100.0 / max(1, len(rep.get("topics", []))), 2)
                if current_publishers_filter:
                    matched_share = sum(
                        p["share"] for p in raw_t_pubs
                        if _publisher_matches_filter(p.get("publisher", ""), current_publishers_filter)
                    )
                    prev = round(max(1.5, matched_share), 2)
                elif current_decade_filter:
                    dec_key = f"{current_decade_filter}s"
                    dec_map = rep.get("diachronic_decade_shares", {}).get(dec_key, {})
                    prev = round(float(dec_map.get(f"Topic {t_id + 1}", base_prev)), 2)
                else:
                    prev = base_prev

                for p_item in t_pubs:
                    pub_arch_accum[p_item["publisher"]][arch_label] += (p_item["share"] * prev) / 100.0

                raw_docs = t.get("representative_docs", [])
                filtered_raw_docs = [
                    d for d in raw_docs
                    if _publisher_matches_filter(d.get("publisher", ""), current_publishers_filter)
                ] if current_publishers_filter else raw_docs
                active_raw_docs = filtered_raw_docs if filtered_raw_docs else raw_docs

                formatted_docs = [
                    {
                        **d,
                        "year": d.get("date") or d.get("year") or "o. J."
                    }
                    for d in active_raw_docs
                ]
                rep_docs_map[t_id] = formatted_docs

                rep_topics.append({
                    "id": t_id,
                    "prevalence": prev,
                    "archetype": arch_info,
                    "seeded_prior": t.get("seeded_prior") or arch_info.get("seeded_prior"),
                    "publishers": t_pubs,
                    "top_publishers": top_pubs_dict,
                    "representative_docs": formatted_docs,
                    "keywords": [
                        {"word": kw["term"], "weight": round(float(kw["weight"]), 4)}
                        for kw in t.get("top_terms", [])
                    ]
                })

            publisher_archetypes = []
            for pub, arch_map in sorted(pub_arch_accum.items()):
                if current_publishers_filter and not _publisher_matches_filter(pub, current_publishers_filter):
                    continue
                total_w = sum(arch_map.values()) or 1.0
                trad = round((arch_map.get("Traditional / Ecclesiastical", 0.0) / total_w) * 100, 1)
                neolib = round((arch_map.get("Neoliberal / Self-Optimization", 0.0) / total_w) * 100, 1)
                crit = round((arch_map.get("Critical / Secular-Humanist", 0.0) / total_w) * 100, 1)
                publisher_archetypes.append({
                    "publisher": pub,
                    "Traditional": trad,
                    "Neoliberal": neolib,
                    "Critical": crit
                })

            grid = _load_coherence_grid()
            cv_lookup = {g["k"]: g["c_v"] for g in grid}
            k_val = len(rep_topics) or config.NUM_TOPICS

            return {
                "lda_mode": active_mode,
                "lda_mode_meta": lda_pipeline.LDA_MODES_META.get(active_mode, lda_pipeline.LDA_MODES_META["unsupervised"]),
                "available_modes": available_modes,
                "modes_comparison": modes_comparison,
                "slda_diagnostics": rep.get("slda_diagnostics", {}),
                "seed_lexicons": seed_lexicons_payload,
                "religious_boost_words": boost_words_payload,
                "active_filters": active_filters_payload,
                "topics": rep_topics,
                "num_topics": k_val,
                "corpus_documents": rep.get("corpus_documents", 1863),
                "vocab_size": rep.get("vocabulary_size", 10279),
                "coherence_score": round(float(rep.get("coherence_score", -2.9771)), 4),
                "cv_coherence": cv_lookup.get(k_val),
                "publisher_archetypes": publisher_archetypes,
                "decade_breakdown": rep.get("diachronic_decade_shares", {}),
                "representative_docs": rep_docs_map
            }

    if not current_model or not current_corpus:
        try:
            await run_lda(year=None, decade=None, num_topics=config.NUM_TOPICS, lda_mode=active_mode)
        except Exception:
            return {"topics": [], "vocab_size": 0, "publisher_archetypes": [], "decade_breakdown": {}}

    topic_prevalence = defaultdict(float)
    doc_count = len(current_corpus)

    if doc_count > 0:
        for doc in current_corpus:
            doc_topics = current_model.get_document_topics(doc)
            for topic_id, prob in doc_topics:
                topic_prevalence[topic_id] += prob

        for tid in topic_prevalence:
            topic_prevalence[tid] = (topic_prevalence[tid] / doc_count) * 100

    pub_breakdown = getattr(current_model, "publisher_breakdown", {})
    dec_breakdown = getattr(current_model, "decade_breakdown", {})
    seed_assignments = getattr(current_model, "seed_assignments", {})
    slda_diagnostics = getattr(current_model, "slda_diagnostics", {})
    model_mode = getattr(current_model, "lda_mode", active_mode)

    topics = []
    pub_arch_accum = defaultdict(lambda: defaultdict(float))

    for topic_id, words in current_model.show_topics(
        num_topics=current_model.num_topics,
        num_words=15,
        formatted=False
    ):
        archetype_info = lda_pipeline.classify_topic_archetype(words)
        if topic_id in seed_assignments:
            archetype_info["seeded_prior"] = seed_assignments[topic_id]
        prev = round(topic_prevalence.get(topic_id, 0), 2)
        t_pubs = pub_breakdown.get(topic_id, [])
        top_pubs_dict = {p["publisher"]: p["share"] for p in t_pubs}

        arch_label = archetype_info.get("label", "Hybrid / Discursive Mediation")
        for p_item in t_pubs:
            pub_arch_accum[p_item["publisher"]][arch_label] += (p_item["share"] * prev) / 100.0

        raw_docs = current_top_docs.get(topic_id, [])
        formatted_docs = [
            {
                **d,
                "year": d.get("date") or d.get("year") or "o. J."
            }
            for d in raw_docs
        ]

        topics.append({
            "id": topic_id,
            "prevalence": prev,
            "archetype": archetype_info,
            "seeded_prior": seed_assignments.get(topic_id),
            "publishers": t_pubs,
            "top_publishers": top_pubs_dict,
            "representative_docs": formatted_docs,
            "keywords": [{"word": w, "weight": round(float(p), 4)} for w, p in words]
        })

    topics = sorted(topics, key=lambda x: x["prevalence"], reverse=True)

    publisher_archetypes = []
    for pub, arch_map in sorted(pub_arch_accum.items()):
        total_w = sum(arch_map.values()) or 1.0
        trad = round((arch_map.get("Traditional / Ecclesiastical", 0.0) / total_w) * 100, 1)
        neolib = round((arch_map.get("Neoliberal / Self-Optimization", 0.0) / total_w) * 100, 1)
        crit = round((arch_map.get("Critical / Secular-Humanist", 0.0) / total_w) * 100, 1)
        publisher_archetypes.append({
            "publisher": pub,
            "Traditional": trad,
            "Neoliberal": neolib,
            "Critical": crit
        })

    grid = _load_coherence_grid()
    cv_lookup = {g["k"]: g["c_v"] for g in grid}
    cv_score = cv_lookup.get(current_model.num_topics)

    return {
        "lda_mode": model_mode,
        "lda_mode_meta": lda_pipeline.LDA_MODES_META.get(model_mode, lda_pipeline.LDA_MODES_META["unsupervised"]),
        "available_modes": available_modes,
        "modes_comparison": modes_comparison,
        "slda_diagnostics": slda_diagnostics,
        "seed_lexicons": seed_lexicons_payload,
        "religious_boost_words": boost_words_payload,
        "active_filters": active_filters_payload,
        "topics": topics,
        "num_topics": current_model.num_topics,
        "corpus_documents": doc_count,
        "vocab_size": len(current_dictionary) if current_dictionary else 10279,
        "coherence_score": round(current_coherence, 4),
        "cv_coherence": cv_score,
        "publisher_archetypes": publisher_archetypes,
        "decade_breakdown": dec_breakdown,
        "representative_docs": current_top_docs
    }


@app.get("/api/data-summary")
async def data_summary():
    summary_json_path = os.path.join(config.BASE_DIR, "app", "data_summary.json")
    if os.path.exists(summary_json_path):
        try:
            import json
            with open(summary_json_path, "r", encoding="utf-8") as sf:
                sdata = json.load(sf)
                if "summary" in sdata and sdata["summary"].get("total_words"):
                    return sdata["summary"]
                if sdata.get("total_words"):
                    return sdata
        except Exception:
            pass

    data_path = _get_active_data_path()
    if os.path.exists(data_path):
        years = set()
        publishers = set()
        pub_counts = defaultdict(int)
        layer_counts = defaultdict(int)
        decade_counts = defaultdict(int)
        unique_base_titles = set()
        total_words = 0
        count = 0

        for row in lda_pipeline.iter_corpus_rows(data_path):
            count += 1
            raw_title = lda_pipeline._clean_marc_control_chars(row.get("title") or "")
            if raw_title:
                base_t = re.sub(r"\[.*?\]", "", raw_title).strip().lower()
                if base_t:
                    unique_base_titles.add(base_t)

            wc_val = row.get("word_count")
            if wc_val:
                try:
                    total_words += int(float(wc_val))
                except Exception:
                    pass

            layer = lda_pipeline._clean_marc_control_chars(row.get("corpus_layer") or "dnb_sru_marc21")
            layer_counts[layer] += 1

            dec = lda_pipeline._clean_marc_control_chars(row.get("decade") or "")
            y = row.get("year") or row.get("date")
            if y:
                m = re.search(r"(\d{4})", str(y))
                if m:
                    yr_int = int(m.group(1))
                    years.add(yr_int)
                    if not dec:
                        dec = f"{m.group(1)[:3]}0s"
            if dec:
                decade_counts[dec] += 1

            if "publisher" in row and row["publisher"]:
                clean_pub = lda_pipeline._clean_marc_control_chars(row["publisher"])
                if clean_pub and clean_pub != "PERSON":
                    publishers.add(clean_pub)
                    pub_counts[clean_pub] += 1

        top_publishers_sorted = [
            p for p, _ in sorted(pub_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        is_dnb = os.path.basename(data_path) == "dnb_metadata.csv"
        return {
            "source": "DNB SRU v1.1 + Multi-Layer OA Full-Text Corpus" if is_dnb else "Custom Corpus",
            "count": count,
            "total_records": count,
            "unique_books": len(unique_base_titles),
            "total_words": total_words,
            "publishers": top_publishers_sorted[:14] if top_publishers_sorted else sorted(list(publishers)),
            "all_publishers_count": len(publishers),
            "publisher_counts": dict(sorted(pub_counts.items(), key=lambda x: x[1], reverse=True)[:15]),
            "corpus_layers": dict(sorted(layer_counts.items(), key=lambda x: x[1], reverse=True)),
            "decade_counts": dict(sorted(decade_counts.items())),
            "year_range": f"{min(years)}–{max(years)}" if years else "1970–2025",
            "pipeline_config": {
                "spacy_model": config.SPACY_MODEL,
                "allowed_postags": config.ALLOWED_POSTAGS,
                "stopwords_total": len(lda_pipeline.ALL_STOPWORDS),
                "fraktur_noise_count": len(lda_pipeline.FRAKTUR_AND_META_NOISE),
                "domain_stopwords_count": len(config.DOMAIN_STOPWORDS),
                "religious_boost_keywords": len(config.RELIGIOUS_VOICE_KEYWORDS),
                "bigram_min_count": 5,
                "bigram_threshold": 10,
                "filter_no_below": 5,
                "filter_no_above": 0.55,
                "filter_keep_n": 25000,
                "lda_passes": config.PASSES,
                "lda_chunksize": 1500,
                "lda_alpha": str(config.ALPHA),
                "lda_eta": str(config.ETA)
            }
        }
    return {"source": "Unknown Data", "count": 0, "publishers": []}


@app.get("/api/conceptual-drift")
async def get_conceptual_drift(lemma: str = Query(None)):
    """
    Returns the Diachronic Word-Shift & Conceptual Drift telemetry (1970s–2020s)
    including 20 tracked German signifiers (Pr(RQ_m | w, Decade), relative frequency,
    Jensen-Shannon drift, Mann-Kendall trend p-values, 3-era co-occurrence collocates)
    and 6 canonical RQ1 -> RQ2/RQ3 Conceptual Replacement Dyads.
    """
    drift_path = os.path.join(config.BASE_DIR, "app", "conceptual_drift_report.json")
    if os.path.exists(drift_path):
        try:
            import json
            with open(drift_path, "r", encoding="utf-8") as df:
                data = json.load(df)
            if lemma:
                q = lemma.strip().lower()
                matched = [s for s in data.get("signifiers", []) if s.get("lemma") == q]
                return {**data, "selected_signifier": matched[0] if matched else None}
            return data
        except Exception as e:
            return {"error": str(e), "signifiers": [], "replacement_dyads": []}
    return {"signifiers": [], "replacement_dyads": []}


# Serve the React frontend (Mount after routes to avoid overlap)
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
