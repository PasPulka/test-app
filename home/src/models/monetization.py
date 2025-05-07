from .user import db # Assuming db is initialized in user.py or a shared models.py
from datetime import datetime, timedelta

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fan_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    coach_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    subscription_type = db.Column(db.String(50), nullable=False)  # e.g., "monthly", "yearly"
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    fan = db.relationship("User", foreign_keys=[fan_id], backref=db.backref("subscriptions_made", lazy=True))
    coach = db.relationship("User", foreign_keys=[coach_id], backref=db.backref("subscribers", lazy=True))

    def __repr__(self):
        return f"<Subscription {self.id}: Fan {self.fan_id} to Coach {self.coach_id}>"

class PayPerViewPurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fan_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey("content.id"), nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount_paid = db.Column(db.Float, nullable=False) # Store the amount paid at the time of purchase

    fan = db.relationship("User", backref=db.backref("purchased_content_items", lazy=True))
    content = db.relationship("Content", backref=db.backref("purchases", lazy=True))

    def __repr__(self):
        return f"<PayPerViewPurchase {self.id}: Fan {self.fan_id} bought Content {self.content_id}>"

