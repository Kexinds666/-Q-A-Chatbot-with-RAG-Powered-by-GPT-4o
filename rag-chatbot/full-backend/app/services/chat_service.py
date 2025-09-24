"""
Chat service with hybrid retrieval (BM25 + Vector Search)
"""

import time
import json
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import math
import re
from openai import AsyncOpenAI
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory

from app.core.config import settings
from app.core.logging import logger, log_chat_interaction
from app.core.database import ChatSession, ChatMessage, DocumentChunk, get_db
from app.services.vector_service import VectorService
from sqlalchemy.ext.asyncio import AsyncSession


class BM25:
    """BM25 implementation for keyword-based retrieval"""
    
    def __init__(self, k1: float = 1.2, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents = []
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        self.avgdl = 0
    
    def fit(self, documents: List[str]):
        """Fit BM25 on documents"""
        self.documents = documents
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        
        # Calculate document frequencies
        for doc in documents:
            words = self._tokenize(doc)
            self.doc_len.append(len(words))
            self.doc_freqs.append(Counter(words))
        
        # Calculate average document length
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0
        
        # Calculate IDF
        df = Counter()
        for doc_freq in self.doc_freqs:
            for word in doc_freq:
                df[word] += 1
        
        for word, freq in df.items():
            self.idf[word] = math.log(len(documents) - freq + 0.5) - math.log(freq + 0.5)
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        return re.findall(r'\b\w+\b', text.lower())
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        """Search for most relevant documents"""
        query_words = self._tokenize(query)
        scores = []
        
        for i, doc_freq in enumerate(self.doc_freqs):
            score = 0
            for word in query_words:
                if word in doc_freq:
                    tf = doc_freq[word]
                    idf = self.idf.get(word, 0)
                    score += idf * (tf * (self.k1 + 1)) / (
                        tf + self.k1 * (1 - self.b + self.b * self.doc_len[i] / self.avgdl)
                    )
            scores.append((i, score))
        
        # Sort by score and return top_k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class ChatService:
    """Chat service with hybrid retrieval and GPT-4o integration"""
    
    def __init__(self, vector_service: VectorService):
        self.vector_service = vector_service
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.chat_model = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        # Chat prompt template
        self.chat_prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        # BM25 instance
        self.bm25 = BM25()
        self.bm25_fitted = False
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the chat model"""
        return """You are an intelligent assistant that answers questions based on provided context from uploaded documents. 

Guidelines:
1. Use only the information provided in the context to answer questions
2. If the context doesn't contain enough information to answer the question, say so clearly
3. Be accurate and cite specific parts of the context when relevant
4. If asked about information not in the context, politely explain that you can only answer based on the uploaded documents
5. Provide clear, well-structured answers
6. If multiple documents are relevant, synthesize information from all sources

Context will be provided with each question. Use it to give accurate, helpful responses."""
    
    async def process_query(
        self,
        question: str,
        session_id: int,
        user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Process user query with hybrid retrieval and generate response"""
        
        start_time = time.time()
        
        try:
            # Get chat history
            chat_history = await self._get_chat_history(session_id, db)
            
            # Hybrid retrieval: BM25 + Vector search
            retrieved_chunks = await self._hybrid_retrieval(question, db)
            
            if not retrieved_chunks:
                response = "I don't have any relevant information in the uploaded documents to answer your question. Please upload some documents first."
            else:
                # Generate response using GPT-4o
                response = await self._generate_response(
                    question, retrieved_chunks, chat_history
                )
            
            # Save user message
            user_message = await self._save_message(
                session_id, "user", question, db
            )
            
            # Save assistant response
            assistant_message = await self._save_message(
                session_id, "assistant", response, 
                retrieved_chunks=retrieved_chunks, db=db
            )
            
            # Calculate metrics
            response_time = time.time() - start_time
            token_usage = self._estimate_token_usage(question + response)
            
            # Log interaction
            log_chat_interaction(
                session_id=session_id,
                user_id=user_id,
                message_count=len(chat_history) + 2,
                response_time=response_time,
                token_usage=token_usage,
                retrieved_chunks=len(retrieved_chunks)
            )
            
            return {
                "response": response,
                "retrieved_chunks": len(retrieved_chunks),
                "response_time": response_time,
                "token_usage": token_usage,
                "message_id": assistant_message.id
            }
            
        except Exception as e:
            logger.error(f"Failed to process query: {e}")
            raise
    
    async def _hybrid_retrieval(
        self, question: str, db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Hybrid retrieval combining BM25 and vector search"""
        
        # Vector search
        vector_results = await self.vector_service.search_similar_chunks(
            question, top_k=settings.TOP_K_RESULTS
        )
        
        # BM25 search (if fitted)
        bm25_results = []
        if self.bm25_fitted:
            bm25_scores = self.bm25.search(question, top_k=settings.TOP_K_RESULTS)
            # Get chunks for BM25 results
            chunk_ids = [score[0] for score in bm25_scores]
            bm25_chunks = await self._get_chunks_by_indices(chunk_ids, db)
            bm25_results = [
                {
                    "content": chunk.content,
                    "metadata": {
                        "document_id": chunk.document_id,
                        "chunk_id": chunk.id,
                        "chunk_index": chunk.chunk_index
                    },
                    "similarity": score[1] / 10,  # Normalize BM25 score
                    "rank": i + 1
                }
                for i, (chunk, score) in enumerate(zip(bm25_chunks, bm25_scores))
            ]
        
        # Combine and rank results
        combined_results = self._combine_search_results(
            vector_results, bm25_results, question
        )
        
        # Filter by similarity threshold
        filtered_results = [
            result for result in combined_results
            if result["similarity"] >= settings.SIMILARITY_THRESHOLD
        ]
        
        return filtered_results[:settings.TOP_K_RESULTS]
    
    def _combine_search_results(
        self, vector_results: List[Dict], bm25_results: List[Dict], query: str
    ) -> List[Dict[str, Any]]:
        """Combine and rank search results from different methods"""
        
        # Create a combined score for each unique chunk
        chunk_scores = {}
        
        # Add vector search results
        for result in vector_results:
            chunk_id = result["metadata"]["chunk_id"]
            chunk_scores[chunk_id] = {
                "content": result["content"],
                "metadata": result["metadata"],
                "vector_score": result["similarity"],
                "bm25_score": 0.0,
                "combined_score": result["similarity"] * settings.VECTOR_WEIGHT
            }
        
        # Add BM25 search results
        for result in bm25_results:
            chunk_id = result["metadata"]["chunk_id"]
            if chunk_id in chunk_scores:
                chunk_scores[chunk_id]["bm25_score"] = result["similarity"]
                chunk_scores[chunk_id]["combined_score"] += result["similarity"] * settings.BM25_WEIGHT
            else:
                chunk_scores[chunk_id] = {
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "vector_score": 0.0,
                    "bm25_score": result["similarity"],
                    "combined_score": result["similarity"] * settings.BM25_WEIGHT
                }
        
        # Sort by combined score
        sorted_results = sorted(
            chunk_scores.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )
        
        # Format results
        formatted_results = []
        for i, result in enumerate(sorted_results):
            formatted_results.append({
                "content": result["content"],
                "metadata": result["metadata"],
                "similarity": result["combined_score"],
                "vector_score": result["vector_score"],
                "bm25_score": result["bm25_score"],
                "rank": i + 1
            })
        
        return formatted_results
    
    async def _get_chunks_by_indices(
        self, indices: List[int], db: AsyncSession
    ) -> List[DocumentChunk]:
        """Get chunks by their indices (for BM25)"""
        from sqlalchemy import select
        
        if not indices:
            return []
        
        result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.id.in_(indices))
            .order_by(DocumentChunk.chunk_index)
        )
        return result.scalars().all()
    
    async def _generate_response(
        self, question: str, retrieved_chunks: List[Dict], chat_history: List[Dict]
    ) -> str:
        """Generate response using GPT-4o with retrieved context"""
        
        # Prepare context
        context = "\n\n".join([
            f"Document {chunk['metadata']['document_id']}, Chunk {chunk['metadata']['chunk_index']}:\n{chunk['content']}"
            for chunk in retrieved_chunks
        ])
        
        # Prepare messages
        messages = [
            SystemMessage(content=self._get_system_prompt()),
        ]
        
        # Add chat history
        for msg in chat_history[-settings.MAX_CHAT_HISTORY:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Add current question with context
        messages.append(HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"))
        
        # Generate response
        response = await self.chat_model.agenerate([messages])
        return response.generations[0][0].text
    
    async def _get_chat_history(
        self, session_id: int, db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get chat history for a session"""
        from sqlalchemy import select
        
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(settings.MAX_CHAT_HISTORY * 2)  # Get more to filter by role
        )
        messages = result.scalars().all()
        
        # Format and reverse order
        history = [
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at
            }
            for msg in reversed(messages)
        ]
        
        return history
    
    async def _save_message(
        self, session_id: int, role: str, content: str,
        retrieved_chunks: List[Dict] = None, db: AsyncSession = None
    ) -> ChatMessage:
        """Save chat message to database"""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            token_count=self._estimate_token_usage(content),
            retrieved_chunks=json.dumps([chunk["metadata"] for chunk in retrieved_chunks]) if retrieved_chunks else None
        )
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message
    
    def _estimate_token_usage(self, text: str) -> int:
        """Estimate token usage for text"""
        # Rough estimation: 4 characters per token
        return len(text) // 4
    
    async def fit_bm25(self, db: AsyncSession):
        """Fit BM25 on all available document chunks"""
        try:
            from sqlalchemy import select
            
            result = await db.execute(
                select(DocumentChunk.content)
                .where(DocumentChunk.content.isnot(None))
            )
            chunks = [row[0] for row in result.fetchall()]
            
            if chunks:
                self.bm25.fit(chunks)
                self.bm25_fitted = True
                logger.info(f"BM25 fitted on {len(chunks)} chunks")
            else:
                logger.warning("No chunks available for BM25 fitting")
                
        except Exception as e:
            logger.error(f"Failed to fit BM25: {e}")
    
    async def create_chat_session(
        self, user_id: int, session_name: str = None, db: AsyncSession = None
    ) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession(
            user_id=user_id,
            session_name=session_name or f"Chat Session {int(time.time())}"
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session
    
    async def get_user_sessions(
        self, user_id: int, db: AsyncSession
    ) -> List[ChatSession]:
        """Get all chat sessions for a user"""
        from sqlalchemy import select
        
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return result.scalars().all()
