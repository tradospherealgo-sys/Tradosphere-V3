"""
Leads Routes - CRM and client management endpoints
Track signups, conversions, and client metrics
"""
import logging
logger = logging.getLogger(__name__)


from flask import Blueprint, request, jsonify, g
from datetime import datetime
from leads_model import (
    SessionLocal, create_lead, get_lead_by_email, convert_lead_to_customer,
    get_all_leads, get_all_clients, get_leads_stats, get_clients_stats
)
from multi_tenant_middleware import MultiTenantMiddleware
from auth_manager import AuthDecorator

leads_bp = Blueprint('leads', __name__, url_prefix='/api/leads')


@leads_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get leads and clients statistics (public)"""
    try:
        db = SessionLocal()
        leads_stats = get_leads_stats(db)
        clients_stats = get_clients_stats(db)
        db.close()

        return jsonify({
            "status": "success",
            "data": {
                "leads": leads_stats,
                "clients": clients_stats
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@leads_bp.route('/track-signup', methods=['POST'])
def track_signup():
    """Track a new signup (creates lead)"""
    try:
        data = request.get_json()

        if not data or "email" not in data:
            return jsonify({
                "status": "error",
                "message": "Email required"
            }), 400

        email = data.get("email", "").strip().lower()
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        source = data.get("source", "organic")

        db = SessionLocal()

        # Check if lead already exists
        existing_lead = get_lead_by_email(db, email)
        if existing_lead:
            db.close()
            return jsonify({
                "status": "info",
                "message": "Lead already exists",
                "data": existing_lead.to_dict()
            }), 200

        # Create new lead
        lead = create_lead(db, email, first_name, last_name, source)
        db.close()

        return jsonify({
            "status": "success",
            "message": "Lead created",
            "data": lead.to_dict()
        }), 201

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@leads_bp.route('/convert', methods=['POST'])
@MultiTenantMiddleware.tenant_required
def convert_to_customer():
    """Convert lead to customer after signup"""
    try:
        user_id = g.user_id
        data = request.get_json()

        if not data or "email" not in data:
            return jsonify({
                "status": "error",
                "message": "Email required"
            }), 400

        email = data.get("email", "").strip().lower()
        tier = data.get("tier", "free")

        db = SessionLocal()
        lead = convert_lead_to_customer(db, email, user_id, tier)
        db.close()

        if lead:
            return jsonify({
                "status": "success",
                "message": f"Lead converted to {tier} customer",
                "data": lead.to_dict()
            }), 200

        return jsonify({
            "status": "error",
            "message": "Lead not found"
        }), 404

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    logger.info("✅ Leads routes module ready")
