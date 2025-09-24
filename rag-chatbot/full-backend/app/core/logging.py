"""
Logging configuration for the RAG Chatbot Backend
"""

import logging
import sys
from typing import Any, Dict
import structlog
from structlog.stdlib import LoggerFactory
from app.core.config import settings


def setup_logging() -> structlog.BoundLogger:
    """Setup structured logging"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
    
    # Set log levels for external libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    return structlog.get_logger()


# Global logger instance
logger = setup_logging()


class LoggingMiddleware:
    """Custom logging middleware for FastAPI"""
    
    def __init__(self, app):
        self.app = app
        self.logger = logger
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Log request
            request_id = scope.get("request_id", "unknown")
            method = scope["method"]
            path = scope["path"]
            
            self.logger.info(
                "Request started",
                request_id=request_id,
                method=method,
                path=path,
                client=scope.get("client"),
            )
            
            # Process request
            await self.app(scope, receive, send)
            
            # Log response (would need response status from send callback)
            self.logger.info(
                "Request completed",
                request_id=request_id,
                method=method,
                path=path,
            )
        else:
            await self.app(scope, receive, send)


def log_api_call(
    endpoint: str,
    method: str,
    user_id: int = None,
    status_code: int = None,
    response_time: float = None,
    token_usage: int = None,
    **kwargs
):
    """Log API call with structured data"""
    logger.info(
        "API call",
        endpoint=endpoint,
        method=method,
        user_id=user_id,
        status_code=status_code,
        response_time=response_time,
        token_usage=token_usage,
        **kwargs
    )


def log_document_processing(
    document_id: int,
    filename: str,
    status: str,
    processing_time: float = None,
    chunk_count: int = None,
    error: str = None,
    **kwargs
):
    """Log document processing events"""
    logger.info(
        "Document processing",
        document_id=document_id,
        filename=filename,
        status=status,
        processing_time=processing_time,
        chunk_count=chunk_count,
        error=error,
        **kwargs
    )


def log_chat_interaction(
    session_id: int,
    user_id: int,
    message_count: int,
    response_time: float = None,
    token_usage: int = None,
    retrieved_chunks: int = None,
    **kwargs
):
    """Log chat interactions"""
    logger.info(
        "Chat interaction",
        session_id=session_id,
        user_id=user_id,
        message_count=message_count,
        response_time=response_time,
        token_usage=token_usage,
        retrieved_chunks=retrieved_chunks,
        **kwargs
    )


def log_error(
    error: Exception,
    context: Dict[str, Any] = None,
    user_id: int = None,
    **kwargs
):
    """Log errors with context"""
    logger.error(
        "Error occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context,
        user_id=user_id,
        **kwargs,
        exc_info=True
    )
