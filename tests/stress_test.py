import requests
import random
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

API_URL = "http://localhost:8000"

SERVICES = ["auth-service", "payment-service", "user-service", "inventory-service", "api-gateway"]
ENDPOINTS = ["/login", "/checkout", "/profile", "/search", "/health", "/orders"]
METHODS = ["GET", "POST", "PUT", "DELETE"]

def generate_log(anomaly=False):
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

def send_single_log(anomaly_rate=0.05):
    is_anomaly = random.random() < anomaly_rate
    log = generate_log(anomaly=is_anomaly)
    start = time.time()
    try:
        response = requests.post(f"{API_URL}/ingest", json=log, timeout=30)
        latency = (time.time() - start) * 1000
        return {
            "success": response.status_code == 200,
            "latency_ms": latency,
            "is_anomaly": response.json().get("is_anomaly", False),
            "actual_anomaly": is_anomaly
        }
    except Exception as e:
        return {"success": False, "latency_ms": 0, "error": str(e)}

def run_sequential_test(count=100):
    print(f"\n{'='*50}")
    print(f"SEQUENTIAL TEST — {count} logs")
    print(f"{'='*50}")

    results = []
    start = time.time()

    for i in range(count):
        result = send_single_log()
        results.append(result)
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{count}")

    total_time = time.time() - start
    successful = [r for r in results if r.get("success")]
    latencies = [r["latency_ms"] for r in successful]
    anomalies_detected = sum(1 for r in successful if r.get("is_anomaly"))

    print(f"\nResults:")
    print(f"  Total time:        {total_time:.2f}s")
    print(f"  Successful:        {len(successful)}/{count}")
    print(f"  Throughput:        {len(successful)/total_time:.1f} requests/sec")
    print(f"  Avg latency:       {sum(latencies)/len(latencies):.1f}ms")
    print(f"  Min latency:       {min(latencies):.1f}ms")
    print(f"  Max latency:       {max(latencies):.1f}ms")
    print(f"  P95 latency:       {sorted(latencies)[int(len(latencies)*0.95)]:.1f}ms")
    print(f"  Anomalies found:   {anomalies_detected}")

    return {
        "total_time": total_time,
        "throughput": len(successful)/total_time,
        "avg_latency": sum(latencies)/len(latencies),
        "p95_latency": sorted(latencies)[int(len(latencies)*0.95)],
        "anomalies_detected": anomalies_detected
    }

def run_concurrent_test(count=200, workers=10):
    print(f"\n{'='*50}")
    print(f"CONCURRENT TEST — {count} logs, {workers} workers")
    print(f"{'='*50}")

    results = []
    start = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(send_single_log) for _ in range(count)]
        for i, future in enumerate(as_completed(futures)):
            results.append(future.result())
            if (i + 1) % 20 == 0:
                print(f"  Progress: {i+1}/{count}")

    total_time = time.time() - start
    successful = [r for r in results if r.get("success")]
    latencies = [r["latency_ms"] for r in successful]
    anomalies_detected = sum(1 for r in successful if r.get("is_anomaly"))

    print(f"\nResults:")
    print(f"  Total time:        {total_time:.2f}s")
    print(f"  Successful:        {len(successful)}/{count}")
    print(f"  Throughput:        {len(successful)/total_time:.1f} requests/sec")
    print(f"  Avg latency:       {sum(latencies)/len(latencies):.1f}ms")
    print(f"  Min latency:       {min(latencies):.1f}ms")
    print(f"  Max latency:       {max(latencies):.1f}ms")
    print(f"  P95 latency:       {sorted(latencies)[int(len(latencies)*0.95)]:.1f}ms")
    print(f"  Anomalies found:   {anomalies_detected}")

    return {
        "total_time": total_time,
        "throughput": len(successful)/total_time,
        "avg_latency": sum(latencies)/len(latencies),
        "p95_latency": sorted(latencies)[int(len(latencies)*0.95)],
        "anomalies_detected": anomalies_detected
    }

