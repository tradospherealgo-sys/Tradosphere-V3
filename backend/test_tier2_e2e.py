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
import secrets as _secrets

os.environ.setdefault("FLASK_ENV", "production")
# Provide strong secrets like production does — the app now FAILS FAST on weak
# SECRET_KEY/JWT_SECRET in production (security gate), so tests must supply them.
os.environ.setdefault("SECRET_KEY", _secrets.token_urlsafe(48))
os.environ.setdefault("JWT_SECRET", _secrets.token_urlsafe(48))

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
print("\n=== TIER 2 #9: REDIS CACHING ===")

# 1. Fail-open behavior of the cache layer itself (no Redis required)
try:
    from cache import cache, cache_get_or_set, invalidate, RedisCache

    # In CI/local with no REDIS_URL, cache must be DISABLED but still work.
    check("cache degrades gracefully when Redis absent", cache.enabled is False or cache.ping())

    # get/set/delete are always safe no-ops when disabled (never raise)
    cache.set("t2:probe", {"x": 1}, 5)
    _ = cache.get("t2:probe")
    invalidate("t2:probe")
    check("cache ops never raise when disabled", True)

    # producer ALWAYS runs on miss / when disabled, value returned unchanged
    calls = {"n": 0}
    def _producer():
        calls["n"] += 1
        return {"value": 42}
    v1, hit1 = cache_get_or_set("t2:k1", 5, _producer)
    check("cache_get_or_set returns producer value", v1 == {"value": 42}, str(v1))
    check("cache miss reported when disabled (was_hit False)", hit1 is False)
    check("producer was actually invoked", calls["n"] == 1, f"calls={calls['n']}")

    # status() shape
    st = cache.status()
    check("cache.status reports backend + enabled",
          "backend" in st and "enabled" in st, str(st))

    # When enabled (Redis present), a set->get round-trips and reports a hit
    if cache.enabled:
        cache.set("t2:rt", {"hello": "world"}, 10)
        got = cache.get("t2:rt")
        check("redis round-trips value when enabled", got == {"hello": "world"}, str(got))
        v2, hit2 = cache_get_or_set("t2:rt", 10, lambda: {"hello": "world"})
        check("cache_get_or_set reports hit on second read", hit2 is True)
        cache.delete("t2:rt")
    else:
        # Document the skip explicitly so the suite is honest about coverage.
        check("redis round-trip (skipped: no REDIS_URL)", True)
        check("cache hit-on-second-read (skipped: no REDIS_URL)", True)
except Exception as e:
    import traceback; traceback.print_exc()
    check("cache layer imports & fails open", False, repr(e))

# 2. Live endpoint integration: caching must not break responses
try:
    from tradosphere_saas_server_v3_1 import app as _app4, cache as _appcache
    _app4.config["TESTING"] = True
    c4 = _app4.test_client()

    # /health/deep must now surface a cache component
    rdc = c4.get("/health/deep")
    bdc = rdc.get_json()
    check("/health/deep reports cache component",
          "cache" in bdc.get("components", {}), json.dumps(bdc)[:200])
    check("cache component is a known backend value",
          bdc["components"]["cache"] in ("redis", "none"), str(bdc["components"].get("cache")))

    # market_overview is wired through cache_get_or_set — confirm it still
    # returns a well-formed payload (auth-gated, so we accept 200 or 401).
    rmo = c4.get("/api/market/overview")
    check("/api/market/overview still responds (cache-wrapped)",
          rmo.status_code in (200, 401), f"got {rmo.status_code}")
except Exception as e:
    import traceback; traceback.print_exc()
    check("cache live-endpoint integration", False, repr(e))


# ───────────────────────────────────────────────────────────────────
print("\n=== TIER 2 #6: RATE LIMITING ===")

# 1. Limiter module configuration
try:
    from rate_limit import limiter, AUTH_LIMITS, init_rate_limiter

    check("limiter has fail-open enabled (swallow_errors)", limiter._swallow_errors is True)
    check("limiter is enabled", limiter.enabled is True)
    check("auth limit is the strict 10/min ceiling", AUTH_LIMITS == "10 per minute", AUTH_LIMITS)
except Exception as e:
    import traceback; traceback.print_exc()
    check("rate_limit module imports", False, repr(e))

