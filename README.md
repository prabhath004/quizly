# Quizly Backend 🧠

A smart AI-powered flashcard application with voice-based learning built with FastAPI and Supabase.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Git

### 1. Clone and Setup
```bash
# Navigate to project directory
cd /Users/prabhathpalakurthi/Desktop/quizly2

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup
```bash
# Copy environment template
cp env.example .env

# Edit .env file with your actual values
# - Add your OpenAI API key
# - Generate a secret key for JWT tokens
```

### 3. Run the Application
```bash
# Start the development server
python main.py

# Or use uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the API
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Root Endpoint**: http://localhost:8000/

## 📁 Project Structure

```
quizly2/
├── app/                    # Application modules
│   ├── __init__.py        # App initialization
│   ├── config.py          # Configuration settings
│   ├── models.py          # Pydantic models
│   ├── database.py        # Database connection
│   ├── auth.py            # Authentication
│   ├── ingest.py          # File processing
│   ├── ai.py              # AI services
│   └── sessions.py        # Study sessions
├── main.py                # FastAPI application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## 🔧 Configuration

### Environment Variables
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Supabase anonymous key
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
- `OPENAI_API_KEY`: OpenAI API key for AI features
- `SECRET_KEY`: JWT secret key

### Supabase Setup
- ✅ Database tables created
- ✅ Row Level Security enabled
- ✅ Authentication configured
- ✅ Storage bucket created

## 🧠 Features

- **AI-Powered Flashcards**: Generate flashcards from PDFs/PPTs
- **Voice-Based Learning**: Answer questions by speaking
- **Spaced Repetition**: Smart review scheduling
- **Secure Authentication**: User-specific data access
- **File Processing**: Extract text from various formats

## 🛠️ Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
flake8 .
```

### Database Migrations
```bash
# Run SQL migrations in Supabase dashboard
# or use Supabase CLI
```

## 📚 API Endpoints

- `GET /health` - Health check
- `GET /docs` - API documentation
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/ingest/upload` - File upload
- `POST /api/ai/generate-flashcards` - Generate flashcards
- `POST /api/sessions/create` - Create study session

## 🚀 Deployment

### Local Development
```bash
python main.py
```

### Production
- Deploy to Render, Railway, or similar
- Set environment variables
- Configure CORS for production domain

## 📝 License

MIT License - see LICENSE file for details
