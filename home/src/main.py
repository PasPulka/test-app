import os
import sys
import stripe # Import stripe

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, logging, request # Import logging
from src.models.user import db 
from src.routes.user import user_bp
from src.routes.profile import profile_bp
from src.routes.content import content_bp
from src.routes.monetization import monetization_bp
from src.routes.admin import admin_bp # Import the admin blueprint

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Add basic logging
if not app.debug:
    import logging
    file_handler = logging.FileHandler('/home/ubuntu/flask_production.log')
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)

# Configure upload folder for content
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "uploads") 

# Stripe Configuration - Replace with your actual keys in a secure way (e.g., environment variables)
app.config['STRIPE_PUBLIC_KEY'] = os.getenv('STRIPE_PUBLIC_KEY', 'pk_test_YOUR_STRIPE_PUBLIC_KEY')
app.config['STRIPE_SECRET_KEY'] = os.getenv('STRIPE_SECRET_KEY', 'sk_test_YOUR_STRIPE_SECRET_KEY')
app.config['STRIPE_WEBHOOK_SECRET'] = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_YOUR_WEBHOOK_SECRET')
stripe.api_key = app.config['STRIPE_SECRET_KEY']

# Platform Fee Configuration (default to 15%)
app.config['PLATFORM_FEE_PERCENTAGE'] = float(os.getenv('PLATFORM_FEE_PERCENTAGE', 15.0))

app.register_blueprint(user_bp, url_prefix='/api/user')
app.register_blueprint(profile_bp, url_prefix='/api/profile')
app.register_blueprint(content_bp, url_prefix='/api/content')
app.register_blueprint(monetization_bp, url_prefix='/api/monetization')
app.register_blueprint(admin_bp, url_prefix='/api/admin') # Register admin blueprint

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USERNAME', 'root')}:{os.getenv('DB_PASSWORD', 'password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'mydb')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True # Enable SQLAlchemy logging
db.init_app(app)

# Test: Comment out db.create_all() to see if it's the blocking call
with app.app_context():
    app.logger.info("Attempting to create database tables...")
    db.create_all()
    app.logger.info("Database tables created (or already exist).")

@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())

@app.after_request
def log_response_info(response):
    app.logger.debug('Response: %s', response.get_data())
    return response

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

if __name__ == '__main__':
    # Ensure the logger is configured for debug level if app.debug is True
    if app.debug:
        app.logger.setLevel(logging.DEBUG)
    app.logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False) # use_reloader=False to avoid issues with debugger and multiple processes

