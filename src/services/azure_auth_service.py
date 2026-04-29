"""
Azure AD Authentication Service using MSAL.
Handles user authentication via Microsoft Entra ID.
"""

import json
import msal
from typing import Optional, Dict, Any
from src.core.config import config_obj
from src.core.database import get_session
from src.core.models import User
from src.utils.logger import get_logger
from src.utils.constants import UserRole

logger = get_logger(__name__)


class AzureAuthService:
    """Service for Azure AD authentication using MSAL."""
    
    def __init__(self):
        """Initialize MSAL public client application."""
        # If authentication is disabled, raise early
        if not config_obj.AUTHENTICATION_ENABLED:
            raise ValueError("Authentication is disabled (AUTH_ENABLED=false in .env)")
        
        if not config_obj.AZURE_CLIENT_ID:
            raise ValueError("AZURE_CLIENT_ID not configured in environment")
        
        self.app = msal.PublicClientApplication(
            client_id=config_obj.AZURE_CLIENT_ID,
            authority=config_obj.AZURE_AUTHORITY,
            token_cache=msal.SerializableTokenCache()
        )
        self.scopes = config_obj.AZURE_SCOPES
    
    def acquire_token_interactive(self) -> Optional[Dict[str, Any]]:
        """
        Acquire access token via interactive login (browser popup).
        
        Returns:
            Dictionary with 'access_token' and user info, or None if failed.
        """
        try:
            result = self.app.acquire_token_interactive(
                scopes=self.scopes,
                login_hint=None
            )
            
            if 'access_token' in result:
                logger.info("User authenticated successfully via Azure AD")
                return result
            else:
                error = result.get('error_description', result.get('error', 'Unknown error'))
                logger.error(f"Azure AD authentication failed: {error}")
                return None
                
        except Exception as e:
            logger.error(f"Error acquiring token: {str(e)}")
            return None
    
    def get_user_from_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Extract user information from access token.
        
        Args:
            access_token: JWT access token from Azure AD.
            
        Returns:
            Dictionary with user info (id, email, displayName, givenName), or None.
        """
        try:
            import jwt
            
            # Decode token without verification (token is trusted from Azure)
            decoded = jwt.decode(access_token, options={"verify_signature": False})
            
            user_info = {
                'id': decoded.get('oid'),  # Object ID in Azure
                'email': decoded.get('upn') or decoded.get('email'),
                'display_name': decoded.get('name'),
                'given_name': decoded.get('given_name')
            }
            
            return user_info
            
        except Exception as e:
            logger.error(f"Error extracting user from token: {str(e)}")
            return None
    
    def authenticate_user(self, access_token: str) -> Optional[User]:
        """
        Authenticate user via Azure AD token and sync with local database.
        Creates or updates user in database if not exists.
        
        Args:
            access_token: JWT access token from Azure AD.
            
        Returns:
            User object from database, or None if failed.
        """
        try:
            # Get user info from token
            user_info = self.get_user_from_token(access_token)
            if not user_info:
                return None
            
            email = user_info.get('email')
            if not email:
                logger.error("No email found in Azure AD token")
                return None
            
            session = get_session()
            
            # Check if user exists in database
            user = session.query(User).filter_by(email=email).first()
            
            if user:
                # Update existing user info
                user.is_active = True
                logger.info(f"User {email} authenticated (existing)")
            else:
                # Create new user from Azure AD
                # Default role is 'user' - admin can change in Azure/database
                user = User(
                    email=email,
                    name=user_info.get('display_name', user_info.get('given_name', email)),
                    role=UserRole.USER,
                    is_active=True
                )
                session.add(user)
                logger.info(f"New user {email} created from Azure AD")
            
            # Store Azure AD object ID for future reference
            user.azure_id = user_info.get('id')
            
            session.commit()
            logger.info(f"User {email} successfully authenticated via Azure AD")
            
            return user
            
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            return None
    
    def logout(self) -> bool:
        """
        Clear local token cache (Azure AD sign-out).
        
        Returns:
            True if successful.
        """
        try:
            # Clear token cache
            self.app.token_cache.clear()
            logger.info("User logged out - token cache cleared")
            return True
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            return False
