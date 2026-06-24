"""
Billing Routes - Subscription management and Stripe integration
"""

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


@billing_bp.route('/plans', methods=['GET'])
def get_plans():
    """Get available subscription plans"""
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
                "priority_support": details["priority_support"]
            })

        return APIResponse.success({"plans": plans, "count": len(plans)})

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@billing_bp.route('/subscription', methods=['GET'])
@MultiTenantMiddleware.tenant_required
def get_subscription():
    """Get current user subscription"""
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
    """Upgrade subscription plan"""
    try:
        user_id = g.user_id
        data = request.get_json()

        if not data or "plan_tier" not in data:
            return APIResponse.bad_request("Plan tier required")

        plan_tier = data.get("plan_tier").lower()

        if plan_tier not in SUBSCRIPTION_TIERS:
            return APIResponse.bad_request(f"Invalid plan tier. Available: {list(SUBSCRIPTION_TIERS.keys())}")

        db = SessionLocal()
        user = get_user_by_id(db, user_id)

        if not user:
            db.close()
            return APIResponse.not_found("User not found")

        subscription = upgrade_subscription(db, user_id, plan_tier)
        db.close()

        return APIResponse.success(subscription.to_dict())

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@billing_bp.route('/downgrade', methods=['POST'])
@MultiTenantMiddleware.tenant_required
def downgrade_plan():
    """Downgrade subscription plan"""
    try:
        user_id = g.user_id
        data = request.get_json()

        if not data or "plan_tier" not in data:
            return APIResponse.bad_request("Plan tier required")

        plan_tier = data.get("plan_tier").lower()

        db = SessionLocal()
        subscription = upgrade_subscription(db, user_id, plan_tier)
        db.close()

        return APIResponse.success(subscription.to_dict())

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@billing_bp.route('/cancel', methods=['POST'])
@MultiTenantMiddleware.tenant_required
def cancel_subscription():
    """Cancel subscription"""
    try:
        user_id = g.user_id
        db = SessionLocal()

        subscription = get_user_subscription(db, user_id)
        if not subscription:
            db.close()
            return APIResponse.not_found("No subscription found")

        subscription.status = "canceled"
        subscription.canceled_at = datetime.utcnow()
        subscription.auto_renew = False
        db.commit()
        db.close()

        return APIResponse.success({"message": "Subscription canceled"})

    except Exception as e:
        return APIResponse.server_error(str(e), e)


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


@billing_bp.route('/create-payment-intent', methods=['POST'])
@MultiTenantMiddleware.tenant_required
def create_payment_intent():
    """Create Stripe payment intent"""
    try:
        user_id = g.user_id
        data = request.get_json()

        if not data or "amount" not in data:
            return APIResponse.bad_request("Amount required")

        amount = data.get("amount", 0)
        if amount <= 0:
            return APIResponse.bad_request("Invalid amount")

        try:
            import stripe
            stripe.api_key = os.getenv("STRIPE_API_KEY")

            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency="inr",
                metadata={"user_id": user_id}
            )

            return APIResponse.success({
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id
            })

        except Exception as e:
            return APIResponse.server_error(f"Payment processing error: {str(e)}", e)

    except Exception as e:
        return APIResponse.server_error(str(e), e)


if __name__ == "__main__":
    print("✅ Billing routes module ready")
