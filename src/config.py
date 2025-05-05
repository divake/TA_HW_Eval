"""
Configuration settings for the lab grading system.
Contains API keys, file paths, model settings, and grading parameters.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# This enhances security by keeping API keys out of the codebase
# Create a .env file based on .env.example and add your actual API keys there
env_path = Path(os.path.dirname(os.path.dirname(__file__))) / '.env'
load_dotenv(dotenv_path=env_path)

# API Keys from environment variables
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
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
IMPORTANT: When deducting points, use smaller increments of 2 points rather than 5 points to provide more granular grading.

IMPORTANT: You MUST format your response as pure JSON with this structure:
{
    "problems": [
        {
            "problem_number": 1,
            "score": X,
            "max_score": Y,
            "feedback": "Concise technical feedback only if not full marks"
        },
        // Repeat for all questions
    ],
    "overall_score": Z,
    "overall_max": 100,
    "overall_feedback": "Brief technical summary"
}

DO NOT include any markdown formatting, explanations, or text outside the JSON structure.
DO NOT use ```json``` or ``` markers.
Return ONLY the JSON object.
Your entire response must be valid parseable JSON.""",
    
    "openai": """You are an expert teaching assistant for Digital Signal Processing (ECE 317).
Grade student lab reports accurately, fairly, and consistently.
Focus on technical content, correctness of signal processing concepts, quality of analysis, and interpretation of results.
IMPORTANT: When deducting points, use smaller increments of 2 points rather than 5 points to provide more granular grading.
Provide specific, constructive feedback highlighting both strengths and areas for improvement.
Format your response as JSON according to the specified structure."""
}

# Grading parameters - removed hardcoded structure and will use lab_analysis files instead
GRADING = {
    "lab_05": {
        "name": "Audio Signals",
        "total_marks": 100
    }
}

# Lab structure definitions - this will be populated dynamically from lab_analysis files
# This is just a fallback structure in case the analysis file is not available
LAB_STRUCTURE = {
    "lab_05": {
        "name": "Audio Signals",
        "total_marks": 100,
        "pdf_path": os.path.join(BASE_DIR, "src/Lab_05_Questions.pdf")
    },
    # Template for adding new labs
    "generic": {
        "name": "Generic Lab",
        "total_marks": 100
    }
}

# File type settings
FILE_TYPES = {
    # Extensions for documents
    "document_extensions": ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'],
    # Extensions for images
    "image_extensions": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'],
    # Media types for various file extensions
    "media_types": {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
        '.webp': 'image/webp',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.txt': 'text/plain',
        '.rtf': 'application/rtf',
        '.odt': 'application/vnd.oasis.opendocument.text'
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
    "rate_limit_delay": (10, 20),  # min and max seconds for random delay
    "anthropic_rate_limit": {
        "tokens_per_minute": 20000,  # Anthropic's rate limit (20k tokens/minute)
        "max_backoff": 120,  # Maximum backoff time in seconds
        "exponential_backoff": True,  # Whether to use exponential backoff
        "jitter": True,  # Add random jitter to backoff times
        "token_buffer": 0.9  # Use only 90% of the rate limit to be safe
    }
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