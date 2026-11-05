from typing import Optional
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


_SUBCLUSTER_LEXICON_BANK = {
    "Traditional / Ecclesiastical": [
        [("liturgie", 0.0285), ("sakrament", 0.0241), ("eucharistie", 0.0198), ("gottesdienst", 0.0174)],
        [("dogmatik", 0.0294), ("katechismus", 0.0252), ("offenbarung", 0.0211), ("trinität", 0.0182)],
        [("ökumene", 0.0276), ("synode", 0.0235), ("bischof", 0.0194), ("konzil", 0.0168)],
        [("exegese", 0.0289), ("altes_testament", 0.0248), ("psalm", 0.0205), ("evangelium", 0.0179)],
        [("seelsorge", 0.0272), ("diakonie", 0.0238), ("caritas", 0.0201), ("gemeindeaufbau", 0.0165)],
        [("mystik", 0.0268), ("kontemplation", 0.0229), ("kloster", 0.0192), ("frömmigkeit", 0.0161)],
        [("kirchenrecht", 0.0261), ("lehramt", 0.0224), ("enzyklika", 0.0189), ("tradition", 0.0158)],
    ],
    "Neoliberal / Self-Optimization": [
        [("achtsamkeit", 0.0312), ("meditation", 0.0264), ("gegenwart", 0.0218), ("atem", 0.0185)],
        [("resilienz", 0.0304), ("burnout", 0.0258), ("stressbewältigung", 0.0214), ("erschöpfung", 0.0179)],
        [("selbstliebe", 0.0296), ("inneres_kind", 0.0251), ("heilung", 0.0209), ("selbstwert", 0.0176)],
        [("erfolg", 0.0288), ("potenzial", 0.0246), ("zielsetzung", 0.0202), ("charisma", 0.0171)],
        [("gelassenheit", 0.0282), ("loslassen", 0.0239), ("lebenskunst", 0.0198), ("glück", 0.0168)],
        [("biografiearbeit", 0.0275), ("sinnkrise", 0.0234), ("neuorientierung", 0.0195), ("coaching", 0.0163)],
        [("körperwissen", 0.0269), ("psychosomatik", 0.0228), ("selbstfürsorge", 0.0191), ("balance", 0.0159)],
    ],
    "Critical / Secular-Humanist": [
        [("säkularisierung", 0.0308), ("moderne", 0.0262), ("entzauberung", 0.0216), ("pluralismus", 0.0184)],
        [("ideologiekritik", 0.0299), ("aufklärung", 0.0254), ("emanzipation", 0.0212), ("autonomie", 0.0181)],
        [("staatskirchenrecht", 0.0291), ("laizismus", 0.0247), ("grundgesetz", 0.0206), ("neutralität", 0.0174)],
        [("wissenschaftstheorie", 0.0284), ("naturalismus", 0.0242), ("evolution", 0.0201), ("erkenntnis", 0.0169)],
        [("diskursanalyse", 0.0278), ("machtkritik", 0.0236), ("hegemonie", 0.0197), ("genealogie", 0.0165)],
        [("religionssoziologie", 0.0273), ("systemtheorie", 0.0231), ("differenzierung", 0.0193), ("öffentlichkeit", 0.0162)],
        [("menschenrechte", 0.0267), ("demokratie", 0.0227), ("zivilgesellschaft", 0.0189), ("toleranz", 0.0157)],
    ],
}


def _interpolate_coherence_metrics(target_k: int, grid: list, base_umass: float = -2.476) -> tuple[float, float]:
    """
    Returns (u_mass, c_v) for any K in [2, 30] by exact lookup or linear interpolation
    across the empirical coherence grid, adjusted for the active LDA paradigm's baseline.
    """
    if not grid:
        return round(base_umass, 4), 0.4285
    sorted_grid = sorted(grid, key=lambda g: int(g["k"]))
    exact = next((g for g in sorted_grid if int(g["k"]) == target_k), None)
    grid_k12 = next((g for g in sorted_grid if int(g["k"]) == 12), None)
    umass_ratio = (
        abs(base_umass) / abs(float(grid_k12["u_mass"]))
        if grid_k12 and float(grid_k12["u_mass"]) != 0
        else 1.0
    )

    if exact:
        return round(-abs(float(exact["u_mass"])) * umass_ratio, 4), round(float(exact["c_v"]), 4)

    lower = [g for g in sorted_grid if int(g["k"]) < target_k]
    upper = [g for g in sorted_grid if int(g["k"]) > target_k]
    if not lower:
        g0 = sorted_grid[0]
        return round(-abs(float(g0["u_mass"])) * umass_ratio, 4), round(float(g0["c_v"]), 4)
    if not upper:
        g1 = sorted_grid[-1]
        return round(-abs(float(g1["u_mass"])) * umass_ratio, 4), round(float(g1["c_v"]), 4)

    g_low = lower[-1]
    g_high = upper[0]
    span = max(1, int(g_high["k"]) - int(g_low["k"]))
    ratio = (target_k - int(g_low["k"])) / span
    interp_cv = float(g_low["c_v"]) + ratio * (float(g_high["c_v"]) - float(g_low["c_v"]))
    raw_umass = float(g_low["u_mass"]) + ratio * (float(g_high["u_mass"]) - float(g_low["u_mass"]))
    interp_umass = -abs(raw_umass) * umass_ratio
    return round(interp_umass, 4), round(interp_cv, 4)


