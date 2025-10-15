from fastapi import APIRouter
from pydantic import BaseModel
from controllers.flashcard_controller import evaluate_answer_controller

router = APIRouter()

class EvaluateRequest(BaseModel):
    flashcard_id: str
    user_answer: str
    session_id: str

@router.post("/evaluate-answer")
def evaluate_answer(data: EvaluateRequest):
    return evaluate_answer_controller(data)


# Purpose: Connects the frontend to your backend.
    # Defines HTTP endpoints (POST, GET, etc.) using FastAPI.
    # Validates input using Pydantic models.
    # Calls controller functions and returns responses.