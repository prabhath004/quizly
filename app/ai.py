"""
Quizly Backend - AI Integration Module
Handles flashcard generation and embeddings-based answer checking
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from app.models import (
    FlashcardGenerationRequest,
    FlashcardGenerationResponse,
    AnswerEvaluationRequest,
    AnswerEvaluationResponse,
    FlashcardCreate,
    DifficultyLevel,
    QuestionType
)
from app.auth import get_current_user
from app.database import db
from app.config import get_settings
import openai
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import time
import logging
import json
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Router setup
ai_router = APIRouter()

# Initialize OpenAI client
def get_openai_client():
    """Get OpenAI client with API key"""
    settings = get_settings()
    return openai.OpenAI(api_key=settings.openai_api_key)


async def generate_flashcards_from_text(
    request: FlashcardGenerationRequest,
    current_user
) -> FlashcardGenerationResponse:
    """Generate flashcards from text using OpenAI GPT"""
    try:
        start_time = time.time()
        client = get_openai_client()
        
        # Create optimized prompt based on question type
        if request.question_type == QuestionType.MCQ:
            prompt = f"""You are creating {request.num_flashcards} multiple choice questions at {request.difficulty_level} difficulty level.

Content to analyze:
{request.text_content[:3000]}

Requirements:
1. Create exactly {request.num_flashcards} questions
2. Each question must have exactly 4 options
3. Difficulty: {request.difficulty_level}
4. Include plausible wrong answers
5. Test understanding, not just memorization

Return ONLY valid JSON in this exact format:
{{
  "flashcards": [
    {{
      "question": "What is X?",
      "answer": "Explanation of correct answer",
      "difficulty": "{request.difficulty_level}",
      "question_type": "mcq",
      "mcq_options": ["Option 1", "Option 2", "Option 3", "Option 4"],
      "correct_option_index": 1,
      "tags": ["topic1", "topic2"]
    }}
  ]
}}"""

        elif request.question_type == QuestionType.TRUE_FALSE:
            prompt = f"""You are creating {request.num_flashcards} true/false questions at {request.difficulty_level} difficulty level.

Content to analyze:
{request.text_content[:3000]}

Requirements:
1. Create exactly {request.num_flashcards} questions
2. Each must be a clear true/false statement
3. Difficulty: {request.difficulty_level}
4. Include explanation for the answer

Return ONLY valid JSON in this exact format:
{{
  "flashcards": [
    {{
      "question": "The Earth is flat",
      "answer": "False. The Earth is an oblate spheroid.",
      "difficulty": "{request.difficulty_level}",
      "question_type": "true_false",
      "mcq_options": ["True", "False"],
      "correct_option_index": 1,
      "tags": ["topic1"]
    }}
  ]
}}"""

        else:
            # Free response questions
            prompt = f"""You are creating {request.num_flashcards} open-ended questions at {request.difficulty_level} difficulty level.

Content to analyze:
{request.text_content[:3000]}

Requirements:
1. Create exactly {request.num_flashcards} questions
2. Questions should be open-ended (require explanation)
3. Difficulty: {request.difficulty_level}
4. Answers should be 2-3 sentences
5. Questions students can speak aloud

