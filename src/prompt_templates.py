"""
Templates for prompts to be sent to AI models for grading.
"""

from typing import Dict, Any, List, Optional

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

def get_lab_grading_prompt(lab_id: str, with_solution: bool = True) -> str:
    """
    Get the appropriate grading prompt for a specific lab.
    
    Args:
        lab_id: Lab identifier (e.g., 'lab_05')
        with_solution: Whether a solution is provided
        
    Returns:
        Grading prompt text
    """
    if lab_id == "lab_05":
        return get_lab05_prompt(with_solution)
    else:
        # Fall back to a generic prompt
        return get_generic_lab_prompt(with_solution)

def get_lab05_prompt(with_solution: bool = True) -> str:
    """
    Get the prompt specifically for Lab 5 (Audio Signals).
    
    Args:
        with_solution: Whether a solution is provided
        
    Returns:
        Grading prompt text
    """
    if with_solution:
        return """
        You are an expert teaching assistant grading a Digital Signal Processing (ECE 317) lab report on Audio Signals.
        
        I have provided multiple images in the following order:
        1. First set: The lab instructions
        2. Second set: The instructor's solution or grading rubric
        3. Third set: The student's submission
        
        This lab has 4 main sections, each worth 25 marks (for a total of 100 marks):
        1. Signal Analysis
        2. Filtering Implementation  
        3. Frequency Response
        4. Audio Quality Assessment
        
        Please grade this submission carefully, following these guidelines:
        - Award full marks (25) if the section is complete, correct, and includes thorough analysis
        - Award partial marks (15-23) if the section is partially correct or has minor errors
        - Award minimal marks (1-14) if the section has major errors but shows some understanding
        - Award 0 marks if the section is not attempted or completely incorrect
        
        For each section, provide specific feedback explaining why marks were deducted. Be constructive and helpful.
        
        Format your response as JSON with the following structure:
        {
            "problems": [
                {
                    "problem_number": 1,
                    "name": "Signal Analysis",
                    "score": 23,
                    "max_score": 25,
                    "feedback": "Good analysis of the signal characteristics, but missed identifying aliasing effects."
                },
                {
                    "problem_number": 2,
                    "name": "Filtering Implementation",
                    "score": 25,
                    "max_score": 25
                },
                // Repeat for sections 3-4
            ],
            "overall_score": 95,
            "overall_max": 100,
            "overall_feedback": "Excellent lab report overall with clear plots and thorough analysis. Minor issues in signal analysis section."
        }
        
        Return only the JSON with no additional text. Ensure you grade all 4 sections.
        """
    else:
        # Prompt without solution
        return """
        You are an expert teaching assistant grading a Digital Signal Processing (ECE 317) lab report on Audio Signals.
        
        I have provided multiple images in the following order:
        1. First set: The lab instructions
        2. Second set: The student's submission
        
        This lab has 4 main sections, each worth 25 marks (for a total of 100 marks):
        1. Signal Analysis
        2. Filtering Implementation  
        3. Frequency Response
        4. Audio Quality Assessment
        
        Please grade this submission carefully, following these guidelines:
        - Award full marks (25) if the section is complete, correct, and includes thorough analysis
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
        {
            "problems": [
                {
                    "problem_number": 1,
                    "name": "Signal Analysis",
                    "score": 23,
                    "max_score": 25,
                    "feedback": "Good analysis of the signal characteristics, but missed identifying aliasing effects."
                },
                {
                    "problem_number": 2,
                    "name": "Filtering Implementation",
                    "score": 25,
                    "max_score": 25
                },
                // Repeat for sections 3-4
            ],
            "overall_score": 95,
            "overall_max": 100,
            "overall_feedback": "Excellent lab report overall with clear plots and thorough analysis. Minor issues in signal analysis section."
        }
        
        Return only the JSON with no additional text. Ensure you grade all 4 sections.
        """

def get_generic_lab_prompt(with_solution: bool = True) -> str:
    """
    Get a generic lab grading prompt that can be used for any lab.
    
    Args:
        with_solution: Whether a solution is provided
        
    Returns:
        Grading prompt text
    """
    if with_solution:
        return """
        You are an expert teaching assistant grading a Digital Signal Processing (ECE 317) lab report.
        
        I have provided multiple images in the following order:
        1. First set: The lab instructions
        2. Second set: The instructor's solution or grading rubric
        3. Third set: The student's submission
        
        Please grade this submission carefully, focusing on:
        - Correctness of concepts and calculations
        - Quality of signal processing implementation
        - Analysis and interpretation of results
        - Clarity of explanations and plots
        
        For each section, provide specific feedback explaining why marks were deducted.
        Be constructive and helpful in your feedback.
        
        Format your response as JSON with the following structure:
        {
            "problems": [
                {
                    "problem_number": 1,
                    "name": "Section 1",
                    "score": 20,
                    "max_score": 25,
                    "feedback": "Specific feedback on this section"
                },
                // Repeat for other sections
            ],
            "overall_score": 85,
            "overall_max": 100,
            "overall_feedback": "Overall assessment of the lab report"
        }
        
        Return only the JSON with no additional text.
        """
    else:
        # Prompt without solution
        return """
        You are an expert teaching assistant grading a Digital Signal Processing (ECE 317) lab report.
        
        I have provided multiple images in the following order:
        1. First set: The lab instructions
        2. Second set: The student's submission
        
        Please grade this submission carefully, focusing on:
        - Correctness of concepts and calculations
        - Quality of signal processing implementation
        - Analysis and interpretation of results
        - Clarity of explanations and plots
        
        Use your expert knowledge of digital signal processing to evaluate the correctness
        of concepts, implementations, and analyses presented in the lab report.
        
        For each section, provide specific feedback explaining why marks were deducted.
        Be constructive and helpful in your feedback.
        
        Format your response as JSON with the following structure:
        {
            "problems": [
                {
                    "problem_number": 1,
                    "name": "Section 1",
                    "score": 20,
                    "max_score": 25,
                    "feedback": "Specific feedback on this section"
                },
                // Repeat for other sections
            ],
            "overall_score": 85,
            "overall_max": 100,
            "overall_feedback": "Overall assessment of the lab report"
        }
        
        Return only the JSON with no additional text.
        """

def build_grading_message(
    lab_id: str,
    lab_instructions: List[Dict[str, Any]], 
    student_submission: List[Dict[str, Any]],
    solution: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Build the complete message to send to the AI model.
    
    Args:
        lab_id: Lab identifier
        lab_instructions: List of content objects for lab instructions
        student_submission: List of content objects for student submission
        solution: List of content objects for solution (optional)
        
    Returns:
        List of message content objects to send to the model
    """
    # Get the appropriate prompt based on whether a solution is provided
    grading_prompt = get_lab_grading_prompt(lab_id, solution is not None)
    
    # Start with the text prompt
    message_content = [{"type": "text", "text": grading_prompt}]
    
    # Add lab instructions
    message_content.append({"type": "text", "text": "LAB INSTRUCTIONS:"})
    message_content.extend(lab_instructions)
    
    # Add solution if provided
    if solution:
        message_content.append({"type": "text", "text": "SOLUTION/GRADING RUBRIC:"})
        message_content.extend(solution)
    
    # Add student submission
    message_content.append({"type": "text", "text": "STUDENT SUBMISSION:"})
    message_content.extend(student_submission)
    
    return message_content 