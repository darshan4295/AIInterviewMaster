from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Association tables for many-to-many relationships
candidate_skills = db.Table('candidate_skills',
    db.Column('candidate_id', db.Integer, db.ForeignKey('candidate.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('candidate_skill.id'), primary_key=True)
)

position_skills = db.Table('position_skills',
    db.Column('position_id', db.Integer, db.ForeignKey('job_position.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('candidate_skill.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_recruiter = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = db.relationship('Candidate', backref='user', uselist=False, cascade='all, delete-orphan')
    recruiter = db.relationship('Recruiter', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Candidate(db.Model):
    __tablename__ = 'candidate'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    linkedin_url = db.Column(db.String(255))
    github_url = db.Column(db.String(255))
    resume_url = db.Column(db.String(255))
    experience_years = db.Column(db.Integer)
    preferred_role = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    skills = db.relationship('CandidateSkill', secondary=candidate_skills, backref=db.backref('candidates', lazy='dynamic'))
    interviews = db.relationship('Interview', backref='candidate', lazy='dynamic', cascade='all, delete-orphan')
    coding_challenges = db.relationship('CodingChallenge', backref='candidate', lazy='dynamic', cascade='all, delete-orphan')
    skill_assessments = db.relationship('SkillAssessment', backref='candidate', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Candidate {self.first_name} {self.last_name}>'

class Recruiter(db.Model):
    __tablename__ = 'recruiter'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    company = db.Column(db.String(100))
    position = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job_positions = db.relationship('JobPosition', backref='recruiter', lazy='dynamic', cascade='all, delete-orphan')
    interviews = db.relationship('Interview', backref='recruiter', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Recruiter {self.first_name} {self.last_name}>'

class CandidateSkill(db.Model):
    __tablename__ = 'candidate_skill'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    category = db.Column(db.String(50))  # e.g., Programming, Database, DevOps, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Skill {self.name}>'

class JobPosition(db.Model):
    __tablename__ = 'job_position'
    
    id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('recruiter.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    required_experience = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    required_skills = db.relationship('CandidateSkill', secondary=position_skills, backref=db.backref('positions', lazy='dynamic'))
    interviews = db.relationship('Interview', backref='position', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<JobPosition {self.title}>'

class Interview(db.Model):
    __tablename__ = 'interview'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('recruiter.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('job_position.id'), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=60)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled
    overall_score = db.Column(db.Float)
    feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    video_interviews = db.relationship('VideoInterview', backref='interview', lazy='dynamic', cascade='all, delete-orphan')
    coding_challenges = db.relationship('CodingChallenge', backref='interview', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Interview {self.id} for {self.candidate_id}>'

class VideoInterview(db.Model):
    __tablename__ = 'video_interview'
    
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    video_url = db.Column(db.String(255))
    transcript = db.Column(db.Text)
    technical_score = db.Column(db.Float)
    communication_score = db.Column(db.Float)
    logical_score = db.Column(db.Float)
    sentiment_analysis = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<VideoInterview {self.id}>'

class CodingChallenge(db.Model):
    __tablename__ = 'coding_challenge'
    
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), default='medium')  # easy, medium, hard
    language = db.Column(db.String(50), nullable=False)
    code_submission = db.Column(db.Text)
    correctness_score = db.Column(db.Float)
    time_complexity_score = db.Column(db.Float)
    space_complexity_score = db.Column(db.Float)
    style_score = db.Column(db.Float)
    overall_score = db.Column(db.Float)
    feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    test_cases = db.relationship('TestCase', backref='challenge', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CodingChallenge {self.title}>'

class TestCase(db.Model):
    __tablename__ = 'test_case'
    
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('coding_challenge.id'), nullable=False)
    input_data = db.Column(db.Text, nullable=False)
    expected_output = db.Column(db.Text, nullable=False)
    is_hidden = db.Column(db.Boolean, default=False)
    weight = db.Column(db.Float, default=1.0)
    passed = db.Column(db.Boolean)
    actual_output = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TestCase {self.id} for challenge {self.challenge_id}>'

class SkillAssessment(db.Model):
    __tablename__ = 'skill_assessment'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('candidate_skill.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    assessment_source = db.Column(db.String(50))  # github, linkedin, resume, coding_challenge, video_interview
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    skill = db.relationship('CandidateSkill')
    
    def __repr__(self):
        return f'<SkillAssessment for skill {self.skill_id} with score {self.score}>'
