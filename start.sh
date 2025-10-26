#!/bin/bash
# Script to activate virtual environment and run Quizly Backend

echo "🚀 Activating Quizly Backend Virtual Environment..."
source venv/bin/activate

echo "✅ Virtual environment activated!"
echo "📦 All dependencies installed:"
echo "   - FastAPI, Uvicorn"
echo "   - Supabase, OpenAI"
echo "   - Pydantic, NumPy, Scikit-learn"
echo "   - Python-dotenv, and more!"

echo ""
echo "🎯 To run the backend:"
echo "   python main.py"
echo ""
echo "🎯 To run with auto-reload:"
echo "   uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "📚 API docs will be available at:"
echo "   http://localhost:8000/docs"
