"""
Data validation utilities.
Provides common validation functions for user input and data.
"""

import re
from typing import Tuple
from datetime import datetime


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class Validator:
    """Validation utilities for common data types."""
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """
        Validate email address format.
        
        Args:
            email: Email address to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email is required"
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            return False, "Invalid email format"
        
        return True, ""
    
    @staticmethod
    def validate_password(password: str, min_length: int = 8) -> Tuple[bool, str]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            min_length: Minimum password length
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"
        
        if len(password) < min_length:
            return False, f"Password must be at least {min_length} characters"
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        # Check for at least one digit
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        return True, ""
    
    @staticmethod
    def validate_name(name: str, min_length: int = 2) -> Tuple[bool, str]:
        """
        Validate user name.
        
        Args:
            name: Name to validate
            min_length: Minimum name length
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name:
            return False, "Name is required"
        
        name = name.strip()
        
        if len(name) < min_length:
            return False, f"Name must be at least {min_length} characters"
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-']+$", name):
            return False, "Name contains invalid characters"
        
        return True, ""
    
    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: set) -> Tuple[bool, str]:
        """
        Validate file extension.
        
        Args:
            filename: Filename to validate
            allowed_extensions: Set of allowed extensions (without dots)
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not filename:
            return False, "Filename is required"
        
        # Get file extension
        if '.' not in filename:
            return False, "File must have an extension"
        
        extension = filename.split('.')[-1].lower()
        
        if extension not in allowed_extensions:
            return False, f"File type .{extension} not allowed"
        
        return True, ""
    
    @staticmethod
    def validate_file_size(file_size: int, max_size: int) -> Tuple[bool, str]:
        """
        Validate file size.
        
        Args:
            file_size: File size in bytes
            max_size: Maximum allowed size in bytes
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if file_size <= 0:
            return False, "Invalid file size"
        
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            return False, f"File size exceeds maximum of {max_size_mb:.1f} MB"
        
        return True, ""
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
        
        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        
        return f"{size_bytes:.2f} PB"
