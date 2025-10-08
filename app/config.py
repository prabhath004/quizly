"""
Quizly Backend - Configuration and Settings
Centralized configuration management using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Supabase Configuration
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    
    # OpenAI Configuration
    openai_api_key: str
    
    # FastAPI Configuration
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Database Configuration
    database_url: Optional[str] = None
    
    # Application Settings
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    
    # File Upload Settings
    max_file_size_mb: int = 50
    allowed_file_types: str = "pdf,pptx,txt"
    
    # AI Settings
    embedding_model: str = "text-embedding-ada-002"
    flashcard_model: str = "gpt-3.5-turbo"
    similarity_threshold: float = 0.8
    
    # Spaced Repetition Settings
    initial_interval_hours: int = 24
    easy_multiplier: float = 2.5
    hard_multiplier: float = 1.3
    max_interval_days: int = 365
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency to get settings"""
    return settings
