"""
Functions for processing PDF documents and other file formats.
Handles direct PDF submission for AI models.
"""

import os
import base64
from io import BytesIO
from typing import List, Dict, Any, Optional, Tuple, Union
import time
import random

from PIL import Image
try:
    import docx
except ImportError:
    print("Warning: python-docx is not installed. DOCX text extraction will be unavailable.")
    docx = None

import config

def is_direct_pdf_supported(model_type: str) -> bool:
    """
    Check if the specified model type supports direct PDF input.
    
    Args:
        model_type: Type of AI model (e.g., 'anthropic', 'openai')
        
    Returns:
        True if direct PDF input is supported, False otherwise
    """
    # Currently only Anthropic models support direct PDF input
    return model_type.lower() == 'anthropic'

def compress_image(image: Image.Image, quality: int = None, max_size: Tuple[int, int] = None) -> Image.Image:
    """
    Compress and resize an image to reduce file size.
    
    Args:
        image: PIL Image object
        quality: JPEG quality (1-100)
        max_size: Maximum width and height
        
    Returns:
        Compressed PIL Image object
    """
    if quality is None:
        quality = config.IMAGE_SETTINGS['quality']
    
    if max_size is None:
        max_size = config.IMAGE_SETTINGS['max_size']
        
    # Create a copy to avoid modifying the original
    image_copy = image.copy()
    
    # Resize if needed
    if image_copy.width > max_size[0] or image_copy.height > max_size[1]:
        image_copy.thumbnail(max_size, Image.LANCZOS)
    
    return image_copy

def image_to_base64(image: Image.Image, format: str = None, quality: int = None) -> str:
    """
    Convert PIL Image to base64 string with compression.
    
    Args:
        image: PIL Image object
        format: Output format (e.g., 'JPEG', 'PNG')
        quality: Image quality (1-100)
        
    Returns:
        Base64-encoded image string
    """
    if format is None:
        format = config.IMAGE_SETTINGS['format']
        
    if quality is None:
        quality = config.IMAGE_SETTINGS['quality']
        
    buffered = BytesIO()
    image.save(buffered, format=format, quality=quality, optimize=True)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def file_to_base64(file_path: str) -> str:
    """
    Convert any file directly to base64 string.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Base64-encoded string
    """
    try:
        with open(file_path, 'rb') as file:
            encoded_string = base64.b64encode(file.read()).decode('utf-8')
        return encoded_string
    except Exception as e:
        print(f"Error converting file to base64: {str(e)}")
        return ""

def get_file_media_type(file_ext: str) -> str:
    """
    Get the media type for a file extension.
    
    Args:
        file_ext: File extension (e.g., '.pdf', '.jpg')
        
    Returns:
        Media type string
    """
    # Use media types from config
    return config.FILE_TYPES["media_types"].get(file_ext.lower(), 'application/octet-stream')

def extract_text_from_docx(file_path: str) -> str:
    """
    Extract text from a DOCX file.
    
    Args:
        file_path: Path to the DOCX file
        
    Returns:
        Extracted text as a string
    """
    if docx is None:
        return "Cannot extract text from DOCX: python-docx not installed"
        
    try:
        doc = docx.Document(file_path)
        full_text = []
        
        # Extract text from paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        
        # Extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    if cell.text.strip():
                        row_text.append(cell.text)
                if row_text:
                    full_text.append(" | ".join(row_text))
        
        return "\n\n".join(full_text)
    except Exception as e:
        return f"Error extracting text from DOCX: {str(e)}"

