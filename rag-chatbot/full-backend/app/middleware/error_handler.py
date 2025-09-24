"""
Error handling middleware
"""

import traceback
from typing import Union
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from openai import OpenAIError

from app.core.logging import logger, log_error


def setup_error_handlers(app: FastAPI):
    """Setup global error handlers"""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions"""
        logger.warning(
            f"HTTP {exc.status_code}: {exc.detail}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "HTTPException",
                    "message": exc.detail,
                    "status_code": exc.status_code
                }
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors"""
        logger.warning(
            f"Validation error: {exc.errors()}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "errors": exc.errors()
            }
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "type": "ValidationError",
                    "message": "Request validation failed",
                    "details": exc.errors()
                }
            }
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handle database errors"""
        log_error(exc, {"path": request.url.path, "method": request.method})
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "DatabaseError",
                    "message": "A database error occurred",
                    "details": "Internal server error" if not app.debug else str(exc)
                }
            }
        )
    
    @app.exception_handler(OpenAIError)
    async def openai_exception_handler(request: Request, exc: OpenAIError):
        """Handle OpenAI API errors"""
        log_error(exc, {"path": request.url.path, "method": request.method})
        
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "type": "OpenAIError",
                    "message": "AI service temporarily unavailable",
                    "details": "Please try again later"
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions"""
        log_error(exc, {"path": request.url.path, "method": request.method})
        
        # Log full traceback for debugging
        logger.error(
            f"Unhandled exception: {str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "InternalServerError",
                    "message": "An unexpected error occurred",
                    "details": "Internal server error" if not app.debug else str(exc)
                }
            }
        )


class CustomHTTPException(HTTPException):
    """Custom HTTP exception with additional context"""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_type: str = None,
        context: dict = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_type = error_type or "CustomError"
        self.context = context or {}


class DocumentProcessingError(CustomHTTPException):
    """Document processing specific error"""
    
    def __init__(self, detail: str, context: dict = None):
        super().__init__(
            status_code=422,
            detail=detail,
            error_type="DocumentProcessingError",
            context=context
        )


class VectorSearchError(CustomHTTPException):
    """Vector search specific error"""
    
    def __init__(self, detail: str, context: dict = None):
        super().__init__(
            status_code=503,
            detail=detail,
            error_type="VectorSearchError",
            context=context
        )


class ChatGenerationError(CustomHTTPException):
    """Chat generation specific error"""
    
    def __init__(self, detail: str, context: dict = None):
        super().__init__(
            status_code=503,
            detail=detail,
            error_type="ChatGenerationError",
            context=context
        )
