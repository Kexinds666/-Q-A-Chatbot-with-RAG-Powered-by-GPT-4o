"""
Document management endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.services.document_service import DocumentService

logger = structlog.get_logger()
router = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_service: DocumentService = Depends()
):
    """Upload and process a document"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        if file.size > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        # Read file content
        content = await file.read()
        
        # Process document
        result = await document_service.process_document(
            file_content=content,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream"
        )
        
        logger.info("Document uploaded successfully", filename=file.filename)
        
        return {
            "message": "Document uploaded and processed successfully",
            "upload_id": result.upload_id,
            "filename": result.filename,
            "chunks_created": result.chunks_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document upload failed", filename=file.filename, error=str(e))
        raise HTTPException(status_code=500, detail="Document processing failed")


@router.get("/")
async def get_documents(
    document_service: DocumentService = Depends()
):
    """Get list of processed documents"""
    try:
        documents = await document_service.get_documents()
        return {"documents": documents}
        
    except Exception as e:
        logger.error("Failed to get documents", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve documents")


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    document_service: DocumentService = Depends()
):
    """Delete a document and its chunks"""
    try:
        success = await document_service.delete_document(document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete document", document_id=document_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete document")
