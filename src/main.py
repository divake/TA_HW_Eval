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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(config.OUTPUT_DIR, "grading.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("lab_grader")

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
    
    # Prepare lab instructions
    # TODO: Implement actual lab instructions loading
    # For now, we'll use a placeholder
    lab_instructions = [
        {"type": "text", "text": "Lab instructions would be loaded here."}
    ]
    
    # Prepare solution if needed
    solution = None
    if with_solution:
        # TODO: Implement actual solution loading
        # For now, we'll use a placeholder
        solution = [
            {"type": "text", "text": "Solution would be loaded here."}
        ]
    
    # Prepare student content based on the type of processed submission
    student_content = []
    
    if processed_submission.get("type") == "image_list":
        # For image-based submissions
        for i, img in enumerate(processed_submission.get("content", [])):
            student_content.append({
                "type": "text",
                "text": f"STUDENT PAGE {i+1}:"
            })
            student_content.append({
                "type": "image", 
                "source": {
                    "type": "base64", 
                    "media_type": "image/jpeg", 
                    "data": document_processor.image_to_base64(img)
                }
            })
    elif processed_submission.get("type") == "pdf_base64":
        # For direct PDF submissions
        student_content.append({
            "type": "text",
            "text": "STUDENT SUBMISSION (PDF):"
        })
        student_content.append({
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": processed_submission.get("content", "")
            }
        })
    elif processed_submission.get("type") == "mixed":
        # For mixed content (multiple files)
        for i, file_content in enumerate(processed_submission.get("content", [])):
            if file_content.get("type") == "image_list":
                for j, img in enumerate(file_content.get("content", [])):
                    student_content.append({
                        "type": "text",
                        "text": f"STUDENT FILE {i+1}, PAGE {j+1}:"
                    })
                    student_content.append({
                        "type": "image", 
                        "source": {
                            "type": "base64", 
                            "media_type": "image/jpeg", 
                            "data": document_processor.image_to_base64(img)
                        }
                    })
            elif file_content.get("type") == "pdf_base64":
                student_content.append({
                    "type": "text",
                    "text": f"STUDENT FILE {i+1} (PDF):"
                })
                student_content.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": file_content.get("content", "")
                    }
                })
    
    # Build the complete message
    message_content = prompt_templates.build_grading_message(
        lab_id, lab_instructions, student_content, solution)
    
    # Send to model
    grading_result = model.send_message(message_content)
    
    # Validate the result
    expected_problem_count = 4  # For lab_05, 4 questions
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
    parallel: bool = False
) -> List[Dict[str, Any]]:
    """
    Process all submissions for a lab.
    
    Args:
        lab_id: ID of the lab
        model_type: Type of model to use
        with_solution: Whether to include the solution in the grading
        max_submissions: Maximum number of submissions to process (for testing)
        parallel: Whether to process submissions in parallel
        
    Returns:
        List of grading results
    """
    logger.info(f"Processing lab {lab_id} with model {model_type}")
    
    # Get all student submissions
    submissions = student_data.get_student_submissions(lab_id)
    
    if not submissions:
        logger.error(f"No student submissions found for {lab_id}")
        return []
        
    logger.info(f"Found {len(submissions)} student submissions")
    
    # Limit if needed
    if max_submissions and max_submissions < len(submissions):
        logger.info(f"Limiting to {max_submissions} submissions for testing")
        submissions = submissions[:max_submissions]
    
    all_results = []
    
    if parallel:
        # Process in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(4, len(submissions))) as executor:
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
                    delay = random.uniform(10, 20)  # Random delay between 10-20 seconds
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
    parser.add_argument("--parallel", action="store_true",
                        help="Process submissions in parallel")
    
    args = parser.parse_args()
    
    # Process the lab
    results = process_lab(
        args.lab_id,
        model_type=args.model,
        with_solution=args.solution,
        max_submissions=args.max,
        parallel=args.parallel
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