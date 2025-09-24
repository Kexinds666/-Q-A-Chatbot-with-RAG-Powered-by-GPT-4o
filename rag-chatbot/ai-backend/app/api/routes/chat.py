"""
Chat endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import structlog

from app.services.chat_service import ChatService

logger = structlog.get_logger()
router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    """Chat response model"""
    answer: str
    sources: List[str]
    response_time: float
    session_id: str


@router.post("/", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    chat_service: ChatService = Depends()
):
    """Send a chat message and get AI response"""
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        if len(request.message) > 1000:
            raise HTTPException(status_code=400, detail="Message too long (max 1000 characters)")
        
        result = await chat_service.process_message(
            message=request.message,
            session_id=request.session_id
        )
        
        return ChatResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat processing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process message")


@router.post("/stream")
async def send_message_stream(
    request: ChatRequest,
    chat_service: ChatService = Depends()
):
    """Send a chat message and get streaming AI response"""
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        if len(request.message) > 1000:
            raise HTTPException(status_code=400, detail="Message too long (max 1000 characters)")
        
        result = await chat_service.process_message(
            message=request.message,
            session_id=request.session_id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Streaming chat processing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process message")


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    chat_service: ChatService = Depends()
):
    """Get chat history for a session"""
    try:
        history = await chat_service.get_chat_history(session_id, limit)
        return {"history": history}
        
    except Exception as e:
        logger.error("Failed to get chat history", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve chat history")


@router.delete("/session/{session_id}")
async def clear_chat_session(
    session_id: str,
    chat_service: ChatService = Depends()
):
    """Clear chat session and history"""
    try:
        await chat_service.clear_session(session_id)
        return {"message": "Session cleared successfully"}
        
    except Exception as e:
        logger.error("Failed to clear session", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to clear session")
