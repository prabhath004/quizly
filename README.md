# 🧠 Quizly - AI-Powered Flashcard Generator

A FastAPI backend that generates intelligent flashcards from PDF documents using OpenAI's GPT-4o. Supports both **Multiple Choice Questions (MCQ)** and **Free Response** questions with AI-powered answer evaluation.

## ✨ Features

- 📄 **PDF Processing**: Upload PDFs and extract intelligent summaries
- 🤖 **AI Flashcard Generation**: Create MCQ and Free Response questions
- 🎯 **Smart Answer Evaluation**: AI-powered evaluation using embeddings
- 🔐 **User Authentication**: JWT-based auth with Supabase
- 📊 **Study Sessions**: Track learning progress
- 🎤 **Speech-to-Text Ready**: Frontend can integrate Web Speech API

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Team environment file (`.env`) - **Already configured**
- Supabase database - **Already set up**

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd quizly2
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Setup** ✅
   - Environment variables are already configured
   - Supabase database is already set up
   - No additional configuration needed

5. **Start the server**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

6. **Access the API**
- **Swagger UI**: http://localhost:8000/docs
- **API Base**: http://localhost:8000/api

## 📚 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user

### AI Services
- `POST /api/ai/generate-flashcards` - Generate flashcards from PDF/text
- `POST /api/ai/evaluate-answer` - Evaluate user answers
- `POST /api/ai/get-embedding` - Get text embeddings

### File Processing
- `POST /api/ingest/upload` - Upload files to Supabase Storage

### Study Sessions
- `POST /api/sessions/create` - Create study session
- `GET /api/sessions/my-sessions` - Get user sessions
- `POST /api/sessions/{session_id}/submit-answer` - Submit answer
- `POST /api/sessions/{session_id}/end` - End session

## 🎯 Usage Examples

### Generate MCQ Flashcards
```bash
curl -X POST "http://localhost:8000/api/ai/generate-flashcards" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@document.pdf" \
  -F "question_type=mcq" \
  -F "num_flashcards=5" \
  -F "difficulty_level=medium"
```

### Generate Free Response Flashcards
```bash
curl -X POST "http://localhost:8000/api/ai/generate-flashcards" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@document.pdf" \
  -F "question_type=free_response" \
  -F "num_flashcards=5"
```

### Evaluate MCQ Answer
```bash
curl -X POST "http://localhost:8000/api/ai/evaluate-answer" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_answer": "2",
    "correct_answer": "Paris is the capital of France",
    "question_type": "mcq",
    "correct_option_index": 2
  }'
```

### Evaluate Free Response Answer
```bash
curl -X POST "http://localhost:8000/api/ai/evaluate-answer" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_answer": "Paris is the capital city of France",
    "correct_answer": "Paris is the capital of France",
    "question_type": "free_response"
  }'
```

## 🏗️ Project Structure

```
quizly2/
├── app/
│   ├── __init__.py
│   ├── ai.py              # AI services (flashcard generation, evaluation)
│   ├── auth.py            # Authentication & JWT handling
│   ├── config.py          # Configuration & settings
│   ├── database.py        # Supabase database operations
│   ├── ingest.py          # File processing & PDF analysis
│   ├── models.py          # Pydantic models & schemas
│   └── sessions.py        # Study session management
├── main.py                # FastAPI application entry point
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
├── start.sh              # Quick start script
└── README.md             # This file
```

## 🔧 Configuration

### Environment Variables ✅
- All environment variables are **already configured**
- Supabase connection is **already set up**
- OpenAI API key is **already configured**
- JWT secret key is **already set up**

### Supabase Database ✅
- All required tables are **already created**
- MCQ support is **already implemented**
- Database schema is **ready to use**

## 🎤 Frontend Integration

This backend is ready for frontend integration with:

- **Web Speech API** for speech-to-text in free response questions
- **REST API** for all flashcard operations
- **JWT Authentication** for user management
- **Real-time feedback** for answer evaluation

## 👥 Team Development

This is a **team project** with shared infrastructure:

- **Environment**: Already configured with Supabase keys
- **Database**: Supabase already set up and ready
- **API Keys**: All necessary keys already configured
- **Deployment**: Ready for team deployment

### For Team Members:
1. Clone the repository
2. Create virtual environment
3. Install dependencies
4. Start developing!

### Adding New Features:
1. Create feature branch
2. Implement changes
3. Test with existing infrastructure
4. Submit pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

If you encounter any issues:
1. Check the Swagger UI at `/docs`
2. Verify your team's environment setup
3. Contact team members for database access
4. Check the logs for detailed error messages

---

**Team Quizly - Happy Learning! 🎓**