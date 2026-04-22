
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer

class RAGExplainer:
    def __init__(self, embeddings_path, index_path, logs_path):
        self.embeddings = np.load(embeddings_path).astype("float32")
        self.index = faiss.read_index(index_path)
        self.df = pd.read_csv(logs_path)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

    def log_to_text(self, log):
        status = log["status_code"]
        latency = log["latency_ms"]
        severity = "HIGH_ERROR HIGH_LATENCY" if (status >= 500 and latency > 1000) else \
                   "ERROR" if status >= 500 else \
                   "SLOW" if latency > 1000 else "NORMAL"
        return (f"service={log['service']} endpoint={log['endpoint']} "
                f"method={log['method']} status={status} status={status} "
                f"latency={latency}ms latency={latency}ms severity={severity}")

    def retrieve(self, log, k=3):
        text = self.log_to_text(log)
        emb = self.embedder.encode([text]).astype("float32")
        distances, indices = self.index.search(emb, k+1)
        similar = []
        for dist, idx in zip(distances[0], indices[0]):
            row = self.df.iloc[idx]
            if row["anomaly"] == True and dist > 0:
                similar.append({
                    "service": row["service"],
                    "endpoint": row["endpoint"],
                    "status_code": int(row["status_code"]),
                    "latency_ms": float(row["latency_ms"])
                })
            if len(similar) == k:
                break
        return similar

    def explain(self, log):
        similar = self.retrieve(log)
        service = log["service"]
        status = log["status_code"]
        latency = log["latency_ms"]

        if status >= 500 and latency > 1000:
            issue = "high latency combined with server errors suggests downstream dependency failure"
            action = f"Check database connection pool and upstream dependencies for {service}"
        elif status >= 500:
            issue = "server errors without high latency suggest application-level failure"
            action = f"Review application logs and recent deployments for {service}"
        elif latency > 1000:
            issue = "high latency without errors suggests resource contention or slow queries"
            action = f"Check CPU/memory usage and database query performance for {service}"
        else:
            issue = "unusual traffic pattern detected on this endpoint"
            action = f"Review access logs for {service} for suspicious activity"

        similar_count = len(similar)
        similar_text = f"{similar_count} similar incidents found in history" if similar_count > 0 else "no similar past incidents"

        explanation = (f"Anomaly detected on {service}{log['endpoint']} — {issue}. "
                      f"With {similar_text}, this pattern is consistent with a recurring instability. "
                      f"{action}.")

        return {"anomaly": log, "similar_cases": similar, "explanation": explanation}
