"""
Redis Caching Layer (Tier 2 #9)

A thin, fail-open cache around Redis. Design goals:

  1. GRACEFUL DEGRADATION — if REDIS_URL is unset, the package is missing, or
     Redis is unreachable at any moment, every cache operation becomes a silent
     no-op and callers transparently fall through to live data. A cache outage
     can NEVER take the API down.

  2. CHEAP TO ADOPT — endpoints wrap their data-building in `cache_get_or_set`
     and get caching for free, without touching response/serialization code.

  3. JSON-SAFE — values are stored as JSON strings, so only plain dict/list/
     scalar payloads should be cached (which is all the API returns anyway).

Usage:
    from cache import cache_get_or_set

    data, was_hit = cache_get_or_set(
        "market:overview", ttl=5, producer=lambda: build_overview()
    )
"""

import os
import json
import logging
import time

logger = logging.getLogger(__name__)


class RedisCache:
    """Fail-open wrapper around a Redis connection."""

    def __init__(self):
        self._client = None
        self.enabled = False
        self._last_connect_attempt = 0.0
        self._reconnect_backoff = 30.0  # seconds between reconnect attempts
        self._connect()

    # ── connection ────────────────────────────────────────────────────
    def _connect(self):
        """Attempt to establish a Redis connection. Fail-open on any error."""
        self._last_connect_attempt = time.time()
        url = os.getenv("REDIS_URL")
        if not url:
            logger.info("ℹ️  REDIS_URL not set — cache disabled (running uncached)")
            self.enabled = False
            self._client = None
            return

        try:
            import redis  # imported lazily so the dep is optional
            client = redis.from_url(
                url,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True,
            )
            client.ping()
            self._client = client
            self.enabled = True
            logger.info("✅ Redis cache connected (Tier 2 #9)")
        except Exception as exc:
            logger.warning(f"⚠️  Redis unavailable — cache disabled, serving live: {exc}")
            self.enabled = False
            self._client = None

    def _maybe_reconnect(self):
        """If disabled but a URL exists, retry occasionally (not every call)."""
        if self.enabled:
            return
        if not os.getenv("REDIS_URL"):
            return
        if (time.time() - self._last_connect_attempt) >= self._reconnect_backoff:
            self._connect()

    # ── core ops (all fail-open) ──────────────────────────────────────
    def get(self, key):
        """Return the cached value for `key`, or None on miss/any error."""
        if not self.enabled:
            self._maybe_reconnect()
            if not self.enabled:
                return None
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.debug(f"cache get failed for {key}: {exc}")
            self.enabled = False  # degrade until next reconnect window
            return None

    def set(self, key, value, ttl):
        """Store `value` under `key` with a TTL (seconds). No-op on any error."""
        if not self.enabled:
            return False
        try:
            self._client.setex(key, int(ttl), json.dumps(value, default=str))
            return True
        except Exception as exc:
            logger.debug(f"cache set failed for {key}: {exc}")
            self.enabled = False
            return False

    def delete(self, *keys):
        """Delete one or more keys. No-op on any error."""
        if not self.enabled or not keys:
            return 0
        try:
            return self._client.delete(*keys)
        except Exception as exc:
            logger.debug(f"cache delete failed: {exc}")
            return 0

    def ping(self):
        """Health probe — True if Redis answers, False otherwise."""
        if not self._client:
            return False
        try:
            return bool(self._client.ping())
        except Exception:
            return False

    def status(self):
        """Lightweight status dict for /health/deep and /metrics."""
        return {
            "enabled": self.enabled,
            "backend": "redis" if self.enabled else "none",
        }


# Single global cache instance.
cache = RedisCache()


def cache_get_or_set(key, ttl, producer):
    """Return cached value for `key`, else call `producer()`, cache it, return it.

    Returns a tuple: (value, was_hit). `was_hit` is True when the value came
    from cache. The producer is ALWAYS called on a miss or when caching is
    disabled, so callers behave identically with or without Redis.

    `producer` must be a zero-arg callable returning a JSON-serializable value.
    """
    hit = cache.get(key)
    if hit is not None:
        return hit, True
    value = producer()
    # Only cache truthy, non-error payloads (avoid caching empty/None).
    if value is not None:
        cache.set(key, value, ttl)
    return value, False


def invalidate(*keys):
    """Explicitly drop cache keys (e.g. after a write). Fail-open."""
    return cache.delete(*keys)
