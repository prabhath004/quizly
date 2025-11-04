from supabase import create_client, Client
from app.config import get_settings
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Supabase client wrapper for database operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client: Client = create_client(
            self.settings.supabase_url,
            self.settings.supabase_anon_key
        )
        self.service_client: Client = create_client(
            self.settings.supabase_url,
            self.settings.supabase_service_role_key
        )
    
    async def test_connection(self) -> bool:
        """Test database connection"""
        try:
            # Simple query to test connection
            result = self.client.table("users").select("id").limit(1).execute()
            logger.info("Supabase connection successful")
            return True
        except Exception as e:
            logger.error(f"Supabase connection failed: {e}")
            return False
    
    # User operations
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        try:
            result = self.client.auth.sign_up(user_data)
            return result.user.__dict__ if result.user else None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            result = self.client.table("users").select("*").eq("id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user"""
        try:
            result = self.client.table("users").update(update_data).eq("id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return None
    
    # Deck operations
    async def create_deck(self, deck_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new deck"""
        try:
            result = self.client.table("decks").insert(deck_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating deck: {e}")
            return None
    
    async def get_user_decks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all decks for a user"""
        try:
            result = self.client.table("decks").select("*").eq("user_id", user_id).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting user decks: {e}")
            return []
    
    async def get_deck(self, deck_id: str) -> Optional[Dict[str, Any]]:
        """Get deck by ID"""
        try:
            result = self.client.table("decks").select("*").eq("id", deck_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting deck: {e}")
            return None
    
    async def update_deck(self, deck_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update deck"""
        try:
            result = self.client.table("decks").update(update_data).eq("id", deck_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating deck: {e}")
            return None
    
    async def delete_deck(self, deck_id: str) -> bool:
        """Delete deck"""
        try:
            self.client.table("decks").delete().eq("id", deck_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting deck: {e}")
            return False
    
    # Flashcard operations
    async def create_flashcard(self, flashcard_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new flashcard"""
        try:
            result = self.client.table("flashcards").insert(flashcard_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating flashcard: {e}")
            return None
    
    async def create_flashcards_batch(self, flashcards_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple flashcards in batch"""
        try:
            result = self.client.table("flashcards").insert(flashcards_data).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error creating flashcards batch: {e}")
            return []
    
    async def get_deck_flashcards(self, deck_id: str) -> List[Dict[str, Any]]:
        """Get all flashcards for a deck"""
        try:
            result = self.client.table("flashcards").select("*").eq("deck_id", deck_id).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting deck flashcards: {e}")
            return []
    
    async def get_flashcard(self, flashcard_id: str) -> Optional[Dict[str, Any]]:
        """Get flashcard by ID"""
        try:
            result = self.client.table("flashcards").select("*").eq("id", flashcard_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting flashcard: {e}")
            return None
    
    async def update_flashcard(self, flashcard_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update flashcard"""
        try:
            result = self.client.table("flashcards").update(update_data).eq("id", flashcard_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating flashcard: {e}")
            return None
    
    async def delete_flashcard(self, flashcard_id: str) -> bool:
        """Delete flashcard"""
        try:
            self.client.table("flashcards").delete().eq("id", flashcard_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting flashcard: {e}")
            return False
    
    # Session operations
    async def create_session(self, session_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new study session"""
        try:
            result = self.client.table("sessions").insert(session_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None
    
    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        try:
            result = self.client.table("sessions").select("*").eq("user_id", user_id).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        try:
            result = self.client.table("sessions").select("*").eq("id", session_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None
    
    async def update_session(self, session_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update session"""
        try:
            result = self.client.table("sessions").update(update_data).eq("id", session_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return None
    
    # Embedding operations
    async def get_embedding_by_hash(self, text_hash: str) -> Optional[Dict[str, Any]]:
        """Get embedding by text hash"""
        try:
            result = self.client.table("embeddings").select("*").eq("text_hash", text_hash).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting embedding by hash: {e}")
            return None
    
    async def create_embedding(self, embedding_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new embedding"""
        try:
            result = self.client.table("embeddings").insert(embedding_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return None
    
    async def get_embedding_by_text(self, text_content: str) -> Optional[Dict[str, Any]]:
        """Get embedding by exact text content"""
        try:
            result = self.client.table("embeddings").select("*").eq("text_content", text_content).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting embedding by text: {e}")
            return None


# Global database instance
db = SupabaseClient()


async def init_db():
    """Initialize database connection"""
    logger.info("Initializing database connection...")
    success = await db.test_connection()
    if success:
        logger.info("Database initialized successfully")
    else:
        logger.error("Database initialization failed")
    return success
