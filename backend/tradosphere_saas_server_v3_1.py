"""
Tradosphere SaaS Server - Multi-tenant trading platform
Phase 1: Authentication, Multi-tenancy, User Management
Phase 2: Subscriptions, Email Notifications, Multi-broker Support
"""

import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables FIRST, before any other imports.
# SECURITY (F-10): never load .env.development in production. The production
# platform (Render) injects real secrets as process env vars; a stray
# .env.development that reached the server must never be able to supply or
# override production secrets (a leaked JWT_SECRET would allow forging tokens
# for any user). FLASK_ENV is set as a real env var by the platform, so it is
# reliable here before any dotenv load. We only read .env.development when we
# are NOT running in production.
if os.getenv('FLASK_ENV', '').lower() == 'production':
    load_dotenv()  # real process environment / standard .env only
else:
    env_file = Path(__file__).parent.parent / '.env.development'
    if env_file.exists():
        load_dotenv(env_file)
    else:
        load_dotenv()  # Fallback to default .env loading

# Set working directory to script location
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Setup logging BEFORE other imports
from logger_config import setup_logging
logger = setup_logging()

from flask import Flask, jsonify, request, send_file, g, make_response
from flask_cors import CORS

# Import modules
from database_v3_1 import init_db, Signal, Trade
from user_model_v3_1 import init_user_db, SessionLocal
from auth_routes_v3_1 import auth_bp
from user_routes_v3_1 import user_bp
from billing_routes_v3_1 import billing_bp
from admin_routes_v3_1 import admin_bp
from trading_routes_v3_1 import trading_bp
from auth_manager_v3_1 import AuthDecorator
from paper_trading_model_v3_1 import init_paper_trading_db
from response_handler import APIResponse
from exceptions import TradosphereException, handle_exception

try:
    from multi_tenant_middleware import MultiTenantMiddleware
except ImportError:
    class MultiTenantMiddleware:
        @staticmethod
        def register_tenant_middleware(app): pass

# Define TenantDataIsolation locally to avoid import issues
class TenantDataIsolation:
    @staticmethod
    def get_user_signals(db, user_id, limit):
        from database_v3_1 import Signal
        try:
            return db.query(Signal).filter_by(user_id=user_id).order_by(Signal.created_at.desc()).limit(limit).all()
        except Exception:  # AUDIT FIX #15: don't swallow KeyboardInterrupt/SystemExit
            return []

    @staticmethod
    def get_user_metrics(db, user_id):
        return {"wins": 0, "losses": 0, "win_rate": 0}

# Optional imports with fallbacks
try:
    from subscription_model import init_subscription_db
except ImportError:
    def init_subscription_db(): pass

try:
    from leads_model import init_leads_db
except ImportError:
    def init_leads_db(): pass

try:
    from leads_routes import leads_bp
except ImportError:
    from flask import Blueprint
    leads_bp = Blueprint('leads', __name__)

try:
    from backtest_routes import backtest_bp
except ImportError:
    from flask import Blueprint
    backtest_bp = Blueprint('backtest', __name__)

# Import trading engine (from existing code)
from market_data import AngelOneMarketData
from signal_writer import generate_on_demand
from technical_engine import TechnicalEngine
from options_engine import OptionsEngine
from signals_engine import SignalsEngine
from signal_writer import SignalGenerator
from ai_analysis_engine import AIAnalysisEngine
from learning_engine import LearningEngine
from reconciliation_engine import ReconciliationEngine
from unified_signal_service import get_unified_signal_service
from real_signal_generator import RealSignalGenerator

try:
    from claude_ai_service import ClaudeAIService
except ImportError:
    class ClaudeAIService:
        @staticmethod
        def analyze_market_data(*args, **kwargs):
            return {"status": "error", "message": "Claude AI not available"}

        @staticmethod
        def validate_signal(*args, **kwargs):
            return {"status": "error", "message": "Claude AI not available"}

# Initialize Flask
app = Flask(__name__)

# ===== TRUST THE RENDER PROXY (AUDIT FIX #1) =====
# Render terminates TLS at a load balancer and forwards the real client IP in
# X-Forwarded-For. Without this, request.remote_addr is the PROXY's IP, which
# would make the rate limiter (Tier 2 #6) bucket every user together and make
# request logs useless. ProxyFix rewrites remote_addr/scheme/host from the
# X-Forwarded-* headers set by exactly ONE trusted proxy hop (Render).
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

# CORS Configuration - Allow frontend to access backend
# Single source of truth for allowed origins (used by both flask-cors AND the
# explicit preflight handler below, so they can't drift apart).
_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5000",
    "http://localhost:5001",
    "https://tradosphere.vercel.app",
    "https://www.tradosphere.vercel.app",
    # SECURITY (F-09): the "https://*.vercel.app" wildcard was removed. With
    # supports_credentials=True it matched ANY Vercel deployment (including
    # attacker-controlled ones), allowing credentialed cross-origin calls on
    # behalf of logged-in users. Only the exact production URL(s) are allowed.
    "https://tradosphere.in",
    "https://www.tradosphere.in",
    "https://tradosphere-v3.onrender.com",
]

# Allow additional production origins via env (comma-separated) without a code
# change, e.g. CORS_ORIGINS="https://app.mydomain.com,https://mydomain.com".
_extra_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
for _o in _extra_origins:
    if _o not in _ALLOWED_ORIGINS:
        _ALLOWED_ORIGINS.append(_o)


def _is_origin_allowed(origin: str) -> bool:
    """Match an Origin against the allow-list, supporting a single `*` wildcard
    label (e.g. https://*.vercel.app matches https://foo.vercel.app)."""
    if not origin:
        return False
    for pattern in _ALLOWED_ORIGINS:
        if pattern == origin:
            return True
        if "*" in pattern:
            # Turn the pattern into a strict regex: escape everything, then
            # allow the single `*` to match one or more non-dot/non-slash chars.
            import re
            regex = "^" + re.escape(pattern).replace(r"\*", r"[^./]+") + "$"
            if re.match(regex, origin):
                return True
    return False


# Enable CORS for ALL routes with explicit headers
CORS(app,
    origins=_ALLOWED_ORIGINS,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    expose_headers=["Content-Type", "Authorization"],
    supports_credentials=True,
    max_age=3600,
    send_wildcard=False
)

# Add explicit CORS headers for preflight requests
@app.before_request
def handle_preflight():
    """Handle CORS preflight requests explicitly.

    AUDIT FIX #5: only reflect the Origin back when it is on the allow-list.
    Previously this reflected ANY origin together with Allow-Credentials:true,
    which let any website make credentialed cross-origin requests. A
    disallowed origin now gets NO Access-Control-Allow-Origin header (the
    browser then blocks the request, which is the correct behavior).
    """
    if request.method == "OPTIONS":
        response = make_response()
        origin = request.headers.get("Origin", "")
        if _is_origin_allowed(origin):
            response.headers.add("Access-Control-Allow-Origin", origin)
            response.headers.add("Access-Control-Allow-Credentials", "true")
        response.headers.add("Vary", "Origin")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,Accept")
        response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS,PATCH")
        response.headers.add("Access-Control-Max-Age", "3600")
        return response, 200

# Configuration
# ===== SECURITY GATE: secrets must be strong in production =====
# Previously SECRET_KEY/JWT_SECRET fell back to well-known hardcoded defaults
# ('tradosphere-secret-key' / 'jwt-secret-key'). Anyone could forge sessions or
# JWTs with those. In production we now FAIL FAST if a secret is missing or left
# at a known-weak default; in development we generate a random ephemeral secret
# so local dev still works without configuration.
import secrets as _secrets

_IS_PROD = os.getenv("FLASK_ENV", "production").lower() == "production"
_WEAK_SECRETS = {
    "", "tradosphere-secret-key", "jwt-secret-key",
    "change-me", "changeme", "secret", "<generate-strong-secret-key>",
}


def _require_secret(env_name: str) -> str:
    """Return a strong secret from env, or fail fast in prod / generate in dev."""
    value = (os.getenv(env_name) or "").strip()
    if value in _WEAK_SECRETS or len(value) < 16:
        if _IS_PROD:
            raise RuntimeError(
                f"SECURITY: {env_name} is missing or weak. Set a strong (>=32 char) "
                f"random value in the environment before starting in production. "
                f"Generate one with: python3 -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        # Development: ephemeral random secret (sessions reset on restart).
        logger.warning(f"⚠️  {env_name} not set — using an ephemeral dev secret (DEV ONLY).")
        return _secrets.token_urlsafe(48)
    return value


app.config['SECRET_KEY'] = _require_secret('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = _require_secret('JWT_SECRET')

# ===== SECURITY GATE: secure session cookies in production =====
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=_IS_PROD,   # HTTPS-only cookies in production
    PREFERRED_URL_SCHEME="https" if _IS_PROD else "http",
)

# ===== COMPLIANCE GATE: trading risk disclaimer =====
# Signals are algorithmic outputs, NOT investment advice. This disclaimer is
# attached to signal responses and exposed at /api/disclaimer so the frontend
# can surface it. (This is standard product copy, not legal advice — have a
# professional review your final Terms before taking paid users.)
TRADING_DISCLAIMER = (
    "Tradosphere provides algorithmically generated market analysis for "
    "educational and informational purposes only. It is NOT investment advice, "
    "a recommendation, or a solicitation to buy or sell any security. Trading in "
    "equities, derivatives, and options carries substantial risk of loss and is "
    "not suitable for every investor. Past performance does not guarantee future "
    "results. You are solely responsible for your own trading decisions. Consult "
    "a SEBI-registered financial advisor before trading."
)
DISCLAIMER_VERSION = "2026-06-26"

# Register error handlers and logging middleware
from error_handler import register_error_handlers, register_logging_middleware
register_error_handlers(app)
register_logging_middleware(app)
logger.info("✅ Error handlers and logging middleware registered")

# ===== MONITORING & METRICS (Tier 2 #10) =====
# Wire the performance monitor: record count/latency/status for every request.
from monitoring import performance_monitor

# App start time for uptime reporting.
APP_START_TIME = datetime.utcnow()


@app.before_request
def _metrics_before_request():
    """Stamp the request start time for latency measurement."""
    g._metrics_start = datetime.utcnow()


@app.after_request
def _metrics_after_request(response):
    """Record this request into the performance monitor."""
    try:
        start = getattr(g, "_metrics_start", None)
        if start is not None:
            duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
            # Use the matched URL rule (not the raw path) so metrics don't
            # explode into a separate bucket per dynamic id.
            # AUDIT FIX #4: unmatched routes (404s) have NO url_rule. Bucketing
            # them under the raw path let a path-scanner create unlimited
            # metric keys (memory-growth / DoS vector). Collapse them all into a
            # single "<unmatched>" bucket instead.
            endpoint = request.url_rule.rule if request.url_rule else "<unmatched>"
            performance_monitor.record_endpoint_call(
                endpoint, request.method, round(duration_ms, 2), response.status_code
            )
    except Exception as _metrics_err:
        logger.debug(f"metrics recording skipped: {_metrics_err}")
    return response


@app.after_request
def _security_headers(response):
    """F-15/F-16: attach defensive security headers to every response.

    These mitigate clickjacking (X-Frame-Options/frame-ancestors), MIME
    sniffing (X-Content-Type-Options), referrer leakage, and enforce HTTPS in
    production (HSTS). The CSP is intentionally conservative; the frontend is
    served from Vercel as static files and talks to this API over fetch, so it
    does not need inline-script privileges from this origin.
    """
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    )
    # Only assert HSTS in production (and over HTTPS) so local http dev still works.
    if os.getenv("FLASK_ENV", "").lower() == "production":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


