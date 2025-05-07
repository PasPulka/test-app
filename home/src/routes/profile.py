from flask import Blueprint, request, jsonify
from src.models.user import User, db
# We might need to add authentication checks later (e.g., using Flask-Login or JWT)

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/<int:user_id>", methods=["GET"])
def get_profile(user_id):
    user = User.query.get_or_404(user_id)
    # For MVP, we return basic info. This can be expanded.
    profile_data = {
        "id": user.id,
        "email": user.email, # May want to hide this depending on privacy settings
        "username": user.username,
        "role": user.role,
        "profile_picture_url": user.profile_picture_url,
        "bio": user.bio
    }
    return jsonify(profile_data), 200

@profile_bp.route("/<int:user_id>", methods=["PUT"])
def update_profile(user_id):
    # Add authentication here to ensure only the user themselves can update their profile
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Update fields if they are provided in the request
    if "username" in data:
        # Check for username uniqueness if it's being changed or set
        existing_user = User.query.filter(User.username == data["username"], User.id != user_id).first()
        if existing_user:
            return jsonify({"error": "Username already taken"}), 400
        user.username = data["username"]
    if "profile_picture_url" in data:
        user.profile_picture_url = data["profile_picture_url"]
    if "bio" in data:
        user.bio = data["bio"]
    
    db.session.commit()
    return jsonify({"message": "Profile updated successfully"}), 200

