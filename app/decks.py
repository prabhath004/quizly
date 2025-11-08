from fastapi import APIRouter, Depends, HTTPException, status
from app.models import Deck, DeckCreate, DeckUpdate
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
from pydub import AudioSegment
import requests

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
        
        # Create script prompt - include all flashcards, but limit individual card lengths
        flashcard_text = "\n\n".join([
            f"Question {i+1}: {card['question'][:500]}\nAnswer: {card['answer'][:1000]}"
            for i, card in enumerate(flashcards)
        ])
        
        # Limit total flashcard text to avoid token limits (keep it reasonable)
        if len(flashcard_text) > 4000:
            flashcard_text = flashcard_text[:4000] + "\n\n[Additional flashcards truncated for script generation...]"
        
        script_prompt = f"""Create a lively, conversational podcast script with natural back-and-forth dialogue between two speakers: a Questioner and an Answerer.
        
        Flashcard Content:
        {flashcard_text}
        
        Requirements:
        1. Make it feel like a real conversation with natural interruptions, follow-up questions, and reactions
        2. The Questioner should ask questions in a friendly, engaging way
        3. The Answerer should respond conversationally, not just recite facts - add personality and enthusiasm
        4. Include natural back-and-forth: the Answerer can ask clarifying questions, the Questioner can react to answers
        5. CLEARLY mark transitions between questions with phrases like "Great! Let's move on to the next question", "Alright, here's another one", or "Perfect! Now for question number X"
        6. Make it feel like two friends having a study session, not a formal Q&A
        
        Format the script as JSON with this structure:
        {{
            "segments": [
                {{
                    "speaker": "questioner",
                    "text": "Hey! Welcome to our study podcast. I'm excited to go through these questions with you. Ready for the first one?"
                }},
                {{
                    "speaker": "answerer",
                    "text": "Absolutely! Let's do this!"
                }},
                {{
                    "speaker": "questioner",
                    "text": "Okay, so here's question one: [question text]"
                }},
                {{
                    "speaker": "answerer",
                    "text": "Oh, that's interesting! So the answer is [answer]. Let me explain why..."
                }},
                {{
                    "speaker": "questioner",
                    "text": "Perfect! That makes sense. Alright, moving on to question two..."
                }}
            ]
        }}
        
        Make it feel natural and conversational with real dialogue, reactions, and clear question transitions."""
        
        # Generate script
        script_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert podcast script writer. Create engaging, natural conversational scripts. Return only valid JSON."},
                {"role": "user", "content": script_prompt}
            ],
            max_tokens=2000,
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
        
        print(f"Generated script with {len(segments)} segments")
        
        # Generate audio for each segment with appropriate voices
        # OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer
        # Use more lively, energetic voices
        questioner_voice = "shimmer"  # More lively, energetic female voice
        answerer_voice = "echo"       # More lively, energetic male voice
        
        audio_segments = []
        for segment in segments:
            speaker = segment.get("speaker", "questioner").lower()
            text = segment.get("text", "")
            
            if not text:
                continue
            
            # Select voice based on speaker
            voice = questioner_voice if speaker == "questioner" else answerer_voice
            
            # Generate audio using OpenAI TTS
            try:
                response = client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=text
                )
                
                # Read audio data
                audio_data = response.content
                audio_segments.append(audio_data)
                
                # Small delay to avoid rate limits
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error generating audio for segment: {e}")
                # Continue with other segments even if one fails
                continue
        
        if not audio_segments:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate audio segments"
            )
        
        # Combine audio segments using pydub
        combined_audio_segment = None
        temp_files = []
        combined_temp = None
        background_music_temp = None
        
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
            
            # Download and add background music (try multiple sources for reliability)
            bg_music_added = False
            bg_music_urls = [
                "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",  # Backup source 1
                "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3",  # Backup source 2
            ]
            
            for bg_music_url in bg_music_urls:
                try:
                    logger.info(f"Attempting to download background music from: {bg_music_url}")
                    bg_response = requests.get(bg_music_url, timeout=15, stream=True)
                    
                    if bg_response.status_code == 200:
                        background_music_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                        for chunk in bg_response.iter_content(chunk_size=8192):
                            background_music_temp.write(chunk)
                        background_music_temp.close()
                        
                        try:
                            bg_music = AudioSegment.from_mp3(background_music_temp.name)
                            
                            # Lower volume by 17dB - present but won't overwhelm voice (balanced level)
                            # This ensures background music is audible but stays in the background
                            bg_music = bg_music - 17
                            
                            # Loop background music to match podcast length
                            podcast_length = len(combined_audio_segment)
                            bg_length = len(bg_music)
                            
                            if bg_length < podcast_length:
                                # Loop the background music
                                loops_needed = (podcast_length // bg_length) + 1
                                bg_music = bg_music * loops_needed
                            
                            # Trim to match podcast length
                            bg_music = bg_music[:podcast_length]
                            
                            # Mix background music with podcast audio
                            combined_audio_segment = combined_audio_segment.overlay(bg_music)
                            bg_music_added = True
                            logger.info("Background music successfully added to podcast")
                            break  # Success, no need to try other URLs
                        except Exception as parse_error:
                            logger.warning(f"Failed to parse background music file: {parse_error}")
                            try:
                                os.unlink(background_music_temp.name)
                            except:
                                pass
                            continue  # Try next URL
                    else:
                        logger.warning(f"Failed to download background music: HTTP {bg_response.status_code}")
                except Exception as bg_error:
                    logger.warning(f"Error downloading background music from {bg_music_url}: {bg_error}")
                    continue  # Try next URL
            
            if not bg_music_added:
                # Last resort: Try to create a subtle ambient background
                # We'll try to use a silent segment with very low volume white noise
                # This ensures there's always some background presence
                try:
                    logger.info("Background music download failed, attempting to create ambient background")
                    podcast_length = len(combined_audio_segment)
                    
                    # Try to generate a subtle ambient tone
                    try:
                        from pydub.generators import Sine
                        # Create a very low, quiet tone
                        ambient_tone = Sine(80).to_audio_segment(duration=min(3000, podcast_length))
                        ambient_tone = ambient_tone - 32  # Very quiet
                        
                        # Loop to match length
                        while len(ambient_tone) < podcast_length:
                            ambient_tone = ambient_tone + ambient_tone
                        ambient_tone = ambient_tone[:podcast_length]
                        
                        # Mix with podcast
                        combined_audio_segment = combined_audio_segment.overlay(ambient_tone)
                        logger.info("Added subtle ambient tone as background music fallback")
                        print("Note: Using generated ambient tone (background music download unavailable)")
                    except ImportError:
                        # pydub.generators not available, skip ambient tone
                        logger.warning("pydub.generators not available, cannot create ambient background")
                        print("Warning: Background music could not be added. Podcast will continue without background music.")
                except Exception as fallback_error:
                    logger.error(f"Error in background music fallback: {fallback_error}")
                    print("Warning: Could not add background music. Podcast will continue without it.")
            
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
            try:
                if background_music_temp:
                    os.unlink(background_music_temp.name)
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
            try:
                if background_music_temp:
                    os.unlink(background_music_temp.name)
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
