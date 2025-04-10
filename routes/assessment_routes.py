from flask import Blueprint, request, jsonify
from utils.auth import token_required, recruiter_required
from utils.profile_parser import extract_skills_from_job_description, match_candidate_to_job
from utils.scoring import calculate_final_candidate_score
from models import JobPosition, Candidate, CandidateSkill, SkillAssessment, db

assessment_bp = Blueprint('assessment', __name__)

@assessment_bp.route('/job-skills', methods=['POST'])
@token_required
def extract_job_skills(current_user):
    """
    Extract required skills from job description
    
    Authorization header:
    Bearer <token>
    
    Request body:
    {
        "job_description": "Detailed job description text..."
    }
    """
    data = request.json
    
    # Validate required fields
    if 'job_description' not in data:
        return jsonify({"error": "Missing required field: job_description"}), 400
    
    # Extract skills from job description
    skills = extract_skills_from_job_description(data['job_description'])
    
    return jsonify(skills)

@assessment_bp.route('/match-candidate', methods=['POST'])
@token_required
def match_candidate_skills(current_user):
    """
    Match candidate skills with job requirements
    
    Authorization header:
    Bearer <token>
    
    Request body:
    {
        "candidate_id": 1,
        "job_position_id": 2
    }
    OR
    {
        "candidate_id": 1,
        "job_skills": {
            "essential_skills": [...],
            "preferred_skills": [...]
        }
    }
    """
    data = request.json
    
    # Validate required fields
    if 'candidate_id' not in data:
        return jsonify({"error": "Missing required field: candidate_id"}), 400
    
    if 'job_position_id' not in data and 'job_skills' not in data:
        return jsonify({"error": "Either job_position_id or job_skills must be provided"}), 400
    
    # Get candidate
    candidate = Candidate.query.get(data['candidate_id'])
    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404
    
    # Get candidate skills with confidence scores
    candidate_skills = []
    for assessment in candidate.skill_assessments:
        candidate_skills.append({
            "skill": assessment.skill.name,
            "confidence": assessment.confidence
        })
    
    # Get job skills
    job_skills = None
    
    if 'job_position_id' in data:
        # Get job position
        position = JobPosition.query.get(data['job_position_id'])
        if not position:
            return jsonify({"error": "Job position not found"}), 404
        
        # Extract skills from job description
        job_skills = extract_skills_from_job_description(position.description)
    
    elif 'job_skills' in data:
        job_skills = data['job_skills']
    
    # Match candidate skills with job requirements
    match_results = match_candidate_to_job(candidate_skills, job_skills)
    
    return jsonify(match_results)

@assessment_bp.route('/evaluate-candidate', methods=['POST'])
@recruiter_required
def evaluate_candidate(current_user):
    """
    Calculate overall candidate score across all assessment phases
    
    Authorization header:
    Bearer <token>
    
    Request body:
    {
        "candidate_id": 1,
        "profile_score": 0.8,
        "video_score": 0.7,
        "coding_score": 0.9,
        "managerial_score": 0.75
    }
    """
    data = request.json
    
    # Validate required fields
    required_fields = ['candidate_id', 'profile_score', 'video_score', 'coding_score']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Verify candidate exists
    candidate = Candidate.query.get(data['candidate_id'])
    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404
    
    # Calculate final candidate score
    try:
        final_score = calculate_final_candidate_score(
            profile_score=float(data['profile_score']),
            video_score=float(data['video_score']),
            coding_score=float(data['coding_score']),
            managerial_score=float(data['managerial_score']) if 'managerial_score' in data else None
        )
        
        return jsonify(final_score)
    
    except Exception as e:
        return jsonify({"error": f"Failed to calculate final score: {str(e)}"}), 500

@assessment_bp.route('/skill-assessments', methods=['POST'])
@token_required
def create_skill_assessment(current_user):
    """
    Create or update a skill assessment
    
    Authorization header:
    Bearer <token>
    
    Request body:
    {
        "candidate_id": 1,
        "skill_name": "Python",
        "score": 0.85,
        "confidence": 0.9,
        "assessment_source": "coding_challenge"
    }
    """
    data = request.json
    
    # Validate required fields
    required_fields = ['candidate_id', 'skill_name', 'score', 'confidence', 'assessment_source']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Verify candidate exists
    candidate = Candidate.query.get(data['candidate_id'])
    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404
    
    # Ensure user has permissions (must be the candidate or a recruiter)
    if not current_user.is_recruiter:
        candidate_user = Candidate.query.filter_by(user_id=current_user.id).first()
        if not candidate_user or candidate_user.id != candidate.id:
            return jsonify({"error": "Unauthorized access"}), 403
    
    # Find or create the skill
    skill = CandidateSkill.query.filter_by(name=data['skill_name']).first()
    if not skill:
        skill = CandidateSkill(
            name=data['skill_name'],
            category=data.get('category', 'Technical')
        )
        db.session.add(skill)
        try:
            db.session.commit()
        except:
            db.session.rollback()
            return jsonify({"error": "Failed to create skill"}), 500
    
    # Add skill to candidate if not already added
    if skill not in candidate.skills:
        candidate.skills.append(skill)
    
    # Create or update skill assessment
    assessment = SkillAssessment.query.filter_by(
        candidate_id=candidate.id,
        skill_id=skill.id,
        assessment_source=data['assessment_source']
    ).first()
    
    try:
        if not assessment:
            assessment = SkillAssessment(
                candidate_id=candidate.id,
                skill_id=skill.id,
                score=data['score'],
                confidence=data['confidence'],
                assessment_source=data['assessment_source']
            )
            db.session.add(assessment)
        else:
            assessment.score = data['score']
            assessment.confidence = data['confidence']
        
        db.session.commit()
        
        return jsonify({
            "message": "Skill assessment created/updated successfully",
            "assessment_id": assessment.id
        }), 201 if not assessment else 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create/update skill assessment: {str(e)}"}), 500

@assessment_bp.route('/skill-assessments/<int:candidate_id>', methods=['GET'])
@token_required
def get_skill_assessments(current_user, candidate_id):
    """
    Get all skill assessments for a candidate
    
    Authorization header:
    Bearer <token>
    
    Path parameters:
    - candidate_id: ID of the candidate
    """
    # Verify candidate exists
    candidate = Candidate.query.get(candidate_id)
    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404
    
    # Ensure user has permissions (must be the candidate or a recruiter)
    if not current_user.is_recruiter:
        candidate_user = Candidate.query.filter_by(user_id=current_user.id).first()
        if not candidate_user or candidate_user.id != candidate.id:
            return jsonify({"error": "Unauthorized access"}), 403
    
    # Get all skill assessments
    assessments = SkillAssessment.query.filter_by(candidate_id=candidate_id).all()
    
    # Format response
    result = []
    for assessment in assessments:
        result.append({
            'id': assessment.id,
            'skill_id': assessment.skill_id,
            'skill_name': assessment.skill.name,
            'score': assessment.score,
            'confidence': assessment.confidence,
            'assessment_source': assessment.assessment_source,
            'created_at': assessment.created_at.isoformat(),
            'updated_at': assessment.updated_at.isoformat()
        })
    
    return jsonify(result)
