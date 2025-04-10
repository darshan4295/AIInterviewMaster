import os
import re
import requests
import logging
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .ai_assessment import analyze_technical_skills, analyze_github_profile

logger = logging.getLogger(__name__)

def extract_github_username(github_url):
    """
    Extract GitHub username from GitHub profile URL
    
    Args:
        github_url (str): GitHub profile URL
        
    Returns:
        str: GitHub username or None if invalid URL
    """
    if not github_url:
        return None
    
    parsed_url = urlparse(github_url)
    if parsed_url.netloc not in ['github.com', 'www.github.com']:
        return None
    
    # Extract username from path
    path_parts = parsed_url.path.strip('/').split('/')
    if not path_parts:
        return None
    
    return path_parts[0]

def extract_linkedin_username(linkedin_url):
    """
    Extract LinkedIn username/ID from LinkedIn profile URL
    
    Args:
        linkedin_url (str): LinkedIn profile URL
        
    Returns:
        str: LinkedIn username/ID or None if invalid URL
    """
    if not linkedin_url:
        return None
    
    parsed_url = urlparse(linkedin_url)
    if parsed_url.netloc not in ['linkedin.com', 'www.linkedin.com']:
        return None
    
    # Handle different LinkedIn URL formats
    path_parts = parsed_url.path.strip('/').split('/')
    if len(path_parts) >= 2 and path_parts[0] == 'in':
        return path_parts[1]
    
    return None

