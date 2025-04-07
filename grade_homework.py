import os
import json
import pandas as pd
from anthropic import Anthropic
import base64
from pdf2image import convert_from_path
from io import BytesIO
from PIL import Image
import time
import random

# Initialize Anthropic client with your API key
anthropic_api_key = ""  # Replace with your actual API key
anthropic_client = Anthropic(api_key=anthropic_api_key)

# Paths
student_dir = "/ssd_4TB/divake/BB_ECE317/gradebook"
question_path = "/ssd_4TB/divake/BB_ECE317/ECE_317_Homework_3_Question.pdf"
solution_path = "/ssd_4TB/divake/BB_ECE317/HW3_Solution.pdf"
output_dir = "/ssd_4TB/divake/BB_ECE317/graded_results"

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

def pdf_to_images(pdf_path, dpi=100, max_pages=None):
    """Convert PDF to a list of images with reduced quality"""
    print(f"Converting PDF to images: {pdf_path}")
    try:
        pages = convert_from_path(pdf_path, dpi=dpi)
        
        if max_pages and len(pages) > max_pages:
            print(f"PDF has {len(pages)} pages, limiting to first {max_pages} pages")
            pages = pages[:max_pages]
        
        return pages
    except Exception as e:
        print(f"Error converting PDF to images: {str(e)}")
        return []

def compress_image(image, quality=40, max_size=(800, 800)):
    """Compress and resize an image to reduce file size"""
    # Resize if needed
    if image.width > max_size[0] or image.height > max_size[1]:
        image.thumbnail(max_size, Image.LANCZOS)
    
    return image

def image_to_base64(image, format="JPEG", quality=40):
    """Convert PIL Image to base64 string with compression"""
    buffered = BytesIO()
    image.save(buffered, format=format, quality=quality, optimize=True)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def prepare_reference_images():
    """Prepare reference images that combine both question and solution PDFs"""
    print("Preparing reference images (question and solution)...")
    
    # Convert question PDF to images
    question_images = pdf_to_images(question_path, dpi=100, max_pages=5)
    question_images = [compress_image(img) for img in question_images]
    print(f"Processed question PDF with {len(question_images)} pages")
    
    # Convert solution PDF to images
    solution_images = pdf_to_images(solution_path, dpi=100, max_pages=5)
    solution_images = [compress_image(img) for img in solution_images]
    print(f"Processed solution PDF with {len(solution_images)} pages")
    
    return {
        'question_images': question_images,
        'solution_images': solution_images
    }

