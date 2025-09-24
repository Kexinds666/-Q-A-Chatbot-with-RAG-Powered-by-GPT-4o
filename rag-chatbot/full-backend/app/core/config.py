"""
Configuration settings for the RAG Chatbot Backend
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator, Field


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Application
    APP_NAME: str = "RAG Chatbot API"
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    ALLOWED_ORIGINS: List[str] = Field(default=["*"], env="ALLOWED_ORIGINS")
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    REDIS_URL: str = Field(..., env="REDIS_URL")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-large", env="OPENAI_EMBEDDING_MODEL")
    OPENAI_TEMPERATURE: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    OPENAI_MAX_TOKENS: int = Field(default=2000, env="OPENAI_MAX_TOKENS")
    
    # Vector Database
    CHROMA_PERSIST_DIRECTORY: str = Field(default="./data/chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    CHROMA_COLLECTION_NAME: str = Field(default="documents", env="CHROMA_COLLECTION_NAME")
    
    # Document Processing
    CHUNK_SIZE: int = Field(default=1000, env="CHUNK_SIZE")
    CHUNK_OVERLAP: int = Field(default=200, env="CHUNK_OVERLAP")
    BATCH_SIZE: int = Field(default=100, env="BATCH_SIZE")
    MAX_FILE_SIZE: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB
    
    # File Upload
    UPLOAD_DIR: str = Field(default="./uploads", env="UPLOAD_DIR")
    PROCESSED_DIR: str = Field(default="./processed", env="PROCESSED_DIR")
    
    # Retrieval Configuration
    TOP_K_RESULTS: int = Field(default=5, env="TOP_K_RESULTS")
    SIMILARITY_THRESHOLD: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    BM25_WEIGHT: float = Field(default=0.3, env="BM25_WEIGHT")
    VECTOR_WEIGHT: float = Field(default=0.7, env="VECTOR_WEIGHT")
    
    # Chat Configuration
    MAX_CHAT_HISTORY: int = Field(default=10, env="MAX_CHAT_HISTORY")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    # JWT Configuration
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [host.strip() for host in v.split(",")]
        return v
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("MAX_FILE_SIZE")
    def validate_file_size(cls, v):
        if v <= 0:
            raise ValueError("MAX_FILE_SIZE must be positive")
        return v
    
    @validator("CHUNK_SIZE")
    def validate_chunk_size(cls, v):
        if v <= 0:
            raise ValueError("CHUNK_SIZE must be positive")
        return v
    
    @validator("CHUNK_OVERLAP")
    def validate_chunk_overlap(cls, v):
        if v < 0:
            raise ValueError("CHUNK_OVERLAP must be non-negative")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
