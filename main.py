"""
Quizly Backend - Main FastAPI Application
A smart AI-powered flashcard application with voice-based learning
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import modules (will be created)
from app.auth import get_current_user
from app.models import UserCreate, UserLogin, Token
from app.database import get_supabase

# from app.ingest import ingest_router
# from app.ai import ai_router
# from app.sessions import sessions_router
# from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting Quizly Backend...")
    # await init_db()  # Initialize database connection
    yield
    # Shutdown
    print("🛑 Shutting down Quizly Backend...")


# Create FastAPI application
app = FastAPI(
    title="Quizly Backend API",
    description="Smart AI-powered flashcard application with voice-based learning",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for deployment testing"""
    return {
        "status": "healthy",
        "message": "Quizly Backend is running!",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Quizly Backend API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0"
    }

# Authentication Endpoints using Supabase Auth
@app.post("/api/auth/register", response_model=Token, tags=["Authentication"])
async def register(user: UserCreate, supabase = Depends(get_supabase)):
    """Register a new user using Supabase Auth."""
    try:
        # Register user with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password,
            "options": {
                "data": {
                    "full_name": user.full_name
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )
        
        return {
            "access_token": auth_response.session.access_token,
            "token_type": "bearer",
            "refresh_token": auth_response.session.refresh_token,
            "user": {
                "id": auth_response.user.id,
                "email": auth_response.user.email
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )


@app.post("/api/auth/login", response_model=Token, tags=["Authentication"])
async def login(user: UserLogin, supabase = Depends(get_supabase)):
    """Login user using Supabase Auth."""
    try:
        # Login with Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        return {
            "access_token": auth_response.session.access_token,
            "token_type": "bearer",
            "refresh_token": auth_response.session.refresh_token,
            "user": {
                "id": auth_response.user.id,
                "email": auth_response.user.email
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        )


@app.get("/api/auth/me", tags=["Authentication"])
async def get_me(current_user = Depends(get_current_user)):
    """Get current user info (protected route example)."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "user_metadata": current_user.user_metadata
    }


@app.post("/api/auth/logout", tags=["Authentication"])
async def logout(supabase = Depends(get_supabase)):
    """Logout user."""
    try:
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Logout failed: {str(e)}"
        )
# Include routers (will be uncommented as modules are created)
# app.include_router(ingest_router, prefix="/api/ingest", tags=["File Ingestion"])
# app.include_router(ai_router, prefix="/api/ai", tags=["AI Services"])
# app.include_router(sessions_router, prefix="/api/sessions", tags=["Study Sessions"])


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "True").lower() == "true"
    )
