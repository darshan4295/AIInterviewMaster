from flask import Blueprint, request, jsonify
from utils.auth import token_required, recruiter_required
from utils.code_execution import execute_code, run_test_cases, generate_test_cases
from utils.ai_assessment import analyze_code_submission
from utils.scoring import calculate_coding_challenge_score
from models import CodingChallenge, TestCase, Candidate, Interview, db
from datetime import datetime

coding_bp = Blueprint('coding', __name__)

@coding_bp.route('/challenges', methods=['GET'])
@token_required
def get_coding_challenges(current_user):
    """
    Get coding challenges for the authenticated user
    
    Authorization header:
    Bearer <token>
    
    Query parameters:
    - difficulty: Filter by difficulty (easy, medium, hard)
    - language: Filter by programming language
    - status: Filter by status (completed, pending)
    """
    # Get query parameters
    difficulty = request.args.get('difficulty')
    language = request.args.get('language')
    status = request.args.get('status')
    
    # Build base query depending on user type
    if current_user.is_recruiter:
        from models import Recruiter
        recruiter = Recruiter.query.filter_by(user_id=current_user.id).first()
        if not recruiter:
            return jsonify({"error": "Recruiter profile not found"}), 404
        
        # For recruiters, get challenges from their interviews
        query = CodingChallenge.query.join(Interview).filter(Interview.recruiter_id == recruiter.id)
    else:
        candidate = Candidate.query.filter_by(user_id=current_user.id).first()
        if not candidate:
            return jsonify({"error": "Candidate profile not found"}), 404
        
        query = CodingChallenge.query.filter_by(candidate_id=candidate.id)
    
    # Apply filters
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    
    if language:
        query = query.filter_by(language=language)
    
    if status == 'completed':
        query = query.filter(CodingChallenge.code_submission.isnot(None))
    elif status == 'pending':
        query = query.filter(CodingChallenge.code_submission.is_(None))
    
    # Execute query
    challenges = query.order_by(CodingChallenge.created_at.desc()).all()
    
    # Format response
    result = []
    for challenge in challenges:
        # Get test case count
        test_case_count = TestCase.query.filter_by(challenge_id=challenge.id).count()
        passed_test_count = TestCase.query.filter_by(challenge_id=challenge.id, passed=True).count()
        
        result.append({
            'id': challenge.id,
            'title': challenge.title,
            'difficulty': challenge.difficulty,
            'language': challenge.language,
            'has_submission': challenge.code_submission is not None,
            'overall_score': challenge.overall_score,
            'test_cases': test_case_count,
            'passed_tests': passed_test_count,
            'created_at': challenge.created_at.isoformat(),
            'updated_at': challenge.updated_at.isoformat()
        })
    
    return jsonify(result)

@coding_bp.route('/challenges/<int:challenge_id>', methods=['GET'])
@token_required
def get_coding_challenge(current_user, challenge_id):
    """
    Get detailed coding challenge information
    
    Authorization header:
    Bearer <token>
    
    Path parameters:
    - challenge_id: ID of the coding challenge
    """
    challenge = CodingChallenge.query.get(challenge_id)
    
    if not challenge:
        return jsonify({"error": "Coding challenge not found"}), 404
    
    # Ensure user has access to this challenge
    if current_user.is_recruiter:
        from models import Recruiter
        recruiter = Recruiter.query.filter_by(user_id=current_user.id).first()
        if not recruiter:
            return jsonify({"error": "Recruiter profile not found"}), 404
        
        if challenge.interview and challenge.interview.recruiter_id != recruiter.id:
            return jsonify({"error": "Unauthorized access"}), 403
    else:
        candidate = Candidate.query.filter_by(user_id=current_user.id).first()
        if not candidate or challenge.candidate_id != candidate.id:
            return jsonify({"error": "Unauthorized access"}), 403
    
    # Get test cases
    is_candidate = not current_user.is_recruiter
    test_cases = TestCase.query.filter_by(challenge_id=challenge.id).all()
    
    test_case_results = []
    for test_case in test_cases:
        # Hide expected output for hidden test cases if user is a candidate
        if is_candidate and test_case.is_hidden and not test_case.passed:
            expected_output = None
        else:
            expected_output = test_case.expected_output
        
        test_case_results.append({
            'id': test_case.id,
            'input_data': test_case.input_data,
            'expected_output': expected_output,
            'actual_output': test_case.actual_output,
            'is_hidden': test_case.is_hidden,
            'weight': test_case.weight,
            'passed': test_case.passed
        })
    
    result = {
        'id': challenge.id,
        'title': challenge.title,
        'description': challenge.description,
        'difficulty': challenge.difficulty,
        'language': challenge.language,
        'code_submission': challenge.code_submission,
        'correctness_score': challenge.correctness_score,
        'time_complexity_score': challenge.time_complexity_score,
        'space_complexity_score': challenge.space_complexity_score,
        'style_score': challenge.style_score,
        'overall_score': challenge.overall_score,
        'feedback': challenge.feedback,
        'test_cases': test_case_results,
        'created_at': challenge.created_at.isoformat(),
        'updated_at': challenge.updated_at.isoformat()
    }
    
    return jsonify(result)