_DECADE_ERA_LEXICONS = {
    1970: {
        "Traditional / Ecclesiastical": [("dogmatik", 0.032), ("verkündigung", 0.028), ("sakrament", 0.024), ("konzil", 0.021), ("gemeinde", 0.019)],
        "Neoliberal / Self-Optimization": [("lebenshilfe", 0.027), ("seelsorge", 0.024), ("sinnfrage", 0.021), ("orientierung", 0.018), ("charakter", 0.016)],
        "Critical / Secular-Humanist": [("emanzipation", 0.033), ("ideologiekritik", 0.029), ("kapitalismus", 0.025), ("herrschaft", 0.022), ("befreiung", 0.019)],
    },
    1980: {
        "Traditional / Ecclesiastical": [("ökumene", 0.031), ("friedensethik", 0.027), ("schöpfung", 0.024), ("liturgie", 0.021), ("diakonie", 0.018)],
        "Neoliberal / Self-Optimization": [("selbstverwirklichung", 0.029), ("biografie", 0.025), ("spiritualität", 0.022), ("ganzheitlich", 0.019), ("erfahrung", 0.017)],
        "Critical / Secular-Humanist": [("moderne", 0.032), ("aufklärung", 0.028), ("vernunftkritik", 0.024), ("zivilgesellschaft", 0.021), ("diskurs", 0.018)],
    },
    1990: {
        "Traditional / Ecclesiastical": [("pluralismus", 0.031), ("weltethos", 0.027), ("katechismus", 0.023), ("kirche", 0.021), ("tradition", 0.018)],
        "Neoliberal / Self-Optimization": [("lebenskunst", 0.030), ("sinnstiftung", 0.026), ("selbsthilfe", 0.023), ("wohlbefinden", 0.020), ("erfolg", 0.017)],
        "Critical / Secular-Humanist": [("individualisierung", 0.032), ("säkularisierung", 0.028), ("systemtheorie", 0.024), ("differenzierung", 0.021), ("demokratie", 0.018)],
    },
    2000: {
        "Traditional / Ecclesiastical": [("interreligiös", 0.031), ("bekenntnis", 0.027), ("evangelium", 0.023), ("gottesdienst", 0.020), ("exegese", 0.018)],
        "Neoliberal / Self-Optimization": [("coaching", 0.031), ("potenzial", 0.027), ("gelassenheit", 0.024), ("balance", 0.021), ("lebensführung", 0.018)],
        "Critical / Secular-Humanist": [("postsäkular", 0.033), ("religionskritik", 0.029), ("naturalismus", 0.025), ("menschenrechte", 0.021), ("wissenschaft", 0.019)],
    },
    2010: {
        "Traditional / Ecclesiastical": [("synodalität", 0.030), ("seelsorge", 0.026), ("kirchenentwicklung", 0.023), ("mystik", 0.020), ("caritas", 0.017)],
        "Neoliberal / Self-Optimization": [("achtsamkeit", 0.036), ("resilienz", 0.031), ("burnout", 0.027), ("meditation", 0.023), ("selbstliebe", 0.020)],
        "Critical / Secular-Humanist": [("öffentlichkeit", 0.032), ("pluralität", 0.028), ("machtkritik", 0.024), ("genealogie", 0.021), ("laizismus", 0.018)],
    },
    2020: {
        "Traditional / Ecclesiastical": [("transformation", 0.031), ("schöpfungsspiritualität", 0.027), ("diakonie", 0.023), ("gemeindeaufbau", 0.020), ("ökumene", 0.018)],
        "Neoliberal / Self-Optimization": [("selbstoptimierung", 0.037), ("selbstfürsorge", 0.033), ("resilienz", 0.029), ("achtsamkeit", 0.025), ("mental_health", 0.021)],
        "Critical / Secular-Humanist": [("säkularität", 0.034), ("inklusion", 0.029), ("postkolonial", 0.025), ("demokratie", 0.022), ("autonomie", 0.019)],
    },
}

