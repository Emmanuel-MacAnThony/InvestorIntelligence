"""
Debug script to test AI analysis with minimal example
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
_PROJECT_ROOT = Path(__file__).parent
_env_name = os.getenv("ENVIRONMENT", "development")
load_dotenv(_PROJECT_ROOT / f".env.{_env_name}", override=False)

from utils.ai_context import EmailMessage, AIContextEngine

def test_simple_analysis():
    """Test with minimal data to debug the issue."""
    
    print("🧪 Testing AI Analysis with Simple Data...")
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No OpenAI API key found")
        return
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Create very simple test messages
    messages = [
        EmailMessage(
            sender="investor@vc.com",
            recipient="founder@startup.com",
            subject="Investment Interest",
            body="Hi, I'm interested in your company. Can we schedule a call?",
            timestamp="2024-01-01T10:00:00Z",
            is_from_team=False
        ),
        EmailMessage(
            sender="founder@startup.com", 
            recipient="investor@vc.com",
            subject="Re: Investment Interest",
            body="Absolutely! I'd love to discuss our Series A round. Are you available this week?",
            timestamp="2024-01-01T14:00:00Z",
            is_from_team=True
        )
    ]
    
    try:
        print("🤖 Initializing AI engine...")
        ai_engine = AIContextEngine()
        
        print("📧 Analyzing simple thread...")
        analysis = ai_engine.analyze_thread(
            messages=messages,
            company_context="Early stage startup looking for Series A funding"
        )
        
        print("✅ Analysis completed!")
        print(f"Interest Level: {analysis.investor_interest_level}")
        print(f"Stage: {analysis.conversation_stage}")
        print(f"Sentiment: {analysis.sentiment_score}")
        print(f"Summary: {analysis.summary}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_simple_analysis()