"""
Configuration settings for the lab grading system.
Contains API keys, file paths, model settings, and grading parameters.
"""

import os

# API Keys (replace with actual keys when deploying)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# File paths
BASE_DIR = "/ssd_4TB/divake/BB_ECE317"
STUDENT_DIR = os.path.join(BASE_DIR, "src/lab_05")  # Submissions
OUTPUT_DIR = os.path.join(BASE_DIR, "graded_results")
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
    "timeout": 300  # seconds
}

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True) 