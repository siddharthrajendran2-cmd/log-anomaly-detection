from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.predictor import AnomalyPredictor
from api.cache import AnomalyCache

app = FastAPI(
    title="Log Anomaly Detection API",
    description="Real-time log anomaly detection with RAG-powered root cause explanation",
    version="1.0.0"
)

# Load predictor and cache once at startup
predictor = AnomalyPredictor(
    embeddings_path="data/embeddings.npy",
    index_path="data/logs.faiss",
    logs_path="data/logs_with_predictions.csv",
    model_path="data/isolation_forest.pkl",
    scaler_path="data/scaler.pkl"
)

cache = AnomalyCache(host='localhost', port=6379, ttl=60)

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
    return {
        "status": "healthy",
        "model_loaded": predictor is not None,
        "cache": cache.get_stats()
    }

@app.post("/ingest", response_model=AnomalyResponse)
def ingest_log(log: LogEntry):
    """Ingest a single log — checks cache first, runs ML if cache miss."""
    log_dict = log.dict()

    # Check cache first
    cached = cache.get(log_dict)
    if cached:
        return cached

    # Cache miss — run ML pipeline
    result = predictor.predict(log_dict)

    # Store in cache for next time
    cache.set(log_dict, result)

    return result

@app.post("/ingest/batch", response_model=BatchResponse)
def ingest_batch(logs: list[LogEntry]):
    """Ingest multiple logs — each log checked against cache individually."""
    if len(logs) > 1000:
        raise HTTPException(status_code=400, detail="Batch size limit is 1000 logs")
    try:
        results = []
        for log in logs:
            log_dict = log.dict()
            cached = cache.get(log_dict)
            if cached:
                results.append(cached)
            else:
                result = predictor.predict(log_dict)
                cache.set(log_dict, result)
                results.append(result)

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
    """Returns the most recent anomalies detected."""
    try:
        anomalies = predictor.get_recent_anomalies(limit=limit)
        return {"count": len(anomalies), "anomalies": anomalies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache/stats")
def cache_stats():
    """Returns Redis cache statistics — hit rate, memory usage, total keys."""
    return cache.get_stats()

@app.get("/explain/{log_id}")
def explain(log_id: int):
    """Returns RAG-powered root cause explanation for a specific log entry."""
    try:
        result = predictor.explain(log_id)
        if not result:
            raise HTTPException(status_code=404, detail="Log not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))