"""
Implementation of the BaseModel interface for Anthropic Claude API.
"""

import os
import re
import math
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union

try:
    from anthropic import Anthropic, RateLimitError
except ImportError:
    print("Warning: anthropic package not installed. Please install with: pip install anthropic")

from model_interface.base_model import BaseModel
import config
import prompt_templates
import logging

# Set up logger
logger = logging.getLogger("model_interface")

class TokenBucket:
    """
    Token bucket for rate limiting API calls.
    Tracks tokens used and resets the counter periodically to stay within rate limits.
    """
    
    def __init__(self, tokens_per_minute: int, buffer_factor: float = 0.9):
        """
        Initialize the token bucket.
        
        Args:
            tokens_per_minute: Maximum number of tokens per minute
            buffer_factor: Factor to reduce the token limit (safety margin)
        """
        self.max_tokens = tokens_per_minute * buffer_factor
        self.remaining_tokens = self.max_tokens
        self.last_reset = datetime.now()
        self.lock = False  # Simple lock mechanism

    def consume(self, tokens: int) -> bool:
        """
        Consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if not enough tokens available
        """
        # Check if it's time to reset the counter
        self._check_reset()
        
        # First check if enough tokens are available
        if self.remaining_tokens < tokens:
            return False
        
        # Consume tokens
        self.remaining_tokens -= tokens
        return True

    def get_wait_time(self, tokens: int) -> float:
        """
        Calculate how long to wait before there are enough tokens.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Wait time in seconds
        """
        # Check if it's time to reset the counter
        self._check_reset()
        
        # If we already have enough tokens, return 0
        if self.remaining_tokens >= tokens:
            return 0
        
        # Calculate how many tokens we need to wait for
        tokens_needed = tokens - self.remaining_tokens
        
        # Calculate how long until the next reset gives us enough tokens
        # Tokens refill at a rate of self.max_tokens per 60 seconds
        time_since_reset = (datetime.now() - self.last_reset).total_seconds()
        time_per_token = 60 / self.max_tokens
        
        # Calculate wait time
        wait_time = tokens_needed * time_per_token
        
        # Adjust for time already passed since last reset
        wait_time = max(0, wait_time - time_since_reset)
        
        return wait_time

    def _check_reset(self) -> None:
        """Check if it's time to reset the token counter."""
        time_since_reset = (datetime.now() - self.last_reset).total_seconds()
        
        # Reset every minute to maintain the tokens_per_minute rate
        if time_since_reset >= 60:
            # Calculate how many tokens are refilled
            tokens_to_refill = min(
                self.max_tokens,
                self.max_tokens * (time_since_reset / 60)
            )
            
            # Update token count and timestamp
            self.remaining_tokens = min(self.max_tokens, self.remaining_tokens + tokens_to_refill)
            self.last_reset = datetime.now()

class AnthropicModel(BaseModel):
    """
    Implementation of the BaseModel interface for Anthropic Claude API.
    """
    
    # Class-level token bucket for rate limiting across all instances
    token_bucket = None
    
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
                logger.error(f"Error initializing Anthropic client: {str(e)}")
                
        # Initialize token bucket if not already initialized
        if AnthropicModel.token_bucket is None:
            rate_limit_config = config.API_SETTINGS.get("anthropic_rate_limit", {})
            tokens_per_minute = rate_limit_config.get("tokens_per_minute", 20000)
            buffer_factor = rate_limit_config.get("token_buffer", 0.9)
            AnthropicModel.token_bucket = TokenBucket(tokens_per_minute, buffer_factor)
    
    def validate_api_key(self) -> bool:
        """
        Validate that the Anthropic API key is set and working.
        
        Returns:
            True if valid, False otherwise
        """
        if not self.api_key:
            logger.error("Anthropic API key not set. Please add it to your config.")
            return False
            
        if not self.client:
            try:
                self.client = Anthropic(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Error initializing Anthropic client: {str(e)}")
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
            logger.error(f"API key validation failed: {str(e)}")
            return False
    
    def _estimate_tokens(self, message_content: List[Dict[str, Any]], system_prompt: str) -> int:
        """
        Estimate the number of tokens in a message.
        
        Args:
            message_content: Message content to estimate tokens for
            system_prompt: System prompt to include in estimate
            
        Returns:
            Estimated token count
        """
        # Convert complex message content to string for estimation
        message_text = ""
        if isinstance(message_content, list):
            for item in message_content:
                if isinstance(item, dict):
                    if 'text' in item:
                        message_text += str(item['text']) + " "
                    elif 'content' in item:
                        message_text += str(item['content']) + " "
                elif isinstance(item, str):
                    message_text += item + " "
        elif isinstance(message_content, str):
            message_text = message_content
            
        # Simple heuristic: approx 4 chars per token for English text
        prompt_tokens = len(message_text) / 4
        system_tokens = len(system_prompt) / 4
        
        # Add overhead for message formatting, headers, etc.
        overhead = 20  # Tokens for message formatting
        
        # Add tokens for max_tokens output
        total_tokens = prompt_tokens + system_tokens + self.max_tokens + overhead
        
        # Return ceiling of token count
        return math.ceil(total_tokens)
    
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
        
        # Estimate token usage for rate limiting
        estimated_tokens = self._estimate_tokens(message_content, system_prompt)
        
        try:
            # Check if we have enough tokens in the bucket
            if not AnthropicModel.token_bucket.consume(estimated_tokens):
                # Not enough tokens, calculate wait time
                wait_time = AnthropicModel.token_bucket.get_wait_time(estimated_tokens)
                
                if wait_time > 0:
                    logger.info(f"Retrying request to /v1/messages in {wait_time:.6f} seconds")
                    time.sleep(wait_time)
            
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
            
        except RateLimitError as e:
            # Handle rate limit error with adaptive backoff
            rate_limit_config = config.API_SETTINGS.get("anthropic_rate_limit", {})
            
            # Extract retry-after time if available
            retry_after = 60  # Default 1 minute
            
            # Try to extract the retry-after from the exception message
            pattern = r"Please retry after (\d+) seconds"
            match = re.search(pattern, str(e))
            if match:
                retry_after = int(match.group(1))
            
            # Use the error message to guide the backoff
            if "per minute" in str(e):
                # We're exceeding tokens per minute rate
                retry_after = max(retry_after, 60)  # At least 1 minute
            
            # Cap at max backoff time
            max_backoff = rate_limit_config.get("max_backoff", 120)
            retry_after = min(retry_after, max_backoff)
            
            # Add jitter if configured
            if rate_limit_config.get("jitter", True):
                jitter = random.uniform(0.8, 1.2)
                retry_after = retry_after * jitter
                
            logger.info(f"Rate limit hit. Retrying in {retry_after:.2f} seconds...")
            time.sleep(retry_after)
            
            # Reset the token bucket after waiting
            AnthropicModel.token_bucket = TokenBucket(
                rate_limit_config.get("tokens_per_minute", 20000),
                rate_limit_config.get("token_buffer", 0.9)
            )
            
            # Return the error instead of retrying to let the caller handle the retry
            return {
                "error": True, 
                "error_message": f"Rate limit error: {str(e)}",
                "retry_after": retry_after,
                "rate_limit_error": True
            }
            
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