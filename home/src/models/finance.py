from .user import db
from datetime import datetime

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_type = db.Column(db.String(50), nullable=False)  # e.g., "subscription_payment", "ppv_purchase", "payout", "platform_fee"
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True) # Fan or Coach, depending on transaction
    coach_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True) # Coach involved, if applicable
    content_id = db.Column(db.Integer, db.ForeignKey("content.id"), nullable=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscription.id"), nullable=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey("pay_per_view_purchase.id"), nullable=True)
    amount = db.Column(db.Float, nullable=False)  # Gross amount of the transaction
    platform_fee = db.Column(db.Float, nullable=True, default=0.0)
    net_amount = db.Column(db.Float, nullable=True) # Amount after platform fee, relevant for coach earnings
    currency = db.Column(db.String(10), nullable=False, default="usd")
    stripe_payment_intent_id = db.Column(db.String(255), nullable=True, unique=True)
    status = db.Column(db.String(50), nullable=False, default="pending") # e.g., "pending", "succeeded", "failed", "refunded"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (optional, but can be useful)
    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("transactions_as_user", lazy="dynamic"))
    coach_involved = db.relationship("User", foreign_keys=[coach_id], backref=db.backref("transactions_as_coach", lazy="dynamic"))
    content_item = db.relationship("Content", backref=db.backref("transactions", lazy="dynamic"))
    # Add relationships for subscription and purchase if needed for easier querying

    def __repr__(self):
        return f"<Transaction {self.id} - Type: {self.transaction_type}, Amount: {self.amount} {self.currency}, Status: {self.status}>"

class Payout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="usd")
    status = db.Column(db.String(50), nullable=False, default="pending") # e.g., "pending", "processing", "completed", "failed"
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    stripe_transfer_id = db.Column(db.String(255), nullable=True, unique=True)
    # Potentially link to transactions included in this payout

    coach = db.relationship("User", backref=db.backref("payouts_received", lazy="dynamic"))

    def __repr__(self):
        return f"<Payout {self.id} - Coach {self.coach_id}, Amount: {self.amount} {self.currency}, Status: {self.status}>"

