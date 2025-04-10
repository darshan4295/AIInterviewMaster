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

def analyze_video_interview(transcript, include_detailed_sentiment=False):
    """
    Analyze video interview transcript for technical knowledge, communication skills,
    logical reasoning, and emotional/sentiment patterns.
    
    Args:
        transcript (str): The video interview transcript
        include_detailed_sentiment (bool): Whether to include detailed sentiment analysis
        
    Returns:
        dict: Analysis of the interview
    """
    try:
        basic_prompt = f"""
        Analyze the following technical interview transcript and evaluate:
        1. Technical knowledge and accuracy
        2. Communication skills
        3. Logical reasoning and problem solving
        4. Overall interview performance
        5. Emotional tone and sentiment patterns
        
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
                "enthusiasm": 0.65,
                "positivity": 0.7,
                "stress_level": 0.4
            }},
            "summary": "Candidate demonstrated strong technical knowledge..."
        }}
        """
        
        # Enhanced prompt with more detailed sentiment analysis
        detailed_prompt = f"""
        Analyze the following technical interview transcript and evaluate:
        1. Technical knowledge and accuracy
        2. Communication skills
        3. Logical reasoning and problem solving
        4. Overall interview performance
        5. Detailed emotional analysis
        
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
                "enthusiasm": 0.65,
                "positivity": 0.7,
                "stress_level": 0.4,
                "detailed_emotions": [
                    {{"emotion": "confidence", "score": 0.75, "trigger_phrases": ["I've worked extensively with...", "I'm certain that..."]}},
                    {{"emotion": "uncertainty", "score": 0.3, "trigger_phrases": ["I think maybe...", "I'm not entirely sure..."]}},
                    {{"emotion": "excitement", "score": 0.8, "trigger_phrases": ["I'm really passionate about...", "I loved working on..."]}}
                ],
                "emotional_progression": "Started nervously but gained confidence as the interview progressed",
                "cultural_fit_indicators": ["Mentions teamwork positively", "Values align with company mission"]
            }},
            "communication_patterns": {{
                "clarity": 0.8,
                "conciseness": 0.7,
                "technical_language_proficiency": 0.85,
                "listening_skills": 0.9
            }},
            "summary": "Candidate demonstrated strong technical knowledge..."
        }}
        """
        
        # Choose which prompt to use
        prompt = detailed_prompt if include_detailed_sentiment else basic_prompt
        
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "system", "content": "You are an expert technical interviewer with skills in emotional intelligence and behavioral analysis."},
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

