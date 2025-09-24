# Production-Ready RAG-Powered Q&A Chatbot

A high-performance, full-stack RAG-powered intelligent Q&A chatbot built with modern technologies.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │ Node.js Interface│    │ Python AI Backend│
│                 │    │                 │    │                 │
│ - Real-time Chat│◄──►│ - Express.js    │◄──►│ - FastAPI       │
│ - Modern UI     │    │ - API Gateway   │    │ - LangChain     │
│ - WebSocket     │    │ - Load Balancer │    │ - GPT-4o        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Redis Cache   │    │ Vector Database │
                       │                 │    │                 │
                       │ - Session Store │    │ - ChromaDB      │
                       │ - Rate Limiting │    │ - Embeddings    │
                       └─────────────────┘    └─────────────────┘
```

## Tech Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for modern styling
- **Socket.io-client** for real-time communication
- **React Query** for state management

### Interface Layer
- **Node.js** with **Express.js**
- **Socket.io** for WebSocket connections
- **Redis** for caching and session management
- **Rate limiting** and **authentication**

### AI Backend Service
- **Python 3.11** with **FastAPI**
- **LangChain** for RAG pipeline
- **OpenAI GPT-4o** for language generation
- **ChromaDB** for vector storage
- **BM25** for hybrid retrieval

### Document Processing
- **PyPDF2** for PDF parsing
- **LangChain Text Splitters** for intelligent chunking
- **OpenAI Embeddings** for vectorization
- **Batch processing** for efficiency

### Infrastructure
- **Docker** containerization
- **Docker Compose** for orchestration
- **k6** for load testing
- **RAGAS** for quality evaluation

## Features

- 🚀 **High Performance**: Supports 500+ requests per second
- 🔍 **Hybrid Retrieval**: Combines BM25 keyword search with vector similarity
- 📄 **Multi-format Support**: PDF, TXT, DOCX document processing
- 💬 **Real-time Chat**: WebSocket-based instant messaging
- 🧠 **Intelligent Chunking**: Context-aware text segmentation
- 📊 **Quality Evaluation**: RAGAS framework for RAG assessment
- 🔒 **Production Ready**: Rate limiting, caching, error handling
- 📈 **Monitoring**: Comprehensive logging and metrics

## Quick Start

1. **Clone and Setup**
```bash
git clone <repository>
cd rag-chatbot
```

2. **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

3. **One-Command Deployment**
```bash
docker-compose up -d
```

4. **Access the Application**
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/docs
- Interface Layer: http://localhost:5000

## Performance Testing

```bash
# Run k6 load tests
npm run test:load
```

## Quality Evaluation

```bash
# Run RAGAS evaluation
python scripts/evaluate_rag.py
```

## Development

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up
```

## License

MIT License
