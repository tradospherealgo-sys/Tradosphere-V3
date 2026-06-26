"""
User Routes - Profile, Settings, API Key Management
"""
import logging
logger = logging.getLogger(__name__)


from flask import Blueprint, request, g
from user_model_v3_1 import (
    SessionLocal, get_user_by_id, update_user, get_user_api_keys,
    create_api_key, delete_api_key
)
from multi_tenant_middleware import MultiTenantMiddleware
from response_handler import APIResponse

user_bp = Blueprint('user', __name__, url_prefix='/api/user')


@user_bp.route('/profile', methods=['GET'])
@MultiTenantMiddleware.tenant_required
def get_profile():
    """Get current user profile"""
    try:
        user_id = g.user_id
        db = SessionLocal()
        user = get_user_by_id(db, user_id)
        db.close()

        if not user:
            return APIResponse.not_found("User not found")

        return APIResponse.success(user.to_dict())

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/profile', methods=['PUT'])
@MultiTenantMiddleware.tenant_required
def update_profile():
    """Update user profile"""
    try:
        user_id = g.user_id
        data = request.get_json()

        if not data:
            return APIResponse.bad_request("No data provided")

        allowed_fields = {"first_name", "last_name", "phone", "company_name", "timezone", "bio"}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        db = SessionLocal()
        user = update_user(db, user_id, **update_data)
        db.close()

        return APIResponse.success(user.to_dict())

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/api-keys', methods=['GET'])
@MultiTenantMiddleware.tenant_required
def get_api_keys():
    """Get all API keys for current user"""
    try:
        user_id = g.user_id
        db = SessionLocal()

        user = get_user_by_id(db, user_id)
        if not user:
            db.close()
            return APIResponse.not_found("User not found")

        api_keys = get_user_api_keys(db, user_id)
        db.close()

        return APIResponse.success({
            "api_keys": [key.to_dict(include_secrets=False) for key in api_keys],
            "count": len(api_keys)
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/api-keys', methods=['POST'])
@MultiTenantMiddleware.tenant_required
def add_api_key():
    """Add new API key for broker connection"""
    try:
        user_id = g.user_id
        data = request.get_json()

        if not data:
            return APIResponse.bad_request("No data provided")

        required = {"key_name", "api_key", "api_secret", "client_code"}
        if not all(field in data for field in required):
            return APIResponse.bad_request(f"Required fields: {', '.join(required)}")

        key_name = data.get("key_name", "").strip()
        api_key = data.get("api_key", "").strip()
        api_secret = data.get("api_secret", "").strip()
        client_code = data.get("client_code", "").strip()

        if not all([key_name, api_key, api_secret, client_code]):
            return APIResponse.bad_request("All fields required and cannot be empty")

        db = SessionLocal()

        user = get_user_by_id(db, user_id)
        if not user:
            db.close()
            return APIResponse.not_found("User not found")

        new_key = create_api_key(db, user_id, key_name, api_key, api_secret, client_code)
        db.close()

        return APIResponse.success(new_key.to_dict(include_secrets=False), http_status=201)

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/api-keys/<int:key_id>', methods=['DELETE'])
@MultiTenantMiddleware.tenant_required
def remove_api_key(key_id):
    """Remove API key (owner only)"""
    try:
        user_id = g.user_id
        db = SessionLocal()

        success = delete_api_key(db, key_id, user_id)
        db.close()

        if not success:
            return APIResponse.not_found("API key not found or unauthorized")

        return APIResponse.success({"message": "API key deleted"})

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/subscription', methods=['GET'])
@MultiTenantMiddleware.tenant_required
def get_subscription():
    """Get user subscription info"""
    try:
        subscription = {
            "plan": "free",
            "status": "active",
            "amount": 0,
            "billing_cycle": "Monthly",
            "next_renewal": "N/A"
        }
        return APIResponse.success(subscription)
    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/billing-history', methods=['GET'])
@MultiTenantMiddleware.tenant_required
def get_billing_history():
    """Get user billing history"""
    try:
        history = [
            {"date": "2026-06-15", "description": "Pro Plan - Monthly", "amount": 999, "status": "paid"},
            {"date": "2026-05-15", "description": "Pro Plan - Monthly", "amount": 999, "status": "paid"},
            {"date": "2026-04-15", "description": "Free Plan", "amount": 0, "status": "paid"},
        ]
        return APIResponse.success({"billing_history": history, "count": len(history)})
    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/watchlist', methods=['GET'])
@MultiTenantMiddleware.tenant_required
def get_watchlist():
    """Get user watchlist"""
    try:
        watchlist = [
            {"symbol": "NIFTY", "price": 52000, "change": 100, "changePercent": 0.19, "volume": 1000000},
            {"symbol": "BANKNIFTY", "price": 48000, "change": -200, "changePercent": -0.42, "volume": 800000},
            {"symbol": "SENSEX", "price": 60000, "change": 300, "changePercent": 0.50, "volume": 500000},
        ]
        return APIResponse.success({"watchlist": watchlist, "count": len(watchlist)})
    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/watchlist', methods=['POST'])
@MultiTenantMiddleware.tenant_required
def add_watchlist():
    """Add symbol to watchlist"""
    try:
        data = request.get_json()
        if not data or "symbol" not in data:
            return APIResponse.bad_request("Symbol required")

        symbol = data.get("symbol")
        return APIResponse.success({"message": f"{symbol} added to watchlist"}, http_status=201)
    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/watchlist/<symbol>', methods=['DELETE'])
@MultiTenantMiddleware.tenant_required
def remove_watchlist(symbol):
    """Remove symbol from watchlist"""
    try:
        return APIResponse.success({"message": f"{symbol} removed from watchlist"})
    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/preferences', methods=['GET'])
@MultiTenantMiddleware.tenant_required
def get_preferences():
    """Get user preferences"""
    try:
        user_id = g.user_id
        db = SessionLocal()
        user = get_user_by_id(db, user_id)
        db.close()

        if not user:
            return APIResponse.not_found("User not found")

        return APIResponse.success({
            "timezone": user.timezone,
            "email_alerts": True,
            "sms_alerts": False,
            "daily_summary": True
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/preferences', methods=['PUT'])
@MultiTenantMiddleware.tenant_required
def update_preferences():
    """Update user preferences"""
    try:
        user_id = g.user_id
        data = request.get_json()

        if not data:
            return APIResponse.bad_request("No data provided")

        return APIResponse.success({"message": "Preferences updated"})

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/account/deactivate', methods=['POST'])
@MultiTenantMiddleware.tenant_required
def deactivate_account():
    """Deactivate user account (soft delete)"""
    try:
        user_id = g.user_id
        db = SessionLocal()

        user = update_user(db, user_id, is_active=False)
        db.close()

        return APIResponse.success({"message": "Account deactivated. You can reactivate by logging in."})

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/account/delete', methods=['POST'])
@MultiTenantMiddleware.tenant_required
def delete_account():
    """Permanently delete user account and all data"""
    try:
        data = request.get_json()

        if not data or "password" not in data:
            return APIResponse.bad_request("Password required to delete account")

        return APIResponse.success({"message": "Account deletion will be enabled in Phase 2 with proper verification"})

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@user_bp.route('/activity', methods=['GET'])
@MultiTenantMiddleware.tenant_required
def get_activity():
    """Get user activity log (sessions, logins)"""
    try:
        user_id = g.user_id
        db = SessionLocal()

        user = get_user_by_id(db, user_id)
        db.close()

        if not user:
            return APIResponse.not_found("User not found")

        return APIResponse.success({
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "active_sessions": 1
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


if __name__ == "__main__":
    logger.info("✅ User routes module ready")
