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
    if lab_id == "lab_05":
        return get_lab05_prompt(with_solution, lab_structure)
    else:
        # Fall back to a generic prompt
        return get_generic_lab_prompt(with_solution, lab_structure)

def get_lab05_prompt(with_solution: bool = True, lab_structure: Optional[Dict[str, Any]] = None) -> str:
    """
    Get the prompt specifically for Lab 5 (Audio Signals).
    
    Args:
        with_solution: Whether a solution is provided
        lab_structure: Dictionary with lab structure information
        
    Returns:
        Grading prompt text
    """
    # Use default structure if none provided
    if lab_structure is None:
        lab_structure = config.LAB_STRUCTURE["lab_05"]
    
    # Format the list of questions for the prompt
    questions_list = ""
    for i, name in enumerate(lab_structure.get("question_names", [])):
        questions_list += f"{i+1}. {name}  \n"
    
    if with_solution:
        return f"""
        You are an expert teaching assistant grading a Digital Signal Processing (ECE 317) lab report on {lab_structure.get('name', 'Audio Signals')}.
        
        I have provided:
        1. The lab instructions PDF
        2. The instructor's solution or grading rubric (if available)
        3. The student's submission
        
        This lab has {lab_structure.get('total_questions', 4)} main sections, each worth {lab_structure.get('marks_per_question', 25)} marks (for a total of {lab_structure.get('total_marks', 100)} marks):
        {questions_list}
        
        Please grade this submission carefully, following these guidelines:
        - Award full marks ({lab_structure.get('marks_per_question', 25)}) if the section is complete, correct, and includes thorough analysis
        - Award partial marks (15-23) if the section is partially correct or has minor errors
        - Award minimal marks (1-14) if the section has major errors but shows some understanding
        - Award 0 marks if the section is not attempted or completely incorrect
        
        For each section, provide specific feedback explaining why marks were deducted. Be constructive and helpful.
        
        Format your response as JSON with the following structure:
        {{
            "problems": [
                {{
                    "problem_number": 1,
                    "name": "{lab_structure.get('question_names', ['Section 1'])[0]}",
                    "score": 23,
                    "max_score": {lab_structure.get('marks_per_question', 25)},
                    "feedback": "Good analysis of the signal characteristics, but missed identifying aliasing effects."
                }},
                // Repeat for all sections
            ],
            "overall_score": 95,
            "overall_max": {lab_structure.get('total_marks', 100)},
            "overall_feedback": "Excellent lab report overall with clear plots and thorough analysis. Minor issues in signal analysis section."
        }}
        
        Return only the JSON with no additional text. Ensure you grade all {lab_structure.get('total_questions', 4)} sections.
        """
    else:
        # Prompt without solution
        return f"""
        You are an expert teaching assistant grading a Digital Signal Processing (ECE 317) lab report on {lab_structure.get('name', 'Audio Signals')}.
        
        I have provided:
        1. The lab instructions PDF
        2. The student's submission
        
        This lab has {lab_structure.get('total_questions', 4)} main sections, each worth {lab_structure.get('marks_per_question', 25)} marks (for a total of {lab_structure.get('total_marks', 100)} marks):
        {questions_list}
        
        Please grade this submission carefully, following these guidelines:
        - Award full marks ({lab_structure.get('marks_per_question', 25)}) if the section is complete, correct, and includes thorough analysis
        - Award partial marks (15-23) if the section is partially correct or has minor errors
        - Award minimal marks (1-14) if the section has major errors but shows some understanding
        - Award 0 marks if the section is not attempted or completely incorrect
        
        For each section, provide specific feedback explaining why marks were deducted. Be constructive and helpful.
        Use your expert knowledge of digital signal processing to evaluate the correctness of:
        - Sampling and aliasing concepts
        - Filter design and implementation
        - Frequency domain analysis
        - Audio quality assessment techniques
        - MATLAB code and plots
        
        Format your response as JSON with the following structure:
        {{
            "problems": [
                {{
                    "problem_number": 1,
                    "name": "{lab_structure.get('question_names', ['Section 1'])[0]}",
                    "score": 23,
                    "max_score": {lab_structure.get('marks_per_question', 25)},
                    "feedback": "Good analysis of the signal characteristics, but missed identifying aliasing effects."
                }},
                // Repeat for all sections
            ],
            "overall_score": 95,
            "overall_max": {lab_structure.get('total_marks', 100)},
            "overall_feedback": "Excellent lab report overall with clear plots and thorough analysis. Minor issues in signal analysis section."
        }}
        
        Return only the JSON with no additional text. Ensure you grade all {lab_structure.get('total_questions', 4)} sections.
        """

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
    
    # Format the list of questions for the prompt
    questions_list = ""
    for i, name in enumerate(lab_structure.get("question_names", [])):
        questions_list += f"{i+1}. {name}  \n"
    
    if with_solution:
        return f"""
        You are an expert teaching assistant grading a Digital Signal Processing (ECE 317) lab report.
        
        I have provided:
        1. The lab instructions PDF
        2. The instructor's solution or grading rubric (if available)
        3. The student's submission
        
        This lab has {lab_structure.get('total_questions', 4)} main sections, each worth {lab_structure.get('marks_per_question', 25)} marks (for a total of {lab_structure.get('total_marks', 100)} marks):
        {questions_list}
        
        Please grade this submission carefully, focusing on:
        - Correctness of concepts and calculations
        - Quality of signal processing implementation
        - Analysis and interpretation of results
        - Clarity of explanations and plots
        
        For each section, provide specific feedback explaining why marks were deducted.
        
        Format your response as JSON with the following structure:
        {{
            "problems": [
                {{
                    "problem_number": 1,
                    "name": "{lab_structure.get('question_names', ['Section 1'])[0]}",
                    "score": 23,
                    "max_score": {lab_structure.get('marks_per_question', 25)},
                    "feedback": "Good work on this section, but missed certain aspects..."
                }},
                // Continue for all sections
            ],
            "overall_score": 90,
            "overall_max": {lab_structure.get('total_marks', 100)},
            "overall_feedback": "Overall feedback on the lab submission..."
        }}
        
        Return only the JSON with no additional text. Ensure you grade all {lab_structure.get('total_questions', 4)} sections.
        """
    else:
        return f"""
        You are an expert teaching assistant grading a Digital Signal Processing (ECE 317) lab report.
        
        I have provided:
        1. The lab instructions PDF
        2. The student's submission
        
        This lab has {lab_structure.get('total_questions', 4)} main sections, each worth {lab_structure.get('marks_per_question', 25)} marks (for a total of {lab_structure.get('total_marks', 100)} marks):
        {questions_list}
        
        Please grade this submission carefully, focusing on:
        - Correctness of concepts and calculations
        - Quality of signal processing implementation
        - Analysis and interpretation of results
        - Clarity of explanations and plots
        
        For each section, provide specific feedback explaining why marks were deducted.
        
        Format your response as JSON with the following structure:
        {{
            "problems": [
                {{
                    "problem_number": 1,
                    "name": "{lab_structure.get('question_names', ['Section 1'])[0]}",
                    "score": 23,
                    "max_score": {lab_structure.get('marks_per_question', 25)},
                    "feedback": "Good work on this section, but missed certain aspects..."
                }},
                // Continue for all sections
            ],
            "overall_score": 90,
            "overall_max": {lab_structure.get('total_marks', 100)},
            "overall_feedback": "Overall feedback on the lab submission..."
        }}
        
        Return only the JSON with no additional text. Ensure you grade all {lab_structure.get('total_questions', 4)} sections.
        """

