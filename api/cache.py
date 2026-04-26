import redis
import json
import hashlib


class AnomalyCache:
    def __init__(self, host='localhost', port=6379, ttl=60):
        """
        ttl = time to live in seconds
        cached results expire after 60 seconds
        """
        self.ttl = ttl
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                decode_responses=True,
                socket_connect_timeout=2
            )
            self.client.ping()
            self.enabled = True
            print("Redis cache connected.")
        except Exception:
            # If Redis isn't available, cache is disabled gracefully
            self.client = None
            self.enabled = False
            print("Redis unavailable — running without cache.")

    def _make_key(self, log: dict) -> str:
        """
        Creates a unique cache key from the log's behaviour fields.
        Ignores timestamp, ip, user_id since those don't affect anomaly detection.
        """
        key_fields = {
            "service": log.get("service"),
            "endpoint": log.get("endpoint"),
            "method": log.get("method"),
            "status_code": log.get("status_code"),
            # Round latency to nearest 100ms bucket so similar latencies hit same cache
            "latency_bucket": round(log.get("latency_ms", 0) / 100) * 100
        }
        key_str = json.dumps(key_fields, sort_keys=True)
        return f"anomaly:{hashlib.md5(key_str.encode()).hexdigest()}"

    def get(self, log: dict):
        """Returns cached result if it exists, None otherwise."""
        if not self.enabled:
            return None
        try:
            key = self._make_key(log)
            cached = self.client.get(key)
            if cached:
                print(f"Cache HIT for {log['service']}{log['endpoint']}")
                return json.loads(cached)
            print(f"Cache MISS for {log['service']}{log['endpoint']}")
            return None
        except Exception:
            return None

    def set(self, log: dict, result: dict):
        """Stores result in cache with TTL expiry."""
        if not self.enabled:
            return
        try:
            key = self._make_key(log)
            # Store result without the log field to save memory
            cache_data = {
                "is_anomaly": result["is_anomaly"],
                "anomaly_score": result["anomaly_score"],
                "severity": result["severity"],
                "explanation": result.get("explanation"),
                "similar_cases": result.get("similar_cases"),
                "from_cache": True
            }
            self.client.setex(key, self.ttl, json.dumps(cache_data))
        except Exception:
            pass

    def get_stats(self):
        """Returns basic cache statistics."""
        if not self.enabled:
            return {"enabled": False}
        try:
            info = self.client.info()
            keys = self.client.dbsize()
            return {
                "enabled": True,
                "total_keys": keys,
                "used_memory": info.get("used_memory_human"),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0) /
                    max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100, 1
                )
            }
        except Exception:
            return {"enabled": False}