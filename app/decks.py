"""
Quizly Backend - Decks Module
Handles deck CRUD operations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.models import Deck, DeckCreate, DeckUpdate
from app.auth import get_current_user
from app.database import db
from typing import List
import logging

logger = logging.getLogger(__name__)

# Router setup
decks_router = APIRouter()


@decks_router.get("/my-decks", tags=["Decks"])
async def get_my_decks(current_user = Depends(get_current_user)):
    """Get all decks for current user"""
    try:
        print(f"🔍 Fetching decks for user: {current_user.id}")
        
        # Use service client to bypass RLS
        decks_result = db.service_client.table("decks").select("*").eq("user_id", current_user.id).execute()
        decks = decks_result.data if decks_result.data else []
        
        print(f"✅ Found {len(decks)} decks")
        
        # Add flashcard count to each deck
        for deck in decks:
            flashcards_result = db.service_client.table("flashcards").select("*").eq("deck_id", deck["id"]).execute()
            flashcards = flashcards_result.data if flashcards_result.data else []
            deck["flashcard_count"] = len(flashcards)
            print(f"  📚 Deck '{deck['title']}': {len(flashcards)} flashcards")
        
        return decks
    
    except Exception as e:
        print(f"❌ Get decks error: {e}")
        logger.error(f"Get decks error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve decks"
        )


@decks_router.get("/{deck_id}", tags=["Decks"])
async def get_deck(deck_id: str, current_user = Depends(get_current_user)):
    """Get specific deck"""
    try:
        deck = await db.get_deck(deck_id)
        
        if not deck or deck["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        
        # Add flashcard count
        flashcards = await db.get_deck_flashcards(deck["id"])
        deck["flashcard_count"] = len(flashcards)
        
        return deck
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get deck error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve deck"
        )


@decks_router.delete("/{deck_id}", tags=["Decks"])
async def delete_deck(deck_id: str, current_user = Depends(get_current_user)):
    """Delete a deck and all its flashcards"""
    try:
        print(f"🗑️ Deleting deck: {deck_id} for user: {current_user.id}")
        
        # Use service client to bypass RLS
        deck_result = db.service_client.table("decks").select("*").eq("id", deck_id).execute()
        deck = deck_result.data[0] if deck_result.data else None
        
        if not deck:
            print(f"❌ Deck not found: {deck_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        
        if deck["user_id"] != current_user.id:
            print(f"❌ Deck doesn't belong to user")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete all flashcards first using service client
        print(f"🗑️ Deleting flashcards...")
        db.service_client.table("flashcards").delete().eq("deck_id", deck_id).execute()
        
        # Delete deck using service client
        print(f"🗑️ Deleting deck...")
        db.service_client.table("decks").delete().eq("id", deck_id).execute()
        
        print(f"✅ Deck deleted successfully")
        
        return {"message": "Deck deleted successfully", "deck_id": deck_id}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Delete deck error: {e}")
        logger.error(f"Delete deck error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete deck"
        )

