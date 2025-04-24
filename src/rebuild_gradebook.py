#!/usr/bin/env python3
import os
import json
import csv
import glob

def main():
    # Directory containing the grading JSON files
    grading_dir = 'src/grading'
    
    # Pattern to match lab_05 JSON files
    pattern = os.path.join(grading_dir, 'lab_05_*_grading.json')
    
    # Output file path
    output_csv = os.path.join(grading_dir, 'lab_05_gradebook.csv')
    
    # List to store student data
    student_data = []
    
    # Process each JSON file
    for json_file in glob.glob(pattern):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
                # Format feedback
                feedback_parts = []
                
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