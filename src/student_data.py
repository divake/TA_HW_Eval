"""
Functions for processing student submission data.
Includes metadata extraction, submission parsing, and CSV generation.
"""

import os
import json
import pandas as pd
import re
from typing import Dict, List, Any, Optional, Tuple

import config

def get_student_submissions(lab_id: str) -> List[Dict[str, Any]]:
    """
    Get all student submissions for a specified lab.
    
    Args:
        lab_id: ID of the lab (e.g., 'lab_05')
        
    Returns:
        List of dictionaries with student submission info
    """
    student_dir = config.STUDENT_DIR
    submissions = []
    
    # Get a list of all TXT metadata files for this lab
    txt_pattern = re.compile(f"{lab_id.replace('_', ' ').title()}_.+_attempt_.+\\.txt$")
    txt_files = []
    
    for root, _, files in os.walk(student_dir):
        for file in files:
            if txt_pattern.match(file):
                txt_files.append(os.path.join(root, file))
    
    if not txt_files:
        print(f"No student submission metadata files found for {lab_id}")
        return []
    
    # Process each metadata file
    for txt_file in txt_files:
        try:
            student_info = extract_student_info(txt_file)
            if student_info and student_info.get("submission_files"):
                submissions.append(student_info)
        except Exception as e:
            print(f"Error processing {txt_file}: {str(e)}")
    
    print(f"Found {len(submissions)} valid student submissions for {lab_id}")
    return submissions

def extract_student_info(txt_file: str) -> Dict[str, Any]:
    """
    Extract student information from a submission metadata text file.
    
    Args:
        txt_file: Path to the metadata text file
        
    Returns:
        Dictionary containing student information and submission files
    """
    try:
        with open(txt_file, 'r') as f:
            lines = f.readlines()
        
        # Extract baseline information
        student_name = "Unknown"
        student_id = "Unknown"
        date_submitted = "Unknown"
        submission_files = []
        
        # Extract the file's base name for later matching
        file_base = os.path.basename(txt_file).split('.')[0]  # Without extension
        
        in_files_section = False
        
        for line in lines:
            line = line.strip()
            if line.startswith("Name:"):
                # Format: "Name: John Doe (jdoe)"
                name_parts = line.split("(")
                if len(name_parts) > 1:
                    student_name = name_parts[0].replace("Name:", "").strip()
                    student_id_part = name_parts[1].replace(")", "").strip()
                    student_id = student_id_part
            elif line.startswith("Date Submitted:"):
                date_submitted = line.replace("Date Submitted:", "").strip()
            elif line == "Files:":
                in_files_section = True
            elif in_files_section and line.startswith("Original filename:"):
                original_filename = line.replace("Original filename:", "").strip()
            elif in_files_section and line.startswith("Filename:"):
                submission_filename = line.replace("Filename:", "").strip()
                full_path = os.path.join(os.path.dirname(txt_file), submission_filename)
                
                # Only include PDF, DOC, DOCX, and image files
                file_ext = submission_filename.lower().split('.')[-1] if '.' in submission_filename else ''
                if os.path.exists(full_path) and file_ext in ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']:
                    submission_files.append({
                        "filename": submission_filename,
                        "path": full_path,
                        "extension": file_ext
                    })
        
        # Return dictionary with student info and files
        return {
            "name": student_name,
            "id": student_id,
            "date_submitted": date_submitted,
            "metadata_file": txt_file,
            "submission_files": submission_files
        }
    
    except Exception as e:
        print(f"Error extracting student info from {txt_file}: {str(e)}")
        return {}

def save_grading_result(student_id: str, lab_id: str, grading_result: Dict[str, Any]) -> str:
    """
    Save the grading result to a JSON file.
    
    Args:
        student_id: Student identifier
        lab_id: Lab identifier
        grading_result: Dictionary with grading results
        
    Returns:
        Path to the saved file
    """
    # Create a safe filename
    safe_id = re.sub(r'[^\w]', '_', student_id)
    result_path = os.path.join(config.OUTPUT_DIR, f"{lab_id}_{safe_id}_grading.json")
    
    with open(result_path, 'w') as f:
        json.dump(grading_result, f, indent=2)
    
    return result_path

def create_gradebook_csv(lab_id: str, grading_results: List[Dict[str, Any]]) -> Optional[str]:
    """
    Create a CSV file formatted for LMS import (Blackboard).
    
    Args:
        lab_id: Lab identifier
        grading_results: List of grading result dictionaries
        
    Returns:
        Path to the generated CSV file, or None if no results
    """
    if not grading_results:
        print("No grading results to include in CSV")
        return None
    
    # Create dataframe for gradebook import
    data = []
    
    for result in grading_results:
        # Skip errored results
        if result.get("error", False):
            print(f"Skipping student {result.get('student_id', 'Unknown')} in CSV due to processing errors")
            continue
            
        # Calculate percentage
        if result.get("overall_max", 0) > 0:
            percentage = (result.get("overall_score", 0) / result.get("overall_max", 100)) * 100
        else:
            percentage = 0
            
        # Format feedback
        feedback_parts = []
        
        # Include feedback for problems that didn't get full marks
        for problem in result.get("problems", []):
            max_score = problem.get("max_score", 25)
            if problem.get("score", max_score) < max_score and "feedback" in problem:
                feedback_parts.append(f"Q{problem['problem_number']}: {problem.get('feedback', '')}")
        
        # Add overall feedback if provided
        if "overall_feedback" in result:
            feedback_parts.append(result["overall_feedback"])
            
        # Join with line breaks for better readability in LMS
        feedback = "\n".join(feedback_parts)
        
        data.append({
            "Student Name": result.get("student_name", "Unknown"),
            "Student ID": result.get("student_id", "Unknown"),
            "Submission Date": result.get("date_submitted", "Unknown"),
            "Grade": f"{percentage:.2f}",
            "Feedback": feedback
        })
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(data)
    csv_path = os.path.join(config.OUTPUT_DIR, f"{lab_id}_gradebook.csv")
    df.to_csv(csv_path, index=False)
    print(f"Created gradebook CSV file at {csv_path}")
    
    return csv_path 