import pytest
import json
from datetime import datetime, timedelta
from app import app, db
from models import User, Candidate, Recruiter, JobPosition, Interview
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
def setup_users():
    """Set up test users and profiles"""
    with app.app_context():
        # Create candidate
        candidate_user = User(
            username='testcandidate',
            email='testcandidate@example.com',
            is_recruiter=False
        )
        candidate_user.set_password('password123')
        db.session.add(candidate_user)
        db.session.commit()
        
        candidate = Candidate(
            user_id=candidate_user.id,
            first_name='Test',
            last_name='Candidate',
            experience_years=3,
            preferred_role='Software Engineer'
        )
        db.session.add(candidate)
        
        # Create recruiter
        recruiter_user = User(
            username='testrecruiter',
            email='testrecruiter@example.com',
            is_recruiter=True
        )
        recruiter_user.set_password('password123')
        db.session.add(recruiter_user)
        db.session.commit()
        
        recruiter = Recruiter(
            user_id=recruiter_user.id,
            first_name='Test',
            last_name='Recruiter',
            company='Tech Corp',
            position='Hiring Manager'
        )
        db.session.add(recruiter)
        
        # Create job position
        position = JobPosition(
            recruiter_id=recruiter.id,
            title='Software Engineer',
            description='We are looking for a skilled software engineer...',
            required_experience=2,
            is_active=True
        )
        db.session.add(position)
        
        db.session.commit()
        
        return {
            'candidate_user': candidate_user,
            'candidate': candidate,
            'recruiter_user': recruiter_user,
            'recruiter': recruiter,
            'position': position,
            'candidate_token': generate_token(candidate_user.id, False),
            'recruiter_token': generate_token(recruiter_user.id, True)
        }

@pytest.fixture
def setup_interview(setup_users):
    """Set up test interview"""
    with app.app_context():
        # Create interview
        interview_time = datetime.utcnow() + timedelta(days=2)
        interview = Interview(
            candidate_id=setup_users['candidate'].id,
            recruiter_id=setup_users['recruiter'].id,
            position_id=setup_users['position'].id,
            scheduled_time=interview_time,
            duration_minutes=60,
            status='scheduled'
        )
        db.session.add(interview)
        db.session.commit()
        
        return interview

def test_get_interviews_recruiter(client, setup_users, setup_interview):
    """Test getting interviews as recruiter"""
    token = setup_users['recruiter_token']
    
    response = client.get('/api/interviews',
                         headers={'Authorization': f'Bearer {token}'})
    
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]['position']['title'] == 'Software Engineer'
    assert data[0]['candidate']['name'] == 'Test Candidate'
    assert data[0]['status'] == 'scheduled'

def test_get_interviews_candidate(client, setup_users, setup_interview):
    """Test getting interviews as candidate"""
    token = setup_users['candidate_token']
    
    response = client.get('/api/interviews',
                         headers={'Authorization': f'Bearer {token}'})
    
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]['position']['title'] == 'Software Engineer'
    assert data[0]['recruiter']['name'] == 'Test Recruiter'
    assert data[0]['status'] == 'scheduled'

def test_get_interview_by_id(client, setup_users, setup_interview):
    """Test getting an interview by ID"""
    token = setup_users['recruiter_token']
    interview_id = setup_interview.id
    
    response = client.get(f'/api/interviews/{interview_id}',
                         headers={'Authorization': f'Bearer {token}'})
    
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['id'] == interview_id
    assert data['status'] == 'scheduled'
    assert data['position']['title'] == 'Software Engineer'
    assert data['candidate']['name'] == 'Test Candidate'
    assert data['recruiter']['name'] == 'Test Recruiter'
    assert 'video_interviews' in data
    assert 'coding_challenges' in data

def test_create_interview(client, setup_users):
    """Test creating a new interview"""
    token = setup_users['recruiter_token']
    
    interview_data = {
        'candidate_id': setup_users['candidate'].id,
        'position_id': setup_users['position'].id,
        'scheduled_time': (datetime.utcnow() + timedelta(days=3)).isoformat(),
        'duration_minutes': 45
    }
    
    response = client.post('/api/interviews',
                          headers={'Authorization': f'Bearer {token}'},
                          json=interview_data)
    
    data = json.loads(response.data)
    
    assert response.status_code == 201
    assert 'interview_id' in data
    assert data['message'] == 'Interview scheduled successfully'
    
    # Verify interview was created
    with app.app_context():
        interview = Interview.query.get(data['interview_id'])
        assert interview is not None
        assert interview.candidate_id == setup_users['candidate'].id
        assert interview.position_id == setup_users['position'].id
        assert interview.duration_minutes == 45
        assert interview.status == 'scheduled'

