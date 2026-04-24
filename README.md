# 🧠 Intelligent Log Anomaly Detection System

A production-grade platform that ingests logs from distributed services in real-time, uses transformer-based ML to detect anomalies, and generates root cause explanations via a RAG pipeline.

## Architecture
![Architecture Diagram](architecture.png)

## Tech Stack
- **ML:** Sentence-Transformers, FAISS, Isolation Forest, Scikit-learn
- **Backend:** FastAPI, Python
- **DevOps:** Docker, GitHub Actions (Week 2)
- **Dashboard:** Streamlit (Week 2)

## Project Structure
```
log-anomaly-detection/
├── ingestion/        # Log generation & streaming pipeline
├── model/            # RAG explainer module
├── api/              # FastAPI backend
│   ├── main.py       # API endpoints
│   └── predictor.py  # ML inference engine
├── dashboard/        # Streamlit frontend (Day 11)
├── tests/            # Test suite (Day 10)
└── data/             # Embeddings, FAISS index, model files
```

## API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service health check |
| POST | `/ingest` | Ingest single log, returns anomaly status |
| POST | `/ingest/batch` | Ingest multiple logs at once |
| GET | `/anomalies` | Fetch recent detected anomalies |
| GET | `/explain/{log_id}` | RAG explanation for a log entry |

## Quickstart
```bash
# Install dependencies
pip install -r requirements.txt

# Run the API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Visit interactive docs
http://localhost:8000/docs
```

## Benchmarks
- Anomaly detection recall: **91%**
- False positive rate: **4%**
- FAISS similarity search: sub-millisecond
- API response time: ~200ms per log (including embedding generation)

## Sample Response
```json
{
  "is_anomaly": true,
  "anomaly_score": -0.523,
  "severity": "CRITICAL",
  "explanation": "Anomaly on payment-service/checkout — high latency combined with server errors suggests downstream dependency failure. With 3 similar incidents found in history, this pattern suggests recurring instability.",
  "similar_cases": [
    {
      "service": "payment-service",
      "endpoint": "/checkout",
      "status_code": 500,
      "latency_ms": 6821.3
    }
  ]
}
```