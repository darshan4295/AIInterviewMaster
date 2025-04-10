import os
import json
import logging
import requests
import base64
from config import JUDGE0_API_KEY, JUDGE0_API_URL, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

def get_language_id(language):
    """
    Get the Judge0 language ID for a given programming language
    
    Args:
        language (str): Programming language name (lowercase)
        
    Returns:
        int: Judge0 language ID or None if not supported
    """
    return SUPPORTED_LANGUAGES.get(language.lower())

def execute_code(source_code, language, stdin="", timeout=10):
    """
    Execute code using the Judge0 API
    
    Args:
        source_code (str): The code to execute
        language (str): Programming language
        stdin (str): Standard input for the code
        timeout (int): Execution timeout in seconds
        
    Returns:
        dict: Execution results
    """
    language_id = get_language_id(language)
    if not language_id:
        return {
            "status": "error", 
            "message": f"Unsupported language: {language}"
        }
    
    # Base64 encode the source code and stdin
    source_code_b64 = base64.b64encode(source_code.encode()).decode()
    stdin_b64 = base64.b64encode(stdin.encode()).decode() if stdin else ""
    
    # Prepare the request data
    submission_data = {
        "source_code": source_code_b64,
        "language_id": language_id,
        "stdin": stdin_b64,
        "cpu_time_limit": timeout,
        "cpu_extra_time": 0.5,
        "wall_time_limit": timeout * 3,
        "memory_limit": 128000,  # 128 MB
        "stack_limit": 64000,     # 64 MB
        "max_processes_and_or_threads": 60,
        "number_of_runs": 1,
        "expected_output": None,
        "enable_per_process_and_thread_time_limit": False,
        "enable_per_process_and_thread_memory_limit": True,
        "max_file_size": 1024,
    }
    
    headers = {
        "Content-Type": "application/json",
    }
    
    # Add API key if available
    if JUDGE0_API_KEY:
        headers["X-RapidAPI-Key"] = JUDGE0_API_KEY
    
    try:
        # Create submission
        response = requests.post(
            f"{JUDGE0_API_URL}/submissions",
            json=submission_data,
            headers=headers
        )
        response.raise_for_status()
        
        submission = response.json()
        token = submission.get("token")
        
        if not token:
            return {"status": "error", "message": "Failed to create submission"}
        
        # Poll for submission results
        attempts = 10
        while attempts > 0:
            response = requests.get(
                f"{JUDGE0_API_URL}/submissions/{token}",
                headers=headers,
                params={"base64_encoded": "true"}
            )
            response.raise_for_status()
            
            submission_status = response.json()
            status_id = submission_status.get("status", {}).get("id")
            
            # Check if the submission is processed
            if status_id in [1, 2]:  # In Queue or Processing
                attempts -= 1
                import time
                time.sleep(1)
                continue
            
            # Decode the base64 outputs
            stdout = base64.b64decode(submission_status.get("stdout", "")).decode("utf-8", errors="replace") if submission_status.get("stdout") else ""
            stderr = base64.b64decode(submission_status.get("stderr", "")).decode("utf-8", errors="replace") if submission_status.get("stderr") else ""
            compile_output = base64.b64decode(submission_status.get("compile_output", "")).decode("utf-8", errors="replace") if submission_status.get("compile_output") else ""
            
            return {
                "status": "success",
                "status_id": status_id,
                "status_description": submission_status.get("status", {}).get("description", ""),
                "stdout": stdout,
                "stderr": stderr,
                "compile_output": compile_output,
                "time": submission_status.get("time"),
                "memory": submission_status.get("memory"),
                "exit_code": submission_status.get("exit_code"),
                "token": token
            }
        
        return {"status": "error", "message": "Timeout waiting for execution results"}
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error executing code: {str(e)}")
        return {"status": "error", "message": f"Request error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in code execution: {str(e)}")
        return {"status": "error", "message": f"Execution error: {str(e)}"}

def run_test_cases(source_code, language, test_cases):
    """
    Run code against multiple test cases
    
    Args:
        source_code (str): The code to execute
        language (str): Programming language
        test_cases (list): List of test case dictionaries with input and expected output
        
    Returns:
        dict: Test results with passing status for each case
    """
    results = []
    
    for i, test_case in enumerate(test_cases):
        input_data = test_case.get("input", "")
        expected_output = test_case.get("expected_output", "").strip()
        
        # Execute code with the test case input
        execution_result = execute_code(source_code, language, stdin=input_data)
        
        if execution_result.get("status") == "error":
            results.append({
                "test_case_id": i + 1,
                "passed": False,
                "input": input_data,
                "expected_output": expected_output,
                "actual_output": "Execution error",
                "error_message": execution_result.get("message", "Unknown error"),
                "execution_time": None,
                "memory_usage": None
            })
            continue
        
        # Check if the output matches the expected output
        actual_output = execution_result.get("stdout", "").strip()
        passed = actual_output == expected_output
        
        results.append({
            "test_case_id": i + 1,
            "passed": passed,
            "input": input_data,
            "expected_output": expected_output,
            "actual_output": actual_output,
            "error_output": execution_result.get("stderr", ""),
            "execution_time": execution_result.get("time"),
            "memory_usage": execution_result.get("memory")
        })
    
    # Calculate overall statistics
    total_cases = len(test_cases)
    passed_cases = sum(1 for r in results if r.get("passed"))
    
    return {
        "status": "success",
        "total_test_cases": total_cases,
        "passed_test_cases": passed_cases,
        "success_rate": passed_cases / total_cases if total_cases > 0 else 0,
        "results": results
    }

def generate_test_cases(problem_statement, language, num_cases=5):
    """
    Generate test cases for a coding problem using OpenAI
    
    Args:
        problem_statement (str): Description of the coding problem
        language (str): Programming language for the test cases
        num_cases (int): Number of test cases to generate
        
    Returns:
        list: Generated test cases
    """
    from .ai_assessment import openai, GPT_MODEL
    
    try:
        prompt = f"""
        Generate {num_cases} test cases for the following coding problem:
        
        Problem Statement:
        {problem_statement}
        
        For each test case, provide:
        1. Input data
        2. Expected output
        3. Description of what this test case is checking
        
        Include a mix of:
        - Basic functionality cases
        - Edge cases
        - Corner cases
        - Performance cases (where applicable)
        
        Provide the test cases in a format that can be easily parsed and executed in {language}.
        
        Respond with a JSON array in this format:
        [
            {{
                "input": "5\\n1 2 3 4 5",
                "expected_output": "15",
                "description": "Basic test with positive integers",
                "is_hidden": false
            }}
        ]
        """
        
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert at creating test cases for coding problems."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        logger.error(f"Error generating test cases: {str(e)}")
        return [
            {
                "input": "",
                "expected_output": "",
                "description": "Default test case (generation failed)",
                "is_hidden": False
            }
        ]
