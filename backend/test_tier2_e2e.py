"""
Tier 2 End-to-End Test Suite
Grows one item at a time as Tier 2 is built.

PHASE 1
  [#10] Monitoring & Metrics   <-- covered here
  [#7]  Input Validation       (pending)
  [#8]  WebSocket Support       (pending)
PHASE 2
  [#9]  Redis Caching           (pending)
  [#6]  Rate Limiting           (pending)

Run:  python3 test_tier2_e2e.py
Exit code 0 = all passed, 1 = failure.
"""

import os
import sys
import json

os.environ.setdefault("FLASK_ENV", "production")

PASS = "\033[32m✅ PASS\033[0m"
FAIL = "\033[31m❌ FAIL\033[0m"
results = []


def check(name, condition, detail=""):
    ok = bool(condition)
    print(f"  {PASS if ok else FAIL}  {name}" + (f"  — {detail}" if detail and not ok else ""))
    results.append((name, ok, detail))
    return ok


# ───────────────────────────────────────────────────────────────────
print("\n=== TIER 2 #10: MONITORING & METRICS ===")

# 1. PerformanceMonitor unit behavior
try:
    from monitoring import performance_monitor, PerformanceMonitor
    pm = PerformanceMonitor()
    pm.record_endpoint_call("/api/test", "GET", 12.0, 200)
    pm.record_endpoint_call("/api/test", "GET", 18.0, 200)
    pm.record_endpoint_call("/api/test", "GET", 30.0, 500)  # one error
    m = pm.get_all_metrics()
    ep = m["endpoints"].get("GET /api/test", {})
    check("records request count", ep.get("count") == 3, str(ep))
    check("computes avg latency", ep.get("avg_time_ms") == 20.0, str(ep))
    check("tracks min/max latency", ep.get("min_time_ms") == 12.0 and ep.get("max_time_ms") == 30.0, str(ep))
    check("computes error rate", abs(ep.get("error_rate_percent", 0) - 33.33) < 0.1, str(ep))
    check("get_all_metrics has expected sections",
          all(k in m for k in ("endpoints", "database", "external_apis", "generated_at")))
except Exception as e:
    import traceback; traceback.print_exc()
    check("monitoring module imports & runs", False, repr(e))

# 2. Full app boot + live endpoints via test client
try:
    from tradosphere_saas_server_v3_1 import app
    app.config["TESTING"] = True
    c = app.test_client()

    # Hit a couple of endpoints so metrics have data to report
    c.get("/api/health")
    c.get("/api/health")
    c.get("/health")

    # /metrics
    rm = c.get("/metrics")
    bm = rm.get_json()
    check("/metrics returns 200", rm.status_code == 200, f"got {rm.status_code}")
    check("/metrics has metrics + uptime",
          bm and "metrics" in bm and "uptime_seconds" in bm, json.dumps(bm)[:200])
    tracked = bm.get("metrics", {}).get("endpoints", {})
    check("/metrics actually recorded requests (after_request hook fired)",
          len(tracked) >= 1, f"tracked={list(tracked.keys())}")
    check("/api/health appears in tracked endpoints",
          any("/api/health" in k for k in tracked), f"tracked={list(tracked.keys())}")

    # /health/deep
    rd = c.get("/health/deep")
    bd = rd.get_json()
    check("/health/deep returns 200 or 503", rd.status_code in (200, 503), f"got {rd.status_code}")
    check("/health/deep reports overall status",
          bd.get("status") in ("healthy", "degraded", "unhealthy"), json.dumps(bd)[:200])
    check("/health/deep has component breakdown",
          "components" in bd and "database" in bd["components"], json.dumps(bd)[:200])
    check("/health/deep has uptime", isinstance(bd.get("uptime_seconds"), int))
    check("/health/deep has metrics_summary",
          "metrics_summary" in bd and "total_requests" in bd["metrics_summary"], json.dumps(bd)[:200])
    check("/health/deep core-up returns 200 (db connected)",
          not (bd["components"]["database"] == "connected" and rd.status_code != 200),
          f"db={bd['components']['database']} status={rd.status_code}")
    # No raw internal leak in deep health
    check("/health/deep leaks no raw exception text",
          "Traceback" not in json.dumps(bd) and "error:" not in json.dumps(bd).lower().replace('"error_rate', ''),
          json.dumps(bd)[:200])
except Exception as e:
    import traceback; traceback.print_exc()
    check("app boots & monitoring endpoints respond", False, repr(e))


# ───────────────────────────────────────────────────────────────────
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed
print("\n" + "=" * 60)
print(f"  TIER 2 E2E RESULT:  {passed}/{total} checks passed")
if failed:
    print(f"  \033[31m{failed} FAILED:\033[0m")
    for name, ok, detail in results:
        if not ok:
            print(f"    - {name}  {detail}")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
