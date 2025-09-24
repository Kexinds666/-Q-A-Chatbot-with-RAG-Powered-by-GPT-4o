#!/bin/bash

# RAG Chatbot Development Startup Script
echo "🚀 Starting RAG Chatbot in Development Mode..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it from env.example"
    exit 1
fi

# Create necessary directories
mkdir -p data/chroma_db uploads processed logs

# Start AI Backend (Python FastAPI)
echo "📡 Starting AI Backend..."
cd ai-backend
python3 -m pip install -r requirements.txt --quiet
python3 main.py &
AI_BACKEND_PID=$!
cd ..

# Wait a moment for AI backend to start
sleep 3

# Start Interface Layer (Node.js)
echo "🔗 Starting Interface Layer..."
cd interface-layer
npm install --silent
npm run dev &
INTERFACE_PID=$!
cd ..

# Wait a moment for interface layer to start
sleep 3

# Start Frontend (React)
echo "🎨 Starting Frontend..."
cd frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ All services started!"
echo ""
echo "🌐 Access your RAG Chatbot:"
echo "   Frontend: http://localhost:3000"
echo "   Interface API: http://localhost:5000"
echo "   AI Backend API: http://localhost:8000"
echo ""
echo "📝 To stop all services, press Ctrl+C"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    kill $AI_BACKEND_PID $INTERFACE_PID $FRONTEND_PID 2>/dev/null
    echo "✅ All services stopped."
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Wait for user to stop
wait
