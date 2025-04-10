from flask import Blueprint, request, jsonify
from datetime import datetime
from utils.auth import token_required, recruiter_required
from utils.ai_assessment import analyze_video_interview, generate_interview_questions
from utils.scoring import calculate_video_interview_score
from models import Interview, VideoInterview, JobPosition, Candidate, Recruiter, db

interview_bp = Blueprint('interview', __name__)

@interview_bp.route('', methods=['GET'])
@token_required
def get_interviews(current_user):
    """
    Get interviews for the authenticated user
    
    Authorization header:
    Bearer <token>
    
    Query parameters:
    - status: Filter by status (scheduled, completed, cancelled)
    - from_date: Filter by date range start (YYYY-MM-DD)
    - to_date: Filter by date range end (YYYY-MM-DD)
    """
    # Get query parameters
    status = request.args.get('status')
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    # Build base query depending on user type
    if current_user.is_recruiter:
        recruiter = Recruiter.query.filter_by(user_id=current_user.id).first()
        if not recruiter:
            return jsonify({"error": "Recruiter profile not found"}), 404
        
        query = Interview.query.filter_by(recruiter_id=recruiter.id)
    else:
        candidate = Candidate.query.filter_by(user_id=current_user.id).first()
        if not candidate:
            return jsonify({"error": "Candidate profile not found"}), 404
        
        query = Interview.query.filter_by(candidate_id=candidate.id)
    
    # Apply filters
    if status:
        query = query.filter_by(status=status)
    
    if from_date:
        try:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d")
            query = query.filter(Interview.scheduled_time >= from_date_obj)
        except ValueError:
            return jsonify({"error": "Invalid from_date format, use YYYY-MM-DD"}), 400
    
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d")
            query = query.filter(Interview.scheduled_time <= to_date_obj)
        except ValueError:
            return jsonify({"error": "Invalid to_date format, use YYYY-MM-DD"}), 400
    
    # Execute query
    interviews = query.order_by(Interview.scheduled_time.desc()).all()
    
    # Format response
    result = []
    for interview in interviews:
        # Get position and candidate info
        position = JobPosition.query.get(interview.position_id)
        candidate = Candidate.query.get(interview.candidate_id)
        recruiter = Recruiter.query.get(interview.recruiter_id)
        
        result.append({
            'id': interview.id,
            'scheduled_time': interview.scheduled_time.isoformat(),
            'duration_minutes': interview.duration_minutes,
            'status': interview.status,
            'overall_score': interview.overall_score,
            'position': {
                'id': position.id,
                'title': position.title
            } if position else None,
            'candidate': {
                'id': candidate.id,
                'name': f"{candidate.first_name} {candidate.last_name}"
            } if candidate else None,
            'recruiter': {
                'id': recruiter.id,
                'name': f"{recruiter.first_name} {recruiter.last_name}"
            } if recruiter else None
        })
    
    return jsonify(result)

@interview_bp.route('/<int:interview_id>', methods=['GET'])
@token_required
def get_interview(current_user, interview_id):
    """
    Get detailed interview information
    
    Authorization header:
    Bearer <token>
    
    Path parameters:
    - interview_id: ID of the interview
    """
    interview = Interview.query.get(interview_id)
    
    if not interview:
        return jsonify({"error": "Interview not found"}), 404
    
    # Ensure user has access to this interview
    if current_user.is_recruiter:
        recruiter = Recruiter.query.filter_by(user_id=current_user.id).first()
        if not recruiter or interview.recruiter_id != recruiter.id:
            return jsonify({"error": "Unauthorized access"}), 403
    else:
        candidate = Candidate.query.filter_by(user_id=current_user.id).first()
        if not candidate or interview.candidate_id != candidate.id:
            return jsonify({"error": "Unauthorized access"}), 403
    
    # Get related data
    position = JobPosition.query.get(interview.position_id)
    candidate = Candidate.query.get(interview.candidate_id)
    recruiter = Recruiter.query.get(interview.recruiter_id)
    
    # Get video interviews
    video_interviews = []
    for video in interview.video_interviews:
        video_interviews.append({
            'id': video.id,
            'video_url': video.video_url,
            'technical_score': video.technical_score,
            'communication_score': video.communication_score,
            'logical_score': video.logical_score,
            'created_at': video.created_at.isoformat()
        })
    
    # Get coding challenges
    coding_challenges = []
    for challenge in interview.coding_challenges:
        coding_challenges.append({
            'id': challenge.id,
            'title': challenge.title,
            'language': challenge.language,
            'difficulty': challenge.difficulty,
            'overall_score': challenge.overall_score,
            'created_at': challenge.created_at.isoformat()
        })
    
    result = {
        'id': interview.id,
        'scheduled_time': interview.scheduled_time.isoformat(),
        'duration_minutes': interview.duration_minutes,
        'status': interview.status,
        'overall_score': interview.overall_score,
        'feedback': interview.feedback,
        'position': {
            'id': position.id,
            'title': position.title,
            'description': position.description
        } if position else None,
        'candidate': {
            'id': candidate.id,
            'name': f"{candidate.first_name} {candidate.last_name}",
            'email': current_user.email if not current_user.is_recruiter else None
        } if candidate else None,
        'recruiter': {
            'id': recruiter.id,
            'name': f"{recruiter.first_name} {recruiter.last_name}",
            'company': recruiter.company
        } if recruiter else None,
        'video_interviews': video_interviews,
        'coding_challenges': coding_challenges,
        'created_at': interview.created_at.isoformat(),
        'updated_at': interview.updated_at.isoformat()
    }
    
    return jsonify(result)

