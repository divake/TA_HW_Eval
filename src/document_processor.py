"""
Functions for processing PDF documents and other file formats.
Handles conversion to images for AI models that require it.
"""

import os
import base64
from io import BytesIO
from typing import List, Dict, Any, Optional, Tuple, Union
import time
import random

from PIL import Image
try:
    from pdf2image import convert_from_path
except ImportError:
    print("Warning: pdf2image not installed. PDF to image conversion will not work.")
    print("Install with: pip install pdf2image")
    print("You may also need to install poppler: https://github.com/oschwartz10612/poppler-windows/")

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

def pdf_to_images(pdf_path: str, dpi: int = None, max_pages: int = None) -> List[Image.Image]:
    """
    Convert PDF to a list of PIL Image objects.
    
    Args:
        pdf_path: Path to the PDF file
        dpi: DPI for converting PDF to images (higher = better quality but larger)
        max_pages: Maximum number of pages to convert
        
    Returns:
        List of PIL Image objects
    """
    if dpi is None:
        dpi = config.IMAGE_SETTINGS['dpi']
        
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

def pdf_to_base64(pdf_path: str) -> str:
    """
    Convert PDF file directly to base64 string.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Base64-encoded PDF string
    """
    try:
        with open(pdf_path, 'rb') as pdf_file:
            encoded_string = base64.b64encode(pdf_file.read()).decode('utf-8')
        return encoded_string
    except Exception as e:
        print(f"Error converting PDF to base64: {str(e)}")
        return ""

def process_submission_file(file_path: str, model_type: str) -> Dict[str, Any]:
    """
    Process a submission file based on its type and the target model.
    
    Args:
        file_path: Path to the submission file
        model_type: Type of model that will process the file
        
    Returns:
        Dictionary with processed file data:
        - type: 'pdf_base64', 'image_list', or 'error'
        - content: base64 string for PDFs or list of PIL Images for images
        - error: Error message if processing failed
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    try:
        # For PDF files
        if file_ext == '.pdf':
            # If model supports direct PDF input, use that
            if is_direct_pdf_supported(model_type):
                pdf_data = pdf_to_base64(file_path)
                return {
                    "type": "pdf_base64",
                    "content": pdf_data
                }
            else:
                # Otherwise convert to images
                images = pdf_to_images(file_path)
                images = [compress_image(img) for img in images]
                return {
                    "type": "image_list",
                    "content": images
                }
                
        # For image files
        elif file_ext in ['.jpg', '.jpeg', '.png']:
            try:
                img = Image.open(file_path)
                img = compress_image(img)
                return {
                    "type": "image_list",
                    "content": [img]
                }
            except Exception as e:
                return {
                    "type": "error",
                    "error": f"Error processing image file: {str(e)}"
                }
                
        # For DOC/DOCX files (future implementation)
        elif file_ext in ['.doc', '.docx']:
            # For now, return an error as DOC/DOCX conversion is not implemented
            return {
                "type": "error",
                "error": "DOC/DOCX conversion not yet implemented"
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
    all_images = []
    has_errors = False
    error_messages = []
    
    for file_info in student_files:
        file_path = file_info["path"]
        processed = process_submission_file(file_path, model_type)
        
        if processed["type"] == "error":
            has_errors = True
            error_messages.append(f"Error processing {os.path.basename(file_path)}: {processed['error']}")
            continue
            
        all_processed_files.append(processed)
        
        # Collect all images from all files for image-based models
        if processed["type"] == "image_list":
            all_images.extend(processed["content"])
    
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
    
    # For image-based models, combine all images
    if not is_direct_pdf_supported(model_type):
        return {
            "type": "image_list",
            "content": all_images
        }
    
    # For direct PDF models, return all processed files
    return {
        "type": "mixed",
        "content": all_processed_files
    } 