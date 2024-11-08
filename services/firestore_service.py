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
        """
        Save video analysis results to Firestore.
        
        Args:
            video_name: Name of the video
            analysis_result: Analysis results dictionary
            video_url: URL of the video in GCS
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            doc_ref = self.collection.document(video_name)
            doc_ref.set({
                'video_name': video_name,
                'video_url': video_url,
                'analysis_result': analysis_result,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'status': 'completed'
            })
            
            self.logger.info(f"Successfully saved analysis for video: {video_name}")
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
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting analysis for {video_name}: {str(e)}")
            return None

    def get_all_analyses(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all video analyses with pagination.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of analysis results
        """
        try:
            query = (self.collection
                    .order_by('timestamp', direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            docs = query.stream()
            return [{**doc.to_dict(), 'id': doc.id} for doc in docs]
            
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