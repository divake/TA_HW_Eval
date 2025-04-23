"""
Configuration settings for the lab grading system.
Contains API keys, file paths, model settings, and grading parameters.
"""

import os

# API Keys (replace with actual keys when deploying)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "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")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# File paths
BASE_DIR = "/ssd_4TB/divake/BB_ECE317"
STUDENT_DIR = os.path.join(BASE_DIR, "src/lab_05")  # Submissions
OUTPUT_DIR = os.path.join(BASE_DIR, "src/grading")
LAB_INSTRUCTION_PATH = os.path.join(BASE_DIR, "lab_instructions")
SOLUTION_PATH = os.path.join(BASE_DIR, "lab_solutions")

# Model settings
MODELS = {
    "anthropic": {
        "name": "claude-3-7-sonnet-20250219",
        "max_tokens": 4000,
        "temperature": 0.0
    },
    "openai": {
        "name": "gpt-4-turbo",
        "max_tokens": 4000,
        "temperature": 0.0
    }
}

# System prompts for different models
SYSTEM_PROMPTS = {
    "anthropic": """You are an expert teaching assistant for Digital Signal Processing (ECE 317).
Your task is to grade student lab reports accurately, fairly, and consistently.
Focus on technical content, correctness of signal processing concepts, quality of analysis, and interpretation of results.
Provide specific, constructive feedback highlighting both strengths and areas for improvement.
Format your response as JSON according to the specified structure.""",
    
    "openai": """You are an expert teaching assistant for Digital Signal Processing (ECE 317).
Grade student lab reports accurately, fairly, and consistently.
Focus on technical content, correctness of signal processing concepts, quality of analysis, and interpretation of results.
Provide specific, constructive feedback highlighting both strengths and areas for improvement.
Format your response as JSON according to the specified structure."""
}

# Grading parameters
GRADING = {
    "lab_05": {
        "name": "Audio Signals",
        "total_marks": 100,
        "questions": {
            1: {"marks": 25, "name": "Signal Analysis"},
            2: {"marks": 25, "name": "Filtering Implementation"},
            3: {"marks": 25, "name": "Frequency Response"},
            4: {"marks": 25, "name": "Audio Quality Assessment"}
        }
    }
}

# Lab structure definitions
LAB_STRUCTURE = {
    "lab_05": {
        "name": "Audio Signals",
        "total_questions": 4,
        "question_names": [
            "Signal Analysis",
            "Filtering Implementation",
            "Frequency Response",
            "Audio Quality Assessment"
        ],
        "marks_per_question": 25,
        "total_marks": 100,
        "pdf_path": os.path.join(BASE_DIR, "src/Lab_05_Questions.pdf")
    },
    # Template for adding new labs
    "generic": {
        "name": "Generic Lab",
        "total_questions": 4,
        "question_names": ["Question 1", "Question 2", "Question 3", "Question 4"],
        "marks_per_question": 25,
        "total_marks": 100
    }
}

# File type settings
FILE_TYPES = {
    # Extensions for documents
    "document_extensions": ['.pdf', '.doc', '.docx'],
    # Extensions for images
    "image_extensions": ['.jpg', '.jpeg', '.png'],
    # Media types for various file extensions
    "media_types": {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
}

# Image processing settings
IMAGE_SETTINGS = {
    "dpi": 100,
    "quality": 40,
    "max_size": (800, 800),
    "format": "JPEG"
}

# API request settings
API_SETTINGS = {
    "max_retries": 5,
    "base_delay": 10,  # seconds
    "timeout": 300,  # seconds
    "rate_limit_delay": (10, 20)  # min and max seconds for random delay
}

# Logging settings
LOGGING = {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "log_file": os.path.join(OUTPUT_DIR, "grading.log")
}

# File matching patterns
FILE_PATTERNS = {
    "metadata_pattern": "Lab {lab_num}_ {lab_title}_.+_attempt_.+\.txt$"
}

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True) 