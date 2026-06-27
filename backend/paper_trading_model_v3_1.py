"""
Paper Trading System - Virtual trading for testing signals and strategies
Track trades, P&L, accuracy, and performance metrics
"""
import logging
logger = logging.getLogger(__name__)


from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///tradosphere_saas.db')
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PaperAccount(Base):
    """Paper trading account per user per symbol"""
    __tablename__ = "paper_accounts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)  # Links to users.id
    symbol = Column(String, index=True)  # NIFTY, BANKNIFTY, etc.
    initial_capital = Column(Float, default=100000)
    current_balance = Column(Float, default=100000)
    invested_amount = Column(Float, default=0)
    total_pnl = Column(Float, default=0)
    pnl_percentage = Column(Float, default=0)

    # Trading stats
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0)
    avg_win = Column(Float, default=0)
    avg_loss = Column(Float, default=0)
    profit_factor = Column(Float, default=0)
    max_drawdown = Column(Float, default=0)

    # Relationships
    trades = relationship("PaperTrade", back_populates="account", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "initial_capital": self.initial_capital,
            "current_balance": self.current_balance,
            "total_pnl": self.total_pnl,
            "pnl_percentage": self.pnl_percentage,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor,
            "max_drawdown": self.max_drawdown
        }


class PaperTrade(Base):
    """Individual paper trades for backtesting"""
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('paper_accounts.id'), index=True)
    symbol = Column(String, index=True)

    # Trade details
    trade_type = Column(String)  # BUY, SELL, CALL, PUT
    signal_type = Column(String)  # TECHNICAL, OPTIONS, MOMENTUM

    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Integer)

    # Position management
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)

    # P&L
    pnl = Column(Float, default=0)
    pnl_percentage = Column(Float, default=0)

    # Status
    status = Column(String, default="open")  # open, closed, stopped_out

    # Timing
    entry_time = Column(DateTime, index=True)
    exit_time = Column(DateTime, nullable=True)
    holding_period = Column(Integer, default=0)  # minutes

    # Signal info
    signal_description = Column(Text, nullable=True)
    accuracy = Column(Float, default=0)  # 0-1 score

    # Relationship back to account
    account = relationship("PaperAccount", back_populates="trades")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "symbol": self.symbol,
            "trade_type": self.trade_type,
            "signal_type": self.signal_type,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "pnl": self.pnl,
            "pnl_percentage": self.pnl_percentage,
            "status": self.status,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "accuracy": self.accuracy
        }


class SignalTracking(Base):
    """Track signal accuracy and performance"""
    __tablename__ = "signal_tracking"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    symbol = Column(String, index=True)

    # Signal details
    signal_type = Column(String)  # TECHNICAL, OPTIONS, MOMENTUM
    direction = Column(String)  # BUY, SELL, CALL, PUT

    entry_price = Column(Float)
    target_price = Column(Float)
    stop_loss = Column(Float)

    # Actual outcome
    outcome_price = Column(Float, nullable=True)
    is_winning = Column(Boolean, nullable=True)
    accuracy_score = Column(Float, default=0)  # How close to target

    # Timing
    generated_at = Column(DateTime, index=True)
    triggered_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # Lifecycle status of the generated signal:
    #   generated -> user has not acted yet
    #   accepted  -> user approved; a PAPER trade was opened (never a live order)
    #   rejected  -> user declined; recorded for accuracy analysis, no trade
    #   closed    -> outcome recorded
    status = Column(String, default="generated")

    # Metadata
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "direction": self.direction,
            "status": self.status,
            "entry_price": self.entry_price,
            "target_price": self.target_price,
            "is_winning": self.is_winning,
            "accuracy_score": self.accuracy_score,
            "status": self.status,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None
        }


# ===== DATABASE FUNCTIONS =====
def init_paper_trading_db():
    """Initialize paper trading tables"""
    Base.metadata.create_all(bind=engine)


def get_or_create_account(db, user_id: int, symbol: str, initial_capital: float = 100000):
    """Get existing or create new paper account"""
    account = db.query(PaperAccount).filter(
        PaperAccount.user_id == user_id,
        PaperAccount.symbol == symbol
    ).first()

    if not account:
        account = PaperAccount(
            user_id=user_id,
            symbol=symbol,
            initial_capital=initial_capital,
            current_balance=initial_capital
        )
        db.add(account)
        db.commit()
        db.refresh(account)

    return account


def open_trade(db, account_id: int, symbol: str, trade_type: str, signal_type: str,
               entry_price: float, quantity: int, stop_loss: float = None,
               take_profit: float = None, signal_desc: str = None):
    """Open a new paper trade"""
    trade = PaperTrade(
        account_id=account_id,
        symbol=symbol,
        trade_type=trade_type,
        signal_type=signal_type,
        entry_price=entry_price,
        quantity=quantity,
        stop_loss=stop_loss,
        take_profit=take_profit,
        signal_description=signal_desc,
        entry_time=datetime.utcnow(),
        status="open"
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)

    # Update account invested amount
    account = db.query(PaperAccount).filter(PaperAccount.id == account_id).first()
    if account:
        account.invested_amount += (entry_price * quantity)
        account.current_balance -= (entry_price * quantity)
        db.commit()

    return trade


