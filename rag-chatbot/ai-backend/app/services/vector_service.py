"""
Vector database service with ChromaDB and hybrid retrieval (BM25 + Vector Search)
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
import structlog

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import settings

logger = structlog.get_logger()


class VectorService:
    """Service for vector database operations and hybrid retrieval"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.chroma_client = None
        self.collection = None
        self.bm25_index = None
        self.documents_cache = []
        
    async def initialize(self):
        """Initialize vector database and BM25 index"""
        try:
            # Initialize ChromaDB
            self.chroma_client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIRECTORY,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            
            # Load existing documents for BM25
            await self._load_documents_for_bm25()
            
            logger.info("Vector service initialized successfully")
            
        except Exception as e:
            logger.error("Vector service initialization failed", error=str(e))
            raise
    
    async def _load_documents_for_bm25(self):
        """Load documents from ChromaDB for BM25 indexing"""
        try:
            # Get all documents from ChromaDB
            results = self.collection.get(include=["documents", "metadatas"])
            
            if results["documents"]:
                # Prepare documents for BM25
                self.documents_cache = []
                for i, doc in enumerate(results["documents"]):
                    self.documents_cache.append({
                        "id": results["ids"][i],
                        "content": doc,
                        "metadata": results["metadatas"][i] if results["metadatas"] else {}
                    })
                
                # Create BM25 index
                tokenized_docs = [self._tokenize(doc["content"]) for doc in self.documents_cache]
                self.bm25_index = BM25Okapi(tokenized_docs)
                
                logger.info("BM25 index created", documents_count=len(self.documents_cache))
            
        except Exception as e:
            logger.error("Failed to load documents for BM25", error=str(e))
            raise
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for BM25"""
        return text.lower().split()
    
    async def add_documents(self, documents: List[Document]):
        """Add documents to vector database"""
        try:
            if not documents:
                return
            
            # Prepare data for ChromaDB
            ids = []
            texts = []
            metadatas = []
            embeddings = []
            
            for i, doc in enumerate(documents):
                doc_id = f"doc_{len(self.documents_cache) + i}"
                ids.append(doc_id)
                texts.append(doc.page_content)
                metadatas.append(doc.metadata)
                
                # Generate embedding
                embedding = await self._generate_embedding(doc.page_content)
                embeddings.append(embedding)
            
            # Add to ChromaDB
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=embeddings
            )
            
            # Update BM25 index
            for i, doc in enumerate(documents):
                self.documents_cache.append({
                    "id": ids[i],
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })
            
            # Rebuild BM25 index
            tokenized_docs = [self._tokenize(doc["content"]) for doc in self.documents_cache]
            self.bm25_index = BM25Okapi(tokenized_docs)
            
            logger.info("Documents added to vector database", count=len(documents))
            
        except Exception as e:
            logger.error("Failed to add documents", error=str(e))
            raise
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            embedding = await self.embeddings.aembed_query(text)
            return embedding
        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e))
            raise
    
    async def hybrid_search(
        self, 
        query: str, 
        top_k: int = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining BM25 and vector similarity"""
        try:
            top_k = top_k or settings.TOP_K_RESULTS
            
            # Vector search
            vector_results = await self._vector_search(query, top_k * 2, filter_metadata)
            
            # BM25 search
            bm25_results = await self._bm25_search(query, top_k * 2)
            
            # Combine and rerank results
            combined_results = await self._combine_results(
                vector_results, bm25_results, query, top_k
            )
            
            logger.info("Hybrid search completed", query_length=len(query), results_count=len(combined_results))
            return combined_results
            
        except Exception as e:
            logger.error("Hybrid search failed", error=str(e))
            raise
    
    async def _vector_search(
        self, 
        query: str, 
        top_k: int, 
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"]
            )
            
            vector_results = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    vector_results.append({
                        "id": results["ids"][0][i],
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"][0] else {},
                        "vector_score": 1 - results["distances"][0][i],  # Convert distance to similarity
                        "search_type": "vector"
                    })
            
            return vector_results
            
        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            raise
    
    async def _bm25_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Perform BM25 keyword search"""
        try:
            if not self.bm25_index or not self.documents_cache:
                return []
            
            # Tokenize query
            query_tokens = self._tokenize(query)
            
            # Get BM25 scores
            scores = self.bm25_index.get_scores(query_tokens)
            
            # Get top-k results
            top_indices = np.argsort(scores)[::-1][:top_k]
            
            bm25_results = []
            for idx in top_indices:
                if scores[idx] > 0:  # Only include documents with positive scores
                    doc = self.documents_cache[idx]
                    bm25_results.append({
                        "id": doc["id"],
                        "content": doc["content"],
                        "metadata": doc["metadata"],
                        "bm25_score": float(scores[idx]),
                        "search_type": "bm25"
                    })
            
            return bm25_results
            
        except Exception as e:
            logger.error("BM25 search failed", error=str(e))
            raise
    
    async def _combine_results(
        self, 
        vector_results: List[Dict[str, Any]], 
        bm25_results: List[Dict[str, Any]], 
        query: str, 
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Combine and rerank results from both search methods"""
        try:
            # Create a combined score for each document
            combined_scores = {}
            
            # Normalize and weight vector scores
            if vector_results:
                max_vector_score = max(r["vector_score"] for r in vector_results)
                for result in vector_results:
                    doc_id = result["id"]
                    normalized_vector_score = result["vector_score"] / max_vector_score if max_vector_score > 0 else 0
                    combined_scores[doc_id] = {
                        "vector_score": normalized_vector_score,
                        "bm25_score": 0,
                        "result": result
                    }
            
            # Normalize and weight BM25 scores
            if bm25_results:
                max_bm25_score = max(r["bm25_score"] for r in bm25_results)
                for result in bm25_results:
                    doc_id = result["id"]
                    normalized_bm25_score = result["bm25_score"] / max_bm25_score if max_bm25_score > 0 else 0
                    
                    if doc_id in combined_scores:
                        combined_scores[doc_id]["bm25_score"] = normalized_bm25_score
                    else:
                        combined_scores[doc_id] = {
                            "vector_score": 0,
                            "bm25_score": normalized_bm25_score,
                            "result": result
                        }
            
            # Calculate final combined scores
            final_results = []
            for doc_id, scores in combined_scores.items():
                combined_score = (
                    scores["vector_score"] * settings.VECTOR_WEIGHT +
                    scores["bm25_score"] * settings.BM25_WEIGHT
                )
                
                result = scores["result"].copy()
                result["combined_score"] = combined_score
                result["vector_score"] = scores["vector_score"]
                result["bm25_score"] = scores["bm25_score"]
                final_results.append(result)
            
            # Sort by combined score and return top-k
            final_results.sort(key=lambda x: x["combined_score"], reverse=True)
            
            return final_results[:top_k]
            
        except Exception as e:
            logger.error("Result combination failed", error=str(e))
            raise
    
    async def delete_documents_by_upload_id(self, upload_id: str):
        """Delete documents by upload ID"""
        try:
            if not upload_id:
                return
            
            # Find documents with matching upload_id
            results = self.collection.get(
                where={"upload_id": upload_id},
                include=["ids"]
            )
            
            if results["ids"]:
                # Delete from ChromaDB
                self.collection.delete(ids=results["ids"])
                
                # Remove from cache and rebuild BM25 index
                self.documents_cache = [
                    doc for doc in self.documents_cache 
                    if doc["id"] not in results["ids"]
                ]
                
                if self.documents_cache:
                    tokenized_docs = [self._tokenize(doc["content"]) for doc in self.documents_cache]
                    self.bm25_index = BM25Okapi(tokenized_docs)
                else:
                    self.bm25_index = None
                
                logger.info("Documents deleted by upload_id", upload_id=upload_id, count=len(results["ids"]))
            
        except Exception as e:
            logger.error("Failed to delete documents by upload_id", upload_id=upload_id, error=str(e))
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.chroma_client:
                # ChromaDB cleanup is handled automatically
                pass
            
            logger.info("Vector service cleanup completed")
            
        except Exception as e:
            logger.error("Vector service cleanup failed", error=str(e))
            raise
