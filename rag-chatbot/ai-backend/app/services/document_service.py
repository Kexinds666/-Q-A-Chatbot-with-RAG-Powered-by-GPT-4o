"""
Document processing service with PDF parsing, chunking, and vectorization
"""

import os
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiofiles
import structlog

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain.schema import Document
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db, Document as DocumentModel, DocumentChunk
from app.services.vector_service import VectorService

logger = structlog.get_logger()


class DocumentMetadata(BaseModel):
    """Document metadata model"""
    filename: str
    file_size: int
    content_type: str
    chunks_count: int
    upload_id: str


class DocumentService:
    """Service for document processing and management"""
    
    def __init__(self, vector_service: VectorService):
        self.vector_service = vector_service
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Create directories
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        os.makedirs(settings.PROCESSED_DIR, exist_ok=True)
    
    async def process_document(self, file_content: bytes, filename: str, content_type: str) -> DocumentMetadata:
        """Process uploaded document"""
        upload_id = str(uuid.uuid4())
        
        try:
            # Save file
            file_path = await self._save_file(file_content, filename, upload_id)
            
            # Extract text
            text_content = await self._extract_text(file_path, content_type)
            
            # Split into chunks
            chunks = await self._split_text(text_content, filename)
            
            # Generate embeddings and store in vector database
            await self._process_chunks(chunks, upload_id)
            
            # Save to database
            document_metadata = await self._save_document_metadata(
                filename, file_path, len(file_content), content_type, len(chunks), upload_id
            )
            
            logger.info(
                "Document processed successfully",
                filename=filename,
                chunks_count=len(chunks),
                upload_id=upload_id
            )
            
            return document_metadata
            
        except Exception as e:
            logger.error("Document processing failed", filename=filename, error=str(e))
            raise
    
    async def _save_file(self, content: bytes, filename: str, upload_id: str) -> str:
        """Save uploaded file to disk"""
        file_path = Path(settings.UPLOAD_DIR) / f"{upload_id}_{filename}"
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        return str(file_path)
    
    async def _extract_text(self, file_path: str, content_type: str) -> str:
        """Extract text from document based on content type"""
        try:
            if content_type == "application/pdf":
                loader = PyPDFLoader(file_path)
                documents = loader.load()
                return "\n\n".join([doc.page_content for doc in documents])
            
            elif content_type == "text/plain":
                loader = TextLoader(file_path, encoding='utf-8')
                documents = loader.load()
                return documents[0].page_content
            
            elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                loader = Docx2txtLoader(file_path)
                documents = loader.load()
                return documents[0].page_content
            
            else:
                raise ValueError(f"Unsupported content type: {content_type}")
                
        except Exception as e:
            logger.error("Text extraction failed", file_path=file_path, error=str(e))
            raise
    
    async def _split_text(self, text: str, filename: str) -> List[Document]:
        """Split text into chunks"""
        try:
            # Create documents with metadata
            documents = self.text_splitter.create_documents(
                [text],
                metadatas=[{"source": filename, "type": "document"}]
            )
            
            logger.info("Text split into chunks", chunks_count=len(documents))
            return documents
            
        except Exception as e:
            logger.error("Text splitting failed", error=str(e))
            raise
    
    async def _process_chunks(self, chunks: List[Document], upload_id: str):
        """Process chunks and store in vector database"""
        try:
            # Process in batches
            batch_size = settings.BATCH_SIZE
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                
                # Add upload_id to metadata
                for chunk in batch:
                    chunk.metadata["upload_id"] = upload_id
                
                # Store in vector database
                await self.vector_service.add_documents(batch)
                
                logger.info(
                    "Chunk batch processed",
                    batch_start=i,
                    batch_size=len(batch),
                    upload_id=upload_id
                )
                
        except Exception as e:
            logger.error("Chunk processing failed", upload_id=upload_id, error=str(e))
            raise
    
    async def _save_document_metadata(
        self, 
        filename: str, 
        file_path: str, 
        file_size: int, 
        content_type: str, 
        chunks_count: int,
        upload_id: str
    ) -> DocumentMetadata:
        """Save document metadata to database"""
        try:
            async for db in get_db():
                document = DocumentModel(
                    filename=filename,
                    file_path=file_path,
                    file_size=file_size,
                    content_type=content_type,
                    chunks_count=chunks_count,
                    processed=True,
                    metadata=f'{{"upload_id": "{upload_id}"}}'
                )
                
                db.add(document)
                await db.commit()
                await db.refresh(document)
                
                return DocumentMetadata(
                    filename=filename,
                    file_size=file_size,
                    content_type=content_type,
                    chunks_count=chunks_count,
                    upload_id=upload_id
                )
                
        except Exception as e:
            logger.error("Failed to save document metadata", error=str(e))
            raise
    
    async def get_documents(self) -> List[Dict[str, Any]]:
        """Get list of processed documents"""
        try:
            async for db in get_db():
                documents = await db.query(DocumentModel).filter(
                    DocumentModel.processed == True
                ).all()
                
                return [
                    {
                        "id": doc.id,
                        "filename": doc.filename,
                        "file_size": doc.file_size,
                        "content_type": doc.content_type,
                        "chunks_count": doc.chunks_count,
                        "upload_date": doc.upload_date.isoformat(),
                        "metadata": doc.metadata
                    }
                    for doc in documents
                ]
                
        except Exception as e:
            logger.error("Failed to get documents", error=str(e))
            raise
    
    async def delete_document(self, document_id: int) -> bool:
        """Delete document and its chunks"""
        try:
            async for db in get_db():
                # Get document
                document = await db.query(DocumentModel).filter(
                    DocumentModel.id == document_id
                ).first()
                
                if not document:
                    return False
                
                # Delete chunks from vector database
                await self.vector_service.delete_documents_by_upload_id(
                    document.metadata.get("upload_id")
                )
                
                # Delete chunks from database
                await db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document_id
                ).delete()
                
                # Delete document
                await db.delete(document)
                await db.commit()
                
                # Delete file
                if os.path.exists(document.file_path):
                    os.remove(document.file_path)
                
                logger.info("Document deleted", document_id=document_id)
                return True
                
        except Exception as e:
            logger.error("Failed to delete document", document_id=document_id, error=str(e))
            raise