def test_update_interview(client, setup_users, setup_interview):
    """Test updating an existing interview"""
    token = setup_users['recruiter_token']
    interview_id = setup_interview.id
    
    update_data = {
        'scheduled_time': (datetime.utcnow() + timedelta(days=4)).isoformat(),
        'duration_minutes': 30,
        'status': 'completed',
        'feedback': 'Candidate performed well in the interview.'
    }
    
    response = client.put(f'/api/interviews/{interview_id}',
                         headers={'Authorization': f'Bearer {token}'},
                         json=update_data)
    
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['message'] == 'Interview updated successfully'
    
    # Verify interview was updated
    with app.app_context():
        interview = Interview.query.get(interview_id)
        assert interview.duration_minutes == 30
        assert interview.status == 'completed'
        assert interview.feedback == 'Candidate performed well in the interview.'

def test_candidate_cannot_create_interview(client, setup_users):
    """Test that candidates cannot create interviews"""
    token = setup_users['candidate_token']
    
    interview_data = {
        'candidate_id': setup_users['candidate'].id,
        'position_id': setup_users['position'].id,
        'scheduled_time': (datetime.utcnow() + timedelta(days=3)).isoformat(),
        'duration_minutes': 45
    }
    
    response = client.post('/api/interviews',
                          headers={'Authorization': f'Bearer {token}'},
                          json=interview_data)
    
    assert response.status_code == 403

def test_add_video_interview(client, setup_users, setup_interview, monkeypatch):
    """Test adding a video interview recording and analysis"""
    # Mock the analyze_video_interview function
    from utils.ai_assessment import analyze_video_interview
    
    def mock_analyze_video_interview(transcript):
        return {
            "technical_knowledge_score": 0.85,
            "communication_score": 0.78,
            "logical_reasoning_score": 0.92,
            "overall_interview_score": 0.84,
            "sentiment_analysis": {
                "confidence": 0.8,
                "engagement": 0.75
            }
        }
    
    # Apply the mock
    monkeypatch.setattr('utils.ai_assessment.analyze_video_interview', mock_analyze_video_interview)
    
    token = setup_users['recruiter_token']
    interview_id = setup_interview.id
    
    video_data = {
        'video_url': 'https://example.com/interview.mp4',
        'transcript': 'This is a sample interview transcript...'
    }
    
    response = client.post(f'/api/interviews/{interview_id}/video',
                          headers={'Authorization': f'Bearer {token}'},
                          json=video_data)
    
    data = json.loads(response.data)
    
    assert response.status_code == 201
    assert 'video_id' in data
    assert data['message'] == 'Video interview added successfully'
    assert data['technical_score'] == 0.85
    assert data['communication_score'] == 0.78
    assert data['logical_score'] == 0.92
    
    # Verify video interview was created
    with app.app_context():
        from models import VideoInterview
        video = VideoInterview.query.get(data['video_id'])
        assert video is not None
        assert video.interview_id == interview_id
        assert video.video_url == 'https://example.com/interview.mp4'
        assert video.transcript == 'This is a sample interview transcript...'
        assert video.technical_score == 0.85

def test_generate_interview_questions(client, setup_users, setup_interview, monkeypatch):
    """Test generating interview questions"""
    # Mock the generate_interview_questions function
    from utils.ai_assessment import generate_interview_questions
    
    def mock_generate_interview_questions(job_description, candidate_skills, difficulty):
        return [
            {
                "question": "Explain the difference between a linked list and an array.",
                "type": "knowledge",
                "difficulty": difficulty,
                "expected_answer": "Arrays have O(1) random access but linked lists have O(n)...",
            },
            {
                "question": "Implement a function to reverse a string without using built-in reverse methods.",
                "type": "coding",
                "difficulty": difficulty,
                "expected_answer": "Two-pointer approach or stack-based solution..."
            }
        ]
    
    # Apply the mock
    monkeypatch.setattr('utils.ai_assessment.generate_interview_questions', mock_generate_interview_questions)
    
    token = setup_users['recruiter_token']
    interview_id = setup_interview.id
    
    response = client.post(f'/api/interviews/{interview_id}/questions',
                          headers={'Authorization': f'Bearer {token}'},
                          json={'difficulty': 'hard'})
    
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]['question'] == "Explain the difference between a linked list and an array."
    assert data[1]['difficulty'] == "hard"
