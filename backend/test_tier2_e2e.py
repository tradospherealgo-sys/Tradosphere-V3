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
print("\n=== TIER 2 #7: INPUT VALIDATION ===")

# 1. Schema-level behavior
try:
    from marshmallow import ValidationError
    from schemas import (
        LoginSchema, SignupSchema, CreateTradeSchema,
        GenerateSignalSchema, BatchGenerateSchema, validate_body,
    )

    # valid passes, returns cleaned dict
    check("valid login loads", LoginSchema().load({"email": "a@b.com", "password": "x"})["email"] == "a@b.com")

    def expect_fail(schema, payload, field):
        try:
            schema().load(payload)
            return False
        except ValidationError as e:
            return field in e.messages

    check("login rejects bad email", expect_fail(LoginSchema, {"email": "nope", "password": "x"}, "email"))
    check("login rejects missing password", expect_fail(LoginSchema, {"email": "a@b.com"}, "password"))
    check("signup rejects short password", expect_fail(SignupSchema, {"email": "a@b.com", "password": "123"}, "password"))
    check("trade rejects invalid direction",
          expect_fail(CreateTradeSchema, {"direction": "HOLD", "entry_price": 1, "target_price": 2, "stop_loss": 1}, "direction"))
    check("trade rejects entry_price <= 0",
          expect_fail(CreateTradeSchema, {"direction": "BUY_CALL", "entry_price": 0, "target_price": 2, "stop_loss": 1}, "entry_price"))
    check("trade accepts option direction BUY_CALL",
          CreateTradeSchema().load({"direction": "BUY_CALL", "entry_price": 100, "target_price": 120, "stop_loss": 90})["direction"] == "BUY_CALL")
    check("generate-signal defaults symbol to NIFTY", GenerateSignalSchema().load({})["symbol"] == "NIFTY")
    check("generate-signal rejects unknown symbol",
          expect_fail(GenerateSignalSchema, {"symbol": "DOGECOIN"}, "symbol"))
    check("batch defaults to 3 symbols", len(BatchGenerateSchema().load({})["symbols"]) == 3)
except Exception as e:
    import traceback; traceback.print_exc()
    check("schemas import & validate", False, repr(e))

# 2. Live endpoint behavior via test client (decorator gating)
try:
    from tradosphere_saas_server_v3_1 import app as _app2
    _app2.config["TESTING"] = True
    c2 = _app2.test_client()

    # Login with malformed body -> clean 400 VALIDATION_ERROR (no 500, no crash)
    r_bad = c2.post("/api/auth/login", json={"email": "not-an-email", "password": ""})
    bb = r_bad.get_json()
    check("login bad input -> 400", r_bad.status_code == 400, f"got {r_bad.status_code}: {json.dumps(bb)[:160]}")
    check("login 400 uses VALIDATION_ERROR code",
          bb.get("error", {}).get("code") == "VALIDATION_ERROR", json.dumps(bb)[:160])
    check("login 400 returns per-field errors",
          "fields" in (bb.get("data") or {}) and "email" in bb["data"]["fields"], json.dumps(bb)[:200])

    # Login with no body at all -> still clean 400 (not a 500)
    r_empty = c2.post("/api/auth/login")
    check("login empty body -> clean 400 (not 500)", r_empty.status_code == 400, f"got {r_empty.status_code}")

    # Signup with short password -> 400 password field error
    r_su = c2.post("/api/auth/signup", json={"email": "new@user.com", "password": "12"})
    bsu = r_su.get_json()
    check("signup short pw -> 400 with password field",
          r_su.status_code == 400 and "password" in (bsu.get("data", {}).get("fields", {})),
          json.dumps(bsu)[:200])

    # Valid-shaped login (wrong creds) must PASS validation and reach handler
    # -> handler returns 401 (invalid credentials), NOT 400 (validation)
    r_valid_shape = c2.post("/api/auth/login", json={"email": "ghost@nowhere.com", "password": "whatever"})
    check("valid-shaped login passes validation, reaches handler (not 400)",
          r_valid_shape.status_code != 400, f"got {r_valid_shape.status_code}")
except Exception as e:
    import traceback; traceback.print_exc()
    check("validation live-endpoint gating", False, repr(e))


# ───────────────────────────────────────────────────────────────────
print("\n=== TIER 2 #8: WEBSOCKET SUPPORT ===")
try:
    from tradosphere_saas_server_v3_1 import app as _app3
    from realtime import socketio, emit_price_update, emit_signal_update, VALID_ROOMS

    _app3.config["TESTING"] = True

    def received_names(client):
        return [m["name"] for m in client.get_received()]

    # Connect
    sc = socketio.test_client(_app3)
    check("socket client connects", sc.is_connected())
    names = received_names(sc)
    check("server emits 'connected' on connect", "connected" in names, str(names))

    # Subscribe to prices room
    sc.emit("subscribe", {"channel": "prices"})
    sub = received_names(sc)
    check("subscribe to 'prices' acknowledged", "subscribed" in sub, str(sub))

    # A price tick broadcast reaches a 'prices' subscriber
    emit_price_update({"NIFTY": 24050.0, "BANKNIFTY": 57500.0})
    got = sc.get_received()
    price_evt = [m for m in got if m["name"] == "price_update"]
    check("subscriber receives 'price_update'", len(price_evt) >= 1, str([m['name'] for m in got]))
    if price_evt:
        payload = price_evt[0]["args"][0]
        check("price_update payload carries prices", payload.get("prices", {}).get("NIFTY") == 24050.0, str(payload))

    # Unknown channel -> error event
    sc.emit("subscribe", {"channel": "hacker"})
    err = received_names(sc)
    check("unknown channel returns 'error'", "error" in err, str(err))

    # Signals room is isolated: a 'prices'-only client must NOT get signal_update
    emit_signal_update({"symbol": "NIFTY", "direction": "BUY"})
    after_sig = [m["name"] for m in sc.get_received()]
    check("prices-only client does NOT receive 'signal_update'",
          "signal_update" not in after_sig, str(after_sig))

    # A signals subscriber DOES receive it
    sc2 = socketio.test_client(_app3)
    sc2.get_received()  # drain 'connected'
    sc2.emit("subscribe", {"channel": "signals"})
    sc2.get_received()  # drain 'subscribed'
    emit_signal_update({"symbol": "BANKNIFTY", "direction": "SELL"})
    sig_got = [m for m in sc2.get_received() if m["name"] == "signal_update"]
    check("signals subscriber receives 'signal_update'", len(sig_got) >= 1, "no signal_update")

    check("VALID_ROOMS are exactly prices+signals", VALID_ROOMS == {"prices", "signals"}, str(VALID_ROOMS))

    sc.disconnect()
    sc2.disconnect()
except Exception as e:
    import traceback; traceback.print_exc()
    check("websocket layer works", False, repr(e))


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
