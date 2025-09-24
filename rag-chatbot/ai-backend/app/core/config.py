"""
Configuration settings for the RAG Chatbot AI Backend
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "RAG Chatbot AI Backend"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    
    # API Keys
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/rag_chatbot"
    REDIS_URL: str = "redis://localhost:6379"
    
    # Vector Database
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "documents"
    
    # Document Processing
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    BATCH_SIZE: int = 100
    
    # Chat Configuration
    MAX_CHAT_HISTORY: int = 10
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 2000
    
    # Retrieval Configuration
    TOP_K_RESULTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    BM25_WEIGHT: float = 0.3
    VECTOR_WEIGHT: float = 0.7
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5000"]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    PROCESSED_DIR: str = "./processed"
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("OPENAI_API_KEY")
    def validate_openai_key(cls, v):
        if not v:
            raise ValueError("OPENAI_API_KEY is required")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
