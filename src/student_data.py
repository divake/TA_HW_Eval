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
import document_processor

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
    
    # Get a list of all TXT files in the student directory
    txt_files = []
    
    for root, _, files in os.walk(student_dir):
        for file in files:
            if file.endswith('.txt'):
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
                
                # Only include supported file types
                file_ext = os.path.splitext(submission_filename.lower())[1] if '.' in submission_filename else ''
                allowed_extensions = document_processor.get_allowed_file_extensions()
                
                if os.path.exists(full_path) and file_ext in allowed_extensions:
                    submission_files.append({
                        "filename": submission_filename,
                        "path": full_path,
                        "extension": file_ext.lstrip('.')
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
    Create or append to a CSV file formatted for LMS import (Blackboard).
    Checks if a gradebook CSV already exists and appends new results while avoiding duplicates.
    
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
    new_data = []
    
    # Check if this is a homework assignment
    is_homework = lab_id.startswith('hw_')
    
    # List of non-technical phrases to filter out for homework assignments
    non_technical_phrases = [
        "student", "good job", "well done", "demonstrates", "understanding", 
        "needs to", "should", "careful", "good understanding"
    ]
    
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
        
        # Process all problems, including those with full marks
        all_problems = sorted(result.get("problems", []), key=lambda p: p.get("problem_number", 0))
        
        if is_homework:
            # Group feedback by question
            for i, problem in enumerate(all_problems):
                problem_num = problem.get("problem_number", 0)
                score = problem.get("score", 0)
                max_score = problem.get("max_score", 25)
                feedback = problem.get("feedback", "").strip()
                justification = problem.get("justification", "").strip()
                
                # Include score for all questions
                feedback_text = f"Q{problem_num}: ({score}/{max_score})"
                
                # Add comma for all but the last question
                if i < len(all_problems) - 1:
                    feedback_text += ","
                
                # Add specific feedback for this question only if not full marks
                if score < max_score and feedback:
                    # Clean up the feedback to remove references to "the student"
                    cleaned_feedback = feedback
                    cleaned_feedback = cleaned_feedback.replace("The student ", "")
                    cleaned_feedback = cleaned_feedback.replace("the student ", "")
                    cleaned_feedback = cleaned_feedback.replace("Student ", "")
                    
                    # Replace common phrases with more direct alternatives
                    cleaned_feedback = cleaned_feedback.replace("correctly determined", "correctly identified")
                    cleaned_feedback = cleaned_feedback.replace("correctly calculated", "calculated")
                    cleaned_feedback = cleaned_feedback.replace("correctly computed", "computed")
                    cleaned_feedback = cleaned_feedback.replace("correctly sketched", "sketched")
                    cleaned_feedback = cleaned_feedback.replace("correctly derived", "derived")
                    cleaned_feedback = cleaned_feedback.replace("needs to", "should")
                    cleaned_feedback = cleaned_feedback.replace("has done", "")
                    cleaned_feedback = cleaned_feedback.replace("demonstrates", "shows")
                    
                    # For homework assignments, filter out non-technical language
                    contains_non_technical = any(phrase.lower() in cleaned_feedback.lower() for phrase in non_technical_phrases)
                    
                    if contains_non_technical:
                        # Convert to more technical format by extracting key technical details
                        cleaned_feedback = cleaned_feedback.replace("The student ", "")
                        cleaned_feedback = cleaned_feedback.replace("student ", "")
                        cleaned_feedback = re.sub(r'demonstrates good understanding of .+, but', '', cleaned_feedback)
                        cleaned_feedback = re.sub(r'needs to be more careful with', 'errors in', cleaned_feedback)
                        cleaned_feedback = re.sub(r'could be more rigorous', 'lacks mathematical rigor', cleaned_feedback)
                    
                    feedback_text += f" {cleaned_feedback}"
                # If no specific feedback but there's a justification and not full marks
                elif justification and not feedback and score < max_score:
                    # Clean up the justification similarly
                    cleaned_justification = justification
                    cleaned_justification = cleaned_justification.replace("The student ", "")
                    cleaned_justification = cleaned_justification.replace("the student ", "")
                    cleaned_justification = cleaned_justification.replace("Student ", "")
                    
                    # Similar replacements for justification text
                    cleaned_justification = cleaned_justification.replace("correctly determined", "correctly identified")
                    cleaned_justification = cleaned_justification.replace("correctly calculated", "calculated")
                    cleaned_justification = cleaned_justification.replace("correctly computed", "computed")
                    cleaned_justification = cleaned_justification.replace("correctly sketched", "sketched")
                    cleaned_justification = cleaned_justification.replace("correctly derived", "derived")
                    cleaned_justification = cleaned_justification.replace("needs to", "should")
                    cleaned_justification = cleaned_justification.replace("has done", "")
                    cleaned_justification = cleaned_justification.replace("demonstrates", "shows")
                    
                    feedback_text += f" {cleaned_justification}"
                
                feedback_parts.append(feedback_text)
            
            # Join with spaces for better readability in LMS
            feedback = " ".join(feedback_parts)
        else:
            # Original behavior for non-homework assignments
            for problem in all_problems:
                if problem.get("score", 0) < problem.get("max_score", 25) and problem.get("feedback", "").strip():
                    feedback_parts.append(f"Q{problem.get('problem_number', 0)}: {problem.get('feedback', '')}")
            
            # Add overall feedback if provided and not empty for non-homework assignments
            if "overall_feedback" in result and result["overall_feedback"].strip():
                feedback_parts.append(result["overall_feedback"])
                
            # Join with line breaks for better readability in LMS
            feedback = "\n".join(feedback_parts)
        
        new_data.append({
            "Student Name": result.get("student_name", "Unknown"),
            "Student ID": result.get("student_id", "Unknown"),
            "Submission Date": result.get("date_submitted", "Unknown"),
            "Grade": f"{percentage:.2f}",
            "Feedback": feedback
        })
    
    # Check if the gradebook already exists
    csv_path = os.path.join(config.OUTPUT_DIR, f"{lab_id}_gradebook.csv")
    existing_data = []
    
    if os.path.exists(csv_path):
        print(f"Appending to existing gradebook at {csv_path}")
        try:
            # Read existing CSV file
            existing_df = pd.read_csv(csv_path)
            existing_data = existing_df.to_dict('records')
        except Exception as e:
            print(f"Error reading existing gradebook: {str(e)}. Creating new file.")
    
    # Combine existing data with new data, avoiding duplicates
    combined_data = existing_data.copy()
    
    # Create a set of student IDs already in the CSV
    existing_student_ids = set(entry.get("Student ID", "").lower() for entry in existing_data)
    
    # Add new data, replacing existing entries with the same student ID
    for new_entry in new_data:
        student_id = new_entry.get("Student ID", "").lower()
        
        # If student already exists in the combined data, update their entry
        if student_id in existing_student_ids:
            for i, entry in enumerate(combined_data):
                if entry.get("Student ID", "").lower() == student_id:
                    combined_data[i] = new_entry
                    break
        else:
            # Otherwise add as a new entry
            combined_data.append(new_entry)
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(combined_data)
    df.to_csv(csv_path, index=False)
    print(f"Updated gradebook CSV file at {csv_path}")
    
    return csv_path 