from fastapi import FastAPI, HTTPException, Query, UploadFile, File
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
    global current_model, current_corpus, current_dictionary, current_viz_html, current_coherence, current_top_docs

    try:
        current_model = None
        current_corpus = None
        current_dictionary = None
        current_coherence = 0.0
        current_top_docs = {}
        current_viz_html = ""
        _MODEL_RUN_CACHE.clear()
        return {"status": "success", "message": "Reverted to Default Research Corpus."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run-lda")
async def run_lda(
    year: int = Query(None),
    decade: int = Query(None),
    num_topics: int = Query(None)
):
    global current_model, current_corpus, current_dictionary, current_viz_html, current_coherence, current_top_docs, current_num_topics

    data_path = _get_active_data_path()
    k_target = int(num_topics) if num_topics else config.NUM_TOPICS

    try:
        if year or decade:
            rows = []
            with open(data_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                for row in reader:
                    date_val = str(row.get("date", ""))
                    match = re.search(r"(\d{4})", date_val)
                    if not match:
                        continue
                    r_year = int(match.group(1))

                    if year and r_year == year:
                        rows.append(row)
                    elif decade and (decade <= r_year < decade + 10):
                        rows.append(row)

            if not rows:
                target = f"year {year}" if year else f"decade {decade}s"
                raise HTTPException(status_code=404, detail=f"No records found for {target}")

            suffix = year if year else f"decade_{decade}"
            filtered_path = os.path.join(DATA_STORAGE_DIR, f"filtered_{suffix}.csv")
            with open(filtered_path, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            data_path = filtered_path

        mtime = os.path.getmtime(data_path) if os.path.exists(data_path) else 0
        cache_key = (data_path, mtime, year, decade, k_target)

        if cache_key in _MODEL_RUN_CACHE:
            current_model, current_corpus, current_dictionary, current_coherence, current_top_docs = _MODEL_RUN_CACHE[cache_key]
        else:
            current_model, current_corpus, current_dictionary, current_coherence, current_top_docs = lda_pipeline.run_pipeline(
                data_path,
                num_topics=k_target
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
            "num_topics": current_num_topics,
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
    data_path = _get_active_data_path()
    data_map = defaultdict(lambda: defaultdict(int))
    publishers = set()

    try:
        with open(data_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = str(row.get("date", ""))
                match = re.search(r"(\d{4})", date_str)
                year = match.group(1) if match else "Unknown"

                pub = row.get("publisher", "N/A")
                data_map[year][pub] += 1
                publishers.add(pub)

        result = []
        for year in sorted(data_map.keys()):
            item = {"year_clean": year}
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
async def get_topics():
    global current_model, current_corpus, current_dictionary, current_coherence, current_top_docs
    if not current_model or not current_corpus:
        # Auto-initialize default model on first load so the observatory is immediately populated
        try:
            await run_lda(year=None, decade=None, num_topics=config.NUM_TOPICS)
        except Exception:
            return {"topics": [], "vocab_size": 0, "publisher_archetypes": []}

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

    topics = []
    pub_arch_accum = defaultdict(lambda: defaultdict(float))

    for topic_id, words in current_model.show_topics(
        num_topics=current_model.num_topics,
        num_words=15,
        formatted=False
    ):
        archetype_info = lda_pipeline.classify_topic_archetype(words)
        prev = round(topic_prevalence.get(topic_id, 0), 2)
        t_pubs = pub_breakdown.get(topic_id, [])

        # Accumulate publisher x ideological archetype matrix
        arch_label = archetype_info.get("label", "Hybrid / Discursive Mediation")
        for p_item in t_pubs:
            pub_arch_accum[p_item["publisher"]][arch_label] += (p_item["share"] * prev) / 100.0

        topics.append({
            "id": topic_id,
            "prevalence": prev,
            "archetype": archetype_info,
            "publishers": t_pubs,
            "keywords": [{"word": w, "weight": round(float(p), 4)} for w, p in words]
        })

    topics = sorted(topics, key=lambda x: x["prevalence"], reverse=True)

    # Normalize publisher_archetypes for the Institutional Matrix view
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

    # Match C_v score from grid search if available
    grid = _load_coherence_grid()
    cv_lookup = {g["k"]: g["c_v"] for g in grid}
    cv_score = cv_lookup.get(current_model.num_topics)

    return {
        "topics": topics,
        "num_topics": current_model.num_topics,
        "vocab_size": len(current_dictionary) if current_dictionary else 3712,
        "coherence_score": round(current_coherence, 4),
        "cv_coherence": cv_score,
        "publisher_archetypes": publisher_archetypes,
        "representative_docs": current_top_docs
    }


@app.get("/api/data-summary")
async def data_summary():
    data_path = _get_active_data_path()
    if os.path.exists(data_path):
        years = set()
        publishers = set()
        count = 0
        with open(data_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                count += 1
                y = row.get("year") or row.get("date")
                if y:
                    try:
                        years.add(int(str(y).strip()[:4]))
                    except Exception:
                        pass
                if "publisher" in row and row["publisher"]:
                    publishers.add(row["publisher"])

        is_dnb = os.path.basename(data_path) == "dnb_metadata.csv"
        return {
            "source": "DNB SRU Harvest (DDC 200/230)" if is_dnb else "Mock Proxy Corpus",
            "count": count,
            "publishers": sorted(list(publishers)),
            "year_range": f"{min(years)}–{max(years)}" if years else "N/A"
        }
    return {"source": "Unknown Data", "count": 0, "publishers": []}


# Serve the React frontend (Mount after routes to avoid overlap)
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
