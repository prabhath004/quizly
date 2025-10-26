"""
Quizly Backend - Study Sessions Module
Handles study sessions and simple progress tracking
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.models import (
    Session, SessionCreate, SessionUpdate,
    Deck, Flashcard
)
from app.auth import get_current_user
from app.database import db
from app.config import get_settings
from datetime import datetime
import random
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Router setup
sessions_router = APIRouter()


@sessions_router.post("/create", response_model=Session, tags=["Study Sessions"])
async def create_study_session(
    session_data: SessionCreate,
    current_user = Depends(get_current_user)
):
    """Create a new study session"""
    try:
        # Verify deck exists and belongs to user
        deck = await db.get_deck(session_data.deck_id)
        if not deck or deck["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        
        # Create session
        session_dict = {
            "user_id": current_user.id,
            "deck_id": session_data.deck_id,
            "started_at": datetime.utcnow().isoformat(),
            "total_cards": 0,
            "correct_answers": 0,
            "incorrect_answers": 0
        }
        
        session = await db.create_session(session_dict)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create session"
            )
        
        return Session(**session)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session creation failed"
        )


@sessions_router.get("/my-sessions", response_model=List[Session], tags=["Study Sessions"])
async def get_my_sessions(current_user = Depends(get_current_user)):
    """Get all sessions for current user"""
    try:
        sessions = await db.get_user_sessions(current_user.id)
        return [Session(**session) for session in sessions]
    
    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )


@sessions_router.get("/deck-cards/{deck_id}", response_model=List[Flashcard], tags=["Study Sessions"])
async def get_deck_cards(
    deck_id: str,
    limit: int = 20,
    current_user = Depends(get_current_user)
):
    """Get flashcards from a deck for study"""
    try:
        # Verify deck belongs to user
        deck = await db.get_deck(deck_id)
        if not deck or deck["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        
        # Get flashcards from deck
        flashcards_data = await db.get_deck_flashcards(deck_id)
        
        # Convert to Flashcard models
        flashcards = []
        for card_data in flashcards_data[:limit]:
            flashcards.append(Flashcard(**card_data))
        
        return flashcards
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get deck cards error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve deck cards"
        )


@sessions_router.post("/submit-answer", tags=["Study Sessions"])
async def submit_answer(
    session_id: str,
    flashcard_id: str,
    user_answer: str,
    is_correct: bool,
    current_user = Depends(get_current_user)
):
    """Submit an answer for a flashcard in a session"""
    try:
        # Verify session belongs to user
        session = await db.get_session(session_id)
        if not session or session["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Update session statistics
        session_update = {}
        if is_correct:
            session_update["correct_answers"] = session["correct_answers"] + 1
        else:
            session_update["incorrect_answers"] = session["incorrect_answers"] + 1
        
        session_update["total_cards"] = session["total_cards"] + 1
        
        await db.update_session(session_id, session_update)
        
        return {
            "message": "Answer submitted successfully",
            "is_correct": is_correct,
            "session_stats": {
                "total_cards": session_update["total_cards"],
                "correct_answers": session_update["correct_answers"],
                "incorrect_answers": session_update["incorrect_answers"]
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Submit answer error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit answer"
        )


@sessions_router.put("/end-session/{session_id}", response_model=Session, tags=["Study Sessions"])
async def end_study_session(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """End a study session"""
    try:
        # Verify session belongs to user
        session = await db.get_session(session_id)
        if not session or session["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Update session with end time
        session_update = {
            "ended_at": datetime.utcnow().isoformat()
        }
        
        updated_session = await db.update_session(session_id, session_update)
        if not updated_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to end session"
            )
        
        return Session(**updated_session)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"End session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end session"
        )


@sessions_router.get("/session-stats/{session_id}", tags=["Study Sessions"])
async def get_session_stats(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Get statistics for a study session"""
    try:
        # Verify session belongs to user
        session = await db.get_session(session_id)
        if not session or session["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Calculate statistics
        total_reviews = session["correct_answers"] + session["incorrect_answers"]
        accuracy = (session["correct_answers"] / total_reviews * 100) if total_reviews > 0 else 0
        
        return {
            "session_id": session_id,
            "total_cards": session["total_cards"],
            "correct_answers": session["correct_answers"],
            "incorrect_answers": session["incorrect_answers"],
            "accuracy_percentage": round(accuracy, 2),
            "started_at": session["started_at"],
            "ended_at": session["ended_at"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session statistics"
        )
