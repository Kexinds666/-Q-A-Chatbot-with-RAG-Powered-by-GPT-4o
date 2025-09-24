#!/usr/bin/env python3
"""
Full Production RAG Chatbot Backend
FastAPI application with enterprise-grade features
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging
from app.middleware.error_handler import setup_error_handlers
from app.middleware.rate_limiter import setup_rate_limiting
from app.api.routes import health, documents, chat, auth
from app.services.vector_service import VectorService
from app.services.document_service import DocumentService
from app.services.chat_service import ChatService

# Setup logging
setup_logging()
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting RAG Chatbot Backend...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize services
    app.state.vector_service = VectorService()
    app.state.document_service = DocumentService()
    app.state.chat_service = ChatService()
    logger.info("Services initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RAG Chatbot Backend...")

# Create FastAPI application
app = FastAPI(
    title="RAG Chatbot API",
    description="Production-ready RAG-powered intelligent Q&A chatbot",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Setup error handlers
setup_error_handlers(app)

# Setup rate limiting
setup_rate_limiting(app)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RAG Chatbot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "disabled"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )
