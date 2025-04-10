from flask import Blueprint, request, jsonify
from utils.auth import token_required
from utils.profile_parser import fetch_github_profile, parse_resume_text, extract_github_username
from utils.scoring import calculate_profile_score
from models import Candidate, CandidateSkill, SkillAssessment, db

candidate_bp = Blueprint('candidate', __name__)

@candidate_bp.route('', methods=['GET'])
def get_candidates():
    """
    Get all candidates (public profiles)
    
    Query parameters:
    - skill: Filter by skill name
    - experience: Filter by minimum years of experience
    - limit: Maximum number of results (default 20)
    - offset: Pagination offset (default 0)
    """
    # Get query parameters
    skill = request.args.get('skill')
    min_experience = request.args.get('experience')
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    
    # Build base query
    query = Candidate.query
    
    # Apply filters
    if skill:
        query = query.join(Candidate.skills).filter(CandidateSkill.name.ilike(f'%{skill}%'))
    
    if min_experience and min_experience.isdigit():
        query = query.filter(Candidate.experience_years >= int(min_experience))
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply pagination
    candidates = query.limit(limit).offset(offset).all()
    
    # Format response
    result = []
    for candidate in candidates:
        # Get skills for the candidate
        skills = [{'id': skill.id, 'name': skill.name} for skill in candidate.skills]
        
        result.append({
            'id': candidate.id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'preferred_role': candidate.preferred_role,
            'experience_years': candidate.experience_years,
            'skills': skills
        })
    
    return jsonify({
        'candidates': result,
        'total': total_count,
        'limit': limit,
        'offset': offset
    })

