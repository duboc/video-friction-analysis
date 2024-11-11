from typing import List, Optional, Dict, Any, Tuple
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import logging
from config.settings import Settings
import time

class FirestoreService:
    """Service for handling Firestore operations."""
    
    def __init__(self):
        """Initialize Firestore client and configure logging."""
        try:
            # Use default credentials from gcloud auth
            self.db = firestore.Client()
            self.collection = self.db.collection(Settings.COLLECTION_NAME)
            
            # Set up logging
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.INFO)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize FirestoreService: {str(e)}")
            raise

    def save_analysis(self, video_name: str, analysis_result: Dict[str, Any], video_url: str) -> Tuple[bool, Optional[str]]:
        """Save video analysis results to Firestore."""
        try:
            doc_ref = self.collection.document(video_name)
            
            # Create the document structure
            doc_data = {
                'video_name': video_name,
                'video_url': video_url,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'status': 'completed',
                'analyses_results': {
                    'video_analysis': analysis_result.get('video_analysis', {}),
                    'user_story': analysis_result.get('user_story', {}),
                    'task_backlog': analysis_result.get('task_backlog', {})
                }
            }
            
            # Log the data being saved for debugging
            self.logger.info(f"Saving analysis data: {doc_data}")
            
            doc_ref.set(doc_data)
            return True, None
            
        except Exception as e:
            error_msg = f"Error saving analysis for {video_name}: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def get_analysis(self, video_name: str) -> Optional[Dict[str, Any]]:
        """
        Get analysis results for a specific video.
        
        Args:
            video_name: Name of the video
            
        Returns:
            Optional[Dict[str, Any]]: Analysis results or None if not found
        """
        try:
            doc_ref = self.collection.document(video_name)
            doc = doc_ref.get()
            
            # Add debug logging
            self.logger.info(f"Attempting to get analysis for video: {video_name}")
            self.logger.info(f"Document exists: {doc.exists}")
            if doc.exists:
                data = doc.to_dict()
                self.logger.info(f"Document data: {data}")
                return data
            
            # If document doesn't exist, try listing all documents to find a match
            all_docs = self.collection.stream()
            for doc in all_docs:
                self.logger.info(f"Found document with ID: {doc.id}")
                if doc.get('video_name') == video_name:
                    return doc.to_dict()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting analysis for {video_name}: {str(e)}")
            return None

    def get_all_analyses(self) -> List[Dict[str, Any]]:
        """Get all analyses from Firestore."""
        try:
            docs = self.collection.get()
            analyses = []
            for doc in docs:
                data = doc.to_dict()
                # Log the retrieved data for debugging
                self.logger.info(f"Retrieved analysis data: {data}")
                analyses.append(data)
            return analyses
        except Exception as e:
            self.logger.error(f"Error getting analyses: {str(e)}")
            return []

    def update_analysis_status(self, video_name: str, status: str) -> None:
        """
        Update the status of a video analysis.
        
        Args:
            video_name: Name of the video
            status: New status ('processing', 'completed', 'failed')
        """
        try:
            doc_ref = self.collection.document(video_name)
            doc_ref.update({
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
        except Exception as e:
            self.logger.error(f"Error updating status for {video_name}: {str(e)}")
            raise

    def delete_analysis(self, video_name: str) -> Tuple[bool, Optional[str]]:
        """
        Delete analysis results for a video.
        
        Args:
            video_name: Name of the video
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            doc_ref = self.collection.document(video_name)
            doc_ref.delete()
            
            self.logger.info(f"Successfully deleted analysis for video: {video_name}")
            return True, None
            
        except Exception as e:
            error_msg = f"Error deleting analysis for {video_name}: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg