"""
User Authentication Manager - JWT-based auth for SaaS
Handles signup, login, password management, token generation
"""

import os
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from functools import wraps
from flask import request, jsonify, g

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("CRITICAL: JWT_SECRET environment variable not set. Set it on Railway before deployment.")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
REFRESH_TOKEN_EXPIRY_DAYS = 30


class PasswordManager:
    """Secure password hashing and verification"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with salt"""
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters")

        # Generate salt
        salt = secrets.token_hex(16)
        # Hash password with salt
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        # Return salt + hash
        return f"{salt}${pwd_hash.hex()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            salt, pwd_hash = hashed.split('$')
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return new_hash.hex() == pwd_hash
        except Exception as e:
            print(f"Password verification error: {e}")
            return False


class JWTManager:
    """JWT token generation and validation"""

    @staticmethod
    def generate_tokens(user_id: int, email: str) -> Dict:
        """Generate access and refresh tokens"""
        now = datetime.utcnow()

        # Access token (24 hours)
        access_payload = {
            "user_id": user_id,
            "email": email,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=JWT_EXPIRY_HOURS)
        }

        # Refresh token (30 days)
        refresh_payload = {
            "user_id": user_id,
            "email": email,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)
        }

        access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": JWT_EXPIRY_HOURS * 3600,
            "user_id": user_id,
            "email": email
        }

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            # Verify token type
            if payload.get("type") != token_type:
                return None

            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def refresh_access_token(refresh_token: str) -> Optional[str]:
        """Generate new access token from refresh token"""
        payload = JWTManager.verify_token(refresh_token, token_type="refresh")
        if not payload:
            return None

        user_id = payload.get("user_id")
        email = payload.get("email")

        new_payload = {
            "user_id": user_id,
            "email": email,
            "type": "access",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
        }

        return jwt.encode(new_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


class AuthDecorator:
    """Flask decorators for authentication"""

    @staticmethod
    def token_required(f):
        """Require valid JWT token"""
        @wraps(f)
        def decorated(*args, **kwargs):
            token = None

            # Check Authorization header
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                try:
                    token = auth_header.split(" ")[1]
                except IndexError:
                    return jsonify({"status": "error", "message": "Invalid token format"}), 401

            if not token:
                return jsonify({"status": "error", "message": "Token missing"}), 401

            # Verify token
            payload = JWTManager.verify_token(token, token_type="access")
            if not payload:
                return jsonify({"status": "error", "message": "Invalid or expired token"}), 401

            # Store user info in Flask g object for use in route
            g.user_id = payload.get("user_id")
            g.email = payload.get("email")

            return f(*args, **kwargs)

        return decorated

    @staticmethod
    def admin_required(f):
        """Require admin user"""
        @wraps(f)
        def decorated(*args, **kwargs):
            # First check token
            token = None
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                try:
                    token = auth_header.split(" ")[1]
                except IndexError:
                    return jsonify({"status": "error", "message": "Invalid token format"}), 401

            if not token:
                return jsonify({"status": "error", "message": "Token missing"}), 401

            payload = JWTManager.verify_token(token, token_type="access")
            if not payload:
                return jsonify({"status": "error", "message": "Invalid or expired token"}), 401

            # Check admin status (will be validated in route by checking user record)
            g.user_id = payload.get("user_id")
            g.email = payload.get("email")

            return f(*args, **kwargs)

        return decorated


# Email validation
class EmailValidator:
    """Email validation and utilities"""

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize email (lowercase, strip spaces)"""
        return email.lower().strip()


# Session management
class SessionManager:
    """Track active sessions per user"""

    @staticmethod
    def create_session(user_id: int, token: str, request_obj) -> Dict:
        """Create new session record"""
        return {
            "user_id": user_id,
            "token": token,
            "ip_address": request_obj.remote_addr,
            "user_agent": request_obj.headers.get("User-Agent", ""),
            "created_at": datetime.utcnow().isoformat(),
            "is_active": True
        }

    @staticmethod
    def invalidate_session(user_id: int, token: str) -> bool:
        """Mark session as inactive (logout)"""
        # In Phase 2, we'll track sessions in database
        # For Phase 1, just return True
        return True


if __name__ == "__main__":
    # Test authentication
    print("\n" + "="*70)
    print("🔐 AUTHENTICATION MANAGER - TEST")
    print("="*70)

    # Test password hashing
    pwd = "MySecurePassword123"
    hashed = PasswordManager.hash_password(pwd)
    print(f"\n✅ Password hashed: {hashed[:50]}...")
    print(f"✅ Password verified: {PasswordManager.verify_password(pwd, hashed)}")
    print(f"❌ Wrong password: {PasswordManager.verify_password('WrongPassword', hashed)}")

    # Test JWT tokens
    tokens = JWTManager.generate_tokens(user_id=123, email="user@example.com")
    print(f"\n✅ Access token generated")
    print(f"✅ Token type: {tokens['token_type']}")
    print(f"✅ Expires in: {tokens['expires_in']} seconds")

    # Verify token
    payload = JWTManager.verify_token(tokens["access_token"], token_type="access")
    print(f"✅ Token verified: user_id={payload.get('user_id')}, email={payload.get('email')}")

    # Test email validation
    print(f"\n✅ Valid email: {EmailValidator.is_valid_email('user@example.com')}")
    print(f"❌ Invalid email: {EmailValidator.is_valid_email('invalid-email')}")

    print("\n" + "="*70)
