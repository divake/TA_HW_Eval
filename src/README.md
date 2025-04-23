# ECE 317 Lab Grading System

This system automates the grading of student lab submissions using AI models. The system is designed to be easily configurable for different labs by updating the settings in `config.py`.

## Configuration Guide

All configuration options are centralized in `config.py` to make it easy to adapt the system for different labs without modifying any other code.

### Adding a New Lab

To add support for a new lab:

1. Update the `LAB_STRUCTURE` dictionary in `config.py`:

```python
LAB_STRUCTURE = {
    # Existing lab_05 structure...
    
    "lab_06": {
        "name": "Your Lab Name",
        "total_questions": 4,  # Number of questions/sections
        "question_names": [
            "Section Name 1",
            "Section Name 2",
            "Section Name 3",
            "Section Name 4"
        ],
        "marks_per_question": 25,  # Points per question
        "total_marks": 100,       # Total points for the lab
        "pdf_path": os.path.join(BASE_DIR, "path/to/Lab_06_Questions.pdf")
    }
}
```

2. Update the `GRADING` dictionary with the same information:

```python
GRADING = {
    # Existing lab_05 entry...
    
    "lab_06": {
        "name": "Your Lab Name",
        "total_marks": 100,
        "questions": {
            1: {"marks": 25, "name": "Section Name 1"},
            2: {"marks": 25, "name": "Section Name 2"},
            3: {"marks": 25, "name": "Section Name 3"},
            4: {"marks": 25, "name": "Section Name 4"}
        }
    }
}
```

3. Update the `STUDENT_DIR` path to point to the folder containing student submissions for the new lab:

```python
STUDENT_DIR = os.path.join(BASE_DIR, "src/lab_06")  # Update this path
```

### File Paths Configuration

Configure the following paths in `config.py`:

- `BASE_DIR`: Root directory for the project
- `STUDENT_DIR`: Directory containing student submissions
- `OUTPUT_DIR`: Directory for grading results
- `LAB_INSTRUCTION_PATH`: Directory containing lab instructions
- `SOLUTION_PATH`: Directory containing model solutions

### AI Models Configuration

Configure AI model settings in the `MODELS` and `SYSTEM_PROMPTS` dictionaries:

```python
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

SYSTEM_PROMPTS = {
    "anthropic": """Your custom system prompt for Anthropic models...""",
    "openai": """Your custom system prompt for OpenAI models..."""
}
```

### Other Settings

The configuration file includes other customizable settings:

- `FILE_TYPES`: Extensions and media types for supported files
- `IMAGE_SETTINGS`: Settings for image processing
- `API_SETTINGS`: API request parameters
- `LOGGING`: Logging configuration
- `FILE_PATTERNS`: Regular expression patterns for file matching

## Running the Grader

To run the grader for a lab, use the command:

```bash
python src/main.py lab_06
```

### Additional Options

- Limit processing to specific students: `--students student1_id student2_id`
- Limit the number of submissions: `--max 2`
- Process submissions in parallel: `--parallel`
- Include solution in grading: `--solution`
- Use a specific model: `--model anthropic`
- Dump prompt template to a file: `--dump-prompt`

Example:
```bash
python src/main.py lab_06 --max 2 --model anthropic
```

This will test your configuration with just 2 student submissions. 