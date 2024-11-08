from typing import Optional, Tuple
import os
import magic
from pathlib import Path
from config.settings import Settings

class SecurityUtils:
    """Utility class for security-related operations."""
    
    @staticmethod
    def validate_file(file) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file for security concerns.
        
        Args:
            file: The uploaded file object
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Check file size
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)
            
            if size > Settings.MAX_FILE_SIZE:
                return False, f"File size exceeds maximum limit of {Settings.MAX_FILE_SIZE // (1024*1024)}MB"

            # Check file extension
            file_ext = Path(file.name).suffix[1:].lower()
            if file_ext not in Settings.ALLOWED_EXTENSIONS:
                return False, f"File type not allowed. Allowed types: {', '.join(Settings.ALLOWED_EXTENSIONS)}"

            # Check actual file content type
            file_content = file.read(2048)
            file.seek(0)
            mime = magic.Magic(mime=True)
            content_type = mime.from_buffer(file_content)
            
            if not any(ext in content_type for ext in ['video']):
                return False, "File content type not allowed"

            return True, None

        except Exception as e:
            return False, f"Error validating file: {str(e)}"

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal attacks.
        
        Args:
            filename: Original filename
            
        Returns:
            str: Sanitized filename
        """
        # Remove path components and return only filename
        return Path(filename).name