Return ONLY valid JSON in this exact format:
{{
  "flashcards": [
    {{
      "question": "Explain the concept of X",
      "answer": "X is defined as... It works by... This is important because...",
      "difficulty": "{request.difficulty_level}",
      "question_type": "free_response",
      "tags": ["topic1", "topic2"]
    }}
  ]
}}"""
        
        # Call OpenAI API with optimized parameters
        response = client.chat.completions.create(
            model=get_settings().flashcard_model,
            messages=[
                {"role": "system", "content": "Expert educator. Create JSON flashcards. No markdown, just valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500 if request.num_flashcards <= 10 else 2500,  # Dynamic token limit
            temperature=0.3,  # Lower temperature for more consistent JSON
            response_format={ "type": "json_object" }  # Force JSON response
        )
        
        # Parse response
        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        # Extract JSON from response
        try:
            # Since we're using JSON mode, content should already be valid JSON
            parsed_data = json.loads(content)
            flashcards_data = parsed_data.get("flashcards", [])
            
            if not flashcards_data:
                logger.error(f"No flashcards in response: {content[:200]}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No flashcards generated"
                )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            logger.error(f"Response content: {content[:500]}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse AI response"
            )
        
        # Convert to FlashcardCreate objects
        flashcards = []
        for card_data in flashcards_data:
            # Handle difficulty - extract value if it's in format "DifficultyLevel.MEDIUM"
            difficulty_str = card_data.get("difficulty", request.difficulty_level.value)
            if isinstance(difficulty_str, str) and "." in difficulty_str:
                # Extract the value part (e.g., "DifficultyLevel.MEDIUM" -> "MEDIUM")
                difficulty_str = difficulty_str.split(".")[-1].lower()
            elif isinstance(difficulty_str, str):
                difficulty_str = difficulty_str.lower()
            
            # Handle question type
            question_type_str = card_data.get("question_type", request.question_type.value)
            if isinstance(question_type_str, str) and "." in question_type_str:
                question_type_str = question_type_str.split(".")[-1].lower()
            elif isinstance(question_type_str, str):
                question_type_str = question_type_str.lower()
            
            # Build flashcard
            flashcard_dict = {
                "question": card_data["question"],
                "answer": card_data["answer"],
                "difficulty": DifficultyLevel(difficulty_str),
                "question_type": QuestionType(question_type_str),
                "tags": card_data.get("tags", []),
                "deck_id": ""  # Will be set when creating the deck
            }
            
            # Add MCQ/True-False specific fields if applicable
            if QuestionType(question_type_str) in [QuestionType.MCQ, QuestionType.TRUE_FALSE]:
                flashcard_dict["mcq_options"] = card_data.get("mcq_options", [])
                flashcard_dict["correct_option_index"] = card_data.get("correct_option_index", 0)
            
            flashcard = FlashcardCreate(**flashcard_dict)
            flashcards.append(flashcard)
        
        processing_time = time.time() - start_time
        
        return FlashcardGenerationResponse(
            flashcards=flashcards,
            processing_time=processing_time,
            tokens_used=tokens_used
        )
    
    except Exception as e:
        logger.error(f"Flashcard generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Flashcard generation failed"
        )


async def get_or_create_embedding(text: str) -> List[float]:
    """Get embedding from cache or create new one"""
    import hashlib
    
    # Create hash of text for caching
    text_hash = hashlib.md5(text.encode()).hexdigest()
    
    # Check if embedding exists in database
    existing = await db.get_embedding_by_hash(text_hash)
    if existing:
        logger.info(f"✅ Found cached embedding for text hash: {text_hash[:8]}...")
        return existing['embedding']
    
    # Generate new embedding
    logger.info(f"🔄 Generating new embedding for text hash: {text_hash[:8]}...")
    embedding = await get_embedding(text)
    
    # Store in database
    embedding_data = {
        'text_hash': text_hash,
        'text_content': text,
        'embedding': embedding,
        'model_name': 'text-embedding-ada-002'
    }
    
    await db.create_embedding(embedding_data)
    logger.info(f"💾 Stored new embedding in database")
    
    return embedding


async def get_embedding(text: str) -> List[float]:
    """Get embedding for text using OpenAI"""
    try:
        client = get_openai_client()
        settings = get_settings()
        
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=text
        )
        
        return response.data[0].embedding
    
    except Exception as e:
        logger.error(f"Embedding generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embedding"
        )


async def evaluate_answer_similarity(
    user_answer: str,
    correct_answer: str
) -> tuple[bool, float]:
    """Evaluate answer similarity using embeddings"""
    try:
        # Get embeddings for both answers (no caching - keep it simple)
        user_embedding = await get_embedding(user_answer)
        correct_embedding = await get_embedding(correct_answer)
        
        # Calculate cosine similarity
        similarity = cosine_similarity(
            [user_embedding],
            [correct_embedding]
        )[0][0]
        
        # Determine if answer is correct based on threshold
        settings = get_settings()
        is_correct = similarity >= settings.similarity_threshold
        
        return is_correct, similarity
    
    except Exception as e:
        logger.error(f"Answer evaluation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Answer evaluation failed"
        )


@ai_router.post("/generate-flashcards", tags=["AI Services"])
async def generate_flashcards(
    deck_title: str = Form("Generated Deck"),
    num_flashcards: int = Form(10),
    difficulty_level: str = Form("medium"),
    question_type: str = Form("free_response"),
    text_content: str = Form(None),
    file: UploadFile = File(None),
    save_to_db: bool = Form(True),
    current_user = Depends(get_current_user)
):
    """Generate flashcards and optionally save to database
    
    Question Types:
    - mcq: Multiple Choice Questions with 4 options
    - true_false: True/False questions
    - free_response: Open-ended questions (users can speak their answer)
    
    Returns: Generated flashcards with deck_id if saved
    """
    try:
        # Log received parameters with print for immediate visibility
        print(f"📥 Received params: deck_title={deck_title}, num={num_flashcards}, difficulty={difficulty_level}, type={question_type}, save_to_db={save_to_db}")
        print(f"📄 Has file: {file is not None and file.filename}, Has text: {text_content is not None and len(text_content or '') > 0}")
        logger.info(f"📥 Received params: deck_title={deck_title}, num={num_flashcards}, difficulty={difficulty_level}, type={question_type}, save_to_db={save_to_db}")
        logger.info(f"📄 Has file: {file is not None and file.filename}, Has text: {text_content is not None and len(text_content or '') > 0}")
        
        # Determine input source
        if file and file.filename:
            # File input - extract text first
            logger.info(f"📁 Processing file: {file.filename}")
            from app.ingest import extract_text_with_openai
            file_content = await file.read()
            text_content = await extract_text_with_openai(file_content, file.filename)
            logger.info(f"✅ Extracted {len(text_content)} characters from file")
        elif text_content and len(text_content.strip()) > 0:
            # Text input - use directly
            logger.info(f"📝 Using text input: {len(text_content)} characters")
        else:
            logger.error("❌ No content provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either provide text content or upload a file"
            )
        
        # Create generation request
        generation_request = FlashcardGenerationRequest(
            text_content=text_content,
            deck_title=deck_title,
            difficulty_level=difficulty_level,
            num_flashcards=num_flashcards,
            question_type=question_type
        )
        
        # Generate flashcards
        flashcard_result = await generate_flashcards_from_text(generation_request, current_user)
        
        # Save to database if requested
        if save_to_db:
            try:
                # Create deck in Supabase using service client to bypass RLS
                deck_data = {
                    "title": deck_title,
                    "user_id": current_user.id,
                    "description": f"{question_type.upper()} flashcards - {difficulty_level} difficulty"
                }
                
                # Use service client to bypass RLS during creation
                print(f"💾 Creating deck: {deck_title}")
                logger.info(f"💾 Creating deck: {deck_title}")
                deck_insert_result = db.service_client.table("decks").insert(deck_data).execute()
                deck = deck_insert_result.data[0] if deck_insert_result.data else None
                
                if not deck:
                    print(f"❌ Failed to create deck in database")
                    logger.error(f"❌ Failed to create deck in database")
                    raise Exception("Deck creation failed")
                
                print(f"✅ Deck created with ID: {deck['id']}")
                logger.info(f"✅ Deck created with ID: {deck['id']}")
                
                if deck:
                    # Save all flashcards to database using service client
                    flashcards_to_save = []
                    for flashcard in flashcard_result.flashcards:
                        flashcard_dict = {
                            "deck_id": deck["id"],
                            "question": flashcard.question,
                            "answer": flashcard.answer,
                            "difficulty": flashcard.difficulty.value,
                            "question_type": flashcard.question_type.value,
                            "tags": flashcard.tags,
                        }
                        
                        # Add MCQ/True-False specific fields
                        if flashcard.mcq_options:
                            flashcard_dict["mcq_options"] = flashcard.mcq_options
                            flashcard_dict["correct_option_index"] = flashcard.correct_option_index
                        
                        flashcards_to_save.append(flashcard_dict)
                    
                    # Use service client for batch insert
                    print(f"💾 Saving {len(flashcards_to_save)} flashcards to database...")
                    logger.info(f"💾 Saving {len(flashcards_to_save)} flashcards to database...")
                    saved_result = db.service_client.table("flashcards").insert(flashcards_to_save).execute()
                    saved_cards = saved_result.data if saved_result.data else []
                    
                    print(f"✅ Saved {len(saved_cards)} flashcards to deck {deck['id']}")
                    logger.info(f"✅ Saved {len(saved_cards)} flashcards to deck {deck['id']}")
                    
                    return {
                        "deck_id": deck["id"],
                        "deck_title": deck_title,
                        "question_type": question_type,
                        "difficulty": difficulty_level,
                        "flashcards": [
                            {
                                "id": card.get("id"),
                                "question": card.get("question"),
                                "answer": card.get("answer"),
                                "difficulty": card.get("difficulty"),
                                "question_type": card.get("question_type"),
                                "mcq_options": card.get("mcq_options"),
                                "correct_option_index": card.get("correct_option_index"),
                                "tags": card.get("tags", [])
                            }
                            for card in saved_cards
                        ],
                        "processing_time": flashcard_result.processing_time,
                        "tokens_used": flashcard_result.tokens_used,
                        "saved_count": len(saved_cards)
                    }
            except Exception as e:
                logger.error(f"❌ Error saving to database: {e}")
                # Return generated flashcards even if save fails
                return {
                    "deck_id": None,
                    "error": "Failed to save to database",
                    "flashcards": flashcard_result.flashcards,
                    "processing_time": flashcard_result.processing_time,
                    "tokens_used": flashcard_result.tokens_used,
                }
        
        # If not saving to DB, return flashcard result
        return {
            "flashcards": flashcard_result.flashcards,
            "processing_time": flashcard_result.processing_time,
            "tokens_used": flashcard_result.tokens_used,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Flashcard generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Flashcard generation failed"
        )


@ai_router.post("/evaluate-answer", response_model=AnswerEvaluationResponse, tags=["AI Services"])
async def evaluate_answer(
    request: AnswerEvaluationRequest,
    current_user = Depends(get_current_user)
):
    """Evaluate user answer against correct answer
    
    For MCQ: Checks if selected option matches correct_option_index
    For Free Response: Uses AI embeddings to evaluate semantic similarity
    """
    try:
        # Handle MCQ and True/False evaluation
        if request.question_type in [QuestionType.MCQ, QuestionType.TRUE_FALSE]:
            # For MCQ/TF, user_answer should be the option index (as string)
            try:
                user_option_index = int(request.user_answer)
                is_correct = user_option_index == request.correct_option_index
                similarity_score = 1.0 if is_correct else 0.0
                
                if is_correct:
                    feedback = "✅ Correct! Well done."
                else:
                    if request.question_type == QuestionType.TRUE_FALSE:
                        correct_ans = "True" if request.correct_option_index == 0 else "False"
                        feedback = f"❌ Incorrect. The correct answer is: {correct_ans}"
                    else:
                        feedback = f"❌ Incorrect. The correct answer was option {request.correct_option_index}."
                
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="For MCQ/True-False, user_answer must be the option index"
                )
        
        # Handle Free Response evaluation
        else:
            is_correct, similarity_score = await evaluate_answer_similarity(
                request.user_answer,
                request.correct_answer
            )
            
            # Generate feedback based on similarity
            if is_correct:
                feedback = "Great job! Your answer is correct."
            elif similarity_score > 0.6:
                feedback = "Close! Your answer is partially correct but could be more specific."
            elif similarity_score > 0.3:
                feedback = "Not quite right. Try to be more precise with your answer."
            else:
                feedback = "Incorrect. Please review the material and try again."
        
        return AnswerEvaluationResponse(
            is_correct=is_correct,
            similarity_score=similarity_score,
            feedback=feedback
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Answer evaluation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Answer evaluation failed"
        )


@ai_router.post("/get-embedding", tags=["AI Services"])
async def get_text_embedding(text: str, current_user = Depends(get_current_user)):
    """Get embedding for text (for testing purposes)"""
    try:
        embedding = await get_embedding(text)
        return {
            "text": text,
            "embedding": embedding,
            "dimension": len(embedding)
        }
    
    except Exception as e:
        logger.error(f"Embedding generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Embedding generation failed"
        )