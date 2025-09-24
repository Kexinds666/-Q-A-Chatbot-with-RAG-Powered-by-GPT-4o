"""
Health check endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.services.vector_service import VectorService

logger = structlog.get_logger()
router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "rag-chatbot-ai-backend",
        "version": "1.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
    vector_service: VectorService = Depends()
):
    """Detailed health check with service dependencies"""
    health_status = {
        "status": "healthy",
        "service": "rag-chatbot-ai-backend",
        "version": "1.0.0",
        "checks": {}
    }
    
    try:
        # Database check
        await db.execute("SELECT 1")
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    try:
        # Vector service check
        if vector_service.collection:
            # Try to get collection info
            collection_info = vector_service.collection.get()
            health_status["checks"]["vector_db"] = "healthy"
            health_status["checks"]["vector_db_documents"] = len(collection_info.get("ids", []))
        else:
            health_status["checks"]["vector_db"] = "not_initialized"
    except Exception as e:
        health_status["checks"]["vector_db"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status
