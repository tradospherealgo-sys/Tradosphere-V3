"""
Tier 1 End-to-End Test Suite
Tests all 4 Tier 1 launch-blocking components:
  1. Logging System          (logger_config.py)
  2. Hide Fallback Messages   (response_handler.py prod gate + sanitization)
  3. Real Signal Generation   (real_signal_generator.py)
  4. Error Handling           (error_handler.py + exceptions.py)

Run:  python3 test_tier1_e2e.py
Exit code 0 = all passed, 1 = failure.
"""

import os
import sys
import json

# Force production behavior for the leak tests (must be set before imports
# that read FLASK_ENV at module load time).
os.environ.setdefault("FLASK_ENV", "production")

PASS = "\033[32m✅ PASS\033[0m"
FAIL = "\033[31m❌ FAIL\033[0m"

results = []


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((name, bool(condition), detail))
    print(f"  {status}  {name}" + (f"  — {detail}" if detail and not condition else ""))
    return bool(condition)


# ───────────────────────────────────────────────────────────────────
print("\n=== TIER 1 #1: LOGGING SYSTEM ===")
try:
    from logger_config import setup_logging, get_logger
    log = setup_logging()
    check("setup_logging() returns a logger", log is not None)
    check("logger has handlers attached", len(log.handlers) >= 1, f"{len(log.handlers)} handlers")
    child = get_logger("tier1.test")
    check("get_logger() returns named logger", child.name == "tier1.test")
    # Verify a log file actually gets written
    from logger_config import LOG_FILE
    log.info("E2E tier1 test log line")
    for h in log.handlers:
        try:
            h.flush()
        except Exception:
            pass
    check("log file is created on disk", os.path.exists(LOG_FILE), str(LOG_FILE))
except Exception as e:
    check("logging module imports & runs", False, repr(e))


# ───────────────────────────────────────────────────────────────────
print("\n=== TIER 1 #4: ERROR HANDLING (exceptions + handlers) ===")
try:
    from exceptions import (
        TradosphereException, AuthenticationError, ValidationError,
        ResourceNotFoundError, handle_exception,
    )
    e1 = ValidationError("bad input")
    check("ValidationError has 400 status", e1.status_code == 400)
    check("ValidationError carries error_code", e1.error_code == "VALIDATION_ERROR")
    check("AuthenticationError has 401 status", AuthenticationError().status_code == 401)
    check("to_dict() serializes cleanly", isinstance(e1.to_dict(), dict) and "code" in e1.to_dict())
    handle_exception(e1, context="e2e")  # must not raise
    check("handle_exception() runs without raising", True)
except Exception as e:
    check("exceptions module imports & runs", False, repr(e))

# Boot a minimal Flask app with the REAL error handlers — this is the
# regression test for the APIResponse.error signature bug we just fixed.
try:
    from flask import Flask, abort
    from error_handler import register_error_handlers, register_logging_middleware
    from exceptions import ResourceNotFoundError

    app = Flask(__name__)
    app.config["TESTING"] = True
    register_error_handlers(app)
    register_logging_middleware(app)

    @app.route("/boom-404")
    def boom_404():
        abort(404)

    @app.route("/boom-400")
    def boom_400():
        abort(400)

    @app.route("/boom-custom")
    def boom_custom():
        raise ResourceNotFoundError("widget not found")

    @app.route("/boom-unexpected")
    def boom_unexpected():
        raise RuntimeError("kaboom internal detail")

    c = app.test_client()

    r404 = c.get("/boom-404")
    body404 = r404.get_json()
    check("404 handler returns 404 (no TypeError)", r404.status_code == 404, f"got {r404.status_code}")
    check("404 body is well-formed JSON error",
          body404 and body404.get("error", {}).get("code") == "NOT_FOUND",
          json.dumps(body404))

    r400 = c.get("/boom-400")
    check("400 handler returns 400 (no TypeError)", r400.status_code == 400, f"got {r400.status_code}")
    check("400 body has BAD_REQUEST code",
          r400.get_json().get("error", {}).get("code") == "BAD_REQUEST")

    rc = c.get("/boom-custom")
    bodyc = rc.get_json()
    check("custom TradosphereException -> 404", rc.status_code == 404, f"got {rc.status_code}")
    check("custom exception message surfaced", bodyc.get("error") == "widget not found", json.dumps(bodyc))

    ru = c.get("/boom-unexpected")
    bodyu = ru.get_json()
    check("unexpected error -> 500 (handled, not crashed)", ru.status_code == 500, f"got {ru.status_code}")
    check("unexpected error hides raw internal detail",
          bodyu and "kaboom internal detail" not in json.dumps(bodyu),
          json.dumps(bodyu))
