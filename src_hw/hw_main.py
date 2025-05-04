#!/usr/bin/env python3
"""
Main entry point for the homework grading system.
"""

import os
import argparse
import json
import time
import random
from typing import Dict, List, Any, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import from lab codebase
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
import config
import student_data
import document_processor
import prompt_templates
from model_interface import AnthropicModel

# Import specific functions we may need to customize
from student_data import extract_student_info, save_grading_result, create_gradebook_csv

# Set up logging using config
logging.basicConfig(
    level=getattr(logging, config.LOGGING["level"]),
    format=config.LOGGING["format"],
    handlers=[
        logging.FileHandler(config.LOGGING["log_file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("hw_grader")

# Global cache for reference solution to avoid uploading it multiple times
_cached_reference_solution = {}

# Homework specific paths
HW_BASE_DIR = os.path.join(os.path.dirname(__file__))
HW_SOLUTIONS_DIR = HW_BASE_DIR  # Solutions are directly in src_hw
HW_QUESTIONS_DIR = HW_BASE_DIR  # Questions are directly in src_hw
HW_SUBMISSIONS_DIR = HW_BASE_DIR  # Submissions are in hw_XX folders in src_hw

def get_cached_reference_solution(hw_id: str) -> List[Dict[str, Any]]:
    """
    Get the reference solution for a homework, using cache if available.
    
    Args:
        hw_id: ID of the homework
        
    Returns:
        List of content blocks with the reference solution
    """
    global _cached_reference_solution
    
    # Return from cache if available
    if hw_id in _cached_reference_solution:
        logger.info(f"Using cached reference solution for {hw_id}")
        return _cached_reference_solution[hw_id]
    
    # Use the specific solution path format
    hw_number = hw_id.split('_')[1] if '_' in hw_id else hw_id.replace('hw', '')
    solution_path = os.path.join(HW_SOLUTIONS_DIR, f"HW{hw_number}_Solution.pdf")
    
    if os.path.exists(solution_path):
        solution_b64 = document_processor.file_to_base64(solution_path)
        solution = [
            {"type": "text", "text": "REFERENCE SOLUTION:"},
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": solution_b64
                }
            }
        ]
        
        # Cache the solution
        _cached_reference_solution[hw_id] = solution
        logger.info(f"Cached reference solution for {hw_id} from {solution_path}")
        return solution
    else:
        # Fall back to placeholder
        logger.warning(f"Could not find reference solution at {solution_path}, using placeholder")
        solution = [
            {"type": "text", "text": f"Could not find reference solution for {hw_id}."}
        ]
        return solution

def analyze_hw_questions(hw_id: str) -> Dict[str, Any]:
    """
    Analyze the homework questions PDF to determine question count and structure.
    Reuses the lab analysis function.
    
    Args:
        hw_id: ID of the homework
        
    Returns:
        Dictionary with homework structure information
    """
    # Reuse the lab analysis function, just change cache directory
    cache_dir = os.path.join(config.OUTPUT_DIR, "hw_analysis")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{hw_id}_analysis.json")
    
    # If we have cached analysis, use it
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                logger.info(f"Using cached homework analysis for {hw_id}")
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error reading cached homework analysis for {hw_id}: {str(e)}")
    
    # Extract hw number from hw_id
    hw_number = hw_id.split('_')[1] if '_' in hw_id else hw_id.replace('hw', '')
    
    # Create a custom hw_structure with the specific pdf path
    questions_path = os.path.join(HW_QUESTIONS_DIR, f"HW{hw_number}_Question.pdf")
    if os.path.exists(questions_path):
        # Start with a basic structure
        hw_structure = {
            "pdf_path": questions_path,
            "total_questions": 4,  # Default, will be updated by AI analysis
            "max_points": 100      # Default
        }
        
        # Try to analyze it with AI
        logger.info(f"Analyzing homework questions for {hw_id} using AI")
        
        # Import the analyzer function
        from document_processor import analyze_lab_questions_with_ai
        
        # Analyze the homework questions PDF (reusing lab analysis function)
        ai_analysis = analyze_lab_questions_with_ai(questions_path, "anthropic")
        
        if not ai_analysis.get("error", False):
            # Success - cache the result
            logger.info(f"AI analysis of homework questions for {hw_id} successful")
            
            # Preserve existing fields not in AI analysis
            for key, value in hw_structure.items():
                if key not in ai_analysis:
                    ai_analysis[key] = value
            
            # Cache the analysis
            try:
                with open(cache_file, 'w') as f:
                    json.dump(ai_analysis, f, indent=2)
            except Exception as e:
                logger.warning(f"Error caching homework analysis for {hw_id}: {str(e)}")
            
            return ai_analysis
        else:
            # AI analysis failed, log error and use basic structure
            logger.warning(f"AI analysis of homework questions failed: {ai_analysis.get('error_message', 'Unknown error')}")
            return hw_structure
    
    # Use structure from config if available (fallback)
    if hw_id in config.LAB_STRUCTURE:  
        return config.LAB_STRUCTURE[hw_id]
    
    # Fall back to generic structure
    return config.LAB_STRUCTURE["generic"]

def get_hw_questions_content(hw_id: str) -> Dict[str, Any]:
    """
    Get the homework questions content.
    
    Args:
        hw_id: ID of the homework
        
    Returns:
        Dictionary with the homework questions content
    """
    # Extract hw number from hw_id
    hw_number = hw_id.split('_')[1] if '_' in hw_id else hw_id.replace('hw', '')
    
    # Use the specific questions path format
    questions_path = os.path.join(HW_QUESTIONS_DIR, f"HW{hw_number}_Question.pdf")
    
    if os.path.exists(questions_path):
        # Process the PDF file
        content_b64 = document_processor.file_to_base64(questions_path)
        return {
            "type": "file_base64",
            "content": content_b64,
            "media_type": "application/pdf",
            "filename": os.path.basename(questions_path)
        }
    
    # If we couldn't find or process the homework questions file
    logger.warning(f"Could not find homework questions at {questions_path}, using placeholder")
    return {
        "type": "text",
        "content": f"Homework questions for {hw_id} would be loaded here.",
    }

def parse_text_response(text_response: str, hw_structure: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse the text response from the model into a structured format.
    
    Args:
        text_response: The raw text response from the model
        hw_structure: Dictionary with homework structure information
        
    Returns:
        Dictionary with structured grading results
    """
    lines = text_response.strip().split('\n')
    result = {
        "problems": [],
        "overall_score": 0,
        "overall_max": hw_structure.get("max_points", 100),
        "overall_feedback": ""
    }
    
    current_problem = None
    total_score = 0
    total_possible = 0
    
    # Process line by line
    for line in lines:
        line = line.strip()
        
        # Skip introductory text
        if "grade the student" in line.lower() or not line:
            continue
            
        # Check if this is a question line
        if line.startswith("QUESTION ") or line.startswith("PROBLEM "):
            # Save previous problem if exists
            if current_problem is not None:
                result["problems"].append(current_problem)
                
            # Extract problem number
            parts = line.split()
            try:
                problem_number = int(parts[1])
            except (IndexError, ValueError):
                problem_number = len(result["problems"]) + 1
                
            # Create new problem
            current_problem = {
                "problem_number": problem_number,
                "score": 0,
                "max_score": 0,
                "feedback": "",
                "justification": ""
            }
                
        # Check if this is a score line
        elif "Score:" in line and current_problem is not None:
            score_part = line.split("Score:")[1].strip()
            if "[" in score_part and "/" in score_part and "]" in score_part:
                # Extract score format [X/Y]
                score_text = score_part.split("[")[1].split("]")[0]
                parts = score_text.split("/")
                try:
                    current_problem["score"] = float(parts[0])
                    current_problem["max_score"] = float(parts[1])
                    total_score += current_problem["score"]
                    total_possible += current_problem["max_score"]
                except (IndexError, ValueError):
                    logger.warning(f"Could not parse score: {score_part}")
                    
        # Check if this is a feedback line
        elif "Feedback:" in line and current_problem is not None:
            current_problem["feedback"] = line.split("Feedback:")[1].strip()
            
        # Check if this is a justification line
        elif "Justification:" in line and current_problem is not None:
            current_problem["justification"] = line.split("Justification:")[1].strip()
            
        # Check if this is the overall score line
        elif "OVERALL SCORE:" in line:
            # Try to extract percentage
            if "%" in line:
                try:
                    percent = line.split("%")[0].split()[-1]
                    result["overall_score"] = float(percent)
                except (IndexError, ValueError):
                    logger.warning(f"Could not parse overall percentage: {line}")
                    
            # If percentage didn't work, calculate from total
            if result["overall_score"] == 0 and total_possible > 0:
                result["overall_score"] = (total_score / total_possible) * 100
                
        # Check if this is the summary line
        elif "SUMMARY COMMENTS:" in line:
            result["overall_feedback"] = line.split("SUMMARY COMMENTS:")[1].strip()
            
        # Append to feedback or justification if continuation
        elif current_problem is not None:
            if current_problem["feedback"] and not current_problem["justification"]:
                current_problem["feedback"] += " " + line
            elif current_problem["justification"]:
                current_problem["justification"] += " " + line
    
    # Add the last problem if exists
    if current_problem is not None:
        result["problems"].append(current_problem)
    
    # Calculate overall score if not set
    if result["overall_score"] == 0 and total_possible > 0:
        result["overall_score"] = (total_score / total_possible) * 100
        
    return result

def process_student_submission(
    student_info: Dict[str, Any],
    hw_id: str,
    model_type: str = "anthropic"
    ) -> Dict[str, Any]:
    """
    Process a single student's homework submission.
    
    Args:
        student_info: Dictionary with student information and submission files
        hw_id: ID of the homework
        model_type: Type of model to use
        
    Returns:
        Dictionary with grading results
    """
    student_id = student_info.get("id", "Unknown")
    student_name = student_info.get("name", "Unknown")
    logger.info(f"Processing homework submission for student {student_name} ({student_id})")
    
    # Check if we already have results for this student
    safe_id = student_id.replace(" ", "_")
    result_path = os.path.join(config.OUTPUT_DIR, f"{hw_id}_{safe_id}_grading.json")
    
    if os.path.exists(result_path):
        logger.info(f"Found existing results for {student_id}")
        try:
            with open(result_path, 'r') as f:
                existing_result = json.load(f)
                
            # Don't reprocess if we already have valid results
            if not existing_result.get("error", False):
                existing_result.update({
                    "student_id": student_id,
                    "student_name": student_name,
                    "date_submitted": student_info.get("date_submitted", "Unknown")
                })
                return existing_result
                
            logger.info(f"Existing results had errors, reprocessing {student_id}")
        except Exception as e:
            logger.error(f"Error reading existing results for {student_id}: {str(e)}")
    
    # Initialize the model
    if model_type.lower() == "anthropic":
        model = AnthropicModel()
    else:
        logger.error(f"Unsupported model type: {model_type}")
        return {
            "error": True,
            "error_message": f"Unsupported model type: {model_type}",
            "student_id": student_id,
            "student_name": student_name
        }
        
    # Validate API key
    if not model.validate_api_key():
        logger.error(f"Invalid API key for {model_type}")
        return {
            "error": True,
            "error_message": f"Invalid API key for {model_type}",
            "student_id": student_id,
            "student_name": student_name
        }
    
    # Process submission files
    submission_files = student_info.get("submission_files", [])
    if not submission_files:
        logger.error(f"No submission files found for {student_id}")
        return {
            "error": True,
            "error_message": "No submission files found",
            "student_id": student_id,
            "student_name": student_name
        }
        
    # Prepare student submission
    processed_submission = document_processor.prepare_submission_for_model(
        submission_files, model_type)
        
    if processed_submission.get("type") == "error":
        logger.error(f"Error processing submission for {student_id}: {processed_submission.get('error', 'Unknown error')}")
        return {
            "error": True,
            "error_message": processed_submission.get("error", "Unknown error"),
            "student_id": student_id,
            "student_name": student_name
        }
    
    # Get homework structure - will use AI analysis if available
    hw_structure = analyze_hw_questions(hw_id)
    
    # Prepare homework instructions
    hw_questions = get_hw_questions_content(hw_id)
    
    # Create homework instruction content
    if hw_questions.get("type") == "file_base64":
        hw_instructions = [
            {
                "type": "text",
                "text": f"HOMEWORK {hw_id.upper()} QUESTIONS:"
            },
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": hw_questions.get("media_type", "application/pdf"),
                    "data": hw_questions.get("content", "")
                }
            }
        ]
    else:
        hw_instructions = [
            {
                "type": "text",
                "text": f"HOMEWORK {hw_id.upper()} QUESTIONS:"
            },
            {
                "type": "text",
                "text": hw_questions.get("content", "Homework instructions placeholder")
            }
        ]
    
    # Get the reference solution (using caching)
    reference_solution = get_cached_reference_solution(hw_id)
    
    # Prepare student content
    student_content = []
    student_content.append({
        "type": "text",
        "text": f"STUDENT SUBMISSION ({student_name}, {student_id}):"
    })
    
    # Process the files based on their type
    for file_info in processed_submission.get("content", []):
        file_type = file_info.get("type")
        filename = file_info.get("filename", "Unknown file")
        
        student_content.append({
            "type": "text",
            "text": f"FILE: {filename}"
        })
        
        if file_type == "file_base64":
            # For PDF and other document files
            student_content.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": file_info.get("media_type", "application/pdf"),
                    "data": file_info.get("content", "")
                }
            })
        elif file_type == "image_base64":
            # For image files
            student_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": file_info.get("media_type", "image/jpeg"),
                    "data": file_info.get("content", "")
                }
            })
    
    # Build the complete message - use our hw-specific prompt builder
    message_content = build_hw_grading_message(
        hw_id, hw_instructions, student_content, reference_solution, hw_structure)
    
    # Send to model
    grading_result = model.send_message(message_content)
    
    # Try to validate the result as JSON
    expected_problem_count = hw_structure.get("total_questions", 4)
    try:
        validated_result = model.validate_grading_result(grading_result, expected_problem_count)
    except Exception as e:
        logger.warning(f"Failed to validate as JSON: {str(e)}. Attempting to parse as text.")
        
        # If JSON validation fails, try to parse the text response
        try:
            text_response = grading_result.get("content", [{}])[0].get("text", "")
            validated_result = parse_text_response(text_response, hw_structure)
            
            # Add the raw response for debugging
            validated_result["raw_response"] = text_response[:500]  # Truncate to avoid huge files
        except Exception as parse_error:
            logger.error(f"Failed to parse text response: {str(parse_error)}")
            return {
                "error": True,
                "error_message": f"Failed to parse response: {str(parse_error)}",
                "raw_response": grading_result.get("content", [{}])[0].get("text", "")[:500],
                "student_id": student_id,
                "student_name": student_name
            }
    
    # Add student info
    validated_result.update({
        "student_id": student_id,
        "student_name": student_name,
        "date_submitted": student_info.get("date_submitted", "Unknown")
    })
    
    # Save the result
    student_data.save_grading_result(student_id, hw_id, validated_result)
    
    return validated_result

def build_hw_grading_message(
    hw_id: str,
    hw_instructions: List[Dict[str, Any]],
    student_content: List[Dict[str, Any]],
    reference_solution: List[Dict[str, Any]],
    hw_structure: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Build the grading message for a homework submission.
    
    Args:
        hw_id: ID of the homework
        hw_instructions: List of content blocks with homework instructions
        student_content: List of content blocks with student submission
        reference_solution: List of content blocks with reference solution
        hw_structure: Dictionary with homework structure information
        
    Returns:
        List of content blocks for the grading message
    """
    # Get the grading prompt for homework
    hw_grading_prompt = get_hw_grading_prompt(hw_id, hw_structure)
    
    # Build the message
    message_content = [
        {
            "type": "text",
            "text": hw_grading_prompt
        }
    ]
    
    # Add homework instructions
    message_content.extend(hw_instructions)
    
    # Add reference solution
    message_content.extend(reference_solution)
    
    # Add student content
    message_content.extend(student_content)
    
    return message_content

def get_hw_grading_prompt(hw_id: str, hw_structure: Dict[str, Any]) -> str:
    """
    Get the grading prompt for a homework.
    
    Args:
        hw_id: ID of the homework
        hw_structure: Dictionary with homework structure information
        
    Returns:
        String with the grading prompt
    """
    # Access the homework-specific prompt template
    total_questions = hw_structure.get("total_questions", 4)
    max_points = hw_structure.get("max_points", 100)
    
    # Create a detailed grading prompt
    prompt = f"""You are tasked with grading a student's homework {hw_id} submission. 
You will be provided with three items:
1. The homework assignment questions
2. The reference solution created by the professor
3. The student's submission

Your task is to:
1. Compare the student's solution to the reference solution.
2. Grade each question according to the following criteria:
   - 0 marks if the student did not attempt the question at all
   - Partial marks if the student attempted but gave a wrong or incomplete answer (be moderate to lenient in partial marking)
   - Full marks if the student provided a correct answer or one very close to the reference solution

The homework has {total_questions} questions and a maximum score of {max_points} points.

FEEDBACK GUIDELINES - FOLLOW STRICTLY:
- Provide ONLY technical feedback focusing on specific mathematical errors, incorrect equations, missing steps, or incorrect logic
- Be extremely concise - use bullet points or short phrases when possible
- Focus exclusively on the technical content (equations, calculations, theoretical concepts)
- DO NOT use subjective language like "student has done a good job" or "student needs to improve"
- DO NOT provide generalized feedback like "good understanding of concepts"
- DO NOT include any non-technical observations
- Include ONLY the precise technical issue with the specific calculation, equation, or concept
- Use mathematical notation where appropriate

For each question:
1. Analyze the student's answer
2. Compare it to the reference solution
3. Determine a score
4. Provide specific feedback ONLY if the student did not receive full marks, following the strict technical guidelines above

Format your response as follows:

QUESTION 1
Score: [X/Y]
Feedback: [Only if not full marks - use concise technical language only]
Justification: [Brief explanation of scoring]

QUESTION 2
Score: [X/Y]
Feedback: [Only if not full marks - use concise technical language only]
Justification: [Brief explanation of scoring]

...

OVERALL SCORE: [X%] ([X/{max_points} points)

SUMMARY COMMENTS: [Only technical observations about specific patterns of errors]
"""
    
    return prompt

# Add a custom function to get student submissions from a specific directory
def get_hw_student_submissions(hw_id: str, submissions_dir: str) -> List[Dict[str, Any]]:
    """
    Get all student submissions for a specified homework from a specific directory.
    
    Args:
        hw_id: ID of the homework (e.g., 'hw_04')
        submissions_dir: Directory containing student submissions
        
    Returns:
        List of dictionaries with student submission info
    """
    submissions = []
    
    # Get a list of all TXT files in the student directory
    txt_files = []
    
    for root, _, files in os.walk(submissions_dir):
        for file in files:
            if file.endswith('.txt'):
                txt_files.append(os.path.join(root, file))
    
    if not txt_files:
        logger.error(f"No student submission metadata files found for {hw_id} in {submissions_dir}")
        return []
    
    # Process each metadata file
    for txt_file in txt_files:
        try:
            student_info = extract_student_info(txt_file)
            if student_info and student_info.get("submission_files"):
                submissions.append(student_info)
        except Exception as e:
            logger.error(f"Error processing {txt_file}: {str(e)}")
    
    logger.info(f"Found {len(submissions)} valid student submissions for {hw_id}")
    return submissions

def process_homework(
    hw_id: str, 
    model_type: str = "anthropic", 
    max_submissions: Optional[int] = None,
    student_ids: Optional[List[str]] = None,
    parallel: bool = False,
    prompt_dump: bool = False
) -> List[Dict[str, Any]]:
    """
    Process all submissions for a homework.
    
    Args:
        hw_id: ID of the homework
        model_type: Type of model to use
        max_submissions: Maximum number of submissions to process (for testing)
        student_ids: List of specific student IDs to process
        parallel: Whether to process submissions in parallel
        prompt_dump: Whether to dump the prompt template to a file
        
    Returns:
        List of grading results
    """
    logger.info(f"Processing homework {hw_id} with model {model_type}")
    
    # Dump the prompt template if requested
    if prompt_dump:
        # Get homework structure
        hw_structure = analyze_hw_questions(hw_id)
        
        # Get the homework grading prompt
        hw_prompt = get_hw_grading_prompt(hw_id, hw_structure)
        
        # Save to file
        dump_path = os.path.join(config.OUTPUT_DIR, f"{hw_id}_hw_prompt.txt")
        with open(dump_path, 'w') as f:
            f.write(hw_prompt)
        
        logger.info(f"Dumped homework prompt template to {dump_path}")
    
    # Get all student submissions from the custom path
    # Extract hw number from hw_id
    hw_number = hw_id.split('_')[1] if '_' in hw_id else hw_id.replace('hw', '')
    submissions_path = os.path.join(HW_SUBMISSIONS_DIR, f"hw_{hw_number.zfill(2)}")
    
    # Check if the submissions directory exists
    if not os.path.exists(submissions_path):
        logger.error(f"Submissions directory not found: {submissions_path}")
        return []
    
    # Get submissions using our custom function
    submissions = get_hw_student_submissions(hw_id, submissions_path)
    
    if not submissions:
        logger.error(f"No student submissions found for {hw_id} in {submissions_path}")
        return []
        
    logger.info(f"Found {len(submissions)} student submissions")
    
    # Filter submissions by student ID if specified
    if student_ids:
        logger.info(f"Filtering submissions for specific students: {', '.join(student_ids)}")
        filtered_submissions = []
        for submission in submissions:
            if submission.get("id", "").lower() in [s.lower() for s in student_ids]:
                filtered_submissions.append(submission)
        
        submissions = filtered_submissions
        logger.info(f"Filtered to {len(submissions)} submissions")
    
    # Limit if needed
    if max_submissions and max_submissions < len(submissions):
        logger.info(f"Limiting to {max_submissions} submissions for testing")
        submissions = submissions[:max_submissions]
    
    all_results = []
    
    if parallel:
        # Process in parallel using ThreadPoolExecutor
        worker_count = min(4, len(submissions))
        logger.info(f"Processing {len(submissions)} submissions in parallel with {worker_count} workers")
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_submission = {
                executor.submit(process_student_submission, submission, hw_id, model_type): submission
                for submission in submissions
            }
            
            for future in as_completed(future_to_submission):
                submission = future_to_submission[future]
                try:
                    result = future.result()
                    all_results.append(result)
                    student_id = submission.get("id", "Unknown")
                    logger.info(f"Completed grading for {student_id}")
                except Exception as e:
                    student_id = submission.get("id", "Unknown")
                    logger.error(f"Error processing {student_id}: {str(e)}")
                    all_results.append({
                        "error": True,
                        "error_message": f"Processing error: {str(e)}",
                        "student_id": student_id,
                        "student_name": submission.get("name", "Unknown")
                    })
    else:
        # Process sequentially
        for i, submission in enumerate(submissions):
            logger.info(f"Processing submission {i+1}/{len(submissions)}")
            
            try:
                # Add delay between submissions to avoid rate limits
                if i > 0:
                    # Use rate limit delay range from config
                    min_delay, max_delay = config.API_SETTINGS["rate_limit_delay"]
                    delay = random.uniform(min_delay, max_delay)
                    logger.info(f"Waiting {delay:.2f} seconds before processing next submission...")
                    time.sleep(delay)
                
                result = process_student_submission(submission, hw_id, model_type)
                all_results.append(result)
            except Exception as e:
                student_id = submission.get("id", "Unknown")
                logger.error(f"Error processing {student_id}: {str(e)}")
                all_results.append({
                    "error": True,
                    "error_message": f"Processing error: {str(e)}",
                    "student_id": student_id,
                    "student_name": submission.get("name", "Unknown")
                })
    
    # Create CSV file for gradebook import
    csv_path = create_gradebook_csv(hw_id, all_results)
    if csv_path:
        logger.info(f"Created gradebook CSV at {csv_path}")
    
    return all_results

def main():
    """Main entry point for the homework grading system."""
    parser = argparse.ArgumentParser(description="Grade homework submissions using AI")
    parser.add_argument("hw_id", help="ID of the homework to grade (e.g., hw_01)")
    parser.add_argument("--model", choices=["anthropic"], default="anthropic",
                        help="Model to use for grading")
    parser.add_argument("--max", type=int, help="Maximum submissions to process")
    parser.add_argument("--students", nargs="+", help="Specific student IDs to process (e.g., jdoe jtsmith)")
    parser.add_argument("--parallel", action="store_true",
                        help="Process submissions in parallel")
    parser.add_argument("--dump-prompt", action="store_true",
                        help="Dump the prompt template to a file")
    
    args = parser.parse_args()
    
    # Process the homework
    results = process_homework(
        args.hw_id,
        model_type=args.model,
        max_submissions=args.max,
        student_ids=args.students,
        parallel=args.parallel,
        prompt_dump=args.dump_prompt
    )
    
    # Print summary
    total = len(results)
    errors = sum(1 for r in results if r.get("error", False))
    success = total - errors
    
    if total > 0:
        avg_score = sum(r.get("overall_score", 0) for r in results if not r.get("error", False)) / max(1, success)
        logger.info(f"Processed {total} submissions: {success} successful, {errors} errors")
        logger.info(f"Average score: {avg_score:.2f}")
    else:
        logger.info("No submissions were processed")

if __name__ == "__main__":
    main() 