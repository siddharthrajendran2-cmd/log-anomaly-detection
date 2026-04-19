import random
import time
import json
from datetime import datetime
from faker import Faker

fake = Faker()

SERVICES = ["auth-service", "payment-service", "user-service", "inventory-service", "api-gateway"]
ENDPOINTS = ["/login", "/checkout", "/profile", "/search", "/health", "/orders"]
NORMAL_STATUS_WEIGHTS = [70, 15, 10, 3, 2]  # 200, 201, 301, 404, 500
STATUS_CODES = [200, 201, 301, 404, 500]

def generate_log(anomaly=False):
    service = random.choice(SERVICES)
    endpoint = random.choice(ENDPOINTS)
    method = random.choice(["GET", "POST", "PUT", "DELETE"])

    if anomaly:
        # Anomalies: high latency + lots of 500s
        status = random.choices([500, 503, 404], weights=[60, 30, 10])[0]
        latency = round(random.uniform(2000, 8000), 2)  # ms
    else:
        status = random.choices(STATUS_CODES, weights=NORMAL_STATUS_WEIGHTS)[0]
        latency = round(random.uniform(50, 400), 2)  # ms

    log = {
        "timestamp": datetime.utcnow().isoformat(),
        "service": service,
        "endpoint": endpoint,
        "method": method,
        "status_code": status,
        "latency_ms": latency,
        "ip": fake.ipv4(),
        "user_id": fake.uuid4(),
        "anomaly": anomaly  # ground truth label for training
    }
    return log

def stream_logs(count=1000, anomaly_rate=0.05, delay=0):
    logs = []
    for i in range(count):
        is_anomaly = random.random() < anomaly_rate
        log = generate_log(anomaly=is_anomaly)
        logs.append(log)
        if delay:
            print(json.dumps(log))
            time.sleep(delay)
    return logs

if __name__ == "__main__":
    print("Streaming logs... (Ctrl+C to stop)\n")
    stream_logs(count=20, delay=0.5)