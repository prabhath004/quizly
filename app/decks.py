from fastapi import APIRouter, Depends, HTTPException, status
from app.models import Deck, DeckCreate, DeckUpdate
from app.auth import get_current_user
from app.database import db
from typing import List
import logging

logger = logging.getLogger(__name__)

# Router setup
decks_router = APIRouter()


@decks_router.post("", response_model=Deck, tags=["Decks"])
async def create_deck(deck_data: DeckCreate, current_user = Depends(get_current_user)):
    """Create a new deck"""
    try:
        print(f"Creating deck: {deck_data.title} for user: {current_user.id}")
        
        # Create deck using service client
        deck_dict = {
            "title": deck_data.title,
            "description": deck_data.description,
            "user_id": current_user.id
        }
        
        # Add folder_id if provided
        if deck_data.folder_id:
            deck_dict["folder_id"] = deck_data.folder_id
        
        result = db.service_client.table("decks").insert(deck_dict).execute()
        
        deck = result.data[0] if result.data else None
        if not deck:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create deck"
            )
        
        deck["flashcard_count"] = 0
        print(f"Deck created: {deck['id']}")
        
        return deck
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create deck error: {e}")
        logger.error(f"Create deck error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create deck"
        )


@decks_router.get("/my-decks", tags=["Decks"])
async def get_my_decks(current_user = Depends(get_current_user)):
    """Get all decks for current user"""
    try:
        print(f"Fetching decks for user: {current_user.id}")
        
        # Use service client to bypass RLS
        decks_result = db.service_client.table("decks").select("*").eq("user_id", current_user.id).execute()
        decks = decks_result.data if decks_result.data else []
        
        print(f"Found {len(decks)} decks")
        
        # Add flashcard count to each deck
        for deck in decks:
            flashcards_result = db.service_client.table("flashcards").select("*").eq("deck_id", deck["id"]).execute()
            flashcards = flashcards_result.data if flashcards_result.data else []
            deck["flashcard_count"] = len(flashcards)
            print(f"  Deck '{deck['title']}': {len(flashcards)} flashcards")
        
        return decks
    
    except Exception as e:
        print(f"Get decks error: {e}")
        logger.error(f"Get decks error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve decks"
        )


@decks_router.get("/{deck_id}", tags=["Decks"])
async def get_deck(deck_id: str, current_user = Depends(get_current_user)):
    """Get specific deck"""
    try:
        print(f"Fetching deck: {deck_id} for user: {current_user.id}")
        
        # Use service client to bypass RLS
        deck_result = db.service_client.table("decks").select("*").eq("id", deck_id).execute()
        deck = deck_result.data[0] if deck_result.data else None
        
        if not deck:
            print(f"Deck not found: {deck_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        
        if deck["user_id"] != current_user.id:
            print("Deck doesn't belong to user")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Add flashcard count
        flashcards_result = db.service_client.table("flashcards").select("*").eq("deck_id", deck_id).execute()
        flashcards = flashcards_result.data if flashcards_result.data else []
        deck["flashcard_count"] = len(flashcards)
        
        print(f"Deck found: {deck['title']} with {len(flashcards)} flashcards")
        
        return deck
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get deck error: {e}")
        logger.error(f"Get deck error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve deck"
        )


@decks_router.put("/{deck_id}", tags=["Decks"])
async def update_deck(deck_id: str, deck_update: DeckUpdate, current_user = Depends(get_current_user)):
    """Update a deck"""
    try:
        print(f"Updating deck: {deck_id}")
        
        # Check if deck exists and belongs to user
        deck_result = db.service_client.table("decks").select("*").eq("id", deck_id).execute()
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
        
        # Prepare update data
        update_data = {}
        if deck_update.title is not None:
            update_data["title"] = deck_update.title
        if deck_update.description is not None:
            update_data["description"] = deck_update.description
        
        # Handle folder_id - check if it was explicitly provided in the request
        # Use model_dump with exclude_unset to check if folder_id was actually sent
        update_dict = deck_update.model_dump(exclude_unset=True)
        if "folder_id" in update_dict:
            folder_id_value = update_dict["folder_id"]
            # If folder_id is being set to a folder (not None), validate it belongs to the user
            if folder_id_value:
                folder_result = db.service_client.table("folders").select("*").eq("id", folder_id_value).execute()
                if not folder_result.data:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Folder not found"
                    )
                if folder_result.data[0]["user_id"] != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to folder"
                    )
            # Allow setting to None (move to root) - explicitly set None in update_data
            # Supabase will handle None values correctly
            update_data["folder_id"] = folder_id_value
        
        if not update_data:
            # No changes to apply
            deck_result = db.service_client.table("decks").select("*").eq("id", deck_id).execute()
            return deck_result.data[0]
        
        # Update deck
        result = db.service_client.table("decks").update(update_data).eq("id", deck_id).execute()
        updated_deck = result.data[0] if result.data else None
        
        if not updated_deck:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update deck"
            )
        
        # Add flashcard count
        flashcards_result = db.service_client.table("flashcards").select("*").eq("deck_id", deck_id).execute()
        flashcards = flashcards_result.data if flashcards_result.data else []
        updated_deck["flashcard_count"] = len(flashcards)
        
        print(f"Deck updated: {deck_id}")
        return updated_deck
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update deck error: {e}")
        logger.error(f"Update deck error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update deck"
        )


@decks_router.delete("/{deck_id}", tags=["Decks"])
async def delete_deck(deck_id: str, current_user = Depends(get_current_user)):
    """Delete a deck and all its flashcards"""
    try:
        print(f"Deleting deck: {deck_id} for user: {current_user.id}")
        
        # Use service client to bypass RLS
        deck_result = db.service_client.table("decks").select("*").eq("id", deck_id).execute()
        deck = deck_result.data[0] if deck_result.data else None
        
        if not deck:
            print(f"Deck not found: {deck_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        
        if deck["user_id"] != current_user.id:
            print("Deck doesn't belong to user")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete all flashcards first using service client
        print("Deleting flashcards...")
        db.service_client.table("flashcards").delete().eq("deck_id", deck_id).execute()
        
        # Delete deck using service client
        print("Deleting deck...")
        db.service_client.table("decks").delete().eq("id", deck_id).execute()
        
        print("Deck deleted successfully")
        
        return {"message": "Deck deleted successfully", "deck_id": deck_id}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete deck error: {e}")
        logger.error(f"Delete deck error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete deck"
        )