@interview_bp.route('', methods=['POST'])
@recruiter_required
def create_interview(current_user):
    """
    Schedule a new interview
    
    Authorization header:
    Bearer <token>
    
    Request body:
    {
        "candidate_id": 1,
        "position_id": 2,
        "scheduled_time": "2023-06-01T10:00:00Z",
        "duration_minutes": 60
    }
    """
    data = request.json
    
    # Validate required fields
    required_fields = ['candidate_id', 'position_id', 'scheduled_time']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Get recruiter profile
    recruiter = Recruiter.query.filter_by(user_id=current_user.id).first()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404
    
    # Verify candidate exists
    candidate = Candidate.query.get(data['candidate_id'])
    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404
    
    # Verify position exists and belongs to the recruiter
    position = JobPosition.query.get(data['position_id'])
    if not position or position.recruiter_id != recruiter.id:
        return jsonify({"error": "Position not found or unauthorized"}), 404
    
    # Parse scheduled time
    try:
        scheduled_time = datetime.fromisoformat(data['scheduled_time'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({"error": "Invalid scheduled_time format, use ISO 8601"}), 400
    
    # Create new interview
    new_interview = Interview(
        candidate_id=data['candidate_id'],
        recruiter_id=recruiter.id,
        position_id=data['position_id'],
        scheduled_time=scheduled_time,
        duration_minutes=data.get('duration_minutes', 60),
        status='scheduled'
    )
    
    try:
        db.session.add(new_interview)
        db.session.commit()
        
        return jsonify({
            "message": "Interview scheduled successfully",
            "interview_id": new_interview.id
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to schedule interview: {str(e)}"}), 500

@interview_bp.route('/<int:interview_id>', methods=['PUT'])
@recruiter_required
def update_interview(current_user, interview_id):
    """
    Update interview details
    
    Authorization header:
    Bearer <token>
    
    Path parameters:
    - interview_id: ID of the interview
    
    Request body:
    {
        "scheduled_time": "2023-06-02T11:00:00Z",
        "duration_minutes": 45,
        "status": "completed",
        "feedback": "Candidate performed well..."
    }
    """
    data = request.json
    
    # Get recruiter profile
    recruiter = Recruiter.query.filter_by(user_id=current_user.id).first()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404
    
    # Get interview
    interview = Interview.query.get(interview_id)
    if not interview:
        return jsonify({"error": "Interview not found"}), 404
    
    # Ensure recruiter has access to this interview
    if interview.recruiter_id != recruiter.id:
        return jsonify({"error": "Unauthorized access"}), 403
    
    # Update fields
    if 'scheduled_time' in data:
        try:
            scheduled_time = datetime.fromisoformat(data['scheduled_time'].replace('Z', '+00:00'))
            interview.scheduled_time = scheduled_time
        except ValueError:
            return jsonify({"error": "Invalid scheduled_time format, use ISO 8601"}), 400
    
    if 'duration_minutes' in data:
        interview.duration_minutes = data['duration_minutes']
    
    if 'status' in data:
        valid_statuses = ['scheduled', 'completed', 'cancelled']
        if data['status'] not in valid_statuses:
            return jsonify({"error": f"Invalid status, must be one of: {', '.join(valid_statuses)}"}), 400
        interview.status = data['status']
    
    if 'feedback' in data:
        interview.feedback = data['feedback']
    
    if 'overall_score' in data:
        try:
            score = float(data['overall_score'])
            if not (0 <= score <= 1):
                return jsonify({"error": "Overall score must be between 0 and 1"}), 400
            interview.overall_score = score
        except ValueError:
            return jsonify({"error": "Overall score must be a number"}), 400
    
    try:
        db.session.commit()
        
        return jsonify({
            "message": "Interview updated successfully",
            "interview_id": interview.id
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update interview: {str(e)}"}), 500

@interview_bp.route('/<int:interview_id>/video', methods=['POST'])
@token_required
def add_video_interview(current_user, interview_id):
    """
    Add video interview recording and analysis
    
    Authorization header:
    Bearer <token>
    
    Path parameters:
    - interview_id: ID of the interview
    
    Request body:
    {
        "video_url": "https://example.com/video.mp4",
        "transcript": "Interview transcript text..."
    }
    """
    data = request.json
    
    # Validate required fields
    if 'video_url' not in data:
        return jsonify({"error": "Missing required field: video_url"}), 400
    
    # Get interview
    interview = Interview.query.get(interview_id)
    if not interview:
        return jsonify({"error": "Interview not found"}), 404
    
    # Ensure user has access to this interview
    if current_user.is_recruiter:
        recruiter = Recruiter.query.filter_by(user_id=current_user.id).first()
        if not recruiter or interview.recruiter_id != recruiter.id:
            return jsonify({"error": "Unauthorized access"}), 403
    else:
        candidate = Candidate.query.filter_by(user_id=current_user.id).first()
        if not candidate or interview.candidate_id != candidate.id:
            return jsonify({"error": "Unauthorized access"}), 403
    
    # Create new video interview
    video_interview = VideoInterview(
        interview_id=interview_id,
        video_url=data['video_url'],
        transcript=data.get('transcript', '')
    )
    
    # If transcript is provided, analyze the video interview
    if 'transcript' in data and data['transcript']:
        try:
            # Analyze video interview
            analysis = analyze_video_interview(data['transcript'])
            
            # Set scores
            video_interview.technical_score = analysis.get('technical_knowledge_score', 0)
            video_interview.communication_score = analysis.get('communication_score', 0)
            video_interview.logical_score = analysis.get('logical_reasoning_score', 0)
            video_interview.sentiment_analysis = analysis.get('sentiment_analysis', {})
            
            # Calculate overall interview score
            scores = calculate_video_interview_score(analysis)
            
            # Update interview overall score if not set yet
            if not interview.overall_score:
                interview.overall_score = scores.get('overall_video_score', 0)
        
        except Exception as e:
            # Log error but continue to save the video
            print(f"Error analyzing video interview: {str(e)}")
    
    try:
        db.session.add(video_interview)
        db.session.commit()
        
        return jsonify({
            "message": "Video interview added successfully",
            "video_id": video_interview.id,
            "technical_score": video_interview.technical_score,
            "communication_score": video_interview.communication_score,
            "logical_score": video_interview.logical_score
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to add video interview: {str(e)}"}), 500

@interview_bp.route('/<int:interview_id>/questions', methods=['POST'])
@recruiter_required
def generate_questions(current_user, interview_id):
    """
    Generate interview questions based on job and candidate
    
    Authorization header:
    Bearer <token>
    
    Path parameters:
    - interview_id: ID of the interview
    
    Request body:
    {
        "difficulty": "medium"
    }
    """
    data = request.json
    
    # Get recruiter profile
    recruiter = Recruiter.query.filter_by(user_id=current_user.id).first()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404
    
    # Get interview
    interview = Interview.query.get(interview_id)
    if not interview:
        return jsonify({"error": "Interview not found"}), 404
    
    # Ensure recruiter has access to this interview
    if interview.recruiter_id != recruiter.id:
        return jsonify({"error": "Unauthorized access"}), 403
    
    # Get job position and candidate
    position = JobPosition.query.get(interview.position_id)
    candidate = Candidate.query.get(interview.candidate_id)
    
    if not position or not candidate:
        return jsonify({"error": "Position or candidate not found"}), 404
    
    # Get candidate skills
    candidate_skill_names = [skill.name for skill in candidate.skills]
    
    # Generate interview questions
    try:
        difficulty = data.get('difficulty', 'medium')
        questions = generate_interview_questions(
            job_description=position.description,
            candidate_skills=candidate_skill_names,
            difficulty=difficulty
        )
        
        return jsonify(questions)
    
    except Exception as e:
        return jsonify({"error": f"Failed to generate questions: {str(e)}"}), 500
