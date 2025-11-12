"""
Quizly Backend - Shared Models and Schemas
Pydantic models for data validation and serialization
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class DifficultyLevel(str, Enum):
    """Difficulty levels for flashcards"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionType(str, Enum):
    """Question types for flashcards"""
    MCQ = "mcq"  # Multiple Choice Question (4 options)
    TRUE_FALSE = "true_false"  # True/False question
    FREE_RESPONSE = "free_response"  # Open-ended question


# User Models
class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """User update model"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class User(UserBase):
    """User model"""
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Folder Models
class FolderBase(BaseModel):
    """Base folder model"""
    name: str = Field(..., min_length=1, max_length=200)


class FolderCreate(FolderBase):
    """Folder creation model"""
    pass


class FolderUpdate(BaseModel):
    """Folder update model"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)


class Folder(FolderBase):
    """Folder model"""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    deck_count: int = 0
    
    class Config:
        from_attributes = True


# Deck Models
class DeckBase(BaseModel):
    """Base deck model"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)


class DeckCreate(DeckBase):
    """Deck creation model"""
    folder_id: Optional[str] = None


class DeckUpdate(BaseModel):
    """Deck update model"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    folder_id: Optional[str] = None
    order_index: Optional[int] = None  # Order within folder


class Deck(DeckBase):
    """Deck model"""
    id: str
    user_id: str
    folder_id: Optional[str] = None
    order_index: Optional[int] = None  # Order within folder (only used when folder_id is not None)
    created_at: datetime
    updated_at: datetime
    flashcard_count: int = 0
    podcast_audio_url: Optional[str] = None
    
    class Config:
        from_attributes = True


# Flashcard Models
class FlashcardBase(BaseModel):
    """Base flashcard model"""
    question: str = Field(..., min_length=1, max_length=1000)
    answer: str = Field(..., min_length=1, max_length=2000)
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    question_type: QuestionType = QuestionType.FREE_RESPONSE
    mcq_options: Optional[List[str]] = None  # For MCQ: list of 4 options
    correct_option_index: Optional[int] = None  # For MCQ: index of correct answer (0-3)
    tags: Optional[List[str]] = Field(default_factory=list)


class FlashcardCreate(FlashcardBase):
    """Flashcard creation model"""
    deck_id: str


class FlashcardUpdate(BaseModel):
    """Flashcard update model"""
    question: Optional[str] = Field(None, min_length=1, max_length=1000)
    answer: Optional[str] = Field(None, min_length=1, max_length=2000)
    difficulty: Optional[DifficultyLevel] = None
    question_type: Optional[QuestionType] = None
    mcq_options: Optional[List[str]] = None
    correct_option_index: Optional[int] = None
    tags: Optional[List[str]] = None
    audio_url: Optional[str] = None  # URL to voice mnemonic recording


class Flashcard(FlashcardBase):
    """Flashcard model"""
    id: str
    deck_id: str
    created_at: datetime
    updated_at: datetime
    audio_url: Optional[str] = None  # URL to voice mnemonic recording
    
    class Config:
        from_attributes = True


# Session Models
class SessionBase(BaseModel):
    """Base session model"""
    deck_id: str


class SessionCreate(SessionBase):
    """Session creation model"""
    pass


class SessionUpdate(BaseModel):
    """Session update model"""
    status: Optional[str] = None
    total_cards: Optional[int] = None
    correct_answers: Optional[int] = None
    incorrect_answers: Optional[int] = None


class Session(SessionBase):
    """Session model"""
    id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_cards: int = 0
    correct_answers: int = 0
    incorrect_answers: int = 0
    
    class Config:
        from_attributes = True


# AI Models
class FlashcardGenerationRequest(BaseModel):
    """Request model for AI flashcard generation"""
    text_content: str = Field(..., min_length=100)
    deck_title: str = Field(..., min_length=1, max_length=200)
    difficulty_level: DifficultyLevel = DifficultyLevel.MEDIUM
    num_flashcards: int = Field(10, ge=1, le=50)
    question_type: QuestionType = QuestionType.FREE_RESPONSE  # Default to free response


class FlashcardGenerationResponse(BaseModel):
    """Response model for AI flashcard generation"""
    flashcards: List[FlashcardCreate]
    processing_time: float
    tokens_used: int


class AnswerEvaluationRequest(BaseModel):
    """Request model for answer evaluation"""
    user_answer: str = Field(..., min_length=1)
    correct_answer: str = Field(..., min_length=1)
    question_type: QuestionType = QuestionType.FREE_RESPONSE
    question: Optional[str] = None  # For GPT-based evaluation context
    correct_option_index: Optional[int] = None  # For MCQ validation


class AnswerEvaluationResponse(BaseModel):
    """Response model for answer evaluation"""
    is_correct: bool
    similarity_score: float
    feedback: str


# File Upload Models
class FileUploadResponse(BaseModel):
    """Response model for file upload"""
    file_id: str
    filename: str
    file_size: int
    content_type: str
    upload_url: str


# Removed TextExtractionResponse - no longer needed since extract_text_from_file endpoint was removed


# Authentication Models
class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Token model"""
    access_token: str
    token_type: str = "bearer"
    user: Optional[User] = None


class TokenData(BaseModel):
    """Token data model"""
    user_id: Optional[str] = None


# Error Models
class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    status_code: int


# Reorder Models
class DeckReorderRequest(BaseModel):
    """Request model for reordering decks in a folder"""
    deck_order: List[str]  # List of deck IDs in desired order
