#!/usr/bin/env python3
"""
Test script to verify OpenAI API key configuration
"""

import os
import sys
from dotenv import load_dotenv
import openai

def test_api_key():
    """Test OpenAI API key configuration"""
    
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please check your .env file")
        return False
    
    if api_key == "your_openai_api_key_here":
        print("❌ Error: Please replace the placeholder API key with your actual key")
        return False
    
    # Test API key
    try:
        client = openai.OpenAI(api_key=api_key)
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": "Hello! This is a test message."}
            ],
            max_tokens=10
        )
        
        print("✅ API Key is valid and working!")
        print(f"✅ Model: {response.model}")
        print(f"✅ Response: {response.choices[0].message.content}")
        return True
        
    except openai.AuthenticationError:
        print("❌ Error: Invalid API key")
        print("Please check your API key in the .env file")
        return False
        
    except openai.PermissionDeniedError:
        print("❌ Error: Permission denied")
        print("You may not have access to GPT-4o. Check your OpenAI plan.")
        return False
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔑 Testing OpenAI API Key Configuration...")
    print("=" * 50)
    
    success = test_api_key()
    
    if success:
        print("\n🎉 Your API key is configured correctly!")
        print("You can now start the RAG chatbot system.")
    else:
        print("\n💡 Troubleshooting tips:")
        print("1. Make sure you have a valid OpenAI API key")
        print("2. Check that your .env file is in the correct location")
        print("3. Ensure you have access to GPT-4o model")
        print("4. Verify your OpenAI account has sufficient credits")
    
    sys.exit(0 if success else 1)
