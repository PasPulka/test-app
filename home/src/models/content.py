from .user import db # Assuming db is initialized in user.py or a shared models.py
from datetime import datetime

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content_type = db.Column(db.String(50), nullable=False)  # e.g., "video", "image", "text"
    # For text content, store directly. For files, store URL/path.
    text_content = db.Column(db.Text, nullable=True)
    file_url = db.Column(db.String(255), nullable=True) # For video/image uploads
    access_setting = db.Column(db.String(50), nullable=False, default="free")  # "free" or "paywall"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    coach = db.relationship("User", backref=db.backref("contents", lazy=True))

    def __repr__(self):
        return f"<Content {self.id} - {self.title} by Coach {self.coach_id}>"