def fetch_github_profile(github_username):
    """
    Fetch GitHub profile information
    
    Args:
        github_username (str): GitHub username
        
    Returns:
        dict: GitHub profile data or error message
    """
    if not github_username:
        return {"error": "Invalid GitHub username"}
    
    try:
        # GitHub API endpoints
        user_url = f"https://api.github.com/users/{github_username}"
        repos_url = f"https://api.github.com/users/{github_username}/repos"
        readme_url = f"https://api.github.com/repos/{github_username}/{github_username}/readme"
        
        # Set headers for GitHub API
        headers = {}
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        # Fetch user profile
        user_response = requests.get(user_url, headers=headers)
        user_response.raise_for_status()
        user_data = user_response.json()
        
        # Fetch repositories
        repos_response = requests.get(repos_url, headers=headers)
        repos_response.raise_for_status()
        repos_data = repos_response.json()
        
        # Try to fetch profile README
        try:
            readme_response = requests.get(readme_url, headers=headers)
            readme_response.raise_for_status()
            readme_data = readme_response.json()
            readme_content = base64.b64decode(readme_data.get("content", "")).decode()
        except:
            readme_content = ""
        
        # Process repos data to extract relevant information
        repos_info = []
        for repo in repos_data:
            if not repo.get("fork"):  # Skip forked repositories
                repos_info.append({
                    "name": repo.get("name"),
                    "description": repo.get("description"),
                    "language": repo.get("language"),
                    "stars": repo.get("stargazers_count"),
                    "forks": repo.get("forks_count"),
                    "created_at": repo.get("created_at"),
                    "updated_at": repo.get("updated_at"),
                    "topics": repo.get("topics", [])
                })
        
        # Create a summary of the profile
        github_profile = {
            "username": github_username,
            "name": user_data.get("name"),
            "bio": user_data.get("bio"),
            "public_repos": user_data.get("public_repos"),
            "followers": user_data.get("followers"),
            "following": user_data.get("following"),
            "joined_at": user_data.get("created_at"),
            "profile_readme": readme_content,
            "repositories": repos_info
        }
        
        # Analyze the GitHub profile
        analysis = analyze_github_profile(
            readme_content=readme_content,
            repo_descriptions=repos_info
        )
        
        return {
            "status": "success",
            "profile": github_profile,
            "analysis": analysis
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching GitHub profile: {str(e)}")
        return {"status": "error", "message": f"Failed to fetch GitHub profile: {str(e)}"}
    
    except Exception as e:
        logger.error(f"Unexpected error in GitHub profile parsing: {str(e)}")
        return {"status": "error", "message": f"Error parsing GitHub profile: {str(e)}"}

def parse_resume_text(resume_text):
    """
    Parse resume text to extract candidate information
    
    Args:
        resume_text (str): Plain text content of the resume
        
    Returns:
        dict: Extracted candidate information
    """
    try:
        # Use AI to extract structured data from resume
        from .ai_assessment import openai, GPT_MODEL
        
        prompt = f"""
        Extract structured information from the following resume text:
        
        {resume_text}
        
        Include:
        1. Full name
        2. Contact information (email, phone)
        3. Education (degrees, institutions, years)
        4. Work experience (companies, titles, dates, descriptions)
        5. Technical skills (programming languages, tools, frameworks)
        6. Projects (names, descriptions, technologies used)
        7. Certifications
        
        Respond with a JSON object structured like this:
        {{
            "name": "Full Name",
            "contact": {{
                "email": "email@example.com",
                "phone": "123-456-7890"
            }},
            "education": [
                {{
                    "degree": "Bachelor of Science in Computer Science",
                    "institution": "University Name",
                    "year": "2018-2022"
                }}
            ],
            "experience": [
                {{
                    "company": "Company Name",
                    "title": "Software Engineer",
                    "period": "Jan 2022 - Present",
                    "description": "Job responsibilities and achievements"
                }}
            ],
            "skills": [
                {{"category": "Programming Languages", "items": ["Python", "JavaScript"]}},
                {{"category": "Frameworks", "items": ["React", "Django"]}}
            ],
            "projects": [
                {{
                    "name": "Project Name",
                    "description": "Brief description",
                    "technologies": ["Python", "TensorFlow"]
                }}
            ],
            "certifications": [
                {{
                    "name": "AWS Certified Developer",
                    "issuer": "Amazon Web Services",
                    "date": "2021"
                }}
            ]
        }}
        """
        
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a resume parsing expert."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        parsed_data = json.loads(response.choices[0].message.content)
        
        # Get skill analysis
        skill_analysis = analyze_technical_skills(resume_text)
        
        return {
            "status": "success",
            "parsed_resume": parsed_data,
            "skill_analysis": skill_analysis
        }
    
    except Exception as e:
        logger.error(f"Error parsing resume: {str(e)}")
        return {"status": "error", "message": f"Error parsing resume: {str(e)}"}

def extract_skills_from_job_description(job_description):
    """
    Extract required skills from a job description
    
    Args:
        job_description (str): The job description text
        
    Returns:
        list: List of identified required skills
    """
    try:
        from .ai_assessment import openai, GPT_MODEL
        
        prompt = f"""
        Extract the required technical skills and qualifications from the following job description.
        
        Job Description:
        {job_description}
        
        For each skill, determine its importance level (essential, preferred, or mentioned).
        
        Respond with a JSON object in this format:
        {{
            "essential_skills": [
                {{"skill": "Python", "context": "5+ years experience with Python"}}
            ],
            "preferred_skills": [
                {{"skill": "Docker", "context": "Experience with containerization preferred"}}
            ],
            "mentioned_skills": [
                {{"skill": "Git", "context": "Mentioned in collaboration context"}}
            ]
        }}
        """
        
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a job description analyzer for technical roles."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        logger.error(f"Error extracting skills from job description: {str(e)}")
        return {
            "essential_skills": [],
            "preferred_skills": [],
            "mentioned_skills": []
        }

def match_candidate_to_job(candidate_skills, job_skills):
    """
    Match candidate skills to job requirements
    
    Args:
        candidate_skills (list): List of candidate's skills with confidence scores
        job_skills (dict): Dictionary of job skills categorized by importance
        
    Returns:
        dict: Skill match analysis
    """
    try:
        # Convert candidate skills to a dictionary for easier lookup
        candidate_skill_dict = {skill["skill"].lower(): skill["confidence"] for skill in candidate_skills}
        
        # Initialize match results
        essential_matches = []
        essential_gaps = []
        preferred_matches = []
        preferred_gaps = []
        
        # Check essential skills
        for skill_item in job_skills.get("essential_skills", []):
            skill = skill_item["skill"]
            skill_lower = skill.lower()
            
            if skill_lower in candidate_skill_dict:
                essential_matches.append({
                    "skill": skill,
                    "confidence": candidate_skill_dict[skill_lower],
                    "job_context": skill_item.get("context", "")
                })
            else:
                essential_gaps.append({
                    "skill": skill,
                    "job_context": skill_item.get("context", "")
                })
        
        # Check preferred skills
        for skill_item in job_skills.get("preferred_skills", []):
            skill = skill_item["skill"]
            skill_lower = skill.lower()
            
            if skill_lower in candidate_skill_dict:
                preferred_matches.append({
                    "skill": skill,
                    "confidence": candidate_skill_dict[skill_lower],
                    "job_context": skill_item.get("context", "")
                })
            else:
                preferred_gaps.append({
                    "skill": skill,
                    "job_context": skill_item.get("context", "")
                })
        
        # Calculate match scores
        essential_count = len(job_skills.get("essential_skills", []))
        essential_match_count = len(essential_matches)
        essential_match_score = essential_match_count / essential_count if essential_count > 0 else 1.0
        
        preferred_count = len(job_skills.get("preferred_skills", []))
        preferred_match_count = len(preferred_matches)
        preferred_match_score = preferred_match_count / preferred_count if preferred_count > 0 else 1.0
        
        # Overall match score (weighted)
        overall_match_score = (essential_match_score * 0.7) + (preferred_match_score * 0.3)
        
        return {
            "essential_match_score": essential_match_score,
            "preferred_match_score": preferred_match_score,
            "overall_match_score": overall_match_score,
            "essential_matches": essential_matches,
            "essential_gaps": essential_gaps,
            "preferred_matches": preferred_matches,
            "preferred_gaps": preferred_gaps
        }
    
    except Exception as e:
        logger.error(f"Error in skill matching: {str(e)}")
        return {
            "error": f"Skill matching failed: {str(e)}",
            "overall_match_score": 0
        }
