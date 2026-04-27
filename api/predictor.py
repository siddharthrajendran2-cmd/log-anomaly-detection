import numpy as np
import pandas as pd
import faiss
import pickle
from sentence_transformers import SentenceTransformer


class AnomalyPredictor:
    def __init__(self, embeddings_path, index_path, logs_path, model_path, scaler_path):
        print("Loading models...")
        self.embeddings = np.load(embeddings_path).astype('float32')
        self.index = faiss.read_index(index_path)
        self.df = pd.read_csv(logs_path)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.recent_anomalies = []

        with open(model_path, 'rb') as f:
            self.iso_forest = pickle.load(f)
        with open(scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)

        print("All models loaded.")

    def log_to_text(self, log):
        status = log['status_code']
        latency = log['latency_ms']
        severity = "HIGH_ERROR HIGH_LATENCY" if (status >= 500 and latency > 1000) else \
                   "ERROR" if status >= 500 else \
                   "SLOW" if latency > 1000 else "NORMAL"
        return (f"service={log['service']} endpoint={log['endpoint']} "
                f"method={log['method']} status={status} status={status} "
                f"latency={latency}ms latency={latency}ms severity={severity}")

    def get_severity(self, score):
        if score < -0.52:
            return "CRITICAL"
        elif score < -0.50:
            return "HIGH"
        elif score < -0.48:
            return "MEDIUM"
        else:
            return "LOW"

    def retrieve_similar(self, log, k=3):
        text = self.log_to_text(log)
        emb = self.embedder.encode([text]).astype('float32')
        distances, indices = self.index.search(emb, k + 1)
        similar = []
        for dist, idx in zip(distances[0], indices[0]):
            row = self.df.iloc[idx]
            if row['anomaly'] == True and dist > 0:
                similar.append({
                    "service": row['service'],
                    "endpoint": row['endpoint'],
                    "status_code": int(row['status_code']),
                    "latency_ms": float(row['latency_ms'])
                })
            if len(similar) == k:
                break
        return similar

    def generate_explanation(self, log, similar_cases):
        service = log['service']
        status = log['status_code']
        latency = log['latency_ms']

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
            issue = "unusual traffic pattern detected"
            action = f"Review access logs for {service} for suspicious activity"

        similar_text = f"{len(similar_cases)} similar incidents found in history" \
                      if similar_cases else "no similar past incidents"

        return (f"Anomaly on {service}{log['endpoint']} — {issue}. "
                f"With {similar_text}, this pattern suggests recurring instability. {action}.")

    def predict(self, log: dict):
        # Build features
        text = self.log_to_text(log)
        embedding = self.embedder.encode([text]).astype('float32')

        raw = np.array([[
            log['status_code'],
            log['latency_ms'],
            int(log['status_code'] >= 500),
            int(log['latency_ms'] > 1000)
        ]])
        raw_scaled = self.scaler.transform(raw)
        features = np.hstack([embedding, raw_scaled])

        # Predict
        pred = self.iso_forest.predict(features)[0]
        score = float(self.iso_forest.score_samples(features)[0])
        is_anomaly = pred == -1

        result = {
            "is_anomaly": bool(is_anomaly),  # convert numpy.bool to Python bool
            "anomaly_score": round(float(score), 4),
            "severity": self.get_severity(score) if is_anomaly else "NONE",
            "log": log,
            "similar_cases": None,
            "explanation": None
        }

        # If anomaly, enrich with RAG explanation
        if is_anomaly:
            similar = self.retrieve_similar(log)
            result['similar_cases'] = similar
            result['explanation'] = self.generate_explanation(log, similar)
            self.recent_anomalies.insert(0, result.copy())
            self.recent_anomalies = self.recent_anomalies[:100]  # keep last 100

        return result

    def get_recent_anomalies(self, limit=10):
        return [
            {k: v for k, v in a.items() if k != "log"}
            for a in self.recent_anomalies[:limit]
        ]

    def explain(self, log_id: int):
        if log_id >= len(self.df):
            return None
        row = self.df.iloc[log_id]
        log = {
            "service": row['service'],
            "endpoint": row['endpoint'],
            "method": row['method'],
            "status_code": int(row['status_code']),
            "latency_ms": float(row['latency_ms'])
        }
        similar = self.retrieve_similar(log)
        explanation = self.generate_explanation(log, similar)
        return {
            "log_id": log_id,
            "log": log,
            "similar_cases": similar,
            "explanation": explanation
        }