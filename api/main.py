from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.predictor import AnomalyPredictor

app = FastAPI(
    title="Log Anomaly Detection API",
    description="Real-time log anomaly detection with RAG-powered root cause explanation",
    version="1.0.0"
)

# Load predictor once at startup
predictor = AnomalyPredictor(
    embeddings_path="data/embeddings.npy",
    index_path="data/logs.faiss",
    logs_path="data/logs_with_predictions.csv",
    model_path="data/isolation_forest.pkl",
    scaler_path="data/scaler.pkl"
)

# --- Request/Response Models ---
class LogEntry(BaseModel):
    service: str
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    ip: Optional[str] = "0.0.0.0"
    user_id: Optional[str] = "unknown"

class AnomalyResponse(BaseModel):
    is_anomaly: bool
    anomaly_score: float
    severity: str
    explanation: Optional[str] = None
    similar_cases: Optional[list] = None

class BatchResponse(BaseModel):
    total: int
    anomalies_found: int
    anomaly_rate: float
    results: list

# --- Endpoints ---
@app.get("/")
def root():
    return {
        "name": "Log Anomaly Detection API",
        "version": "1.0.0",
        "endpoints": ["/ingest", "/anomalies", "/explain/{log_id}"]
    }

@app.get("/health")
def health():
    return {"status": "healthy", "model_loaded": predictor is not None}

@app.post("/ingest", response_model=AnomalyResponse)
def ingest_log(log: LogEntry):
    """
    Ingest a single log entry and check if it's anomalous.
    Returns anomaly status, score, and severity.
    """
    try:
        result = predictor.predict(log.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/batch", response_model=BatchResponse)
def ingest_batch(logs: list[LogEntry]):
    """
    Ingest multiple log entries at once.
    Returns summary and per-log results.
    """
    if len(logs) > 1000:
        raise HTTPException(status_code=400, detail="Batch size limit is 1000 logs")
    try:
        results = [predictor.predict(log.dict()) for log in logs]
        anomalies = [r for r in results if r['is_anomaly']]
        return {
            "total": len(logs),
            "anomalies_found": len(anomalies),
            "anomaly_rate": round(len(anomalies) / len(logs), 3),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/anomalies")
def get_anomalies(limit: int = 10):
    """
    Returns the most recent anomalies detected in the system.
    """
    try:
        anomalies = predictor.get_recent_anomalies(limit=limit)
        return {"count": len(anomalies), "anomalies": anomalies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/explain/{log_id}")
def explain(log_id: int):
    """
    Returns RAG-powered root cause explanation for a specific log entry.
    """
    try:
        result = predictor.explain(log_id)
        if not result:
            raise HTTPException(status_code=404, detail="Log not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))