def html_escape(value) -> str:
    """F-15: escape user-controlled text before it is embedded in any HTML.

    Use this for any value that originates from user input and gets rendered
    into an HTML context (e.g. server-rendered fragments, email templates).
    """
    import html as _html
    return _html.escape("" if value is None else str(value), quote=True)


logger.info("✅ Monitoring & metrics wired (Tier 2 #10)")
logger.info("✅ Security headers + HTML escaping wired (F-15/F-16)")

# ===== INPUT VALIDATION (Tier 2 #7) =====
from schemas import (
    validate_body, GenerateSignalSchema, BatchGenerateSchema, CreateTradeSchema
)
logger.info("✅ Input validation schemas loaded (Tier 2 #7)")

# ===== REDIS CACHING (Tier 2 #9) =====
from cache import cache, cache_get_or_set
logger.info(f"✅ Cache layer loaded (Tier 2 #9) — enabled={cache.enabled}")

# ===== API RATE LIMITING (Tier 2 #6) =====
# Init early so the limiter is bound before blueprints register. Limits are
# Redis-backed (shared across workers) and FAIL-OPEN if storage is down.
from rate_limit import init_rate_limiter, limiter, AUTH_LIMITS
init_rate_limiter(app)

# ===== REAL-TIME WEBSOCKETS (Tier 2 #8) =====
from realtime import (
    init_socketio, socketio, emit_signal_update, start_price_broadcaster
)
init_socketio(app)

def _ws_get_live_prices():
    """Return current REAL index prices for the WebSocket broadcaster.

    INTEGRITY (F-19): this previously fell back to hardcoded prices
    (NIFTY 24047.50 / BANKNIFTY 57489.75 / FINNIFTY 18950.00) whenever the
    broker was unavailable, streaming fabricated ticks to clients as if live —
    the same problem F-19 fixes for the REST /api/market/live endpoint. It now
    returns ONLY real LTPs that are actually available; when nothing real is
    available it returns an empty dict and the broadcaster (which only emits on
    a truthy result) pushes nothing. No fake prices ever go over the socket.
    """
    prices = {}
    try:
        if market is not None and market.is_authenticated():
            sources = {
                "NIFTY": market.get_nifty_price,
                "BANKNIFTY": market.get_banknifty_price,
                "FINNIFTY": market.get_finnifty_price,
            }
            for sym, fetch in sources.items():
                data = fetch() or {}
                ltp = data.get("ltp")
                if ltp is not None:
                    prices[sym] = ltp
    except Exception as _ws_err:
        logger.debug(f"WS price fetch skipped: {_ws_err}")
    return prices


# The perpetual broadcaster is opt-in (off by default) so importing the app
# for tests never spawns a background thread. Enable in production via env.
if os.getenv("ENABLE_WS_BROADCASTER", "false").lower() == "true":
    start_price_broadcaster(_ws_get_live_prices, interval_seconds=5)
    logger.info("✅ WS price broadcaster enabled (Tier 2 #8)")
else:
    logger.info("✅ Socket.IO ready; broadcaster opt-in (ENABLE_WS_BROADCASTER)")