@candidate_bp.route('/<int:candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    """
    Get detailed candidate profile
    
    Path parameters:
    - candidate_id: ID of the candidate
    """
    candidate = Candidate.query.get(candidate_id)
    
    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404
    
    # Get skills for the candidate
    skills = [{'id': skill.id, 'name': skill.name, 'category': skill.category} 
              for skill in candidate.skills]
    
    # Get skill assessments
    skill_assessments = []
    for assessment in candidate.skill_assessments:
        skill_assessments.append({
            'skill_id': assessment.skill_id,
            'skill_name': assessment.skill.name,
            'score': assessment.score,
            'confidence': assessment.confidence,
            'source': assessment.assessment_source
        })
    
    result = {
        'id': candidate.id,
        'user_id': candidate.user_id,
        'first_name': candidate.first_name,
        'last_name': candidate.last_name,
        'full_name': f"{candidate.first_name} {candidate.last_name}",
        'phone': candidate.phone,
        'linkedin_url': candidate.linkedin_url,
        'github_url': candidate.github_url,
        'resume_url': candidate.resume_url,
        'experience_years': candidate.experience_years,
        'preferred_role': candidate.preferred_role,
        'skills': skills,
        'skill_assessments': skill_assessments,
        'created_at': candidate.created_at.isoformat(),
        'updated_at': candidate.updated_at.isoformat()
    }
    
    return jsonify(result)

@candidate_bp.route('/profile', methods=['GET'])
@token_required
def get_own_profile(current_user):
    """
    Get current candidate's own profile
    
    Authorization header:
    Bearer <token>
    """
    # Ensure user is a candidate
    if current_user.is_recruiter:
        return jsonify({"error": "Recruiter cannot access candidate profile"}), 403
    
    candidate = Candidate.query.filter_by(user_id=current_user.id).first()
    
    if not candidate:
        return jsonify({"error": "Candidate profile not found"}), 404
    
    # Get skills for the candidate
    skills = [{'id': skill.id, 'name': skill.name, 'category': skill.category} 
              for skill in candidate.skills]
    
    # Get skill assessments
    skill_assessments = []
    for assessment in candidate.skill_assessments:
        skill_assessments.append({
            'skill_id': assessment.skill_id,
            'skill_name': assessment.skill.name,
            'score': assessment.score,
            'confidence': assessment.confidence,
            'source': assessment.assessment_source
        })
    
    result = {
        'id': candidate.id,
        'user_id': candidate.user_id,
        'first_name': candidate.first_name,
        'last_name': candidate.last_name,
        'full_name': f"{candidate.first_name} {candidate.last_name}",
        'phone': candidate.phone,
        'linkedin_url': candidate.linkedin_url,
        'github_url': candidate.github_url,
        'resume_url': candidate.resume_url,
        'experience_years': candidate.experience_years,
        'preferred_role': candidate.preferred_role,
        'skills': skills,
        'skill_assessments': skill_assessments,
        'created_at': candidate.created_at.isoformat(),
        'updated_at': candidate.updated_at.isoformat()
    }
    
    return jsonify(result)

@candidate_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """
    Update candidate profile
    
    Authorization header:
    Bearer <token>
    
    Request body:
    {
        "first_name": "John",
        "last_name": "Doe",
        "phone": "123-456-7890",
        "linkedin_url": "https://linkedin.com/in/johndoe",
        "github_url": "https://github.com/johndoe",
        "experience_years": 5,
        "preferred_role": "Software Engineer"
    }
    """
    # Ensure user is a candidate
    if current_user.is_recruiter:
        return jsonify({"error": "Recruiter cannot update candidate profile"}), 403
    
    data = request.json
    candidate = Candidate.query.filter_by(user_id=current_user.id).first()
    
    if not candidate:
        return jsonify({"error": "Candidate profile not found"}), 404
    
    # Update profile fields
    if 'first_name' in data:
        candidate.first_name = data['first_name']
    if 'last_name' in data:
        candidate.last_name = data['last_name']
    if 'phone' in data:
        candidate.phone = data['phone']
    if 'linkedin_url' in data:
        candidate.linkedin_url = data['linkedin_url']
    if 'github_url' in data:
        candidate.github_url = data['github_url']
    if 'experience_years' in data:
        candidate.experience_years = data['experience_years']
    if 'preferred_role' in data:
        candidate.preferred_role = data['preferred_role']
    
    try:
        db.session.commit()
        
        return jsonify({
            "message": "Profile updated successfully",
            "candidate_id": candidate.id
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update profile: {str(e)}"}), 500

@candidate_bp.route('/github-analysis', methods=['POST'])
@token_required
def analyze_github(current_user):
    """
    Analyze candidate's GitHub profile
    
    Authorization header:
    Bearer <token>
    
    Request body:
    {
        "github_url": "https://github.com/username"
    }
    """
    # Ensure user is a candidate
    if current_user.is_recruiter:
        return jsonify({"error": "Recruiters cannot use this endpoint"}), 403
    
    data = request.json
    github_url = data.get('github_url')
    
    if not github_url:
        # Check if the candidate has a GitHub URL in their profile
        candidate = Candidate.query.filter_by(user_id=current_user.id).first()
        if not candidate or not candidate.github_url:
            return jsonify({"error": "No GitHub URL provided"}), 400
        github_url = candidate.github_url
    
    # Extract GitHub username
    github_username = extract_github_username(github_url)
    if not github_username:
        return jsonify({"error": "Invalid GitHub URL"}), 400
    
    # Fetch and analyze GitHub profile
    github_data = fetch_github_profile(github_username)
    
    if "error" in github_data:
        return jsonify(github_data), 400
    
    # Update candidate's GitHub URL if needed
    candidate = Candidate.query.filter_by(user_id=current_user.id).first()
    if candidate and not candidate.github_url:
        candidate.github_url = github_url
        try:
            db.session.commit()
        except:
            db.session.rollback()
    
    # Extract skills and create skill assessments
    if "analysis" in github_data and "identified_skills" in github_data["analysis"]:
        for skill_info in github_data["analysis"].get("identified_skills", []):
            skill_name = skill_info.get("skill")
            confidence = skill_info.get("evidence", "").lower().count(skill_name.lower()) / 10
            confidence = min(max(confidence, 0.1), 1.0)  # Ensure between 0.1 and 1.0
            
            # Check if skill exists, create if not
            skill = CandidateSkill.query.filter_by(name=skill_name).first()
            if not skill:
                skill = CandidateSkill(name=skill_name, category="Technical")
                db.session.add(skill)
                try:
                    db.session.commit()
                except:
                    db.session.rollback()
                    continue
            
            # Add skill to candidate if not already added
            if skill not in candidate.skills:
                candidate.skills.append(skill)
            
            # Create or update skill assessment
            assessment = SkillAssessment.query.filter_by(
                candidate_id=candidate.id,
                skill_id=skill.id,
                assessment_source="github"
            ).first()
            
            if not assessment:
                assessment = SkillAssessment(
                    candidate_id=candidate.id,
                    skill_id=skill.id,
                    score=confidence,
                    confidence=confidence,
                    assessment_source="github"
                )
                db.session.add(assessment)
            else:
                assessment.score = confidence
                assessment.confidence = confidence
            
            try:
                db.session.commit()
            except:
                db.session.rollback()
    
    return jsonify(github_data)

@candidate_bp.route('/resume-analysis', methods=['POST'])
@token_required
def analyze_resume(current_user):
    """
    Analyze candidate's resume
    
    Authorization header:
    Bearer <token>
    
    Request body:
    {
        "resume_text": "Resume content..."
    }
    """
    # Ensure user is a candidate
    if current_user.is_recruiter:
        return jsonify({"error": "Recruiters cannot use this endpoint"}), 403
    
    data = request.json
    resume_text = data.get('resume_text')
    
    if not resume_text:
        return jsonify({"error": "No resume text provided"}), 400
    
    # Parse and analyze resume
    resume_analysis = parse_resume_text(resume_text)
    
    if "error" in resume_analysis:
        return jsonify(resume_analysis), 400
    
    # Update candidate profile with resume information
    candidate = Candidate.query.filter_by(user_id=current_user.id).first()
    if candidate and "parsed_resume" in resume_analysis:
        parsed_data = resume_analysis["parsed_resume"]
        
        # Update basic information if not already set
        if not candidate.first_name and "name" in parsed_data:
            name_parts = parsed_data["name"].split(" ", 1)
            candidate.first_name = name_parts[0]
            if len(name_parts) > 1:
                candidate.last_name = name_parts[1]
        
        if not candidate.phone and "contact" in parsed_data:
            candidate.phone = parsed_data["contact"].get("phone", "")
        
        # Extract skills and create skill assessments
        if "skill_analysis" in resume_analysis and "identified_skills" in resume_analysis["skill_analysis"]:
            for skill_info in resume_analysis["skill_analysis"]["identified_skills"]:
                skill_name = skill_info.get("skill")
                confidence = skill_info.get("confidence", 0.5)
                
                # Check if skill exists, create if not
                skill = CandidateSkill.query.filter_by(name=skill_name).first()
                if not skill:
                    skill = CandidateSkill(name=skill_name, category="Technical")
                    db.session.add(skill)
                    try:
                        db.session.commit()
                    except:
                        db.session.rollback()
                        continue
                
                # Add skill to candidate if not already added
                if skill not in candidate.skills:
                    candidate.skills.append(skill)
                
                # Create or update skill assessment
                assessment = SkillAssessment.query.filter_by(
                    candidate_id=candidate.id,
                    skill_id=skill.id,
                    assessment_source="resume"
                ).first()
                
                if not assessment:
                    assessment = SkillAssessment(
                        candidate_id=candidate.id,
                        skill_id=skill.id,
                        score=confidence,
                        confidence=confidence,
                        assessment_source="resume"
                    )
                    db.session.add(assessment)
                else:
                    assessment.score = confidence
                    assessment.confidence = confidence
                
                try:
                    db.session.commit()
                except:
                    db.session.rollback()
    
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Failed to update profile: {str(e)}"}), 500
    
    return jsonify(resume_analysis)
