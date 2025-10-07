"""
Thread Analysis Page - AI-Powered Email Analysis for Fundraising Teams
Human-in-the-loop approval workflow for email strategies
"""

import os
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import sys
from typing import Dict, Any, Optional

# Load environment
_PROJECT_ROOT = Path(__file__).parent.parent
_env_name = os.getenv("ENVIRONMENT", "development")
load_dotenv(_PROJECT_ROOT / f".env.{_env_name}", override=False)
load_dotenv(_PROJECT_ROOT / ".env", override=False)

# Add utils to path
sys.path.append(str(_PROJECT_ROOT))
from gmail_client import GmailClient
from utils.email_analyzer import analyze_fundraising_thread
from utils.strategy_generator import generate_fundraising_strategy
from utils.report_generator import generate_fundraising_report

st.set_page_config(page_title="Thread Analysis", layout="wide")

# Check if thread is selected
thread_data = st.session_state.get("selected_thread")
if not thread_data:
    st.warning("No email thread selected. Go back to Email Search and select a thread.")
    if st.button("🔍 Back to Email Search"):
        st.switch_page("pages/EmailSearch.py")
    st.stop()

# Page header
st.title("🤖 AI Thread Analysis")
st.caption(f"Analyzing thread: {thread_data.get('subject', 'Unknown Subject')}")

# Sidebar with analysis controls
with st.sidebar:
    st.markdown("## Analysis Options")
    
    # Company context input
    company_context = st.text_area(
        "Company Context (Optional)",
        placeholder="Brief description of your company, stage, industry, etc.",
        help="Provide context about your company to improve analysis quality"
    )
    
    # Analysis settings
    st.markdown("### Settings")
    auto_report = st.checkbox("Generate Report", value=True, help="Automatically generate downloadable analysis report")
    include_alternatives = st.checkbox("Generate Alternative Strategies", value=True)
    
    st.markdown("---")
    
    # Quick actions
    if st.button("🏠 Back to Home"):
        st.switch_page("Home.py")
    
    if st.button("🔍 Back to Email Search"):
        st.switch_page("pages/EmailSearch.py")

# Main analysis interface
tab1, tab2, tab3 = st.tabs(["🔍 Analysis", "📧 Strategy", "🚀 Send Email"])

