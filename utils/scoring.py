import logging
import numpy as np
from config import SCORING_CONFIG

logger = logging.getLogger(__name__)

def calculate_profile_score(github_analysis, resume_analysis, linkedin_analysis=None):
    """
    Calculate profile score based on GitHub, resume, and LinkedIn analysis
    
    Args:
        github_analysis (dict): GitHub profile analysis results
        resume_analysis (dict): Resume analysis results
        linkedin_analysis (dict, optional): LinkedIn analysis results
        
    Returns:
        dict: Profile score components and overall profile score
    """
    try:
        scores = {}
        
        # GitHub score
        if github_analysis and "overall_github_score" in github_analysis:
            scores["github_score"] = github_analysis.get("overall_github_score", 0)
        else:
            scores["github_score"] = 0
        
        # Resume score (based on skill confidence)
        if resume_analysis and "skill_analysis" in resume_analysis:
            skills = resume_analysis.get("skill_analysis", {}).get("identified_skills", [])
            if skills:
                confidence_scores = [skill.get("confidence", 0) for skill in skills]
                scores["resume_score"] = sum(confidence_scores) / len(confidence_scores)
            else:
                scores["resume_score"] = 0
        else:
            scores["resume_score"] = 0
        
        # LinkedIn score (if available)
        if linkedin_analysis and "skill_confidence" in linkedin_analysis:
            scores["linkedin_score"] = linkedin_analysis.get("skill_confidence", 0)
        else:
            scores["linkedin_score"] = 0
        
        # Calculate overall profile score
        available_scores = [s for s in scores.values() if s > 0]
        if available_scores:
            scores["overall_profile_score"] = sum(available_scores) / len(available_scores)
        else:
            scores["overall_profile_score"] = 0
        
        return scores
    
    except Exception as e:
        logger.error(f"Error calculating profile score: {str(e)}")
        return {"error": str(e), "overall_profile_score": 0}

def calculate_video_interview_score(video_analysis):
    """
    Calculate video interview score based on technical knowledge, communication, and reasoning
    
    Args:
        video_analysis (dict): Video interview analysis results
        
    Returns:
        dict: Video interview score components and overall score
    """
    try:
        # Extract component scores
        technical_score = video_analysis.get("technical_knowledge_score", 0)
        communication_score = video_analysis.get("communication_score", 0)
        reasoning_score = video_analysis.get("logical_reasoning_score", 0)
        
        # Apply component weights
        weights = {
            "technical": 0.5,
            "communication": 0.3,
            "reasoning": 0.2
        }
        
        # Calculate overall score
        overall_score = (
            technical_score * weights["technical"] +
            communication_score * weights["communication"] +
            reasoning_score * weights["reasoning"]
        )
        
        return {
            "technical_score": technical_score,
            "communication_score": communication_score,
            "reasoning_score": reasoning_score,
            "overall_video_score": overall_score
        }
    
    except Exception as e:
        logger.error(f"Error calculating video interview score: {str(e)}")
        return {"error": str(e), "overall_video_score": 0}

def calculate_coding_challenge_score(code_analysis, test_results):
    """
    Calculate coding challenge score based on code analysis and test results
    
    Args:
        code_analysis (dict): Code submission analysis
        test_results (dict): Test case execution results
        
    Returns:
        dict: Coding challenge score components and overall score
    """
    try:
        # Extract scores from code analysis
        correctness_score = code_analysis.get("correctness_score", 0)
        time_complexity_score = code_analysis.get("time_complexity_score", 0)
        space_complexity_score = code_analysis.get("space_complexity_score", 0)
        code_style_score = code_analysis.get("code_style_score", 0)
        
        # Test case execution success rate
        test_success_rate = test_results.get("success_rate", 0)
        
        # Apply component weights
        weights = {
            "correctness": 0.4,
            "test_success": 0.3,
            "time_complexity": 0.1,
            "space_complexity": 0.1,
            "code_style": 0.1
        }
        
        # Calculate overall score
        overall_score = (
            correctness_score * weights["correctness"] +
            test_success_rate * weights["test_success"] +
            time_complexity_score * weights["time_complexity"] +
            space_complexity_score * weights["space_complexity"] +
            code_style_score * weights["code_style"]
        )
        
        return {
            "correctness_score": correctness_score,
            "test_success_rate": test_success_rate,
            "time_complexity_score": time_complexity_score,
            "space_complexity_score": space_complexity_score,
            "code_style_score": code_style_score,
            "overall_coding_score": overall_score
        }
    
    except Exception as e:
        logger.error(f"Error calculating coding challenge score: {str(e)}")
        return {"error": str(e), "overall_coding_score": 0}

