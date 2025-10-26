"""
Quizly Backend - AI Integration Module
Handles flashcard generation and embeddings-based answer checking
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
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
        
        # Create prompt based on question type
        if request.question_type == QuestionType.MCQ:
            prompt = f"""
            Generate {request.num_flashcards} high-quality Multiple Choice Questions (MCQ) from the following text content.
            
            Text Content:
            {request.text_content}
            
            Requirements:
            - Create questions that test understanding, not just memorization
            - Provide exactly 4 options for each question
            - Make the correct answer clear and unambiguous
            - Include plausible distractors (wrong options that seem reasonable)
            - Difficulty level: {request.difficulty_level}
            - Questions should be clear and specific
            
            Return the flashcards in JSON format:
            {{
                "flashcards": [
                    {{
                        "question": "Question text here",
                        "answer": "The correct answer explanation",
                        "difficulty": "{request.difficulty_level}",
                        "question_type": "mcq",
                        "mcq_options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_option_index": 0,
                        "tags": ["tag1", "tag2"]
                    }}
                ]
            }}
            
            IMPORTANT: 
            - mcq_options must have exactly 4 options
            - correct_option_index is 0-based (0, 1, 2, or 3)
            - The answer field should explain WHY the correct option is right
            """
        else:
            # Free response questions
            prompt = f"""
            Generate {request.num_flashcards} high-quality free-response flashcards from the following text content.
            
            Text Content:
            {request.text_content}
            
            Requirements:
            - Create questions that test understanding, not just memorization
            - Make answers concise but comprehensive (1-3 sentences)
            - Difficulty level: {request.difficulty_level}
            - Questions should be clear and specific
            - Answers should be educational and informative
            - These are open-ended questions where users can speak their answer
            
            Return the flashcards in JSON format:
            {{
                "flashcards": [
                    {{
                        "question": "Question text here",
                        "answer": "Answer text here",
                        "difficulty": "{request.difficulty_level}",
                        "question_type": "free_response",
                        "tags": ["tag1", "tag2"]
                    }}
                ]
            }}
            """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=get_settings().flashcard_model,
            messages=[
                {"role": "system", "content": "You are an expert educator creating high-quality flashcards for effective learning."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        # Parse response
        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        # Extract JSON from response
        try:
            # Find JSON in the response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            json_content = content[start_idx:end_idx]
            parsed_data = json.loads(json_content)
            
            flashcards_data = parsed_data.get("flashcards", [])
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
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
            
            # Add MCQ-specific fields if applicable
            if QuestionType(question_type_str) == QuestionType.MCQ:
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


@ai_router.post("/generate-flashcards", response_model=FlashcardGenerationResponse, tags=["AI Services"])
async def generate_flashcards(
    file: UploadFile = File(None),
    deck_title: str = "Generated Deck",
    num_flashcards: int = 10,
    difficulty_level: str = "medium",
    question_type: str = "free_response",  # "mcq" or "free_response"
    text_content: str = None,
    current_user = Depends(get_current_user)
):
    """Generate flashcards from text content OR uploaded file
    
    Question Types:
    - mcq: Multiple Choice Questions with 4 options
    - free_response: Open-ended questions (users can speak their answer)
    """
    try:
        # Determine input source
        if file and file.filename:
            # File input - extract text first
            from app.ingest import extract_text_with_openai
            file_content = await file.read()
            text_content = await extract_text_with_openai(file_content, file.filename)
        elif text_content:
            # Text input - use directly
            pass
        else:
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
        return await generate_flashcards_from_text(generation_request, current_user)
    
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
        # Handle MCQ evaluation
        if request.question_type == QuestionType.MCQ:
            # For MCQ, user_answer should be the option index (as string)
            try:
                user_option_index = int(request.user_answer)
                is_correct = user_option_index == request.correct_option_index
                similarity_score = 1.0 if is_correct else 0.0
                
                if is_correct:
                    feedback = "Correct! Well done."
                else:
                    feedback = f"Incorrect. The correct answer was option {request.correct_option_index}."
                
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="For MCQ, user_answer must be the option index (0-3)"
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