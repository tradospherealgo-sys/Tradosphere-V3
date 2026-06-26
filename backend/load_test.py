"""
Basic Load Test  (Pre-launch Gate 6)
====================================
Fires concurrent requests at a DEPLOYED Tradosphere instance and reports
throughput, latency percentiles, error rate, and how the rate limiter behaves
under burst (429s are EXPECTED and prove the limiter works).

Stdlib only — no extra dependencies.

Usage:
    python3 load_test.py https://tradosphere-v3.onrender.com [concurrency] [requests]
    # defaults: concurrency=20, total_requests=400, endpoint=/api/health

    # To stress the heavier signal path:
    ENDPOINT=/api/generate METHOD=POST python3 load_test.py <url> 20 200

Notes:
  * Start small. A free Render dyno will fall over quickly — that itself is a
    finding (Gate 4: upgrade the plan).
  * This is a smoke-level load test, not a 10k-user benchmark. For that, use a
    dedicated tool (k6, Locust, vegeta) from a machine with enough bandwidth.
"""

import json
import os
import sys
import time
import threading
import urllib.request
import urllib.error
from collections import Counter

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else
            os.getenv("BASE_URL", "https://tradosphere-v3.onrender.com")).rstrip("/")
CONCURRENCY = int(sys.argv[2]) if len(sys.argv) > 2 else 20
TOTAL = int(sys.argv[3]) if len(sys.argv) > 3 else 400
ENDPOINT = os.getenv("ENDPOINT", "/api/health")
METHOD = os.getenv("METHOD", "GET")
BODY = {"symbols": ["NIFTY", "BANKNIFTY"]} if METHOD == "POST" else None

latencies = []
status_counts = Counter()
_lock = threading.Lock()
_remaining = TOTAL


def worker():
    global _remaining
    data = json.dumps(BODY).encode() if BODY is not None else None
    while True:
        with _lock:
            if _remaining <= 0:
                return
            _remaining -= 1
        req = urllib.request.Request(
            BASE_URL + ENDPOINT, data=data, method=METHOD,
            headers={"Content-Type": "application/json"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                code = r.status
                r.read()
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception:
            code = 0  # connection error / timeout
        dt = (time.time() - t0) * 1000
        with _lock:
            latencies.append(dt)
            status_counts[code] += 1


def pct(values, p):
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, int(round((p / 100) * (len(s) - 1))))
    return round(s[idx], 1)


print(f"\n=== LOAD TEST → {BASE_URL}{ENDPOINT} ({METHOD}) ===")
print(f"    concurrency={CONCURRENCY}, total_requests={TOTAL}\n")

start = time.time()
threads = [threading.Thread(target=worker) for _ in range(CONCURRENCY)]
for t in threads:
    t.start()
for t in threads:
    t.join()
elapsed = time.time() - start

ok = sum(v for k, v in status_counts.items() if 200 <= k < 400)
rate_limited = status_counts.get(429, 0)
errors = sum(v for k, v in status_counts.items() if k == 0 or k >= 500)

print(f"  duration:        {elapsed:.2f}s")
print(f"  throughput:      {TOTAL / elapsed:.1f} req/s")
print(f"  latency p50:     {pct(latencies, 50)} ms")
print(f"  latency p95:     {pct(latencies, 95)} ms")
print(f"  latency p99:     {pct(latencies, 99)} ms")
print(f"  max latency:     {round(max(latencies), 1) if latencies else 0} ms")
print(f"  status codes:    {dict(status_counts)}")
print(f"  success (2xx/3xx): {ok}")
print(f"  rate-limited (429): {rate_limited}   <- expected under burst; proves limiter works")
print(f"  server errors (5xx/conn): {errors}")

verdict = "✅ healthy" if errors == 0 else "⚠️  some server errors — investigate"
print(f"\n  VERDICT: {verdict}")
print("=" * 60)
sys.exit(1 if errors > 0 else 0)
