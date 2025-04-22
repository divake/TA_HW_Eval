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
    media_types = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    
    return media_types.get(file_ext.lower(), 'application/octet-stream')

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
        # For PDF files or other document types
        if file_ext in ['.pdf', '.doc', '.docx']:
            # Check if direct PDF/document input is supported
            if is_direct_pdf_supported(model_type):
                file_data = file_to_base64(file_path)
                media_type = get_file_media_type(file_ext)
                return {
                    "type": "file_base64",
                    "content": file_data,
                    "media_type": media_type
                }
            else:
                # For models that don't support direct PDF input
                # This is just a placeholder for now, as we're focusing on direct PDF support
                return {
                    "type": "error",
                    "error": f"Model {model_type} doesn't support direct {file_ext} input"
                }
                
        # For image files
        elif file_ext in ['.jpg', '.jpeg', '.png']:
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
    has_errors = False
    error_messages = []
    
    for file_info in student_files:
        file_path = file_info["path"]
        processed = process_submission_file(file_path, model_type)
        
        if processed["type"] == "error":
            has_errors = True
            error_messages.append(f"Error processing {os.path.basename(file_path)}: {processed['error']}")
            continue
            
        all_processed_files.append({
            "type": processed["type"],
            "content": processed["content"],
            "media_type": processed["media_type"],
            "filename": os.path.basename(file_path)
        })
    
    # If we have errors but managed to process some files, only log the errors
    if has_errors and all_processed_files:
        for error in error_messages:
            print(error)
    
    # If we have no processed files at all, return the error
    if not all_processed_files:
        return {
            "type": "error",
            "error": "\n".join(error_messages)
        }
    
    # Return all processed files
    return {
        "type": "files",
        "content": all_processed_files
    } 