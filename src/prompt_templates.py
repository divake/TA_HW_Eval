"""
Templates for prompts to be sent to AI models for grading.
"""

from typing import Dict, Any, List, Optional
import config

# Get system prompts from config
SYSTEM_PROMPTS = config.SYSTEM_PROMPTS

def get_lab_grading_prompt(lab_id: str, with_solution: bool = True, lab_structure: Optional[Dict[str, Any]] = None) -> str:
    """
    Get the appropriate grading prompt for a specific lab.
    
    Args:
        lab_id: Lab identifier (e.g., 'lab_05')
        with_solution: Whether a solution is provided
        lab_structure: Dictionary with lab structure information
        
    Returns:
        Grading prompt text
    """
    # Always use the dynamic prompt generation if lab_structure is provided
    if lab_structure:
        return generate_dynamic_lab_prompt(lab_structure, with_solution)
    
    # Fall back to a generic prompt if no lab-specific prompt is available
    return get_generic_lab_prompt(with_solution)

def get_generic_lab_prompt(with_solution: bool = True, lab_structure: Optional[Dict[str, Any]] = None) -> str:
    """
    Get a generic lab grading prompt that can be used for any lab.
    
    Args:
        with_solution: Whether a solution is provided
        lab_structure: Dictionary with lab structure information
        
    Returns:
        Grading prompt text
    """
    # Use default structure if none provided
    if lab_structure is None:
        lab_structure = config.LAB_STRUCTURE["generic"]
    
    # Generate a dynamic prompt using the generic structure
    return generate_dynamic_lab_prompt(lab_structure, with_solution)

def generate_dynamic_lab_prompt(lab_structure: Dict[str, Any], with_solution: bool = True) -> str:
    """
    Generate a dynamic lab grading prompt based on lab structure.
    
    Args:
        lab_structure: Dictionary with lab structure
        with_solution: Whether a solution is provided
        
    Returns:
        Dynamically generated grading prompt text
    """
    lab_name = lab_structure.get("name", "Lab Exercise")
    total_questions = lab_structure.get("total_questions", 0)
    question_names = lab_structure.get("question_names", [])
    total_marks = lab_structure.get("total_marks", 100)
    
    # If question_names is not provided or empty, generate generic question names
    if not question_names and total_questions > 0:
        question_names = [f"Question {i+1}" for i in range(total_questions)]
    # If question_names is provided but total_questions is not, infer it
    elif question_names and not total_questions:
        total_questions = len(question_names)
    # If neither is provided, default to 1 question
    elif not question_names and not total_questions:
        total_questions = 1
        question_names = ["Question 1"]
    
    # Get question points (marks per question)
    if "question_points" in lab_structure and lab_structure["question_points"]:
        question_points = lab_structure["question_points"]
        # If the length doesn't match, adjust it
        if len(question_points) != total_questions:
            # Distribute points evenly if the lengths don't match
            question_points = [total_marks // total_questions] * total_questions
    else:
        # Distribute points evenly if question_points is not provided
        question_points = [total_marks // total_questions] * total_questions
    
    # Format the list of questions with their point values for the prompt
    questions_list = ""
    for i, (name, points) in enumerate(zip(question_names, question_points)):
        questions_list += f"{i+1}. {name} ({points} marks)  \n"
    
    if with_solution:
        return f"""
        You are an expert teaching assistant grading a Digital Signal Processing (ECE 317) lab report on {lab_name}.
        
        I have provided:
        1. The lab instructions PDF
        2. The instructor's solution or grading rubric (if available)
        3. The student's submission
        
        This lab has {total_questions} questions with the following point allocations (for a total of {total_marks} marks):
        {questions_list}
        
        GRADING GUIDELINES - READ CAREFULLY:
        - Be lenient in grading. If a student has attempted the question and got close to the correct answer, give full marks.
        - Only deduct 1-2 marks if the solution is seriously flawed but shows effort.
        - Give 0 marks ONLY when a question is completely unattempted.
        - Provide extremely concise feedback - just a few words identifying what's missing or wrong.
        - Do NOT provide any feedback for questions that receive full marks.
        - Do NOT use phrases like "the student has done a good job" or other generic feedback.
        - Do NOT provide overall feedback on the lab submission.
        
        Format your response as JSON with the following structure:
        {{
            "problems": [
                {{
                    "problem_number": 1,
                    "name": "{question_names[0] if question_names else 'Question 1'}",
                    "score": <score>,
                    "max_score": {question_points[0] if question_points else (total_marks // total_questions)},
                    "feedback": "<only for questions with deducted points; leave empty string for full marks>"
                }},
                // Repeat for all questions
            ],
            "overall_score": <total score>,
            "overall_max": {total_marks}
        }}
        
        Return only the JSON with no additional text. Ensure you grade all {total_questions} questions.
        """
    else:
        # Prompt without solution
        return f"""
        You are an expert teaching assistant grading a Digital Signal Processing (ECE 317) lab report on {lab_name}.
        
        I have provided:
        1. The lab instructions PDF
        2. The student's submission
        
        This lab has {total_questions} questions with the following point allocations (for a total of {total_marks} marks):
        {questions_list}
        
        GRADING GUIDELINES - READ CAREFULLY:
        - Be lenient in grading. If a student has attempted the question and got close to the correct answer, give full marks.
        - Only deduct 1-2 marks if the solution is seriously flawed but shows effort.
        - Give 0 marks ONLY when a question is completely unattempted.
        - Provide extremely concise feedback - just a few words identifying what's missing or wrong.
        - Do NOT provide any feedback for questions that receive full marks.
        - Do NOT use phrases like "the student has done a good job" or other generic feedback.
        - Do NOT provide overall feedback on the lab submission.
        
        Format your response as JSON with the following structure:
        {{
            "problems": [
                {{
                    "problem_number": 1,
                    "name": "{question_names[0] if question_names else 'Question 1'}",
                    "score": <score>,
                    "max_score": {question_points[0] if question_points else (total_marks // total_questions)},
                    "feedback": "<only for questions with deducted points; leave empty string for full marks>"
                }},
                // Repeat for all questions
            ],
            "overall_score": <total score>,
            "overall_max": {total_marks}
        }}
        
        Return only the JSON with no additional text. Ensure you grade all {total_questions} questions.
        """

def build_grading_message(
    lab_id: str,
    lab_instructions: List[Dict[str, Any]], 
    student_submission: List[Dict[str, Any]],
    solution: Optional[List[Dict[str, Any]]] = None,
    lab_structure: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Build the message to send to the model with all the content.
    
    Args:
        lab_id: Lab identifier
        lab_instructions: Lab instruction content
        student_submission: Student submission content
        solution: Optional solution content
        lab_structure: Optional lab structure information
        
    Returns:
        List of content dictionaries for the model
    """
    # Get the appropriate grading prompt using the provided lab structure
    prompt = get_lab_grading_prompt(lab_id, solution is not None, lab_structure)
    
    # Create the message content
    message_content = [
        {
            "type": "text",
            "text": prompt
        },
        {
            "type": "text",
            "text": "\n\nLAB INSTRUCTIONS:"
        }
    ]
    
    # Add lab instructions
    message_content.extend(lab_instructions)
    
    # Add solution if provided
    if solution:
        message_content.append({
            "type": "text",
            "text": "\n\nINSTRUCTOR SOLUTION:"
        })
        message_content.extend(solution)
    
    # Add student submission
    message_content.append({
        "type": "text",
        "text": "\n\nSTUDENT SUBMISSION:"
    })
    message_content.extend(student_submission)
    
    return message_content 