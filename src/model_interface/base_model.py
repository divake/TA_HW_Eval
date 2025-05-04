"""
Abstract base class for AI model interfaces.
All model-specific implementations should inherit from this class.
"""

import json
import time
import random
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple

import sys
import os
# Add the parent directory to the path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

class BaseModel(ABC):
    """
    Abstract base class for AI model interfaces.
    """
    
    def __init__(self):
        """Initialize the model interface."""
        self.model_type = "base"
        self.model_name = "base_model"
        self.max_tokens = 4000
        self.temperature = 0.0
        
    @abstractmethod
    def validate_api_key(self) -> bool:
        """
        Validate that the API key is set and valid.
        
        Returns:
            True if valid, False otherwise
        """
        pass
        
    @abstractmethod
    def send_message(self, message_content: List[Dict[str, Any]], system_prompt: str = None) -> Dict[str, Any]:
        """
        Send a message to the model and get a response.
        
        Args:
            message_content: List of content objects formatted for the specific model
            system_prompt: Optional system prompt to use
            
        Returns:
            Dictionary with the model's response
        """
        pass
        
    def extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """
        Extract JSON from the model's response text.
        
        Args:
            response_text: The text response from the model
            
        Returns:
            Parsed JSON as a dictionary
        """
        try:
            # First try direct JSON parsing of the whole response
            try:
                return json.loads(response_text)
            except:
                # If that fails, try to find JSON delimiters
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    try:
                        return json.loads(json_str)
                    except:
                        # Try to fix common JSON issues
                        # Replace single quotes with double quotes
                        json_str = json_str.replace("'", "\"")
                        # Fix common missing quotes around keys
                        json_str = re.sub(r'([{,])\s*(\w+):', r'\1"\2":', json_str)
                        # Try parsing again
                        try:
                            return json.loads(json_str)
                        except:
                            # Fall back to text parsing
                            pass
            
            # If JSON parsing failed, try to parse as a structured text response
            parsed_result = self.parse_text_grading_response(response_text)
            if parsed_result:
                # Add a warning flag but still return the parsed result
                parsed_result["_warning"] = "Response was parsed from text format, not JSON"
                return parsed_result
                
            # If all parsing attempts fail, return a detailed error
            return {
                "error": True,
                "error_message": "Failed to parse response as JSON or structured text",
                "raw_response": response_text[:500]  # First 500 chars only
            }
                
        except Exception as e:
            print(f"Error extracting JSON from response: {str(e)}")
            print(f"Response text: {response_text[:100]}...")
            
            # Try to parse as a structured text response as last resort
            try:
                parsed_result = self.parse_text_grading_response(response_text)
                if parsed_result:
                    parsed_result["_warning"] = "Parsed from text due to JSON error"
                    return parsed_result
            except:
                pass
            
            # Return error object with the original error
            return {
                "error": True,
                "error_message": f"Failed to parse JSON: {str(e)}",
                "raw_response": response_text[:500]  # First 500 chars only
            }
    
    def parse_text_grading_response(self, text_response: str) -> Dict[str, Any]:
        """
        Parse the text response from the model into a structured format.
        
        Args:
            text_response: The raw text response from the model
            
        Returns:
            Dictionary with structured grading results or None if parsing fails
        """
        try:
            lines = text_response.strip().split('\n')
            result = {
                "problems": [],
                "overall_score": 0,
                "overall_max": 100,  # Default
                "overall_feedback": ""
            }
            
            current_problem = None
            total_score = 0
            total_possible = 0
            
            # Process line by line
            for line in lines:
                line = line.strip()
                
                # Skip introductory text
                if "grade the student" in line.lower() or not line:
                    continue
                    
                # Check if this is a question line
                if line.startswith("QUESTION ") or line.startswith("PROBLEM "):
                    # Save previous problem if exists
                    if current_problem is not None:
                        result["problems"].append(current_problem)
                        
                    # Extract problem number
                    parts = line.split()
                    try:
                        problem_number = int(parts[1])
                    except (IndexError, ValueError):
                        problem_number = len(result["problems"]) + 1
                        
                    # Create new problem
                    current_problem = {
                        "problem_number": problem_number,
                        "score": 0,
                        "max_score": 0,
                        "feedback": "",
                        "justification": ""
                    }
                        
                # Check if this is a score line
                elif line.startswith("Score:") and current_problem is not None:
                    score_part = line.split("Score:")[1].strip()
                    if "[" in score_part and "/" in score_part and "]" in score_part:
                        # Extract score format [X/Y]
                        score_text = score_part.split("[")[1].split("]")[0]
                        parts = score_text.split("/")
                        try:
                            current_problem["score"] = float(parts[0])
                            current_problem["max_score"] = float(parts[1])
                            total_score += current_problem["score"]
                            total_possible += current_problem["max_score"]
                        except (IndexError, ValueError):
                            print(f"Could not parse score: {score_part}")
                    else:
                        # Try to handle other score formats
                        try:
                            # Look for numbers in the score line
                            numbers = re.findall(r"[-+]?\d*\.\d+|\d+", score_part)
                            if len(numbers) >= 2:
                                current_problem["score"] = float(numbers[0])
                                current_problem["max_score"] = float(numbers[1])
                                total_score += current_problem["score"]
                                total_possible += current_problem["max_score"]
                            elif len(numbers) == 1:
                                # Assume out of 25 if only one number
                                current_problem["score"] = float(numbers[0])
                                current_problem["max_score"] = 25
                                total_score += current_problem["score"]
                                total_possible += 25
                        except:
                            print(f"Could not parse alternative score format: {score_part}")
                            
                # Check if this is a feedback line
                elif line.startswith("Feedback:") and current_problem is not None:
                    current_problem["feedback"] = line.split("Feedback:")[1].strip()
                    
                # Check if this is a justification line
                elif line.startswith("Justification:") and current_problem is not None:
                    current_problem["justification"] = line.split("Justification:")[1].strip()
                    
                # Check if this is the overall score line
                elif "OVERALL SCORE:" in line:
                    # Try to extract percentage
                    if "%" in line:
                        try:
                            percent_text = re.search(r"(\d+(\.\d+)?)%", line)
                            if percent_text:
                                result["overall_score"] = float(percent_text.group(1))
                        except:
                            print(f"Could not parse overall percentage: {line}")
                            
                    # Try to extract points
                    points_match = re.search(r"\((\d+(\.\d+)?)/(\d+(\.\d+)?)\s*points?\)", line)
                    if points_match:
                        try:
                            result["overall_score"] = float(points_match.group(1))
                            result["overall_max"] = float(points_match.group(3))
                        except:
                            print(f"Could not parse overall points: {line}")
                            
                    # If percentage and points didn't work, calculate from total
                    if result["overall_score"] == 0 and total_possible > 0:
                        result["overall_score"] = (total_score / total_possible) * 100
                        
                # Check if this is the summary line
                elif "SUMMARY COMMENTS:" in line:
                    result["overall_feedback"] = line.split("SUMMARY COMMENTS:")[1].strip()
                    
                # Append to feedback or justification if continuation
                elif current_problem is not None:
                    if current_problem["feedback"] and not current_problem["justification"]:
                        current_problem["feedback"] += " " + line
                    elif current_problem["justification"]:
                        current_problem["justification"] += " " + line
            
            # Add the last problem if exists
            if current_problem is not None:
                result["problems"].append(current_problem)
            
            # Calculate overall score if not set
            if result["overall_score"] == 0 and total_possible > 0:
                result["overall_score"] = (total_score / total_possible) * 100
                
            # Final validation - must have at least one problem
            if not result["problems"]:
                return None
                
            return result
        except Exception as e:
            print(f"Error parsing text response: {str(e)}")
            return None
    
    def process_with_retry(self, process_func, *args, **kwargs) -> Dict[str, Any]:
        """
        Process a request with retry logic and exponential backoff.
        
        Args:
            process_func: Function to execute with retry logic
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            The result of the function call
        """
        max_retries = config.API_SETTINGS['max_retries']
        base_delay = config.API_SETTINGS['base_delay']
        
        for attempt in range(max_retries):
            try:
                print(f"API attempt {attempt+1}/{max_retries}...")
                return process_func(*args, **kwargs)
                
            except Exception as e:
                # Check for rate limit errors
                if any(err in str(e).lower() for err in ['rate limit', 'rate_limit', 'too many requests', '429']):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(1, 5)
                        print(f"Rate limit hit. Retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
                    else:
                        print(f"Max retries reached after rate limit errors: {str(e)}")
                        return {
                            "error": True,
                            "error_message": f"Rate limit error after {max_retries} attempts: {str(e)}"
                        }
                else:
                    # Other error
                    print(f"API error: {str(e)}")
                    return {
                        "error": True,
                        "error_message": f"API error: {str(e)}"
                    }
        
        # Should not reach here, but just in case
        return {
            "error": True,
            "error_message": "Unexpected error in retry logic"
        }
    
    def validate_grading_result(self, result: Dict[str, Any], expected_problem_count: int = 4) -> Dict[str, Any]:
        """
        Validate that the grading result has the expected structure.
        
        Args:
            result: Grading result dictionary
            expected_problem_count: Expected number of problems in the result
            
        Returns:
            Validated result or error object
        """
        # Check for error
        if result.get("error", False):
            return result
            
        # Check basic structure
        required_fields = ["problems", "overall_score", "overall_max"]
        for field in required_fields:
            if field not in result:
                return {
                    "error": True,
                    "error_message": f"Missing required field: {field}",
                    "partial_result": result
                }
                
        # Check problems length
        problems = result.get("problems", [])
        if len(problems) != expected_problem_count:
            print(f"Warning: Expected {expected_problem_count} problems, got {len(problems)}")
            
            # If fewer problems than expected, try to fill in the missing ones
            if len(problems) < expected_problem_count:
                existing_numbers = [p.get("problem_number") for p in problems]
                for i in range(1, expected_problem_count + 1):
                    if i not in existing_numbers:
                        # Add a placeholder problem with 0 score
                        problems.append({
                            "problem_number": i,
                            "score": 0,
                            "max_score": 25,
                            "feedback": "This section was not evaluated by the AI."
                        })
                        
                # Sort problems by problem number
                problems.sort(key=lambda p: p.get("problem_number", 0))
                result["problems"] = problems
                
                # Update overall score
                overall_score = sum(p.get("score", 0) for p in problems)
                result["overall_score"] = overall_score
        
        # Ensure each problem has a feedback field, even if empty
        for problem in problems:
            if "feedback" not in problem:
                # Get max_score from the problem
                max_score = problem.get("max_score", 25)
                
                # If the score is full marks, set empty feedback
                if problem.get("score", 0) == max_score:
                    problem["feedback"] = ""
                else:
                    problem["feedback"] = "No specific feedback provided."
                    
        # Add an empty overall_feedback for compatibility with existing code
        if "overall_feedback" not in result:
            result["overall_feedback"] = ""
                
        # Ensure overall_score matches sum of individual scores
        sum_scores = sum(p.get("score", 0) for p in problems)
        if result.get("overall_score") != sum_scores:
            print(f"Warning: overall_score ({result.get('overall_score')}) doesn't match sum of scores ({sum_scores})")
            result["overall_score"] = sum_scores
            
        return result 