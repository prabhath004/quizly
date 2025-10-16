"""
Database connection module for Supabase
"""

from supabase import create_client, Client
from app.config import settings
from typing import Generator


def get_supabase() -> Generator[Client, None, None]:
    """
    Dependency to get Supabase client.
    Used with FastAPI's Depends() for dependency injection.
    """
    supabase: Client = create_client(
        settings.supabase_url,
        settings.supabase_service_role_key  # Use service role for backend operations
    )
    try:
        yield supabase
    finally:
        # Cleanup if needed (Supabase client doesn't need explicit cleanup)
        pass


def get_supabase_client() -> Client:
    """
    Get a Supabase client instance directly.
    Use this for non-FastAPI contexts.
    """
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key
    )