def process_submission_file(file_path: str, model_type: str) -> Dict[str, Any]:
    """
    Process a submission file based on its type and the target model.
    
    Args:
        file_path: Path to the submission file
        model_type: Type of model that will process the file
        
    Returns:
        Dictionary with processed file data:
        - type: 'file_base64', 'image_base64', or 'error'
        - content: base64 string content
        - media_type: MIME type of the file
        - error: Error message if processing failed
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    try:
        # For images, compress and convert to base64
        if file_ext in config.FILE_TYPES["image_extensions"]:
            try:
                img = Image.open(file_path)
                img = compress_image(img)
                image_data = image_to_base64(img)
                return {
                    "type": "image_base64",
                    "content": image_data,
                    "media_type": get_file_media_type(file_ext)
                }
            except Exception as e:
                return {
                    "type": "error",
                    "error": f"Error processing image file: {str(e)}"
                }
                
        # For PDF documents
        elif file_ext == '.pdf':
            file_data = file_to_base64(file_path)
            return {
                "type": "file_base64",
                "content": file_data,
                "media_type": "application/pdf"
            }
            
        # For non-PDF documents
        elif file_ext in config.FILE_TYPES["document_extensions"]:
            # If using Anthropic, which only accepts PDF documents
            if model_type.lower() == 'anthropic':
                # For documents that Anthropic can't process directly,
                # we'll convert them to text and send as text content
                try:
                    # Extract text from DOCX files
                    if file_ext == '.docx':
                        content = extract_text_from_docx(file_path)
                        return {
                            "type": "text",
                            "content": f"[Content from {os.path.basename(file_path)}]:\n\n{content}"
                        }
                    # Simple text extraction for plain text files
                    elif file_ext in ['.txt', '.md', '.csv']:
                        with open(file_path, 'r', errors='ignore') as f:
                            content = f.read()
                        return {
                            "type": "text",
                            "content": f"[Content from {os.path.basename(file_path)}]:\n\n{content}"
                        }
                    # For other document types we'll handle as base64 image
                    # Anthropic will process it as an image rather than a document
                    else:
                        file_data = file_to_base64(file_path)
                        return {
                            "type": "image_base64",
                            "content": file_data,
                            "media_type": "application/octet-stream",
                            "filename": os.path.basename(file_path)
                        }
                except Exception as e:
                    return {
                        "type": "error",
                        "error": f"Error processing non-PDF document for Anthropic: {str(e)}"
                    }
            # For other models that can handle different document types
            else:
                file_data = file_to_base64(file_path)
                media_type = get_file_media_type(file_ext)
                return {
                    "type": "file_base64",
                    "content": file_data,
                    "media_type": media_type
                }
        else:
            return {
                "type": "error",
                "error": f"Unsupported file type: {file_ext}"
            }
            
    except Exception as e:
        return {
            "type": "error",
            "error": f"Error processing file: {str(e)}"
        }

def prepare_submission_for_model(student_files: List[Dict[str, str]], model_type: str) -> Dict[str, Any]:
    """
    Prepare all of a student's submitted files for a specific model type.
    
    Args:
        student_files: List of dictionaries with file paths
        model_type: Target model type
        
    Returns:
        Dictionary with processed files
    """
    all_processed_files = []
    pdf_files = []
    non_pdf_files = []
    has_errors = False
    error_messages = []
    
    # First sort files by type to prioritize PDFs
    for file_info in student_files:
        file_path = file_info["path"]
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext == '.pdf':
            pdf_files.append(file_info)
        else:
            non_pdf_files.append(file_info)
    
    # Process PDF files first (since they're most likely to work with Anthropic)
    for file_info in pdf_files:
        file_path = file_info["path"]
        file_name = file_info.get("filename", os.path.basename(file_path))
        
        # Process the file
        processed = process_submission_file(file_path, model_type)
        
        # Add filename to processed file for better organization
        processed["filename"] = file_name
        
        # Keep track of errors
        if processed.get("type") == "error":
            has_errors = True
            error_messages.append(processed.get("error", "Unknown error"))
        
        all_processed_files.append(processed)
    
    # Then process non-PDF files
    for file_info in non_pdf_files:
        file_path = file_info["path"]
        file_name = file_info.get("filename", os.path.basename(file_path))
        
        # Process the file
        processed = process_submission_file(file_path, model_type)
        
        # Add filename to processed file for better organization
        processed["filename"] = file_name
        
        # Keep track of errors
        if processed.get("type") == "error":
            has_errors = True
            error_messages.append(processed.get("error", "Unknown error"))
        
        all_processed_files.append(processed)
    
    # If we have no files, return an error
    if not all_processed_files:
        return {
            "type": "error",
            "error": "No files could be processed"
        }
    
    # If all files had errors, return an error
    if has_errors and len(error_messages) == len(student_files):
        return {
            "type": "error",
            "error": "; ".join(error_messages)
        }
    else:
        # At least some files were processed successfully
        return {
            "type": "success",
            "content": all_processed_files
        }

def get_allowed_file_extensions():
    """
    Get a list of all allowed file extensions.
    
    Returns:
        List of allowed file extensions (e.g., ['.pdf', '.jpg'])
    """
    # Combine document and image extensions from config
    return config.FILE_TYPES["document_extensions"] + config.FILE_TYPES["image_extensions"]

def analyze_lab_questions_with_ai(pdf_path: str, model_type: str = "anthropic") -> Dict[str, Any]:
    """
    Analyze a lab question PDF using AI to automatically determine structure and grading criteria.
    
    Args:
        pdf_path: Path to the PDF file containing lab questions
        model_type: Type of AI model to use for analysis
        
    Returns:
        Dictionary with lab structure information:
        - name: Lab name/title
        - total_questions: Number of questions/sections
        - question_names: List of question/section names
        - marks_per_question: Points per question (if evenly distributed)
        - total_marks: Total available marks
    """
    # Check if the specified model supports direct PDF input
    if not is_direct_pdf_supported(model_type):
        return {"error": True, "error_message": f"Model {model_type} doesn't support direct PDF analysis"}
    
    # Import model class based on model_type
    if model_type.lower() == "anthropic":
        from model_interface import AnthropicModel
        model = AnthropicModel()
    else:
        return {"error": True, "error_message": f"Unsupported model type: {model_type}"}
    
    # Convert PDF to base64 for AI processing
    pdf_content = file_to_base64(pdf_path)
    
    # Create the analysis prompt
    system_prompt = """You are a teaching assistant analyzing lab instruction documents. 
