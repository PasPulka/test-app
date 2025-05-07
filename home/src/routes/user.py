from flask import Blueprint, request, jsonify
from src.models.user import User, db

user_bp = Blueprint("user", __name__)

@user_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password are required"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email address already registered"}), 400

    new_user = User(email=data["email"], role=data.get("role", "fan")) # Default role to fan if not specified
    new_user.set_password(data["password"])
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

@user_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=data["email"]).first()

    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401
    
    # In a real application, you would generate and return a JWT token here
    # For MVP, we'll just return a success message
    return jsonify({"message": "Login successful", "user_id": user.id, "role": user.role}), 200

