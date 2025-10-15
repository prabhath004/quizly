from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from supabase import create_client, Client
import openai
import json
from numpy import dot
from numpy.linalg import norm

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)  # from env

# Flashcard models
class Flashcard(BaseModel):
    question: str
    answer: str
    category: Optional[str] = "General"
    difficulty: Optional[str] = "medium"
    tags: Optional[List[str]] = []

class FlashcardResponse(BaseModel):
    flashcards: List[Flashcard]

load_dotenv()
llm = ChatOpenAI(model="gpt-3.5-turbo")

# Generate flashcards from text (PDF/PPT)
def generate_flashcards_from_text(text: str) -> List[Flashcard]:
    prompt = f"""
    Generate flashcards from the following text. 
    Return the output as JSON with a list of flashcards containing:
    question, answer, category, difficulty, and tags.

    Text: {text}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    gpt_output = response.choices[0].message.content

    try:
        data = json.loads(gpt_output)
    except json.JSONDecodeError:
        raise ValueError("GPT output is not valid JSON")

    flashcards_response = FlashcardResponse(flashcards=data)
    return flashcards_response.flashcards


# Generate embeddings for semantic search
def generate_flashcard_embedding(text: str) -> list:
    response = openai.Embedding.create(
        model="text-embedding-3-small",
        input=text
    )
    return response["data"][0]["embedding"]

# Update your flashcards table to store embeddings:
# ALTER TABLE public.flashcards
# ADD COLUMN embedding vector(1536); -- if pgvector is enabled
# If pgvector isn’t enabled yet:
# CREATE EXTENSION IF NOT EXISTS vector;

# Save flashcards to Supabase
def save_flashcards_to_db(deck_id: str, flashcards: List[Flashcard]):
    records = []
    for fc in flashcards:
        text = fc.question + " " + fc.answer
        embedding = generate_flashcard_embedding(text)
        records.append({
            "deck_id": deck_id,
            "question": fc.question,
            "answer": fc.answer,
            "difficulty": fc.difficulty,
            "tags": fc.tags,
            "embedding": embedding
        })
    supabase.table("flashcards").insert(records).execute()


# Cosine similarity function
def cosine_similarity(a, b):
    return dot(a, b) / (norm(a) * norm(b))


# Evaluate user answer via embeddings
def evaluate_user_answer_with_embedding(correct_answer: str, user_answer: str, threshold: float = 0.80) -> dict:
    correct_emb = openai.embeddings.create(
        input=correct_answer,
        model="text-embedding-3-small"
    ).data[0].embedding

    user_emb = openai.embeddings.create(
        input=user_answer,
        model="text-embedding-3-small"
    ).data[0].embedding

    similarity = cosine_similarity(correct_emb, user_emb)
    is_correct = similarity >= threshold

    feedback = "Good job! Your answer conveys the correct idea." if is_correct else "Your answer missed some key points."

    return {
        "is_correct": is_correct,
        "similarity": round(similarity, 3),
        "feedback": feedback
    }

# Hybrid Mode both embeddings and GPT for detailed feedback when wrong

# def evaluate_user_answer(question, correct_answer, user_answer):
#     # Step 1: quick semantic check
#     emb_result = evaluate_user_answer_with_embedding(correct_answer, user_answer)
#
#     if emb_result["is_correct"]:
#         return emb_result  # no need GPT
#
#     # Step 2: detailed feedback via GPT
#     gpt_result = openai.ChatCompletion.create(
#         model="gpt-4-turbo",
#         messages=[{
#             "role": "user",
#             "content": f"Provide short feedback comparing:\nCorrect: {correct_answer}\nUser: {user_answer}"
#         }]
#     )
#
#     emb_result["feedback"] = gpt_result.choices[0].message.content.strip()
#     return emb_result


# Find similar flashcards using embeddings
def find_similar_flashcards(query: str, match_threshold: float = 0.8, match_count: int = 5):
    query_embedding = generate_flashcard_embedding(query)
    response = supabase.rpc(
        "match_flashcards", 
        {"query_embedding": query_embedding, "match_threshold": match_threshold, "match_count": match_count}
    ).execute()
    return response.data
# Need this if use the above
# create or replace function match_flashcards(
#   query_embedding vector(1536),
#   match_threshold float,
#   match_count int
# )
# returns table (
#   id uuid,
#   question text,
#   answer text,
#   similarity float
# )
# language sql stable as $$
#   select
#     id,
#     question,
#     answer,
#     1 - (flashcards.embedding <=> query_embedding) as similarity
#   from flashcards
#   where 1 - (flashcards.embedding <=> query_embedding) > match_threshold
#   order by similarity desc
#   limit match_count;
# $$;
