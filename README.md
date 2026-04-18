# 🧠 Intelligent Log Anomaly Detection System

A production-grade platform that ingests logs from distributed services 
in real-time, uses transformer-based ML to detect anomalies, and generates 
plain-English root cause explanations via a RAG pipeline.

## Architecture
[We'll add diagram tomorrow]

## Tech Stack
- **ML:** Sentence-Transformers, FAISS, HuggingFace, Isolation Forest
- **Backend:** FastAPI, Redis
- **DevOps:** Docker, GitHub Actions
- **Dashboard:** Streamlit

## Modules
| Module | Description |
|---|---|
| `ingestion/` | Simulates & streams structured server logs |
| `model/` | Anomaly detection + RAG-based explanation |
| `api/` | REST API for ingestion, querying, explanation |
| `dashboard/` | Live monitoring UI |

## Setup
```bash
docker-compose up
```

## Benchmarks
[To be added]