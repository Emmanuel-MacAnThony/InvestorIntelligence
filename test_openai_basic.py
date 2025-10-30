"""
Basic OpenAI API test to verify connectivity and authentication
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import openai

# Load environment
_PROJECT_ROOT = Path(__file__).parent
_env_name = os.getenv("ENVIRONMENT", "development")
load_dotenv(_PROJECT_ROOT / f".env.{_env_name}", override=False)

def test_openai_basic():
    """Test basic OpenAI API connectivity."""
    
    print("🔑 Testing OpenAI API...")
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No OPENAI_API_KEY found in environment")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        # Initialize client
        client = openai.OpenAI(api_key=api_key)
        
        print("🤖 Testing simple API call...")
        
        # Test simple request
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say 'Hello, API test successful!' and nothing else."}
            ],
            max_tokens=50,
            temperature=0
        )
        
        result = response.choices[0].message.content
        print(f"✅ API Response: {result}")
        
        # Test JSON response
        print("📝 Testing JSON response...")
        
        json_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": 'Respond with only this JSON: {"test": "success", "number": 42}'}
            ],
            max_tokens=50,
            temperature=0
        )
        
        json_result = json_response.choices[0].message.content
        print(f"✅ JSON Response: {json_result}")
        
        # Try to parse JSON
        import json
        try:
            parsed = json.loads(json_result)
            print(f"✅ JSON parsing successful: {parsed}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"Raw response: '{json_result}'")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_openai_basic()
    if success:
        print("\n🎉 OpenAI API is working correctly!")
    else:
        print("\n🔧 Please check your API key and internet connection.")