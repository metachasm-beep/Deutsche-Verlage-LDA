from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import lda_pipeline
import config
import csv
import re
import shutil
from collections import defaultdict

app = FastAPI(title="The Computational Turn: LDA Dashboard")

# CORS config to allow the Vercel deployed frontend and localhost testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://deutscheverlagelda.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to store the model state (Vercel serverless functions are ephemeral!)
# In a robust production environment, these would be dumped to S3 or a database.
current_model = None
current_corpus = None
current_dictionary = None
current_coherence = 0.0
current_top_docs = {}
current_viz_html = ""

# Since Vercel serverless environment represents a readonly filesystem except for /tmp
# we conditionally set the storage path.
DATA_STORAGE_DIR = "/tmp/data" if os.environ.get("VERCEL") else "data"
os.makedirs(DATA_STORAGE_DIR, exist_ok=True)
REAL_DATA_PATH = os.path.join(DATA_STORAGE_DIR, "dnb_metadata.csv")

# Copy the default data to tmp if it exists locally and not in tmp yet
DEFAULT_DATA_SOURCE = os.path.join(config.DATA_DIR, "dnb_metadata.csv")
if not os.path.exists(REAL_DATA_PATH) and os.path.exists(DEFAULT_DATA_SOURCE):
    shutil.copy(DEFAULT_DATA_SOURCE, REAL_DATA_PATH)

@app.get("/api/health")
async def health():
    return {"status": "ok", "mode": "PhD Research API Active"}

@app.get("/api/debug-fs")
async def debug_fs():
    """
    Diagnostic endpoint to see what files are actually present in the serverless environment.
    """
    import os
    results = {}
    try:
        results["cwd"] = os.getcwd()
        results["base_dir"] = config.BASE_DIR
        results["data_dir"] = config.DATA_DIR
        results["root_files"] = os.listdir(".")
        if os.path.exists("app"):
            results["app_files"] = os.listdir("app")
            if os.path.exists("app/data"):
                results["app_data_files"] = os.listdir("app/data")
        
        # Check specifically for the mock file
        results["mock_file_exists"] = os.path.exists(config.MOCK_DATA_PATH)
        results["mock_path_abs"] = os.path.abspath(config.MOCK_DATA_PATH)
        
    except Exception as e:
        results["error"] = str(e)
    return results

