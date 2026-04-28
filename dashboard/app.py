import streamlit as st
import requests
import json
import time
import random
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime

# --- Config ---
API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Log Anomaly Detection",
    page_icon="🧠",
    layout="wide"
)

# --- Header ---
st.title("🧠 Intelligent Log Anomaly Detection")
st.markdown("Real-time monitoring powered by Transformer embeddings + RAG explanation engine")
st.divider()

# --- Session state for storing logs ---
if "logs" not in st.session_state:
    st.session_state.logs = []
if "anomalies" not in st.session_state:
    st.session_state.anomalies = []

# --- Sidebar controls ---
st.sidebar.title("⚙️ Controls")
auto_generate = st.sidebar.toggle("Auto-generate logs", value=False)
anomaly_rate = st.sidebar.slider("Anomaly rate", 0.0, 1.0, 0.1, 0.05)
refresh_rate = st.sidebar.slider("Refresh rate (seconds)", 1, 10, 3)
batch_size = st.sidebar.slider("Logs per batch", 1, 20, 5)

st.sidebar.divider()
st.sidebar.markdown("### Manual Log Injection")
service = st.sidebar.selectbox("Service", [
    "auth-service", "payment-service", "user-service",
    "inventory-service", "api-gateway"
])
endpoint = st.sidebar.selectbox("Endpoint", [
    "/login", "/checkout", "/profile", "/search", "/health", "/orders"
])
method = st.sidebar.selectbox("Method", ["GET", "POST", "PUT", "DELETE"])
status_code = st.sidebar.selectbox("Status Code", [200, 201, 301, 404, 500, 503])
latency_ms = st.sidebar.slider("Latency (ms)", 50, 9000, 200)

if st.sidebar.button("🚀 Send Log"):
    log = {
        "service": service,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "latency_ms": float(latency_ms)
    }
    try:
        response = requests.post(f"{API_URL}/ingest", json=log, timeout=10)
        result = response.json()
        result["log"] = log
        result["timestamp"] = datetime.now().strftime("%H:%M:%S")
        st.session_state.logs.append(result)
        if result["is_anomaly"]:
            st.session_state.anomalies.append(result)
        st.sidebar.success("Log sent!" if not result["is_anomaly"] else "⚠️ Anomaly detected!")
    except Exception as e:
        st.sidebar.error(f"API error: {e}")

# --- Log generator ---
SERVICES = ["auth-service", "payment-service", "user-service", "inventory-service", "api-gateway"]
ENDPOINTS = ["/login", "/checkout", "/profile", "/search", "/health", "/orders"]
METHODS = ["GET", "POST", "PUT", "DELETE"]

def generate_random_log(anomaly=False):
    if anomaly:
        return {
            "service": random.choice(SERVICES),
            "endpoint": random.choice(ENDPOINTS),
            "method": random.choice(METHODS),
            "status_code": random.choice([500, 503]),
            "latency_ms": float(random.randint(2000, 9000))
        }
    return {
        "service": random.choice(SERVICES),
        "endpoint": random.choice(ENDPOINTS),
        "method": random.choice(METHODS),
        "status_code": random.choice([200, 200, 200, 201, 301, 404]),
        "latency_ms": float(random.randint(50, 400))
    }

# --- Auto generate logs ---
if auto_generate:
    logs_to_send = []
    for _ in range(batch_size):
        is_anomaly = random.random() < anomaly_rate
        logs_to_send.append(generate_random_log(anomaly=is_anomaly))

    try:
        response = requests.post(f"{API_URL}/ingest/batch", json=logs_to_send, timeout=30)
        results = response.json()
        for i, result in enumerate(results["results"]):
            result["log"] = logs_to_send[i]
            result["timestamp"] = datetime.now().strftime("%H:%M:%S")
            st.session_state.logs.append(result)
            if result["is_anomaly"]:
                st.session_state.anomalies.append(result)
    except Exception as e:
        st.error(f"API error: {e}")

