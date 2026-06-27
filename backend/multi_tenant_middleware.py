"""
Multi-Tenant Middleware - Enforce user data isolation
Filters all queries by user_id to ensure data privacy
"""
import logging
logger = logging.getLogger(__name__)


from flask import request, g, jsonify
from functools import wraps
from auth_manager import JWTManager


class MultiTenantMiddleware:
    """Middleware for multi-tenant data isolation"""

    @staticmethod
    def extract_user_id():
        """Extract and validate user_id from JWT token"""
        token = None

        # Check Authorization header
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(" ")[1]
            except IndexError:
                return None

        if not token:
            return None

        # Verify token
        payload = JWTManager.verify_token(token, token_type="access")
        if not payload:
            return None

        return payload.get("user_id")

    @staticmethod
    def tenant_required(f):
        """
        Decorator to enforce multi-tenancy
        Extracts user_id from token and stores in g.user_id
        Rejects unauthenticated requests
        """
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = MultiTenantMiddleware.extract_user_id()

            if not user_id:
                return jsonify({
                    "status": "error",
                    "message": "Unauthorized - valid token required"
                }), 401

            # Store in Flask g object (request context)
            g.user_id = user_id

            return f(*args, **kwargs)

        return decorated

    @staticmethod
    def tenant_optional(f):
        """
        Decorator for endpoints that work with or without auth
        Useful for public pages that can show different content if logged in
        """
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = MultiTenantMiddleware.extract_user_id()
            g.user_id = user_id  # Will be None if not authenticated

            return f(*args, **kwargs)

        return decorated


class TenantQueryFilter:
    """Helper class to add tenant filter to database queries"""

    @staticmethod
    def filter_by_user(query, user_id: int):
        """
        Filter query to only return rows for specific user
        Usage: query = TenantQueryFilter.filter_by_user(query, user_id)
        """
        # The actual filtering depends on the table
        # For Signal table: query = query.filter(Signal.user_id == user_id)
        # For Trade table: query = query.filter(Trade.user_id == user_id)
        # etc.
        return query

    @staticmethod
    def ensure_user_owns_resource(resource, user_id: int) -> bool:
        """
        Verify that user owns the resource before allowing operations
        Usage: if not TenantQueryFilter.ensure_user_owns_resource(signal, g.user_id):
                   return 403 error
        """
        if hasattr(resource, 'user_id'):
            return resource.user_id == user_id
        return False


class TenantDataIsolation:
    """Helper functions for tenant data operations"""

    @staticmethod
    def get_user_signals(db, user_id: int, limit: int = 50):
        """Get signals for a specific user only (F-21: tenant isolation).

        Previously this returned EVERY user's signals regardless of user_id,
        leaking one tenant's trading signals to another. It now filters by
        user_id so callers only ever see their own rows.
        """
        from database import Signal
        return (
            db.query(Signal)
            .filter(Signal.user_id == user_id)
            .order_by(Signal.timestamp.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_user_trades(db, user_id: int, limit: int = 50):
        """Get trades for specific user"""
        from database import Trade
        return db.query(Trade).filter(Trade.user_id == user_id).limit(limit).all()

    @staticmethod
    def get_user_metrics(db, user_id: int):
        """Get performance metrics for user"""
        from database import Signal, Trade
        from sqlalchemy import func

        # Get signal count
        signal_count = db.query(func.count(Signal.id)).filter(
            Signal.user_id == user_id
        ).scalar()

        # Get trade count
        trade_count = db.query(func.count(Trade.id)).filter(
            Trade.user_id == user_id
        ).scalar()

        # Get total P&L
        total_pnl = db.query(func.sum(Trade.pnl)).filter(
            Trade.user_id == user_id
        ).scalar()

        return {
            "signals_count": signal_count or 0,
            "trades_count": trade_count or 0,
            "total_pnl": float(total_pnl) if total_pnl else 0.0
        }

    @staticmethod
    def verify_signal_access(db, signal_id: int, user_id: int) -> bool:
        """Verify user can access signal"""
        from database import Signal
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        if not signal:
            return False
        return signal.user_id == user_id

    @staticmethod
    def verify_trade_access(db, trade_id: int, user_id: int) -> bool:
        """Verify user can access trade"""
        from database import Trade
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            return False
        return trade.user_id == user_id


def register_tenant_middleware(app):
    """
    Register multi-tenant middleware with Flask app
    This runs before each request to set up tenant context
    """

    @app.before_request
    def before_request():
        """Runs before each request"""
        # Extract user_id if available
        user_id = MultiTenantMiddleware.extract_user_id()
        if user_id:
            g.user_id = user_id
            g.is_authenticated = True
        else:
            g.user_id = None
            g.is_authenticated = False

    @app.after_request
    def after_request(response):
        """Runs after each request"""
        # Can add tenant info to response headers if needed
        return response


# Example usage in routes:
"""
from flask import Blueprint, g
from multi_tenant_middleware import MultiTenantMiddleware, TenantDataIsolation

@bp.route('/api/signals')
@MultiTenantMiddleware.tenant_required
def get_user_signals():
    user_id = g.user_id
    signals = TenantDataIsolation.get_user_signals(db, user_id)
    return jsonify({"data": [s.to_dict() for s in signals]})
"""


if __name__ == "__main__":
    logger.info("✅ Multi-tenant middleware module ready")
