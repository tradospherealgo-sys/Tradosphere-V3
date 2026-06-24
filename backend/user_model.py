"""
User Model - SQLAlchemy ORM models for SaaS multi-tenancy
Users, API Keys, Sessions, and user-specific data
"""

from datetime import datetime
from typing import Dict, List
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tradosphere.db")

# Support PostgreSQL in production
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User account model - Google OAuth V1"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)  # Full name from Google

    # Google OAuth fields
    google_id = Column(String(255), unique=True, index=True, nullable=True)  # Google's unique ID
    picture_url = Column(String(500), nullable=True)  # Profile picture URL from Google

    # Legacy/optional fields for future use
    password_hash = Column(String(255), nullable=True)  # Optional, for migration
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    company_name = Column(String(200), nullable=True)
    timezone = Column(String(50), default="Asia/Kolkata")

    # Account status
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=True)  # Always True for Google auth

    # Profile
    profile_pic = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)

    # Account info
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relations
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "company_name": self.company_name,
            "timezone": self.timezone,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_admin={self.is_admin})>"


class APIKey(Base):
    """User's broker API keys"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    key_name = Column(String(100), nullable=False)  # e.g., "Angel One Main"
    broker = Column(String(50), default="angel_one")  # broker type
    api_key = Column(String(255), nullable=False)
    api_secret = Column(String(255), nullable=False)
    client_code = Column(String(100), nullable=False)

    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_connected = Column(Boolean, default=False)

    # Connection tracking
    last_tested = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relation
    user = relationship("User", back_populates="api_keys")

    def to_dict(self, include_secrets=False) -> Dict:
        """Convert to dict (optionally hide secrets)"""
        data = {
            "id": self.id,
            "key_name": self.key_name,
            "broker": self.broker,
            "client_code": self.client_code,
            "is_active": self.is_active,
            "is_connected": self.is_connected,
            "last_tested": self.last_tested.isoformat() if self.last_tested else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

        if include_secrets:
            data["api_key"] = self.api_key
            data["api_secret"] = self.api_secret

        return data

    def __repr__(self):
        return f"<APIKey(id={self.id}, user_id={self.user_id}, broker={self.broker})>"


class UserSession(Base):
    """Track user login sessions"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(500), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_type = Column(String(50), nullable=True)  # web, mobile, desktop

    # Session info
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    last_activity = Column(DateTime, default=datetime.utcnow)

    # Relation
    user = relationship("User", back_populates="sessions")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "device_type": self.device_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active
        }

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, ip={self.ip_address})>"


# Note: The Signal and Trade models need to be imported from database.py
# We'll add user_id foreign key constraint in migration


def init_user_db():
    """Initialize user database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ User database tables created")


def get_user_db():
    """Get database session for user operations"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# User operations
def create_user(db, email: str, password_hash: str = None, first_name: str = None,
                last_name: str = None, name: str = None, google_id: str = None,
                picture_url: str = None) -> User:
    """Create new user - supports both password and Google OAuth"""
    user = User(
        email=email,
        password_hash=password_hash,
        name=name,
        google_id=google_id,
        picture_url=picture_url,
        first_name=first_name,
        last_name=last_name,
        is_verified=True if google_id else False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db, email: str) -> User:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db, user_id: int) -> User:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_all_users(db, skip: int = 0, limit: int = 100) -> List[User]:
    """Get all users (admin only)"""
    return db.query(User).offset(skip).limit(limit).all()


def update_user(db, user_id: int, **kwargs) -> User:
    """Update user fields"""
    user = get_user_by_id(db, user_id)
    if user:
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        db.commit()
        db.refresh(user)
    return user


def delete_user(db, user_id: int) -> bool:
    """Delete user (cascades to api_keys and sessions)"""
    user = get_user_by_id(db, user_id)
    if user:
        db.delete(user)
        db.commit()
        return True
    return False


# API Key operations
def create_api_key(db, user_id: int, key_name: str, api_key: str,
                   api_secret: str, client_code: str) -> APIKey:
    """Create API key for user"""
    api_key_obj = APIKey(
        user_id=user_id,
        key_name=key_name,
        api_key=api_key,
        api_secret=api_secret,
        client_code=client_code
    )
    db.add(api_key_obj)
    db.commit()
    db.refresh(api_key_obj)
    return api_key_obj


def get_user_api_keys(db, user_id: int) -> List[APIKey]:
    """Get all API keys for user"""
    return db.query(APIKey).filter(APIKey.user_id == user_id).all()


def get_active_api_key(db, user_id: int) -> APIKey:
    """Get first active API key for user"""
    return db.query(APIKey).filter(
        APIKey.user_id == user_id,
        APIKey.is_active == True
    ).first()


def delete_api_key(db, key_id: int, user_id: int) -> bool:
    """Delete API key (only owner can delete)"""
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == user_id
    ).first()
    if key:
        db.delete(key)
        db.commit()
        return True
    return False


# Session operations
def create_session(db, user_id: int, token: str, ip_address: str,
                   user_agent: str) -> UserSession:
    """Create new session"""
    session = UserSession(
        user_id=user_id,
        token=token,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_user_sessions(db, user_id: int) -> List[UserSession]:
    """Get active sessions for user"""
    return db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_active == True
    ).all()


if __name__ == "__main__":
    # Test models
    print("\n" + "="*70)
    print("👤 USER MODEL - TEST")
    print("="*70)

    init_user_db()
    print("✅ User database initialized")

    print("\n" + "="*70)