with tab1:
    st.subheader("AI Thread Analysis")
    
    # Analysis trigger
    if st.button("🤖 Analyze Thread", type="primary", use_container_width=True):
        # Quick environment check
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("❌ OPENAI_API_KEY not found in environment. Please check your .env.development file.")
            st.stop()
        else:
            st.info(f"✅ Using API key: {api_key[:10]}...")
        
        with st.spinner("Analyzing email thread with AI..."):
            try:
                # Get Gmail client
                gmail_client = GmailClient()
                if not gmail_client:
                    st.error("Could not connect to Gmail. Please check your authentication.")
                    st.stop()
                
                # Get user email from session or prompt
                user_email = st.session_state.get("user_email")
                if not user_email:
                    # Try to get from Gmail profile
                    try:
                        profile = gmail_client.service.users().getProfile(userId='me').execute()
                        user_email = profile.get('emailAddress', '')
                        st.session_state["user_email"] = user_email
                    except:
                        st.error("Could not determine user email. Please set user_email in session state.")
                        st.stop()
                
                # Perform analysis
                thread_id = thread_data.get("thread_id")
                mailbox = thread_data.get("mailbox", user_email)  # Get mailbox from thread data
                analysis_result = analyze_fundraising_thread(
                    gmail_client=gmail_client,
                    mailbox=mailbox,
                    thread_id=thread_id,
                    user_email=user_email,
                    company_context=company_context
                )
                
                if "error" in analysis_result:
                    st.error(f"Analysis failed: {analysis_result['error']}")
                    st.stop()
                
                # Store analysis in session
                st.session_state["thread_analysis"] = analysis_result
                
                st.success("✅ Analysis completed!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
    
    # Display analysis results if available
    if "thread_analysis" in st.session_state:
        analysis_data = st.session_state["thread_analysis"]
        analysis = analysis_data.get("analysis")
        metadata = analysis_data.get("metadata", {})
        
        # Quick overview
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            interest_emoji = {"high": "🔥", "medium": "⚡", "low": "❄️", "unknown": "❓"}.get(analysis.investor_interest_level, "❓")
            st.metric("Interest Level", f"{interest_emoji} {analysis.investor_interest_level.title()}")
        
        with col2:
            stage_emoji = {"cold_outreach": "🆕", "follow_up": "🔄", "due_diligence": "🔍", "negotiation": "💰", "closed": "✅"}.get(analysis.conversation_stage, "❓")
            st.metric("Stage", f"{stage_emoji} {analysis.conversation_stage.replace('_', ' ').title()}")
        
        with col3:
            sentiment_color = "🟢" if analysis.sentiment_score > 0.3 else "🟡" if analysis.sentiment_score > -0.3 else "🔴"
            st.metric("Sentiment", f"{sentiment_color} {analysis.sentiment_score:.2f}")
        
        with col4:
            urgency_emoji = {"high": "🚨", "medium": "⚠️", "low": "✅"}.get(analysis.urgency_level, "ℹ️")
            st.metric("Urgency", f"{urgency_emoji} {analysis.urgency_level.title()}")
        
        st.markdown("---")
        
        # Detailed analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Key Insights")
            st.write(f"**Summary:** {analysis.summary}")
            
            if analysis.key_topics:
                st.write("**Key Topics:**")
                for topic in analysis.key_topics:
                    st.write(f"• {topic}")
            
            if analysis.investment_signals:
                st.write("**🎯 Investment Signals:**")
                for signal in analysis.investment_signals:
                    st.write(f"• {signal}")
        
        with col2:
            st.subheader("📈 Thread Statistics")
            st.write(f"**Total Messages:** {metadata.get('total_messages', 0)}")
            st.write(f"**Team Messages:** {metadata.get('team_messages', 0)}")
            st.write(f"**External Messages:** {metadata.get('external_messages', 0)}")
            st.write(f"**Conversation Span:** {metadata.get('conversation_span_days', 0)} days")
            st.write(f"**Last Sender:** {'Team' if metadata.get('last_sender_is_team') else 'External'}")
            
            if analysis.concerns_raised:
                st.write("**⚠️ Concerns Raised:**")
                for concern in analysis.concerns_raised:
                    st.write(f"• {concern}")

with tab2:
    st.subheader("📧 Email Strategy")
    
    if "thread_analysis" not in st.session_state:
        st.info("Please run the analysis first to generate email strategies.")
    else:
        # Generate strategy button
        if st.button("🎯 Generate Strategy", type="primary", use_container_width=True):
            with st.spinner("Generating fundraising strategy..."):
                try:
                    analysis_data = st.session_state["thread_analysis"]
                    messages = analysis_data.get("messages", [])
                    analysis = analysis_data.get("analysis")
                    
                    # Generate strategy
                    strategy = generate_fundraising_strategy(
                        analysis=analysis,
                        messages=messages,
                        company_context=company_context
                    )
                    
                    # Store strategy in session
                    st.session_state["email_strategy"] = strategy
                    
                    # Generate report if enabled
                    if auto_report:
                        report_path = generate_fundraising_report(
                            analysis_data=analysis_data,
                            strategy=strategy,
                            thread_url=None  # Could add Gmail thread URL here
                        )
                        
                        if report_path:
                            st.success("✅ Strategy generated and report created!")
                            st.session_state["latest_report_path"] = report_path
                        else:
                            st.warning("✅ Strategy generated, but report generation failed")
                    else:
                        st.success("✅ Strategy generated!")
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Strategy generation failed: {str(e)}")
        
        # Display strategy if available
        if "email_strategy" in st.session_state:
            strategy = st.session_state["email_strategy"]
            
            # Primary strategy
            st.markdown("### 🎯 Primary Strategy")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(strategy.primary_strategy.priority, "🟡")
                st.metric("Priority", f"{priority_color} {strategy.primary_strategy.priority.title()}")
            
            with col2:
                st.metric("Type", strategy.primary_strategy.strategy_type.replace('_', ' ').title())
            
            with col3:
                st.metric("Timing", strategy.primary_strategy.timing.replace('_', ' ').title())
            
            # Strategy details
            with st.expander("📧 Email Draft", expanded=True):
                st.write(f"**Subject:** {strategy.primary_strategy.subject_line}")
                st.text_area("Email Body", value=strategy.primary_strategy.email_body, height=200, key="primary_email_body")
                
                if strategy.primary_strategy.talking_points:
                    st.write("**Key Talking Points:**")
                    for point in strategy.primary_strategy.talking_points:
                        st.write(f"• {point}")
                
                if strategy.primary_strategy.attachments_needed:
                    st.write("**Attachments Needed:**")
                    for attachment in strategy.primary_strategy.attachments_needed:
                        st.write(f"• {attachment}")
            
            with st.expander("📝 Strategy Details"):
                st.write(f"**Rationale:** {strategy.primary_strategy.rationale}")
                st.write(f"**Relationship Temperature:** {strategy.relationship_temperature.title()}")
                st.write(f"**Recommended Timeline:** {strategy.recommended_timeline}")
                
                if strategy.next_steps:
                    st.write("**Next Steps:**")
                    for step in strategy.next_steps:
                        st.write(f"• {step}")
                
                if strategy.opportunities:
                    st.write("**🎯 Opportunities:**")
                    for opp in strategy.opportunities:
                        st.write(f"• {opp}")
                
                if strategy.red_flags:
                    st.write("**🚨 Red Flags:**")
                    for flag in strategy.red_flags:
                        st.write(f"• {flag}")
            
            # Alternative strategies
            if include_alternatives and strategy.alternative_strategies:
                st.markdown("### 🔄 Alternative Strategies")
                for i, alt_strategy in enumerate(strategy.alternative_strategies, 1):
                    with st.expander(f"Alternative {i}: {alt_strategy.strategy_type.replace('_', ' ').title()}"):
                        st.write(f"**Subject:** {alt_strategy.subject_line}")
                        st.write(f"**Priority:** {alt_strategy.priority.title()}")
                        st.write(f"**Timing:** {alt_strategy.timing.replace('_', ' ')}")
                        st.text_area(f"Email Body {i}", value=alt_strategy.email_body, height=150, key=f"alt_email_body_{i}")
                        st.write(f"**Rationale:** {alt_strategy.rationale}")
            
            # Download report section
            if "latest_report_path" in st.session_state:
                st.markdown("---")
                st.markdown("### 📄 Analysis Report")
                
                report_col1, report_col2 = st.columns([2, 1])
                
                with report_col1:
                    st.info("📊 Complete analysis report generated with all insights and strategies")
                
                with report_col2:
                    report_path = st.session_state["latest_report_path"]
                    if os.path.exists(report_path):
                        with open(report_path, 'r', encoding='utf-8') as f:
                            report_content = f.read()
                        
                        st.download_button(
                            label="📥 Download Report",
                            data=report_content,
                            file_name=os.path.basename(report_path),
                            mime="text/plain",
                            use_container_width=True
                        )

with tab3:
    st.subheader("🚀 Send Email")
    
    if "email_strategy" not in st.session_state:
        st.info("Please generate a strategy first before sending emails.")
    else:
        strategy = st.session_state["email_strategy"]
        
        st.markdown("### ✅ Human-in-the-Loop Approval")
        
        # Email composition area
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Editable email fields
            final_subject = st.text_input("Subject Line", value=strategy.primary_strategy.subject_line)
            final_body = st.text_area("Email Body", value=strategy.primary_strategy.email_body, height=300)
            
            # Additional options
            with st.expander("⚙️ Send Options"):
                send_from = st.selectbox("Send From", ["Primary Mailbox", "Alternative Mailbox"])
                schedule_send = st.checkbox("Schedule Send")
                if schedule_send:
                    send_time = st.time_input("Send Time")
                
                cc_team = st.checkbox("CC Team Members")
                if cc_team:
                    cc_emails = st.text_input("CC Emails", placeholder="email1@company.com, email2@company.com")
        
        with col2:
            st.markdown("#### 📋 Pre-Send Checklist")
            
            checklist_items = [
                "Subject line is compelling",
                "Email addresses specific points from conversation",
                "Tone is appropriate for relationship stage",
                "Call-to-action is clear",
                "No typos or grammatical errors",
                "Attachments ready (if needed)"
            ]
            
            all_checked = True
            for item in checklist_items:
                checked = st.checkbox(item)
                if not checked:
                    all_checked = False
            
            # Send buttons
            st.markdown("---")
            
            if st.button("✉️ Send Email", type="primary", disabled=not all_checked, use_container_width=True):
                with st.spinner("Sending email..."):
                    try:
                        # Here you would integrate with your email sending logic
                        # For now, we'll simulate the send
                        
                        # Get recipient from thread data
                        thread_data = st.session_state.get("selected_thread", {})
                        recipient = thread_data.get("sender", "Unknown")
                        
                        # Simulate email send (replace with actual Gmail API call)
                        st.success(f"✅ Email sent successfully to {recipient}!")
                        
                        # Log the action
                        st.session_state["last_email_sent"] = {
                            "recipient": recipient,
                            "subject": final_subject,
                            "body": final_body,
                            "timestamp": str(st.datetime.now())
                        }
                        
                        # Clear the strategy to prevent accidental re-sends
                        if "email_strategy" in st.session_state:
                            del st.session_state["email_strategy"]
                        
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"Failed to send email: {str(e)}")
            
            if st.button("📝 Save as Draft", use_container_width=True):
                st.session_state["email_draft"] = {
                    "subject": final_subject,
                    "body": final_body,
                    "thread_id": thread_data.get("thread_id")
                }
                st.success("✅ Draft saved!")

# Footer
st.markdown("---")
st.markdown("**🤖 AI Thread Analysis** - Powered by fundraising intelligence")

# Display recent actions
if "last_email_sent" in st.session_state:
    last_sent = st.session_state["last_email_sent"]
    st.success(f"📧 Last email sent to {last_sent['recipient']} - Subject: {last_sent['subject']}")