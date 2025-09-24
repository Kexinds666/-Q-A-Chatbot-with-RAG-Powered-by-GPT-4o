"""
RAG Chatbot AI Backend Service
FastAPI application with LangChain integration for document processing and chat
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import structlog

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging
from app.services.document_service import DocumentService
from app.services.chat_service import ChatService
from app.services.vector_service import VectorService
from app.api.routes import documents, chat, health
from app.middleware.error_handler import setup_error_handlers
from app.middleware.rate_limiter import RateLimiterMiddleware

# Setup logging
setup_logging()
logger = structlog.get_logger()

# Global services
document_service: Optional[DocumentService] = None
chat_service: Optional[ChatService] = None
vector_service: Optional[VectorService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global document_service, chat_service, vector_service
    
    logger.info("Starting RAG Chatbot AI Backend Service")
    
    # Initialize database
    await init_db()
    
    # Initialize services
    vector_service = VectorService()
    await vector_service.initialize()
    
    document_service = DocumentService(vector_service)
    chat_service = ChatService(vector_service)
    
    logger.info("All services initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down services")
    if vector_service:
        await vector_service.cleanup()


# Create FastAPI app
app = FastAPI(
    title="RAG Chatbot AI Backend",
    description="AI-powered document processing and chat service with RAG",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RateLimiterMiddleware)

# Setup error handlers
setup_error_handlers(app)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RAG Chatbot AI Backend Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/docs")
async def api_docs():
    """API documentation endpoint"""
    return {
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json"
    }


# Dependency injection for services
def get_document_service() -> DocumentService:
    if document_service is None:
        raise HTTPException(status_code=503, detail="Document service not initialized")
    return document_service


def get_chat_service() -> ChatService:
    if chat_service is None:
        raise HTTPException(status_code=503, detail="Chat service not initialized")
    return chat_service


def get_vector_service() -> VectorService:
    if vector_service is None:
        raise HTTPException(status_code=503, detail="Vector service not initialized")
    return vector_service


# Make services available to routers
app.dependency_overrides[get_document_service] = get_document_service
app.dependency_overrides[get_chat_service] = get_chat_service
app.dependency_overrides[get_vector_service] = get_vector_service


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
