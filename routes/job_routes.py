from flask import Blueprint, request, jsonify
from utils.auth import token_required, recruiter_required
from utils.profile_parser import extract_skills_from_job_description
from models import JobPosition, Recruiter, CandidateSkill, db

job_bp = Blueprint('jobs', __name__)

@job_bp.route('', methods=['GET'])
@token_required
def get_job_positions(current_user):
    """
    Get all job positions
    
    Authorization header:
    Bearer <token>
    
    Query parameters:
    - recruiter_id: Filter by recruiter ID
    - is_active: Filter by active status (true/false)
    - skill: Filter by required skill
    - experience: Filter by minimum years of experience
    """
    # Get query parameters
    recruiter_id = request.args.get('recruiter_id')
    is_active = request.args.get('is_active')
    skill = request.args.get('skill')
    experience = request.args.get('experience')
    
    # Build query
    query = JobPosition.query
    
    # Apply filters
    if recruiter_id:
        query = query.filter(JobPosition.recruiter_id == recruiter_id)
    
    if is_active is not None:
        is_active_bool = is_active.lower() == 'true'
        query = query.filter(JobPosition.is_active == is_active_bool)
    
    if experience:
        try:
            exp_val = int(experience)
            query = query.filter(JobPosition.required_experience <= exp_val)
        except ValueError:
            return jsonify({"error": "Experience must be a number"}), 400
    
    # Execute query
    positions = query.all()
    
    # Apply skill filter (has to be done after query execution)
    if skill:
        positions = [p for p in positions if any(s.name.lower() == skill.lower() for s in p.required_skills)]
    
    # Format response
    result = []
    for position in positions:
        result.append({
            'id': position.id,
            'title': position.title,
            'description': position.description,
            'required_experience': position.required_experience,
            'is_active': position.is_active,
            'required_skills': [
                {'id': skill.id, 'name': skill.name, 'category': skill.category}
                for skill in position.required_skills
            ],
            'recruiter': {
                'id': position.recruiter_id,
                'name': f"{position.recruiter.first_name} {position.recruiter.last_name}",
                'company': position.recruiter.company
            },
            'created_at': position.created_at.isoformat(),
            'updated_at': position.updated_at.isoformat()
        })
    
    return jsonify(result)

@job_bp.route('/<int:position_id>', methods=['GET'])
@token_required
def get_job_position(current_user, position_id):
    """
    Get detailed job position information
    
    Authorization header:
    Bearer <token>
    
    Path parameters:
    - position_id: ID of the job position
    """
    # Get position
    position = JobPosition.query.get(position_id)
    if not position:
        return jsonify({"error": "Job position not found"}), 404
    
    # Format response
    result = {
        'id': position.id,
        'title': position.title,
        'description': position.description,
        'required_experience': position.required_experience,
        'is_active': position.is_active,
        'required_skills': [
            {'id': skill.id, 'name': skill.name, 'category': skill.category}
            for skill in position.required_skills
        ],
        'recruiter': {
            'id': position.recruiter_id,
            'name': f"{position.recruiter.first_name} {position.recruiter.last_name}",
            'company': position.recruiter.company
        },
        'created_at': position.created_at.isoformat(),
        'updated_at': position.updated_at.isoformat()
    }
    
    return jsonify(result)

@job_bp.route('', methods=['POST'])
@recruiter_required
def create_job_position(current_user):
    """
    Create a new job position
    
    Authorization header:
    Bearer <token>
    
    Request body:
    {
        "title": "Senior Software Engineer",
        "description": "We are looking for a senior software engineer...",
        "required_experience": 5,
        "required_skills": ["Python", "React", "AWS"]
    }
    """
    data = request.json
    
    # Validate required fields
    required_fields = ['title', 'description']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Get recruiter profile
    recruiter = Recruiter.query.filter_by(user_id=current_user.id).first()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404
    
    # Create new job position
    new_position = JobPosition(
        recruiter_id=recruiter.id,
        title=data['title'],
        description=data['description'],
        required_experience=data.get('required_experience', 0),
        is_active=data.get('is_active', True)
    )
    
    # Add required skills
    if 'required_skills' in data and data['required_skills']:
        for skill_name in data['required_skills']:
            # Check if skill exists
            skill = CandidateSkill.query.filter_by(name=skill_name).first()
            # If not, create it
            if not skill:
                skill = CandidateSkill(name=skill_name)
                db.session.add(skill)
                db.session.flush()  # Flush to get ID without committing
            
            # Add skill to position
            new_position.required_skills.append(skill)
    
    # Alternatively, extract skills from description if no skills provided
    elif 'auto_extract_skills' in data and data['auto_extract_skills']:
        skills_data = extract_skills_from_job_description(data['description'])
        if 'essential_skills' in skills_data:
            for skill_name in skills_data['essential_skills']:
                # Check if skill exists
                skill = CandidateSkill.query.filter_by(name=skill_name).first()
                # If not, create it
                if not skill:
                    skill = CandidateSkill(name=skill_name)
                    db.session.add(skill)
                    db.session.flush()  # Flush to get ID without committing
                
                # Add skill to position
                new_position.required_skills.append(skill)
    
    # Save to database
    db.session.add(new_position)
    db.session.commit()
    
    return jsonify({
        'id': new_position.id,
        'message': 'Job position created successfully'
    }), 201