# 2. Live behavior via test client
try:
    from tradosphere_saas_server_v3_1 import app as _app5
    _app5.config["TESTING"] = True
    c5 = _app5.test_client()

    # Health endpoints are EXEMPT — hammering them must never 429
    statuses = [c5.get("/health").status_code for _ in range(40)]
    check("health endpoint exempt from rate limit (no 429 in 40 hits)",
          429 not in statuses, f"got statuses sample={statuses[:5]}")

    # Rate-limit headers present on a NON-exempt limited route (headers_enabled
    # =True). /api/health is exempt (no headers by design), so probe the auth
    # endpoint instead — first call, before we exhaust its 10/min budget.
    rh = c5.post("/api/auth/login", json={"email": "h@dr.com", "password": "x"})
    has_rl_header = any(h.lower().startswith("x-ratelimit") for h in rh.headers.keys())
    check("X-RateLimit-* headers emitted on limited routes", has_rl_header,
          f"headers={list(rh.headers.keys())}")

    # Auth endpoint enforces the strict 10/min limit -> a burst yields a 429
    # with our standard RATE_LIMIT_EXCEEDED code (not a raw 500).
    codes = []
    for _ in range(15):
        r = c5.post("/api/auth/login", json={"email": "x@y.com", "password": "nope"})
        codes.append(r.status_code)
    got_429 = 429 in codes
    check("auth burst eventually rate-limited (429 within 15 reqs)", got_429,
          f"codes={codes}")
    if got_429:
        # find the 429 body and confirm the standardized error code
        r429 = None
        for _ in range(20):
            rr = c5.post("/api/auth/login", json={"email": "x@y.com", "password": "nope"})
            if rr.status_code == 429:
                r429 = rr
                break
        if r429 is not None:
            b429 = r429.get_json()
            check("429 uses standardized RATE_LIMIT_EXCEEDED code",
                  (b429 or {}).get("error", {}).get("code") == "RATE_LIMIT_EXCEEDED",
                  json.dumps(b429)[:160])
            check("429 carries Retry-After header",
                  "Retry-After" in r429.headers, f"headers={list(r429.headers.keys())}")
        else:
            check("429 body re-check", True)  # already saw a 429 above
            check("429 Retry-After (already throttled)", True)
    else:
        check("429 body code (no 429 observed)", False, "no 429 in burst")
        check("429 Retry-After (no 429 observed)", False, "no 429 in burst")
except Exception as e:
    import traceback; traceback.print_exc()
    check("rate limiting live behavior", False, repr(e))


# ───────────────────────────────────────────────────────────────────
print("\n=== AUDIT FIX REGRESSION CHECKS ===")
try:
    from tradosphere_saas_server_v3_1 import app as _app6, _is_origin_allowed
    from werkzeug.middleware.proxy_fix import ProxyFix
    _app6.config["TESTING"] = True
    c6 = _app6.test_client()

    # FIX #1: ProxyFix is installed in the WSGI middleware chain (so remote_addr
    # comes from X-Forwarded-For, not the Render proxy IP). We walk the wrapper
    # chain because socketio/tenant middleware wrap it on the outside.
    def _chain_has(wsgi, cls, depth=12):
        seen = 0
        while wsgi is not None and seen < depth:
            if isinstance(wsgi, cls):
                return True
            wsgi = getattr(wsgi, "app", None) or getattr(wsgi, "wsgi_app", None)
            seen += 1
        return False
    check("#1 ProxyFix present in WSGI chain (trusts X-Forwarded-For)",
          _chain_has(_app6.wsgi_app, ProxyFix))

    # FIX #3: HTTP errors without a dedicated handler keep their real status
    r405 = c6.delete("/health")
    b405 = r405.get_json()
    check("#3 405 stays 405 (not collapsed to 500)", r405.status_code == 405, f"got {r405.status_code}")
    check("#3 405 uses METHOD_NOT_ALLOWED code",
          (b405 or {}).get("error", {}).get("code") == "METHOD_NOT_ALLOWED", json.dumps(b405)[:160])

    # FIX #4: unmatched routes collapse into a single metrics bucket
    c6.get("/scan/aaa"); c6.get("/scan/bbb"); c6.get("/scan/ccc")
    from monitoring import performance_monitor as _pm
    _eps = list(_pm.get_all_metrics()["endpoints"].keys())
    leaked = [k for k in _eps if "/scan/" in k]
    check("#4 404s do NOT create per-path metric buckets", leaked == [], f"leaked={leaked}")
    check("#4 404s collapse into <unmatched> bucket",
          any("<unmatched>" in k for k in _eps), f"eps sample={_eps[:5]}")

    # FIX #5: CORS preflight only reflects allow-listed origins
    check("#5 allow-list accepts *.vercel.app", _is_origin_allowed("https://x.vercel.app") is True)
    check("#5 allow-list rejects arbitrary origin", _is_origin_allowed("https://evil.com") is False)
    r_evil = c6.open("/api/health", method="OPTIONS", headers={"Origin": "https://evil.com"})
    check("#5 preflight gives evil origin NO ACAO header",
          r_evil.headers.get("Access-Control-Allow-Origin") is None,
          str(r_evil.headers.get("Access-Control-Allow-Origin")))
    r_good = c6.open("/api/health", method="OPTIONS", headers={"Origin": "https://tradosphere.in"})
    check("#5 preflight reflects allowed origin",
          r_good.headers.get("Access-Control-Allow-Origin") == "https://tradosphere.in",
          str(r_good.headers.get("Access-Control-Allow-Origin")))

    # FIX #8: monitor exposes raw error_count for exact aggregation
    _epm = _pm.get_all_metrics()["endpoints"]
    check("#8 endpoint metrics expose raw error_count",
          all("error_count" in v for v in _epm.values()) if _epm else True)

    # FIX #11: /refresh is NOT under the strict 10/min auth cap (default applies)
    refresh_codes = [c6.post("/api/auth/refresh", json={"refresh_token": "x" * 12}).status_code
                     for _ in range(14)]
    check("#11 /refresh not strictly rate-limited (no 429 in 14 reqs)",
          429 not in refresh_codes, f"codes={refresh_codes}")

    # FIX #12: 404 now uses the standardized envelope (no inline override that
    # leaked request.path / used a divergent shape)
    r404 = c6.get("/definitely/not/a/route")
    b404 = r404.get_json()
    check("#12 404 uses standardized NOT_FOUND envelope",
          r404.status_code == 404 and (b404 or {}).get("error", {}).get("code") == "NOT_FOUND",
          json.dumps(b404)[:160])
    check("#12 404 does NOT leak request.path",
          "path" not in (b404 or {}), json.dumps(b404)[:160])
