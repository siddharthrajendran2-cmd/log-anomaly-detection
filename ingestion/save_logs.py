import json
import os
from log_generator import stream_logs

def save_logs(count=1000, output_path="../data/logs.json"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    logs = stream_logs(count=count)
    with open(output_path, "w") as f:
        json.dump(logs, f, indent=2)
    
    total_anomalies = sum(1 for l in logs if l["anomaly"])
    print(f"Saved {count} logs to {output_path}")
    print(f"Anomalies: {total_anomalies} ({(total_anomalies/count)*100:.1f}%)")

if __name__ == "__main__":
    save_logs(count=1000)