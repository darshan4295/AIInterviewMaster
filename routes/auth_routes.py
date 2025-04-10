from flask import Blueprint, request, jsonify
from utils.auth import register_user, login_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user (candidate or recruiter)
    
    Request body:
    {
        "username": "user123",
        "email": "user@example.com",
        "password": "securepassword",
        "is_recruiter": false,
        "first_name": "John",
        "last_name": "Doe",
        ...additional profile fields
    }
    """
    data = request.json
    
    # Validate required fields
    required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Extract user type and profile data
    is_recruiter = data.get('is_recruiter', False)
    
    # Register the user
    result, status_code = register_user(
        username=data['username'],
        email=data['email'],
        password=data['password'],
        is_recruiter=is_recruiter,
        first_name=data['first_name'],
        last_name=data['last_name'],
        # Include additional profile fields
        phone=data.get('phone'),
        linkedin_url=data.get('linkedin_url'),
        github_url=data.get('github_url'),
        experience_years=data.get('experience_years'),
        company=data.get('company'),
        position=data.get('position')
    )
    
    return jsonify(result), status_code

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login user and return authentication token
    
    Request body:
    {
        "username_or_email": "user123",
        "password": "securepassword"
    }
    """
    data = request.json
    
    # Validate required fields
    if 'username_or_email' not in data or 'password' not in data:
        return jsonify({"error": "Missing username/email or password"}), 400
    
    # Login the user
    result, status_code = login_user(
        username_or_email=data['username_or_email'],
        password=data['password']
    )
    
    return jsonify(result), status_code

@auth_bp.route('/check', methods=['GET'])
def check_auth():
    """
    Check if authentication token is valid (for testing purposes)
    
    Authorization header:
    Bearer <token>
    """
    from utils.auth import token_required
    
    @token_required
    def validate_token(current_user):
        return jsonify({
            "valid": True,
            "user_id": current_user.id,
            "username": current_user.username,
            "is_recruiter": current_user.is_recruiter
        })
    
    return validate_token()
