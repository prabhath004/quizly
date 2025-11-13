#!/bin/bash

# Quizly - Start Both Backend and Frontend

echo "Starting Quizly..."
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Setup backend
echo "Setting up Backend..."
cd "$SCRIPT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Check for ffmpeg (required for audio processing)
if ! command -v ffmpeg &> /dev/null; then
    echo ""
    echo " WARNING: ffmpeg not found. Audio processing features may not work."
    echo "   Install with: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
    echo ""
fi

# Start backend in background
echo "Starting Backend on port 8000..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 3

# Setup frontend
echo "Setting up Frontend..."
cd "$SCRIPT_DIR/Frontend"

# Install frontend dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing Frontend dependencies..."
    npm install
fi

# Start frontend in background
echo "Starting Frontend on port 8080..."
npm run dev &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "Both servers started!"
echo ""
echo "Access Points:"
echo "   Frontend:  http://localhost:8080"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
