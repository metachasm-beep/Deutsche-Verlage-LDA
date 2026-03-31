from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import lda_pipeline
import config
import pandas as pd
import shutil

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
current_viz_html = ""

# Since Vercel serverless environment represents a readonly filesystem except for /tmp
# we conditionally set the storage path.
DATA_STORAGE_DIR = "/tmp/data" if os.environ.get("VERCEL") else "data"
os.makedirs(DATA_STORAGE_DIR, exist_ok=True)
REAL_DATA_PATH = os.path.join(DATA_STORAGE_DIR, "dnb_metadata.csv")

# Copy the default data to tmp if it exists locally and not in tmp yet
if not os.path.exists(REAL_DATA_PATH) and os.path.exists("data/dnb_metadata.csv"):
    shutil.copy("data/dnb_metadata.csv", REAL_DATA_PATH)

@app.get("/api/health")
async def health():
    return {"status": "ok", "mode": "PhD Research API Active"}

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
        
        # Verify it's readable by Pandas
        df = pd.read_csv(file_location)
        if 'publisher' not in df.columns or 'date' not in df.columns:
            os.remove(file_location)
            raise HTTPException(status_code=400, detail="CSV must contain 'publisher' and 'date' columns.")
        
        return {"status": "success", "message": f"Dataset {file.filename} ingested successfully, containing {len(df)} records."}
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="CSV is empty.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run-lda")
async def run_lda(year: int = Query(None)):
    global current_model, current_corpus, current_dictionary, current_viz_html
    
    data_path = REAL_DATA_PATH if os.path.exists(REAL_DATA_PATH) else config.MOCK_DATA_PATH
    
    try:
        if year:
            df = pd.read_csv(data_path)
            # Filter by year
            df = df[df['date'].astype(str).str.contains(str(year))]
            if df.empty:
                raise HTTPException(status_code=404, detail=f"No records found for year {year}")
            
            filtered_path = os.path.join(DATA_STORAGE_DIR, f"filtered_{year}.csv")
            df.to_csv(filtered_path, index=False)
            data_path = filtered_path

        current_model, current_corpus, current_dictionary = lda_pipeline.run_pipeline(data_path)
        current_viz_html = lda_pipeline.get_viz_html(current_model, current_corpus, current_dictionary)
        return {"status": "success", "year_filtered": year}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trends")
async def get_trends():
    """
    Returns year-by-year counts for the 'Live Graph'.
    """
    data_path = REAL_DATA_PATH if os.path.exists(REAL_DATA_PATH) else config.MOCK_DATA_PATH
    df = pd.read_csv(data_path)
    df['year_clean'] = df['date'].astype(str).str.extract(r'(\d{4})')
    trends = df.groupby(['year_clean', 'publisher']).size().unstack(fill_value=0).reset_index()
    return trends.to_dict(orient="records")

@app.get("/api/topic-viz", response_class=HTMLResponse)
async def get_viz():
    if not current_viz_html:
        return "<html><body style='color: white; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;'><h3>No model trained yet. Please click 'Execute Full Analysis'</h3></body></html>"
    return current_viz_html

@app.get("/api/data-summary")
async def data_summary():
    data_path = REAL_DATA_PATH if os.path.exists(REAL_DATA_PATH) else config.MOCK_DATA_PATH
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        return {
            "source": "Custom Upload" if os.environ.get("VERCEL") or data_path == REAL_DATA_PATH else "Mock Data",
            "count": len(df),
            "publishers": df['publisher'].unique().tolist(),
            "first_titles": df['title'].head(5).tolist() if 'title' in df.columns else []
        }
    return {"source": "Unknown Data", "count": 0}

# Local Testing Serve React
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
