import pytest
import json
from app import app, db
from models import User, Candidate, CandidateSkill, SkillAssessment
from utils.auth import generate_token

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

@pytest.fixture
def candidate_user():
    """Create a test candidate user"""
    with app.app_context():
        user = User(
            username='testcandidate',
            email='testcandidate@example.com',
            is_recruiter=False
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        candidate = Candidate(
            user_id=user.id,
            first_name='Test',
            last_name='Candidate',
            phone='123-456-7890',
            github_url='https://github.com/testcandidate',
            experience_years=3,
            preferred_role='Software Engineer'
        )
        db.session.add(candidate)
        db.session.commit()
        
        # Add some skills
        python_skill = CandidateSkill(name='Python', category='Programming')
        javascript_skill = CandidateSkill(name='JavaScript', category='Programming')
        
        db.session.add_all([python_skill, javascript_skill])
        db.session.commit()
        
        candidate.skills.append(python_skill)
        candidate.skills.append(javascript_skill)
        
        # Add skill assessments
        python_assessment = SkillAssessment(
            candidate_id=candidate.id,
            skill_id=python_skill.id,
            score=0.9,
            confidence=0.85,
            assessment_source='github'
        )
        
        javascript_assessment = SkillAssessment(
            candidate_id=candidate.id,
            skill_id=javascript_skill.id,
            score=0.8,
            confidence=0.75,
            assessment_source='resume'
        )
        
        db.session.add_all([python_assessment, javascript_assessment])
        db.session.commit()
        
        return {
            'user': user,
            'candidate': candidate,
            'token': generate_token(user.id, False)
        }

@pytest.fixture
def recruiter_user():
    """Create a test recruiter user"""
    with app.app_context():
        user = User(
            username='testrecruiter',
            email='testrecruiter@example.com',
            is_recruiter=True
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        from models import Recruiter
        recruiter = Recruiter(
            user_id=user.id,
            first_name='Test',
            last_name='Recruiter',
            company='Tech Corp',
            position='Hiring Manager'
        )
        db.session.add(recruiter)
        db.session.commit()
        
        return {
            'user': user,
            'recruiter': recruiter,
            'token': generate_token(user.id, True)
        }

def test_get_candidates(client, candidate_user):
    """Test getting all candidates"""
    response = client.get('/api/candidates')
    
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert 'candidates' in data
    assert len(data['candidates']) > 0
    assert data['candidates'][0]['first_name'] == 'Test'
    assert data['candidates'][0]['last_name'] == 'Candidate'
    assert len(data['candidates'][0]['skills']) == 2

def test_get_candidate_by_id(client, candidate_user):
    """Test getting a candidate by ID"""
    candidate_id = candidate_user['candidate'].id
    
    response = client.get(f'/api/candidates/{candidate_id}')
    
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['id'] == candidate_id
    assert data['first_name'] == 'Test'
    assert data['last_name'] == 'Candidate'
    assert data['github_url'] == 'https://github.com/testcandidate'
    assert len(data['skills']) == 2
    assert len(data['skill_assessments']) == 2

def test_get_own_profile(client, candidate_user):
    """Test getting own candidate profile"""
    token = candidate_user['token']
    
    response = client.get('/api/candidates/profile', headers={
        'Authorization': f'Bearer {token}'
    })
    
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['first_name'] == 'Test'
    assert data['last_name'] == 'Candidate'
    assert data['full_name'] == 'Test Candidate'
    assert data['preferred_role'] == 'Software Engineer'

def test_recruiter_cannot_access_candidate_profile(client, recruiter_user):
    """Test that recruiters cannot access candidate profile endpoint"""
    token = recruiter_user['token']
    
    response = client.get('/api/candidates/profile', headers={
        'Authorization': f'Bearer {token}'
    })
    
    assert response.status_code == 403

def test_update_profile(client, candidate_user):
    """Test updating candidate profile"""
    token = candidate_user['token']
    
    update_data = {
        'first_name': 'Updated',
        'last_name': 'Name',
        'phone': '987-654-3210',
        'preferred_role': 'Senior Developer'
    }
    
    response = client.put('/api/candidates/profile', 
                         headers={'Authorization': f'Bearer {token}'},
                         json=update_data)
    
    assert response.status_code == 200
    
    # Verify profile was updated
    get_response = client.get('/api/candidates/profile', 
                             headers={'Authorization': f'Bearer {token}'})
    
    data = json.loads(get_response.data)
    
    assert data['first_name'] == 'Updated'
    assert data['last_name'] == 'Name'
    assert data['phone'] == '987-654-3210'
    assert data['preferred_role'] == 'Senior Developer'

def test_github_analysis(client, candidate_user, monkeypatch):
    """Test GitHub profile analysis"""
    # Mock the fetch_github_profile function
    from utils.profile_parser import fetch_github_profile
    
    def mock_fetch_github_profile(username):
        return {
            "status": "success",
            "profile": {
                "username": username,
                "repositories": []
            },
            "analysis": {
                "code_quality_score": 0.85,
                "overall_github_score": 0.8,
                "identified_skills": [
                    {"skill": "Python", "evidence": "Several Python projects"},
                    {"skill": "Django", "evidence": "Two Django web apps"}
                ]
            }
        }
    
    # Apply the mock
    monkeypatch.setattr('utils.profile_parser.fetch_github_profile', mock_fetch_github_profile)
    
    token = candidate_user['token']
    
    response = client.post('/api/candidates/github-analysis',
                          headers={'Authorization': f'Bearer {token}'},
                          json={'github_url': 'https://github.com/testcandidate'})
    
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['status'] == 'success'
    assert 'profile' in data
    assert 'analysis' in data
    assert data['analysis']['overall_github_score'] == 0.8
    
    # Check that skills were added
    with app.app_context():
        candidate = Candidate.query.get(candidate_user['candidate'].id)
        skill_names = [skill.name for skill in candidate.skills]
        assert 'Python' in skill_names
        assert 'Django' in skill_names

def test_resume_analysis(client, candidate_user, monkeypatch):
    """Test resume analysis"""
    # Mock the parse_resume_text function
    from utils.profile_parser import parse_resume_text
    
    def mock_parse_resume_text(text):
        return {
            "status": "success",
            "parsed_resume": {
                "name": "Test Candidate",
                "contact": {
                    "email": "test@example.com",
                    "phone": "123-456-7890"
                },
                "skills": [
                    {"category": "Programming Languages", "items": ["Python", "JavaScript"]}
                ]
            },
            "skill_analysis": {
                "identified_skills": [
                    {"skill": "Python", "confidence": 0.9},
                    {"skill": "JavaScript", "confidence": 0.8},
                    {"skill": "React", "confidence": 0.7}
                ]
            }
        }
    
    # Apply the mock
    monkeypatch.setattr('utils.profile_parser.parse_resume_text', mock_parse_resume_text)
    
    token = candidate_user['token']
    
    response = client.post('/api/candidates/resume-analysis',
                          headers={'Authorization': f'Bearer {token}'},
                          json={'resume_text': 'Sample resume content with skills...'})
    
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['status'] == 'success'
    assert 'parsed_resume' in data
    assert 'skill_analysis' in data
    
    # Check that skills were added
    with app.app_context():
        candidate = Candidate.query.get(candidate_user['candidate'].id)
        skill_names = [skill.name for skill in candidate.skills]
        assert 'Python' in skill_names
        assert 'JavaScript' in skill_names
        assert 'React' in skill_names
