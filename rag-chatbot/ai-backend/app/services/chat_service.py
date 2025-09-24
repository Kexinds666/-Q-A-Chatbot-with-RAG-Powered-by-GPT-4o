"""
Chat service with RAG pipeline using LangChain and GPT-4o
"""

import asyncio
from typing import List, Dict, Any, Optional
import structlog
from datetime import datetime

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks import AsyncCallbackHandler

from app.core.config import settings
from app.core.database import get_db, ChatSession, ChatMessage
from app.services.vector_service import VectorService

logger = structlog.get_logger()


class StreamingCallbackHandler(AsyncCallbackHandler):
    """Custom callback handler for streaming responses"""
    
    def __init__(self):
        self.tokens = []
        self.finished = False
    
    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Handle new token from LLM"""
        self.tokens.append(token)
    
    async def on_llm_end(self, response, **kwargs) -> None:
        """Handle end of LLM response"""
        self.finished = True


class ChatService:
    """Service for chat functionality with RAG"""
    
    def __init__(self, vector_service: VectorService):
        self.vector_service = vector_service
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
            openai_api_key=settings.OPENAI_API_KEY,
            streaming=True
        )
        
        # Chat prompt template
        self.chat_prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        # Memory for conversation context
        self.memories = {}  # session_id -> memory
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the chat"""
        return """You are an intelligent AI assistant that helps users find information from their documents. 
        
        You have access to a knowledge base of documents that users have uploaded. When answering questions:
        
        1. Use the provided context from the documents to give accurate, helpful answers
        2. If the information is not in the provided context, say so clearly
        3. Cite specific sources when possible
        4. Be concise but comprehensive
        5. If asked about something not related to the documents, politely redirect to document-related topics
        
        Always be helpful, accurate, and professional in your responses."""
    
    def _get_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        """Get or create memory for session"""
        if session_id not in self.memories:
            self.memories[session_id] = ConversationBufferWindowMemory(
                k=settings.MAX_CHAT_HISTORY,
                return_messages=True,
                memory_key="chat_history"
            )
        return self.memories[session_id]
    
    async def process_message(
        self, 
        message: str, 
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Process chat message with RAG"""
        start_time = datetime.utcnow()
        
        try:
            # Get or create session
            await self._ensure_session(session_id)
            
            # Retrieve relevant documents
            relevant_docs = await self.vector_service.hybrid_search(
                query=message,
                top_k=settings.TOP_K_RESULTS
            )
            
            # Prepare context from retrieved documents
            context = self._prepare_context(relevant_docs)
            
            # Get conversation memory
            memory = self._get_memory(session_id)
            
            # Create chat chain
            chain = self.chat_prompt | self.llm
            
            # Prepare input
            chain_input = {
                "question": message,
                "context": context,
                "chat_history": memory.chat_memory.messages
            }
            
            # Generate response
            response = await chain.ainvoke(chain_input)
            
            # Save message and response to database
            await self._save_conversation(session_id, message, response.content, relevant_docs)
            
            # Update memory
            memory.chat_memory.add_user_message(message)
            memory.chat_memory.add_ai_message(response.content)
            
            # Calculate response time
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Prepare sources
            sources = [doc["metadata"].get("source", "Unknown") for doc in relevant_docs]
            
            logger.info(
                "Chat message processed",
                session_id=session_id,
                response_time=response_time,
                sources_count=len(sources)
            )
            
            return {
                "answer": response.content,
                "sources": sources,
                "response_time": response_time,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error("Chat processing failed", session_id=session_id, error=str(e))
            raise
    
    async def _ensure_session(self, session_id: str):
        """Ensure chat session exists in database"""
        try:
            async for db in get_db():
                session = await db.query(ChatSession).filter(
                    ChatSession.session_id == session_id
                ).first()
                
                if not session:
                    session = ChatSession(session_id=session_id)
                    db.add(session)
                    await db.commit()
                    logger.info("New chat session created", session_id=session_id)
                
        except Exception as e:
            logger.error("Failed to ensure session", session_id=session_id, error=str(e))
            raise
    
    def _prepare_context(self, relevant_docs: List[Dict[str, Any]]) -> str:
        """Prepare context from relevant documents"""
        if not relevant_docs:
            return "No relevant documents found."
        
        context_parts = []
        for i, doc in enumerate(relevant_docs, 1):
            source = doc["metadata"].get("source", "Unknown")
            content = doc["content"]
            score = doc.get("combined_score", 0)
            
            context_parts.append(
                f"Source {i} ({source}, relevance: {score:.3f}):\n{content}\n"
            )
        
        return "\n".join(context_parts)
    
    async def _save_conversation(
        self, 
        session_id: str, 
        user_message: str, 
        ai_response: str, 
        sources: List[Dict[str, Any]]
    ):
        """Save conversation to database"""
        try:
            async for db in get_db():
                # Save user message
                user_msg = ChatMessage(
                    session_id=session_id,
                    message_type="user",
                    content=user_message
                )
                db.add(user_msg)
                
                # Save AI response
                ai_msg = ChatMessage(
                    session_id=session_id,
                    message_type="assistant",
                    content=ai_response,
                    sources=str([doc["metadata"].get("source", "Unknown") for doc in sources])
                )
                db.add(ai_msg)
                
                # Update session
                session = await db.query(ChatSession).filter(
                    ChatSession.session_id == session_id
                ).first()
                
                if session:
                    session.message_count += 2
                    session.last_activity = datetime.utcnow()
                
                await db.commit()
                
        except Exception as e:
            logger.error("Failed to save conversation", session_id=session_id, error=str(e))
            raise
    
    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for session"""
        try:
            async for db in get_db():
                messages = await db.query(ChatMessage).filter(
                    ChatMessage.session_id == session_id
                ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
                
                return [
                    {
                        "id": msg.id,
                        "message_type": msg.message_type,
                        "content": msg.content,
                        "sources": msg.sources,
                        "created_at": msg.created_at.isoformat(),
                        "response_time": msg.response_time
                    }
                    for msg in reversed(messages)
                ]
                
        except Exception as e:
            logger.error("Failed to get chat history", session_id=session_id, error=str(e))
            raise
    
    async def clear_session(self, session_id: str):
        """Clear chat session and memory"""
        try:
            async for db in get_db():
                # Delete messages
                await db.query(ChatMessage).filter(
                    ChatMessage.session_id == session_id
                ).delete()
                
                # Delete session
                await db.query(ChatSession).filter(
                    ChatSession.session_id == session_id
                ).delete()
                
                await db.commit()
            
            # Clear memory
            if session_id in self.memories:
                del self.memories[session_id]
            
            logger.info("Session cleared", session_id=session_id)
            
        except Exception as e:
            logger.error("Failed to clear session", session_id=session_id, error=str(e))
            raise