# Initialize databases
logger.info("🔧 Initializing databases...")
init_db()
init_user_db()
init_subscription_db()
init_leads_db()
init_paper_trading_db()
logger.info("✅ Databases initialized")

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(billing_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(leads_bp)
app.register_blueprint(trading_bp)
app.register_blueprint(backtest_bp)

# ===== APPLY RATE LIMITS (Tier 2 #6) =====
# AUDIT FIX #11: apply the strict 10/min limit ONLY to credential-verifying
# endpoints (login/signup/google/forgot-password/reset-password) rather than
# the entire auth blueprint. The old blanket application also throttled
# /refresh, /logout and /me, which broke normal flows (e.g. silent token
# refresh) for active users. The default limits still protect those routes.
# (Monitoring-probe exemptions are applied at the end of the module.)
_AUTH_STRICT_ENDPOINTS = (
    "auth.login", "auth.signup", "auth.google_auth",
    "auth.forgot_password", "auth.reset_password",
)
_applied = []
for _ep in _AUTH_STRICT_ENDPOINTS:
    _vf = app.view_functions.get(_ep)
    if _vf is not None:
        # Wrap the registered view in-place with the strict limit.
        app.view_functions[_ep] = limiter.limit(AUTH_LIMITS)(_vf)
        _applied.append(_ep)
logger.info(f"✅ Strict rate limits applied to {len(_applied)} auth endpoints (Tier 2 #6): {_applied}")

# Register multi-tenant middleware
MultiTenantMiddleware.register_tenant_middleware(app) if hasattr(MultiTenantMiddleware, 'register_tenant_middleware') else None

# Global market data instance
market = None
_market_initialized = False
# F-18: the broker can be (re)connected from a background thread while request
# handlers read the `market` global concurrently. Guard every assignment and
# read of `market` with this lock so a request can never observe a half-set or
# torn reference during reconnection.
_market_lock = threading.Lock()


def get_market():
    """Thread-safe accessor for the current market data instance."""
    with _market_lock:
        return market

def init_market_data():
    """Initialize market data with credentials

    NOTE: Gunicorn with multiple workers will attempt initialization in each worker.
    Angel One has rate limits on authentication. We catch auth failures gracefully
    and allow workers to boot without broker. Broker will auto-retry on first request.
    """
    global market, _market_initialized

    # Prevent multiple initialization attempts within same worker
    if _market_initialized:
        return

    _market_initialized = True

    try:
        api_key = os.getenv("ANGEL_ONE_API_KEY", "")
        client_code = os.getenv("ANGEL_ONE_CLIENT_CODE", "")
        pin = os.getenv("ANGEL_ONE_PIN", "")
        totp_secret = os.getenv("ANGEL_ONE_TOTP_SECRET", "")

        if not api_key or not client_code or not pin:
            logger.warning("⚠️  Angel One credentials not fully configured")
            with _market_lock:
                market = None
            return

        # Create market data instance (handles auth internally)
        # This may fail with rate limit on multiple workers
        _m = AngelOneMarketData(api_key, client_code, pin, totp_secret)
        with _market_lock:
            market = _m
        logger.info("✅ Angel One market data initialized successfully")
    except Exception as e:
        # CRITICAL FIX: Catch auth failures and allow worker to boot
        # Instead of crashing, gracefully degrade to fallback prices
        logger.info(f"⚠️  Market data initialization failed: {str(e)}")

        # Check if it's a rate limit error
        if "rate" in str(e).lower() or "429" in str(e) or "access denied" in str(e).lower():
            logger.warning("⚠️  Angel One rate limit detected (multiple worker auth attempts)")
            logger.warning("⚠️  Worker will boot without broker connection")
            logger.warning("⚠️  Fallback prices will be used until broker recovers")
        else:
            logger.info(f"⚠️  Error details: {str(e)}")

        # Set market to None to trigger fallback behavior
        # This allows worker to boot and serve requests with fallback data
        with _market_lock:
            market = None

# Initialize at module import time
# Multiple workers will each attempt this, but with graceful degradation
init_market_data()

def _retry_broker_connection():
    """Background thread: retry broker connection if initial auth failed

    This helps recover from Angel One rate limiting by retrying after 30s delay.
    Runs in background without blocking worker boot.
    """
    global market, _market_initialized

    if market is not None:
        # Broker already connected, nothing to do
        return

    # Wait before retrying to avoid immediate rate limiting
    time.sleep(30)

    max_retries = 3
    retry_count = 0

    while market is None and retry_count < max_retries:
        retry_count += 1
        logger.info(f"\n🔄 Broker connection retry {retry_count}/{max_retries}...")

        try:
            api_key = os.getenv("ANGEL_ONE_API_KEY", "")
            client_code = os.getenv("ANGEL_ONE_CLIENT_CODE", "")
            pin = os.getenv("ANGEL_ONE_PIN", "")
            totp_secret = os.getenv("ANGEL_ONE_TOTP_SECRET", "")

            if not api_key or not client_code or not pin:
                logger.warning("⚠️  Credentials still not configured, giving up")
                break

            _m = AngelOneMarketData(api_key, client_code, pin, totp_secret)
            with _market_lock:
                market = _m
            logger.info("✅ Broker reconnected successfully on retry!")
            break

        except Exception as e:
            logger.info(f"⚠️  Retry {retry_count} failed: {str(e)[:100]}")
            if retry_count < max_retries:
                wait_time = 30 * retry_count  # Exponential backoff: 30s, 60s, 90s
                logger.info(f"   Waiting {wait_time}s before next retry...")
                time.sleep(wait_time)

    if market is None and retry_count >= max_retries:
        logger.info(f"❌ Broker connection failed after {max_retries} retries, will use fallback prices")

# Start background retry thread (only if initial init failed)
if market is None:
    logger.info("🔄 Starting background broker reconnection thread...")
    retry_thread = threading.Thread(target=_retry_broker_connection, daemon=True)
    retry_thread.start()

# Helper function to serve HTML files
def get_html_file(filename):
    """Safely get HTML file path"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)

    # Try frontend folder first
    filepath = os.path.join(parent_dir, 'frontend', filename)
    if not os.path.exists(filepath):
        # Try backend folder as fallback
        filepath = os.path.join(script_dir, filename)

    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.info(f"Error reading {filename}: {e}")
        return None

# ===== PUBLIC CONFIG ENDPOINT =====
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint - returns OK if backend is running"""
    return APIResponse.success({
        "status": "online",
        "service": "Tradosphere Backend",
        "version": "3.1",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get public configuration (no auth required)"""
    return APIResponse.success({
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        # Stripe removed — paid plans are "coming soon", so no payment key is
        # exposed to the frontend.
        "payments_available": False,
        "environment": os.getenv("FLASK_ENV", "production"),
        "api_version": "3.1"
    })

@app.route('/config_v3_1.js', methods=['GET'])
def serve_config():
    """Serve config_v3_1.js file"""
    config_content = get_html_file('config_v3_1.js')
    if config_content:
        return config_content, 200, {'Content-Type': 'application/javascript; charset=utf-8'}
    return "console.error('config_v3_1.js not found');", 200, {'Content-Type': 'application/javascript'}

@app.route('/favicon.ico', methods=['GET'])
def favicon():
    """Serve favicon"""
    return send_file('frontend/favicon.ico', mimetype='image/x-icon') if os.path.exists('frontend/favicon.ico') else '', 204

# ===== USER PAGES =====
@app.route('/user/dashboard', methods=['GET'])
def user_dashboard():
    """Serve user dashboard with live market data"""
    html_content = get_html_file('dashboard_live_v3.1.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return APIResponse.not_found("dashboard_live_v3.1.html not found")

@app.route('/user/<page>', methods=['GET'])
def user_page(page):
    """Serve user pages dynamically"""
    allowed_pages = ['market', 'portfolio', 'profile', 'settings', 'signals', 'subscription', 'trading']
    if page not in allowed_pages:
        return jsonify({"status": "error", "message": f"Page {page} not found"}), 404

    html_content = get_html_file(f'frontend/user/{page}.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return jsonify({"status": "error", "message": f"{page}.html not found"}), 404

# ===== ADMIN PAGES =====
@app.route('/admin/dashboard', methods=['GET'])
def admin_dashboard_page():
    """Serve admin dashboard"""
    html_content = get_html_file('frontend/admin/dashboard.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return APIResponse.not_found("dashboard.html not found")

@app.route('/admin/<page>', methods=['GET'])
def admin_page(page):
    """Serve admin pages dynamically"""
    allowed_pages = ['analytics', 'health', 'settings', 'signals', 'subscriptions', 'users']
    if page not in allowed_pages:
        return jsonify({"status": "error", "message": f"Page {page} not found"}), 404

    html_content = get_html_file(f'frontend/admin/{page}.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return jsonify({"status": "error", "message": f"{page}.html not found"}), 404

# ===== AUTH PAGES =====
@app.route('/login', methods=['GET'])
def login_page():
    """Serve simple login page with admin & user options"""
    html_content = get_html_file('login_v3.1.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}

    return jsonify({
        "status": "error",
        "message": "login_v3.1.html not found in " + os.getcwd()
    }), 404

@app.route('/', methods=['GET'])
def home():
    """Root endpoint - API is running"""
    return APIResponse.success({
        "service": "Tradosphere Trading Platform",
        "status": "online",
        "version": "3.1",
        "message": "Backend API is running",
        "endpoints": {
            "auth": "/api/auth/login, /api/auth/signup, /api/auth/logout",
            "user": "/api/user/profile, /api/user/api-keys",
            "trading": "/api/market/live, /api/analysis/technical",
            "signals": "/api/signals/generate, /api/signals/history",
            "options": "/api/options/chain, /api/options/greeks"
        }
    })

@app.route('/dashboard', methods=['GET'])
@app.route('/dashboard_live_v3.1.html', methods=['GET'])
def dashboard():
    """Serve Angel One-style trading dashboard"""
    html_content = get_html_file('dashboard_live_v3.1.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}

    return jsonify({
        "status": "error",
        "message": "dashboard_live_v3.1.html not found"
    }), 404

@app.route('/demo', methods=['GET'])
def demo_dashboard():
    """Serve demo dashboard (no auth required) - shows sample data"""
    html_content = get_html_file('dashboard_unified.html')
    if html_content:
        # Inject demo flag
        demo_html = html_content.replace(
            '<script>',
            '<script>const DEMO_MODE = true;</script><script>',
            1
        )
        return demo_html, 200, {'Content-Type': 'text/html; charset=utf-8'}

    return jsonify({
        "status": "error",
        "message": "Dashboard not found"
    }), 404

@app.route('/trading', methods=['GET'])
@AuthDecorator.token_required
def trading_dashboard():
    """Serve live trading dashboard"""
    html_content = get_html_file('live_trading_dashboard.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}

    return jsonify({
        "status": "error",
        "message": "Trading dashboard not found"
    }), 404

# ===== TEST DASHBOARDS (for local testing) =====
@app.route('/test/dashboard-live', methods=['GET'])
def test_dashboard_live():
    """Test dashboard_live_v3.1.html"""
    html_content = get_html_file('dashboard_live_v3.1.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return APIResponse.not_found("dashboard_live_v3.1.html not found")

@app.route('/test/dashboard-saas', methods=['GET'])
def test_dashboard_saas():
    """Test saas_dashboard.html"""
    html_content = get_html_file('saas_dashboard.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return APIResponse.not_found("saas_dashboard.html not found")

@app.route('/test/dashboard-unified', methods=['GET'])
def test_dashboard_unified():
    """Test dashboard_unified.html"""
    html_content = get_html_file('dashboard_unified.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return APIResponse.not_found("dashboard_unified.html not found")

@app.route('/test/dashboard-pro', methods=['GET'])
def test_dashboard_pro():
    """Test dashboard_pro.html"""
    html_content = get_html_file('dashboard_pro.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return APIResponse.not_found("dashboard_pro.html not found")

@app.route('/test/dashboard-5tabs', methods=['GET'])
def test_dashboard_5tabs():
    """Test dashboard_unified_5tabs.html - NEW 5-TAB UNIFIED DASHBOARD"""
    html_content = get_html_file('dashboard_unified_5tabs.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return APIResponse.not_found("dashboard_unified_5tabs.html not found")

@app.route('/test/login', methods=['GET'])
def test_login():
    """Test login_v3.1.html"""
    html_content = get_html_file('login_v3.1.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return APIResponse.not_found("login_v3.1.html not found")

# ===== HEALTH & STATUS =====
@app.route('/api/health', methods=['GET'])
def health():
    """Simple health check - used by load balancers"""
    return jsonify({
        "status": "healthy",
        "service": "Tradosphere SaaS v3",
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@app.route('/api/health/detailed', methods=['GET'])
def health_detailed():
    """Detailed health check - includes token status, database, broker connection"""
    try:
        # Check broker connection
        broker_status = "disconnected"
        token_status = None

        if market is not None:
            if market.is_authenticated():
                broker_status = "connected"
                # Get token information
                token_status = market.get_token_status() if hasattr(market, 'get_token_status') else {
                    "authenticated": True,
                    "token_age_hours": None
                }
            else:
                broker_status = "failed_auth"

        # Check database connection
        db_status = "unknown"
        try:
            from sqlalchemy import text
            session = SessionLocal()
            session.execute(text("SELECT 1"))
            session.close()
            db_status = "connected"
        except Exception as db_error:
            db_status = f"error: {str(db_error)[:50]}"

        # Build comprehensive health response
        health_response = {
            "status": "operational" if broker_status == "connected" and db_status == "connected" else "degraded",
            "service": "Tradosphere SaaS v3",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "broker": {
                    "name": "Angel One",
                    "status": broker_status,
                    "token": token_status
                },
                "database": {
                    "status": db_status,
                    "type": "PostgreSQL/SQLite"
                },
                "api_server": {
                    "status": "operational",
                    "version": "3.0",
                    "uptime_available": True
                }
            },
            "checks_performed": [
                "broker_connection",
                "token_freshness",
                "database_connection",
                "api_server_health"
            ]
        }

        http_status = 200 if health_response["status"] == "operational" else 503
        return jsonify(health_response), http_status

    except Exception as e:
        logger.error(f"health_detailed error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Health check failed",
            "timestamp": datetime.utcnow().isoformat()
        }), 500


# ===== METRICS & DEEP HEALTH (Tier 2 #10) =====
@app.route('/metrics', methods=['GET'])
def metrics():
    """Live performance metrics: per-endpoint count, latency, error rate."""
    return jsonify({
        "status": "success",
        "metrics": performance_monitor.get_all_metrics(),
        "uptime_seconds": int((datetime.utcnow() - APP_START_TIME).total_seconds()),
        "timestamp": datetime.utcnow().isoformat()
    }), 200


@app.route('/health/deep', methods=['GET'])
def health_deep():
    """Deep health check: component status + uptime + live metrics summary.

    Lightweight by design — reuses the already-connected global broker and a
    single DB ping. Returns 200 while the core (DB) is up even if the broker is
    degraded; only returns 503 if the core service itself is down.
    """
    # Broker (reuse the existing global connection — no new auth)
    broker_status = "disconnected"
    try:
        if market is not None and market.is_authenticated():
            broker_status = "connected"
        elif market is not None:
            broker_status = "failed_auth"
    except Exception:
        broker_status = "error"

    # Database (single lightweight ping)
    db_status = "connected"
    try:
        from sqlalchemy import text
        _session = SessionLocal()
        _session.execute(text("SELECT 1"))
        _session.close()
    except Exception as db_err:
        logger.warning(f"health/deep DB ping failed: {db_err}")
        db_status = "error"

    # Live metrics summary
    all_metrics = performance_monitor.get_all_metrics()
    endpoints = all_metrics.get("endpoints", {})
    total_requests = sum(e.get("count", 0) for e in endpoints.values())
    if total_requests > 0:
        avg_latency = round(
            sum(e["avg_time_ms"] * e["count"] for e in endpoints.values()) / total_requests, 2
        )
        # AUDIT FIX #8: sum the EXACT raw error counts now exposed by the
        # monitor, instead of reconstructing them from rounded percentages.
        total_errors = sum(e.get("error_count", 0) for e in endpoints.values())
        error_rate = round(total_errors / total_requests * 100, 2)
    else:
        avg_latency = 0.0
        error_rate = 0.0

    core_ok = db_status == "connected"
    if core_ok and broker_status == "connected":
        overall = "healthy"
    elif core_ok:
        overall = "degraded"
    else:
        overall = "unhealthy"

    payload = {
        "status": overall,
        "uptime_seconds": int((datetime.utcnow() - APP_START_TIME).total_seconds()),
        "components": {
            "broker": broker_status,
            "database": db_status,
            "cache": cache.status()["backend"],
            "api_server": "operational"
        },
        "metrics_summary": {
            "total_requests": total_requests,
            "avg_latency_ms": avg_latency,
            "error_rate_percent": error_rate,
            "tracked_endpoints": len(endpoints)
        },
        "version": "3.1",
        "environment": os.getenv("FLASK_ENV", "production"),
        "timestamp": datetime.utcnow().isoformat()
    }
    return jsonify(payload), (200 if core_ok else 503)


@app.route('/api/status', methods=['GET'])
def status():
    """System status including auth"""
    try:
        broker_connected = market is not None and market.is_authenticated() if market else False

        return APIResponse.success({
            "status": "operational",
            "service": "Tradosphere SaaS v3.1",
            "authentication": "enabled",
            "multi_tenant": "enabled",
            "broker": "Angel One",
            "broker_connected": broker_connected,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return APIResponse.server_error(str(e), e)

# ===== MARKET DATA (With User Context) =====
@app.route('/api/market/overview', methods=['GET'])
@AuthDecorator.token_required
def market_overview():
    """Get market overview with major indices (Redis-cached, 5s TTL)."""
    try:
        def _build_overview():
            symbols_data = []

            # Default symbols to display
            default_symbols = [
                {'symbol': 'NIFTY', 'exchange': 'NSE', 'token': '99926000'},
                {'symbol': 'BANKNIFTY', 'exchange': 'NSE', 'token': '99926009'},
                {'symbol': 'SENSEX', 'exchange': 'BSE', 'token': '1'},
                {'symbol': 'FINNIFTY', 'exchange': 'NSE', 'token': '99926037'},
            ]

            for sym in default_symbols:
                try:
                    if market and market.is_authenticated():
                        price = market.get_ltp(sym['exchange'], sym['symbol'], sym['token'])
                    else:
                        # Mock data fallback
                        price = 50000 + (hash(sym['symbol']) % 5000)

                    change = (hash(sym['symbol']) % 100) * 10 - 500
                    change_percent = (change / price) * 100 if price else 0

                    symbols_data.append({
                        'name': sym['symbol'],
                        'price': round(price, 2),
                        'change': round(change, 2),
                        'changePercent': round(change_percent, 2),
                        'volume': hash(sym['symbol']) % 10000000,
                        'openInterest': hash(sym['symbol']) % 1000000
                    })
                except Exception as e:
                    logger.info(f"⚠️  {sym['symbol']} fetch error: {e}")

            return {
                "symbols": symbols_data,
                "timestamp": datetime.utcnow().isoformat()
            }

        # Market overview uses the default symbol set (no per-user variation),
        # so a single global key is safe. Short TTL keeps prices fresh.
        data, _hit = cache_get_or_set("market:overview", ttl=5, producer=_build_overview)
        return APIResponse.success(data)

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@app.route('/api/market/live', methods=['GET'])
@AuthDecorator.token_required
def market_live():
    """Get live NIFTY and BANKNIFTY prices (Dashboard format)"""
    try:
        user_id = g.user_id

        # Try to get real Angel One data
        tickers = []

        if market and market.is_authenticated():
            # Get NIFTY data
            try:
                nifty_ltp = market.get_ltp("NSE", "NIFTY", "99926000")
                # Get historical candles for OHLC data
                nifty_candles = market.get_historical_candles("NIFTY", "1", 2)

                if nifty_ltp and nifty_candles and len(nifty_candles) > 0:
                    current_candle = nifty_candles[-1] if nifty_candles else {}
                    prev_candle = nifty_candles[-2] if len(nifty_candles) > 1 else {}

                    prev_close = float(prev_candle.get("close", nifty_ltp)) if prev_candle else nifty_ltp
                    change = nifty_ltp - prev_close
                    change_percent = (change / prev_close * 100) if prev_close else 0

                    tickers.append({
                        "symbol": "NIFTY",
                        "current_price": round(nifty_ltp, 2),
                        "change": round(change, 2),
                        "change_percent": round(change_percent, 2),
                        "open": round(float(current_candle.get("open", nifty_ltp)), 2),
                        "high": round(float(current_candle.get("high", nifty_ltp)), 2),
                        "low": round(float(current_candle.get("low", nifty_ltp)), 2),
                        "volume": int(current_candle.get("volume", 0)),
                        "timestamp": datetime.utcnow().isoformat()
                    })
            except Exception as e:
                logger.info(f"⚠️  NIFTY fetch error: {str(e)}")

            # Get BANKNIFTY data
            try:
                banknifty_ltp = market.get_ltp("NSE", "BANKNIFTY", "99926009")
                banknifty_candles = market.get_historical_candles("BANKNIFTY", "1", 2)

                if banknifty_ltp and banknifty_candles and len(banknifty_candles) > 0:
                    current_candle = banknifty_candles[-1] if banknifty_candles else {}
                    prev_candle = banknifty_candles[-2] if len(banknifty_candles) > 1 else {}

                    prev_close = float(prev_candle.get("close", banknifty_ltp)) if prev_candle else banknifty_ltp
                    change = banknifty_ltp - prev_close
                    change_percent = (change / prev_close * 100) if prev_close else 0

                    tickers.append({
                        "symbol": "BANKNIFTY",
                        "current_price": round(banknifty_ltp, 2),
                        "change": round(change, 2),
                        "change_percent": round(change_percent, 2),
                        "open": round(float(current_candle.get("open", banknifty_ltp)), 2),
                        "high": round(float(current_candle.get("high", banknifty_ltp)), 2),
                        "low": round(float(current_candle.get("low", banknifty_ltp)), 2),
                        "volume": int(current_candle.get("volume", 0)),
                        "timestamp": datetime.utcnow().isoformat()
                    })
            except Exception as e:
                logger.info(f"⚠️  BANKNIFTY fetch error: {str(e)}")

        # F-19: when the broker is unavailable, DO NOT inject hardcoded ticker
        # prices that render as if live. Return an explicit offline status with
        # no fabricated tickers so the frontend shows a 'market data offline'
        # state instead of stale numbers presented as current.
        if not tickers:
            return APIResponse.success({
                "tickers": [],
                "data_status": "offline",
                "message": "Live market data is currently unavailable (broker not connected).",
                "timestamp": datetime.utcnow().isoformat()
            })

        return APIResponse.success({
            "tickers": tickers,
            "data_status": "live",
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.info(f"❌ Error in market_live: {str(e)}")
        return APIResponse.server_error(str(e), e)

# ===== TECHNICAL ANALYSIS (With User Context & Tenant Filter) =====
@app.route('/api/analysis/technical', methods=['GET'])
@AuthDecorator.token_required
def technical_analysis():
    """Get technical analysis with real indicators from candle data"""
    try:
        user_id = g.user_id
        symbol = request.args.get('symbol', 'NIFTY')
        interval = request.args.get('interval', '15')
        limit = request.args.get('limit', 100, type=int)

        if not market or not market.is_authenticated():
            return APIResponse.unauthorized("Broker not connected")

        # Get REAL candles from Angel One. get_historical_candles() returns None
        # when live data is unavailable (F-01) — it never fabricates OHLCV.
        candles = market.get_historical_candles(symbol, interval, limit)

        if candles is None:
            return jsonify({
                "status": "error",
                "data_status": "unavailable",
                "message": f"Live market data unavailable for {symbol} — broker not yet connected. Please try again shortly."
            }), 503

        if len(candles) < 26:
            return jsonify({
                "status": "error",
                "message": f"Insufficient candle data for {symbol} (need minimum 26 candles)"
            }), 400

        # Perform technical analysis
        analysis = TechnicalEngine.analyze(candles)

        if analysis.get("status") != "success":
            return jsonify({
                "status": "error",
                "message": analysis.get("message", "Analysis failed")
            }), 400

        # Return complete analysis with all indicators
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "interval": interval,
            "candle_count": len(candles),
            "user_id": user_id,
            "trend": analysis.get("trend", "NEUTRAL"),
            "momentum": analysis.get("momentum", "NEUTRAL"),
            "setup": analysis.get("setup", "RANGE_BOUND"),
            "indicators": analysis.get("indicators", {}),
            "macd": analysis.get("macd", {}),
            "bollinger_bands": analysis.get("bollinger_bands", {}),
            "ema_crossover": analysis.get("ema_crossover", {}),
            "price_vs_indicators": analysis.get("price_vs_indicators", {}),
            "breakout": analysis.get("breakout", {}),
            "ema_crossover_signal": analysis.get("ema_crossover_signal", "NONE"),
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.info(f"Technical analysis error: {str(e)}")
        import traceback
        traceback.print_exc()
        return APIResponse.server_error(str(e), e)

# ===== OPTIONS ANALYSIS (With User Context) =====
@app.route('/api/analysis/options', methods=['GET'])
@AuthDecorator.token_required
def options_analysis():
    """Get options chain analysis (Dashboard format)"""
    try:
        user_id = g.user_id
        symbol = request.args.get('symbol', 'NIFTY')
        expiry = request.args.get('expiry', 'current')

        if not market or not market.is_authenticated():
            return APIResponse.unauthorized("Broker not connected")

        # Validate symbol
        if symbol not in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
            symbol = 'NIFTY'

        # Get REAL option chain from Angel One. get_option_chain() returns None
        # when the broker options feed is unavailable (F-02) — never fabricated.
        option_chain = market.get_option_chain(symbol, expiry)

        if option_chain is None:
            return jsonify({
                "status": "error",
                "data_status": "unavailable",
                "message": f"Live options data unavailable for {symbol} — broker options feed not connected. Please try again shortly."
            }), 503

        if option_chain.get("status") != "success":
            return jsonify({
                "status": "error",
                "message": f"Could not fetch option chain for {symbol}"
            }), 400

        # Extract data
        strikes_raw = option_chain.get("strikes", [])
        spot_price = option_chain.get("spot_price", 0)
        pcr = option_chain.get("pcr", 0)

        # Transform to dashboard format
        chain = []
        for strike_data in strikes_raw:
            strike = strike_data.get("strike", 0)
            ce = strike_data.get("ce", {})
            pe = strike_data.get("pe", {})

            # Calculate strike-level PCR
            ce_oi = ce.get("oi", 0)
            pe_oi = pe.get("oi", 0)
            strike_pcr = pe_oi / ce_oi if ce_oi > 0 else 0

            chain.append({
                "strike": strike,
                "call_oi": int(ce_oi),
                "call_ltp": float(ce.get("ltp", 0)),
                "call_iv": float(ce.get("iv", 0)),
                "call_vol": int(ce.get("volume", 0)),
                "call_change": float(ce.get("change", 0)),
                "put_oi": int(pe_oi),
                "put_ltp": float(pe.get("ltp", 0)),
                "put_iv": float(pe.get("iv", 0)),
                "put_vol": int(pe.get("volume", 0)),
                "put_change": float(pe.get("change", 0)),
                "is_atm": abs(strike - spot_price) < 50,  # Within 50 points of spot
                "pcr": round(strike_pcr, 3)
            })

        # Calculate Max Pain (highest OI concentration)
        max_pain = spot_price
        max_oi = 0
        for item in chain:
            total_oi = item["call_oi"] + item["put_oi"]
            if total_oi > max_oi:
                max_oi = total_oi
                max_pain = item["strike"]

        # Get trend analysis if available
        try:
            analysis = OptionsEngine.analyze(option_chain)
            trend = "bullish" if pcr < 1.0 else ("bearish" if pcr > 1.2 else "neutral")
        except Exception:  # AUDIT FIX #15: don't swallow KeyboardInterrupt/SystemExit
            trend = "neutral"
            analysis = {}

        return jsonify({
            "status": "success",
            "data": {
                "symbol": symbol,
                "expiry": expiry,
                "spot_price": round(spot_price, 2),
                "chain": chain,
                "pcr": round(pcr, 3),
                "max_pain": round(max_pain, 0),
                "trend": trend,
                "total_call_oi": int(option_chain.get("total_call_oi", 0)),
                "total_put_oi": int(option_chain.get("total_put_oi", 0))
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.info(f"❌ Error in options_analysis: {str(e)}")
        return APIResponse.server_error(str(e), e)

# ===== SIGNALS (Multi-tenant) =====
@app.route('/api/signals', methods=['GET'])
@AuthDecorator.token_required
def get_signals():
    """Get real trading signals for all symbols"""
    try:
        user_id = g.user_id
        # AUDIT FIX #2: getlist()'s 2nd arg is a value-coercion callable, NOT a
        # default. Passing a list there made `?symbols=X` raise TypeError (->500)
        # and made an absent param return [] instead of the intended default.
        symbols = request.args.getlist('symbols') or ['NIFTY', 'BANKNIFTY']

        def _build_signals():
            signals = []
            broker_live = bool(market and market.is_authenticated())
            for symbol in symbols:
                try:
                    # INTEGRITY: compute REAL EMA/RSI/MACD from live candles.
                    # Never feed hardcoded/fabricated indicators into the signal
                    # engine — emit an honest HOLD until real data is available.
                    technical_data = None
                    price = None
                    if broker_live:
                        candles = market.get_historical_candles(symbol, "15", 250)
                        technical_data = _quick_technical_data(candles) if candles else None

                        exch, token = _QUICK_SIGNAL_TOKENS.get(symbol, ("NSE", ""))
                        if token:
                            try:
                                price = market.get_ltp(exch, symbol, token)
                            except Exception:
                                price = None
                        if not price and candles:
                            price = candles[-1].get("close")

                    if not technical_data or not price:
                        signals.append({
                            "symbol": symbol,
                            "signal": "HOLD",
                            "reason": "Awaiting sufficient market data",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        continue

                    # Generate real signal from real indicators
                    signal = RealSignalGenerator.generate_signal(symbol, float(price), technical_data, ai_confidence=70)
                    signals.append(signal)

                except Exception as e:
                    # Log the real error for ops, but never expose raw internals to users.
                    logger.warning(f"Error generating signal for {symbol}: {e}")
                    signals.append({
                        "symbol": symbol,
                        "signal": "HOLD",
                        "reason": "Awaiting sufficient market data",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            return {
                "signals": signals,
                "count": len(signals),
                "timestamp": datetime.utcnow().isoformat()
            }

        # Signals are not user-specific (computed from market data), so key on
        # the requested symbol set. 30s TTL balances freshness vs. broker load.
        cache_key = "signals:" + ",".join(sorted(symbols))
        data, _hit = cache_get_or_set(cache_key, ttl=30, producer=_build_signals)
        # user_id is request-specific, so attach it AFTER cache (never cached).
        payload = dict(data)
        payload["user_id"] = user_id
        return APIResponse.success(payload)

    except Exception as e:
        logger.error(f"Error in get_signals: {e}", exc_info=True)
        return APIResponse.server_error(str(e), e)

@app.route('/api/signals/generate', methods=['POST'])
@AuthDecorator.token_required
@validate_body(GenerateSignalSchema)
def generate_signals():
    """
    Generate intelligent trade signals using System B (SignalGenerator)
    UNIFIED ENDPOINT: Single source of truth for all signal generation
    Dashboard, Terminal, and API clients receive identical signals
    """
    try:
        user_id = g.user_id
        symbol = request.json.get('symbol', 'NIFTY') if request.json else 'NIFTY'

        if not market or not market.is_authenticated():
            return APIResponse.unauthorized("Broker not connected")

        # Validate symbol
        if symbol not in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
            symbol = 'NIFTY'

        # Get unified signal service (System B based)
        signal_service = get_unified_signal_service(market)

        # Generate signal using System B (SignalGenerator)
        result = signal_service.generate_signal(symbol)

        # Add user context to response
        if result['status'] == 'success':
            result['user_id'] = user_id
            result['api_endpoint'] = 'unified_signal_service'
            # Real-time push: broadcast the new signal to WS 'signals' subscribers
            try:
                emit_signal_update(result.get('signal', result))
            except Exception as _ws_emit_err:
                logger.debug(f"WS signal emit skipped: {_ws_emit_err}")
            return jsonify(result), 200
        elif result['status'] == 'no_signal':
            result['user_id'] = user_id
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        # AUDIT FIX #13: log full detail server-side, but never return raw
        # str(e) to the client (Tier 1 #2). server_error hides internals in
        # production and only includes detail outside production.
        logger.error(f"Signal generation error: {str(e)}", exc_info=True)
        return APIResponse.server_error(
            "Unable to generate signals right now. Please try again shortly.", e
        )


@app.route('/api/signals/batch-generate', methods=['POST'])
@AuthDecorator.token_required
@validate_body(BatchGenerateSchema)
def batch_generate_signals():
    """
    Generate signals for multiple symbols in one call
    SYSTEM B ONLY: Ensures consistency across all symbols
    """
    try:
        user_id = g.user_id
        symbols = request.json.get('symbols', ['NIFTY', 'BANKNIFTY', 'FINNIFTY']) if request.json else ['NIFTY', 'BANKNIFTY', 'FINNIFTY']

        if not market or not market.is_authenticated():
            return APIResponse.unauthorized("Broker not connected")

        # Get unified signal service
        signal_service = get_unified_signal_service(market)

        # Generate signals for all symbols
        result = signal_service.generate_signals_batch(symbols)
        result['user_id'] = user_id

        return jsonify(result), 200

    except Exception as e:
        # AUDIT FIX #14: don't leak raw str(e) to clients (Tier 1 #2).
        logger.error(f"Batch signal generation error: {str(e)}", exc_info=True)
        return APIResponse.server_error(
            "Unable to generate signals right now. Please try again shortly.", e
        )


@app.route('/api/signals/history/<symbol>', methods=['GET'])
@AuthDecorator.token_required
def signal_history(symbol):
    """
    Get signal history for a specific symbol
    Shows all signals generated for this symbol (NIFTY, BANKNIFTY, FINNIFTY)
    """
    try:
        user_id = g.user_id
        limit = request.args.get('limit', 20, type=int)

        if symbol not in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
            return jsonify({"status": "error", "message": f"Invalid symbol: {symbol}"}), 400

        # Get unified signal service
        signal_service = get_unified_signal_service(market)

        # Get history
        history = signal_service.get_signal_history(symbol, limit)

        return jsonify({
            "status": "success",
            "symbol": symbol,
            "count": len(history),
            "user_id": user_id,
            "data": history,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@app.route('/api/signals/performance', methods=['GET'])
@AuthDecorator.token_required
def signal_performance():
    """
    Get signal performance metrics
    Win rate, accuracy, P&L tracking
    """
    try:
        user_id = g.user_id
        symbol = request.args.get('symbol')

        # Get unified signal service
        signal_service = get_unified_signal_service(market)

        # Get performance
        performance = signal_service.get_signal_performance(symbol)
        performance['user_id'] = user_id

        return jsonify({
            "status": "success",
            "data": performance,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@app.route('/api/signals/validate-consistency', methods=['POST'])
@AuthDecorator.token_required
def validate_signal_consistency():
    """
    Validate that signals are consistent across dashboard, terminal, and API
    Used to verify System B is being used everywhere
    """
    try:
        user_id = g.user_id
        symbol = request.json.get('symbol', 'NIFTY') if request.json else 'NIFTY'
        external_signal = request.json.get('signal', {}) if request.json else {}

        # Get unified signal service
        signal_service = get_unified_signal_service(market)

        # Validate consistency
        validation = signal_service.validate_signal_consistency(symbol, external_signal)
        validation['user_id'] = user_id

        return jsonify({
            "status": "success",
            "data": validation,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return APIResponse.server_error(str(e), e)

# ===== AI INSIGHTS (Smart Analysis) =====
@app.route('/api/ai-analysis', methods=['GET'])
@AuthDecorator.token_required
def get_ai_analysis():
    """Get AI analysis for a symbol from LIVE market data.

    INTEGRITY (F-07): this endpoint previously hardcoded the price
    (24000 for NIFTY / 58000 for BANKNIFTY) and fake indicators
    (EMA bullish / RSI 65 / MACD positive) and passed them to Claude as if
    they were live — so the AI narrative could describe a price the market
    was nowhere near. It now fetches the real LTP and computes real technical
    indicators from live candles, and returns HTTP 503 when the broker is
    unavailable instead of analysing fabricated inputs.
    """
    try:
        symbol = request.args.get('symbol', 'NIFTY')

        # Validate symbol
        if symbol not in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
            symbol = 'NIFTY'

        if not market or not market.is_authenticated():
            return jsonify({
                "status": "error",
                "data_status": "unavailable",
                "message": f"Live market data unavailable for {symbol} — broker not connected."
            }), 503

        # Live LTP from the broker (never hardcoded)
        if symbol == 'NIFTY':
            price_data = market.get_nifty_price()
        elif symbol == 'BANKNIFTY':
            price_data = market.get_banknifty_price()
        else:
            price_data = market.get_finnifty_price()

        if not price_data or not price_data.get('ltp'):
            return jsonify({
                "status": "error",
                "data_status": "unavailable",
                "message": f"Live price unavailable for {symbol} — broker not connected."
            }), 503

        price = float(price_data['ltp'])

        # Real candles + technical indicators (None when unavailable — F-01)
        candles = market.get_historical_candles(symbol, '15', 100)
        if candles is None or len(candles) < 26:
            return jsonify({
                "status": "error",
                "data_status": "unavailable",
                "message": f"Live technical data unavailable for {symbol} — insufficient live candles."
            }), 503

        technical = TechnicalEngine.analyze(candles)
        if technical.get("status") != "success":
            return jsonify({
                "status": "error",
                "message": "Technical analysis failed"
            }), 400

        # Real change %: latest live price vs previous candle close
        try:
            prev_close = float(candles[-2]['close'])
            change_percent = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
        except Exception:
            change_percent = 0.0

        # Pass REAL indicators (not hardcoded) to Claude
        technical_for_ai = {
            "trend": technical.get("trend"),
            "momentum": technical.get("momentum"),
            "setup": technical.get("setup"),
            "indicators": technical.get("indicators", {}),
            "macd": technical.get("macd", {}),
            "ema_crossover_signal": technical.get("ema_crossover_signal"),
        }

        analysis = ClaudeAIService.analyze_market_data(
            symbol,
            price,
            change_percent,
            technical_for_ai
        )

        if analysis.get("status") == "error":
            return jsonify({
                "status": "error",
                "message": analysis.get("error", "AI analysis service is temporarily unavailable"),
                "code": analysis.get("code", "AI_SERVICE_UNAVAILABLE")
            }), 503

        return APIResponse.success(analysis.get('analysis', {}))

    except Exception as e:
        logger.info(f"❌ Error in get_ai_analysis: {str(e)}")
        return APIResponse.server_error(str(e), e)


@app.route('/api/analysis/ai-insights', methods=['POST'])
@AuthDecorator.token_required
def ai_insights():
    """Generate AI-powered market insights and recommendations"""
    try:
        user_id = g.user_id
        symbol = request.json.get('symbol', 'NIFTY') if request.json else 'NIFTY'

        if not market or not market.is_authenticated():
            return APIResponse.unauthorized("Broker not connected")

        # Validate symbol
        if symbol not in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
            symbol = 'NIFTY'

        # Get market data
        if symbol == 'NIFTY':
            market_data_obj = market.get_nifty_price()
        elif symbol == 'BANKNIFTY':
            market_data_obj = market.get_banknifty_price()
        else:
            market_data_obj = market.get_finnifty_price()

        if not market_data_obj:
            return jsonify({"status": "error", "message": f"Could not fetch market data for {symbol}"}), 400

        market_for_ai = {
            "current_price": market_data_obj.get('ltp', 0)
        }

        # Get options chain (REAL data only; None when unavailable — F-02)
        option_chain = market.get_option_chain(symbol, 'current')
        if option_chain is None:
            return jsonify({
                "status": "error",
                "data_status": "unavailable",
                "message": f"Live options data unavailable for {symbol} — broker not connected."
            }), 503
        if option_chain.get("status") != "success":
            return jsonify({
                "status": "error",
                "message": f"Could not fetch option chain for {symbol}"
            }), 400

        options_for_ai = {
            "pcr": option_chain.get("pcr", 1.0),
            "max_pain": option_chain.get("max_pain", market_for_ai['current_price'])
        }

        # Get technical indicators (REAL candles only; None when unavailable — F-01)
        candles = market.get_historical_candles(symbol, '15', 100)
        if candles is None:
            return jsonify({
                "status": "error",
                "data_status": "unavailable",
                "message": f"Live market data unavailable for {symbol} — broker not connected."
            }), 503
        if len(candles) < 26:
            return jsonify({
                "status": "error",
                "message": f"Insufficient candle data for {symbol}"
            }), 400

        technical_for_ai = TechnicalEngine.analyze(candles)
        if technical_for_ai.get("status") != "success":
            return jsonify({
                "status": "error",
                "message": "Technical analysis failed"
            }), 400

        # Generate signals
        signals = SignalsEngine.generate_signals(
            market_for_ai,
            options_for_ai,
            technical_for_ai,
            symbol
        )

        # Get AI insights from both engines
        ai_analysis = AIAnalysisEngine.analyze_market(
            market_for_ai,
            options_for_ai,
            technical_for_ai,
            signals,
            symbol
        )

        # Also get Claude AI insights
        claude_analysis = ClaudeAIService.analyze_market_data(
            symbol,
            market_for_ai.get('current_price', 0),
            0,
            technical_for_ai.get('indicators', {}) if technical_for_ai.get('status') == 'success' else {},
            options_for_ai
        )

        if ai_analysis.get("status") != "success":
            return APIResponse.bad_request("AI analysis failed")

        return APIResponse.success({
            "symbol": symbol,
            "analysis": ai_analysis,
            "claude_insights": claude_analysis.get('analysis', {}),
            "signals": signals,
            "source": ["AIAnalysisEngine", "Claude AI"]
        })

    except Exception as e:
        logger.info(f"AI insights error: {str(e)}")
        import traceback
        traceback.print_exc()
        return APIResponse.server_error(str(e), e)

# ===== PERFORMANCE (Multi-tenant) =====
@app.route('/api/learning/performance', methods=['GET'])
@AuthDecorator.token_required
def learning_performance():
    """Get user's performance metrics"""
    try:
        user_id = g.user_id
        days = request.args.get('days', 30, type=int)

        db = SessionLocal()
        # Get trades for metrics calculation
        trades = db.query(Trade).filter_by(user_id=user_id).all()
        db.close()

        # Calculate metrics
        metrics = {
            "total_trades": len(trades),
            "profitable_trades": len([t for t in trades if t.pnl > 0 if hasattr(t, 'pnl')]),
            "losing_trades": len([t for t in trades if t.pnl < 0 if hasattr(t, 'pnl')]),
            "win_rate": 0,
            "avg_pnl": 0
        }

        return APIResponse.success(metrics)

    except Exception as e:
        return APIResponse.server_error(str(e), e)

# ===== RECONCILIATION (Admin Only) =====
@app.route('/api/reconciliation/reconcile', methods=['POST'])
@AuthDecorator.token_required
def reconcile_signals():
    """Execute post-market reconciliation (admin only)"""
    try:
        user_id = g.user_id
        db = SessionLocal()
        user = get_user_by_id(db, user_id)
        db.close()

        if not user or not user.is_admin:
            return jsonify({
                "status": "error",
                "message": "Admin access required"
            }), 403

        if not ReconciliationEngine.is_reconciliation_time():
            return jsonify({
                "status": "warning",
                "message": "Reconciliation only runs between 3:45 PM - 4:00 PM IST"
            }), 400

        result = ReconciliationEngine.reconcile_all_pending()
        return jsonify(result), 200

    except Exception as e:
        return APIResponse.server_error(str(e), e)

# ===== PAPER TRADING (NEW) =====
@app.route('/api/trading/create-trade', methods=['POST'])
@AuthDecorator.token_required
@validate_body(CreateTradeSchema)
def create_paper_trade():
    """Create a new paper trade (requires approval)"""
    try:
        from database_v3_1 import create_paper_trade

        data = request.json
        symbol = data.get('symbol', 'NIFTY')
        direction = data.get('direction', 'BUY_CALL')  # BUY_CALL, BUY_PUT, SELL_CALL, SELL_PUT
        entry_price = float(data.get('entry_price', 0))
        target_price = float(data.get('target_price', 0))
        stop_loss = float(data.get('stop_loss', 0))
        quantity = int(data.get('quantity', 1))
        strike_price = float(data.get('strike_price', 0)) if data.get('strike_price') else None

        if not entry_price or not target_price or not stop_loss:
            return jsonify({
                "status": "error",
                "message": "Missing required fields: entry_price, target_price, stop_loss"
            }), 400

        # Create trade in PENDING_APPROVAL status
        trade = create_paper_trade(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            quantity=quantity,
            strike_price=strike_price,
            created_by=g.user_id if hasattr(g, 'user_id') else 'user'
        )

        if not trade:
            return jsonify({
                "status": "error",
                "message": "Failed to create trade"
            }), 500

        return jsonify({
            "status": "success",
            "message": "Trade created - awaiting your approval",
            "trade": trade,
            "timestamp": datetime.utcnow().isoformat()
        }), 201

    except Exception as e:
        logger.info(f"❌ Error creating trade: {str(e)}")
        return APIResponse.server_error(str(e), e)

@app.route('/api/trading/pending-approval', methods=['GET'])
@AuthDecorator.token_required
def get_pending_approval_trades():
    """Get all trades pending user approval"""
    try:
        from database_v3_1 import get_pending_approval_trades

        trades = get_pending_approval_trades(g.user_id)

        return jsonify({
            "status": "success",
            "count": len(trades),
            "trades": trades,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return APIResponse.server_error(str(e), e)

@app.route('/api/trading/approve/<int:trade_id>', methods=['POST'])
@AuthDecorator.token_required
def approve_trade(trade_id):
    """Approve a pending trade (user approval)"""
    try:
        from database_v3_1 import approve_paper_trade

        data = request.json or {}
        reason = data.get('reason', 'User approved')

        trade = approve_paper_trade(trade_id, reason, g.user_id)

        if not trade:
            return jsonify({
                "status": "error",
                "message": f"Trade {trade_id} not found or not pending approval"
            }), 404

        return jsonify({
            "status": "success",
            "message": "Trade approved and opened",
            "trade": trade,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return APIResponse.server_error(str(e), e)

@app.route('/api/trading/reject/<int:trade_id>', methods=['POST'])
@AuthDecorator.token_required
def reject_trade(trade_id):
    """Reject a pending trade"""
    try:
        from database_v3_1 import reject_paper_trade

        data = request.json or {}
        reason = data.get('reason', 'User rejected')

        trade = reject_paper_trade(trade_id, reason, g.user_id)

        if not trade:
            return jsonify({
                "status": "error",
                "message": f"Trade {trade_id} not found or not pending approval"
            }), 404

        return jsonify({
            "status": "success",
            "message": "Trade rejected",
            "trade": trade,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return APIResponse.server_error(str(e), e)

@app.route('/api/trading/open-trades', methods=['GET'])
@AuthDecorator.token_required
def get_open_trades():
    """Get all open paper trades"""
    try:
        from database_v3_1 import get_open_trades

        trades = get_open_trades(g.user_id)

        return jsonify({
            "status": "success",
            "count": len(trades),
            "trades": trades,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return APIResponse.server_error(str(e), e)

@app.route('/api/trading/close/<int:trade_id>', methods=['POST'])
@AuthDecorator.token_required
def close_trade(trade_id):
    """Close an open paper trade"""
    try:
        from database_v3_1 import close_paper_trade

        data = request.json
        exit_price = float(data.get('exit_price', 0))

        if not exit_price:
            return jsonify({
                "status": "error",
                "message": "Missing required field: exit_price"
            }), 400

        trade = close_paper_trade(trade_id, exit_price, g.user_id)

        if not trade:
            return jsonify({
                "status": "error",
                "message": f"Trade {trade_id} not found or not open"
            }), 404

        return jsonify({
            "status": "success",
            "message": "Trade closed",
            "trade": trade,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return APIResponse.server_error(str(e), e)

@app.route('/api/trading/closed-trades', methods=['GET'])
@AuthDecorator.token_required
def get_closed_trades():
    """Get closed paper trades"""
    try:
        from database_v3_1 import get_closed_trades

        limit = request.args.get('limit', 100, type=int)
        trades = get_closed_trades(limit, g.user_id)

        return jsonify({
            "status": "success",
            "count": len(trades),
            "trades": trades,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return APIResponse.server_error(str(e), e)

@app.route('/api/trading/<int:trade_id>', methods=['GET'])
@AuthDecorator.token_required
def get_trade(trade_id):
    """Get a specific paper trade"""
    try:
        from database_v3_1 import get_paper_trade

        trade = get_paper_trade(trade_id, g.user_id)

        if not trade:
            return jsonify({
                "status": "error",
                "message": f"Trade {trade_id} not found"
            }), 404

        return jsonify({
            "status": "success",
            "trade": trade,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return APIResponse.server_error(str(e), e)

@app.route('/api/trading/stats', methods=['GET'])
@AuthDecorator.token_required
def get_trading_stats():
    """Get paper trading statistics"""
    try:
        from database_v3_1 import get_paper_trading_stats

        stats = get_paper_trading_stats(g.user_id)

        return jsonify({
            "status": "success",
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return APIResponse.server_error(str(e), e)

# ===== DASHBOARD OVERVIEW (NEW) =====
@app.route('/api/user/dashboard-overview', methods=['GET'])
@AuthDecorator.token_required
def get_dashboard_overview():
    """Get real dynamic dashboard overview data"""
    try:
        from database_v3_1 import get_paper_trading_stats, get_all_signals, get_metrics

        # Get paper trading stats
        trading_stats = get_paper_trading_stats(g.user_id)

        # Get signal metrics
        signals = get_all_signals(limit=10)
        signal_count = len(signals)

        # Get overall metrics
        metrics = get_metrics()

        # Build overview response with real data
        overview = {
            "account": {
                "total_capital": 100000,
                "used_margin": trading_stats.get("total_pnl", 0),
                "available_margin": 100000 - abs(trading_stats.get("total_pnl", 0)),
                "total_pnl": trading_stats.get("total_pnl", 0),
                "pnl_percent": round((trading_stats.get("total_pnl", 0) / 100000) * 100, 2)
            },
            "trades": {
                "total_trades": trading_stats.get("total_trades", 0),
                "open_trades": trading_stats.get("open_trades", 0),
                "closed_trades": trading_stats.get("closed_trades", 0),
                "pending_approval": trading_stats.get("pending_approval", 0),
                "win_rate": trading_stats.get("win_rate", 0),
                "avg_pnl_per_trade": trading_stats.get("avg_pnl_per_trade", 0)
            },
            "signals": {
                "total_signals": metrics.get("total_signals", 0),
                "nifty_signals": metrics.get("nifty_signals", 0),
                "banknifty_signals": metrics.get("banknifty_signals", 0),
                "pending_signals": len([s for s in signals if s.get("status") == "PENDING"])
            },
            "performance": {
                "total_wins": metrics.get("wins", 0),
                "total_losses": metrics.get("losses", 0),
                "win_rate": metrics.get("win_rate", 0),
                "profit_factor": metrics.get("profit_factor", 0),
                "sharpe_ratio": metrics.get("sharpe_ratio", 0),
                "max_drawdown": metrics.get("max_drawdown", 0)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        return APIResponse.success(overview)

    except Exception as e:
        logger.info(f"❌ Error getting dashboard overview: {str(e)}")
        return APIResponse.server_error(str(e), e)


# ===== QUICK SIGNAL GENERATION (No Auth Required) =====

# Symbol -> (exchange, token) used for live LTP lookups on the quick endpoint.
_QUICK_SIGNAL_TOKENS = {
    "NIFTY": ("NSE", "99926000"),
    "BANKNIFTY": ("NSE", "99926009"),
    "FINNIFTY": ("NSE", "99926037"),
}


def _quick_technical_data(candles):
    """Compute REAL EMA/RSI/MACD from live candles for RealSignalGenerator.

    Returns None when there isn't enough history to compute the core
    indicators. We deliberately never fabricate values — callers fall back to
    a HOLD signal instead of inventing a setup.
    """
    closes = [c.get("close", 0) for c in candles if c.get("close")]
    if len(closes) < 26:  # MACD needs 26 candles; below this nothing is reliable
        return None

    ema_20 = TechnicalEngine.calculate_ema(closes, 20)
    ema_50 = TechnicalEngine.calculate_ema(closes, 50)
    ema_200 = TechnicalEngine.calculate_ema(closes, 200)
    rsi = TechnicalEngine.calculate_rsi(closes, 14)
    macd_data = TechnicalEngine.calculate_macd(closes, 12, 26, 9) or {}

    # Core indicators must be real; if any is missing, don't emit a signal.
    if ema_20 is None or ema_50 is None or rsi is None:
        return None

    # F-13: compute ATR(14) from live candles so the signal generator can size
    # target/stop by real volatility instead of a fixed 2%.
    atr = _compute_atr(candles, 14)

    return {
        "ema_20": ema_20,
        "ema_50": ema_50,
        # ema_200 needs >=200 candles; degrade to ema_50 (NOT a random value)
        # so the trend filter still works on shorter history.
        "ema_200": ema_200 if ema_200 is not None else ema_50,
        "rsi": rsi,
        "macd": macd_data.get("macd", 0),
        "macd_signal": macd_data.get("signal_line", 0),
        "atr": atr,
    }


def _compute_atr(candles, period: int = 14):
    """Average True Range from live OHLC candles. Returns None if insufficient
    data or fields are missing (caller then falls back to a percentage stop)."""
    try:
        if not candles or len(candles) < period + 1:
            return None
        trs = []
        prev_close = None
        for c in candles:
            high = c.get("high")
            low = c.get("low")
            close = c.get("close")
            if high is None or low is None or close is None:
                return None
            high, low, close = float(high), float(low), float(close)
            if prev_close is None:
                tr = high - low
            else:
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
            prev_close = close
        if len(trs) < period:
            return None
        return sum(trs[-period:]) / period
    except Exception:
        return None


def _quick_hold_signal(symbol, reason):
    """Honest placeholder when real market data isn't available (no fabrication)."""
    return {
        "symbol": symbol,
        "direction": "HOLD",
        "signal": "HOLD",
        "entry": None,
        "target": None,
        "stoploss": None,
        "confidence": 0,
        "reason": reason,
        "current_price": None,
        "risk_reward": 0,
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "_live": False,
    }


def _quick_signal_for_symbol(symbol, broker_live):
    """Build one quick signal from REAL technicals, or a HOLD if unavailable."""
    if not broker_live:
        return _quick_hold_signal(symbol, "Awaiting live market data")

    try:
        candles = market.get_historical_candles(symbol, "15", 250)
        technical_data = _quick_technical_data(candles) if candles else None
        if not technical_data:
            return _quick_hold_signal(symbol, "Awaiting sufficient market data")

        # Live price: prefer broker LTP, fall back to the latest candle close.
        exch, token = _QUICK_SIGNAL_TOKENS.get(symbol, ("NSE", ""))
        price = None
        if token:
            try:
                price = market.get_ltp(exch, symbol, token)
            except Exception:
                price = None
        if not price:
            price = candles[-1].get("close")

        sig = RealSignalGenerator.generate_signal(
            symbol, float(price), technical_data, ai_confidence=70
        )

        entry = sig.get("entry_price")
        target = sig.get("target")
        stoploss = sig.get("stop_loss")
        used = sig.get("signals_used") or []
        risk_reward = (
            round(abs(target - entry) / abs(entry - stoploss), 2)
            if entry is not None and stoploss is not None and entry != stoploss
            else 0
        )
        return {
            "symbol": symbol,
            "direction": sig.get("signal", "HOLD"),
            "signal": sig.get("signal", "HOLD"),
            "entry": entry,
            "target": target,
            "stoploss": stoploss,
            "confidence": sig.get("confidence", 0),
            "current_price": sig.get("current_price"),
            "rsi": sig.get("rsi"),
            "rsi_status": sig.get("rsi_status"),
            "reason": ("Technical confluence: " + ", ".join(used)) if used else "Technical analysis",
            "risk_reward": risk_reward,
            "timestamp": sig.get("timestamp"),
            "_live": True,
        }
    except Exception as e:
        logger.warning(f"Quick signal generation failed for {symbol}: {e}")
        return _quick_hold_signal(symbol, "Awaiting sufficient market data")


@app.route('/api/disclaimer', methods=['GET'])
def get_disclaimer():
    """Public trading risk disclaimer (COMPLIANCE GATE). The frontend should
    surface this on signal views and at signup/checkout."""
    return jsonify({
        "status": "success",
        "disclaimer": TRADING_DISCLAIMER,
        "version": DISCLAIMER_VERSION,
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }), 200


@app.route('/api/generate', methods=['POST'])
def generate_quick_signals():
    """
    Generate trading signals from REAL technical analysis of live Angel One
    candle data (EMA / RSI / MACD via TechnicalEngine -> RealSignalGenerator).

    INTEGRITY: this endpoint never fabricates signals. If the broker is not
    connected, or there isn't enough candle history to compute the indicators,
    it returns a HOLD with data_status "delayed" instead of inventing a setup.
    """
    try:
        data = request.get_json() or {}
        requested = data.get('symbols', ['NIFTY', 'BANKNIFTY', 'FINNIFTY'])

        valid_symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY']
        symbols = [s for s in (requested or []) if s in valid_symbols]
        if not symbols:
            symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY']

        broker_live = bool(market and market.is_authenticated())

        signals = []
        any_live = False
        for symbol in symbols:
            sig = _quick_signal_for_symbol(symbol, broker_live)
            if sig.pop("_live", False):
                any_live = True
            signals.append(sig)

        # User-facing status: 'live' only when at least one symbol used real
        # broker data; otherwise 'delayed'. We never expose internal wording.
        public_data_status = "live" if (broker_live and any_live) else "delayed"

        return jsonify({
            "status": "success",
            "message": f"{len(signals)} signals generated",
            "data_status": public_data_status,  # 'live' or 'delayed' (user-facing)
            "signals": signals,
            "disclaimer": TRADING_DISCLAIMER,  # COMPLIANCE GATE
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 200

    except Exception as e:
        # Log full detail server-side; return a clean, generic message to the client.
        logger.error(f"Signal generation error: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Unable to generate signals right now. Please try again shortly."
        }), 500


# ===== STATIC FILE SERVING =====
@app.route('/dashboard_live_v3.1.html', methods=['GET'])
def serve_dashboard_html():
    """Serve dashboard_live_v3.1.html directly"""
    html_content = get_html_file('dashboard_live_v3.1.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return jsonify({
        "status": "error",
        "message": "Dashboard not found"
    }), 404


@app.route('/', methods=['GET'])
def serve_root():
    """Serve dashboard at root path"""
    html_content = get_html_file('dashboard_live_v3.1.html')
    if html_content:
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return jsonify({
        "status": "error",
        "message": "Dashboard not found"
    }), 404


# ===== ERROR HANDLERS =====
# AUDIT FIX #12: the inline 404/500/401 handlers that used to live here were
# registered AFTER register_error_handlers(app) ran, so they silently
# OVERRODE the standardized handlers in error_handler.py — returning a
# divergent {status, message[, path]} shape (and leaking request.path on 404)
# instead of the canonical error envelope. They are removed so the
# standardized, consistent handlers (NOT_FOUND / INTERNAL_ERROR / UNAUTHORIZED)
# from error_handler.py take effect for every endpoint.

# ===== RATE-LIMIT EXEMPTIONS (Tier 2 #6) =====
# Applied here (end of module) so every health/metrics route is already
# defined. Uptime probes, metrics scrapers and deep-health checks must never
# be throttled by the default limits.
for _ep in ("health_check", "health", "health_detailed", "metrics", "health_deep"):
    _vf = app.view_functions.get(_ep)
    if _vf is not None:
        limiter.exempt(_vf)
logger.info("✅ Monitoring endpoints exempted from rate limits (Tier 2 #6)")

# ===== STARTUP =====
if __name__ == '__main__':
    separator = "=" * 70
    logger.info(f"\n{separator}")
    logger.info("🚀 TRADOSPHERE SAAS V3 - Multi-Tenant Trading Platform")
    logger.info(separator)
    logger.info("\n✨ PHASE 1: Authentication & Multi-Tenancy")
    logger.info("   ✅ User signup/login with JWT")
    logger.info("   ✅ Multi-tenant data isolation")
    logger.info("   ✅ API key management")
    logger.info("   ✅ User profile & settings")
    logger.info("   ✅ Session management")
    logger.info("\n✨ PHASE 2: Pro SaaS Features")
    logger.info("   ✅ Subscription tiers (paid plans COMING SOON — no payments)")
    logger.info("   ✅ Email notifications (SendGrid/SMTP)")
    logger.info("   ✅ Multi-broker support framework")
    logger.info("   ✅ Usage analytics & tracking")
    logger.info("   ✅ Admin panel for user management")
    logger.info("   ✅ Billing history & invoices")
    logger.info("\n📊 CORE FEATURES:")
    logger.info("   ✓ Live market data (Angel One)")
    logger.info("   ✓ Technical analysis & indicators")
    logger.info("   ✓ Options intelligence & Greeks")
    logger.info("   ✓ Signal generation & alerts")
    logger.info("   ✓ Performance analytics")
    logger.info("\n📍 KEY ENDPOINTS:")
    logger.info("   Auth:        /api/auth/signup, /api/auth/login, /api/auth/logout")
    logger.info("   User:        /api/user/profile, /api/user/api-keys, /api/user/preferences")
    logger.info("   Billing:     /api/billing/plans, /api/billing/subscription, /api/billing/usage")
    logger.info("   Admin:       /api/admin/users, /api/admin/analytics, /api/admin/health")
    logger.info("   Trading:     /api/market/live, /api/analysis/technical, /api/signals")
    port = int(os.getenv('PORT', 5000))
    logger.info(f"\n🌐 Access at: http://localhost:{port}")
    logger.info(f"   Login: http://localhost:{port}/login")
    logger.info(f"   Dashboard: http://localhost:{port}/dashboard (requires auth)")
    logger.info(separator + "\n")

    # AUDIT FIX #10: consolidated the previously-duplicated __main__ block and
    # switched the dev server from app.run() to socketio.run() so WebSocket
    # support (Tier 2 #8) actually works when running locally. In production
    # gunicorn imports `app` and neither block runs, so this is dev-only.
    socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False,
                 allow_unsafe_werkzeug=True)