def analyze_code_submission(code, problem_statement, language, check_plagiarism=False, reference_solutions=None):
    """
    Analyze a candidate's code submission for correctness, efficiency, and style.
    Optionally checks for potential plagiarism against reference solutions.
    
    Args:
        code (str): The submitted code
        problem_statement (str): Description of the coding problem
        language (str): Programming language of the submission
        check_plagiarism (bool): Whether to check for potential plagiarism
        reference_solutions (list): List of reference solutions to check against
        
    Returns:
        dict: Analysis of the code submission
    """
    try:
        basic_prompt = f"""
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
        
        # If we're not checking for plagiarism, use the basic prompt
        if not check_plagiarism or not reference_solutions:
            prompt = basic_prompt
        else:
            # Format reference solutions for comparison
            formatted_references = "\n\n".join([
                f"Reference Solution {i+1}:\n```{language}\n{solution}\n```"
                for i, solution in enumerate(reference_solutions)
            ])
            
            # Enhanced prompt with plagiarism detection
            plagiarism_prompt = f"""
            Analyze the following code submission for a coding problem and check for potential plagiarism:
            
            Problem Statement:
            {problem_statement}
            
            Candidate's Code Submission ({language}):
            ```{language}
            {code}
            ```
            
            Reference Solutions to check against:
            {formatted_references}
            
            Evaluate the submission on:
            1. Correctness (assuming it passes test cases)
            2. Time complexity
            3. Space complexity
            4. Code style and best practices
            5. Problem-solving approach
            6. Originality and potential plagiarism
            
            For plagiarism detection, consider:
            - Exact or near-exact code matches
            - Distinctive algorithm implementations that are uncommon
            - Unusual variable naming patterns that match reference solutions
            - Unique code structure/organization similarities
            - Comment patterns or distinctive code style elements
            
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
                "plagiarism_detection": {{
                    "originality_score": 0.95,
                    "potential_plagiarism": false,
                    "similarity_details": [
                        {{
                            "reference_solution_index": 0,
                            "similarity_score": 0.15,
                            "similar_elements": ["Basic algorithm structure is common for this problem type"],
                            "is_concerning": false
                        }}
                    ],
                    "assessment": "The solution appears to be the candidate's original work with standard implementation patterns for this problem type."
                }},
                "strengths": ["Efficient algorithm", "Clear variable names"],
                "weaknesses": ["Missing comments", "Could handle edge cases better"],
                "feedback": "The solution correctly solves the problem with excellent efficiency..."
            }}
            """
            
            prompt = plagiarism_prompt
        
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert code reviewer for technical interviews with experience in plagiarism detection."},
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

def evaluate_cultural_fit(transcript, company_values=None, team_dynamics=None):
    """
    Evaluate a candidate's cultural fit based on interview transcript
    
    Args:
        transcript (str): The interview transcript
        company_values (list, optional): List of company values to match against
        team_dynamics (dict, optional): Description of team dynamics and culture
        
    Returns:
        dict: Cultural fit evaluation
    """
    try:
        # Prepare company values if provided
        company_values_str = ""
        if company_values:
            company_values_str = "Company Values:\n" + "\n".join([f"- {value}" for value in company_values])
        
        # Prepare team dynamics if provided
        team_dynamics_str = ""
        if team_dynamics:
            team_dynamics_str = "Team Dynamics:\n"
            for key, value in team_dynamics.items():
                team_dynamics_str += f"- {key}: {value}\n"
        
        prompt = f"""
        Evaluate the cultural fit of a candidate based on the following interview transcript:
        
        {transcript}
        
        {company_values_str}
        
        {team_dynamics_str}
        
        Analyze the following aspects:
        1. Value alignment (how well the candidate's expressed values match company values)
        2. Communication style
        3. Work preferences and habits
        4. Team collaboration approach
        5. Leadership style (if applicable)
        6. Problem-solving approach
        7. Adaptability and learning mindset
        
        Respond with a JSON object in this format:
        {{
            "cultural_fit_score": 0.85,
            "value_alignment": {{
                "score": 0.9,
                "matching_values": ["Innovation", "Customer focus"],
                "misaligned_values": ["Work-life balance expectations"]
            }},
            "communication_style": {{
                "description": "Direct and clear communicator with a collaborative tone",
                "strengths": ["Clarity", "Active listening"],
                "areas_for_improvement": ["Could be more concise"]
            }},
            "team_collaboration": {{
                "score": 0.8,
                "strengths": ["Enjoys mentoring others", "Values diverse perspectives"],
                "concerns": ["May need guidance on conflict resolution"]
            }},
            "adaptability": {{
                "score": 0.75,
                "evidence": ["Described successfully pivoting during project challenges"]
            }},
            "overall_assessment": "Strong cultural fit with notable alignment in core values...",
            "recommendations": ["Would fit well in teams that value autonomy", "May thrive in innovative projects"]
        }}
        """
        
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert in organizational psychology and cultural fit assessment."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        logging.error(f"Error in evaluating cultural fit: {str(e)}")
        return {
            "error": f"Failed to evaluate cultural fit: {str(e)}",
            "cultural_fit_score": 0
        }

def generate_interview_questions(job_description, candidate_skills, difficulty="medium", include_cultural=False):
    """
    Generate technical interview questions based on job description and candidate skills
    
    Args:
        job_description (str): Description of the job position
        candidate_skills (list): List of candidate's skills
        difficulty (str): Question difficulty level (easy, medium, hard)
        include_cultural (bool): Whether to include cultural fit questions
        
    Returns:
        list: Generated technical interview questions
    """
    try:
        if not include_cultural:
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
        else:
            prompt = f"""
            Generate 7 interview questions for a candidate with the following skills:
            {', '.join(candidate_skills)}
            
            Job Description:
            {job_description}
            
            Include a mix of:
            - Technical questions (difficulty: {difficulty})
            - Cultural fit questions
            - Behavioral questions
            - Team collaboration scenarios
            - Problem-solving approaches
            
            For each question, include:
            - The question itself
            - Expected answer or solution approach
            - What skill/knowledge/trait it tests
            - Evaluation criteria
            
            The cultural fit and behavioral questions should help assess:
            - Alignment with company values
            - Teamwork approach
            - Communication style
            - Adaptability
            - Initiative and ownership
            
            Respond with a JSON array in this format:
            [
                {{
                    "question": "Implement a function to check if a string is a palindrome",
                    "type": "coding",
                    "difficulty": "easy",
                    "expected_answer": "A two-pointer solution comparing characters from start and end...",
                    "tests_skills": ["String manipulation", "Algorithm implementation"],
                    "evaluation_criteria": ["Correctness", "Edge cases handling", "Code efficiency"]
                }},
                {{
                    "question": "Describe a time when you had to make a difficult decision with limited information. How did you approach the problem?",
                    "type": "behavioral",
                    "expected_answer": "Looking for structured decision-making process, risk assessment, and learning from outcomes",
                    "tests_traits": ["Decision-making", "Risk assessment", "Learning mindset"],
                    "evaluation_criteria": ["Clarity of thought process", "Consideration of alternatives", "Reflection on outcomes"]
                }}
            ]
            """
        
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert technical and behavioral interviewer."},
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
