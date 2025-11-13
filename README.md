# Quizly - AI-Powered Flashcard Generator

An intelligent flashcard generation platform with FastAPI backend and React frontend. Generate flashcards from PDFs or text using OpenAI's GPT-4o.

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- ffmpeg (for audio processing) - Install with `brew install ffmpeg` (macOS) or `apt-get install ffmpeg` (Linux)
- `.env` file with your Supabase and OpenAI credentials (see `env.example`)

---

## Backend Setup

1. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Start the backend server**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## Frontend Setup

1. **Navigate to frontend directory**
```bash
cd Frontend
```

2. **Install dependencies**
```bash
npm install
```

3. **Start the development server**
```bash
npm run dev
```

The frontend will be available at:
- **Frontend**: http://localhost:8080 (or the port shown in terminal)

---

## Start Both Servers (Alternative)

You can start both backend and frontend with one command:

```bash
./start-all.sh
```

This script will:
- Start the backend on port 8000
- Start the frontend on port 8080
- Display both access URLs

---

## Features

- Generate flashcards from PDFs or text using AI
- Create decks manually with custom flashcards
- Edit existing decks and flashcards
- Multiple question types: MCQ, True/False, Free Response
- AI-powered answer evaluation
- User authentication with JWT
- Speech-to-text support for free response
- Deck management and study sessions

---

## Configuration

Make sure your `.env` file contains:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_KEY`
- `OPENAI_API_KEY`
- `JWT_SECRET_KEY`

See `env.example` for reference.

---

## Database Schema

The application requires the following database columns:
- `decks.order_index` - For folder-based deck ordering and podcast autoplay
- `flashcards.audio_url` - For voice mnemonic recordings

These should already be set up in your Supabase database. If you're setting up a new database, ensure these columns exist.

---

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation.

---