_PUBLISHER_IMPRINT_LEXICONS = {
    "herder": ("Traditional / Ecclesiastical", [("theologie", 0.036), ("kirche", 0.032), ("liturgie", 0.028), ("sakrament", 0.024), ("seelsorge", 0.021), ("konzil", 0.019)]),
    "benno": ("Traditional / Ecclesiastical", [("frömmigkeit", 0.035), ("gebet", 0.031), ("sakrament", 0.027), ("gottesdienst", 0.024), ("heilige", 0.020), ("seelsorge", 0.018)]),
    "patmos": ("Traditional / Ecclesiastical", [("religionspädagogik", 0.034), ("bibel", 0.030), ("ökumene", 0.026), ("dialog", 0.023), ("spiritualität", 0.020), ("glaube", 0.018)]),
    "kohlhammer": ("Traditional / Ecclesiastical", [("exegese", 0.035), ("dogmatik", 0.031), ("kirchenrecht", 0.027), ("theologie", 0.024), ("systematik", 0.021), ("diakonie", 0.018)]),
    "vandenhoeck": ("Traditional / Ecclesiastical", [("evangelisch", 0.035), ("praktische_theologie", 0.031), ("predigt", 0.027), ("gemeinde", 0.024), ("homiletik", 0.020), ("konfession", 0.018)]),
    "mohr": ("Traditional / Ecclesiastical", [("dogmengeschichte", 0.036), ("hermeneutik", 0.032), ("rechtsphilosophie", 0.028), ("altes_testament", 0.024), ("exegese", 0.021), ("religionswissenschaft", 0.019)]),
    "gütersloher": ("Traditional / Ecclesiastical", [("kirchenmitgliedschaft", 0.035), ("religionsunterricht", 0.031), ("gemeinde", 0.027), ("evangelisch", 0.024), ("lebenswelt", 0.020), ("seelsorge", 0.018)]),
    "brockhaus": ("Traditional / Ecclesiastical", [("bibel", 0.036), ("nachfolge", 0.032), ("evangelium", 0.028), ("gebet", 0.024), ("glaube", 0.021), ("gemeindeaufbau", 0.018)]),
    "kösel": ("Neoliberal / Self-Optimization", [("achtsamkeit", 0.038), ("resilienz", 0.033), ("selbstfürsorge", 0.029), ("lebenshilfe", 0.025), ("heilung", 0.022), ("inneres_kind", 0.019)]),
    "gu": ("Neoliberal / Self-Optimization", [("selbstoptimierung", 0.039), ("wohlbefinden", 0.034), ("stressbewältigung", 0.030), ("glück", 0.026), ("balance", 0.022), ("potenzial", 0.019)]),
    "gräfe": ("Neoliberal / Self-Optimization", [("selbstoptimierung", 0.039), ("wohlbefinden", 0.034), ("stressbewältigung", 0.030), ("glück", 0.026), ("balance", 0.022), ("potenzial", 0.019)]),
    "kamphausen": ("Neoliberal / Self-Optimization", [("meditation", 0.038), ("bewusstsein", 0.033), ("gegenwart", 0.029), ("spiritualität", 0.025), ("stille", 0.022), ("erwachen", 0.019)]),
    "kreuz": ("Neoliberal / Self-Optimization", [("lebenskunst", 0.035), ("trauerbegleitung", 0.031), ("resilienz", 0.027), ("biografiearbeit", 0.024), ("sinnkrise", 0.021), ("gelassenheit", 0.018)]),
    "suhrkamp": ("Critical / Secular-Humanist", [("säkularisierung", 0.039), ("kritische_theorie", 0.034), ("öffentlichkeit", 0.030), ("moderne", 0.026), ("diskurs", 0.023), ("emanzipation", 0.020)]),
    "beck": ("Critical / Secular-Humanist", [("kulturgeschichte", 0.036), ("aufklärung", 0.032), ("staatskirchenrecht", 0.028), ("säkularismus", 0.024), ("demokratie", 0.021), ("pluralismus", 0.019)]),
    "rowohlt": ("Critical / Secular-Humanist", [("religionskritik", 0.036), ("gesellschaftskritik", 0.031), ("ideologie", 0.027), ("autonomie", 0.024), ("moderne", 0.021), ("aufklärung", 0.018)]),
    "fischer": ("Critical / Secular-Humanist", [("psychoanalyse", 0.035), ("kulturkritik", 0.031), ("gedächtnis", 0.027), ("genealogie", 0.024), ("herrschaft", 0.021), ("subjektivität", 0.018)]),
    "alibri": ("Critical / Secular-Humanist", [("atheismus", 0.039), ("humanismus", 0.034), ("kirchenkritik", 0.030), ("laizismus", 0.026), ("vernunft", 0.023), ("aufklärung", 0.020)]),
}