def close_trade(db, trade_id: int, exit_price: float):
    """Close a paper trade and calculate P&L"""
    trade = db.query(PaperTrade).filter(PaperTrade.id == trade_id).first()
    if not trade:
        return None

    trade.exit_price = exit_price
    trade.exit_time = datetime.utcnow()
    trade.status = "closed"

    # Calculate P&L
    if trade.trade_type in ["BUY", "CALL"]:
        pnl = (exit_price - trade.entry_price) * trade.quantity
    else:  # SELL, PUT
        pnl = (trade.entry_price - exit_price) * trade.quantity

    trade.pnl = pnl
    trade.pnl_percentage = ((exit_price - trade.entry_price) / trade.entry_price) * 100

    # Update account
    account = db.query(PaperAccount).filter(PaperAccount.id == trade.account_id).first()
    if account:
        account.current_balance += (exit_price * trade.quantity)
        account.invested_amount -= (trade.entry_price * trade.quantity)
        account.total_pnl += pnl
        account.total_trades += 1

        if pnl > 0:
            account.winning_trades += 1
        else:
            account.losing_trades += 1

        # Calculate metrics
        if account.total_trades > 0:
            account.win_rate = (account.winning_trades / account.total_trades) * 100
            account.pnl_percentage = (account.total_pnl / account.initial_capital) * 100

        db.commit()

    db.commit()
    db.refresh(trade)
    return trade


def get_account_trades(db, account_id: int, limit: int = 50):
    """Get trades for an account"""
    return db.query(PaperTrade).filter(
        PaperTrade.account_id == account_id
    ).order_by(PaperTrade.entry_time.desc()).limit(limit).all()


def get_account_performance(db, account_id: int):
    """Get performance metrics for account"""
    account = db.query(PaperAccount).filter(PaperAccount.id == account_id).first()
    if account:
        return account.to_dict()
    return None


def track_signal(db, user_id: int, symbol: str, signal_type: str, direction: str,
                 entry_price: float, target_price: float, stop_loss: float, desc: str = None):
    """Track a signal for accuracy monitoring"""
    signal = SignalTracking(
        user_id=user_id,
        symbol=symbol,
        signal_type=signal_type,
        direction=direction,
        entry_price=entry_price,
        target_price=target_price,
        stop_loss=stop_loss,
        description=desc,
        generated_at=datetime.utcnow()
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def reject_signal(db, signal_id: int, user_id: int, reason: str = None):
    """Record that the user declined a generated signal.

    No order (live OR paper) is created — the signal is simply marked
    'rejected' so it still counts toward accuracy/analytics. Scoped to the
    owning user so one tenant can never reject another's signal.
    """
    signal = db.query(SignalTracking).filter(
        SignalTracking.id == signal_id,
        SignalTracking.user_id == user_id
    ).first()
    if not signal:
        return None

    signal.status = "rejected"
    signal.closed_at = datetime.utcnow()
    if reason:
        existing = signal.description or ""
        signal.description = (existing + f" | rejected: {reason}").strip(" |")
    db.commit()
    db.refresh(signal)
    return signal


def accept_signal(db, signal_id: int, user_id: int):
    """Mark a generated signal as accepted (a paper trade is opened separately).

    Scoped to the owning user. This never places a live broker order — the
    platform is paper-trading only.
    """
    signal = db.query(SignalTracking).filter(
        SignalTracking.id == signal_id,
        SignalTracking.user_id == user_id
    ).first()
    if not signal:
        return None
    signal.status = "accepted"
    signal.triggered_at = datetime.utcnow()
    db.commit()
    db.refresh(signal)
    return signal


def close_signal(db, signal_id: int, outcome_price: float):
    """Close signal tracking and calculate accuracy"""
    signal = db.query(SignalTracking).filter(SignalTracking.id == signal_id).first()
    if not signal:
        return None
    signal.status = "closed"

    signal.outcome_price = outcome_price
    signal.closed_at = datetime.utcnow()

    # Determine if signal was winning
    if signal.direction in ["BUY", "CALL"]:
        signal.is_winning = outcome_price >= signal.target_price
        accuracy = min(1.0, (outcome_price - signal.entry_price) / (signal.target_price - signal.entry_price))
    else:  # SELL, PUT
        signal.is_winning = outcome_price <= signal.target_price
        accuracy = min(1.0, (signal.entry_price - outcome_price) / (signal.entry_price - signal.target_price))

    signal.accuracy_score = max(0, accuracy)

    db.commit()
    db.refresh(signal)
    return signal


if __name__ == "__main__":
    logger.info("✅ Paper trading model module ready")
    init_paper_trading_db()
    logger.info("✅ Paper trading tables initialized")
