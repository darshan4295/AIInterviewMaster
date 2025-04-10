import pytest
import json
from app import app, db
from models import User

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def test_register_candidate(client):
    """Test registering a new candidate"""
    response = client.post('/api/auth/register', json={
        'username': 'testcandidate',
        'email': 'testcandidate@example.com',
        'password': 'password123',
        'first_name': 'Test',
        'last_name': 'Candidate',
        'phone': '123-456-7890',
        'github_url': 'https://github.com/testcandidate',
        'is_recruiter': False
    })
    
    data = json.loads(response.data)
    
    assert response.status_code == 201
    assert 'token' in data
    assert 'user_id' in data
    assert data['message'] == 'User registered successfully'
    
    # Verify user was created in DB
    with app.app_context():
        user = User.query.filter_by(username='testcandidate').first()
        assert user is not None
        assert user.email == 'testcandidate@example.com'
        assert user.is_recruiter == False
        assert user.check_password('password123')

def test_register_recruiter(client):
    """Test registering a new recruiter"""
    response = client.post('/api/auth/register', json={
        'username': 'testrecruiter',
        'email': 'testrecruiter@example.com',
        'password': 'password123',
        'first_name': 'Test',
        'last_name': 'Recruiter',
        'company': 'Tech Corp',
        'position': 'Hiring Manager',
        'is_recruiter': True
    })
    
    data = json.loads(response.data)
    
    assert response.status_code == 201
    assert 'token' in data
    assert 'user_id' in data
    
    # Verify user was created in DB
    with app.app_context():
        user = User.query.filter_by(username='testrecruiter').first()
        assert user is not None
        assert user.email == 'testrecruiter@example.com'
        assert user.is_recruiter == True

def test_register_duplicate_username(client):
    """Test registering with a duplicate username"""
    # Register first user
    client.post('/api/auth/register', json={
        'username': 'duplicate',
        'email': 'first@example.com',
        'password': 'password123',
        'first_name': 'First',
        'last_name': 'User',
        'is_recruiter': False
    })
    
    # Try to register with same username
    response = client.post('/api/auth/register', json={
        'username': 'duplicate',
        'email': 'second@example.com',
        'password': 'password123',
        'first_name': 'Second',
        'last_name': 'User',
        'is_recruiter': False
    })
    
    data = json.loads(response.data)
    
    assert response.status_code == 400
    assert 'error' in data
    assert 'Username already taken' in data['error']

def test_login_success(client):
    """Test successful login"""
    # Register a user
    client.post('/api/auth/register', json={
        'username': 'logintest',
        'email': 'logintest@example.com',
        'password': 'password123',
        'first_name': 'Login',
        'last_name': 'Test',
        'is_recruiter': False
    })
    
    # Login with username
    response = client.post('/api/auth/login', json={
        'username_or_email': 'logintest',
        'password': 'password123'
    })
    
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert 'token' in data
    assert data['message'] == 'Login successful'
    
    # Login with email
    response = client.post('/api/auth/login', json={
        'username_or_email': 'logintest@example.com',
        'password': 'password123'
    })
    
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert 'token' in data

def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    # Register a user
    client.post('/api/auth/register', json={
        'username': 'faillogin',
        'email': 'faillogin@example.com',
        'password': 'password123',
        'first_name': 'Fail',
        'last_name': 'Login',
        'is_recruiter': False
    })
    
    # Login with wrong password
    response = client.post('/api/auth/login', json={
        'username_or_email': 'faillogin',
        'password': 'wrongpassword'
    })
    
    data = json.loads(response.data)
    
    assert response.status_code == 401
    assert 'error' in data
    assert 'Invalid username/email or password' in data['error']

def test_check_auth(client):
    """Test auth token validation"""
    # Register a user
    register_response = client.post('/api/auth/register', json={
        'username': 'authcheck',
        'email': 'authcheck@example.com',
        'password': 'password123',
        'first_name': 'Auth',
        'last_name': 'Check',
        'is_recruiter': False
    })
    
    register_data = json.loads(register_response.data)
    token = register_data['token']
    
    # Check auth with valid token
    response = client.get('/api/auth/check', headers={
        'Authorization': f'Bearer {token}'
    })
    
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['valid'] == True
    assert data['username'] == 'authcheck'
    
    # Check auth with invalid token
    response = client.get('/api/auth/check', headers={
        'Authorization': 'Bearer invalidtoken'
    })
    
    assert response.status_code == 401
