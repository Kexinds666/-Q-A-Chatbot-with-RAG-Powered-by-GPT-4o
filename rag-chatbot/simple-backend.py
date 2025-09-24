#!/usr/bin/env python3
"""
Simple RAG Backend for testing
"""
import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
import openai
from PyPDF2 import PdfReader
import tempfile

# Load environment variables
load_dotenv()

app = FastAPI(title="Simple RAG Backend")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Simple in-memory storage for demo
documents = []

class QueryRequest(BaseModel):
    question: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Simple RAG Backend is running"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a PDF file"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Extract text from PDF
        reader = PdfReader(tmp_file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        # Store the document
        documents.append({
            "filename": file.filename,
            "content": text,
            "chunks": [text[i:i+1000] for i in range(0, len(text), 1000)]
        })
        
        # Clean up temp file
        os.unlink(tmp_file_path)
        
        return {"message": f"File {file.filename} processed successfully", "chunks": len(documents[-1]["chunks"])}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/query")
async def query_documents(request: QueryRequest):
    """Query the uploaded documents"""
    if not documents:
        raise HTTPException(status_code=400, detail="No documents uploaded yet")
    
    try:
        # Simple similarity search (for demo purposes)
        question = request.question
        relevant_chunks = []
        
        for doc in documents:
            for chunk in doc["chunks"]:
                # Simple keyword matching for demo
                if any(word.lower() in chunk.lower() for word in question.split()):
                    relevant_chunks.append(chunk)
        
        if not relevant_chunks:
            return {"answer": "I couldn't find relevant information in the uploaded documents to answer your question."}
        
        # Use OpenAI to generate answer
        context = "\n\n".join(relevant_chunks[:3])  # Use top 3 chunks
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context. Use only the information from the context to answer questions."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return {"answer": response.choices[0].message.content}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

if __name__ == "__main__":
    print("Starting Simple RAG Backend...")
    print("Make sure you have set OPENAI_API_KEY in your .env file")
    uvicorn.run(app, host="0.0.0.0", port=8000)
