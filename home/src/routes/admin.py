from flask import Blueprint, request, jsonify, current_app
from src.models.user import User, db
from src.models.content import Content
from src.models.monetization import Subscription, PayPerViewPurchase
from src.models.finance import Transaction, Payout # Import finance models
from werkzeug.security import generate_password_hash
from datetime import datetime

admin_bp = Blueprint("admin", __name__)

# Basic authentication for admin routes (decorator)
# In a real app, use a robust authentication mechanism (e.g., Flask-Login, roles)
def admin_required(f):
    def decorated_function(*args, **kwargs):
        # Placeholder for admin check. Replace with actual admin user check.
        # For now, let's assume an API key or a specific user ID for simplicity.
        auth_header = request.headers.get("X-Admin-Auth")
        if auth_header != "SUPER_SECRET_ADMIN_KEY": # Replace with a secure check
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__ # Preserve original function name for Flask
    return decorated_function

@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    users = User.query.all()
    user_list = []
    for user in users:
        user_list.append({
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "profile_picture_url": user.profile_picture_url
        })
    return jsonify(user_list), 200

@admin_bp.route("/user/<int:user_id>", methods=["GET"])
@admin_required
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "profile_picture_url": user.profile_picture_url,
        "bio": user.bio
    }), 200

@admin_bp.route("/content", methods=["GET"])
@admin_required
def list_all_content():
    content_items = Content.query.order_by(Content.created_at.desc()).all()
    content_list = []
    for item in content_items:
        content_list.append({
            "id": item.id,
            "coach_id": item.coach_id,
            "title": item.title,
            "content_type": item.content_type,
            "access_setting": item.access_setting,
            "created_at": item.created_at.isoformat()
        })
    return jsonify(content_list), 200

@admin_bp.route("/content/<int:content_id>", methods=["DELETE"])
@admin_required
def delete_content(content_id):
    content_item = Content.query.get_or_404(content_id)
    # Potentially add more checks, e.g., soft delete or archiving
    db.session.delete(content_item)
    db.session.commit()
    return jsonify({"message": f"Content item {content_id} deleted"}), 200

@admin_bp.route("/transactions", methods=["GET"])
@admin_required
def list_transactions():
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
    transaction_list = []
    for t in transactions:
        transaction_list.append({
            "id": t.id,
            "transaction_type": t.transaction_type,
            "user_id": t.user_id,
            "coach_id": t.coach_id,
            "content_id": t.content_id,
            "amount": t.amount,
            "platform_fee": t.platform_fee,
            "net_amount": t.net_amount,
            "currency": t.currency,
            "stripe_payment_intent_id": t.stripe_payment_intent_id,
            "status": t.status,
            "created_at": t.created_at.isoformat()
        })
    return jsonify(transaction_list), 200

@admin_bp.route("/payouts", methods=["GET"])
@admin_required
def list_payouts():
    payouts = Payout.query.order_by(Payout.requested_at.desc()).all()
    payout_list = []
    for p in payouts:
        payout_list.append({
            "id": p.id,
            "coach_id": p.coach_id,
            "amount": p.amount,
            "currency": p.currency,
            "status": p.status,
            "requested_at": p.requested_at.isoformat(),
            "processed_at": p.processed_at.isoformat() if p.processed_at else None,
            "stripe_transfer_id": p.stripe_transfer_id
        })
    return jsonify(payout_list), 200

# Placeholder for initiating/managing payouts - more complex with Stripe Connect
@admin_bp.route("/payouts/process/<int:payout_id>", methods=["POST"])
@admin_required
def process_payout(payout_id):
    payout = Payout.query.get_or_404(payout_id)
    if payout.status != "pending":
        return jsonify({"error": "Payout not in pending state"}), 400

    # TODO: Integrate with Stripe Connect to create a Transfer to the coach's connected account
    # This is a simplified placeholder for MVP
    payout.status = "processing" # Or "completed" if direct
    payout.processed_at = datetime.utcnow()
    # payout.stripe_transfer_id = "simulated_transfer_id_" + str(payout.id) # Simulate Stripe transfer ID
    db.session.commit()
    return jsonify({"message": f"Payout {payout_id} marked as processing/completed", "payout_status": payout.status}), 200

# Endpoint to configure platform fee (example)
@admin_bp.route("/config/platform_fee", methods=["POST"])
@admin_required
def set_platform_fee():
    data = request.get_json()
    fee_percentage = data.get("fee_percentage")
    if fee_percentage is None or not (0 <= fee_percentage <= 100):
        return jsonify({"error": "Invalid fee percentage. Must be between 0 and 100."}), 400
    
    # In a real app, store this in a config file or database setting
    # For now, we can update a global app config or a dedicated settings model
    current_app.config["PLATFORM_FEE_PERCENTAGE"] = float(fee_percentage)
    return jsonify({"message": f"Platform fee set to {fee_percentage}%"}), 200