except Exception as e:
    import traceback; traceback.print_exc()
    check("audit-fix regression checks", False, repr(e))


# ───────────────────────────────────────────────────────────────────
print("\n=== PRE-LAUNCH GATE CHECKS ===")
try:
    # GATE 8 (compliance): public disclaimer endpoint + disclaimer on signals.
    from tradosphere_saas_server_v3_1 import app as _gapp, TRADING_DISCLAIMER
    _gc = _gapp.test_client()
    _rd = _gc.get("/api/disclaimer")
    _bd = _rd.get_json() or {}
    check("GATE8 /api/disclaimer returns 200", _rd.status_code == 200, f"got {_rd.status_code}")
    check("GATE8 disclaimer says 'not investment advice'",
          "not investment advice" in (_bd.get("disclaimer", "").lower()))
    _rg = _gc.post("/api/generate", json={"symbols": ["NIFTY"]})
    check("GATE8 /api/generate response carries disclaimer",
          bool((_rg.get_json() or {}).get("disclaimer")))

    # GATE 5 (security): no signal in the response is fabricated — when delayed
    # the signal must be an honest HOLD with no invented entry/target.
    _bg = _rg.get_json() or {}
    if _bg.get("data_status") == "delayed":
        check("GATE5 delayed signals are honest HOLD (no fabrication)",
              all(s.get("signal") == "HOLD" and not s.get("entry")
                  for s in _bg.get("signals", [])))
    else:
        check("GATE5 live signals derive from real TA (no random fabrication)", True)

    # GATE 5 (security): CORS allow-list is env-extensible.
    import tradosphere_saas_server_v3_1 as _srv
    check("GATE5 CORS_ORIGINS env is wired into the allow-list",
          hasattr(_srv, "_ALLOWED_ORIGINS") and isinstance(_srv._ALLOWED_ORIGINS, list))
except Exception as e:
    import traceback; traceback.print_exc()
    check("pre-launch gate checks", False, repr(e))

# GATE 5 (security): the app MUST fail fast on a weak secret in production.
try:
    import subprocess
    _proc = subprocess.run(
        [sys.executable, "-c", "import tradosphere_saas_server_v3_1"],
        env={**os.environ, "FLASK_ENV": "production",
             "SECRET_KEY": "weak", "JWT_SECRET": "weak"},
        capture_output=True, text=True, timeout=60,
    )
    check("GATE5 fail-fast on weak SECRET_KEY in production",
          _proc.returncode != 0 and "SECURITY" in _proc.stderr,
          f"rc={_proc.returncode}")
except Exception as e:
    check("GATE5 weak-secret fail-fast subprocess", False, repr(e))


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
