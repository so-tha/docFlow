"""
File handling utilities.
Provides functions for file operations, hashing, and validation.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from src.core.config import config_obj
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FileHandler:
    """Utility class for file operations."""
    
    @staticmethod
    def ensure_upload_directory() -> bool:
        """
        Ensure the upload directory exists.
        
        Returns:
            True if directory exists or was created successfully
        """
        try:
            config_obj.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
            logger.info(f"Upload directory ensured: {config_obj.UPLOAD_FOLDER}")
            return True
        except Exception as e:
            logger.error(f"Failed to create upload directory: {str(e)}")
            return False
    
    @staticmethod
    def calculate_file_hash(file_path: str, algorithm: str = 'sha256') -> Optional[str]:
        """
        Calculate hash of a file.
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm (sha256, md5, etc.)
        
        Returns:
            Hash string or None if calculation failed
        """
        try:
            hash_obj = hashlib.new(algorithm)
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
        
        except Exception as e:
            logger.error(f"Failed to calculate file hash: {str(e)}")
            return None
    
    @staticmethod
    def get_file_size(file_path: str) -> Optional[int]:
        """
        Get file size in bytes.
        
        Args:
            file_path: Path to the file
        
        Returns:
            File size in bytes or None if failed
        """
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Failed to get file size: {str(e)}")
            return None
    
    @staticmethod
    def generate_unique_filename(original_filename: str) -> str:
        """
        Generate a unique filename to prevent collisions.
        
        Args:
            original_filename: Original filename
        
        Returns:
            Unique filename with timestamp prefix
        """
        from datetime import datetime
        
        # Get file extension
        if '.' in original_filename:
            name, extension = original_filename.rsplit('.', 1)
            extension = f".{extension}"
        else:
            name = original_filename
            extension = ""
        
        # Generate unique name with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
        unique_name = f"{timestamp}_{name}{extension}"
        
        return unique_name
    
    @staticmethod
    # def save_uploaded_file(source_path: str, original_filename: str) -> Tuple[bool, str]:
    #     """
    #     Save uploaded file to the upload directory.
        
    #     Args:
    #         source_path: Temporary source path
    #         original_filename: Original filename
        
    #     Returns:
    #         Tuple of (success, destination_path or error_message)
    #     """
    #     try:
    #         # Ensure upload directory exists
    #         if not FileHandler.ensure_upload_directory():
    #             return False, "Upload directory not accessible"
            
    #         # Generate unique filename
    #         unique_filename = FileHandler.generate_unique_filename(original_filename)
    #         destination_path = config_obj.UPLOAD_FOLDER / unique_filename
            
    #         # Copy file
    #         with open(source_path, 'rb') as source:
    #             with open(destination_path, 'wb') as dest:
    #                 dest.write(source.read())
            
    #         logger.info(f"File saved: {destination_path}")
    #         return True, str(destination_path)
        
    #     except Exception as e:
    #         logger.error(f"Failed to save file: {str(e)}")
    #         return False, str(e)
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        Delete a file.
        
        Args:
            file_path: Path to the file
        
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            return False
    
    @staticmethod
    def file_exists(file_path: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            file_path: Path to the file
        
        Returns:
            True if file exists, False otherwise
        """
        return os.path.exists(file_path) and os.path.isfile(file_path)
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size to human-readable format.
        
        Args:
            size_bytes: Size in bytes
        
        Returns:
            Formatted size string (e.g., "1.2 MB")
        """
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        
        for unit in units:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        
        return f"{size:.1f} PB"
