"""
Implementation of the BaseModel interface for Anthropic Claude API.
"""

import os
from typing import Dict, List, Any, Optional, Union
import time

try:
    from anthropic import Anthropic
except ImportError:
    print("Warning: anthropic package not installed. Please install with: pip install anthropic")

from model_interface.base_model import BaseModel
import config
import prompt_templates

class AnthropicModel(BaseModel):
    """
    Implementation of the BaseModel interface for Anthropic Claude API.
    """
    
    def __init__(self, model_name: str = None, max_tokens: int = None, temperature: float = None):
        """
        Initialize the Anthropic Claude model interface.
        
        Args:
            model_name: Name of the Claude model to use
            max_tokens: Maximum tokens for model response
            temperature: Temperature setting for response randomness
        """
        super().__init__()
        self.model_type = "anthropic"
        self.model_name = model_name or config.MODELS["anthropic"]["name"]
        self.max_tokens = max_tokens or config.MODELS["anthropic"]["max_tokens"]
        self.temperature = temperature or config.MODELS["anthropic"]["temperature"]
        
        # Get API key from config
        self.api_key = config.ANTHROPIC_API_KEY
        
        # Initialize client if API key is set
        self.client = None
        if self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
            except Exception as e:
                print(f"Error initializing Anthropic client: {str(e)}")
    
    def validate_api_key(self) -> bool:
        """
        Validate that the Anthropic API key is set and working.
        
        Returns:
            True if valid, False otherwise
        """
        if not self.api_key:
            print("Anthropic API key not set. Please add it to your config.")
            return False
            
        if not self.client:
            try:
                self.client = Anthropic(api_key=self.api_key)
            except Exception as e:
                print(f"Error initializing Anthropic client: {str(e)}")
                return False
                
        # Attempt a simple API call to validate the key
        try:
            # Just make a minimal call to check authentication
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}],
                system="Respond with 'OK' only."
            )
            return True
        except Exception as e:
            print(f"API key validation failed: {str(e)}")
            return False
    
    def _process_message(self, message_content: List[Dict[str, Any]], system_prompt: str = None) -> Dict[str, Any]:
        """
        Process a message to the Claude API (internal implementation).
        
        Args:
            message_content: List of content objects in Claude format
            system_prompt: System prompt to use
            
        Returns:
            Response dictionary
        """
        if not self.client:
            if not self.api_key:
                return {"error": True, "error_message": "Anthropic API key not set"}
                
            try:
                self.client = Anthropic(api_key=self.api_key)
            except Exception as e:
                return {"error": True, "error_message": f"Error initializing Anthropic client: {str(e)}"}
        
        # Use default system prompt if none provided
        if system_prompt is None:
            system_prompt = prompt_templates.SYSTEM_PROMPTS["anthropic"]
            
        try:
            # Make the API call
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": message_content}]
            )
            
            # Extract the response text
            response_text = response.content[0].text
            
            # Parse JSON from the response
            grading_result = self.extract_json_from_response(response_text)
            
            return grading_result
            
        except Exception as e:
            return {"error": True, "error_message": f"Error calling Anthropic API: {str(e)}"}
    
    def send_message(self, message_content: List[Dict[str, Any]], system_prompt: str = None) -> Dict[str, Any]:
        """
        Send a message to the Claude API with retry logic.
        
        Args:
            message_content: List of content objects in Claude format
            system_prompt: System prompt to use
            
        Returns:
            Response dictionary with grading results
        """
        return self.process_with_retry(self._process_message, message_content, system_prompt)
        
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the configured model.
        
        Returns:
            Dictionary with model information
        """
        return {
            "type": self.model_type,
            "name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "supports_direct_pdf": True
        } 