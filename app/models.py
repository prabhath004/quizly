"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# Authentication Models
class UserCreate(BaseModel):
    """Model for user registration"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """Model for user login"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Model for JWT token response"""
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    user: Optional[dict] = None


class UserResponse(BaseModel):
    """Model for user data response"""
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: Optional[datetime] = None


# Deck Models
class DeckCreate(BaseModel):
    """Model for creating a deck"""
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None


class DeckResponse(BaseModel):
    """Model for deck response"""
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    user_id: str
    created_at: datetime


# Flashcard Models
class FlashcardCreate(BaseModel):
    """Model for creating a flashcard"""
    deck_id: str
    question: str
    answer: str
    difficulty: Optional[str] = "medium"
    card_type: Optional[str] = "flashcard"


class FlashcardResponse(BaseModel):
    """Model for flashcard response"""
    id: str
    deck_id: str
    question: str
    answer: str
    difficulty: str
    card_type: str
    created_at: datetime


# Study Session Models
class SessionCreate(BaseModel):
    """Model for creating a study session"""
    deck_id: str
    session_length: Optional[int] = 10  # Number of cards


class SessionResponse(BaseModel):
    """Model for session response"""
    id: str
    deck_id: str
    user_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None


# Answer Submission
class AnswerSubmit(BaseModel):
    """Model for submitting an answer"""
    session_id: str
    flashcard_id: str
    user_answer: str
    
    
class AnswerResult(BaseModel):
    """Model for answer evaluation result"""
    is_correct: bool
    similarity_score: float
    feedback: Optional[str] = None