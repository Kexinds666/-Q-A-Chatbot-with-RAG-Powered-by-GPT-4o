#!/usr/bin/env python3
"""
Quick test of the full backend - minimal version
"""

import os
import sys
from pathlib import Path

# Set environment variables
os.environ["OPENAI_API_KEY"] = "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"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["ALLOWED_HOSTS"] = "*"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"

def test_basic_imports():
    """Test basic imports without complex configuration"""
    print("🧪 Testing Basic Imports...")
    
    try:
        # Test OpenAI
        import openai
        print("   ✅ OpenAI imported")
        
        # Test FastAPI
        from fastapi import FastAPI
        print("   ✅ FastAPI imported")
        
        # Test LangChain
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        print("   ✅ LangChain imported")
        
        # Test ChromaDB
        import chromadb
        print("   ✅ ChromaDB imported")
        
        # Test PyPDF2
        import PyPDF2
        print("   ✅ PyPDF2 imported")
        
        return True
    except Exception as e:
        print(f"   ❌ Import Error: {e}")
        return False

def test_openai_connection():
    """Test OpenAI API connection"""
    print("\n🤖 Testing OpenAI Connection...")
    
    try:
        import openai
        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        
        # Test a simple completion
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, RAG Chatbot!'"}
            ],
            max_tokens=10
        )
        
        print("   ✅ OpenAI API connection successful")
        print(f"   ✅ Test response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"   ❌ OpenAI Error: {e}")
        return False

def test_document_processing():
    """Test document processing capabilities"""
    print("\n📄 Testing Document Processing...")
    
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        # Test text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Test text
        test_text = "This is a test document. " * 100
        
        chunks = text_splitter.split_text(test_text)
        print(f"   ✅ Text splitter working: {len(chunks)} chunks created")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Document Processing Error: {e}")
        return False

def test_vector_operations():
    """Test vector operations"""
    print("\n🔍 Testing Vector Operations...")
    
    try:
        import chromadb
        
        # Create a test client
        client = chromadb.Client()
        
        # Create a test collection
        collection = client.create_collection("test_collection")
        
        # Add some test documents
        collection.add(
            documents=["This is a test document", "Another test document"],
            ids=["1", "2"]
        )
        
        # Test search
        results = collection.query(
            query_texts=["test document"],
            n_results=2
        )
        
        print(f"   ✅ ChromaDB working: {len(results['documents'][0])} results found")
        
        # Clean up
        client.delete_collection("test_collection")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Vector Operations Error: {e}")
        return False

def create_simple_fastapi_app():
    """Create a simple FastAPI app for testing"""
    print("\n🚀 Creating Simple FastAPI App...")
    
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        
        app = FastAPI(title="RAG Chatbot Test API")
        
        # Add CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @app.get("/")
        async def root():
            return {"message": "RAG Chatbot API is working!"}
        
        @app.get("/health")
        async def health():
            return {"status": "healthy", "service": "RAG Chatbot API"}
        
        @app.post("/test-chat")
        async def test_chat(message: str):
            try:
                import openai
                client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": message}
                    ],
                    max_tokens=100
                )
                return {
                    "response": response.choices[0].message.content,
                    "status": "success"
                }
            except Exception as e:
                return {"error": str(e), "status": "error"}
        
        print("   ✅ FastAPI app created with test endpoints")
        return app
        
    except Exception as e:
        print(f"   ❌ FastAPI App Error: {e}")
        return None

def main():
    """Main test function"""
    print("🚀 Quick Test of Full Production RAG Chatbot Backend")
    print("=" * 60)
    
    # Test 1: Basic imports
    if not test_basic_imports():
        print("\n❌ Basic import tests failed!")
        return False
    
    # Test 2: OpenAI connection
    if not test_openai_connection():
        print("\n❌ OpenAI connection failed!")
        return False
    
    # Test 3: Document processing
    if not test_document_processing():
        print("\n❌ Document processing tests failed!")
        return False
    
    # Test 4: Vector operations
    if not test_vector_operations():
        print("\n❌ Vector operations tests failed!")
        return False
    
    # Test 5: FastAPI app
    app = create_simple_fastapi_app()
    if not app:
        print("\n❌ FastAPI app creation failed!")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All quick tests passed! Backend components are working.")
    print("\n📋 What's Working:")
    print("   ✅ OpenAI API connection")
    print("   ✅ Document processing (text splitting)")
    print("   ✅ Vector operations (ChromaDB)")
    print("   ✅ FastAPI app creation")
    print("\n🚀 Next Steps:")
    print("   1. Install dependencies: pip install -r requirements.txt")
    print("   2. Run the simple FastAPI app: uvicorn quick_test:app --reload")
    print("   3. Test at: http://localhost:8000/docs")
    print("   4. Try the test-chat endpoint with a message")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
