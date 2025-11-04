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
        logger.info(f"Found cached embedding for text hash: {text_hash[:8]}...")
        return existing['embedding']
    
    # Generate new embedding
    logger.info(f"Generating new embedding for text hash: {text_hash[:8]}...")
    embedding = await get_embedding(text)
    
    # Store in database
    embedding_data = {
        'text_hash': text_hash,
        'text_content': text,
        'embedding': embedding,
        'model_name': 'text-embedding-ada-002'
    }
    
    await db.create_embedding(embedding_data)
    logger.info("Stored new embedding in database")
    
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


def preprocess_text(text: str) -> str:
    """Preprocess text for better similarity comparison"""
    import re

    # Convert to lowercase
    text = text.lower().strip()

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove common filler words that don't add semantic meaning
    filler_words = ['um', 'uh', 'like', 'you know', 'basically', 'actually', 'literally']
    for filler in filler_words:
        text = re.sub(r'\b' + filler + r'\b', '', text, flags=re.IGNORECASE)

    # Remove repeated words (e.g., "it is it is" -> "it is")
    words = text.split()
    cleaned_words = []
    prev_word = None
    for word in words:
        if word != prev_word or word not in ['is', 'the', 'a', 'an', 'it', 'and', 'or']:
            cleaned_words.append(word)
        prev_word = word

    text = ' '.join(cleaned_words)

    # Clean up punctuation (keep it but normalize)
    text = re.sub(r'[,;]+', ',', text)
    text = re.sub(r'\.+', '.', text)

    return text.strip()


