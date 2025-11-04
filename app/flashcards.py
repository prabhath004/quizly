from fastapi import APIRouter, Depends, HTTPException, status
from app.models import Flashcard, FlashcardCreate, FlashcardUpdate
from app.auth import get_current_user
from app.database import db
from typing import List
import logging

logger = logging.getLogger(__name__)

# Router setup
flashcards_router = APIRouter()


@flashcards_router.get("/deck/{deck_id}", tags=["Flashcards"])
async def get_deck_flashcards(deck_id: str, current_user = Depends(get_current_user)):
    """Get all flashcards for a deck with deck info (for study pages)"""
    try:
        print(f"Fetching flashcards for deck: {deck_id}, user: {current_user.id}")
        
        # Verify deck belongs to user
        deck_result = db.service_client.table("decks").select("*").eq("id", deck_id).execute()
        if not deck_result.data:
            print(f"Deck not found: {deck_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        
        deck = deck_result.data[0]
        if deck["user_id"] != current_user.id:
            print(f"Deck doesn't belong to user")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        print(f"Deck found: {deck['title']}")
        
        # Get flashcards
        flashcards_result = db.service_client.table("flashcards").select("*").eq("deck_id", deck_id).execute()
        flashcards_data = flashcards_result.data if flashcards_result.data else []
        
        print(f"Found {len(flashcards_data)} flashcards")
        
        # Format flashcards for study pages (with MCQ/True-False support)
        flashcards = []
        for card_data in flashcards_data:
            flashcard = {
                "id": card_data["id"],
                "question": card_data["question"],
                "answer": card_data["answer"],
                "difficulty": card_data.get("difficulty", "medium"),
                "question_type": card_data.get("question_type", "free_response"),
                "tags": card_data.get("tags", []),
            }
            
            # Add MCQ/True-False specific fields
            if card_data.get("mcq_options"):
                flashcard["options"] = card_data["mcq_options"]
                flashcard["correctAnswer"] = card_data.get("correct_option_index", 0)
                flashcard["correct_option_index"] = card_data.get("correct_option_index", 0)
            
            flashcards.append(flashcard)
        
        return {"flashcards": flashcards, "deck": deck}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get flashcards error: {e}")
        logger.error(f"Get flashcards error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve flashcards"
        )


@flashcards_router.post("", response_model=Flashcard, tags=["Flashcards"])
async def create_flashcard(flashcard_data: FlashcardCreate, current_user = Depends(get_current_user)):
    """Create a new flashcard"""
    try:
        print(f"Creating flashcard for deck: {flashcard_data.deck_id}")
        
        # Verify deck belongs to user
        deck_result = db.service_client.table("decks").select("*").eq("id", flashcard_data.deck_id).execute()
        if not deck_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        
        deck = deck_result.data[0]
        if deck["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Create flashcard
        flashcard_dict = {
            "deck_id": flashcard_data.deck_id,
            "question": flashcard_data.question,
            "answer": flashcard_data.answer,
            "difficulty": flashcard_data.difficulty.value,
            "question_type": flashcard_data.question_type.value,
            "tags": flashcard_data.tags,
        }
        
        if flashcard_data.mcq_options:
            flashcard_dict["mcq_options"] = flashcard_data.mcq_options
            flashcard_dict["correct_option_index"] = flashcard_data.correct_option_index
        
        result = db.service_client.table("flashcards").insert(flashcard_dict).execute()
        flashcard = result.data[0] if result.data else None
        
        if not flashcard:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create flashcard"
            )
        
        print(f"Flashcard created: {flashcard['id']}")
        
        return flashcard
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create flashcard error: {e}")
        logger.error(f"Create flashcard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create flashcard"
        )


@flashcards_router.put("/{flashcard_id}", tags=["Flashcards"])
async def update_flashcard(
    flashcard_id: str,
    flashcard_update: FlashcardUpdate,
    current_user = Depends(get_current_user)
):
    """Update a flashcard"""
    try:
        print(f"Updating flashcard: {flashcard_id}")
        
        # Get flashcard and verify access
        flashcard_result = db.service_client.table("flashcards").select("*").eq("id", flashcard_id).execute()
        if not flashcard_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flashcard not found"
            )
        
        flashcard = flashcard_result.data[0]
        
        # Verify deck belongs to user
        deck_result = db.service_client.table("decks").select("*").eq("id", flashcard["deck_id"]).execute()
        if not deck_result.data or deck_result.data[0]["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Prepare update data
        update_data = {}
        if flashcard_update.question is not None:
            update_data["question"] = flashcard_update.question
        if flashcard_update.answer is not None:
            update_data["answer"] = flashcard_update.answer
        if flashcard_update.difficulty is not None:
            update_data["difficulty"] = flashcard_update.difficulty.value
        if flashcard_update.question_type is not None:
            update_data["question_type"] = flashcard_update.question_type.value
        if flashcard_update.mcq_options is not None:
            update_data["mcq_options"] = flashcard_update.mcq_options
            if flashcard_update.correct_option_index is not None:
                update_data["correct_option_index"] = flashcard_update.correct_option_index
        if flashcard_update.tags is not None:
            update_data["tags"] = flashcard_update.tags
        
        if not update_data:
            # No changes to apply
            return flashcard
        
        # Update flashcard
        result = db.service_client.table("flashcards").update(update_data).eq("id", flashcard_id).execute()
        updated_flashcard = result.data[0] if result.data else None
        
        if not updated_flashcard:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update flashcard"
            )
        
        print(f"Flashcard updated: {flashcard_id}")
        return updated_flashcard
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update flashcard error: {e}")
        logger.error(f"Update flashcard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update flashcard"
        )


@flashcards_router.delete("/{flashcard_id}", tags=["Flashcards"])
async def delete_flashcard(flashcard_id: str, current_user = Depends(get_current_user)):
    """Delete a flashcard"""
    try:
        print(f"Deleting flashcard: {flashcard_id}")
        
        # Get flashcard and verify access
        flashcard_result = db.service_client.table("flashcards").select("*").eq("id", flashcard_id).execute()
        if not flashcard_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flashcard not found"
            )
        
        flashcard = flashcard_result.data[0]
        
        # Verify deck belongs to user
        deck_result = db.service_client.table("decks").select("*").eq("id", flashcard["deck_id"]).execute()
        if not deck_result.data or deck_result.data[0]["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete flashcard
        db.service_client.table("flashcards").delete().eq("id", flashcard_id).execute()
        
        print(f"Flashcard deleted: {flashcard_id}")
        
        return {"message": "Flashcard deleted successfully", "flashcard_id": flashcard_id}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete flashcard error: {e}")
        logger.error(f"Delete flashcard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete flashcard"
        )
