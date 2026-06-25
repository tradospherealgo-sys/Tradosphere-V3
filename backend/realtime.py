"""
Real-time WebSocket Support (Tier 2 #8)

Socket.IO server running in `threading` async mode — deliberately chosen over
eventlet/gevent so there is NO monkey-patching that could conflict with
apscheduler (token-refresh scheduler) or SmartAPI's own websocket client.

Channels (Socket.IO rooms):
  - "prices"  : live index price ticks   (event: "price_update")
  - "signals" : new trading-signal pushes (event: "signal_update")

Client flow:
  socket.emit("subscribe",   { channel: "prices"  })
  socket.on("price_update",  data => ...)
  socket.emit("unsubscribe", { channel: "prices"  })
"""

import logging
from datetime import datetime

from flask_socketio import SocketIO, emit, join_room, leave_room

logger = logging.getLogger(__name__)

# Mirror the REST CORS allow-list for the socket handshake.
_WS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5000",
    "http://localhost:5001",
    "https://tradosphere.vercel.app",
    "https://www.tradosphere.vercel.app",
    "https://tradosphere.in",
    "https://www.tradosphere.in",
    "https://tradosphere-v3.onrender.com",
]

VALID_ROOMS = {"prices", "signals"}

# Single global Socket.IO instance, bound to the app in init_socketio().
socketio = SocketIO(
    cors_allowed_origins=_WS_ORIGINS,
    async_mode="threading",
    logger=False,
    engineio_logger=False,
    ping_timeout=20,
    ping_interval=25,
)

_broadcaster_started = False


def init_socketio(app):
    """Bind Socket.IO to the Flask app and register event handlers."""
    socketio.init_app(app)

    @socketio.on("connect")
    def _on_connect():
        logger.info("🔌 WS client connected")
        emit("connected", {"status": "ok", "ts": datetime.utcnow().isoformat()})

    @socketio.on("disconnect")
    def _on_disconnect():
        logger.info("🔌 WS client disconnected")

    @socketio.on("subscribe")
    def _on_subscribe(data):
        channel = (data or {}).get("channel")
        if channel in VALID_ROOMS:
            join_room(channel)
            emit("subscribed", {"channel": channel})
            logger.debug(f"WS client subscribed to '{channel}'")
        else:
            emit("error", {"message": f"unknown channel: {channel}"})

    @socketio.on("unsubscribe")
    def _on_unsubscribe(data):
        channel = (data or {}).get("channel")
        if channel in VALID_ROOMS:
            leave_room(channel)
            emit("unsubscribed", {"channel": channel})

    logger.info("✅ Socket.IO initialized (Tier 2 #8)")
    return socketio


# ─────────────────────────────────────────────────────────────────────
# Emit helpers — safe to call from anywhere in the app.
# ─────────────────────────────────────────────────────────────────────
def emit_price_update(prices: dict):
    """Broadcast a price tick to everyone subscribed to the 'prices' room."""
    socketio.emit(
        "price_update",
        {"prices": prices, "ts": datetime.utcnow().isoformat()},
        room="prices",
    )


def emit_signal_update(signal: dict):
    """Broadcast a new signal to everyone subscribed to the 'signals' room."""
    socketio.emit(
        "signal_update",
        {"signal": signal, "ts": datetime.utcnow().isoformat()},
        room="signals",
    )


def start_price_broadcaster(get_prices, interval_seconds: int = 5):
    """Start a background task that emits price ticks on an interval.

    Opt-in (the main server gates this behind an env var) so importing the
    app for tests never spawns a perpetual background thread.

    `get_prices` must be a zero-arg callable returning a dict of prices.
    """
    global _broadcaster_started
    if _broadcaster_started:
        return
    _broadcaster_started = True

    def _loop():
        logger.info(f"📡 Price broadcaster running every {interval_seconds}s")
        while True:
            try:
                prices = get_prices()
                if prices:
                    emit_price_update(prices)
            except Exception as exc:
                logger.debug(f"price broadcaster tick skipped: {exc}")
            socketio.sleep(interval_seconds)

    socketio.start_background_task(_loop)
