import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create SQLAlchemy base
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure JWT
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", app.secret_key)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 86400  # 24 hours

# Initialize extensions with app
db.init_app(app)
jwt = JWTManager(app)
CORS(app)

# Import models for DB creation
with app.app_context():
    # Import models and create tables
    from models import User, Candidate, Recruiter, JobPosition, Interview, CodingChallenge, VideoInterview, CandidateSkill, SkillAssessment, TestCase
    db.create_all()

# Register blueprints
from routes.auth_routes import auth_bp
from routes.candidate_routes import candidate_bp
from routes.interview_routes import interview_bp
from routes.assessment_routes import assessment_bp
from routes.coding_routes import coding_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(candidate_bp, url_prefix='/api/candidates')
app.register_blueprint(interview_bp, url_prefix='/api/interviews')
app.register_blueprint(assessment_bp, url_prefix='/api/assessments')
app.register_blueprint(coding_bp, url_prefix='/api/coding')

@app.route('/')
def index():
    return "AI-Powered Interview Platform API"

@app.route('/api/docs')
def api_docs():
    from flask import render_template
    return render_template('api_docs.html')

# Error handlers
@app.errorhandler(404)
def not_found(error):
    from flask import jsonify
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def server_error(error):
    from flask import jsonify
    return jsonify({"error": "Internal server error"}), 500
