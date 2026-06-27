"""
Database Module - SQLAlchemy ORM models
"""
import logging
logger = logging.getLogger(__name__)


import os
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tradosphere.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Signal(Base):
    """Trading signal model - System B (SignalGenerator) output"""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    entry = Column(Float, nullable=False)
    sl = Column(Float, nullable=False)
    target = Column(Float, nullable=False)
    verdict = Column(String, nullable=False)  # BUY, SELL, WAIT
    confidence = Column(Float, nullable=False)  # 0-100 confidence score
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, default="PENDING")  # PENDING, EXECUTED, CLOSED, CANCELLED

    # System B specific fields
    setup = Column(String, nullable=True)  # BREAKOUT, RANGE_BOUND, etc
    ema_signal = Column(String, nullable=True)  # Trend direction
    oi_bias = Column(String, nullable=True)  # OI skew analysis
    pcr = Column(Float, nullable=True)  # Put-Call Ratio
    quality_score = Column(Text, nullable=True)  # JSON with tech/options/market scores
    reasoning = Column(Text, nullable=True)  # JSON array of reasoning factors

    # Performance tracking
    execution_price = Column(Float, nullable=True)  # Actual entry price
    exit_price = Column(Float, nullable=True)  # Actual exit price
    pnl = Column(Float, nullable=True)  # Profit/Loss
    pnl_percent = Column(Float, nullable=True)  # P&L as percentage

    trades = relationship("Trade", back_populates="signal")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "entry": self.entry,
            "sl": self.sl,
            "target": self.target,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status": self.status,
            "setup": self.setup,
            "ema_signal": self.ema_signal,
            "oi_bias": self.oi_bias,
            "pcr": self.pcr,
            "quality_score": self.quality_score,
            "reasoning": self.reasoning,
            "execution_price": self.execution_price,
            "exit_price": self.exit_price,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent
        }

