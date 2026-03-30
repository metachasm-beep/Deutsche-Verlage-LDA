from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import lda_pipeline
import config
import pandas as pd

app = FastAPI(title="The Computational Turn: LDA Dashboard")

# Global variables to store the model state
current_model = None
current_corpus = None
current_dictionary = None
current_viz_html = ""

# Path to the data file
REAL_DATA_PATH = "data/dnb_metadata.csv"

@app.get("/")
async def read_index():
    return FileResponse('app/index.html')

@app.get("/styles.css")
async def read_css():
    return FileResponse('app/style.css')

@app.get("/health")
async def health():
    return {"status": "ok", "mode": "PhD Research"}

@app.post("/run-lda")
async def run_lda():
    global current_model, current_corpus, current_dictionary, current_viz_html
    
    # Check if we have data
    data_path = REAL_DATA_PATH if os.path.exists(REAL_DATA_PATH) else config.MOCK_DATA_PATH
    
    try:
        current_model, current_corpus, current_dictionary = lda_pipeline.run_pipeline(data_path)
        current_viz_html = lda_pipeline.get_viz_html(current_model, current_corpus, current_dictionary)
        return {"status": "success", "message": f"LDA completed on {data_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/topic-viz", response_class=HTMLResponse)
async def get_viz():
    if not current_viz_html:
        return "<html><body><h3>No model trained yet. Please click 'Run LDA'</h3></body></html>"
    return current_viz_html

@app.get("/data-summary")
async def data_summary():
    if os.path.exists(REAL_DATA_PATH):
        df = pd.read_csv(REAL_DATA_PATH)
        return {
            "source": "DNB Harvest",
            "count": len(df),
            "publishers": df['publisher'].unique().tolist(),
            "first_titles": df['title'].head(5).tolist()
        }
    return {"source": "Mock Data", "count": 15}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
