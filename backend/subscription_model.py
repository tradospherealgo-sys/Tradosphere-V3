"""
Subscription Management - SaaS billing tiers and subscription tracking
"""

from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///tradosphere_saas.db')
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ===== SUBSCRIPTION TIERS =====
SUBSCRIPTION_TIERS = {
    "free": {
        "name": "Free",
        "price": 0,
        "signals_per_month": 100,
        "api_calls_per_day": 1000,
        "brokers_supported": 1,
        "features": ["Live prices", "Basic technical analysis"],
        "priority_support": False
    },
    "pro": {
        "name": "Pro",
        "price": 99,
        "signals_per_month": 5000,
        "api_calls_per_day": 50000,
        "brokers_supported": 3,
        "features": ["Live prices", "Technical analysis", "Options intelligence", "Signal generation", "Advanced analytics"],
        "priority_support": True
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 499,
        "signals_per_month": 999999,
        "api_calls_per_day": 999999,
        "brokers_supported": 10,
        "features": ["Everything", "White-label", "Custom integrations", "Dedicated support", "SLA guaranteed"],
        "priority_support": True
    }
}


# ===== DATABASE MODELS =====
class SubscriptionPlan(Base):
    """Subscription plan tier"""
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True)
    tier = Column(String, unique=True, index=True)  # free, pro, enterprise
    name = Column(String)
    monthly_price = Column(Float)
    annual_price = Column(Float)
    signals_limit = Column(Integer)
    api_calls_limit = Column(Integer)
    brokers_supported = Column(Integer)
    features = Column(Text)  # JSON string
    priority_support = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subscriptions = relationship("UserSubscription", back_populates="plan")


class UserSubscription(Base):
    """User subscription to a plan"""
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)  # Reference to users.id (no FK to avoid circular dependency)
    plan_id = Column(Integer, ForeignKey('subscription_plans.id'))
    stripe_customer_id = Column(String, unique=True)
    stripe_subscription_id = Column(String)
    status = Column(String, default="active")  # active, trialing, past_due, canceled
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    trial_end = Column(DateTime)
    canceled_at = Column(DateTime)
    auto_renew = Column(Boolean, default=True)
    payment_method = Column(String)  # card, bank_transfer, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    plan = relationship("SubscriptionPlan", back_populates="subscriptions")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "plan_tier": self.plan.tier if self.plan else None,
            "status": self.status,
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "auto_renew": self.auto_renew
        }

    def is_active(self):
        return self.status == "active" and (not self.current_period_end or self.current_period_end > datetime.utcnow())

    def days_remaining(self):
        if self.current_period_end:
            delta = self.current_period_end - datetime.utcnow()
            return max(0, delta.days)
        return 0


class UsageMetrics(Base):
    """Track API usage and signal generation"""
    __tablename__ = "usage_metrics"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)  # Reference to users.id (no FK to avoid circular dependency)
    month = Column(String)  # YYYY-MM format
    signals_generated = Column(Integer, default=0)
    signals_executed = Column(Integer, default=0)
    api_calls = Column(Integer, default=0)
    brokers_connected = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "month": self.month,
            "signals_generated": self.signals_generated,
            "signals_executed": self.signals_executed,
            "api_calls": self.api_calls,
            "brokers_connected": self.brokers_connected,
            "winning_trades": self.winning_trades,
            "total_pnl": self.total_pnl
        }


class Invoice(Base):
    """Billing invoices"""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)  # Reference to users.id
    subscription_id = Column(Integer, index=True)  # Reference to user_subscriptions.id
    invoice_number = Column(String, unique=True)
    stripe_invoice_id = Column(String)
    amount = Column(Float)
    status = Column(String, default="unpaid")  # paid, unpaid, failed
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    due_date = Column(DateTime)
    paid_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "amount": self.amount,
            "status": self.status,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "paid_date": self.paid_date.isoformat() if self.paid_date else None
        }


# ===== DATABASE FUNCTIONS =====
def init_subscription_db():
    """Initialize subscription tables"""
    Base.metadata.create_all(bind=engine)

    # Create default plans if they don't exist
    db = SessionLocal()
    try:
        existing = db.query(SubscriptionPlan).filter(SubscriptionPlan.tier == "free").first()
        if not existing:
            for tier, details in SUBSCRIPTION_TIERS.items():
                plan = SubscriptionPlan(
                    tier=tier,
                    name=details["name"],
                    monthly_price=details["price"],
                    annual_price=details["price"] * 10,  # 2 months free
                    signals_limit=details["signals_per_month"],
                    api_calls_limit=details["api_calls_per_day"],
                    brokers_supported=details["brokers_supported"],
                    features=str(details["features"]),
                    priority_support=details["priority_support"]
                )
                db.add(plan)
            db.commit()
    finally:
        db.close()


def get_user_subscription(db, user_id: int):
    """Get current subscription for user"""
    return db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()


def create_subscription(db, user_id: int, plan_tier: str, stripe_customer_id: str = None):
    """Create user subscription"""
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.tier == plan_tier).first()
    if not plan:
        return None

    now = datetime.utcnow()
    subscription = UserSubscription(
        user_id=user_id,
        plan_id=plan.id,
        stripe_customer_id=stripe_customer_id,
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30)
    )
    db.add(subscription)
    db.commit()
    return subscription


def upgrade_subscription(db, user_id: int, new_plan_tier: str):
    """Upgrade user subscription"""
    subscription = get_user_subscription(db, user_id)
    if not subscription:
        return create_subscription(db, user_id, new_plan_tier)

    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.tier == new_plan_tier).first()
    if not plan:
        return None

    subscription.plan_id = plan.id
    subscription.updated_at = datetime.utcnow()
    db.commit()
    return subscription


def get_user_usage(db, user_id: int, month: str = None):
    """Get usage metrics for user"""
    if not month:
        month = datetime.utcnow().strftime("%Y-%m")

    return db.query(UsageMetrics).filter(
        UsageMetrics.user_id == user_id,
        UsageMetrics.month == month
    ).first()


def increment_usage(db, user_id: int, signals: int = 0, api_calls: int = 0):
    """Increment usage counters"""
    month = datetime.utcnow().strftime("%Y-%m")
    metrics = get_user_usage(db, user_id, month)

    if not metrics:
        metrics = UsageMetrics(user_id=user_id, month=month)
        db.add(metrics)

    metrics.signals_generated += signals
    metrics.api_calls += api_calls
    db.commit()
    return metrics


def create_invoice(db, user_id: int, subscription_id: int, amount: float):
    """Create invoice"""
    invoice_number = f"INV-{user_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    now = datetime.utcnow()

    invoice = Invoice(
        user_id=user_id,
        subscription_id=subscription_id,
        invoice_number=invoice_number,
        amount=amount,
        status="unpaid",
        period_start=now,
        period_end=now + timedelta(days=30),
        due_date=now + timedelta(days=15)
    )
    db.add(invoice)
    db.commit()
    return invoice


def get_user_invoices(db, user_id: int, limit: int = 20):
    """Get user's invoices"""
    return db.query(Invoice).filter(Invoice.user_id == user_id).order_by(
        Invoice.created_at.desc()
    ).limit(limit).all()


if __name__ == "__main__":
    print("✅ Subscription model module ready")
    init_subscription_db()
    print("✅ Subscription tables initialized")
