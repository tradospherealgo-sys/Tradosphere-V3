"""
Authentication Routes - Google OAuth, Signup, Login, Logout, Token Refresh
"""

from flask import Blueprint, request, g
from datetime import datetime
import os
from user_model_v3_1 import (
    SessionLocal, get_user_by_email, create_user, get_user_by_id,
    create_session, get_user_sessions, User
)
from auth_manager_v3_1 import (
    PasswordManager, JWTManager, EmailValidator, AuthDecorator
)
from response_handler import APIResponse
from leads_model import SessionLocal as LeadsSessionLocal, create_lead, convert_lead_to_customer, get_lead_by_email

# Google JWT verification
try:
    from google.auth.transport import requests
    from google.oauth2 import id_token
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    print("⚠️  google-auth not installed. Google authentication will not work.")

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/google', methods=['POST'])
def google_auth():
    """Google OAuth authentication endpoint"""
    try:
        data = request.get_json()

        if not data or 'credential' not in data:
            return APIResponse.bad_request("Missing credential in request")

        google_token = data.get('credential')

        if not GOOGLE_AUTH_AVAILABLE:
            return APIResponse.server_error("Google authentication not configured on server")

        try:
            google_client_id = os.getenv("GOOGLE_CLIENT_ID")
            if not google_client_id:
                return APIResponse.server_error("Server configuration error: GOOGLE_CLIENT_ID not set")

            idinfo = id_token.verify_oauth2_token(
                google_token,
                requests.Request(),
                cid=google_client_id
            )

            if not idinfo.get('email_verified'):
                return APIResponse.error("EMAIL_NOT_VERIFIED", "Email not verified by Google", 401)

            email = idinfo.get('email')
            name = idinfo.get('name', '')
            picture_url = idinfo.get('picture', '')
            google_id = idinfo.get('sub')

            if not email:
                return APIResponse.error("NO_EMAIL", "Email not available in Google token", 401)

            print(f"✅ Google token verified for: {email}")

        except ValueError as e:
            print(f"❌ Invalid Google token: {str(e)}")
            return APIResponse.error("INVALID_TOKEN", "Invalid Google token", 401)

        db = SessionLocal()
        try:
            user = get_user_by_email(db, email)

            if not user:
                print(f"👤 Creating new user: {email}")
                user = create_user(
                    db,
                    email=email,
                    name=name,
                    google_id=google_id,
                    picture_url=picture_url
                )
                print(f"✅ User created: {user.id}")
            else:
                user.last_login = datetime.utcnow()
                db.commit()
                print(f"✅ User already exists: {user.id}")

            tokens = JWTManager.generate_tokens(user.id, user.email)
            print(f"🔐 Generated JWT for user: {user.id}")

            return APIResponse.success({
                "access_token": tokens['access_token'],
                "refresh_token": tokens.get('refresh_token'),
                "token_type": "Bearer",
                "expires_in": 3600,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "is_admin": user.is_admin
                }
            })

        finally:
            db.close()

    except Exception as e:
        print(f"❌ Google auth error: {str(e)}")
        return APIResponse.server_error(f"Authentication failed: {str(e)}", e)


