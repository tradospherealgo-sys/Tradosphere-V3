"""
Production Smoke Test  (Pre-launch Gate 3 + Gate 6)
===================================================
Hits a DEPLOYED Tradosphere instance and verifies the live integrations are
actually wired: broker (Angel One), database, cache (Redis), the trading
disclaimer, and the real (non-fabricated) signal path.

Read-only and safe — it only calls public GET endpoints plus the no-auth
POST /api/generate. It NEVER touches billing, auth mutation, or email.

Usage:
    python3 prod_smoke_test.py https://tradosphere-v3.onrender.com
    # or set BASE_URL env var; defaults to the Render service URL.

Exit code 0 = all critical checks passed, 1 = a critical check failed.
"""

import json
import os
import sys
import urllib.request
import urllib.error

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else
            os.getenv("BASE_URL", "https://tradosphere-v3.onrender.com")).rstrip("/")

PASS = "\033[32m✅ PASS\033[0m"
FAIL = "\033[31m❌ FAIL\033[0m"
WARN = "\033[33m⚠️  WARN\033[0m"

results = []  # (name, ok, critical, detail)


def _get(path, method="GET", body=None, timeout=30):
    url = BASE_URL + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}
    except Exception as e:
        return None, {"_error": repr(e)}


def check(name, ok, critical=True, detail=""):
    results.append((name, bool(ok), critical, detail))
    status = PASS if ok else (FAIL if critical else WARN)
    print(f"  {status}  {name}" + (f"  — {detail}" if detail else ""))
    return bool(ok)


print(f"\n=== PRODUCTION SMOKE TEST → {BASE_URL} ===\n")

# 1) Liveness
s, _ = _get("/api/health")
check("server is reachable (/api/health 200)", s == 200, True, f"status={s}")

# 2) Deep health: component integrations
s, deep = _get("/health/deep")
comp = deep.get("components", {}) if isinstance(deep, dict) else {}
check("/health/deep responds", s in (200, 503), True, f"status={s}")
check("database connected", comp.get("database") == "connected", True,
      f"database={comp.get('database')}")
check("broker (Angel One) connected", comp.get("broker") == "connected", False,
      f"broker={comp.get('broker')} (WARN: needs live creds + market hours)")
check("cache backend is redis (not memory)", comp.get("cache") == "redis", False,
      f"cache={comp.get('cache')} (WARN: set REDIS_URL for shared cache/limits)")

# 3) Compliance disclaimer
s, disc = _get("/api/disclaimer")
check("disclaimer endpoint serves text", s == 200 and bool(disc.get("disclaimer")),
      True, f"status={s}")

# 4) Real signal path — must NOT fabricate
s, gen = _get("/api/generate", method="POST", body={"symbols": ["NIFTY", "BANKNIFTY"]})
sigs = gen.get("signals", []) if isinstance(gen, dict) else []
check("/api/generate returns 200", s == 200, True, f"status={s}")
check("response carries disclaimer", bool(gen.get("disclaimer")), True)
data_status = gen.get("data_status")
check("data_status is 'live' or 'delayed'", data_status in ("live", "delayed"), True,
      f"data_status={data_status}")
# Integrity: when delayed, every signal must be an honest HOLD with no levels.
if data_status == "delayed":
    honest = all(sg.get("signal") == "HOLD" and sg.get("entry") in (None, 0) for sg in sigs)
    check("delayed signals are honest HOLD (no fabrication)", honest, True,
          json.dumps(sigs)[:200])
else:
    # Live: signals should be derived from real TA (carry an rsi value).
    has_ta = all(("rsi" in sg or sg.get("signal") == "HOLD") for sg in sigs)
    check("live signals carry real indicators (rsi)", has_ta, False)

# ── Summary ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
crit_fail = [r for r in results if not r[1] and r[2]]
warns = [r for r in results if not r[1] and not r[2]]
passed = sum(1 for r in results if r[1])
print(f"  SMOKE TEST: {passed}/{len(results)} checks passed, "
      f"{len(crit_fail)} critical failures, {len(warns)} warnings")
if crit_fail:
    print("  \033[31mCRITICAL FAILURES:\033[0m")
    for n, _, _, d in crit_fail:
        print(f"    - {n}  {d}")
if warns:
    print("  \033[33mWARNINGS (often expected pre-config / off-market):\033[0m")
    for n, _, _, d in warns:
        print(f"    - {n}  {d}")

print("""
  MANUAL CHECKS (cannot be automated safely — do these by hand):
    [ ] Stripe: complete one real checkout on LIVE keys; confirm webhook fires
    [ ] Email: trigger signup + password-reset; confirm both emails arrive
    [ ] Google OAuth: sign in with a real Google account
    [ ] Frontend: load the Vercel site, confirm signals + WebSocket connect
""")
print("=" * 60)
sys.exit(1 if crit_fail else 0)