def generate_dynamic_lab_prompt(lab_structure: Dict[str, Any], with_solution: bool = True) -> str:
    """
    Generate a dynamic lab grading prompt based on AI analysis of lab instructions.
    
    Args:
        lab_structure: Dictionary with lab structure from AI analysis
        with_solution: Whether a solution is provided
        
    Returns:
        Dynamically generated grading prompt text
    """
    lab_name = lab_structure.get("name", "Lab Exercise")
    total_questions = lab_structure.get("total_questions", 4)
    question_names = lab_structure.get("question_names", [f"Question {i+1}" for i in range(total_questions)])
    total_marks = lab_structure.get("total_marks", 100)
    
    # Handle per-question marks
    if "question_points" in lab_structure:
        question_points = lab_structure["question_points"]
    elif "marks_per_question" in lab_structure:
        marks_per_question = lab_structure["marks_per_question"]
        question_points = [marks_per_question] * total_questions
    else:
        # Default to equal distribution
        marks_per_question = total_marks // total_questions
        question_points = [marks_per_question] * total_questions
    
    # Format the list of questions with their point values for the prompt
    questions_list = ""
    for i, (name, points) in enumerate(zip(question_names, question_points)):
        questions_list += f"{i+1}. {name} ({points} marks)  \n"
    
    # Determine average points per question for partial grading guidance
    avg_points = sum(question_points) / len(question_points) if question_points else 25
    
    if with_solution:
        return f"""
        You are an expert teaching assistant grading a Digital Signal Processing (ECE 317) lab report on {lab_name}.
        
        I have provided:
        1. The lab instructions PDF
        2. The instructor's solution or grading rubric (if available)
        3. The student's submission
        
        This lab has {total_questions} main sections with the following point allocations (for a total of {total_marks} marks):
        {questions_list}
        
        Please grade this submission carefully, following these guidelines:
        - Award full marks for a section if it is complete, correct, and includes thorough analysis
        - Award approximately 70-90% of the marks for a section if it is partially correct or has minor errors
        - Award approximately 1-70% of the marks for a section if it has major errors but shows some understanding
        - Award 0 marks if the section is not attempted or completely incorrect
        
        For each section, provide specific feedback explaining why marks were deducted. Be constructive and helpful.
        
        Format your response as JSON with the following structure:
        {{
            "problems": [
                {{
                    "problem_number": 1,
                    "name": "{question_names[0] if question_names else 'Question 1'}",
                    "score": 23,
                    "max_score": {question_points[0] if question_points else avg_points},
                    "feedback": "Good analysis of the signal characteristics, but missed identifying aliasing effects."
                }},
                // Repeat for all sections
            ],
            "overall_score": 95,
            "overall_max": {total_marks},
            "overall_feedback": "Excellent lab report overall with clear plots and thorough analysis. Minor issues in signal analysis section."
        }}
        
        Return only the JSON with no additional text. Ensure you grade all {total_questions} sections.
        """
    else:
        # Prompt without solution
        return f"""
        You are an expert teaching assistant grading a Digital Signal Processing (ECE 317) lab report on {lab_name}.
        
        I have provided:
        1. The lab instructions PDF
        2. The student's submission
        
        This lab has {total_questions} main sections with the following point allocations (for a total of {total_marks} marks):
        {questions_list}
        
        Please grade this submission carefully, following these guidelines:
        - Award full marks for a section if it is complete, correct, and includes thorough analysis
        - Award approximately 70-90% of the marks for a section if it is partially correct or has minor errors
        - Award approximately 1-70% of the marks for a section if it has major errors but shows some understanding
        - Award 0 marks if the section is not attempted or completely incorrect
        
        For each section, provide specific feedback explaining why marks were deducted. Be constructive and helpful.
        Use your expert knowledge of digital signal processing to evaluate the correctness of concepts, calculations, implementations, and analysis.
        
        Format your response as JSON with the following structure:
        {{
            "problems": [
                {{
                    "problem_number": 1,
                    "name": "{question_names[0] if question_names else 'Question 1'}",
                    "score": 23,
                    "max_score": {question_points[0] if question_points else avg_points},
                    "feedback": "Good analysis of the signal characteristics, but missed identifying aliasing effects."
                }},
                // Repeat for all sections
            ],
            "overall_score": 95,
            "overall_max": {total_marks},
            "overall_feedback": "Excellent lab report overall with clear plots and thorough analysis. Minor issues in signal analysis section."
        }}
        
        Return only the JSON with no additional text. Ensure you grade all {total_questions} sections.
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
    # Get the appropriate grading prompt
    prompt = get_lab_grading_prompt(lab_id, solution is not None, lab_structure)
    
    # Try to use dynamic prompt if it exists
    if lab_structure:
        try:
            prompt = generate_dynamic_lab_prompt(lab_structure, solution is not None)
        except Exception as e:
            print(f"Error generating dynamic prompt: {str(e)}")
            # Fall back to standard prompt
            pass
    
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