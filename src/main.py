#!/usr/bin/env python3
"""
Main entry point for the lab grading system.
"""

import os
import argparse
import json
import time
import random
from typing import Dict, List, Any, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
import student_data
import document_processor
import prompt_templates
from model_interface import AnthropicModel

# Set up logging using config
logging.basicConfig(
    level=getattr(logging, config.LOGGING["level"]),
    format=config.LOGGING["format"],
    handlers=[
        logging.FileHandler(config.LOGGING["log_file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("lab_grader")

def analyze_lab_questions(lab_id: str) -> Dict[str, Any]:
    """
    Analyze the lab questions PDF to determine question count and structure.
    
    Args:
        lab_id: ID of the lab
        
    Returns:
        Dictionary with lab structure information
    """
    # Use lab structure from config if available
    if lab_id in config.LAB_STRUCTURE:
        return config.LAB_STRUCTURE[lab_id]
    
    # Fall back to generic structure
    return config.LAB_STRUCTURE["generic"]

def get_lab_questions_content(lab_id: str) -> Dict[str, Any]:
    """
    Get the lab questions content.
    
    Args:
        lab_id: ID of the lab
        
    Returns:
        Dictionary with the lab questions content
    """
    if lab_id in config.LAB_STRUCTURE:
        questions_path = config.LAB_STRUCTURE[lab_id].get("pdf_path")
        
        if questions_path and os.path.exists(questions_path):
            # Process the PDF file
            content_b64 = document_processor.file_to_base64(questions_path)
            return {
                "type": "file_base64",
                "content": content_b64,
                "media_type": "application/pdf",
                "filename": os.path.basename(questions_path)
            }
    
    # If we couldn't find or process the lab questions file
    logger.warning(f"Could not find lab questions for {lab_id}, using placeholder")
    return {
        "type": "text",
        "content": f"Lab questions for {lab_id} would be loaded here.",
    }

def process_student_submission(
    student_info: Dict[str, Any],
    lab_id: str,
    model_type: str = "anthropic",
    with_solution: bool = False,
    ) -> Dict[str, Any]:
    """
    Process a single student's submission.
    
    Args:
        student_info: Dictionary with student information and submission files
        lab_id: ID of the lab
        model_type: Type of model to use
        with_solution: Whether to include the solution in the grading
        
    Returns:
        Dictionary with grading results
    """
    student_id = student_info.get("id", "Unknown")
    student_name = student_info.get("name", "Unknown")
    logger.info(f"Processing submission for student {student_name} ({student_id})")
    
    # Check if we already have results for this student
    safe_id = student_id.replace(" ", "_")
    result_path = os.path.join(config.OUTPUT_DIR, f"{lab_id}_{safe_id}_grading.json")
    
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
    
    # Get lab structure
    lab_structure = analyze_lab_questions(lab_id)
    
    # Prepare lab instructions
    lab_questions = get_lab_questions_content(lab_id)
    
    # Create lab instruction content
    if lab_questions.get("type") == "file_base64":
        lab_instructions = [
            {
                "type": "text",
                "text": f"LAB {lab_id.upper()} QUESTIONS:"
            },
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": lab_questions.get("media_type", "application/pdf"),
                    "data": lab_questions.get("content", "")
                }
            }
        ]
    else:
        lab_instructions = [
            {
                "type": "text",
                "text": f"LAB {lab_id.upper()} QUESTIONS:"
            },
            {
                "type": "text",
                "text": lab_questions.get("content", "Lab instructions placeholder")
            }
        ]
    
    # Prepare solution if needed
    solution = None
    if with_solution:
        # Load solution from configuration path if available
        solution_path = os.path.join(config.SOLUTION_PATH, f"{lab_id}_solution.pdf")
        if os.path.exists(solution_path):
            solution_b64 = document_processor.file_to_base64(solution_path)
            solution = [
                {"type": "text", "text": "INSTRUCTOR SOLUTION:"},
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": solution_b64
                    }
                }
            ]
        else:
            # Fall back to placeholder
            solution = [
                {"type": "text", "text": "Solution would be loaded here."}
            ]
    
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
    
    # Build the complete message
    message_content = prompt_templates.build_grading_message(
        lab_id, lab_instructions, student_content, solution, lab_structure)
    
    # Send to model
    grading_result = model.send_message(message_content)
    
    # Validate the result
    expected_problem_count = lab_structure.get("total_questions", 4)
    validated_result = model.validate_grading_result(grading_result, expected_problem_count)
    
    # Add student info
    validated_result.update({
        "student_id": student_id,
        "student_name": student_name,
        "date_submitted": student_info.get("date_submitted", "Unknown")
    })
    
    # Save the result
    student_data.save_grading_result(student_id, lab_id, validated_result)
    
    return validated_result

def process_lab(
    lab_id: str, 
    model_type: str = "anthropic", 
    with_solution: bool = False,
    max_submissions: Optional[int] = None,
    student_ids: Optional[List[str]] = None,
    parallel: bool = False,
    prompt_dump: bool = False
) -> List[Dict[str, Any]]:
    """
    Process all submissions for a lab.
    
    Args:
        lab_id: ID of the lab
        model_type: Type of model to use
        with_solution: Whether to include the solution in the grading
        max_submissions: Maximum number of submissions to process (for testing)
        student_ids: List of specific student IDs to process
        parallel: Whether to process submissions in parallel
        prompt_dump: Whether to dump the prompt template to a file
        
    Returns:
        List of grading results
    """
    logger.info(f"Processing lab {lab_id} with model {model_type}")
    
    # Dump the prompt template if requested
    if prompt_dump:
        # Get lab structure
        lab_structure = analyze_lab_questions(lab_id)
        
        # Get the appropriate prompt based on whether a solution is provided
        grading_prompt = prompt_templates.get_lab_grading_prompt(lab_id, with_solution, lab_structure)
        
        # Save to file
        dump_path = os.path.join(config.OUTPUT_DIR, f"{lab_id}_prompt.txt")
        with open(dump_path, 'w') as f:
            f.write(grading_prompt)
        
        logger.info(f"Dumped prompt template to {dump_path}")
    
    # Get all student submissions
    submissions = student_data.get_student_submissions(lab_id)
    
    if not submissions:
        logger.error(f"No student submissions found for {lab_id}")
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
                executor.submit(process_student_submission, submission, lab_id, model_type, with_solution): submission
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
                
                result = process_student_submission(submission, lab_id, model_type, with_solution)
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
    csv_path = student_data.create_gradebook_csv(lab_id, all_results)
    if csv_path:
        logger.info(f"Created gradebook CSV at {csv_path}")
    
    return all_results

def main():
    """Main entry point for the lab grading system."""
    parser = argparse.ArgumentParser(description="Grade lab submissions using AI")
    parser.add_argument("lab_id", help="ID of the lab to grade (e.g., lab_05)")
    parser.add_argument("--model", choices=["anthropic"], default="anthropic",
                        help="Model to use for grading")
    parser.add_argument("--solution", action="store_true",
                        help="Include solution in grading prompt")
    parser.add_argument("--max", type=int, help="Maximum submissions to process")
    parser.add_argument("--students", nargs="+", help="Specific student IDs to process (e.g., jdoe jtsmith)")
    parser.add_argument("--parallel", action="store_true",
                        help="Process submissions in parallel")
    parser.add_argument("--dump-prompt", action="store_true",
                        help="Dump the prompt template to a file")
    
    args = parser.parse_args()
    
    # Process the lab
    results = process_lab(
        args.lab_id,
        model_type=args.model,
        with_solution=args.solution,
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