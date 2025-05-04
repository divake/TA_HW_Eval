#!/usr/bin/env python3
import os
import json
import csv
import glob
import sys
import re

def main():
    # Check if homework ID is provided as command line argument
    if len(sys.argv) > 1:
        hw_id = sys.argv[1]
    else:
        # Default to lab_05 for backward compatibility
        hw_id = 'lab_05'
    
    print(f"Rebuilding gradebook for {hw_id}")
    
    # Directory containing the grading JSON files
    grading_dir = 'src/grading'
    
    # Pattern to match JSON files
    pattern = os.path.join(grading_dir, f'{hw_id}_*_grading.json')
    
    # Output file path
    output_csv = os.path.join(grading_dir, f'{hw_id}_gradebook.csv')
    
    # List to store student data
    student_data = []
    
    # Check if this is a homework assignment
    is_homework = hw_id.startswith('hw_')
    
    # Process each JSON file
    for json_file in glob.glob(pattern):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
                # Format feedback
                feedback_parts = []
                
                if is_homework:
                    # For homework assignments, process all problems with scores
                    all_problems = sorted(data.get("problems", []), key=lambda p: p.get("problem_number", 0))
                    
                    # Group feedback by question
                    for i, problem in enumerate(all_problems):
                        problem_num = problem.get("problem_number", 0)
                        score = problem.get("score", 0)
                        max_score = problem.get("max_score", 10)
                        feedback = problem.get("feedback", "").strip()
                        justification = problem.get("justification", "").strip()
                        
                        # Include score for all questions
                        feedback_text = f"Q{problem_num}: ({score}/{max_score})"
                        
                        # Add comma for all but the last question
                        if i < len(all_problems) - 1:
                            feedback_text += ","
                        
                        # Add specific feedback for this question
                        if score < max_score and feedback:
                            feedback_text += f" {feedback}"
                        # If no specific feedback but there's a justification, use that
                        elif justification and not feedback and score < max_score:
                            feedback_text += f" {justification}"
                        
                        feedback_parts.append(feedback_text)
                    
                    # Join with spaces for better readability in LMS
                    feedback = " ".join(feedback_parts)
                    
                else:
                    # For lab assignments, use original format
                    # Include feedback only for problems that didn't get full marks and have non-empty feedback
                    for problem in data.get("problems", []):
                        max_score = problem.get("max_score", 10)
                        feedback = problem.get("feedback", "").strip()
                        
                        # Only include feedback if:
                        # 1. The score is less than max (not full marks)
                        # 2. There is actual feedback text (not empty)
                        if problem.get("score", max_score) < max_score and feedback:
                            feedback_parts.append(f"Q{problem['problem_number']}: {feedback}")
                    
                    # Add overall feedback if provided and not empty
                    if "overall_feedback" in data and data["overall_feedback"].strip():
                        feedback_parts.append(data["overall_feedback"])
                        
                    # Join with line breaks for better readability in LMS
                    feedback = "\n".join(feedback_parts)
                
                # Extract student information
                student_info = {
                    'Student Name': data.get('student_name', ''),
                    'Student ID': data.get('student_id', ''),
                    'Submission Date': data.get('date_submitted', ''),
                    'Grade': f"{data.get('overall_score', 0):.2f}",
                    'Feedback': feedback
                }
                
                student_data.append(student_info)
                print(f"Processed: {json_file}")
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    # Sort by student name
    student_data.sort(key=lambda x: x['Student Name'])
    
    # Write to CSV
    fieldnames = ['Student Name', 'Student ID', 'Submission Date', 'Grade', 'Feedback']
    
    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(student_data)
    
    print(f"Gradebook has been rebuilt at: {output_csv}")
    print(f"Total students processed: {len(student_data)}")

if __name__ == "__main__":
    main() 