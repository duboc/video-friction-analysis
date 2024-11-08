from typing import List, Optional, Tuple, Dict, Any
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
import logging
import streamlit as st
from config.settings import Settings
from utils.security import SecurityUtils
from pathlib import Path
import time
import os
import datetime
from datetime import timedelta as datetime_timedelta

class StorageService:
    """Service for handling Google Cloud Storage operations."""
    
    def __init__(self):
        """Initialize storage client and configure logging."""
        try:
            # Use application default credentials
            self.client = storage.Client()
            self.bucket = self.client.bucket(Settings.BUCKET_NAME)
            
            # Set up logging
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.INFO)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize StorageService: {str(e)}")
            raise

    def get_public_url(self, blob_name: str) -> str:
        """Generate a public URL for a blob."""
        return f"https://storage.googleapis.com/{Settings.BUCKET_NAME}/{blob_name}"

    def upload_video(self, file) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload video to GCS bucket with security checks.
        
        Args:
            file: StreamLit UploadedFile object
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (success, url, error_message)
        """
        try:
            # Validate file
            is_valid, error_message = SecurityUtils.validate_file(file)
            if not is_valid:
                return False, None, error_message

            # Sanitize filename and create unique name
            safe_filename = SecurityUtils.sanitize_filename(file.name)
            
            # Check if a video with the same name (ignoring timestamp) exists
            existing_videos = self.list_videos()
            for video in existing_videos:
                # Extract original filename without timestamp
                if '_' in video['name']:
                    _, existing_name = video['name'].split('_', 1)
                    if existing_name.lower() == safe_filename.lower():
                        self.logger.info(f"Video {safe_filename} already exists")
                        return False, None, f"Video {safe_filename} already exists. Please rename the file or upload a different video."

            # Create timestamp and blob name after check
            timestamp = int(time.time())
            blob_name = f"videos/{timestamp}_{safe_filename}"

            # Create a temporary file
            temp_file_path = f"/tmp/{file.name}"
            with open(temp_file_path, "wb") as f:
                f.write(file.getbuffer())
                
            # Create blob and upload with metadata
            blob = self.bucket.blob(blob_name)
            blob.metadata = {
                'uploaded_at': str(timestamp),
                'original_filename': safe_filename,
                'content_type': file.type
            }
            
            # Upload using upload_from_filename
            blob.upload_from_filename(temp_file_path, content_type=file.type)
            blob.patch()  # Update metadata
            
            # Clean up temporary file
            os.remove(temp_file_path)
            
            # Generate public URL
            url = self.get_public_url(blob_name)
            
            self.logger.info(f"Successfully uploaded video: {blob_name}")
            return True, url, None

        except Exception as e:
            error_msg = f"Unexpected error during upload: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def list_videos(self) -> List[Dict[str, Any]]:
        """List all videos in storage."""
        try:
            videos = []
            blobs = self.bucket.list_blobs(prefix="videos/")
            
            for blob in blobs:
                if blob.name == "videos/":  # Skip the directory itself
                    continue
                    
                videos.append({
                    'name': blob.name.replace('videos/', ''),
                    'size': blob.size,
                    'uploaded_at': blob.time_created
                })
                
            return videos
        except Exception as e:
            self.logger.error(f"Error listing videos: {str(e)}")
            return []

    def delete_video(self, video_name: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a video from the bucket.
        
        Args:
            video_name: Name of the video to delete
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            # List all videos in the bucket
            blobs = self.bucket.list_blobs(prefix="videos/")
            
            # Find the blob that matches the full name (including timestamp)
            for blob in blobs:
                if Path(blob.name).name == video_name:  # Compare with full filename including timestamp
                    # Delete the blob
                    blob.delete()
                    self.logger.info(f"Successfully deleted video: {blob.name}")
                    return True, None
            
            return False, f"Video {video_name} not found"
            
        except Exception as e:
            error_msg = f"Error deleting video {video_name}: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def get_video_metadata(self, video_name: str) -> Optional[dict]:
        """
        Get metadata for a specific video.
        
        Args:
            video_name: Name of the video
            
        Returns:
            Optional[dict]: Video metadata or None if not found
        """
        try:
            blob = self.bucket.get_blob(f"videos/{video_name}")
            if not blob:
                return None
                
            return {
                'name': Path(blob.name).name,
                'size': f"{blob.size / (1024*1024):.2f} MB",
                'uploaded_at': blob.metadata.get('uploaded_at') if blob.metadata else 'Unknown',
                'content_type': blob.content_type,
                'url': self.get_public_url(blob.name)
            }
        except Exception as e:
            self.logger.error(f"Error getting video metadata: {str(e)}")
            return None

    def get_video_url(self, video_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Get the URL for a video in storage.
        
        Args:
            video_name: Name of the video
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (success, url, error_message)
        """
        try:
            blob = self.bucket.blob(f"videos/{video_name}")
            if not blob.exists():
                return False, None, "Video not found in storage"
            
            # Use the public URL instead of signed URL
            url = self.get_public_url(f"videos/{video_name}")
            return True, url, None
            
        except Exception as e:
            error_msg = f"Error getting video URL: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg