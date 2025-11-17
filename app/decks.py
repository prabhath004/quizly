from fastapi import APIRouter, Depends, HTTPException, status
from app.models import Deck, DeckCreate, DeckUpdate, DeckReorderRequest
from app.auth import get_current_user
from app.database import db
from app.config import get_settings
from typing import List
import logging
import openai
import json
import io
import time
import tempfile
import os
import random
from pydub import AudioSegment
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Router setup
decks_router = APIRouter()

# Initialize OpenAI client
def get_openai_client():
    """Get OpenAI client with API key"""
    settings = get_settings()
    return openai.OpenAI(api_key=settings.openai_api_key)


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
            # Set order_index to the last position in the folder (only if column exists)
            try:
                folder_decks_result = db.service_client.table("decks").select("order_index").eq("folder_id", deck_data.folder_id).eq("user_id", current_user.id).execute()
                folder_decks = folder_decks_result.data if folder_decks_result.data else []
                max_order = max([d.get("order_index") or -1 for d in folder_decks], default=-1)
                deck_dict["order_index"] = max_order + 1
            except Exception as e:
                error_str = str(e)
                if "order_index" in error_str or "42703" in error_str:
                    logger.warning("order_index column not found - creating deck without order_index. Please run migration.")
                # Continue without order_index - deck creation should still work
        # Note: We don't set order_index for root decks - it's not needed
        
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
    """Get all decks for current user, ordered by order_index within folders"""
    try:
        print(f"Fetching decks for user: {current_user.id}")
        
        # Use service client to bypass RLS
        decks_result = db.service_client.table("decks").select("*").eq("user_id", current_user.id).execute()
        decks = decks_result.data if decks_result.data else []
        
        print(f"Found {len(decks)} decks")
        
        # Add flashcard count to each deck and ensure order_index is set
        for deck in decks:
            flashcards_result = db.service_client.table("flashcards").select("*").eq("deck_id", deck["id"]).execute()
            flashcards = flashcards_result.data if flashcards_result.data else []
            deck["flashcard_count"] = len(flashcards)
            
            # If deck is in a folder but has no order_index, assign one
            # Only do this if the column exists (graceful degradation)
            if deck.get("folder_id"):
                try:
                    # Try to check and set order_index
                    if deck.get("order_index") is None:
                        # Get max order_index in this folder and set to next
                        folder_decks_result = db.service_client.table("decks").select("order_index").eq("folder_id", deck["folder_id"]).eq("user_id", current_user.id).execute()
                        folder_decks = folder_decks_result.data if folder_decks_result.data else []
                        max_order = max([d.get("order_index") or -1 for d in folder_decks], default=-1)
                        new_order = max_order + 1
                        db.service_client.table("decks").update({"order_index": new_order}).eq("id", deck["id"]).execute()
                        deck["order_index"] = new_order
                        print(f"  Assigned order_index {new_order} to deck '{deck['title']}' in folder")
                except Exception as e:
                    # Column might not exist - that's okay, continue without it
                    if "order_index" in str(e) or "42703" in str(e):
                        logger.warning(f"order_index column not found - please run migration: {e}")
                    # Continue processing other decks
            
            print(f"  Deck '{deck['title']}': {len(flashcards)} flashcards")
        
        # Sort decks: folders first (by order_index), then root decks (by created_at)
        def sort_key(deck):
            try:
                if deck.get("folder_id"):
                    # Decks in folders: sort by folder_id first, then order_index
                    folder_id = str(deck.get("folder_id") or "")
                    order_index = deck.get("order_index")
                    # Handle None order_index - use a large number so they sort last
                    if order_index is None:
                        order_index = 999999
                    # Ensure order_index is an integer
                    try:
                        order_index = int(order_index)
                    except (ValueError, TypeError):
                        order_index = 999999
                    return (0, folder_id, order_index)  # 0 means it's in a folder
                else:
                    # Root decks: sort by created_at (newest first, None last)
                    created_at = deck.get("created_at")
                    # Convert None to empty string, ensure it's a string
                    if created_at is None:
                        created_at = ""
                    created_at = str(created_at)
                    # For descending order (newest first), we'll reverse the sort after
                    # For now, use empty string for None so they sort last
                    return (1, created_at)  # 1 means it's a root deck
            except Exception as e:
                # Fallback: if anything goes wrong, put problematic decks at the end
                logger.warning(f"Error sorting deck {deck.get('id')}: {e}")
                return (2, "")
        
        # Sort: folders first (0), then root decks (1), then errors (2)
        # Within folders: by folder_id, then order_index
        # Root decks: by created_at (will reverse for newest first)
        decks.sort(key=sort_key)
        
        # For root decks, we want newest first, so we need to reverse their section
        # Separate folders and root decks
        folder_decks = [d for d in decks if d.get("folder_id")]
        root_decks = [d for d in decks if not d.get("folder_id")]
        
        # Sort root decks by created_at in descending order (newest first)
        root_decks.sort(key=lambda d: d.get("created_at") or "", reverse=True)
        
        # Combine: folders first, then root decks
        decks[:] = folder_decks + root_decks
        
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
        current_deck = deck_result.data[0]
        old_folder_id = current_deck.get("folder_id")
        
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
                
                # If moving to a different folder (or from root to folder), assign order_index (last position)
                # Only try to set order_index if the column exists (catch error gracefully)
                if old_folder_id != folder_id_value:
                    try:
                        # Get all decks in the target folder, EXCLUDING the current deck being moved
                        # This handles the case where we're moving within the same folder or from another folder
                        folder_decks_result = db.service_client.table("decks").select("id,order_index").eq("folder_id", folder_id_value).eq("user_id", current_user.id).execute()
                        folder_decks = folder_decks_result.data if folder_decks_result.data else []
                        # Exclude the current deck from the calculation (in case it's already in this folder)
                        folder_decks = [d for d in folder_decks if d.get("id") != deck_id]
                        max_order = max([d.get("order_index") or -1 for d in folder_decks], default=-1)
                        update_data["order_index"] = max_order + 1
                        logger.info(f"Moving deck {deck_id} to folder {folder_id_value}, assigning order_index {max_order + 1}")
                    except Exception as e:
                        # Column might not exist yet - log warning but continue without it
                        error_str = str(e)
                        if "order_index" in error_str or "42703" in error_str:
                            logger.warning("order_index column not found - please run migration. Continuing without order_index.")
                        # Don't fail the operation, just skip order_index
                
                update_data["folder_id"] = folder_id_value
            else:
                # Moving to root - clear folder_id and order_index
                update_data["folder_id"] = None
                # Try to clear order_index, but don't fail if column doesn't exist
                # We'll let the update attempt handle the error gracefully
                # Only set order_index to None if we're actually moving (not just updating other fields)
                if old_folder_id is not None:
                    # Only try to clear order_index if deck was actually in a folder
                    update_data["order_index"] = None
        
        # Handle order_index update if explicitly provided
        if "order_index" in update_dict and current_deck.get("folder_id"):
            # Only allow order_index updates for decks in folders
            update_data["order_index"] = update_dict["order_index"]
        
        if not update_data:
            # No changes to apply
            deck_result = db.service_client.table("decks").select("*").eq("id", deck_id).execute()
            return deck_result.data[0]
        
        # Update deck - handle case where order_index column doesn't exist
        try:
            result = db.service_client.table("decks").update(update_data).eq("id", deck_id).execute()
        except Exception as update_error:
            error_str = str(update_error)
            error_dict = {}
            # Try to extract error details
            try:
                if hasattr(update_error, '__dict__'):
                    error_dict = update_error.__dict__
                elif isinstance(update_error, dict):
                    error_dict = update_error
                # Check for message attribute
                if hasattr(update_error, 'message'):
                    error_str = str(update_error.message) + " " + error_str
            except:
                pass
            
            # Check if error is about order_index column not existing
            is_order_index_error = (
                "order_index" in error_str or 
                "42703" in error_str or
                str(error_dict.get("code")) == "42703" or
                ("column" in error_str.lower() and "order_index" in error_str.lower())
            )
            
            if is_order_index_error:
                logger.warning("order_index column not found - retrying update without order_index. Please run migration.")
                # Remove order_index from update_data and retry
                update_data_retry = {k: v for k, v in update_data.items() if k != "order_index"}
                if update_data_retry:
                    try:
                        result = db.service_client.table("decks").update(update_data_retry).eq("id", deck_id).execute()
                        logger.info(f"Successfully updated deck {deck_id} without order_index")
                    except Exception as retry_error:
                        logger.error(f"Failed to update deck even without order_index: {retry_error}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to update deck: {str(retry_error)}"
                        )
                else:
                    # No other updates to make, just return current deck
                    logger.info("No updates to apply after removing order_index")
                    deck_result = db.service_client.table("decks").select("*").eq("id", deck_id).execute()
                    updated_deck = deck_result.data[0] if deck_result.data else None
                    if updated_deck:
                        flashcards_result = db.service_client.table("flashcards").select("*").eq("deck_id", deck_id).execute()
                        flashcards = flashcards_result.data if flashcards_result.data else []
                        updated_deck["flashcard_count"] = len(flashcards)
                    return updated_deck
            else:
                # Some other error - provide better error message
                logger.error(f"Error updating deck {deck_id}: {update_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update deck: {str(update_error)}"
                )
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


@decks_router.get("/{deck_id}/next-podcast", tags=["Decks"])
async def get_next_podcast_in_folder(deck_id: str, current_user = Depends(get_current_user)):
    """Get the next deck with a podcast in the same folder"""
    try:
        # Get current deck
        deck_result = db.service_client.table("decks").select("*").eq("id", deck_id).execute()
        if not deck_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        
        current_deck = deck_result.data[0]
        if current_deck["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        folder_id = current_deck.get("folder_id")
        if not folder_id:
            # Deck is in root, no autoplay
            return {"next_deck": None}
        
        current_order = current_deck.get("order_index") or 0
        
        # Get next deck in folder with podcast, ordered by order_index
        all_decks_result = db.service_client.table("decks").select("*").eq("folder_id", folder_id).eq("user_id", current_user.id).execute()
        folder_decks = all_decks_result.data if all_decks_result.data else []
        
        # Filter decks with podcasts and order_index > current_order
        next_decks = [
            deck for deck in folder_decks
            if deck.get("podcast_audio_url") and (deck.get("order_index") or 0) > current_order
        ]
        
        if not next_decks:
            return {"next_deck": None}
        
        # Get the one with the smallest order_index (next in sequence)
        next_deck = min(next_decks, key=lambda d: d.get("order_index") or 0)
        
        # Add flashcard count
        flashcards_result = db.service_client.table("flashcards").select("*").eq("deck_id", next_deck["id"]).execute()
        flashcards = flashcards_result.data if flashcards_result.data else []
        next_deck["flashcard_count"] = len(flashcards)
        
        return {"next_deck": next_deck}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get next podcast error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get next podcast"
        )