def run_batch_test(total_logs=1000, batch_size=50):
    print(f"\n{'='*50}")
    print(f"BATCH TEST — {total_logs} logs in batches of {batch_size}")
    print(f"{'='*50}")

    results = []
    start = time.time()
    batches = total_logs // batch_size

    for i in range(batches):
        batch = [generate_log(anomaly=random.random() < 0.05) for _ in range(batch_size)]
        batch_start = time.time()
        try:
            response = requests.post(f"{API_URL}/ingest/batch", json=batch, timeout=60)
            batch_time = (time.time() - batch_start) * 1000
            if response.status_code == 200:
                data = response.json()
                results.append({
                    "success": True,
                    "batch_time_ms": batch_time,
                    "anomalies": data["anomalies_found"]
                })
        except Exception as e:
            results.append({"success": False, "error": str(e)})

        if (i + 1) % 5 == 0:
            print(f"  Progress: {(i+1)*batch_size}/{total_logs} logs")

    total_time = time.time() - start
    successful = [r for r in results if r.get("success")]
    total_anomalies = sum(r["anomalies"] for r in successful)
    avg_batch_time = sum(r["batch_time_ms"] for r in successful) / len(successful)

    print(f"\nResults:")
    print(f"  Total time:        {total_time:.2f}s")
    print(f"  Logs processed:    {len(successful)*batch_size}/{total_logs}")
    print(f"  Throughput:        {len(successful)*batch_size/total_time:.1f} logs/sec")
    print(f"  Avg batch time:    {avg_batch_time:.1f}ms per batch")
    print(f"  Total anomalies:   {total_anomalies}")
    print(f"  Anomaly rate:      {total_anomalies/(len(successful)*batch_size)*100:.1f}%")

    return {
        "total_time": total_time,
        "throughput": len(successful)*batch_size/total_time,
        "avg_batch_time": avg_batch_time,
        "total_anomalies": total_anomalies
    }

if __name__ == "__main__":
    print("🚀 Log Anomaly Detection — Stress Test")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check API is up
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        print(f"\n✅ API is healthy: {r.json()['status']}")
    except:
        print("❌ API is not running. Start it first.")
        exit(1)

    # Run all three tests
    seq_results = run_sequential_test(count=100)
    conc_results = run_concurrent_test(count=200, workers=10)
    batch_results = run_batch_test(total_logs=1000, batch_size=50)

    # Summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"Sequential throughput:   {seq_results['throughput']:.1f} req/sec")
    print(f"Concurrent throughput:   {conc_results['throughput']:.1f} req/sec")
    print(f"Batch throughput:        {batch_results['throughput']:.1f} logs/sec")
    print(f"Avg response latency:    {seq_results['avg_latency']:.1f}ms")
    print(f"P95 latency:             {seq_results['p95_latency']:.1f}ms")
    print(f"Total logs processed:    {100 + 200 + 1000}")
    print(f"\n✅ Stress test complete.")
    # Add to bottom of stress_test.py and run separately
def run_cache_test(count=50):
    print(f"\n{'='*50}")
    print(f"CACHE TEST — same log {count} times")
    print(f"{'='*50}")
    
    log = {
        "service": "payment-service",
        "endpoint": "/checkout",
        "method": "POST",
        "status_code": 500,
        "latency_ms": 7500.0
    }
    
    latencies = []
    for i in range(count):
        start = time.time()
        requests.post(f"{API_URL}/ingest", json=log, timeout=30)
        latencies.append((time.time() - start) * 1000)
    
    first = latencies[0]
    cached = latencies[1:]
    print(f"  First request (no cache):  {first:.1f}ms")
    print(f"  Cached avg (hits):         {sum(cached)/len(cached):.1f}ms")
    print(f"  Speedup:                   {first/( sum(cached)/len(cached)):.1f}x faster")

run_cache_test()