"""
Vector service with ChromaDB and OpenAI embeddings
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings as ChromaSettings
import openai
from openai import AsyncOpenAI
import numpy as np
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.schema import Document as LangchainDocument

from app.core.config import settings
from app.core.logging import logger
from app.core.database import DocumentChunk, get_db
from sqlalchemy.ext.asyncio import AsyncSession


class VectorService:
    """Vector database service with ChromaDB and OpenAI embeddings"""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self.embeddings = None
        self.openai_client = None
        self._initialize()
    
    def _initialize(self):
        """Initialize ChromaDB client and OpenAI embeddings"""
        try:
            # Initialize OpenAI client
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Initialize OpenAI embeddings
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_EMBEDDING_MODEL,
                chunk_size=1000
            )
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIRECTORY,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("Vector service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector service: {e}")
            raise
    
    async def add_document_chunks(
        self, chunks: List[DocumentChunk], document_id: int
    ) -> List[str]:
        """Add document chunks to vector database"""
        try:
            if not chunks:
                return []
            
            # Prepare documents for embedding
            documents = []
            metadatas = []
            ids = []
            
            for chunk in chunks:
                # Create unique ID
                chunk_id = f"doc_{document_id}_chunk_{chunk.id}"
                
                documents.append(chunk.content)
                metadatas.append({
                    "document_id": document_id,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "token_count": chunk.token_count,
                    "content_hash": chunk.content_hash
                })
                ids.append(chunk_id)
            
            # Generate embeddings
            embeddings = await self._generate_embeddings(documents)
            
            # Add to ChromaDB
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            
            # Update chunk records with embedding IDs
            await self._update_chunk_embedding_ids(chunks, ids)
            
            logger.info(f"Added {len(chunks)} chunks to vector database for document {document_id}")
            return ids
            
        except Exception as e:
            logger.error(f"Failed to add document chunks: {e}")
            raise
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts using OpenAI"""
        try:
            # Process in batches to avoid rate limits
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                response = await self.openai_client.embeddings.create(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    input=batch
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
                
                # Small delay to respect rate limits
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    async def _update_chunk_embedding_ids(
        self, chunks: List[DocumentChunk], embedding_ids: List[str]
    ):
        """Update chunk records with embedding IDs"""
        from sqlalchemy import update
        
        async with get_db() as db:
            for chunk, embedding_id in zip(chunks, embedding_ids):
                await db.execute(
                    update(DocumentChunk)
                    .where(DocumentChunk.id == chunk.id)
                    .values(embedding_id=embedding_id)
                )
            await db.commit()
    
    async def search_similar_chunks(
        self, query: str, top_k: int = None, filter_metadata: Dict = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity"""
        try:
            if top_k is None:
                top_k = settings.TOP_K_RESULTS
            
            # Generate query embedding
            query_embedding = await self._generate_embeddings([query])
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            similar_chunks = []
            if results["documents"] and results["documents"][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )):
                    # Convert distance to similarity score (1 - distance for cosine)
                    similarity = 1 - distance
                    
                    similar_chunks.append({
                        "content": doc,
                        "metadata": metadata,
                        "similarity": similarity,
                        "rank": i + 1
                    })
            
            return similar_chunks
            
        except Exception as e:
            logger.error(f"Failed to search similar chunks: {e}")
            raise
    
    async def delete_document_vectors(self, document_id: int) -> bool:
        """Delete all vectors for a document"""
        try:
            # Get all chunk IDs for the document
            async with get_db() as db:
                from sqlalchemy import select
                result = await db.execute(
                    select(DocumentChunk.embedding_id)
                    .where(DocumentChunk.document_id == document_id)
                    .where(DocumentChunk.embedding_id.isnot(None))
                )
                embedding_ids = [row[0] for row in result.fetchall()]
            
            if embedding_ids:
                # Delete from ChromaDB
                self.collection.delete(ids=embedding_ids)
                logger.info(f"Deleted {len(embedding_ids)} vectors for document {document_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document vectors: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get vector collection statistics"""
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": settings.CHROMA_COLLECTION_NAME,
                "embedding_model": settings.OPENAI_EMBEDDING_MODEL
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}
    
    async def reset_collection(self) -> bool:
        """Reset the entire vector collection"""
        try:
            self.client.delete_collection(settings.CHROMA_COLLECTION_NAME)
            self.collection = self.client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Vector collection reset successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check vector service health"""
        try:
            # Test ChromaDB connection
            count = self.collection.count()
            
            # Test OpenAI embeddings
            test_embedding = await self._generate_embeddings(["test"])
            
            return {
                "status": "healthy",
                "chromadb_connected": True,
                "openai_connected": True,
                "total_chunks": count,
                "embedding_model": settings.OPENAI_EMBEDDING_MODEL
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "chromadb_connected": False,
                "openai_connected": False
            }
