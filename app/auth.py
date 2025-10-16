"""
Authentication using Supabase Auth
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from app.database import get_supabase

# JWT token bearer
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase)
):
    """
    Validate Supabase JWT token and return current user.
    This is used as a dependency in protected routes.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        
        # Get user from Supabase using the token
        user_response = supabase.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise credentials_exception
        
        # Return user data
        return user_response.user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )