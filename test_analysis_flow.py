"""
Test script for the AI analysis flow
Tests the basic functionality without requiring Gmail integration
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
_PROJECT_ROOT = Path(__file__).parent
_env_name = os.getenv("ENVIRONMENT", "development")
load_dotenv(_PROJECT_ROOT / f".env.{_env_name}", override=False)

# Add utils to path
sys.path.append(str(_PROJECT_ROOT))

from utils.ai_context import EmailMessage, AIContextEngine
from utils.strategy_generator import generate_fundraising_strategy
from utils.report_generator import generate_fundraising_report

def test_analysis_flow():
    """Test the complete analysis flow with mock data."""
    
    print("🧪 Testing AI Analysis Flow...")
    print("=" * 50)
    
    # Check OpenAI API key
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key or openai_key == "your_dev_openai_key_here":
        print("❌ OpenAI API key not configured. Please set OPENAI_API_KEY in .env.development")
        return False
    
    print("✅ OpenAI API key found")
    
    # Create mock email messages (simulating a fundraising conversation)
    mock_messages = [
        EmailMessage(
            sender="john.investor@vc.com",
            recipient="founder@startup.com", 
            subject="Re: Introduction to TechCorp",
            body="Hi, thanks for the introduction. I'm interested in learning more about your AI platform. Could you send over your pitch deck and recent metrics?",
            timestamp="2024-01-15T10:00:00Z",
            is_from_team=False
        ),
        EmailMessage(
            sender="founder@startup.com",
            recipient="john.investor@vc.com",
            subject="Re: Introduction to TechCorp", 
            body="Hi John, thanks for your interest! Attached is our latest pitch deck. We've grown 300% YoY and just closed our first enterprise customers including Fortune 500 companies. Our ARR is now $2M with strong unit economics. Would love to schedule a call to discuss our Series A round further.",
            timestamp="2024-01-15T14:30:00Z",
            is_from_team=True
        ),
        EmailMessage(
            sender="john.investor@vc.com",
            recipient="founder@startup.com",
            subject="Re: Introduction to TechCorp",
            body="Great metrics! I'd like to set up a call with my partners. Are you currently raising? What's your timeline for closing the round?",
            timestamp="2024-01-16T09:15:00Z", 
            is_from_team=False
        )
    ]
    
    try:
        # Test AI analysis
        print("🤖 Testing AI analysis...")
        ai_engine = AIContextEngine()
        analysis = ai_engine.analyze_thread(
            messages=mock_messages,
            company_context="AI-powered investor intelligence platform, Series A stage, SaaS model"
        )
        
        print(f"✅ Analysis completed:")
        print(f"   Interest Level: {analysis.investor_interest_level}")
        print(f"   Stage: {analysis.conversation_stage}")
        print(f"   Sentiment: {analysis.sentiment_score}")
        print(f"   Summary: {analysis.summary[:100]}...")
        
        # Test strategy generation
        print("\n🎯 Testing strategy generation...")
        strategy = generate_fundraising_strategy(
            analysis=analysis,
            messages=mock_messages,
            company_context="AI-powered investor intelligence platform, Series A stage"
        )
        
        print(f"✅ Strategy generated:")
        print(f"   Primary Strategy: {strategy.primary_strategy.strategy_type}")
        print(f"   Priority: {strategy.primary_strategy.priority}")
        print(f"   Subject: {strategy.primary_strategy.subject_line}")
        print(f"   Alternatives: {len(strategy.alternative_strategies)}")
        
        # Test report generation
        print("\n📄 Testing report generation...")
        
        # Create mock analysis data structure
        analysis_data = {
            "thread_id": "test_thread_123",
            "messages": mock_messages,
            "analysis": analysis,
            "metadata": {
                "total_messages": len(mock_messages),
                "team_messages": sum(1 for m in mock_messages if m.is_from_team),
                "external_messages": sum(1 for m in mock_messages if not m.is_from_team),
                "conversation_span_days": 1,
                "last_sender_is_team": False,
                "team_participants": ["founder@startup.com"],
                "external_participants": ["john.investor@vc.com"]
            },
            "timestamp": "2024-01-16T12:00:00Z"
        }
        
        report_path = generate_fundraising_report(
            analysis_data=analysis_data,
            strategy=strategy
        )
        
        if report_path and os.path.exists(report_path):
            print(f"✅ Report generated: {report_path}")
            
            # Show first few lines of report
            with open(report_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:10]
                print("\n📋 Report preview:")
                for line in lines:
                    print(f"   {line.strip()}")
                print("   ...")
        else:
            print("❌ Report generation failed")
            return False
        
        print("\n🎉 All tests passed! The analysis flow is working correctly.")
        print(f"\n💡 Next steps:")
        print(f"   1. Navigate to Email Search in Streamlit")
        print(f"   2. Find an investor email thread")
        print(f"   3. Click '🚀 Analyze Thread' button")
        print(f"   4. Review AI analysis and strategy")
        print(f"   5. Download the generated report")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_analysis_flow()
    if success:
        print("\n🚀 Ready to test in Streamlit!")
    else:
        print("\n🔧 Please fix the issues above before proceeding.")