"""
Abstract base class for AI model interfaces.
All model-specific implementations should inherit from this class.
"""

import json
import time
import random
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
            # Find JSON in the response (in case the model adds text before/after)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in the response")
                
        except Exception as e:
            print(f"Error extracting JSON from response: {str(e)}")
            print(f"Response text: {response_text[:100]}...")
            
            # Try to fix common JSON errors
            try:
                # Sometimes the model adds markdown formatting
                cleaned_text = response_text.replace("```json", "").replace("```", "")
                return json.loads(cleaned_text)
            except:
                # Return error object
                return {
                    "error": True,
                    "error_message": f"Failed to parse JSON: {str(e)}",
                    "raw_response": response_text[:500]  # First 500 chars only
                }
    
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
                
        # Ensure overall_score matches sum of individual scores
        sum_scores = sum(p.get("score", 0) for p in problems)
        if result.get("overall_score") != sum_scores:
            print(f"Warning: overall_score ({result.get('overall_score')}) doesn't match sum of scores ({sum_scores})")
            result["overall_score"] = sum_scores
            
        return result 