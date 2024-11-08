from typing import Callable, Any
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from google.api_core.exceptions import ResourceExhausted
import vertexai
import streamlit as st
from config.settings import Settings

class RetryHandler:
    """Handler for retry operations with regional fallback."""
    
    @staticmethod
    def init_vertex_ai(region: str) -> None:
        """
        Initialize Vertex AI with specific region.
        
        Args:
            region: GCP region to initialize
        """
        vertexai.init(project=Settings.PROJECT_ID, location=region)

    @staticmethod
    def get_retry_strategy():
        """Get the retry strategy configuration."""
        return {
            'wait': wait_exponential(multiplier=1, min=2, max=10),
            'stop': stop_after_attempt(3)
        }

    @staticmethod
    @retry(**get_retry_strategy())
    def execute_with_regional_fallback(func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute function with regional fallback.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Any: Function execution result
            
        Raises:
            RetryError: If all regions fail
        """
        last_exception = None
        
        for region in Settings.REGIONS:
            try:
                RetryHandler.init_vertex_ai(region)
                return func(*args, **kwargs)
            except ResourceExhausted as e:
                last_exception = e
                st.warning(f"Region {region} exhausted, trying next region...")
                continue
            except Exception as e:
                st.error(f"Unexpected error in region {region}: {str(e)}")
                raise

        raise RetryError(f"All regions exhausted. Last error: {str(last_exception)}")