@decks_router.post("/folder/{folder_id}/reorder", tags=["Decks"])
async def reorder_decks_in_folder(
    folder_id: str,
    reorder_request: DeckReorderRequest,
    current_user = Depends(get_current_user)
):
    """Reorder decks in a folder"""
    try:
        # Verify folder belongs to user
        folder_result = db.service_client.table("folders").select("*").eq("id", folder_id).execute()
        if not folder_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found"
            )
        
        if folder_result.data[0]["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Verify all decks belong to the user and are in this folder
        if reorder_request.deck_order:
            decks_result = db.service_client.table("decks").select("id,folder_id,user_id").in_("id", reorder_request.deck_order).execute()
            decks = decks_result.data if decks_result.data else []
            
            for deck in decks:
                if deck["user_id"] != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access denied to deck {deck['id']}"
                    )
                if deck.get("folder_id") != folder_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Deck {deck['id']} is not in folder {folder_id}"
                    )
        
        # Update order_index for each deck - handle case where column doesn't exist
        try:
            for index, deck_id in enumerate(reorder_request.deck_order):
                db.service_client.table("decks").update({
                    "order_index": index
                }).eq("id", deck_id).eq("folder_id", folder_id).eq("user_id", current_user.id).execute()
        except Exception as e:
            error_str = str(e)
            if "order_index" in error_str or "42703" in error_str:
                logger.warning("order_index column not found - cannot reorder. Please run migration.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Order index column not found. Please run the database migration."
                )
            raise
        
        return {"message": "Decks reordered successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reorder decks error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder decks"
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
        
        # Delete podcast audio if it exists
        if deck.get("podcast_audio_url"):
            try:
                # Extract file path from URL (format: .../storage/v1/object/public/quizly-files/path/to/file.mp3)
                if "quizly-files" in deck["podcast_audio_url"]:
                    file_path = deck["podcast_audio_url"].split("quizly-files/")[-1]
                    db.service_client.storage.from_("quizly-files").remove([file_path])
            except Exception as e:
                logger.warning(f"Failed to delete podcast audio: {e}")
        
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


@decks_router.post("/{deck_id}/generate-podcast", tags=["Decks"])
async def generate_podcast(deck_id: str, current_user = Depends(get_current_user)):
    """Generate podcast-style audio for a deck"""
    try:
        print(f"Generating podcast for deck: {deck_id}")
        
        # Verify deck belongs to user
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
        
        # Get all flashcards for the deck
        flashcards_result = db.service_client.table("flashcards").select("*").eq("deck_id", deck_id).execute()
        flashcards = flashcards_result.data if flashcards_result.data else []
        
        if len(flashcards) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot generate podcast for a deck with no flashcards"
            )
        
        print(f"Found {len(flashcards)} flashcards for podcast generation")
        
        # Generate podcast script using OpenAI
        client = get_openai_client()
        
        # Create script prompt - include ALL flashcards with full content
        # Don't truncate - we need all cards covered
        flashcard_text = "\n\n".join([
            f"Card {i+1}:\nQuestion: {card['question']}\nAnswer: {card['answer']}"
            for i, card in enumerate(flashcards)
        ])
        
        total_cards = len(flashcards)
        
        script_prompt = f"""Create a comprehensive, lively conversational podcast script covering ALL {total_cards} flashcards. This should be a detailed, engaging study session podcast.

        Flashcard Content (ALL {total_cards} cards must be covered):
        {flashcard_text}
        
        CRITICAL REQUIREMENTS:
        1. COVER EVERY SINGLE CARD - You must include all {total_cards} cards in the podcast. Do not skip any.
        2. Each card should have substantial coverage (at least 3-5 dialogue exchanges per card):
           - Questioner introduces the question clearly
           - Answerer provides a detailed, conversational explanation
           - Questioner can ask follow-up questions or request clarification
           - Answerer expands on the answer with examples, context, or additional details
           - Natural transitions between cards
        3. Make answers detailed and explanatory - don't just state facts. Expand on WHY, HOW, and provide context.
        4. Each card should take approximately 30-60 seconds of dialogue to cover properly.
        5. Use clear transitions: "Great! Now let's move to card {total_cards if total_cards > 1 else 1}", "Perfect! Next up is question number X", "Alright, here's another interesting one - card X"
        6. Make it feel like two friends having an in-depth study session with thorough explanations
        7. The Answerer should elaborate on answers, provide examples, explain concepts thoroughly
        8. Include natural reactions: "Oh interesting!", "That makes sense!", "Let me think about that..."
        9. Ensure the podcast is comprehensive - aim for at least 4-6 minutes of content for {total_cards} cards
        
        Format the script as JSON with this structure:
        {{
            "segments": [
                {{
                    "speaker": "questioner",
                    "text": "Hey! Welcome to our study podcast. We have {total_cards} great questions to go through today. Ready to dive in?"
                }},
                {{
                    "speaker": "answerer",
                    "text": "Absolutely! I'm excited. Let's make sure we cover everything thoroughly."
                }},
                {{
                    "speaker": "questioner",
                    "text": "Perfect! So here's our first question: [full question text from Card 1]"
                }},
                {{
                    "speaker": "answerer",
                    "text": "[Detailed, expanded answer with explanation, examples, and context - make this substantial]"
                }},
                {{
                    "speaker": "questioner",
                    "text": "[Follow-up question or reaction, then transition to Card 2]"
                }},
                {{
                    "speaker": "answerer",
                    "text": "[Response and continuation]"
                }}
                // Continue this pattern for ALL {total_cards} cards...
            ]
        }}
        
        IMPORTANT: 
        - Generate segments for ALL {total_cards} cards
        - Each card needs multiple dialogue exchanges (not just one question-answer pair)
        - Make answers detailed and explanatory
        - Include natural transitions between each card
        - The total script should be comprehensive and cover everything thoroughly"""
        
        # Generate script with increased token limit to ensure all cards are covered
        # Calculate token limit based on number of cards (more cards = more tokens needed)
        # Base: 2000 tokens, add 500 per card for detailed coverage
        estimated_tokens = 2000 + (len(flashcards) * 500)
        # Cap at 4000 tokens (GPT-3.5-turbo max output tokens is 4096, using 4000 to be safe)
        max_tokens = min(estimated_tokens, 4000)
        
        script_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are an expert podcast script writer. Create comprehensive, detailed conversational scripts that cover ALL {total_cards} flashcards provided. Each card must have substantial coverage with multiple dialogue exchanges. Return only valid JSON."},
                {"role": "user", "content": script_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        script_content = script_response.choices[0].message.content
        script_data = json.loads(script_content)
        segments = script_data.get("segments", [])
        
        if not segments:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate podcast script"
            )
        
        # Validate script quality - check if we have enough segments for all cards
        # Each card should have at least 3-4 segments (intro, question, answer, transition)
        min_expected_segments = total_cards * 3 + 2  # 3 per card + intro/outro
        if len(segments) < min_expected_segments:
            logger.warning(f"Generated script has {len(segments)} segments but expected at least {min_expected_segments} for {total_cards} cards. Script may be incomplete.")
            print(f"Warning: Script may not cover all cards. Generated {len(segments)} segments for {total_cards} cards.")
        
        # Calculate total script length (rough estimate: ~150 words per minute of speech)
        total_words = sum(len(seg.get("text", "").split()) for seg in segments)
        estimated_minutes = total_words / 150
        
        print(f"Generated script with {len(segments)} segments covering {total_cards} cards")
        print(f"Estimated podcast length: ~{estimated_minutes:.1f} minutes ({total_words} words)")
        
        # Generate audio for each segment with appropriate voices
        # OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer
        # Use more lively, energetic voices
        questioner_voice = "shimmer"  # More lively, energetic female voice
        answerer_voice = "echo"       # More lively, energetic male voice
        
        # Prepare segments for parallel processing
        segment_tasks = []
        for i, segment in enumerate(segments):
            speaker = segment.get("speaker", "questioner").lower()
            text = segment.get("text", "")
            
            if not text:
                continue
            
            # Select voice based on speaker
            voice = questioner_voice if speaker == "questioner" else answerer_voice
            segment_tasks.append((i, text, voice))
        
        # Function to generate TTS audio for a single segment
        def generate_tts_audio(index, text, voice):
            """Generate TTS audio for a single segment"""
            try:
                response = client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=text
                )
                return (index, response.content, None)
            except Exception as e:
                logger.error(f"Error generating audio for segment {index}: {e}")
                return (index, None, str(e))
        
        # Generate audio segments in parallel (much faster!)
        # Use ThreadPoolExecutor to parallelize TTS API calls
        audio_segments_dict = {}
        max_workers = min(10, len(segment_tasks))  # Process up to 10 segments concurrently
        
        print(f"Generating audio for {len(segment_tasks)} segments in parallel (max {max_workers} concurrent)...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(generate_tts_audio, idx, text, voice): idx 
                for idx, text, voice in segment_tasks
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_index):
                index, audio_data, error = future.result()
                if audio_data:
                    audio_segments_dict[index] = audio_data
                    completed += 1
                    if completed % 5 == 0:
                        print(f"Generated {completed}/{len(segment_tasks)} audio segments...")
                else:
                    logger.warning(f"Failed to generate audio for segment {index}: {error}")
        
        # Convert dict back to list in correct order
        audio_segments = [audio_segments_dict[i] for i in sorted(audio_segments_dict.keys())]
        
        print(f"Successfully generated {len(audio_segments)}/{len(segment_tasks)} audio segments")
        
        if not audio_segments:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate audio segments"
            )
        
        # Combine audio segments using pydub
        combined_audio_segment = None
        temp_files = []
        combined_temp = None
        
        try:
            # Try using pydub for proper audio combination
            # Write each audio segment to a temporary file and load with pydub
            for i, audio_data in enumerate(audio_segments):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_files.append(temp_file.name)
                temp_file.write(audio_data)
                temp_file.close()
                
                # Load audio segment
                segment = AudioSegment.from_mp3(temp_file.name)
                
                # Add small pause between segments (500ms)
                if combined_audio_segment is None:
                    combined_audio_segment = segment
                else:
                    # Add pause and concatenate
                    pause = AudioSegment.silent(duration=500)  # 500ms pause
                    combined_audio_segment = combined_audio_segment + pause + segment
            
            # Background music disabled - podcast will contain only voice audio
            # (Background music code removed per user request)
            
            # Export combined audio to bytes
            combined_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            combined_temp.close()
            combined_audio_segment.export(combined_temp.name, format="mp3")
            
            # Read the combined audio file
            with open(combined_temp.name, 'rb') as f:
                combined_audio = f.read()
            
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            try:
                if combined_temp:
                    os.unlink(combined_temp.name)
            except:
                pass
                
        except Exception as e:
            # Clean up on error
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            try:
                if combined_temp:
                    os.unlink(combined_temp.name)
            except:
                pass
            
            # Fallback: Simple concatenation (works if all segments are same format)
            # Note: This is less ideal but works without ffmpeg
            logger.warning(f"pydub/ffmpeg failed ({e}), using simple concatenation fallback")
            print(f"Warning: Using fallback audio combination method. Error: {e}")
            
            try:
                # Simple byte concatenation - works for OpenAI TTS MP3 files
                # OpenAI TTS generates consistent MP3 format, so this should work
                combined_audio = b"".join(audio_segments)
                logger.info("Successfully combined audio using fallback method")
            except Exception as fallback_error:
                logger.error(f"Fallback audio combination also failed: {fallback_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to combine audio segments: {str(e)}. Note: ffmpeg may be required for proper audio processing. Install ffmpeg or check server logs for details."
                )
        
        # Upload to Supabase Storage
        file_path = f"podcasts/{current_user.id}/{deck_id}.mp3"
        
        try:
            # Upload the audio file using service client to bypass RLS
            upload_result = db.service_client.storage.from_("quizly-files").upload(
                file_path,
                combined_audio,
                file_options={"content-type": "audio/mpeg", "upsert": "true"}
            )
            
            # Get public URL
            public_url = db.service_client.storage.from_("quizly-files").get_public_url(file_path)
            
            # Update deck with podcast URL
            update_result = db.service_client.table("decks").update({
                "podcast_audio_url": public_url
            }).eq("id", deck_id).execute()
            
            updated_deck = update_result.data[0] if update_result.data else None
            
            print(f"Podcast generated and uploaded: {public_url}")
            
            return {
                "message": "Podcast generated successfully",
                "podcast_audio_url": public_url,
                "deck_id": deck_id
            }
            
        except Exception as e:
            logger.error(f"Error uploading podcast: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload podcast: {str(e)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Podcast generation error: {e}")
        print(f"Podcast generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate podcast: {str(e)}"
        )
