"""
Billing Routes - Subscription tiers (payments COMING SOON)

Product decision: paid subscriptions and online payments are not yet launched.
Stripe has been removed entirely (F-03 / F-14 / F-17). The plan catalogue is
still served so the frontend can render a "Coming soon" pricing page, but no
money ever changes hands and every account has full access. Any endpoint that
would previously have charged or upgraded a paying customer now returns a
'coming_soon' response instead of performing a billing mutation.
"""
import logging
logger = logging.getLogger(__name__)


from flask import Blueprint, request, g
from datetime import datetime, timedelta
from subscription_model import (
    SessionLocal, get_user_subscription, create_subscription, upgrade_subscription,
    get_user_usage, get_user_invoices, SUBSCRIPTION_TIERS, init_subscription_db
)
from user_model_v3_1 import get_user_by_id
from multi_tenant_middleware import MultiTenantMiddleware
from response_handler import APIResponse
import os

billing_bp = Blueprint('billing', __name__, url_prefix='/api/billing')

init_subscription_db()

# Single source of truth for the "payments not live yet" state.
PAYMENTS_AVAILABLE = False
COMING_SOON_MESSAGE = (
    "Paid plans are coming soon. Your account currently has full access at no "
    "charge — there is nothing to purchase yet."
)


def _coming_soon():
    """Standard response for any endpoint that would have taken a payment."""
    return APIResponse.success({
        "status": "coming_soon",
        "available": False,
        "message": COMING_SOON_MESSAGE,
    })


@billing_bp.route('/plans', methods=['GET'])
def get_plans():
    """Get available subscription plans (marked coming soon)."""
    try:
        plans = []
        for tier, details in SUBSCRIPTION_TIERS.items():
            plans.append({
                "tier": tier,
                "name": details["name"],
                "monthly_price": details["price"],
                "annual_price": details["price"] * 10,
                "signals_limit": details["signals_per_month"],
                "api_calls_limit": details["api_calls_per_day"],
                "brokers_supported": details["brokers_supported"],
                "features": details["features"],
                "priority_support": details["priority_support"],
                # The UI uses these flags to render a disabled "Coming soon" CTA.
                "available": False,
                "status": "coming_soon",
            })

        return APIResponse.success({
            "plans": plans,
            "count": len(plans),
            "payments_available": PAYMENTS_AVAILABLE,
            "message": COMING_SOON_MESSAGE,
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@billing_bp.route('/subscription', methods=['GET'])
@MultiTenantMiddleware.tenant_required
def get_subscription():
    """Get current user subscription (read-only, always available)."""
    try:
        user_id = g.user_id
        db = SessionLocal()

        subscription = get_user_subscription(db, user_id)
        db.close()

        if not subscription:
            return APIResponse.not_found("No subscription found")

        sub_dict = subscription.to_dict()
        sub_dict["is_active"] = subscription.is_active()
        sub_dict["days_remaining"] = subscription.days_remaining()

        return APIResponse.success(sub_dict)

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@billing_bp.route('/upgrade', methods=['POST'])
@MultiTenantMiddleware.tenant_required
def upgrade_plan():
    """Upgrade subscription plan — disabled while payments are coming soon."""
    return _coming_soon()


@billing_bp.route('/downgrade', methods=['POST'])
@MultiTenantMiddleware.tenant_required
def downgrade_plan():
    """Downgrade subscription plan — disabled while payments are coming soon."""
    return _coming_soon()


@billing_bp.route('/cancel', methods=['POST'])
@MultiTenantMiddleware.tenant_required
def cancel_subscription():
    """Cancel subscription — nothing to cancel while payments are coming soon."""
    return _coming_soon()


@billing_bp.route('/create-payment-intent', methods=['POST'])
@MultiTenantMiddleware.tenant_required
def create_payment_intent():
    """Payment processing is not available yet (Stripe removed)."""
    return _coming_soon()


@billing_bp.route('/usage', methods=['GET'])
@MultiTenantMiddleware.tenant_required
def get_usage():
    """Get current month usage"""
    try:
        user_id = g.user_id
        db = SessionLocal()

        subscription = get_user_subscription(db, user_id)
        if not subscription:
            db.close()
            return APIResponse.not_found("No subscription found")

        usage = get_user_usage(db, user_id)
        plan = SUBSCRIPTION_TIERS.get(subscription.plan.tier if subscription.plan else "free")

        db.close()

        return APIResponse.success({
            "current_plan": subscription.plan.tier if subscription.plan else "free",
            "signals_generated": usage.signals_generated if usage else 0,
            "signals_limit": plan["signals_per_month"],
            "api_calls": usage.api_calls if usage else 0,
            "api_calls_limit": plan["api_calls_per_day"] * 30,
            "brokers_connected": usage.brokers_connected if usage else 0,
            "brokers_supported": plan["brokers_supported"],
            "usage_percentage": {
                "signals": int((usage.signals_generated if usage else 0) / plan["signals_per_month"] * 100),
                "api_calls": int((usage.api_calls if usage else 0) / (plan["api_calls_per_day"] * 30) * 100)
            }
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@billing_bp.route('/invoices', methods=['GET'])
@MultiTenantMiddleware.tenant_required
def list_invoices():
    """Get user invoices"""
    try:
        user_id = g.user_id
        limit = request.args.get('limit', 20, type=int)

        db = SessionLocal()
        invoices = get_user_invoices(db, user_id, limit)
        db.close()

        return APIResponse.success({
            "invoices": [inv.to_dict() for inv in invoices],
            "count": len(invoices)
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


if __name__ == "__main__":
    logger.info("✅ Billing routes module ready (payments coming soon)")