Your task is to extract the structure of the lab questions, including titles, point values, and number of questions.
Return your analysis as structured JSON only, with no additional explanation or text."""
    
    message_content = [
        {"type": "text", "text": "Please analyze this lab instruction document and extract the following information:\n\n"
                                 "1. The lab title/name\n"
                                 "2. The total number of questions or sections to be completed\n"
                                 "3. The name of each question or section\n"
                                 "4. The points allocated to each question (if specified)\n"
                                 "5. The total points for the lab\n\n"
                                 "Return the analysis as a JSON object with this structure:\n"
                                 "{\n"
                                 "  \"name\": \"Lab Title\",\n"
                                 "  \"total_questions\": 4,\n"
                                 "  \"question_names\": [\"Question 1 Title\", \"Question 2 Title\", ...],\n"
                                 "  \"question_points\": [25, 25, ...],\n"
                                 "  \"total_marks\": 100\n"
                                 "}\n\n"
                                 "If points are not explicitly specified, distribute 100 points equally among the questions."
        },
        {"type": "document", 
         "source": {
             "type": "base64",
             "media_type": "application/pdf",
             "data": pdf_content
         }}
    ]
    
    # Send to AI for analysis
    try:
        result = model.send_message(message_content, system_prompt)
        
        # Ensure we have the required fields
        if "name" in result and "total_questions" in result and "question_names" in result:
            # Calculate marks_per_question if not provided
            if "question_points" in result:
                # Use provided point values
                points = result["question_points"]
                result["total_marks"] = sum(points)
            else:
                # Equal distribution of points
                if "total_marks" not in result:
                    result["total_marks"] = 100
                result["marks_per_question"] = result["total_marks"] // result["total_questions"]
                result["question_points"] = [result["marks_per_question"]] * result["total_questions"]
            
            # Add file path for reference
            result["pdf_path"] = pdf_path
            return result
        else:
            return {
                "error": True, 
                "error_message": "AI analysis did not return expected structure",
                "ai_response": result
            }
            
    except Exception as e:
        return {"error": True, "error_message": f"Error during AI analysis: {str(e)}"} 