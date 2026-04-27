import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "name" in response.json()

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_ingest_normal_log():
    response = client.post("/ingest", json={
        "service": "auth-service",
        "endpoint": "/login",
        "method": "POST",
        "status_code": 200,
        "latency_ms": 120.5
    })
    assert response.status_code == 200
    data = response.json()
    assert "is_anomaly" in data
    assert "anomaly_score" in data
    assert "severity" in data

def test_ingest_anomalous_log():
    response = client.post("/ingest", json={
        "service": "payment-service",
        "endpoint": "/checkout",
        "method": "POST",
        "status_code": 500,
        "latency_ms": 7500.0
    })
    assert response.status_code == 200
    data = response.json()
    assert data["is_anomaly"] == True
    assert data["severity"] in ["HIGH", "CRITICAL"]
    assert data["explanation"] is not None

def test_ingest_missing_fields():
    response = client.post("/ingest", json={
        "service": "auth-service"
        # missing required fields
    })
    assert response.status_code == 422  # validation error

def test_batch_ingest():
    response = client.post("/ingest/batch", json=[
        {"service": "auth-service", "endpoint": "/login", "method": "GET", "status_code": 200, "latency_ms": 95.0},
        {"service": "api-gateway", "endpoint": "/search", "method": "POST", "status_code": 500, "latency_ms": 6000.0}
    ])
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["anomalies_found"] >= 1

def test_get_anomalies():
    response = client.get("/anomalies")
    assert response.status_code == 200
    assert "anomalies" in response.json()

def test_explain():
    response = client.get("/explain/1")
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data
    assert "similar_cases" in data

def test_batch_size_limit():
    logs = [{"service": "auth-service", "endpoint": "/login", "method": "GET",
             "status_code": 200, "latency_ms": 95.0}] * 1001
    response = client.post("/ingest/batch", json=logs)
    assert response.status_code == 400