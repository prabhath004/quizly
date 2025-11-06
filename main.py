from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import modules
from app.auth import auth_router
from app.ingest import ingest_router
from app.ai import ai_router
from app.decks import decks_router
from app.flashcards import flashcards_router
from app.folders import folders_router
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting Quizly Backend...")
    await init_db()  # Initialize database connection
    yield
    # Shutdown
    print("Shutting down Quizly Backend...")


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
    allow_origins=["http://localhost:8080", "http://localhost:5173"],  # Configure appropriately for production
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

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(ingest_router, prefix="/api/ingest", tags=["File Ingestion"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI Services"])
app.include_router(decks_router, prefix="/api/decks", tags=["Decks"])
app.include_router(flashcards_router, prefix="/api/flashcards", tags=["Flashcards"])
app.include_router(folders_router, prefix="/api/folders", tags=["Folders"])


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "True").lower() == "true"
    )