# --- Metrics row ---
total_logs = len(st.session_state.logs)
total_anomalies = len(st.session_state.anomalies)
anomaly_rate_actual = (total_anomalies / total_logs * 100) if total_logs > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Logs", total_logs)
col2.metric("Anomalies Detected", total_anomalies)
col3.metric("Anomaly Rate", f"{anomaly_rate_actual:.1f}%")
col4.metric("API Status", "🟢 Online" if total_logs >= 0 else "🔴 Offline")

st.divider()

# --- Charts ---
if st.session_state.logs:
    df = pd.DataFrame([{
        "timestamp": l["timestamp"],
        "service": l["log"]["service"],
        "status_code": l["log"]["status_code"],
        "latency_ms": l["log"]["latency_ms"],
        "is_anomaly": l["is_anomaly"],
        "severity": l.get("severity", "NONE")
    } for l in st.session_state.logs])

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Latency Distribution")
        fig = px.histogram(
            df, x="latency_ms", color="is_anomaly",
            color_discrete_map={True: "#ef4444", False: "#22c55e"},
            labels={"is_anomaly": "Anomaly", "latency_ms": "Latency (ms)"},
            nbins=30
        )
        fig.update_layout(height=300, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🔥 Anomalies by Service")
        if total_anomalies > 0:
            anomaly_df = pd.DataFrame([{
                "service": a["log"]["service"]
            } for a in st.session_state.anomalies])
            service_counts = anomaly_df["service"].value_counts().reset_index()
            service_counts.columns = ["service", "count"]
            fig2 = px.bar(
                service_counts, x="service", y="count",
                color="count", color_continuous_scale="Reds"
            )
            fig2.update_layout(height=300, margin=dict(t=20, b=20))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No anomalies detected yet.")

    st.divider()

    # --- Status code breakdown ---
    st.subheader("📈 Status Code Breakdown")
    status_counts = df["status_code"].value_counts().reset_index()
    status_counts.columns = ["status_code", "count"]
    status_counts["status_code"] = status_counts["status_code"].astype(str)
    fig3 = px.pie(status_counts, names="status_code", values="count",
                  color_discrete_sequence=px.colors.qualitative.Set3)
    fig3.update_layout(height=300, margin=dict(t=20, b=20))
    st.plotly_chart(fig3, use_container_width=True)

else:
    st.info("No logs yet — send a log from the sidebar or enable auto-generation.")

st.divider()

# --- Anomaly feed ---
st.subheader("🚨 Recent Anomalies")
if st.session_state.anomalies:
    for anomaly in reversed(st.session_state.anomalies[-5:]):
        with st.expander(
            f"⚠️ [{anomaly['timestamp']}] {anomaly['log']['service']} → "
            f"{anomaly['log']['endpoint']} | {anomaly['severity']}",
            expanded=True
        ):
            col1, col2, col3 = st.columns(3)
            col1.metric("Status Code", anomaly['log']['status_code'])
            col2.metric("Latency", f"{anomaly['log']['latency_ms']}ms")
            col3.metric("Anomaly Score", anomaly['anomaly_score'])

            if anomaly.get("similar_cases"):
                st.markdown("**Similar past incidents:**")
                for case in anomaly["similar_cases"]:
                    st.markdown(
                        f"- `{case['service']}` → `{case['endpoint']}` | "
                        f"Status: {case['status_code']} | Latency: {case['latency_ms']}ms"
                    )

            if anomaly.get("explanation"):
                st.info(f"🔍 **Root Cause:** {anomaly['explanation']}")
else:
    st.success("✅ No anomalies detected yet.")

st.divider()

# --- Raw log feed ---
st.subheader("📋 Recent Log Feed")
if st.session_state.logs:
    recent = st.session_state.logs[-10:]
    for log in reversed(recent):
        color = "🔴" if log["is_anomaly"] else "🟢"
        st.markdown(
            f"{color} `{log['timestamp']}` | "
            f"**{log['log']['service']}** → `{log['log']['endpoint']}` | "
            f"Status: `{log['log']['status_code']}` | "
            f"Latency: `{log['log']['latency_ms']}ms` | "
            f"Severity: `{log.get('severity', 'NONE')}`"
        )
else:
    st.info("No logs yet.")

# --- Auto refresh ---
if auto_generate:
    time.sleep(refresh_rate)
    st.rerun()