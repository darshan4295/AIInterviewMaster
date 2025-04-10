import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, Candidate, Recruiter
from app import db

def generate_token(user_id, is_recruiter=False):
    """Generate a JWT token for authentication"""
    payload = {
        'user_id': user_id,
        'is_recruiter': is_recruiter,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }
    token = jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')
    return token

def token_required(f):
    """Decorator for routes that require token authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Authentication token is missing!'}), 401
        
        try:
            payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(payload['user_id'])
            if not current_user:
                return jsonify({'error': 'User not found!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

def recruiter_required(f):
    """Decorator for routes that require recruiter access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Authentication token is missing!'}), 401
        
        try:
            payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            if not payload.get('is_recruiter', False):
                return jsonify({'error': 'Recruiter access required!'}), 403
                
            current_user = User.query.get(payload['user_id'])
            if not current_user or not current_user.is_recruiter:
                return jsonify({'error': 'Recruiter access required!'}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

def register_user(username, email, password, is_recruiter=False, **kwargs):
    """Register a new user in the system"""
    # Check if user already exists
    existing_user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()
    
    if existing_user:
        if existing_user.username == username:
            return {"error": "Username already taken"}, 400
        else:
            return {"error": "Email already registered"}, 400
    
    # Create new user
    new_user = User(
        username=username,
        email=email,
        is_recruiter=is_recruiter
    )
    new_user.set_password(password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        
        # Create profile based on user type
        if is_recruiter:
            recruiter = Recruiter(
                user_id=new_user.id,
                first_name=kwargs.get('first_name', ''),
                last_name=kwargs.get('last_name', ''),
                company=kwargs.get('company', ''),
                position=kwargs.get('position', '')
            )
            db.session.add(recruiter)
        else:
            candidate = Candidate(
                user_id=new_user.id,
                first_name=kwargs.get('first_name', ''),
                last_name=kwargs.get('last_name', ''),
                phone=kwargs.get('phone', ''),
                linkedin_url=kwargs.get('linkedin_url', ''),
                github_url=kwargs.get('github_url', ''),
                experience_years=kwargs.get('experience_years', 0)
            )
            db.session.add(candidate)
        
        db.session.commit()
        
        # Generate token
        token = generate_token(new_user.id, is_recruiter)
        
        return {
            "message": "User registered successfully",
            "user_id": new_user.id,
            "token": token
        }, 201
        
    except Exception as e:
        db.session.rollback()
        return {"error": f"Registration failed: {str(e)}"}, 500

def login_user(username_or_email, password):
    """Login a user and return authentication token"""
    # Find user by username or email
    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()
    
    if not user or not user.check_password(password):
        return {"error": "Invalid username/email or password"}, 401
    
    # Generate token
    token = generate_token(user.id, user.is_recruiter)
    
    return {
        "message": "Login successful",
        "user_id": user.id,
        "is_recruiter": user.is_recruiter,
        "token": token
    }, 200
