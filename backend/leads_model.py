"""
Leads & Clients Tracking - CRM for managing signups and active users
Track leads, conversions, and client lifecycle
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///tradosphere_saas.db')
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ===== LEADS & CLIENTS MODELS =====
class Lead(Base):
    """Track signup leads and conversions"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String, nullable=True)
    company_name = Column(String, nullable=True)

    # Lead source
    source = Column(String, default="organic")  # organic, referral, ad, direct, etc.
    source_details = Column(Text, nullable=True)

    # Lead status
    status = Column(String, default="lead")  # lead, trial, free_customer, paid_customer, churned
    lead_score = Column(Integer, default=0)  # 0-100

    # Conversion tracking
    signed_up = Column(Boolean, default=False)
    user_id = Column(Integer, nullable=True, index=True)  # Links to users table
    signed_up_date = Column(DateTime, nullable=True)

    # Engagement
    last_login = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)
    days_active = Column(Integer, default=0)

    # Subscription
    subscription_tier = Column(String, default="free")  # free, pro, enterprise
    subscription_date = Column(DateTime, nullable=True)
    monthly_spent = Column(Float, default=0.0)
    total_spent = Column(Float, default=0.0)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "company_name": self.company_name,
            "source": self.source,
            "status": self.status,
            "lead_score": self.lead_score,
            "signed_up": self.signed_up,
            "user_id": self.user_id,
            "signed_up_date": self.signed_up_date.isoformat() if self.signed_up_date else None,
            "subscription_tier": self.subscription_tier,
            "subscription_date": self.subscription_date.isoformat() if self.subscription_date else None,
            "total_spent": self.total_spent,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "days_active": self.days_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Client(Base):
    """Track active paying clients"""
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, index=True)  # Link to user
    email = Column(String, unique=True, index=True)
    company_name = Column(String, nullable=True)

    # Client status
    status = Column(String, default="active")  # active, inactive, suspended, churned
    tier = Column(String, default="pro")  # free, pro, enterprise

    # Engagement metrics
    signals_generated = Column(Integer, default=0)
    trades_executed = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    roi = Column(Float, default=0.0)

    # Billing
    monthly_revenue = Column(Float, default=0.0)
    annual_revenue = Column(Float, default=0.0)
    lifetime_value = Column(Float, default=0.0)
    next_billing_date = Column(DateTime, nullable=True)
    payment_method = Column(String, nullable=True)

    # Activity
    last_login = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)
    days_since_activity = Column(Integer, default=0)
    activity_score = Column(Integer, default=50)  # 0-100

    # Health
    health_status = Column(String, default="healthy")  # healthy, at_risk, inactive
    churn_risk = Column(Float, default=0.0)  # 0-1 probability

    # Timestamps
    onboarded_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email": self.email,
            "company_name": self.company_name,
            "status": self.status,
            "tier": self.tier,
            "signals_generated": self.signals_generated,
            "total_pnl": self.total_pnl,
            "roi": self.roi,
            "monthly_revenue": self.monthly_revenue,
            "lifetime_value": self.lifetime_value,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "health_status": self.health_status,
            "churn_risk": self.churn_risk,
            "onboarded_date": self.onboarded_date.isoformat() if self.onboarded_date else None
        }


# ===== DATABASE FUNCTIONS =====
def init_leads_db():
    """Initialize leads tables"""
    Base.metadata.create_all(bind=engine)


def create_lead(db, email: str, first_name: str = None, last_name: str = None, source: str = "organic"):
    """Create a new lead"""
    lead = Lead(
        email=email,
        first_name=first_name,
        last_name=last_name,
        source=source,
        status="lead"
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def get_lead_by_email(db, email: str):
    """Get lead by email"""
    return db.query(Lead).filter(Lead.email == email).first()


def convert_lead_to_customer(db, email: str, user_id: int, tier: str = "free"):
    """Convert a lead to a customer"""
    lead = get_lead_by_email(db, email)
    if lead:
        lead.signed_up = True
        lead.user_id = user_id
        lead.signed_up_date = datetime.utcnow()
        lead.status = "free_customer" if tier == "free" else "paid_customer"
        lead.subscription_tier = tier
        if tier in ["pro", "enterprise"]:
            lead.subscription_date = datetime.utcnow()
        db.commit()
        db.refresh(lead)

        # Create corresponding client record if paid
        if tier in ["pro", "enterprise"]:
            create_client(db, user_id, email, tier)

    return lead


def create_client(db, user_id: int, email: str, tier: str = "pro"):
    """Create a new paid client"""
    client = Client(
        user_id=user_id,
        email=email,
        tier=tier,
        status="active"
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get_client_by_user_id(db, user_id: int):
    """Get client by user ID"""
    return db.query(Client).filter(Client.user_id == user_id).first()


def get_all_leads(db, limit: int = 100):
    """Get all leads"""
    return db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()


def get_all_clients(db, limit: int = 100):
    """Get all active clients"""
    return db.query(Client).filter(Client.status == "active").order_by(Client.lifetime_value.desc()).limit(limit).all()


def get_leads_stats(db):
    """Get lead statistics"""
    from sqlalchemy import func

    total_leads = db.query(func.count(Lead.id)).scalar()
    converted_leads = db.query(func.count(Lead.id)).filter(Lead.signed_up == True).scalar()
    paid_customers = db.query(func.count(Lead.id)).filter(Lead.status.in_(["paid_customer"])).scalar()

    conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
    paid_rate = (paid_customers / total_leads * 100) if total_leads > 0 else 0

    return {
        "total_leads": total_leads or 0,
        "converted_leads": converted_leads or 0,
        "paid_customers": paid_customers or 0,
        "conversion_rate": round(conversion_rate, 2),
        "paid_conversion_rate": round(paid_rate, 2)
    }


def get_clients_stats(db):
    """Get client statistics"""
    from sqlalchemy import func

    clients = db.query(Client).all()
    total_clients = len(clients)
    active_clients = len([c for c in clients if c.status == "active"])
    at_risk_clients = len([c for c in clients if c.churn_risk > 0.5])

    total_mrr = db.query(func.sum(Client.monthly_revenue)).scalar() or 0
    total_ltv = db.query(func.sum(Client.lifetime_value)).scalar() or 0

    return {
        "total_clients": total_clients,
        "active_clients": active_clients,
        "at_risk_clients": at_risk_clients,
        "total_mrr": float(total_mrr),
        "total_ltv": float(total_ltv),
        "average_ltv": float(total_ltv / max(1, total_clients))
    }


if __name__ == "__main__":
    print("✅ Leads model module ready")
    init_leads_db()
    print("✅ Leads tables initialized")