def calculate_managerial_round_score(managerial_analysis):
    """
    Calculate managerial round score based on leadership, behavior, and cultural fit
    
    Args:
        managerial_analysis (dict): Managerial round analysis results
        
    Returns:
        dict: Managerial round score components and overall score
    """
    try:
        # Extract component scores
        leadership_score = managerial_analysis.get("leadership_score", 0)
        behavior_score = managerial_analysis.get("behavior_score", 0)
        cultural_fit_score = managerial_analysis.get("cultural_fit_score", 0)
        decision_making_score = managerial_analysis.get("decision_making_score", 0)
        
        # Apply component weights
        weights = {
            "leadership": 0.3,
            "behavior": 0.2,
            "cultural_fit": 0.3,
            "decision_making": 0.2
        }
        
        # Calculate overall score
        overall_score = (
            leadership_score * weights["leadership"] +
            behavior_score * weights["behavior"] +
            cultural_fit_score * weights["cultural_fit"] +
            decision_making_score * weights["decision_making"]
        )
        
        return {
            "leadership_score": leadership_score,
            "behavior_score": behavior_score,
            "cultural_fit_score": cultural_fit_score,
            "decision_making_score": decision_making_score,
            "overall_managerial_score": overall_score
        }
    
    except Exception as e:
        logger.error(f"Error calculating managerial round score: {str(e)}")
        return {"error": str(e), "overall_managerial_score": 0}

def calculate_final_candidate_score(profile_score, video_score, coding_score, managerial_score=None):
    """
    Calculate final candidate score across all assessment phases
    
    Args:
        profile_score (float): Profile assessment score
        video_score (float): Video interview score
        coding_score (float): Coding challenge score
        managerial_score (float, optional): Managerial round score
        
    Returns:
        dict: Final score with phase breakdown and overall score
    """
    try:
        # Get scoring weights from config
        weights = {
            "profile": SCORING_CONFIG.get("profile_weight", 0.2),
            "video": SCORING_CONFIG.get("video_interview_weight", 0.3),
            "coding": SCORING_CONFIG.get("coding_challenge_weight", 0.4),
            "managerial": SCORING_CONFIG.get("managerial_round_weight", 0.1)
        }
        
        # Initialize score components
        scores = {
            "profile_score": profile_score,
            "video_score": video_score,
            "coding_score": coding_score
        }
        
        if managerial_score is not None:
            scores["managerial_score"] = managerial_score
            
            # Calculate weighted average with all phases
            overall_score = (
                profile_score * weights["profile"] +
                video_score * weights["video"] +
                coding_score * weights["coding"] +
                managerial_score * weights["managerial"]
            )
        else:
            # Adjust weights for missing managerial round
            adjusted_weights = {
                "profile": weights["profile"] / (1 - weights["managerial"]),
                "video": weights["video"] / (1 - weights["managerial"]),
                "coding": weights["coding"] / (1 - weights["managerial"])
            }
            
            # Calculate weighted average without managerial round
            overall_score = (
                profile_score * adjusted_weights["profile"] +
                video_score * adjusted_weights["video"] +
                coding_score * adjusted_weights["coding"]
            )
        
        # Add overall score to result
        scores["overall_candidate_score"] = overall_score
        
        # Map score to qualitative assessment
        if overall_score >= 0.85:
            scores["assessment"] = "Excellent Candidate"
        elif overall_score >= 0.75:
            scores["assessment"] = "Strong Candidate"
        elif overall_score >= 0.65:
            scores["assessment"] = "Good Candidate"
        elif overall_score >= 0.5:
            scores["assessment"] = "Average Candidate"
        else:
            scores["assessment"] = "Below Average Candidate"
        
        return scores
    
    except Exception as e:
        logger.error(f"Error calculating final candidate score: {str(e)}")
        return {"error": str(e), "overall_candidate_score": 0}