@auth_bp.route('/signup', methods=['POST'])
def signup():
    """User signup endpoint"""
    try:
        data = request.get_json()

        if not data:
            return APIResponse.bad_request("No data provided")

        email = data.get("email", "").strip()
        password = data.get("password", "")
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()

        if not email or not password:
            return APIResponse.bad_request("Email and password required")

        if not EmailValidator.is_valid_email(email):
            return APIResponse.bad_request("Invalid email format")

        if len(password) < 6:
            return APIResponse.bad_request("Password must be at least 6 characters")

        email = EmailValidator.normalize_email(email)

        db = SessionLocal()
        existing_user = get_user_by_email(db, email)
        if existing_user:
            db.close()
            return APIResponse.conflict("Email already registered")

        try:
            password_hash = PasswordManager.hash_password(password)
        except ValueError as e:
            db.close()
            return APIResponse.bad_request(str(e))

        user = create_user(db, email, password_hash, first_name, last_name)
        user_id = user.id
        user_email = user.email
        user_dict = user.to_dict()

        tokens = JWTManager.generate_tokens(user_id, user_email)

        ip_address = request.remote_addr
        user_agent = request.headers.get("User-Agent", "")
        create_session(db, user_id, tokens["access_token"], ip_address, user_agent)

        db.close()

        try:
            leads_db = LeadsSessionLocal()
            convert_lead_to_customer(leads_db, email, user_id, "free")
            leads_db.close()
        except Exception as lead_error:
            print(f"⚠️  Lead conversion failed: {lead_error}")

        return APIResponse.success({
            "user": user_dict,
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "token_type": "Bearer",
            "expires_in": 3600
        }, http_status=201)

    except Exception as e:
        return APIResponse.server_error(f"Signup error: {str(e)}", e)


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()

        if not data:
            return APIResponse.bad_request("No data provided")

        email = data.get("email", "").strip()
        password = data.get("password", "")

        if not email or not password:
            return APIResponse.bad_request("Email and password required")

        email = EmailValidator.normalize_email(email)

        db = SessionLocal()

        user = get_user_by_email(db, email)
        if not user:
            db.close()
            return APIResponse.error("INVALID_CREDENTIALS", "Invalid email or password", 401)

        if not user.is_active:
            db.close()
            return APIResponse.forbidden("Account is disabled")

        if not PasswordManager.verify_password(password, user.password_hash):
            db.close()
            return APIResponse.error("INVALID_CREDENTIALS", "Invalid email or password", 401)

        user_id = user.id
        user_email = user.email
        user_is_admin = user.is_admin
        user_dict = user.to_dict()
        tokens = JWTManager.generate_tokens(user_id, user_email)

        user.last_login = datetime.utcnow()

        ip_address = request.remote_addr
        user_agent = request.headers.get("User-Agent", "")
        create_session(db, user_id, tokens["access_token"], ip_address, user_agent)

        db.commit()
        db.close()

        return APIResponse.success({
            "user": user_dict,
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "token_type": "Bearer",
            "expires_in": 3600,
            "is_admin": user_is_admin
        })

    except Exception as e:
        return APIResponse.server_error(f"Login error: {str(e)}", e)


@auth_bp.route('/logout', methods=['POST'])
@AuthDecorator.token_required
def logout():
    """Logout endpoint - invalidate current session"""
    try:
        user_id = g.user_id
        db = SessionLocal()

        sessions = get_user_sessions(db, user_id)
        for session in sessions:
            session.is_active = False

        db.commit()
        db.close()

        return APIResponse.success({"message": "Logout successful"})

    except Exception as e:
        return APIResponse.server_error(f"Logout error: {str(e)}", e)


@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token"""
    try:
        data = request.get_json()

        if not data or "refresh_token" not in data:
            return APIResponse.bad_request("Refresh token required")

        refresh_token_value = data.get("refresh_token")

        payload = JWTManager.verify_token(refresh_token_value, token_type="refresh")
        if not payload:
            return APIResponse.error("INVALID_TOKEN", "Invalid or expired refresh token", 401)

        new_access_token = JWTManager.refresh_access_token(refresh_token_value)
        if not new_access_token:
            return APIResponse.server_error("Failed to generate new token")

        return APIResponse.success({
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": 3600
        })

    except Exception as e:
        return APIResponse.server_error(f"Token refresh error: {str(e)}", e)


@auth_bp.route('/me', methods=['GET'])
@AuthDecorator.token_required
def get_current_user():
    """Get current logged-in user info"""
    try:
        user_id = g.user_id
        db = SessionLocal()
        user = get_user_by_id(db, user_id)
        db.close()

        if not user:
            return APIResponse.not_found("User not found")

        return APIResponse.success(user.to_dict())

    except Exception as e:
        return APIResponse.server_error(f"Error: {str(e)}", e)


@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """Verify email address (Phase 2 feature - email sending)"""
    return APIResponse.success({"message": "Email verification coming in Phase 2"})


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset (Phase 2 feature - email sending)"""
    return APIResponse.success({"message": "Password reset coming in Phase 2"})


@auth_bp.route('/reset-password', methods=['POST'])
@AuthDecorator.token_required
def reset_password():
    """Reset password (authenticated user)"""
    try:
        user_id = g.user_id
        data = request.get_json()

        if not data:
            return APIResponse.bad_request("No data provided")

        old_password = data.get("old_password", "")
        new_password = data.get("new_password", "")

        if not old_password or not new_password:
            return APIResponse.bad_request("Old and new passwords required")

        if len(new_password) < 6:
            return APIResponse.bad_request("New password must be at least 6 characters")

        db = SessionLocal()
        user = get_user_by_id(db, user_id)

        if not user:
            db.close()
            return APIResponse.not_found("User not found")

        if not PasswordManager.verify_password(old_password, user.password_hash):
            db.close()
            return APIResponse.error("INVALID_PASSWORD", "Old password is incorrect", 401)

        user.password_hash = PasswordManager.hash_password(new_password)
        db.commit()
        db.close()

        return APIResponse.success({"message": "Password reset successful"})

    except Exception as e:
        return APIResponse.server_error(f"Password reset error: {str(e)}", e)


if __name__ == "__main__":
    print("✅ Auth routes module ready")
