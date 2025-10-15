from ai.ai import evaluate_user_answer_with_embedding
from supabase import create_client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def evaluate_answer_controller(data):
    flashcard_res = supabase.table("flashcards").select("question, answer").eq("id", data.flashcard_id).execute()
    flashcard = flashcard_res.data[0]
    result = evaluate_user_answer_with_embedding(flashcard["answer"], data.user_answer)
    
    supabase.table("session_results").insert({
        "session_id": data.session_id,
        "flashcard_id": data.flashcard_id,
        "user_answer": data.user_answer,
        "is_correct": result["is_correct"],
        "feedback": result["feedback"]
    }).execute()
    
    return result

# Purpose: Orchestrates AI + database + other operations.
    # Takes the raw input from routes (frontend) and decides what to do.
    # Calls functions from ai.py and interacts with the database.
    # Returns structured data to the route.