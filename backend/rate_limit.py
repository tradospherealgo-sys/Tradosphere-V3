"""
API Rate Limiting (Tier 2 #6)

flask-limiter backed by the SAME Redis instance used for caching (REDIS_URL),
so limit counters are shared across all gunicorn threads/workers. Design goals:

  1. FAIL-OPEN — `swallow_errors=True` means if Redis is unreachable, the limiter
     logs and ALLOWS the request rather than 500-ing. A limiter/storage outage
     can never take the API down. If REDIS_URL is unset we fall back to an
     in-process memory store (fine for a single worker; per-process only).

  2. TIERED LIMITS
       - default (all routes) : generous ceiling to stop abuse/runaway clients
       - auth endpoints       : strict, to blunt credential-stuffing / brute force

  3. STANDARD HEADERS — X-RateLimit-* + Retry-After are emitted so clients can
     back off gracefully. The 429 body is handled by our existing error handler
     (RATE_LIMIT_EXCEEDED), giving a consistent APIResponse shape.

Wiring (in the main server):
    from rate_limit import init_rate_limiter, limiter, AUTH_LIMITS
    init_rate_limiter(app)                 # before/after blueprints both work
    limiter.limit(AUTH_LIMITS)(auth_bp)    # strict limits on the auth blueprint
"""

import os
import logging

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)


def _storage_uri():
    """Use Redis when available; otherwise an in-process memory store."""
    url = os.getenv("REDIS_URL")
    if url:
        logger.info("✅ Rate limiter using Redis storage (shared across workers)")
        return url
    logger.info("ℹ️  REDIS_URL not set — rate limiter using in-memory store (per-process)")
    return "memory://"


# Strict ceiling for authentication endpoints (brute-force / credential-stuffing
# protection). Applied to the whole auth blueprint in the main server.
AUTH_LIMITS = "10 per minute"

# Single global limiter. Default limits apply to every route unless overridden
# or exempted. Generous enough not to bother normal users, low enough to stop
# runaway scripts.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage_uri(),
    default_limits=["300 per minute", "30 per second"],
    strategy="fixed-window",
    swallow_errors=True,   # FAIL-OPEN on any storage/backend error
    headers_enabled=True,  # emit X-RateLimit-* + Retry-After
)


def init_rate_limiter(app):
    """Bind the limiter to the Flask app. Safe to call once at startup."""
    limiter.init_app(app)
    logger.info("✅ Rate limiter initialized (Tier 2 #6)")
    return limiter
