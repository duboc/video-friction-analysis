from pathlib import Path
from typing import List
import os
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Settings:
    """Configuration settings loaded from environment variables."""
    
    PROJECT_ID: str = os.getenv('GCP_PROJECT')
    BUCKET_NAME: str = os.getenv('GCS_BUCKET')
    DEFAULT_REGION: str = os.getenv('DEFAULT_REGION', 'us-central1')
    REGIONS: List[str] = os.getenv('REGIONS', 'us-central1,europe-west4,asia-east1').split(',')
    MODEL_NAME: str = os.getenv('VERTEX_MODEL_NAME', 'gemini-1.5-pro-002')
    COLLECTION_NAME: str = os.getenv('FIRESTORE_COLLECTION', 'video_analysis')
    ALLOWED_EXTENSIONS: List[str] = os.getenv('ALLOWED_VIDEO_EXTENSIONS', 'mp4,avi,mov').split(',')
    MAX_FILE_SIZE: int = int(os.getenv('MAX_VIDEO_SIZE_MB', '100')) * 1024 * 1024  # Convert MB to bytes

    @classmethod
    def validate_settings(cls) -> List[str]:
        """Validate that all required settings are present."""
        missing_vars = []
        required_vars = ['PROJECT_ID', 'BUCKET_NAME']
        
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        return missing_vars

    @classmethod
    def is_valid(cls) -> bool:
        """Check if all required settings are valid."""
        return len(cls.validate_settings()) == 0