def process_submission(submission_path, student_identifier, reference_images=None):
    """Process a single student submission"""
    print(f"Processing submission for student {student_identifier}...")
    
    try:
        # If reference images weren't provided, create them now
        if reference_images is None:
            reference_images = prepare_reference_images()
            
        question_images = reference_images['question_images']
        solution_images = reference_images['solution_images']
        
        # Convert student submission to images
        if submission_path.lower().endswith('.pdf'):
            student_images = pdf_to_images(submission_path, dpi=100, max_pages=5)
            student_images = [compress_image(img) for img in student_images]
            print(f"Processed student submission with {len(student_images)} pages")
        else:
            # If it's already an image file, just load it
            try:
                img = Image.open(submission_path)
                student_images = [compress_image(img)]
            except Exception as e:
                print(f"Error loading image file: {str(e)}")
                return {
                    "problems": [],
                    "overall_score": 0,
                    "overall_max": 100,
                    "overall_feedback": f"Error loading image file: {str(e)}",
                    "error": True
                }
        
        # Create the grading prompt
        grading_prompt = """
        You are an expert teaching assistant grading a Digital Signal Processing (ECE317) homework assignment.
        
        I have provided multiple images in the following order:
        1. First set: The homework questions
        2. Second set: The solution to the assignment
        3. Third set: The student's submission
        
        This homework has 5 questions, each worth 20 marks (for a total of 100 marks).
        
        Please grade this submission carefully, following these specific guidelines:
        - Award full marks (20) if the answer is perfect and matches the solution
        - Award partial marks (15-18) if the answer is partially correct or has minor errors
        - Award 0 marks if the question is not attempted
        - Be generous with partial credit (prefer to give 18-15 rather than lower scores)
        
        For ONLY the questions that did NOT receive full marks (20), provide a single line of 
        feedback explaining why marks were deducted. The feedback should be very brief and to the point.
        
        Format your response as JSON with the following structure:
        {
            "problems": [
                {
                    "problem_number": 1,
                    "score": 20,  // Full marks example, no feedback needed
                    "max_score": 20
                },
                {
                    "problem_number": 2,
                    "score": 18,  // Partial marks example
                    "max_score": 20,
                    "feedback": "Missed the aliasing explanation in the frequency domain."
                },
                // Repeat for all 5 questions
            ],
            "overall_score": Z,  // Sum of all 5 question scores
            "overall_max": 100,
            "overall_feedback": "Brief summary of the student's overall performance"
        }
        
        Return only the JSON with no additional text. Ensure you grade all 5 questions.
        """
        
        # Prepare message content with images
        message_content = [{"type": "text", "text": grading_prompt}]
        
        # Add question images
        for i, img in enumerate(question_images):
            message_content.append({
                "type": "text",
                "text": f"QUESTION PAGE {i+1}:"
            })
            message_content.append({
                "type": "image", 
                "source": {
                    "type": "base64", 
                    "media_type": "image/jpeg", 
                    "data": image_to_base64(img)
                }
            })
            
        # Add solution images
        for i, img in enumerate(solution_images):
            message_content.append({
                "type": "text",
                "text": f"SOLUTION PAGE {i+1}:"
            })
            message_content.append({
                "type": "image", 
                "source": {
                    "type": "base64", 
                    "media_type": "image/jpeg", 
                    "data": image_to_base64(img)
                }
            })
        
        # Add student images
        message_content.append({
            "type": "text",
            "text": "STUDENT SUBMISSION:"
        })
        
        for i, img in enumerate(student_images):
            message_content.append({
                "type": "text",
                "text": f"STUDENT PAGE {i+1}:"
            })
            message_content.append({
                "type": "image", 
                "source": {
                    "type": "base64", 
                    "media_type": "image/jpeg", 
                    "data": image_to_base64(img)
                }
            })
        
        # Add retry logic with exponential backoff
        max_retries = 5
        base_delay = 10  # seconds
        
        for attempt in range(max_retries):
            try:
                print(f"API attempt {attempt+1}/{max_retries}...")
                # Call Claude API
                response = anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    temperature=0,
                    system="You are a Digital Signal Processing teaching assistant. Grade homework submissions accurately and fairly, focusing only on the technical content. Format your response as JSON.",
                    messages=[
                        {"role": "user", "content": message_content}
                    ]
                )
                
                # Extract JSON from Claude's response
                response_text = response.content[0].text
                # Find JSON in the response (in case Claude adds any text before/after)
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    grading_result = json.loads(json_str)
                    print(f"Successfully processed submission for student {student_identifier}")
                    # Success! Break out of retry loop
                    break
                else:
                    raise ValueError("No JSON found in the response")
                    
            except Exception as e:
                if "rate_limit_error" in str(e) and attempt < max_retries - 1:
                    # Rate limit hit, apply exponential backoff
                    delay = base_delay * (2 ** attempt) + random.uniform(1, 5)
                    print(f"Rate limit hit. Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    # Other error or final retry failed
                    print(f"API error for student {student_identifier}: {str(e)}")
                    grading_result = {
                        "problems": [],
                        "overall_score": 0,
                        "overall_max": 100,
                        "overall_feedback": f"API error: {str(e)}",
                        "error": True
                    }
                    break
                
    except Exception as e:
        print(f"Processing error for student {student_identifier}: {str(e)}")
        grading_result = {
            "problems": [],
            "overall_score": 0,
            "overall_max": 100,
            "overall_feedback": f"Processing error: {str(e)}",
            "error": True
        }
    
    # Save the grading result with a consistent filename
    # Use the submission filename as identifier, but ensure it doesn't have problematic characters
    safe_identifier = os.path.basename(student_identifier)
    result_path = os.path.join(output_dir, f"{safe_identifier}_grading.json")
    with open(result_path, 'w') as f:
        json.dump(grading_result, f, indent=2)
    
    return grading_result

def get_student_info(submission_filename):
    """Extract student name and submission date from the text file"""
    # The submission filename should be in this format:
    # "Homework 3_studentid_attempt_timestamp_originalname.pdf"
    
    # Split by underscore to get parts
    parts = submission_filename.split('_')
    if len(parts) < 4:
        return {"name": "Unknown", "date_submitted": "Unknown", "original_filename": "Unknown"}
    
    # Construct the base pattern for finding the corresponding text file
    base_pattern = f"{parts[0]}_{parts[1]}_{parts[2]}_{parts[3]}"
    
    # Search for the matching text file
    txt_files = []
    for root, dirs, files in os.walk(student_dir):
        for file in files:
            if file.startswith(base_pattern) and file.endswith('.txt'):
                txt_files.append(os.path.join(root, file))
    
    if not txt_files:
        print(f"No text file found for submission {submission_filename}")
        return {"name": "Unknown", "date_submitted": "Unknown", "original_filename": "Unknown"}
    
    # Use the first matching text file
    txt_file = txt_files[0]
    
    # Read the text file
    try:
        with open(txt_file, 'r') as f:
            lines = f.readlines()
        
        # Extract student name and submission date
        student_name = "Unknown"
        student_id = "Unknown"
        date_submitted = "Unknown"
        original_filename = "Unknown"
        
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
                in_files_section = False  # Stop after getting the first filename
        
        return {"name": student_name, "student_id": student_id, "date_submitted": date_submitted, "original_filename": original_filename}
    
    except Exception as e:
        print(f"Error reading text file for submission {submission_filename}: {str(e)}")
        return {"name": "Unknown", "student_id": "Unknown", "date_submitted": "Unknown", "original_filename": "Unknown"}

def create_blackboard_csv(grading_results):
    """Create a CSV file for Blackboard import"""
    # Create dataframe for Blackboard import
    data = []
    for submission_filename, result in grading_results.items():
        # Skip errored results or add placeholder for them
        if result.get("error", False):
            print(f"Skipping submission {submission_filename} in CSV due to processing errors")
            continue
            
        # Calculate percentage
        if result.get("overall_max", 0) > 0:
            percentage = (result.get("overall_score", 0) / result.get("overall_max", 100)) * 100
        else:
            percentage = 0
            
        # Format overall feedback by combining feedback from each problem
        feedback = result.get("overall_feedback", "") + "\n\n"
        
        # Only include feedback for problems that didn't get full marks
        for problem in result.get("problems", []):
            if problem.get("score", 20) < 20 and "feedback" in problem:
                feedback += f"Q{problem['problem_number']}: {problem.get('feedback', '')}\n"
        
        # Get student name and submission date
        student_info = get_student_info(submission_filename)
        
        data.append({
            "Student Name": student_info["name"],
            "Student ID": student_info["student_id"],
            "Submission Date": student_info["date_submitted"],
            "Submitted File": student_info["original_filename"],
            "Grade": f"{percentage:.2f}",
            "Feedback": feedback.strip()
        })
    
    if not data:
        print("No valid grading results to include in CSV")
        return None
        
    # Create DataFrame and save to CSV
    df = pd.DataFrame(data)
    csv_path = os.path.join(output_dir, "blackboard_grades.csv")
    df.to_csv(csv_path, index=False)
    print(f"Created CSV file for Blackboard import at {csv_path}")
    return csv_path

def main():
    """Main function to process all submissions"""
    # Dictionary to store all grading results
    all_results = {}
    
    # Get a list of student submission text files first
    txt_files = []
    for root, dirs, files in os.walk(student_dir):
        for file in files:
            if file.endswith('.txt') and file.startswith('Homework 3_'):
                txt_files.append(os.path.join(root, file))
    
    if not txt_files:
        print("No student submission metadata files found. Check the directory path.")
        return
        
    print(f"Found {len(txt_files)} student submissions")
    
    # Prepare reference images once to avoid repetitive processing
    reference_images = prepare_reference_images()
    
    # Process submissions
    test_limit = 2  # Change to None to process all submissions
    processed_count = 0
    
    for txt_file in txt_files:
        try:
            # Extract student information from the text file
            with open(txt_file, 'r') as f:
                lines = f.readlines()
            
            # Extract student ID and submission filename
            student_name = "Unknown"
            student_id = os.path.basename(txt_file).split('_attempt_')[0]  # Extract ID from filename
            submission_filename = None
            
            in_files_section = False
            full_submission_path = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("Name:"):
                    # Format: "Name: John Doe (jdoe)"
                    name_parts = line.strip().split("(")
                    if len(name_parts) > 1:
                        student_name = name_parts[0].replace("Name:", "").strip()
                elif line == "Files:":
                    in_files_section = True
                elif in_files_section and line.startswith("Filename:"):
                    submission_filename = line.replace("Filename:", "").strip()
                    full_submission_path = os.path.join(os.path.dirname(txt_file), submission_filename)
                    break  # Stop after getting the first filename
            
            if not submission_filename or not os.path.exists(full_submission_path):
                print(f"No valid submission file found for student {student_id}")
                continue
                
            print(f"Processing submission {processed_count+1}/{min(test_limit or len(txt_files), len(txt_files))}: {student_id} - {student_name}")
            
            # Check if we already processed this student
            result_path = os.path.join(output_dir, f"{submission_filename}_grading.json")
            if os.path.exists(result_path):
                print(f"Student {student_id} already processed, loading from file")
                with open(result_path, 'r') as f:
                    all_results[submission_filename] = json.load(f)
                processed_count += 1
                continue
            
            # Add delay between submissions to avoid rate limits
            if processed_count > 0:
                delay = random.uniform(15, 30)  # Random delay between 15-30 seconds
                print(f"Waiting {delay:.2f} seconds before processing next submission...")
                time.sleep(delay)
            
            # Process the submission
            result = process_submission(full_submission_path, submission_filename, reference_images)
            all_results[submission_filename] = result
            
            processed_count += 1
            if test_limit is not None and processed_count >= test_limit:
                print(f"Processed {processed_count} submissions for testing. Set test_limit to None to process all.")
                break
                
        except Exception as e:
            print(f"Error processing text file {txt_file}: {str(e)}")
            continue
    
    # Create CSV for Blackboard
    if all_results:
        csv_path = create_blackboard_csv(all_results)
        if csv_path:
            print(f"Grading complete! Results saved to {csv_path}")
        else:
            print("No CSV file was generated due to processing errors.")
    else:
        print("No results were generated. Please check the inputs and try again.")

if __name__ == "__main__":
    main() 