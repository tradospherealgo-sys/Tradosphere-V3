#!/usr/bin/env python3
"""Seed database with sample signals for testing"""

from database import Signal, SessionLocal, Base, engine
from datetime import datetime

# Ensure tables exist
Base.metadata.create_all(engine)

db = SessionLocal()

# Delete existing signals
db.query(Signal).delete()
db.commit()

# Create sample signals
signals = [
    Signal(
        symbol='NIFTY',
        entry=23500,
        sl=23000,
        target=24500,
        verdict='BUY',
        confidence=85,
        timestamp=datetime.utcnow(),
        status='PENDING',
        setup='BREAKOUT',
        ema_signal='BULLISH',
        pcr=0.95
    ),
    Signal(
        symbol='BANKNIFTY',
        entry=48000,
        sl=47000,
        target=49500,
        verdict='BUY',
        confidence=80,
        timestamp=datetime.utcnow(),
        status='PENDING',
        setup='RANGE_BOUND',
        ema_signal='BULLISH',
        pcr=1.05
    ),
    Signal(
        symbol='SENSEX',
        entry=73000,
        sl=71500,
        target=75000,
        verdict='SELL',
        confidence=75,
        timestamp=datetime.utcnow(),
        status='PENDING',
        setup='BREAKDOWN',
        ema_signal='BEARISH',
        pcr=0.85
    ),
]

db.add_all(signals)
db.commit()
print(f"✅ Seeded {len(signals)} signals")
db.close()