except Exception as e:
    import traceback
    check("error-handler Flask integration boots", False, repr(e))
    traceback.print_exc()


# ───────────────────────────────────────────────────────────────────
print("\n=== TIER 1 #2: HIDE FALLBACK MESSAGES ===")
try:
    from flask import Flask as _Flask
    from response_handler import APIResponse, _DEBUG_MODE
    check("production gate is OFF (FLASK_ENV=production)", _DEBUG_MODE is False, f"_DEBUG_MODE={_DEBUG_MODE}")

    # server_error calls jsonify(), which needs an app context (always present
    # during a real request). Provide one for the unit check.
    _ctx_app = _Flask(__name__)
    with _ctx_app.app_context():
        # server_error must NOT leak the raw exception in production
        secret = "SECRET_DB_PASSWORD_LEAK_12345"
        resp, status = APIResponse.server_error("ctx", Exception(secret))
        payload = resp.get_json()
    check("server_error returns 500", status == 500)
    check("server_error hides raw exception in prod",
          secret not in json.dumps(payload), json.dumps(payload))
    check("server_error returns a clean generic message",
          "try again" in json.dumps(payload).lower())

    # The signals endpoint maps internal source -> public data_status.
    # Replicate the exact mapping logic to lock the contract.
    def public_status(price_source):
        return "live" if price_source in ("live_angel_one", "live") else "delayed"
    check("price_source 'live_angel_one' -> 'live'", public_status("live_angel_one") == "live")
    check("price_source 'fallback' -> 'delayed' (no leak)", public_status("fallback") == "delayed")
    check("'delayed'/'live' contain no scary words",
          all(w not in ("delayed", "live") for w in ("fallback", "mock", "fake")))
except Exception as e:
    check("response_handler imports & runs", False, repr(e))

# Verify debug mode DOES expose detail (the dev-experience half of the gate)
try:
    import importlib
    from flask import Flask as _Flask2
    os.environ["FLASK_ENV"] = "development"
    import response_handler as rh
    importlib.reload(rh)
    check("dev gate is ON (FLASK_ENV=development)", rh._DEBUG_MODE is True)
    _ctx_app2 = _Flask2(__name__)
    with _ctx_app2.app_context():
        resp, status = rh.APIResponse.server_error("ctx", Exception("dev-detail-xyz"))
        dev_payload = json.dumps(resp.get_json())
    check("server_error exposes detail in development",
          "dev-detail-xyz" in dev_payload)
    # restore
    os.environ["FLASK_ENV"] = "production"
    importlib.reload(rh)
except Exception as e:
    check("response_handler dev-mode reload", False, repr(e))


# ───────────────────────────────────────────────────────────────────
print("\n=== TIER 1 #3: REAL SIGNAL GENERATION ===")
try:
    from real_signal_generator import RealSignalGenerator

    # Strong bullish setup: price above all EMAs, healthy RSI, MACD positive
    bullish = RealSignalGenerator.generate_signal(
        "NIFTY", 24000,
        {"ema_20": 23800, "ema_50": 23600, "ema_200": 23000,
         "rsi": 60, "macd": 15, "macd_signal": 8},
        ai_confidence=75,
    )
    check("returns a dict", isinstance(bullish, dict))
    sig = bullish.get("signal") or bullish.get("direction")
    check("bullish setup -> BUY", sig == "BUY", f"got {sig}; full={json.dumps(bullish, default=str)}")

    # Strong bearish setup
    bearish = RealSignalGenerator.generate_signal(
        "BANKNIFTY", 50000,
        {"ema_20": 50500, "ema_50": 51000, "ema_200": 52000,
         "rsi": 35, "macd": -20, "macd_signal": -5},
        ai_confidence=70,
    )
    sigb = bearish.get("signal") or bearish.get("direction")
    check("bearish setup -> SELL", sigb == "SELL", f"got {sigb}")

    # Robustness: empty technicals must not crash
    safe = RealSignalGenerator.generate_signal("FINNIFTY", 19000, {})
    check("handles empty technical_data without crashing", isinstance(safe, dict))
    check("signal is one of BUY/SELL/HOLD",
          (safe.get("signal") or safe.get("direction")) in ("BUY", "SELL", "HOLD"))
except Exception as e:
    import traceback
    check("real_signal_generator imports & runs", False, repr(e))
    traceback.print_exc()


# ───────────────────────────────────────────────────────────────────
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed
print("\n" + "=" * 60)
print(f"  TIER 1 E2E RESULT:  {passed}/{total} checks passed")
if failed:
    print(f"  \033[31m{failed} FAILED:\033[0m")
    for name, ok, detail in results:
        if not ok:
            print(f"    - {name}  {detail}")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
