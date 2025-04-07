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

def process_submission(submission_path, student_id, reference_images=None):
    """Process a single student submission"""
    print(f"Processing submission for student {student_id}...")
    
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
                    print(f"Successfully processed submission for student {student_id}")
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
                    print(f"API error for student {student_id}: {str(e)}")
                    grading_result = {
                        "problems": [],
                        "overall_score": 0,
                        "overall_max": 100,
                        "overall_feedback": f"API error: {str(e)}",
                        "error": True
                    }
                    break
                
    except Exception as e:
        print(f"Processing error for student {student_id}: {str(e)}")
        grading_result = {
            "problems": [],
            "overall_score": 0,
            "overall_max": 100,
            "overall_feedback": f"Processing error: {str(e)}",
            "error": True
        }
    
    # Save the grading result
    result_path = os.path.join(output_dir, f"{student_id}_grading.json")
    with open(result_path, 'w') as f:
        json.dump(grading_result, f, indent=2)
    
    return grading_result

def create_blackboard_csv(grading_results):
    """Create a CSV file for Blackboard import"""
    # Create dataframe for Blackboard import
    data = []
    for student_id, result in grading_results.items():
        # Skip errored results or add placeholder for them
        if result.get("error", False):
            print(f"Skipping student {student_id} in CSV due to processing errors")
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
        
        data.append({
            "Student ID": student_id,
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
    
    # Get a list of student submissions
    student_files = []
    for root, dirs, files in os.walk(student_dir):
        for file in files:
            # Check for PDF files or other submission formats
            if file.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                student_files.append(os.path.join(root, file))
    
    if not student_files:
        print("No student submissions found. Check the directory path.")
        return
        
    print(f"Found {len(student_files)} student submissions")
    
    # Prepare reference images once to avoid repetitive processing
    reference_images = prepare_reference_images()
    
    # Process first few submissions as a test
    test_limit = 2  # Change to None to process all submissions
    processed_count = 0
    
    for submission_path in student_files:
        # Extract student ID from filename or path
        filename = os.path.basename(submission_path)
        student_id = os.path.splitext(filename)[0]  # Remove extension
        
        print(f"Processing submission {processed_count+1}/{min(test_limit or len(student_files), len(student_files))}: {student_id}")
        
        # Check if we already processed this student
        result_path = os.path.join(output_dir, f"{student_id}_grading.json")
        if os.path.exists(result_path):
            print(f"Student {student_id} already processed, loading from file")
            with open(result_path, 'r') as f:
                all_results[student_id] = json.load(f)
            processed_count += 1
            continue
        
        # Add delay between submissions to avoid rate limits
        if processed_count > 0:
            delay = random.uniform(15, 30)  # Random delay between 15-30 seconds
            print(f"Waiting {delay:.2f} seconds before processing next submission...")
            time.sleep(delay)
        
        # Process the submission
        result = process_submission(submission_path, student_id, reference_images)
        all_results[student_id] = result
        
        processed_count += 1
        if test_limit is not None and processed_count >= test_limit:
            print(f"Processed {processed_count} submissions for testing. Set test_limit to None to process all.")
            break
    
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