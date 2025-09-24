"""
Health check endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.logging import logger

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "RAG Chatbot API",
        "version": "1.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db)
):
    """Detailed health check with database connectivity"""
    try:
        # Test database connection
        await db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Test vector service (would need to be injected)
    # vector_status = await vector_service.health_check()
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "RAG Chatbot API",
        "version": "1.0.0",
        "components": {
            "database": db_status,
            "vector_service": "not_implemented",  # Would be actual status
            "openai": "not_implemented"  # Would be actual status
        }
    }