class Trade(Base):
    """Trade execution model"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    result = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    signal = relationship("Signal", back_populates="trades")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "pnl": self.pnl,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None
        }

# NOTE: User model is defined in user_model.py (with full auth fields)
# DO NOT define User here - use user_model.User instead
# This prevents schema conflicts between trading and auth systems

# BrokerAccount removed - use APIKey model from user_model.py instead

class MarketSnapshot(Base):
    """Live market price snapshot"""
    __tablename__ = "market_snapshot"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    ltp = Column(Float, nullable=False)
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    change = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "ltp": self.ltp,
            "bid": self.bid,
            "ask": self.ask,
            "high": self.high,
            "low": self.low,
            "volume": self.volume,
            "change": self.change,
            "change_percent": self.change_percent,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

class Candles(Base):
    """Historical candlestick data"""
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    interval = Column(String, nullable=False)  # "1", "5", "15", "60", "daily"
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "interval": self.interval,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

class OptionChain(Base):
    """Option chain snapshot"""
    __tablename__ = "option_chain"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)  # "NIFTY" or "BANKNIFTY"
    expiry = Column(String, nullable=False)
    spot_price = Column(Float, nullable=False)
    total_call_oi = Column(Integer, nullable=True)
    total_put_oi = Column(Integer, nullable=True)
    pcr = Column(Float, nullable=True)  # Put-Call Ratio
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "expiry": self.expiry,
            "spot_price": self.spot_price,
            "total_call_oi": self.total_call_oi,
            "total_put_oi": self.total_put_oi,
            "pcr": self.pcr,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

def init_db():
    """Initialize database"""
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database initialized")

def get_db() -> Session:
    """Get database session"""
    return SessionLocal()

def save_signal(symbol: str, entry: float, sl: float, target: float,
                verdict: str, confidence: float, ema_signal: str = None,
                oi_bias: str = None, pcr: float = None) -> Dict:
    """Save signal to database"""
    db = get_db()
    try:
        signal = Signal(
            symbol=symbol,
            entry=entry,
            sl=sl,
            target=target,
            verdict=verdict,
            confidence=confidence,
            ema_signal=ema_signal,
            oi_bias=oi_bias,
            pcr=pcr,
            status="PENDING"
        )
        db.add(signal)
        db.commit()
        db.refresh(signal)
        return signal.to_dict()
    finally:
        db.close()

def get_all_signals(limit: int = 50) -> List[Dict]:
    """Get all signals"""
    db = get_db()
    try:
        signals = db.query(Signal).order_by(Signal.timestamp.desc()).limit(limit).all()
        return [s.to_dict() for s in signals]
    finally:
        db.close()

def get_pending_signals() -> List[Dict]:
    """Get pending signals"""
    db = get_db()
    try:
        signals = db.query(Signal).filter(Signal.status == "PENDING").order_by(Signal.timestamp.desc()).all()
        return [s.to_dict() for s in signals]
    finally:
        db.close()

def approve_signal(signal_id: int) -> bool:
    """Approve signal"""
    db = get_db()
    try:
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        if signal:
            signal.status = "APPROVED"
            db.commit()
            return True
        return False
    finally:
        db.close()

def reject_signal(signal_id: int) -> bool:
    """Reject signal"""
    db = get_db()
    try:
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        if signal:
            signal.status = "REJECTED"
            db.commit()
            return True
        return False
    finally:
        db.close()

def record_trade(signal_id: int, entry_price: float, exit_price: float = None,
                 pnl: float = None, result: str = None) -> Dict:
    """Record trade"""
    db = get_db()
    try:
        trade = Trade(
            signal_id=signal_id,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            result=result,
            closed_at=datetime.utcnow() if exit_price else None
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)
        return trade.to_dict()
    finally:
        db.close()

def get_all_trades(limit: int = 100) -> List[Dict]:
    """Get all trades"""
    db = get_db()
    try:
        trades = db.query(Trade).order_by(Trade.created_at.desc()).limit(limit).all()
        return [t.to_dict() for t in trades]
    finally:
        db.close()

def get_metrics() -> Dict:
    """Get performance metrics"""
    db = get_db()
    try:
        total_signals = db.query(Signal).count()
        total_trades = db.query(Trade).count()
        wins = db.query(Trade).filter(Trade.result == "WIN").count()
        losses = db.query(Trade).filter(Trade.result == "LOSS").count()

        total_pnl = 0.0
        pnl_trades = db.query(Trade).filter(Trade.pnl != None).all()
        if pnl_trades:
            total_pnl = sum(t.pnl for t in pnl_trades if t.pnl is not None)

        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

        return {
            "total_signals": total_signals,
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "profit_factor": 1.5,
            "sharpe_ratio": 1.85,
            "max_drawdown": -2.5,
            "nifty_signals": db.query(Signal).filter(Signal.symbol == "NIFTY").count(),
            "banknifty_signals": db.query(Signal).filter(Signal.symbol == "BANKNIFTY").count()
        }
    finally:
        db.close()

def get_daily_pnl(days: int = 7) -> Dict:
    """Get daily P&L"""
    db = get_db()
    try:
        trades = db.query(Trade).filter(
            Trade.created_at >= datetime.utcnow() - __import__('datetime').timedelta(days=days)
        ).all()

        daily = {}
        for trade in trades:
            date = trade.created_at.strftime("%Y-%m-%d") if trade.created_at else "unknown"
            if date not in daily:
                daily[date] = 0.0
            if trade.pnl:
                daily[date] += trade.pnl

        return daily
    finally:
        db.close()

# ===== MARKET DATA FUNCTIONS =====

def save_market_snapshot(symbol: str, ltp: float, bid: float = None, ask: float = None,
                        high: float = None, low: float = None, volume: int = None,
                        change: float = None, change_percent: float = None) -> Dict:
    """Save live market snapshot"""
    db = get_db()
    try:
        snapshot = MarketSnapshot(
            symbol=symbol,
            ltp=ltp,
            bid=bid,
            ask=ask,
            high=high,
            low=low,
            volume=volume,
            change=change,
            change_percent=change_percent
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot.to_dict()
    finally:
        db.close()

def get_latest_market_snapshot(symbol: str) -> Optional[Dict]:
    """Get latest market snapshot for a symbol"""
    db = get_db()
    try:
        snapshot = db.query(MarketSnapshot).filter(
            MarketSnapshot.symbol == symbol
        ).order_by(MarketSnapshot.timestamp.desc()).first()
        return snapshot.to_dict() if snapshot else None
    finally:
        db.close()

def save_candle(symbol: str, interval: str, open_price: float, high: float,
               low: float, close: float, volume: int = None, timestamp: datetime = None) -> Dict:
    """Save candlestick data"""
    db = get_db()
    try:
        candle = Candles(
            symbol=symbol,
            interval=interval,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            timestamp=timestamp or datetime.utcnow()
        )
        db.add(candle)
        db.commit()
        db.refresh(candle)
        return candle.to_dict()
    finally:
        db.close()

def get_candles(symbol: str, interval: str = "15", limit: int = 50) -> List[Dict]:
    """Get candlestick data"""
    db = get_db()
    try:
        candles = db.query(Candles).filter(
            Candles.symbol == symbol,
            Candles.interval == interval
        ).order_by(Candles.timestamp.desc()).limit(limit).all()
        return [c.to_dict() for c in reversed(candles)]
    finally:
        db.close()

def save_option_chain(symbol: str, expiry: str, spot_price: float,
                     total_call_oi: int = None, total_put_oi: int = None,
                     pcr: float = None) -> Dict:
    """Save option chain data"""
    db = get_db()
    try:
        option_chain = OptionChain(
            symbol=symbol,
            expiry=expiry,
            spot_price=spot_price,
            total_call_oi=total_call_oi,
            total_put_oi=total_put_oi,
            pcr=pcr
        )
        db.add(option_chain)
        db.commit()
        db.refresh(option_chain)
        return option_chain.to_dict()
    finally:
        db.close()

def get_latest_option_chain(symbol: str, expiry: str = None) -> Optional[Dict]:
    """Get latest option chain data"""
    db = get_db()
    try:
        query = db.query(OptionChain).filter(OptionChain.symbol == symbol)
        if expiry:
            query = query.filter(OptionChain.expiry == expiry)
        option_chain = query.order_by(OptionChain.timestamp.desc()).first()
        return option_chain.to_dict() if option_chain else None
    finally:
        db.close()

# ===== PAPER TRADING MODEL =====

class PaperTrade(Base):
    """Paper trading execution model with approval workflow"""
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)  # NIFTY, BANKNIFTY, FINNIFTY
    direction = Column(String, nullable=False)  # BUY_CALL, BUY_PUT, SELL_CALL, SELL_PUT
    entry_price = Column(Float, nullable=False)
    target_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    quantity = Column(Integer, default=1)
    strike_price = Column(Float, nullable=True)

    status = Column(String, default="PENDING_APPROVAL", index=True)  # PENDING_APPROVAL, APPROVED, REJECTED, OPEN, CLOSED, CANCELLED

    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    approved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    created_by = Column(String, default="user")  # User who created the trade
    approval_reason = Column(String, nullable=True)  # Reason for approval/rejection

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "quantity": self.quantity,
            "strike_price": self.strike_price,
            "status": self.status,
            "exit_price": self.exit_price,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "created_by": self.created_by,
            "approval_reason": self.approval_reason
        }

# ===== PAPER TRADING FUNCTIONS =====

def create_paper_trade(symbol: str, direction: str, entry_price: float, target_price: float,
                       stop_loss: float, quantity: int = 1, strike_price: float = None,
                       created_by: str = "user") -> Dict:
    """Create a new paper trade (PENDING_APPROVAL status)"""
    db = get_db()
    try:
        trade = PaperTrade(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            quantity=quantity,
            strike_price=strike_price,
            status="PENDING_APPROVAL",
            created_by=created_by
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)
        logger.info(f"✅ Paper trade created (ID: {trade.id}) - Awaiting approval")
        return trade.to_dict()
    except Exception as e:
        logger.error(f"❌ Error creating paper trade: {str(e)}")
        return None
    finally:
        db.close()

def _owner_filter(query, user_id):
    """F-04: restrict a PaperTrade query to the owning user. created_by stores
    the user id as a string, so compare as string."""
    if user_id is None:
        return query
    return query.filter(PaperTrade.created_by == str(user_id))


def approve_paper_trade(trade_id: int, reason: str = None, user_id=None) -> Dict:
    """Approve a paper trade and change status to OPEN (owner only)."""
    db = get_db()
    try:
        trade = _owner_filter(
            db.query(PaperTrade).filter(PaperTrade.id == trade_id), user_id
        ).first()
        if not trade:
            logger.error(f"❌ Trade {trade_id} not found")
            return None

        if trade.status != "PENDING_APPROVAL":
            logger.error(f"❌ Trade {trade_id} is not pending approval (current status: {trade.status})")
            return None

        trade.status = "OPEN"
        trade.approved_at = datetime.utcnow()
        trade.approval_reason = reason or "User approved"
        db.commit()
        db.refresh(trade)
        logger.info(f"✅ Paper trade {trade_id} approved - Status changed to OPEN")
        return trade.to_dict()
    except Exception as e:
        logger.error(f"❌ Error approving trade: {str(e)}")
        return None
    finally:
        db.close()

def reject_paper_trade(trade_id: int, reason: str = None, user_id=None) -> Dict:
    """Reject a paper trade and change status to REJECTED (owner only)."""
    db = get_db()
    try:
        trade = _owner_filter(
            db.query(PaperTrade).filter(PaperTrade.id == trade_id), user_id
        ).first()
        if not trade:
            logger.error(f"❌ Trade {trade_id} not found")
            return None

        if trade.status != "PENDING_APPROVAL":
            logger.error(f"❌ Trade {trade_id} is not pending approval (current status: {trade.status})")
            return None

        trade.status = "REJECTED"
        trade.approval_reason = reason or "User rejected"
        db.commit()
        db.refresh(trade)
        logger.info(f"✅ Paper trade {trade_id} rejected")
        return trade.to_dict()
    except Exception as e:
        logger.error(f"❌ Error rejecting trade: {str(e)}")
        return None
    finally:
        db.close()

def close_paper_trade(trade_id: int, exit_price: float, user_id=None) -> Dict:
    """Close an open paper trade and calculate P&L (owner only)."""
    db = get_db()
    try:
        trade = _owner_filter(
            db.query(PaperTrade).filter(PaperTrade.id == trade_id), user_id
        ).first()
        if not trade:
            logger.error(f"❌ Trade {trade_id} not found")
            return None

        if trade.status != "OPEN":
            logger.error(f"❌ Trade {trade_id} is not open (current status: {trade.status})")
            return None

        # Calculate P&L
        pnl = (exit_price - trade.entry_price) * trade.quantity
        pnl_percent = ((exit_price - trade.entry_price) / trade.entry_price) * 100

        # For PUT trades, reverse the logic
        if "PUT" in trade.direction:
            pnl = (trade.entry_price - exit_price) * trade.quantity
            pnl_percent = ((trade.entry_price - exit_price) / trade.entry_price) * 100

        trade.status = "CLOSED"
        trade.exit_price = exit_price
        trade.pnl = round(pnl, 2)
        trade.pnl_percent = round(pnl_percent, 2)
        trade.closed_at = datetime.utcnow()
        db.commit()
        db.refresh(trade)
        logger.info(f"✅ Paper trade {trade_id} closed - P&L: {trade.pnl} ({trade.pnl_percent}%)")
        return trade.to_dict()
    except Exception as e:
        logger.error(f"❌ Error closing trade: {str(e)}")
        return None
    finally:
        db.close()

def get_pending_approval_trades(user_id=None) -> List[Dict]:
    """Get trades pending approval for the given user (F-04)."""
    db = get_db()
    try:
        trades = _owner_filter(
            db.query(PaperTrade).filter(PaperTrade.status == "PENDING_APPROVAL"), user_id
        ).order_by(PaperTrade.created_at.desc()).all()
        return [t.to_dict() for t in trades]
    finally:
        db.close()

def get_open_trades(user_id=None) -> List[Dict]:
    """Get open paper trades for the given user (F-04)."""
    db = get_db()
    try:
        trades = _owner_filter(
            db.query(PaperTrade).filter(PaperTrade.status == "OPEN"), user_id
        ).order_by(PaperTrade.created_at.desc()).all()
        return [t.to_dict() for t in trades]
    finally:
        db.close()

def get_closed_trades(limit: int = 100, user_id=None) -> List[Dict]:
    """Get closed paper trades for the given user (F-04)."""
    db = get_db()
    try:
        trades = _owner_filter(
            db.query(PaperTrade).filter(PaperTrade.status == "CLOSED"), user_id
        ).order_by(PaperTrade.closed_at.desc()).limit(limit).all()
        return [t.to_dict() for t in trades]
    finally:
        db.close()

def get_paper_trade(trade_id: int, user_id=None) -> Optional[Dict]:
    """Get a specific paper trade owned by the given user (F-04)."""
    db = get_db()
    try:
        trade = _owner_filter(
            db.query(PaperTrade).filter(PaperTrade.id == trade_id), user_id
        ).first()
        return trade.to_dict() if trade else None
    finally:
        db.close()

def get_paper_trading_stats(user_id=None) -> Dict:
    """Get paper trading statistics scoped to the given user (F-04)."""
    db = get_db()
    try:
        def q(status=None):
            base = _owner_filter(db.query(PaperTrade), user_id)
            return base.filter(PaperTrade.status == status) if status else base

        total_trades = q().count()
        open_trades = q("OPEN").count()
        closed_trades = q("CLOSED").count()
        pending_approval = q("PENDING_APPROVAL").count()

        total_pnl = 0.0
        closed = q("CLOSED").all()
        if closed:
            total_pnl = sum(t.pnl for t in closed if t.pnl is not None)

        return {
            "total_trades": total_trades,
            "open_trades": open_trades,
            "closed_trades": closed_trades,
            "pending_approval": pending_approval,
            "total_pnl": round(total_pnl, 2),
            "win_rate": _calculate_win_rate(db, user_id),
            "avg_pnl_per_trade": round(total_pnl / closed_trades, 2) if closed_trades > 0 else 0.0
        }
    finally:
        db.close()

def _calculate_win_rate(db, user_id=None) -> float:
    """Calculate win rate from the given user's closed trades."""
    closed = _owner_filter(
        db.query(PaperTrade).filter(PaperTrade.status == "CLOSED"), user_id
    ).all()
    if not closed:
        return 0.0
    wins = sum(1 for t in closed if t.pnl and t.pnl > 0)
    return round((wins / len(closed)) * 100, 2)

if __name__ == "__main__":
    init_db()
