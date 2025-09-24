"""
Chat endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db, ChatSession, ChatMessage, User
from app.middleware.auth import get_current_active_user
from app.services.chat_service import ChatService
from app.services.vector_service import VectorService
from app.core.logging import logger

router = APIRouter()


# Pydantic models
class ChatQuery(BaseModel):
    question: str
    session_id: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    retrieved_chunks: int
    response_time: float
    token_usage: int
    message_id: int


class ChatSessionResponse(BaseModel):
    id: int
    session_name: str
    is_active: bool
    created_at: str
    updated_at: str
    message_count: int
    
    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    token_count: int
    created_at: str
    
    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    session_id: int
    messages: List[ChatMessageResponse]


@router.post("/chat/query", response_model=ChatResponse)
async def chat_query(
    query: ChatQuery,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Process a chat query"""
    
    if not query.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )
    
    try:
        # Get or create chat session
        if query.session_id:
            # Verify session ownership
            result = await db.execute(
                select(ChatSession).where(
                    ChatSession.id == query.session_id,
                    ChatSession.user_id == current_user.id
                )
            )
            session = result.scalar_one_or_none()
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )
        else:
            # Create new session
            chat_service = ChatService(VectorService())
            session = await chat_service.create_chat_session(
                user_id=current_user.id,
                db=db
            )
        
        # Process query
        chat_service = ChatService(VectorService())
        result = await chat_service.process_query(
            question=query.question,
            session_id=session.id,
            user_id=current_user.id,
            db=db
        )
        
        return ChatResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat query"
        )


@router.get("/chat/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's chat sessions"""
    
    chat_service = ChatService(VectorService())
    sessions = await chat_service.get_user_sessions(current_user.id, db)
    
    # Add message count to each session
    session_responses = []
    for session in sessions:
        # Get message count
        result = await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session.id)
        )
        message_count = len(result.scalars().all())
        
        session_data = ChatSessionResponse.from_orm(session)
        session_data.message_count = message_count
        session_responses.append(session_data)
    
    return session_responses


@router.get("/chat/sessions/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chat history for a session"""
    
    # Verify session ownership
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    # Get messages
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[ChatMessageResponse.from_orm(msg) for msg in messages]
    )


@router.post("/chat/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_name: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat session"""
    
    try:
        chat_service = ChatService(VectorService())
        session = await chat_service.create_chat_session(
            user_id=current_user.id,
            session_name=session_name,
            db=db
        )
        
        session_data = ChatSessionResponse.from_orm(session)
        session_data.message_count = 0
        return session_data
        
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session"
        )


@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat session"""
    
    # Verify session ownership
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    try:
        # Delete session (messages will be deleted by cascade)
        await db.delete(session)
        await db.commit()
        
        return {"message": "Chat session deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat session"
        )


@router.get("/chat/search")
async def search_documents(
    query: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Search across user's documents"""
    
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty"
        )
    
    try:
        vector_service = VectorService()
        
        # Search for similar chunks
        results = await vector_service.search_similar_chunks(
            query=query,
            top_k=10
        )
        
        # Filter results to only include user's documents
        user_documents = []
        for result in results:
            document_id = result["metadata"]["document_id"]
            
            # Check if user owns this document
            doc_result = await db.execute(
                select(Document).where(
                    Document.id == document_id,
                    Document.owner_id == current_user.id
                )
            )
            if doc_result.scalar_one_or_none():
                user_documents.append(result)
        
        return {
            "query": query,
            "results": user_documents,
            "total_results": len(user_documents)
        }
        
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search documents"
        )
