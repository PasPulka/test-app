from flask import Blueprint, request, jsonify, current_app
from src.models.user import User, db
from src.models.content import Content
from src.models.monetization import Subscription, PayPerViewPurchase
from src.models.finance import Transaction # Import Transaction model
from datetime import datetime, timedelta
import stripe

monetization_bp = Blueprint("monetization", __name__)

def calculate_order_amount(item_id, item_type):
    if item_type == "subscription_monthly":
        return 1000 # 10.00 USD in cents
    elif item_type == "subscription_yearly":
        return 10000 # 100.00 USD in cents
    elif item_type == "content_ppv":
        # In a real app, fetch price from DB based on content_id
        # For now, using a fixed price for PPV content for calculation
        content = Content.query.get(item_id)
        if content: # Assuming a price attribute or a fixed price for demo
            return 500 # 5.00 USD in cents
    return 0

@monetization_bp.route("/create_payment_intent", methods=["POST"])
def create_payment():
    try:
        data = request.get_json()
        item_id = data.get("item_id")
        item_type = data.get("item_type")
        currency = data.get("currency", "usd")
        # fan_id should be retrieved from authenticated session/token in a real app
        fan_id = data.get("fan_id") # For metadata

        if not all([item_id, item_type, fan_id]):
            return jsonify(error="Missing item_id, item_type, or fan_id"), 400

        amount = calculate_order_amount(item_id, item_type)
        if amount == 0:
            return jsonify(error="Invalid item_type or item_id for amount calculation"), 400

        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            automatic_payment_methods={"enabled": True},
            metadata={
                "item_id": str(item_id), # Ensure it's a string for Stripe metadata
                "item_type": item_type,
                "user_id": str(fan_id) # Fan's ID
            }
        )
        return jsonify({
            "clientSecret": intent.client_secret
        })
    except Exception as e:
        return jsonify(error=str(e)), 403

@monetization_bp.route("/subscribe", methods=["POST"])
def subscribe_to_coach():
    data = request.get_json()
    fan_id = data.get("fan_id") 
    coach_id = data.get("coach_id")
    subscription_type = data.get("subscription_type")
    payment_intent_id = data.get("payment_intent_id") # Client should send this after successful payment confirmation

    if not all([fan_id, coach_id, subscription_type, payment_intent_id]):
        return jsonify({"error": "Fan ID, Coach ID, subscription type, and payment_intent_id are required"}), 400

    fan = User.query.get(fan_id)
    coach = User.query.get(coach_id)
    if not fan or fan.role != "fan": return jsonify({"error": "Invalid fan"}), 403
    if not coach or coach.role != "coach": return jsonify({"error": "Invalid coach"}), 403

    # Verify payment intent status with Stripe (important for security)
    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        if payment_intent.status != "succeeded":
            return jsonify({"error": "Payment not successful or still processing"}), 402
        # Further check if amount and currency match expected values for the subscription
    except stripe.error.StripeError as e:
        return jsonify({"error": f"Stripe error: {str(e)}"}), 500

    existing_subscription = Subscription.query.filter_by(fan_id=fan_id, coach_id=coach_id, is_active=True).first()
    if existing_subscription and existing_subscription.end_date > datetime.utcnow():
        return jsonify({"message": "Already subscribed and active"}), 200
    if existing_subscription:
        existing_subscription.is_active = False # Deactivate old one before creating new

    if subscription_type == "monthly":
        end_date = datetime.utcnow() + timedelta(days=30)
    elif subscription_type == "yearly":
        end_date = datetime.utcnow() + timedelta(days=365)
    else:
        return jsonify({"error": "Invalid subscription type"}), 400
    
    new_subscription = Subscription(
        fan_id=fan_id, coach_id=coach_id, subscription_type=subscription_type,
        end_date=end_date, is_active=True
    )
    db.session.add(new_subscription)
    # Transaction record is now handled by webhook
    db.session.commit()
    return jsonify({"message": "Subscription successful", "subscription_id": new_subscription.id}), 201

