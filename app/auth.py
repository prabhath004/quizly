"""
Quizly Backend - Authentication Module
Handles JWT validation with Supabase and user authentication
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.config import get_settings
from app.models import User, UserCreate, UserUpdate, Token, TokenData
from app.database import db
from supabase import create_client
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Router setup
auth_router = APIRouter()
security = HTTPBearer()

# Direct Supabase connection
settings = get_settings()
supabase = create_client(settings.supabase_url, settings.supabase_anon_key)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        settings = get_settings()
        token = credentials.credentials
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    # Get user from Supabase Auth using the user_id from JWT
    try:
        # Use service client for admin operations
        service_client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        response = service_client.auth.admin.get_user_by_id(user_id)
        if not response.user:
            raise credentials_exception
        
        # Create User object from Supabase user data
        user_data = {
            "id": response.user.id,
            "email": response.user.email,
            "full_name": response.user.user_metadata.get("full_name", ""),
            "created_at": response.user.created_at,
            "updated_at": response.user.updated_at
        }
        
        return User(**user_data)
        
    except Exception as e:
        logger.error(f"User validation error: {e}")
        raise credentials_exception


async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[User]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


@auth_router.post("/register", response_model=Token, tags=["Authentication"])
async def register(user_data: UserCreate):
    """Register a new user and return JWT token"""
    try:
        # Register with Supabase Auth
        result = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "full_name": user_data.full_name
                }
            }
        })
        
        if not result.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )
        
        # Create JWT token
        settings = get_settings()
        access_token = jwt.encode(
            {"sub": result.user.id},
            settings.secret_key,
            algorithm=settings.algorithm
        )
        
        return Token(access_token=access_token)
    
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) if "User already registered" in str(e) else "Registration failed"
        )


@auth_router.post("/login", response_model=Token, tags=["Authentication"])
async def login(email: str, password: str):
    """Login user and return JWT token"""
    try:
        # Authenticate with Supabase
        response = db.client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Create JWT token
        settings = get_settings()
        access_token = jwt.encode(
            {"sub": response.user.id},
            settings.secret_key,
            algorithm=settings.algorithm
        )
        
        return Token(access_token=access_token)
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@auth_router.get("/me", response_model=User, tags=["Authentication"])
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@auth_router.put("/me", response_model=User, tags=["Authentication"])
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update current user information"""
    try:
        # Update user in Supabase
        updated_user = await db.update_user(current_user.id, user_update.dict(exclude_unset=True))
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Update failed"
            )
        
        return User(**updated_user)
    
    except Exception as e:
        logger.error(f"User update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Update failed"
        )


@auth_router.post("/logout", tags=["Authentication"])
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user"""
    try:
        # Sign out from Supabase
        db.client.auth.sign_out()
        return {"message": "Successfully logged out"}
    
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logout failed"
        )
