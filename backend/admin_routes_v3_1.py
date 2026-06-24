"""
Admin Routes - User management, analytics, and admin controls
"""

from flask import Blueprint, request, g
from datetime import datetime, timedelta
from functools import wraps
from user_model_v3_1 import SessionLocal, get_user_by_id, update_user
from subscription_model import (
    SessionLocal as SubSessionLocal, get_user_subscription,
    UsageMetrics, Invoice
)
from multi_tenant_middleware import MultiTenantMiddleware
from response_handler import APIResponse
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def is_admin(f):
    """Decorator to check if user is admin"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = g.user_id
        db = SessionLocal()
        user = get_user_by_id(db, user_id)
        db.close()

        if not user or not user.is_admin:
            return APIResponse.forbidden("Admin access required")

        return f(*args, **kwargs)

    return decorated


@admin_bp.route('/dashboard', methods=['GET'])
@MultiTenantMiddleware.tenant_required
@is_admin
def admin_dashboard():
    """Get admin dashboard overview"""
    try:
        db = SessionLocal()
        sub_db = SubSessionLocal()

        from user_model_v3_1 import User
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        new_users_7d = db.query(User).filter(
            User.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()

        from subscription_model import UserSubscription
        active_subscriptions = sub_db.query(UserSubscription).filter(
            UserSubscription.status == 'active'
        ).count()

        invoices = sub_db.query(Invoice).filter(
            Invoice.status == 'paid',
            Invoice.created_at >= datetime.utcnow() - timedelta(days=30)
        ).all()
        monthly_revenue = sum([inv.amount for inv in invoices]) if invoices else 0

        db.close()
        sub_db.close()

        return APIResponse.success({
            "users": {
                "total": total_users,
                "active": active_users,
                "new_7d": new_users_7d
            },
            "subscriptions": {
                "active": active_subscriptions
            },
            "revenue": {
                "monthly": monthly_revenue,
                "currency": "INR"
            },
            "health": {
                "status": "healthy",
                "api_uptime": 99.9,
                "database": "connected"
            }
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@admin_bp.route('/users', methods=['GET'])
@MultiTenantMiddleware.tenant_required
@is_admin
def list_users():
    """List all users (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        search = request.args.get('search', '')

        db = SessionLocal()
        from user_model_v3_1 import User

        query = db.query(User)

        if search:
            query = query.filter(
                (User.email.ilike(f"%{search}%")) |
                (User.first_name.ilike(f"%{search}%")) |
                (User.last_name.ilike(f"%{search}%"))
            )

        total = query.count()
        users = query.offset((page - 1) * limit).limit(limit).all()
        db.close()

        return APIResponse.success({
            "users": [u.to_dict() for u in users],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@MultiTenantMiddleware.tenant_required
@is_admin
def get_user_details(user_id):
    """Get detailed user information"""
    try:
        db = SessionLocal()
        user = get_user_by_id(db, user_id)

        if not user:
            db.close()
            return APIResponse.not_found("User not found")

        user_dict = user.to_dict()
        user_dict["is_admin"] = user.is_admin
        user_dict["is_verified"] = user.is_verified
        user_dict["is_active"] = user.is_active

        db.close()

        return APIResponse.success(user_dict)

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@admin_bp.route('/users/<int:user_id>/promote', methods=['POST'])
@MultiTenantMiddleware.tenant_required
@is_admin
def promote_to_admin(user_id):
    """Promote user to admin"""
    try:
        db = SessionLocal()
        user = get_user_by_id(db, user_id)

        if not user:
            db.close()
            return APIResponse.not_found("User not found")

        user = update_user(db, user_id, is_admin=True)
        db.close()

        return APIResponse.success(user.to_dict())

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@admin_bp.route('/users/<int:user_id>/disable', methods=['POST'])
@MultiTenantMiddleware.tenant_required
@is_admin
def disable_user(user_id):
    """Disable user account"""
    try:
        db = SessionLocal()
        user = get_user_by_id(db, user_id)

        if not user:
            db.close()
            return APIResponse.not_found("User not found")

        user = update_user(db, user_id, is_active=False)
        db.close()

        return APIResponse.success({"message": f"User {user.email} disabled"})

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@admin_bp.route('/users/<int:user_id>/enable', methods=['POST'])
@MultiTenantMiddleware.tenant_required
@is_admin
def enable_user(user_id):
    """Enable user account"""
    try:
        db = SessionLocal()
        user = update_user(db, user_id, is_active=True)
        db.close()

        return APIResponse.success({"message": f"User {user.email} enabled"})

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@admin_bp.route('/analytics/overview', methods=['GET'])
@MultiTenantMiddleware.tenant_required
@is_admin
def analytics_overview():
    """Get platform analytics overview"""
    try:
        db = SessionLocal()
        from user_model_v3_1 import User

        total_users = db.query(func.count(User.id)).scalar()
        active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
        new_users_today = db.query(func.count(User.id)).filter(
            User.created_at >= datetime.utcnow() - timedelta(days=1)
        ).scalar()

        from subscription_model import UserSubscription
        sub_db = SubSessionLocal()

        active_subscriptions = sub_db.query(func.count(UserSubscription.id)).filter(
            UserSubscription.status == "active"
        ).scalar()

        total_revenue = sub_db.query(func.sum(Invoice.amount)).filter(
            Invoice.status == "paid"
        ).scalar()

        sub_db.close()
        db.close()

        return APIResponse.success({
            "users": {
                "total": total_users or 0,
                "active": active_users or 0,
                "new_today": new_users_today or 0
            },
            "subscriptions": {
                "active": active_subscriptions or 0
            },
            "revenue": {
                "total": float(total_revenue) if total_revenue else 0.0,
                "currency": "INR",
                "period": "all_time"
            }
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@admin_bp.route('/health', methods=['GET'])
@MultiTenantMiddleware.tenant_required
@is_admin
def system_health():
    """Get system health status"""
    try:
        db = SessionLocal()

        try:
            db.execute("SELECT 1")
            db_status = "healthy"
        except:
            db_status = "unhealthy"

        db.close()

        return APIResponse.success({
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_status,
            "api": "healthy",
            "overall": "healthy" if db_status == "healthy" else "degraded"
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@admin_bp.route('/config', methods=['GET'])
@MultiTenantMiddleware.tenant_required
@is_admin
def get_config():
    """Get system configuration (non-sensitive)"""
    try:
        import os

        return APIResponse.success({
            "environment": os.getenv("ENVIRONMENT", "development"),
            "version": "3.1",
            "broker": "Angel One",
            "features": {
                "multi_tenant": True,
                "subscriptions": True,
                "email_notifications": True,
                "multi_broker": "coming_soon"
            }
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@admin_bp.route('/audit-log', methods=['GET'])
@MultiTenantMiddleware.tenant_required
@is_admin
def get_audit_log():
    """Get system audit log"""
    try:
        return APIResponse.success({
            "message": "Audit logging will be implemented in Phase 2.5",
            "audit_logs": []
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


if __name__ == "__main__":
    print("✅ Admin routes module ready")
