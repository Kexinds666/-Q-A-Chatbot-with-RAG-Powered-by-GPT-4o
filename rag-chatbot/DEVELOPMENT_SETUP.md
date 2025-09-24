# Development Setup (Without Docker)

If you prefer to run the services individually without Docker, follow these steps:

## Prerequisites

- Node.js 18+ 
- Python 3.11+
- PostgreSQL
- Redis

## 1. Install Dependencies

### Frontend
```bash
cd frontend
npm install
```

### Interface Layer
```bash
cd interface-layer
npm install
```

### AI Backend
```bash
cd ai-backend
pip install -r requirements.txt
```

## 2. Start Services

### Start PostgreSQL and Redis
```bash
# Using Homebrew on macOS
brew services start postgresql
brew services start redis
```

### Start AI Backend
```bash
cd ai-backend
python main.py
```

### Start Interface Layer
```bash
cd interface-layer
npm run dev
```

### Start Frontend
```bash
cd frontend
npm run dev
```

## 3. Access Application

- Frontend: http://localhost:3000
- Interface API: http://localhost:5000
- AI Backend API: http://localhost:8000

## 4. Test Upload

1. Go to http://localhost:3000
2. Click "Upload Document"
3. Select a PDF, TXT, or DOCX file
4. Wait for processing
5. Start chatting with your document!