@app.post("/api/upload-dataset")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Receives a custom CSV dataset from the researcher.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
    
    try:
        # Save to ephemeral or local storage securely
        file_location = REAL_DATA_PATH
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        
        # Verify it's readable and check columns
        with open(file_location, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            if not headers or 'publisher' not in headers or 'date' not in headers:
                os.remove(file_location)
                raise HTTPException(status_code=400, detail="CSV must contain 'publisher' and 'date' columns.")
            
            count = sum(1 for row in reader)
        
        return {"status": "success", "message": f"Dataset {file.filename} ingested successfully, containing {count} records."}
    except Exception as e:
        if os.path.exists(REAL_DATA_PATH): os.remove(REAL_DATA_PATH)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset-to-mock")
async def reset_to_mock():
    """
    Deletes any uploaded custom dataset and resets the model state to force return to mock data.
    """
    global current_model, current_corpus, current_dictionary, current_viz_html
    
    try:
        if os.path.exists(REAL_DATA_PATH):
            os.remove(REAL_DATA_PATH)
        
        # Reset model state
        current_model = None
        current_corpus = None
        current_dictionary = None
        current_coherence = 0.0
        current_top_docs = {}
        current_viz_html = ""
        
        return {"status": "success", "message": "Reverted to Demo Corpus (Voices on Religion)."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run-lda")
async def run_lda(year: int = Query(None), decade: int = Query(None)):
    global current_model, current_corpus, current_dictionary, current_viz_html
    
    data_path = REAL_DATA_PATH if os.path.exists(REAL_DATA_PATH) else config.MOCK_DATA_PATH
    
    try:
        # Filter logic for Year or Decade
        if year or decade:
            rows = []
            with open(data_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                for row in reader:
                    date_val = str(row.get('date', ''))
                    match = re.search(r'(\d{4})', date_val)
                    if not match: continue
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
            with open(filtered_path, mode='w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            data_path = filtered_path

        current_model, current_corpus, current_dictionary, current_coherence, current_top_docs = lda_pipeline.run_pipeline(data_path)
        current_viz_html = lda_pipeline.get_viz_html(current_model, current_corpus, current_dictionary)
        return {"status": "success", "year_filtered": year, "decade_filtered": decade}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trends")
async def get_trends():
    """
    Returns year-by-year counts for the 'Live Graph'.
    Replaces pandas groupby/unstack logic.
    """
    data_path = REAL_DATA_PATH if os.path.exists(REAL_DATA_PATH) else config.MOCK_DATA_PATH
    
    data_map = defaultdict(lambda: defaultdict(int))
    publishers = set()
    
    try:
        with open(data_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = str(row.get('date', ''))
                match = re.search(r'(\d{4})', date_str)
                year = match.group(1) if match else "Unknown"
                
                pub = row.get('publisher', 'N/A')
                data_map[year][pub] += 1
                publishers.add(pub)
                
        result = []
        for year in sorted(data_map.keys()):
            item = {"year_clean": year}
            for pub in publishers:
                item[pub] = data_map[year][pub]
            result.append(item)
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/topic-viz", response_class=HTMLResponse)
async def get_viz():
    if not current_viz_html or "Disabled" in current_viz_html:
        return f"<html><body style='color: white; background: #0f172a; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;'><div><h3>Visualization optimized for React</h3><p>pyLDAvis is disabled to reduce server load. Switching to native React components.</p></div></body></html>"
    return current_viz_html

@app.get("/api/topics")
async def get_topics():
    if not current_model or not current_corpus:
        return {"topics": []}
    
    # Calculate topic prevalence across the entire corpus
    # This sums the probability of each topic across all documents
    topic_prevalence = defaultdict(float)
    doc_count = len(current_corpus)
    
    if doc_count > 0:
        for doc in current_corpus:
            doc_topics = current_model.get_document_topics(doc)
            for topic_id, prob in doc_topics:
                topic_prevalence[topic_id] += prob
        
        # Convert to percentage
        for tid in topic_prevalence:
            topic_prevalence[tid] = (topic_prevalence[tid] / doc_count) * 100

    # Extract topics with weights and prevalence
    topics = []
    for topic_id, words in current_model.show_topics(num_topics=config.NUM_TOPICS, num_words=15, formatted=False):
        topics.append({
            "id": topic_id,
            "prevalence": round(topic_prevalence.get(topic_id, 0), 2),
            "keywords": [{"word": w, "weight": round(float(p), 4)} for w, p in words]
        })
    
    # Sort topics by prevalence (most common first)
    topics = sorted(topics, key=lambda x: x['prevalence'], reverse=True)
    return {
        "topics": topics,
        "coherence_score": round(current_coherence, 4),
        "representative_docs": current_top_docs
    }

@app.get("/api/data-summary")
async def data_summary():
    data_path = REAL_DATA_PATH if os.path.exists(REAL_DATA_PATH) else config.MOCK_DATA_PATH
    if os.path.exists(data_path):
        years = set()
        publishers = set()
        count = 0
        with open(data_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                count += 1
                y = row.get('year') or row.get('date')
                if y:
                    try:
                        years.add(int(str(y).strip()[:4]))
                    except: pass
                if 'publisher' in row: publishers.add(row['publisher'])
                
        return {
            "source": "Custom Upload" if os.environ.get("VERCEL") or data_path == REAL_DATA_PATH else "Mock Data",
            "count": count,
            "publishers": sorted(list(publishers))
        }
    return {"source": "Unknown Data", "count": 0}
    return {"source": "Unknown Data", "count": 0}

# Local Testing Serve React
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