async def evaluate_with_gpt(
    question: str,
    user_answer: str,
    correct_answer: str
) -> tuple[bool, float, str]:
    """Use GPT to semantically evaluate the answer quality"""
    try:
        client = get_openai_client()

        prompt = f"""You are an expert educator evaluating a student's answer to a question.

Question: {question}

Correct/Model Answer: {correct_answer}

Student's Answer: {user_answer}

Evaluate the student's answer and provide:
1. A score from 0-100 representing how well they answered (100 = perfect, 0 = completely wrong)
2. Whether the answer should be marked as correct (true/false) - be generous, if they demonstrate understanding mark as correct
3. Specific feedback on what was good and what could be improved

Consider:
- Did they capture the key concepts?
- Is the explanation accurate even if worded differently?
- Award partial credit for partially correct answers
- Ignore minor grammatical issues or filler words
- Focus on semantic understanding, not exact wording

Return ONLY valid JSON in this exact format:
{{
  "score": 85,
  "is_correct": true,
  "feedback": "Good answer! You correctly identified X and Y. However, you could improve by mentioning Z.",
  "key_concepts_covered": ["concept1", "concept2"],
  "key_concepts_missing": ["concept3"]
}}"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert educator. Evaluate answers fairly and provide constructive feedback. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        score = result.get("score", 0) / 100.0  # Convert to 0-1 scale
        is_correct = result.get("is_correct", score >= 0.65)
        feedback = result.get("feedback", "Answer evaluated.")

        logger.info(f"GPT Evaluation - Score: {score:.2f}, Correct: {is_correct}")

        return is_correct, score, feedback

    except Exception as e:
        logger.error(f"GPT evaluation error: {e}")
        # Fall back to embedding-based evaluation if GPT fails
        return None, None, None


async def evaluate_answer_similarity(
    user_answer: str,
    correct_answer: str,
    question: str = None
) -> tuple[bool, float]:
    """Evaluate answer similarity using hybrid approach: GPT + embeddings"""
    try:
        # Preprocess both answers
        user_answer_clean = preprocess_text(user_answer)
        correct_answer_clean = preprocess_text(correct_answer)

        logger.info(f"Original user answer: '{user_answer}'")
        logger.info(f"Cleaned user answer: '{user_answer_clean}'")

        # Try GPT-based evaluation first (more accurate)
        if question:
            gpt_is_correct, gpt_score, gpt_feedback = await evaluate_with_gpt(
                question, user_answer_clean, correct_answer_clean
            )

            if gpt_score is not None:
                logger.info(f"Using GPT evaluation: score={gpt_score:.2f}")
                return gpt_is_correct, gpt_score

        # Fallback to embedding-based similarity
        logger.info("Using embedding-based evaluation")
        user_embedding = await get_embedding(user_answer_clean)
        correct_embedding = await get_embedding(correct_answer_clean)

        # Calculate cosine similarity
        similarity = cosine_similarity(
            [user_embedding],
            [correct_embedding]
        )[0][0]

        logger.info(f"Embedding similarity: {similarity:.2f}")

        # Use lower threshold for preprocessed text
        settings = get_settings()
        is_correct = similarity >= settings.similarity_threshold

        return is_correct, float(similarity)

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
    try:
        # Log received parameters with print for immediate visibility
        print(f"Received params: deck_title={deck_title}, num={num_flashcards}, difficulty={difficulty_level}, type={question_type}, save_to_db={save_to_db}")
        print(f"File object: {file}, File filename: {file.filename if file else None}")
        print(f"Text content length: {len(text_content) if text_content else 0}")
        logger.info(f"Received params: deck_title={deck_title}, num={num_flashcards}, difficulty={difficulty_level}, type={question_type}, save_to_db={save_to_db}")
        logger.info(f"File object: {file}, File filename: {file.filename if file else None}")
        logger.info(f"Text content length: {len(text_content) if text_content else 0}")
        
        # Determine input source - check file first, then text
        # Process file input first (if provided)
        if file and hasattr(file, 'filename') and file.filename:
            # File input - extract text first
            try:
                logger.info(f"Processing file: {file.filename}")
                from app.ingest import extract_text_with_openai
                file_content = await file.read()
                if len(file_content) == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Uploaded file is empty"
                    )
                text_content = await extract_text_with_openai(file_content, file.filename)
                logger.info(f"Extracted {len(text_content)} characters from file")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error extracting text from file: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to process file: {str(e)}"
                )
        # Check text input (if file wasn't provided or file processing failed)
        elif text_content:
            # Normalize text_content - FastAPI Form(None) might return empty string
            text_content = text_content.strip() if text_content and text_content.strip() else None
            if text_content and len(text_content) > 0:
                # Text input - use directly
                logger.info(f"Using text input: {len(text_content)} characters")
            else:
                text_content = None
        
        # Final validation - ensure we have content
        if not text_content:
            logger.error("No content provided - neither file nor text content")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either provide text content or upload a file"
            )
        
        # Validate that we have text content after processing
        if not text_content or len(text_content.strip()) < 100:
            logger.error(f"Text content too short after processing: {len(text_content) if text_content else 0} characters")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Extracted content is too short. Please provide more content or upload a valid file."
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
                print(f"Creating deck: {deck_title}")
                logger.info(f"Creating deck: {deck_title}")
                deck_insert_result = db.service_client.table("decks").insert(deck_data).execute()
                deck = deck_insert_result.data[0] if deck_insert_result.data else None
                
                if not deck:
                    print("Failed to create deck in database")
                    logger.error("Failed to create deck in database")
                    raise Exception("Deck creation failed")
                
                print(f"Deck created with ID: {deck['id']}")
                logger.info(f"Deck created with ID: {deck['id']}")
                
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
                    print(f"Saving {len(flashcards_to_save)} flashcards to database...")
                    logger.info(f"Saving {len(flashcards_to_save)} flashcards to database...")
                    saved_result = db.service_client.table("flashcards").insert(flashcards_to_save).execute()
                    saved_cards = saved_result.data if saved_result.data else []
                    
                    print(f"Saved {len(saved_cards)} flashcards to deck {deck['id']}")
                    logger.info(f"Saved {len(saved_cards)} flashcards to deck {deck['id']}")
                    
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
                logger.error(f"Error saving to database: {e}")
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
    try:
        # Handle MCQ and True/False evaluation
        if request.question_type in [QuestionType.MCQ, QuestionType.TRUE_FALSE]:
            # For MCQ/TF, user_answer should be the option index (as string)
            try:
                user_option_index = int(request.user_answer)
                is_correct = user_option_index == request.correct_option_index
                similarity_score = 1.0 if is_correct else 0.0

                if is_correct:
                    feedback = "Correct! Well done."
                else:
                    if request.question_type == QuestionType.TRUE_FALSE:
                        correct_ans = "True" if request.correct_option_index == 0 else "False"
                        feedback = f"Incorrect. The correct answer is: {correct_ans}"
                    else:
                        feedback = f"Incorrect. The correct answer was option {request.correct_option_index}."

            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="For MCQ/True-False, user_answer must be the option index"
                )

        # Handle Free Response evaluation with improved GPT-based logic
        else:
            # Try GPT-based evaluation first if question is provided
            if request.question:
                user_answer_clean = preprocess_text(request.user_answer)
                correct_answer_clean = preprocess_text(request.correct_answer)

                gpt_is_correct, gpt_score, gpt_feedback = await evaluate_with_gpt(
                    request.question,
                    user_answer_clean,
                    correct_answer_clean
                )

                if gpt_score is not None:
                    # Use GPT evaluation results
                    is_correct = gpt_is_correct
                    similarity_score = gpt_score
                    feedback = gpt_feedback
                else:
                    # GPT failed, fall back to embeddings
                    is_correct, similarity_score = await evaluate_answer_similarity(
                        request.user_answer,
                        request.correct_answer,
                        request.question
                    )

                    # Generate improved feedback based on similarity
                    if is_correct:
                        feedback = "Excellent! Your answer demonstrates strong understanding of the concept."
                    elif similarity_score >= 0.55:
                        feedback = "Good effort! You're on the right track. Your answer captures some key points but could be more complete."
                    elif similarity_score >= 0.40:
                        feedback = "Partially correct. You've identified some aspects but missed important details. Review the material and try again."
                    else:
                        feedback = "Not quite right. Your answer doesn't align with the expected response. Please review the concept and try again."
            else:
                # No question provided, use basic embedding comparison
                is_correct, similarity_score = await evaluate_answer_similarity(
                    request.user_answer,
                    request.correct_answer,
                    None
                )

                # Generate feedback based on similarity
                if is_correct:
                    feedback = "Great job! Your answer is correct."
                elif similarity_score >= 0.55:
                    feedback = "Close! Your answer is partially correct. Consider adding more details."
                elif similarity_score >= 0.40:
                    feedback = "Your answer shows some understanding but needs improvement. Try to be more specific."
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
