import os
import json
import re
import logging
import openai
from config import OPENAI_API_KEY

# Configure OpenAI API
openai.api_key = OPENAI_API_KEY

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
GPT_MODEL = "gpt-4o"

def analyze_technical_skills(text_content, job_requirements=None):
    """
    Analyze technical skills from a text content (resume, GitHub README, LinkedIn profile)
    
    Args:
        text_content (str): The text to analyze
        job_requirements (list, optional): List of required skills for the job
        
    Returns:
        dict: Dictionary containing identified skills and their confidence scores
    """
    try:
        prompt = f"""
        Analyze the following text and identify all technical skills present.
        For each identified skill, provide a confidence score (0-1) indicating how confident
        you are that the person possesses this skill based on the text.
        
        If job requirements are provided, also assess how well the candidate's skills match them.
        
        Text: {text_content}
        
        Job Requirements: {', '.join(job_requirements) if job_requirements else 'Not specified'}
        
        Respond with a JSON object in this format:
        {{
            "identified_skills": [
                {{"skill": "Python", "confidence": 0.95, "description": "Extensive Python experience mentioned"}},
                {{"skill": "JavaScript", "confidence": 0.8, "description": "Several JavaScript projects listed"}}
            ],
            "missing_skills": [
                {{"skill": "Docker", "importance": "high"}}
            ],
            "overall_match_score": 0.75  # Only if job requirements provided
        }}
        """
        
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "system", "content": "You are a technical skills analyzer for recruitment."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        logging.error(f"Error in analyzing technical skills: {str(e)}")
        return {
            "error": f"Failed to analyze technical skills: {str(e)}",
            "identified_skills": []
        }

def analyze_github_profile(readme_content, repo_descriptions):
    """
    Analyze GitHub profile for code quality and project contributions
    
    Args:
        readme_content (str): README content from main GitHub profile
        repo_descriptions (list): List of repository descriptions and stats
        
    Returns:
        dict: GitHub profile analysis results
    """
    try:
        prompt = f"""
        Analyze the following GitHub profile information and assess:
        1. Code quality indicators
        2. Project diversity and complexity
        3. Technical skill evidence
        4. Activity level and consistency
        
        README content: {readme_content}
        
        Repository information:
        {json.dumps(repo_descriptions, indent=2)}
        
        Respond with a JSON object in this format:
        {{
            "code_quality_score": 0.85,
            "project_diversity_score": 0.7,
            "technical_breadth_score": 0.9,
            "activity_score": 0.6,
            "overall_github_score": 0.8,
            "identified_skills": [
                {{"skill": "Python", "evidence": "7 repositories with Python as main language"}},
                {{"skill": "Machine Learning", "evidence": "3 ML projects with TensorFlow"}}
            ],
            "summary": "Candidate shows strong Python skills with focus on machine learning..."
        }}
        """
        
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "system", "content": "You are a GitHub profile analyzer for technical recruitment."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        logging.error(f"Error in analyzing GitHub profile: {str(e)}")
        return {
            "error": f"Failed to analyze GitHub profile: {str(e)}",
            "overall_github_score": 0
        }

def analyze_video_interview(transcript):
    """
    Analyze video interview transcript for technical knowledge, communication skills,
    and logical reasoning.
    
    Args:
        transcript (str): The video interview transcript
        
    Returns:
        dict: Analysis of the interview
    """
    try:
        prompt = f"""
        Analyze the following technical interview transcript and evaluate:
        1. Technical knowledge and accuracy
        2. Communication skills
        3. Logical reasoning and problem solving
        4. Overall interview performance
        
        Transcript:
        {transcript}
        
        Respond with a JSON object in this format:
        {{
            "technical_knowledge_score": 0.85,
            "communication_score": 0.7,
            "logical_reasoning_score": 0.9,
            "overall_interview_score": 0.82,
            "strengths": ["Clear explanations of algorithms", "Good problem-solving approach"],
            "weaknesses": ["Some hesitation on system design questions"],
            "sentiment_analysis": {{
                "confidence": 0.8,
                "engagement": 0.75,
                "enthusiasm": 0.65
            }},
            "summary": "Candidate demonstrated strong technical knowledge..."
        }}
        """
        
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "system", "content": "You are an expert technical interviewer."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        logging.error(f"Error in analyzing video interview: {str(e)}")
        return {
            "error": f"Failed to analyze video interview: {str(e)}",
            "overall_interview_score": 0
        }

def analyze_code_submission(code, problem_statement, language):
    """
    Analyze a candidate's code submission for correctness, efficiency, and style
    
    Args:
        code (str): The submitted code
        problem_statement (str): Description of the coding problem
        language (str): Programming language of the submission
        
    Returns:
        dict: Analysis of the code submission
    """
    try:
        prompt = f"""
        Analyze the following code submission for a coding problem:
        
        Problem Statement:
        {problem_statement}
        
        Code Submission ({language}):
        ```{language}
        {code}
        ```
        
        Evaluate the submission on:
        1. Correctness (assuming it passes test cases)
        2. Time complexity
        3. Space complexity
        4. Code style and best practices
        5. Problem-solving approach
        
        Respond with a JSON object in this format:
        {{
            "correctness_score": 1.0,
            "time_complexity": "O(n)",
            "time_complexity_score": 0.9,
            "space_complexity": "O(1)",
            "space_complexity_score": 1.0,
            "code_style_score": 0.85,
            "problem_solving_score": 0.9,
            "overall_code_score": 0.93,
            "strengths": ["Efficient algorithm", "Clear variable names"],
            "weaknesses": ["Missing comments", "Could handle edge cases better"],
            "feedback": "The solution correctly solves the problem with excellent efficiency..."
        }}
        """
        
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert code reviewer for technical interviews."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        logging.error(f"Error in analyzing code submission: {str(e)}")
        return {
            "error": f"Failed to analyze code submission: {str(e)}",
            "overall_code_score": 0
        }

def generate_interview_questions(job_description, candidate_skills, difficulty="medium"):
    """
    Generate technical interview questions based on job description and candidate skills
    
    Args:
        job_description (str): Description of the job position
        candidate_skills (list): List of candidate's skills
        difficulty (str): Question difficulty level (easy, medium, hard)
        
    Returns:
        list: Generated technical interview questions
    """
    try:
        prompt = f"""
        Generate 5 technical interview questions for a candidate with the following skills:
        {', '.join(candidate_skills)}
        
        Job Description:
        {job_description}
        
        Question difficulty level: {difficulty}
        
        Include a mix of:
        - Coding problems
        - System design questions
        - Technical knowledge questions
        - Problem-solving scenarios
        
        For each question, include:
        - The question itself
        - Expected answer or solution approach
        - What skill/knowledge it tests
        - Evaluation criteria
        
        Respond with a JSON array in this format:
        [
            {{
                "question": "Implement a function to check if a string is a palindrome",
                "type": "coding",
                "difficulty": "easy",
                "expected_answer": "A two-pointer solution comparing characters from start and end...",
                "tests_skills": ["String manipulation", "Algorithm implementation"],
                "evaluation_criteria": ["Correctness", "Edge cases handling", "Code efficiency"]
            }}
        ]
        """
        
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert technical interviewer."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        logging.error(f"Error in generating interview questions: {str(e)}")
        return {
            "error": f"Failed to generate interview questions: {str(e)}"
        }
