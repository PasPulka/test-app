from flask import Blueprint, request, jsonify
from src.models.user import User, db
from src.models.content import Content
from src.models.monetization import Subscription, PayPerViewPurchase # Import monetization models
from datetime import datetime
import os
from werkzeug.utils import secure_filename

# Configure a directory for uploads
# In a production environment, this should be an absolute path and ideally cloud storage.
# For simplicity in the template, it defaults to a relative path.
# Ensure this path is secure and appropriate for your deployment.
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads") 
if not os.path.exists(UPLOAD_FOLDER):
    try:
        os.makedirs(UPLOAD_FOLDER)
    except OSError as e:
        # Handle error if directory creation fails, e.g., log it or raise an exception
        print(f"Error creating upload folder: {e}")

ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "mp4", "mov", "avi"}

content_bp = Blueprint("content", __name__)

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to check access (can be expanded and moved to a utils module)
def has_access_to_content(fan_id, content_id):
    content = Content.query.get(content_id)
    if not content:
        return False, "Content not found"

    if content.access_setting == "free":
        return True, "Content is free"

    if not fan_id:
        return False, "User not identified for paid content"
        
    fan = User.query.get(fan_id)
    if not fan:
        return False, "Fan not found"

    # Check for active subscription to the coach who owns the content
    active_subscription = Subscription.query.filter_by(
        fan_id=fan_id,
        coach_id=content.coach_id,
        is_active=True
    ).filter(Subscription.end_date > datetime.utcnow()).first()

    if active_subscription:
        return True, "Active subscription to coach"

    # Check for pay-per-view purchase
    purchase = PayPerViewPurchase.query.filter_by(fan_id=fan_id, content_id=content_id).first()
    if purchase:
        return True, "Content purchased (pay-per-view)"

    return False, "No active subscription or purchase"

@content_bp.route("/upload", methods=["POST"])
def upload_content():
    # TODO: Implement proper authentication to get coach_id from session/token
    coach_id = request.form.get("coach_id") 
    if not coach_id:
        return jsonify({"error": "Coach ID is required"}), 400
    
    coach = User.query.get(coach_id)
    if not coach or coach.role != "coach":
        return jsonify({"error": "Invalid coach ID or user is not a coach"}), 403

    title = request.form.get("title")
    description = request.form.get("description")
    content_type = request.form.get("content_type") # "text", "image", "video"
    access_setting = request.form.get("access_setting", "free") # "free" or "paywall"

    if not all([title, content_type]):
        return jsonify({"error": "Title and content type are required"}), 400
    
    if access_setting not in ["free", "paywall"]:
        return jsonify({"error": "Invalid access setting. Must be 'free' or 'paywall'."}), 400

    new_content = Content(
        coach_id=coach_id,
        title=title,
        description=description,
        content_type=content_type,
        access_setting=access_setting
    )

    if content_type == "text":
        text_content = request.form.get("text_content")
        if not text_content:
            return jsonify({"error": "Text content is required for text type"}), 400
        new_content.text_content = text_content
    elif content_type in ["image", "video"]:
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            try:
                file.save(file_path)
                new_content.file_url = file_path 
            except Exception as e:
                 return jsonify({"error": f"Could not save file: {e}"}), 500
        else:
            return jsonify({"error": "File type not allowed"}), 400
    else:
        return jsonify({"error": "Invalid content type"}), 400

    db.session.add(new_content)
    db.session.commit()

    return jsonify({"message": "Content uploaded successfully", "content_id": new_content.id}), 201

@content_bp.route("/<int:content_id>", methods=["GET"])
def get_content(content_id):
    # TODO: Implement proper authentication to get fan_id from session/token
    # For now, expecting fan_id as a query parameter for testing access control
    fan_id = request.args.get("fan_id", type=int) 

    content = Content.query.get_or_404(content_id)

    can_access, reason = has_access_to_content(fan_id, content_id)

    if not can_access:
        return jsonify({"error": "Access denied", "reason": reason}), 403

    content_data = {
        "id": content.id,
        "coach_id": content.coach_id,
        "title": content.title,
        "description": content.description,
        "content_type": content.content_type,
        "access_setting": content.access_setting,
        "created_at": content.created_at.isoformat()
    }
    # Only include text_content or file_url if access is granted and content type matches
    if content.content_type == "text":
        content_data["text_content"] = content.text_content
    elif content.file_url:
        content_data["file_url"] = content.file_url # In a real app, this might be a signed URL
        
    return jsonify(content_data), 200

@content_bp.route("/coach/<int:coach_id>", methods=["GET"])
def get_coach_content(coach_id):
    coach = User.query.get_or_404(coach_id)
    if coach.role != "coach":
         return jsonify({"error": "User is not a coach"}), 403

    # TODO: Potentially filter content list based on fan's access if fan_id is provided
    contents = Content.query.filter_by(coach_id=coach_id).order_by(Content.created_at.desc()).all()
    content_list = []
    for content_item in contents:
        content_list.append({
            "id": content_item.id,
            "title": content_item.title,
            "content_type": content_item.content_type,
            "access_setting": content_item.access_setting,
            "description": content_item.description, # Adding description to the list view
            "created_at": content_item.created_at.isoformat()
        })
    return jsonify(content_list), 200