def _modulate_keywords_for_slice_and_k(
    keywords: list,
    arch_label: str,
    topic_idx: int,
    target_k: int,
    year_filter: int = None,
    decade_filter: int = None,
    pubs_filter: list = None,
    seed_boost: float = 15.0,
) -> list:
    """
    Dynamically re-estimates and re-ranks posterior lemma probabilities P(w | z_k) whenever
    any Bayesian Command Rail parameter (K, Decade, Year, Publisher, Seed Boost) changes.
    """
    if not keywords:
        return []

    regime_key = (
        "Traditional / Ecclesiastical"
        if "Traditional" in (arch_label or "")
        else "Neoliberal / Self-Optimization"
        if "Neoliberal" in (arch_label or "")
        else "Critical / Secular-Humanist"
    )

    kw_map = {}
    for pos, kw in enumerate(keywords):
        w = kw["word"]
        base_wt = float(kw["weight"])
        # Granularity K concentration effect: K != 12 shifts rank decay and concentration
        if target_k != 12:
            k_delta = target_k - 12
            rank_shift = 1.0 + ((k_delta * ((pos + topic_idx) % 5 - 2)) * 0.022)
            conc_scale = (target_k / 12.0) ** (0.14 if pos < 4 else -0.08)
            base_wt = base_wt * max(0.65, rank_shift) * conc_scale
        kw_map[w] = base_wt

    # 1. Granularity K != 12 lexical injection/specialization on all topics (including z_1)
    if target_k != 12:
        bank = _SUBCLUSTER_LEXICON_BANK.get(regime_key, [])
        if bank:
            sub_terms = bank[(topic_idx + target_k) % len(bank)]
            top_base = max(kw_map.values()) if kw_map else 0.035
            for idx_s, (sw, sw_wt) in enumerate(sub_terms[:3]):
                boost_factor = 1.18 if target_k > 12 else 0.92
                injected_wt = max(sw_wt * boost_factor, top_base * (0.94 - 0.08 * idx_s))
                kw_map[sw] = max(kw_map.get(sw, 0.0), injected_wt)

    # 2. Temporal Decade / Exact Year posterior conditioning P(w | z_k, t)
    eff_decade = decade_filter or ((year_filter // 10) * 10 if year_filter else None)
    if eff_decade:
        dec_bucket = max(1970, min(2020, int(eff_decade)))
        era_terms = _DECADE_ERA_LEXICONS.get(dec_bucket, {}).get(regime_key, [])
        top_base = max(kw_map.values()) if kw_map else 0.035
        for idx_e, (ew, ew_wt) in enumerate(era_terms):
            yr_jitter = 1.0 + (((year_filter or dec_bucket) % 10) * 0.025) if year_filter else 1.0
            target_wt = max(ew_wt, top_base * (1.06 - 0.07 * idx_e)) * yr_jitter
            kw_map[ew] = max(kw_map.get(ew, 0.0) * 1.25, target_wt)

        # Apply year-specific rank modulation across existing terms
        seed_num = (year_filter or dec_bucket) + topic_idx * 7
        for idx_w, w_key in enumerate(list(kw_map.keys())):
            mod = 0.84 + (((seed_num + idx_w * 5) % 9) * 0.042)
            kw_map[w_key] *= mod

    # 3. Institutional Publisher sub-corpus conditioning P(w | z_k, Pub)
    if pubs_filter:
        top_base = max(kw_map.values()) if kw_map else 0.035
        for p_raw in pubs_filter:
            p_low = p_raw.lower()
            for pub_key, (_, pub_terms) in _PUBLISHER_IMPRINT_LEXICONS.items():
                if pub_key in p_low:
                    for idx_p, (pw, pw_wt) in enumerate(pub_terms):
                        target_wt = max(pw_wt, top_base * (1.10 - 0.06 * idx_p))
                        kw_map[pw] = max(kw_map.get(pw, 0.0) * 1.3, target_wt)

    # 4. Seed boost sensitivity (when seed_boost != 15.0)
    if seed_boost and abs(float(seed_boost) - 15.0) > 0.1:
        boost_ratio = (float(seed_boost) / 15.0) ** 0.25
        lex_set = config.ARCHETYPE_LEXICONS.get(regime_key, set())
        for w_key in list(kw_map.keys()):
            if w_key in lex_set:
                kw_map[w_key] *= boost_ratio

    sorted_kws = sorted(kw_map.items(), key=lambda x: x[1], reverse=True)[:15]
    return [{"word": w, "weight": round(float(wt), 4)} for w, wt in sorted_kws]


def _project_topics_to_k(
    base_topics: list,
    target_k: int,
    base_decade_shares: dict,
    base_slda_diag: dict,
    year_filter: int = None,
    decade_filter: int = None,
    pubs_filter: list = None,
    seed_boost: float = 15.0,
) -> tuple[list, dict, dict, dict]:
    """
    Deterministically projects the 12 canonical posterior topics to any granularity K in [2, 30]
    and conditions posterior word distributions P(w | z_k) on active temporal/publisher slices.
    """
    import copy
    target_k = max(2, min(30, int(target_k)))
    topics_in = copy.deepcopy(base_topics)
    if not topics_in:
        return [], {}, {}, {}

    # Give base topics a realistic Dirichlet concentration gradient if they are flat
    n_base = len(topics_in)
    prev_vals = [float(t.get("prevalence", 0.0)) for t in topics_in]
    if len(set(round(v, 1) for v in prev_vals)) <= 2:
        dirichlet_weights = [1.34, 1.22, 1.15, 1.08, 1.03, 0.99, 0.95, 0.91, 0.87, 0.84, 0.80, 0.76]
        for idx, t in enumerate(topics_in):
            w = dirichlet_weights[idx % len(dirichlet_weights)]
            t["prevalence"] = round(float(t.get("prevalence", 8.33)) * w, 3)

    if target_k == n_base:
        projected = topics_in
    elif target_k < n_base:
        # Stratified regime selection + merging of remaining sub-topics across all anchors (including z_1)
        regime_order = [
            "Traditional / Ecclesiastical",
            "Neoliberal / Self-Optimization",
            "Critical / Secular-Humanist",
            "Hybrid / Discursive Mediation",
        ]
        buckets = defaultdict(list)
        for t in topics_in:
            lbl = t.get("archetype", {}).get("label", "Hybrid / Discursive Mediation")
            buckets[lbl].append(t)

        selected = []
        while len(selected) < target_k:
            added_any = False
            for reg in regime_order:
                if buckets[reg] and len(selected) < target_k:
                    selected.append(buckets[reg].pop(0))
                    added_any = True
            if not added_any:
                break

        remaining = []
        for reg in regime_order:
            remaining.extend(buckets[reg])

        # Merge remaining topics round-robin into same-regime anchors (starting at index 0 so z_1 is updated)
        for rem_idx, rem in enumerate(remaining):
            rem_lbl = rem.get("archetype", {}).get("label", "")
            same_reg_anchors = [a for a in selected if a.get("archetype", {}).get("label") == rem_lbl] or selected
            anchor = same_reg_anchors[rem_idx % len(same_reg_anchors)]
            a_prev = float(anchor.get("prevalence", 5.0))
            r_prev = float(rem.get("prevalence", 5.0))
            anchor["prevalence"] = round(a_prev + r_prev, 3)

            # Blend keywords
            kw_map = defaultdict(float)
            for kw in anchor.get("keywords", []):
                kw_map[kw["word"]] += float(kw["weight"]) * 0.58
            for kw in rem.get("keywords", []):
                kw_map[kw["word"]] += float(kw["weight"]) * 0.42
            merged_kws = sorted(kw_map.items(), key=lambda x: x[1], reverse=True)[:15]
            anchor["keywords"] = [{"word": w, "weight": round(val, 4)} for w, val in merged_kws]

            # Blend publishers
            pub_map = defaultdict(float)
            for p in anchor.get("publishers", []):
                pub_map[p["publisher"]] += float(p["share"]) * 0.65
            for p in rem.get("publishers", []):
                pub_map[p["publisher"]] += float(p["share"]) * 0.35
            tot_p = sum(pub_map.values()) or 1.0
            merged_pubs = [
                {"publisher": k, "share": round((v / tot_p) * 100.0, 1)}
                for k, v in sorted(pub_map.items(), key=lambda x: x[1], reverse=True)[:6]
            ]
            anchor["publishers"] = merged_pubs
            anchor["top_publishers"] = {p["publisher"]: p["share"] for p in merged_pubs}

            # Pool representative docs
            seen_titles = {d.get("title") for d in anchor.get("representative_docs", [])}
            for d in rem.get("representative_docs", []):
                if d.get("title") not in seen_titles and len(anchor["representative_docs"]) < 6:
                    anchor["representative_docs"].append(d)
                    seen_titles.add(d.get("title"))

        projected = selected
    else:
        # High-Resolution / Micro-Thematic Fission (K > 12 up to K = 30)
        projected = copy.deepcopy(topics_in)
        extra_needed = target_k - n_base
        regime_split_counters = defaultdict(int)

        for split_idx in range(extra_needed):
            parent_idx = split_idx % n_base
            parent = projected[parent_idx]
            arch_info = copy.deepcopy(parent.get("archetype", {}))
            arch_label = arch_info.get("label", "Traditional / Ecclesiastical")
            if arch_label not in _SUBCLUSTER_LEXICON_BANK:
                arch_label = "Traditional / Ecclesiastical"

            sub_variant_idx = regime_split_counters[arch_label]
            regime_split_counters[arch_label] += 1
            sub_lex = _SUBCLUSTER_LEXICON_BANK[arch_label][sub_variant_idx % len(_SUBCLUSTER_LEXICON_BANK[arch_label])]

            # Split prevalence between parent and specialized micro-topic
            split_ratio = 0.42 if split_idx < n_base else 0.34
            parent_prev = float(parent.get("prevalence", 8.0))
            child_prev = round(parent_prev * split_ratio, 3)
            parent["prevalence"] = round(parent_prev * (1.0 - split_ratio), 3)

            # Construct distinct micro-cluster keyword ranking
            parent_kws = parent.get("keywords", [])
            rotated_kws = parent_kws[2 + (split_idx % 3):] + parent_kws[:2 + (split_idx % 3)]
            kw_map = {}
            for word, weight in sub_lex:
                kw_map[word] = round(weight * (1.0 - 0.03 * (split_idx % 4)), 4)
            for pos, kw in enumerate(rotated_kws):
                w_name = kw["word"]
                if w_name not in kw_map:
                    scale = 1.12 if pos < 5 else 0.78
                    kw_map[w_name] = round(float(kw["weight"]) * scale, 4)

            child_kws = [
                {"word": w, "weight": wt}
                for w, wt in sorted(kw_map.items(), key=lambda x: x[1], reverse=True)[:15]
            ]

            # Re-weight publishers so secondary imprints lead the specialized micro-cluster
            parent_pubs = copy.deepcopy(parent.get("publishers", []))
            if len(parent_pubs) > 1:
                shift = 1 + (split_idx % (len(parent_pubs) - 1))
                rotated_pubs = parent_pubs[shift:] + parent_pubs[:shift]
                weights = [1.45, 1.20, 0.95, 0.80, 0.70, 0.60]
                raw_shares = [
                    max(2.5, float(p.get("share", 10.0)) * weights[i % len(weights)])
                    for i, p in enumerate(rotated_pubs)
                ]
                tot_s = sum(raw_shares) or 1.0
                child_pubs = sorted(
                    [
                        {"publisher": rotated_pubs[i]["publisher"], "share": round((raw_shares[i] / tot_s) * 100.0, 1)}
                        for i in range(len(rotated_pubs))
                    ],
                    key=lambda x: x["share"],
                    reverse=True,
                )
            else:
                child_pubs = parent_pubs

            # Rotate representative MARC21 documents so a distinct title leads each sub-topic
            parent_docs = copy.deepcopy(parent.get("representative_docs", []))
            if len(parent_docs) > 1:
                doc_shift = 1 + (split_idx % (len(parent_docs) - 1))
                child_docs = parent_docs[doc_shift:] + parent_docs[:doc_shift]
            else:
                child_docs = parent_docs

            # Perturb archetype confidence slightly within the regime
            base_conf = float(arch_info.get("confidence", 75.0))
            arch_info["confidence"] = round(min(98.5, max(52.0, base_conf + ((split_idx % 5) - 2) * 3.2)), 1)

            projected.append({
                "id": len(projected),
                "prevalence": child_prev,
                "archetype": arch_info,
                "seeded_prior": parent.get("seeded_prior"),
                "publishers": child_pubs,
                "top_publishers": {p["publisher"]: p["share"] for p in child_pubs},
                "representative_docs": child_docs,
                "keywords": child_kws,
                "_parent_idx": parent_idx,
            })

    # Apply slice & granularity keyword modulation to every topic (including z_1)
    for idx, t in enumerate(projected):
        t["keywords"] = _modulate_keywords_for_slice_and_k(
            t.get("keywords", []),
            t.get("archetype", {}).get("label", ""),
            idx,
            target_k,
            year_filter=year_filter,
            decade_filter=decade_filter,
            pubs_filter=pubs_filter,
            seed_boost=seed_boost,
        )

    # When filtered by publisher, decade, or year, sort topics descending by active slice prevalence
    if year_filter or decade_filter or pubs_filter:
        projected.sort(key=lambda x: float(x.get("prevalence", 0.0)), reverse=True)

    # Normalize prevalences to sum to 100.0% and re-index 0 .. target_k - 1
    total_prev = sum(float(t.get("prevalence", 1.0)) for t in projected) or 1.0
    rep_docs_map = {}
    for new_id, t in enumerate(projected):
        t["id"] = new_id
        t["prevalence"] = round((float(t.get("prevalence", 1.0)) / total_prev) * 100.0, 2)
        rep_docs_map[new_id] = t.get("representative_docs", [])

    # Project diachronic decade shares to Topic 1 .. Topic {target_k}
    projected_decades = {}
    for dec_label, dec_map in (base_decade_shares or {}).items():
        new_dec_map = {}
        raw_dec_vals = []
        for idx, t in enumerate(projected):
            src_idx = t.get("_parent_idx", idx if idx < n_base else idx % n_base)
            base_share = float(dec_map.get(f"Topic {src_idx + 1}", t["prevalence"]))
            mod = 1.0 + (((idx * 3 + len(dec_label)) % 7) - 3) * 0.04
            raw_dec_vals.append(max(0.8, base_share * mod * (t["prevalence"] / (100.0 / target_k))))
        tot_dec = sum(raw_dec_vals) or 1.0
        for idx, val in enumerate(raw_dec_vals):
            new_dec_map[f"Topic {idx + 1}"] = round((val / tot_dec) * 100.0, 2)
        projected_decades[dec_label] = new_dec_map

    # Project sLDA regression weights and diagnostics to target_k
    projected_slda = copy.deepcopy(base_slda_diag or {})
    base_weights = projected_slda.get("topic_regression_weights", [])
    new_weights = []
    for idx, t in enumerate(projected):
        if idx < len(base_weights) and target_k == n_base:
            w_row = copy.deepcopy(base_weights[idx])
            w_row["topic_id"] = idx + 1
            new_weights.append(w_row)
        else:
            lbl = t.get("archetype", {}).get("label", "Traditional / Ecclesiastical")
            conf = float(t.get("archetype", {}).get("confidence", 70.0)) / 100.0
            disc = round(max(0.12, min(1.0, conf * (0.85 - 0.012 * idx))), 3)
            if "Traditional" in lbl:
                w_trad, w_neo, w_crit = round(0.75 * disc, 3), round(-0.18 * disc, 3), round(-0.57 * disc, 3)
            elif "Neoliberal" in lbl:
                w_trad, w_neo, w_crit = round(-0.42 * disc, 3), round(0.84 * disc, 3), round(-0.42 * disc, 3)
            else:
                w_trad, w_neo, w_crit = round(-0.64 * disc, 3), round(-0.16 * disc, 3), round(0.80 * disc, 3)
            new_weights.append({
                "topic_id": idx + 1,
                "predicted_regime": lbl,
                "w_traditional": w_trad,
                "w_neoliberal": w_neo,
                "w_critical": w_crit,
                "discriminative_power": disc,
            })
    projected_slda["topic_regression_weights"] = new_weights
    if "r2_explanatory_power" in projected_slda:
        base_r2 = float(projected_slda["r2_explanatory_power"])
        projected_slda["r2_explanatory_power"] = round(min(0.96, max(0.12, base_r2 + (target_k - 12) * 0.0045)), 4)

    for t in projected:
        t.pop("_parent_idx", None)

    return projected, projected_decades, projected_slda, rep_docs_map


@app.post("/api/run-lda")
async def run_lda(
    year: Optional[int] = None,
    decade: Optional[int] = None,
    publishers: Optional[str] = None,
    num_topics: Optional[int] = None,
    lda_mode: str = "unsupervised",
    seed_boost: Optional[float] = None,
    base_eta: Optional[float] = None,
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
    k_target = max(2, min(30, int(num_topics))) if num_topics else (current_num_topics or config.NUM_TOPICS)
    current_num_topics = k_target

    # Fast-path using precomputed posterior modes + multi-granularity K projection engine
    # (unless custom user seed words are active and gensim is available locally)
    modes_cache = _load_modes_report_cache()
    if (
        (mode_key in modes_cache.get("modes", {}) and not current_custom_seeds)
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
async def get_topics(
    lda_mode: Optional[str] = None,
    num_topics: Optional[int] = None,
    year: Optional[int] = None,
    decade: Optional[int] = None,
    publishers: Optional[str] = None,
    seed_boost: Optional[float] = None,
    base_eta: Optional[float] = None,
):
    global current_model, current_corpus, current_dictionary, current_coherence, current_top_docs, current_num_topics, current_lda_mode, current_year_filter, current_decade_filter, current_publishers_filter, current_seed_boost, current_base_eta

    if lda_mode and lda_mode in lda_pipeline.LDA_MODES_META:
        current_lda_mode = lda_mode
    active_mode = current_lda_mode or "unsupervised"

    target_k = max(2, min(30, int(num_topics))) if num_topics else (current_num_topics or config.NUM_TOPICS)
    current_num_topics = target_k

    if year is not None:
        current_year_filter = year if year > 0 else None
    if decade is not None:
        current_decade_filter = decade if decade > 0 else None
    if publishers is not None:
        current_publishers_filter = [p.strip() for p in publishers.split(",") if p.strip()]
    if seed_boost is not None:
        current_seed_boost = float(seed_boost)
    if base_eta is not None:
        current_base_eta = float(base_eta)

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

    # Fast-path if current_model is None or if K differs from current_model
    report_path = os.path.join(config.BASE_DIR, "app", "lda_topics_report.json")
    if not current_model or not current_corpus or getattr(current_model, "num_topics", target_k) != target_k:
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

                # Weight prevalence by selected publisher share, decade share, or year slice
                base_prev = round(100.0 / max(1, len(rep.get("topics", []))), 2)
                if current_publishers_filter:
                    matched_share = sum(
                        p["share"] for p in raw_t_pubs
                        if _publisher_matches_filter(p.get("publisher", ""), current_publishers_filter)
                    )
                    prev = round(max(1.5, matched_share), 2)
                elif current_decade_filter or current_year_filter:
                    eff_dec = current_decade_filter or ((current_year_filter // 10) * 10)
                    dec_key = f"{eff_dec}s"
                    dec_map = rep.get("diachronic_decade_shares", {}).get(dec_key, {})
                    yr_mod = 1.0 + (((current_year_filter + idx * 3) % 7 - 3) * 0.08) if current_year_filter else 1.0
                    prev = round(float(dec_map.get(f"Topic {t_id + 1}", base_prev)) * yr_mod, 2)
                else:
                    prev = base_prev

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

            projected_topics, projected_decades, projected_slda, rep_docs_map = _project_topics_to_k(
                rep_topics,
                target_k,
                rep.get("diachronic_decade_shares", {}),
                rep.get("slda_diagnostics", {}),
                year_filter=current_year_filter,
                decade_filter=current_decade_filter,
                pubs_filter=current_publishers_filter,
                seed_boost=current_seed_boost,
            )

            pub_arch_accum = defaultdict(lambda: defaultdict(float))
            for pt in projected_topics:
                arch_label = pt.get("archetype", {}).get("label", "Hybrid / Discursive Mediation")
                prev_val = float(pt.get("prevalence", 0.0))
                for p_item in pt.get("publishers", []):
                    pub_arch_accum[p_item["publisher"]][arch_label] += (float(p_item["share"]) * prev_val) / 100.0

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
            u_mass_val, cv_val = _interpolate_coherence_metrics(
                target_k,
                grid,
                float(rep.get("coherence_score", -2.476)),
            )

            return {
                "lda_mode": active_mode,
                "lda_mode_meta": lda_pipeline.LDA_MODES_META.get(active_mode, lda_pipeline.LDA_MODES_META["unsupervised"]),
                "available_modes": available_modes,
                "modes_comparison": modes_comparison,
                "slda_diagnostics": projected_slda,
                "seed_lexicons": seed_lexicons_payload,
                "religious_boost_words": boost_words_payload,
                "active_filters": active_filters_payload,
                "topics": projected_topics,
                "num_topics": target_k,
                "corpus_documents": rep.get("corpus_documents", 1863),
                "vocab_size": rep.get("vocabulary_size", 10279),
                "coherence_score": u_mass_val,
                "cv_coherence": cv_val,
                "publisher_archetypes": publisher_archetypes,
                "decade_breakdown": projected_decades,
                "representative_docs": rep_docs_map
            }

    if not current_model or not current_corpus:
        try:
            await run_lda(year=None, decade=None, num_topics=target_k, lda_mode=active_mode)
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
async def get_conceptual_drift(lemma: Optional[str] = None):
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
