from typing import Optional, Dict, Any, Tuple
from vertexai.generative_models import GenerativeModel, GenerationConfig, SafetySetting, HarmCategory, HarmBlockThreshold
import logging
from config.settings import Settings
from schemas.analysis_schemas import VIDEO_ANALYSIS_SCHEMA, USER_STORY_SCHEMA, TASK_BACKLOG_SCHEMA
import json

class VertexService:
    """Service for handling Vertex AI operations."""
    
    def __init__(self):
        """Initialize Vertex AI service and configure logging."""
        self.model = None
        self.schemas = {
            'video_analysis': VIDEO_ANALYSIS_SCHEMA,
            'user_story': USER_STORY_SCHEMA,
            'task_backlog': TASK_BACKLOG_SCHEMA
        }
        self.generation_config = {
            'temperature': 0.3,
            'top_p': 1,
            'top_k': 40,
            'max_output_tokens': 8000,
            'candidate_count': 1,
            'response_mime_type': 'application/json'
        }
        
        # Safety settings for the model
        self.safety_settings = [
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=HarmBlockThreshold.BLOCK_NONE
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=HarmBlockThreshold.BLOCK_NONE
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=HarmBlockThreshold.BLOCK_NONE
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=HarmBlockThreshold.BLOCK_NONE
            )
        ]
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def initialize_model(self, schema_type: str = 'video_analysis') -> Tuple[bool, Optional[str]]:
        """Initialize the Vertex AI model with the specified schema."""
        try:
            schema = self.schemas.get(schema_type)
            if not schema:
                return False, f"Invalid schema type: {schema_type}"

            self.model = GenerativeModel(
                model_name=Settings.MODEL_NAME,
                generation_config=GenerationConfig(
                    temperature=self.generation_config['temperature'],
                    top_p=self.generation_config['top_p'],
                    top_k=self.generation_config['top_k'],
                    candidate_count=self.generation_config['candidate_count'],
                    response_mime_type=self.generation_config['response_mime_type'],
                    response_schema=schema
                ),
                safety_settings=self.safety_settings
            )
            return True, None
        except Exception as e:
            error_msg = f"Error initializing model: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def _generate_content(self, prompt: str, schema_type: str = 'video_analysis') -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Helper method to generate content using the model with the specified schema.
        
        Args:
            prompt: The prompt to send to the model
            schema_type: Type of schema to use ('video_analysis' or 'user_story')
            
        Returns:
            Tuple[bool, Optional[Dict[str, Any]], Optional[str]]: (success, result, error_message)
        """
        try:
            if not self.model:
                success, error = self.initialize_model(schema_type)
                if not success:
                    return False, None, error

            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=self.generation_config['temperature'],
                    top_p=self.generation_config['top_p'],
                    top_k=self.generation_config['top_k'],
                    candidate_count=self.generation_config['candidate_count'],
                    response_mime_type=self.generation_config['response_mime_type'],
                    response_schema=self.schemas[schema_type]
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

    def analyze_video(self, video_url: str, custom_prompt: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Generate video analysis using the video analysis schema."""
        return self._generate_content(custom_prompt or video_url, 'video_analysis')

    def generate_user_story(self, video_analysis: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Generate user stories using the user story schema."""
        return self._generate_content(str(video_analysis), 'user_story')

    def generate_task_backlog(self, user_story: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Generate task backlog from user stories using the task backlog schema."""
        try:
            prompt_template = self._load_and_format_prompt('task_backlog.md')
            prompt = prompt_template.format(user_story=json.dumps(user_story, indent=2))
            return self._generate_content(prompt, 'task_backlog')
        except Exception as e:
            error_msg = f"Error generating task backlog: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def _load_and_format_prompt(self, prompt_file: str) -> str:
        """Helper method to load prompts."""
        try:
            with open(f'prompts/{prompt_file}', 'r') as f:
                prompt_template = f.read()
            return prompt_template
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