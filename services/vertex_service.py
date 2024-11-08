from typing import Optional, Dict, Any, Tuple
from vertexai.generative_models import GenerativeModel, GenerationConfig
from utils.retry_handler import RetryHandler
import logging
from config.settings import Settings
import json

class VertexService:
    """Service for handling Vertex AI operations."""
    
    def __init__(self):
        """Initialize Vertex AI service and configure logging."""
        self.model = None
        self.generation_config = {
            'temperature': 0.9,
            'top_p': 1,
            'top_k': 40,
            'max_output_tokens': 2048,
            'candidate_count': 1
        }
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def initialize_model(self):
        """Initialize the Vertex AI model."""
        try:
            self.model = GenerativeModel(
                model_name=Settings.MODEL_NAME,
                generation_config=GenerationConfig(
                    temperature=self.generation_config['temperature'],
                    top_p=self.generation_config['top_p'],
                    top_k=self.generation_config['top_k'],
                    candidate_count=self.generation_config['candidate_count']
                )
            )
            return True, None
        except Exception as e:
            error_msg = f"Error initializing model: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def _generate_content(self, prompt: str, response_type: str = "application/json") -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Helper method to generate content using the model.
        
        Args:
            prompt: The prompt to send to the model
            response_type: Expected response MIME type
            
        Returns:
            Tuple[bool, Optional[Dict[str, Any]], Optional[str]]: (success, result, error_message)
        """
        try:
            if not self.model:
                success, error = self.initialize_model()
                if not success:
                    return False, None, error

            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=self.generation_config['temperature'],
                    top_p=self.generation_config['top_p'],
                    top_k=self.generation_config['top_k'],
                    candidate_count=self.generation_config['candidate_count'],
                    response_mime_type=response_type
                )
            )
            
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                result = {
                    'raw_analysis': response.text,
                    'structured': False
                }
            
            return True, result, None
                
        except Exception as e:
            error_msg = f"Error generating content: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def analyze_video(self, video_url: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Analyze video using Vertex AI."""
        try:
            prompt_template = self._load_and_format_prompt('video_analysis_prompt.md', video_url=video_url)
            return self._generate_content(prompt_template)
        except Exception as e:
            error_msg = f"Error analyzing video: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def generate_user_story(self, video_analysis: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Generate user stories from video analysis."""
        try:
            prompt_template = self._load_and_format_prompt(
                'user_story.md',
                video_analysis=json.dumps(video_analysis, indent=2)
            )
            return self._generate_content(prompt_template)
        except Exception as e:
            error_msg = f"Error generating user story: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def generate_task_backlog(self, user_story: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Generate task backlog from user stories."""
        try:
            prompt_template = self._load_and_format_prompt(
                'task_backlog.md',
                user_story=json.dumps(user_story, indent=2)
            )
            return self._generate_content(prompt_template)
        except Exception as e:
            error_msg = f"Error generating task backlog: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def _load_and_format_prompt(self, prompt_file: str, **kwargs) -> str:
        """Helper method to load and format prompts."""
        try:
            with open(f'prompts/{prompt_file}', 'r') as f:
                prompt_template = f.read()
            return prompt_template.format(**kwargs)
        except Exception as e:
            self.logger.error(f"Error loading prompt {prompt_file}: {str(e)}")
            raise

    def get_model_status(self) -> Dict[str, Any]:
        """Get current model status and configuration."""
        try:
            if not self.model:
                self.initialize_model()
                
            return {
                'model_name': Settings.MODEL_NAME,
                'initialized': self.model is not None,
                'current_region': Settings.DEFAULT_REGION,
                'config': self.generation_config
            }
        except Exception as e:
            self.logger.error(f"Error getting model status: {str(e)}")
            return {
                'error': str(e),
                'initialized': False
            }