@monetization_bp.route("/purchase_content", methods=["POST"])
def purchase_content_item():
    data = request.get_json()
    fan_id = data.get("fan_id")
    content_id = data.get("content_id")
    payment_intent_id = data.get("payment_intent_id")

    if not all([fan_id, content_id, payment_intent_id]):
        return jsonify({"error": "Fan ID, Content ID, and payment_intent_id are required"}), 400

    fan = User.query.get(fan_id)
    content = Content.query.get(content_id)
    if not fan or fan.role != "fan": return jsonify({"error": "Invalid fan"}), 403
    if not content: return jsonify({"error": "Content not found"}), 404

    if content.access_setting != "paywall":
        return jsonify({"error": "Content not for individual purchase or access already granted"}), 400

    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        if payment_intent.status != "succeeded":
            return jsonify({"error": "Payment not successful or still processing"}), 402
    except stripe.error.StripeError as e:
        return jsonify({"error": f"Stripe error: {str(e)}"}), 500

    existing_purchase = PayPerViewPurchase.query.filter_by(fan_id=fan_id, content_id=content_id).first()
    if existing_purchase:
        return jsonify({"message": "Content already purchased"}), 200

    amount_for_item = payment_intent.amount / 100.0 # Amount from successful PI

    new_purchase = PayPerViewPurchase(
        fan_id=fan_id, content_id=content_id, amount_paid=amount_for_item
    )
    db.session.add(new_purchase)
    # Transaction record is now handled by webhook
    db.session.commit()
    return jsonify({"message": "Content purchased successfully", "purchase_id": new_purchase.id}), 201

@monetization_bp.route("/stripe_webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    endpoint_secret = current_app.config["STRIPE_WEBHOOK_SECRET"]
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e: return jsonify(error=str(e)), 400
    except stripe.error.SignatureVerificationError as e: return jsonify(error=str(e)), 400

    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object
        metadata = payment_intent.metadata
        item_id = metadata.get("item_id")
        item_type = metadata.get("item_type")
        fan_id = metadata.get("user_id") # This is the fan's ID
        
        gross_amount = payment_intent.amount / 100.0 # Convert from cents
        platform_fee_percentage = current_app.config.get("PLATFORM_FEE_PERCENTAGE", 15.0) / 100.0
        platform_fee_amount = gross_amount * platform_fee_percentage
        net_amount_for_coach = gross_amount - platform_fee_amount

        coach_id_for_transaction = None
        content_id_for_transaction = None
        subscription_id_for_transaction = None
        purchase_id_for_transaction = None
        transaction_type_str = "unknown_payment"

        if item_type in ["subscription_monthly", "subscription_yearly"]:
            coach_id_for_transaction = item_id # item_id is coach_id for subscriptions
            transaction_type_str = "subscription_payment"
            # Find the subscription to link it, if needed, though this webhook is the source of truth for payment
            # sub = Subscription.query.filter_by(fan_id=fan_id, coach_id=coach_id_for_transaction, is_active=True).order_by(Subscription.start_date.desc()).first()
            # if sub: subscription_id_for_transaction = sub.id

        elif item_type == "content_ppv":
            content_id_for_transaction = item_id # item_id is content_id for PPV
            content_item = Content.query.get(content_id_for_transaction)
            if content_item:
                coach_id_for_transaction = content_item.coach_id
            transaction_type_str = "ppv_purchase"
            # Find the purchase to link it
            # ppv = PayPerViewPurchase.query.filter_by(fan_id=fan_id, content_id=content_id_for_transaction).first()
            # if ppv: purchase_id_for_transaction = ppv.id

        # Create Transaction record
        transaction = Transaction(
            transaction_type=transaction_type_str,
            user_id=fan_id,
            coach_id=coach_id_for_transaction,
            content_id=content_id_for_transaction,
            # subscription_id=subscription_id_for_transaction, # Link if found
            # purchase_id=purchase_id_for_transaction, # Link if found
            amount=gross_amount,
            platform_fee=platform_fee_amount,
            net_amount=net_amount_for_coach,
            currency=payment_intent.currency,
            stripe_payment_intent_id=payment_intent.id,
            status="succeeded"
        )
        db.session.add(transaction)
        db.session.commit()

    elif event.type == "payment_method.attached":
        pass # payment_method = event.data.object
    else:
        print(f"Unhandled event type {event.type}")

    return jsonify(success=True), 200

@monetization_bp.route("/check_access/<int:fan_id>/<int:content_id>", methods=["GET"])
def check_content_access(fan_id, content_id):
    fan = User.query.get_or_404(fan_id)
    content = Content.query.get_or_404(content_id)

    if content.access_setting == "free":
        return jsonify({"access": True, "reason": "Content is free"}), 200

    active_subscription = Subscription.query.filter_by(
        fan_id=fan_id,
        coach_id=content.coach_id,
        is_active=True
    ).filter(Subscription.end_date > datetime.utcnow()).first()

    if active_subscription:
        return jsonify({"access": True, "reason": "Active subscription to coach"}), 200

    purchase = PayPerViewPurchase.query.filter_by(fan_id=fan_id, content_id=content_id).first()
    if purchase:
        return jsonify({"access": True, "reason": "Content purchased (pay-per-view)"}), 200

    return jsonify({"access": False, "reason": "No active subscription or purchase"}), 403