@job_bp.route('/<int:position_id>', methods=['PUT'])
@recruiter_required
def update_job_position(current_user, position_id):
    """
    Update job position details
    
    Authorization header:
    Bearer <token>
    
    Path parameters:
    - position_id: ID of the job position
    
    Request body:
    {
        "title": "Updated Title",
        "description": "Updated description...",
        "required_experience": 3,
        "is_active": true,
        "required_skills": ["Python", "Django", "PostgreSQL"]
    }
    """
    data = request.json
    
    # Get recruiter profile
    recruiter = Recruiter.query.filter_by(user_id=current_user.id).first()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404
    
    # Get position
    position = JobPosition.query.get(position_id)
    if not position:
        return jsonify({"error": "Job position not found"}), 404
    
    # Ensure recruiter has access to this position
    if position.recruiter_id != recruiter.id:
        return jsonify({"error": "Unauthorized access"}), 403
    
    # Update fields
    if 'title' in data:
        position.title = data['title']
    
    if 'description' in data:
        position.description = data['description']
    
    if 'required_experience' in data:
        position.required_experience = data['required_experience']
    
    if 'is_active' in data:
        position.is_active = data['is_active']
    
    # Update required skills
    if 'required_skills' in data:
        # Clear existing skills
        position.required_skills.clear()
        
        # Add new skills
        for skill_name in data['required_skills']:
            # Check if skill exists
            skill = CandidateSkill.query.filter_by(name=skill_name).first()
            # If not, create it
            if not skill:
                skill = CandidateSkill(name=skill_name)
                db.session.add(skill)
                db.session.flush()  # Flush to get ID without committing
            
            # Add skill to position
            position.required_skills.append(skill)
    
    # Save to database
    db.session.commit()
    
    return jsonify({
        'id': position.id,
        'message': 'Job position updated successfully'
    })

@job_bp.route('/<int:position_id>', methods=['DELETE'])
@recruiter_required
def delete_job_position(current_user, position_id):
    """
    Delete a job position
    
    Authorization header:
    Bearer <token>
    
    Path parameters:
    - position_id: ID of the job position
    """
    # Get recruiter profile
    recruiter = Recruiter.query.filter_by(user_id=current_user.id).first()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404
    
    # Get position
    position = JobPosition.query.get(position_id)
    if not position:
        return jsonify({"error": "Job position not found"}), 404
    
    # Ensure recruiter has access to this position
    if position.recruiter_id != recruiter.id:
        return jsonify({"error": "Unauthorized access"}), 403
    
    # Check if position has associated interviews
    if position.interviews.count() > 0:
        # Instead of deleting, mark as inactive
        position.is_active = False
        db.session.commit()
        return jsonify({
            'id': position.id,
            'message': 'Job position has associated interviews, marked as inactive instead of deleting'
        })
    
    # Delete position
    db.session.delete(position)
    db.session.commit()
    
    return jsonify({
        'message': 'Job position deleted successfully'
    })

@job_bp.route('/<int:position_id>/skills', methods=['GET'])
@token_required
def get_job_skills(current_user, position_id):
    """
    Get skills required for a job position
    
    Authorization header:
    Bearer <token>
    
    Path parameters:
    - position_id: ID of the job position
    """
    # Get position
    position = JobPosition.query.get(position_id)
    if not position:
        return jsonify({"error": "Job position not found"}), 404
    
    # Format response
    skills = [
        {'id': skill.id, 'name': skill.name, 'category': skill.category}
        for skill in position.required_skills
    ]
    
    return jsonify(skills)

@job_bp.route('/<int:position_id>/extract-skills', methods=['POST'])
@recruiter_required
def extract_job_position_skills(current_user, position_id):
    """
    Extract and add skills from job description
    
    Authorization header:
    Bearer <token>
    
    Path parameters:
    - position_id: ID of the job position
    
    Request body (optional):
    {
        "add_to_position": true
    }
    """
    data = request.json or {}
    add_to_position = data.get('add_to_position', True)
    
    # Get recruiter profile
    recruiter = Recruiter.query.filter_by(user_id=current_user.id).first()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404
    
    # Get position
    position = JobPosition.query.get(position_id)
    if not position:
        return jsonify({"error": "Job position not found"}), 404
    
    # Ensure recruiter has access to this position
    if position.recruiter_id != recruiter.id:
        return jsonify({"error": "Unauthorized access"}), 403
    
    # Extract skills from job description
    skills_data = extract_skills_from_job_description(position.description)
    
    # Add skills to position if requested
    if add_to_position and 'essential_skills' in skills_data:
        for skill_name in skills_data['essential_skills']:
            # Check if skill exists
            skill = CandidateSkill.query.filter_by(name=skill_name).first()
            # If not, create it
            if not skill:
                skill = CandidateSkill(name=skill_name)
                db.session.add(skill)
                db.session.flush()
            
            # Add skill to position if not already added
            if skill not in position.required_skills:
                position.required_skills.append(skill)
        
        db.session.commit()
    
    return jsonify(skills_data)