@coding_bp.route('/challenges', methods=['POST'])
@recruiter_required
def create_coding_challenge(current_user):
    """
    Create a new coding challenge
    
    Authorization header:
    Bearer <token>
    
    Request body:
    {
        "candidate_id": 1,
        "interview_id": 2, (optional)
        "title": "Reverse a String",
        "description": "Write a function to reverse a string...",
        "difficulty": "medium",
        "language": "python",
        "generate_test_cases": true, (optional)
        "test_cases": [] (optional)
    }
    """
    data = request.json
    
    # Validate required fields
    required_fields = ['candidate_id', 'title', 'description', 'difficulty', 'language']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Verify candidate exists
    candidate = Candidate.query.get(data['candidate_id'])
    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404
    
    # Verify interview if provided
    interview_id = data.get('interview_id')
    if interview_id:
        from models import Interview
        interview = Interview.query.get(interview_id)
        if not interview:
            return jsonify({"error": "Interview not found"}), 404
        
        # Ensure recruiter has access to this interview
        from models import Recruiter
        recruiter = Recruiter.query.filter_by(user_id=current_user.id).first()
        if not recruiter or interview.recruiter_id != recruiter.id:
            return jsonify({"error": "Unauthorized access"}), 403
    
    # Create new coding challenge
    new_challenge = CodingChallenge(
        candidate_id=data['candidate_id'],
        interview_id=interview_id,
        title=data['title'],
        description=data['description'],
        difficulty=data['difficulty'],
        language=data['language']
    )
    
    try:
        db.session.add(new_challenge)
        db.session.commit()
        
        # Add test cases if provided
        if 'test_cases' in data and data['test_cases']:
            for tc_data in data['test_cases']:
                test_case = TestCase(
                    challenge_id=new_challenge.id,
                    input_data=tc_data.get('input', ''),
                    expected_output=tc_data.get('expected_output', ''),
                    is_hidden=tc_data.get('is_hidden', False),
                    weight=tc_data.get('weight', 1.0)
                )
                db.session.add(test_case)
            
            db.session.commit()
        
        # Generate test cases if requested and none provided
        elif data.get('generate_test_cases', False):
            test_cases = generate_test_cases(
                problem_statement=data['description'],
                language=data['language']
            )
            
            for tc_data in test_cases:
                test_case = TestCase(
                    challenge_id=new_challenge.id,
                    input_data=tc_data.get('input', ''),
                    expected_output=tc_data.get('expected_output', ''),
                    is_hidden=tc_data.get('is_hidden', False),
                    weight=tc_data.get('weight', 1.0) if 'weight' in tc_data else 1.0
                )
                db.session.add(test_case)
            
            db.session.commit()
        
        return jsonify({
            "message": "Coding challenge created successfully",
            "challenge_id": new_challenge.id
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create coding challenge: {str(e)}"}), 500

@coding_bp.route('/challenges/<int:challenge_id>/submit', methods=['POST'])
@token_required
def submit_solution(current_user, challenge_id):
    """
    Submit a solution for a coding challenge
    
    Authorization header:
    Bearer <token>
    
    Path parameters:
    - challenge_id: ID of the coding challenge
    
    Request body:
    {
        "code": "def solution(input_str): ..."
    }
    """
    data = request.json
    
    # Validate required fields
    if 'code' not in data:
        return jsonify({"error": "Missing required field: code"}), 400
    
    # Get challenge
    challenge = CodingChallenge.query.get(challenge_id)
    if not challenge:
        return jsonify({"error": "Coding challenge not found"}), 404
    
    # Ensure user is the candidate for this challenge
    if not current_user.is_recruiter:
        candidate = Candidate.query.filter_by(user_id=current_user.id).first()
        if not candidate or challenge.candidate_id != candidate.id:
            return jsonify({"error": "Unauthorized access"}), 403
    
    # Get test cases
    test_cases = TestCase.query.filter_by(challenge_id=challenge.id).all()
    
    if not test_cases:
        return jsonify({"error": "No test cases found for this challenge"}), 400
    
    # Prepare test cases for execution
    test_case_data = []
    for tc in test_cases:
        test_case_data.append({
            "input": tc.input_data,
            "expected_output": tc.expected_output,
            "id": tc.id
        })
    
    # Execute code against test cases
    code = data['code']
    language = challenge.language
    
    test_results = run_test_cases(code, language, test_case_data)
    
    # Update test case results
    if test_results.get("status") == "success":
        for result in test_results.get("results", []):
            test_case = next((tc for tc in test_cases if tc.id == result.get("test_case_id")), None)
            if test_case:
                test_case.passed = result.get("passed", False)
                test_case.actual_output = result.get("actual_output", "")
    
    # Analyze code submission
    code_analysis = analyze_code_submission(
        code=code,
        problem_statement=challenge.description,
        language=language
    )
    
    # Calculate overall score
    scores = calculate_coding_challenge_score(
        code_analysis=code_analysis,
        test_results=test_results
    )
    
    # Update challenge
    challenge.code_submission = code
    challenge.correctness_score = scores.get("correctness_score", 0)
    challenge.time_complexity_score = scores.get("time_complexity_score", 0)
    challenge.space_complexity_score = scores.get("space_complexity_score", 0)
    challenge.style_score = scores.get("code_style_score", 0)
    challenge.overall_score = scores.get("overall_coding_score", 0)
    challenge.feedback = code_analysis.get("feedback", "")
    challenge.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        
        return jsonify({
            "message": "Solution submitted successfully",
            "test_results": test_results,
            "code_analysis": code_analysis,
            "scores": scores
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to submit solution: {str(e)}"}), 500

@coding_bp.route('/execute', methods=['POST'])
@token_required
def execute_code_snippet(current_user):
    """
    Execute code with provided input
    
    Authorization header:
    Bearer <token>
    
    Request body:
    {
        "code": "print('Hello, World!')",
        "language": "python",
        "input": "optional input data"
    }
    """
    data = request.json
    
    # Validate required fields
    if 'code' not in data or 'language' not in data:
        return jsonify({"error": "Missing required fields: code, language"}), 400
    
    code = data['code']
    language = data['language']
    stdin = data.get('input', '')
    
    # Execute the code
    result = execute_code(code, language, stdin)
    
    return jsonify(result)

@coding_bp.route('/test-cases/generate', methods=['POST'])
@token_required
def generate_test_cases_endpoint(current_user):
    """
    Generate test cases for a coding problem
    
    Authorization header:
    Bearer <token>
    
    Request body:
    {
        "problem_statement": "Write a function to calculate the factorial of a number...",
        "language": "python",
        "num_cases": 5
    }
    """
    data = request.json
    
    # Validate required fields
    required_fields = ['problem_statement', 'language']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    num_cases = data.get('num_cases', 5)
    
    # Generate test cases
    test_cases = generate_test_cases(
        problem_statement=data['problem_statement'],
        language=data['language'],
        num_cases=num_cases
    )
    
    return jsonify(test_cases)
