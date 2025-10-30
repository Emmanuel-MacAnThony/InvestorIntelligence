"""
Advanced Thread Analysis Page - Multi-Step LangGraph Fundraising Intelligence
Complete investor relationship analysis with campaign generation and retrospective reports
"""

import os
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import sys
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Load environment
_PROJECT_ROOT = Path(__file__).parent.parent
_env_name = os.getenv("ENVIRONMENT", "development")
load_dotenv(_PROJECT_ROOT / f".env.{_env_name}", override=False)
load_dotenv(_PROJECT_ROOT / ".env", override=False)

# Add utils to path
sys.path.append(str(_PROJECT_ROOT))
from utils.gmail_client import GmailClient
from utils.fundraising_intelligence import get_fundraising_intelligence_engine, FundraisingState
from utils.email_analyzer import analyze_fundraising_thread
from utils.strategy_generator import generate_fundraising_strategy
from utils.report_generator import generate_fundraising_report

st.set_page_config(page_title="Fundraising Intelligence", layout="wide")

# Page header
st.title("🧠 Advanced Fundraising Intelligence")
st.markdown("**LangGraph-Powered Multi-Step Analysis** • Investor Context • Campaign Strategies • Retrospective Reports")

# Sidebar with analysis options
with st.sidebar:
    st.markdown("## 🎯 Analysis Type")

    # Only show Single Thread Analysis for now
    analysis_mode = "Single Thread Analysis"

    # COMMENTED OUT: Complete Intelligence Audit option
    # analysis_mode = st.radio(
    #     "Select Analysis:",
    #     ["Single Thread Analysis", "Complete Intelligence Audit"],
    #     help="Single Thread: Analyze selected email thread | Complete: Full mailbox analysis"
    # )

    if analysis_mode == "Single Thread Analysis":
        # Check if thread is selected
        thread_data = st.session_state.get("selected_thread")
        if not thread_data:
            st.warning("No email thread selected. Go back to Email Search and select a thread.")
            if st.button("🔍 Back to Email Search"):
                st.switch_page("pages/EmailSearch.py")
            st.stop()

        st.success(f"Thread: {thread_data.get('subject', 'Unknown Subject')[:50]}...")

    elif analysis_mode == "Complete Intelligence Audit":
        st.info("This will analyze all fundraising emails in your mailbox")

        # Time window selection
        time_window = st.selectbox(
            "Analysis Time Window:",
            [7, 14, 30, 60, 90],
            index=2,
            format_func=lambda x: f"Last {x} days",
            help="How far back to analyze emails"
        )
    
    st.markdown("---")
    
    # Company context input
    company_context = st.text_area(
        "Company Context",
        placeholder="Brief description of your company, stage, industry, fundraising goals, etc.",
        help="Provide context about your company to improve analysis quality and strategy generation",
        value=st.session_state.get("company_context", "")
    )
    
    if company_context:
        st.session_state["company_context"] = company_context
    
    st.markdown("---")

    # Mailbox selection
    selected_mailbox = st.session_state.get("selected_mailbox")
    if analysis_mode == "Single Thread Analysis":
        if selected_mailbox:
            st.success(f"📧 Mailbox: {selected_mailbox}")
        else:
            st.info("📧 Using mailbox from thread data")
    else:
        # Complete Intelligence Audit doesn't need mailbox
        if selected_mailbox:
            st.info(f"📧 Available Mailbox: {selected_mailbox}")
        else:
            st.info("📧 Using authenticated mailbox")

    st.markdown("---")

    if st.button("🏠 Back to Home", use_container_width=True):
        st.switch_page("Home.py")
    
# Main content area
if analysis_mode == "Single Thread Analysis":
    st.header("🧠 Advanced Intelligence - Selected Thread")
    st.info("📌 Deep AI analysis of selected investor + all their correspondence with this mailbox")

    # Show current thread and investor
    selected_mailbox = st.session_state.get("selected_mailbox")
    thread_data = st.session_state.get("selected_thread", {})

    if not thread_data:
        st.error("No thread selected. Please go to Email Search and select a thread first.")
        st.stop()

    # Extract investor email from selected thread (the OTHER party, not your mailbox)
    sender_email = thread_data.get("sender", "")
    mailbox = thread_data.get("mailbox", "")

    # Clean email addresses
    import re

    def extract_email(email_str):
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', email_str)
        return email_match.group().lower() if email_match else email_str.lower()

    sender_clean = extract_email(sender_email)
    mailbox_clean = extract_email(mailbox) if mailbox else ""

    # Determine who the investor is (not your mailbox)
    if sender_clean == mailbox_clean:
        # You sent this email, so investor is the recipient
        recipient_email = thread_data.get("recipient", "")
        investor_email = extract_email(recipient_email)
    else:
        # You received this email, so investor is the sender
        investor_email = sender_clean

    st.write(f"**Investor:** {investor_email}")
    st.write(f"**Your Mailbox:** {mailbox}")
    st.write(f"**Selected Thread:** {thread_data.get('subject', 'Unknown')}")

    if st.button("🚀 Analyze This Investor", type="primary"):
        with st.spinner(f"Running advanced analysis for {investor_email}..."):
            try:
                engine = get_fundraising_intelligence_engine()
                gmail_client = GmailClient()

                mailbox_to_use = thread_data.get("mailbox") or selected_mailbox

                if not mailbox_to_use:
                    st.error("No mailbox selected.")
                    st.stop()

                st.info(f"🔍 Searching for ALL emails with {investor_email}...")

                # Search for ALL emails between this mailbox and this specific investor
                query_parts = [
                    f"(from:{investor_email} OR to:{investor_email})",
                    f"(from:{mailbox_to_use} OR to:{mailbox_to_use})"
                ]
                query = " ".join(query_parts)

                search_result = gmail_client.search_emails(mailbox_to_use, query, max_results=50)

                if search_result.get("error"):
                    st.error(f"Search failed: {search_result['error']}")
                    st.stop()

                messages = search_result.get("messages", [])
                st.info(f"✅ Found {len(messages)} messages with {investor_email}")

                if not messages:
                    st.warning("No messages found with this investor")
                    st.stop()

                # Get full message details
                raw_emails = []
                thread_ids = set()
                for msg in messages:
                    msg_data = gmail_client.get_message(mailbox_to_use, msg["id"])
                    if msg_data and not msg_data.get("error"):
                        raw_emails.append(msg_data)
                        thread_ids.add(msg_data.get("threadId"))

                st.info(f"✅ Retrieved {len(raw_emails)} messages across {len(thread_ids)} threads")

                # Create a minimal state for the intelligence engine
                from utils.fundraising_intelligence import FundraisingState

                initial_state = FundraisingState(
                    mailbox=mailbox_to_use,
                    user_email=mailbox_to_use,
                    company_context=company_context or "No specific company context provided",
                    time_window_days=7,
                    current_step="initializing"
                )

                # Store gmail client
                engine._gmail_client = gmail_client

                # Manually set the raw_emails to bypass the fetch step
                initial_state.raw_emails = raw_emails

                # Parse emails into metadata format (this is what the engine needs)
                st.info("📧 Parsing email metadata...")
                from utils.fundraising_intelligence import EmailMetadata
                from email.utils import parsedate_to_datetime

                email_metadata = []
                for email in raw_emails:
                    try:
                        headers = {h["name"]: h["value"] for h in email.get("payload", {}).get("headers", [])}

                        # Parse timestamp
                        date_str = headers.get("Date", "")
                        timestamp = None
                        try:
                            timestamp = parsedate_to_datetime(date_str)
                        except:
                            timestamp = datetime.now()

                        sender = headers.get("From", "")
                        recipient = headers.get("To", "")

                        # Check if it's a reply
                        is_reply = "Re:" in headers.get("Subject", "") or headers.get("In-Reply-To") is not None

                        # Determine if outbound
                        is_outbound = mailbox_to_use.lower() in sender.lower()

                        # Extract body content
                        body_content = engine._extract_email_body(email)

                        metadata = EmailMetadata(
                            message_id=email["id"],
                            thread_id=email["threadId"],
                            sender=sender,
                            recipient=recipient,
                            timestamp=timestamp,
                            is_reply=is_reply,
                            subject=headers.get("Subject", ""),
                            body_length=len(body_content),
                            has_attachments="attachment" in str(email).lower(),
                            labels=email.get("labelIds", []),
                            body_content=body_content,
                            snippet=email.get("snippet", ""),
                            is_outbound=is_outbound
                        )

                        email_metadata.append(metadata)

                    except Exception as e:
                        st.warning(f"Failed to parse email: {str(e)}")
                        continue

                initial_state.email_metadata = email_metadata
                st.info(f"✅ Parsed {len(email_metadata)} emails")

                # Run just the analysis steps (skip the broad email fetch)
                st.info("🧠 Running AI analysis pipeline...")

                async def run_focused_analysis():
                    # Process the emails we already have
                    state = await engine._group_threads_node(initial_state)
                    state = await engine._analyze_conversations_node(state)
                    state = await engine._extract_timing_patterns_node(state)
                    state = await engine._analyze_strategy_effectiveness_node(state)
                    state = await engine._generate_campaign_strategies_node(state)
                    state = await engine._generate_retrospective_node(state)
                    return state

                results = asyncio.run(run_focused_analysis())

                st.session_state["advanced_thread_analysis"] = results

                # Auto-save to CRM for advanced analysis
                st.info("💾 Saving investor data to CRM...")
                try:
                    from utils.investor_crm import InvestorCRM

                    st.write(f"**DEBUG:** Initializing CRM...")
                    crm = InvestorCRM()
                    st.write(f"**DEBUG:** CRM initialized. Base ID: {crm.base_id}, Table ID: {crm.table_id}")

                    saved_count = 0
                    failed_count = 0

                    st.write(f"**DEBUG:** Found {len(results.investor_contexts)} investors to save")

                    # For each analyzed investor, save to CRM
                    for investor_email_key, ctx in results.investor_contexts.items():
                        try:
                            st.info(f"Processing {investor_email_key}...")
                            st.write(f"**DEBUG:** Investor context - Name: {ctx.name}, Stage: {ctx.relationship_stage}, Sentiment: {ctx.sentiment_trend}")

                            # Build a mock analysis result for CRM compatibility
                            from utils.ai_context import ThreadAnalysis

                            # Create ThreadAnalysis object from InvestorContext
                            mock_analysis = ThreadAnalysis(
                                conversation_stage=ctx.relationship_stage,
                                investor_interest_level="high" if ctx.sentiment_trend == "positive" else "medium" if ctx.sentiment_trend == "neutral" else "low",
                                key_topics=ctx.key_interests or [],
                                pain_points=ctx.objections_raised or [],
                                value_propositions_mentioned=[],
                                next_actions=[ctx.next_action_suggested] if ctx.next_action_suggested else [],
                                sentiment_score=0.5 if ctx.sentiment_trend == "positive" else 0.0 if ctx.sentiment_trend == "neutral" else -0.5,
                                urgency_level="medium",
                                investment_signals=[],
                                concerns_raised=ctx.objections_raised or [],
                                summary=ctx.conversation_summary or ""
                            )

                            # Build mock analysis result
                            mock_analysis_result = {
                                "analysis": mock_analysis,
                                "metadata": {
                                    "team_messages": ctx.total_emails_sent,
                                    "external_messages": ctx.total_replies_received,
                                    "first_message_date": ctx.last_contact_date.isoformat() if ctx.last_contact_date else None,
                                    "last_message_date": ctx.last_contact_date.isoformat() if ctx.last_contact_date else None
                                }
                            }

                            # Build mock thread data
                            mock_thread_data = {
                                "thread_id": thread_data.get("thread_id", "unknown"),
                                "sender": investor_email_key,
                                "recipient": mailbox_to_use
                            }

                            st.write(f"**DEBUG:** Calling save_analysis_to_crm with:")
                            st.write(f"  - Investor email: {investor_email_key}")
                            st.write(f"  - User email: {mailbox_to_use}")
                            st.write(f"  - Thread ID: {mock_thread_data['thread_id']}")

                            # Save to CRM
                            crm_result = crm.save_analysis_to_crm(
                                analysis_result=mock_analysis_result,
                                thread_data=mock_thread_data,
                                user_email=mailbox_to_use
                            )

                            st.write(f"**DEBUG:** CRM result: {crm_result}")

                            # Check for error in CRM result
                            if crm_result.get("error"):
                                failed_count += 1
                                st.warning(f"⚠️ Failed to save {investor_email_key}: {crm_result['error']}")
                            else:
                                saved_count += 1
                                action = "Created" if crm_result.get("created") else "Updated"
                                st.success(f"✅ {action} {investor_email_key} in CRM")

                        except Exception as inner_error:
                            failed_count += 1
                            st.error(f"❌ Exception saving {investor_email_key}: {str(inner_error)}")
                            import traceback
                            with st.expander("Show Error Details"):
                                st.code(traceback.format_exc())
                            continue

                    if saved_count > 0:
                        st.success(f"✅ Analysis complete! Saved {saved_count} investor(s) to CRM")
                    else:
                        st.warning(f"⚠️ Analysis complete but no investors were saved to CRM. Failed: {failed_count}")

                except Exception as crm_error:
                    # Don't fail the analysis if CRM fails
                    st.error(f"❌ CRM save failed: {str(crm_error)}")
                    import traceback
                    st.code(traceback.format_exc())

                st.rerun()

            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

    # Display results using the same format as Complete Intelligence Audit
    if "advanced_thread_analysis" in st.session_state:
        results = st.session_state["advanced_thread_analysis"]

        st.success("📊 Analysis Complete!")

        # Overview metrics
        st.markdown("### 📊 Intelligence Overview")

        col1, col2, col3, col4 = st.columns(4)

        investor_contexts = results.investor_contexts or {}

        with col1:
            total_investors = len(investor_contexts)
            st.metric("Investors Analyzed", total_investors)

        with col2:
            total_emails = sum(ctx.total_emails_sent for ctx in investor_contexts.values()) if investor_contexts else 0
            st.metric("Emails Sent", total_emails)

        with col3:
            total_replies = sum(ctx.total_replies_received for ctx in investor_contexts.values()) if investor_contexts else 0
            st.metric("Replies Received", total_replies)

        with col4:
            reply_rate = (total_replies / total_emails * 100) if total_emails > 0 else 0
            st.metric("Reply Rate", f"{reply_rate:.1f}%")

        # Tabs for results
        tab1, tab2, tab3, tab4 = st.tabs(["👥 Investor Profile", "📧 Strategies", "⏰ Timing Intelligence", "📈 Report"])

        with tab1:
            st.subheader("👥 Investor Insights")

            # Add button to navigate to Investor CRM
            if st.button("💼 View in Investor CRM", type="primary", use_container_width=True):
                st.switch_page("pages/InvestorCRM.py")

            st.markdown("---")

            if investor_contexts:
                for email, ctx in investor_contexts.items():
                    with st.expander(f"{ctx.name or email} - {ctx.relationship_stage}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Email:** {ctx.email}")
                            st.write(f"**Sentiment:** {ctx.sentiment_trend}")
                            st.write(f"**Stage:** {ctx.relationship_stage}")

                        with col2:
                            st.write(f"**Emails:** {ctx.total_emails_sent}")
                            st.write(f"**Replies:** {ctx.total_replies_received}")
                            if ctx.next_action_suggested:
                                st.write(f"**Next:** {ctx.next_action_suggested}")

                        if ctx.conversation_summary:
                            st.markdown(f"**Summary:** {ctx.conversation_summary}")

        with tab2:
            st.subheader("📧 Campaign Strategies")

            campaign_strategies = results.campaign_strategies or []

            if campaign_strategies:
                for i, strategy in enumerate(campaign_strategies):
                    with st.expander(f"{strategy.investor_email} - {strategy.strategy_type.replace('_', ' ').title()}"):
                        st.markdown("**📧 Email Draft:**")
                        st.text_area("Email Draft", strategy.email_draft, height=150, key=f"email_adv_{i}", label_visibility="collapsed")

                        st.write(f"**Confidence:** {strategy.confidence_score:.1%}")
                        st.write(f"**Expected Response:** {strategy.expected_response_rate:.1%}")

                        if strategy.reasoning:
                            st.markdown(f"**Reasoning:** {strategy.reasoning}")
            else:
                st.info("No strategies generated")

        with tab3:
            st.subheader("⏰ Timing Intelligence & Communication Patterns")

            timing_patterns = results.timing_patterns or {}

            if timing_patterns and investor_contexts:
                # Get the investor email
                investor_email_key = list(investor_contexts.keys())[0] if investor_contexts else None
                ctx = investor_contexts.get(investor_email_key) if investor_email_key else None
                timing = timing_patterns.get(investor_email_key, {}) if investor_email_key else {}

                if ctx and timing:
                    st.markdown(f"### 📊 Communication Pattern Analysis for {ctx.name or investor_email_key}")

                    # Key metrics
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        preferred_day = timing.get("preferred_day", "Unknown").title()
                        st.metric("📅 Preferred Day", preferred_day)

                    with col2:
                        preferred_hour = timing.get("preferred_hour", 10)
                        time_str = f"{preferred_hour}:00"
                        st.metric("🕒 Preferred Time", time_str)

                    with col3:
                        avg_hours = timing.get("avg_response_hours", 0)
                        if avg_hours < 24:
                            st.metric("⚡ Avg Response", f"{avg_hours:.1f}h")
                        else:
                            st.metric("⚡ Avg Response", f"{avg_hours/24:.1f}d")

                    with col4:
                        response_rate = timing.get("response_rate", 0)
                        st.metric("📈 Response Rate", f"{response_rate:.1%}")

                    st.markdown("---")

                    # Detailed insights
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("### 🎯 Best Time to Contact")

                        # Time of day recommendation
                        if preferred_hour < 8:
                            time_insight = "🌅 **Early Bird (Before 8 AM)**\n\nThis investor responds to early morning emails. They likely check email before their day starts. Send important messages before 8 AM for best visibility."
                        elif preferred_hour < 12:
                            time_insight = f"☀️ **Morning Person ({preferred_hour}:00 AM)**\n\nMid-morning is their sweet spot. They're likely settled into work mode but not yet in back-to-back meetings. Perfect time for thoughtful responses."
                        elif preferred_hour < 14:
                            time_insight = f"🕐 **Lunch Window ({preferred_hour}:00 PM)**\n\nThey engage during lunch hours. Brief, focused emails work well. They might be catching up between meetings or during a quick break."
                        elif preferred_hour < 17:
                            time_insight = f"🌆 **Afternoon Reviewer ({preferred_hour}:00 PM)**\n\nLate afternoon is their engagement window. They're likely wrapping up the day and reviewing correspondence. Good time for follow-ups."
                        else:
                            time_insight = f"🌙 **Evening Processor ({preferred_hour}:00 PM)**\n\nThey review emails after hours. This suggests they take time to thoughtfully respond outside business hours. Detailed emails may get more attention."

                        st.info(time_insight)

                        # Day of week recommendation
                        st.markdown("### 📅 Best Day to Send")

                        if preferred_day.lower() == "monday":
                            day_insight = "**Monday** - They engage at start of week. Good for setting weekly priorities and scheduling."
                        elif preferred_day.lower() == "friday":
                            day_insight = "**Friday** - End of week engagement. Good for recaps and planning ahead."
                        elif preferred_day.lower() in ["tuesday", "wednesday", "thursday"]:
                            day_insight = f"**{preferred_day}** - Mid-week is optimal. Peak focus and availability. Best for important asks."
                        else:
                            day_insight = f"**{preferred_day}** - Weekend communication. Respect work-life boundaries."

                        st.success(day_insight)

                    with col2:
                        st.markdown("### ⚡ Response Speed Analysis")

                        avg_hours = timing.get("avg_response_hours", 0)

                        if avg_hours < 1:
                            speed_insight = "🚀 **Lightning Fast (< 1 hour)**\n\nExtremely responsive! They prioritize quick replies. This suggests high interest and engagement. Strike while the iron is hot - follow up quickly."
                            speed_emoji = "🚀"
                        elif avg_hours < 4:
                            speed_insight = "⚡ **Very Quick (1-4 hours)**\n\nHighly engaged and responsive. They check email frequently and respond promptly. Your communications are getting priority attention."
                            speed_emoji = "⚡"
                        elif avg_hours < 24:
                            speed_insight = "📅 **Same Day (4-24 hours)**\n\nReliable same-day responses. They're engaged but measured in their replies. Allow time for thoughtful consideration."
                            speed_emoji = "📅"
                        elif avg_hours < 72:
                            speed_insight = "🤔 **Deliberate (1-3 days)**\n\nThoughtful, measured responses. They take time to consider before replying. Don't mistake slow replies for lack of interest."
                            speed_emoji = "🤔"
                        else:
                            speed_insight = "🐌 **Slow Burn (3+ days)**\n\nVery slow to respond. Could indicate low priority, busy schedule, or consideration style. May need stronger hooks or different approach."
                            speed_emoji = "🐌"

                        st.info(f"{speed_emoji} {speed_insight}")

                        # Engagement level
                        st.markdown("### 💪 Engagement Level")

                        total_replies = timing.get("total_replies", 0)

                        if response_rate > 0.7 and total_replies > 3:
                            engagement = "🔥 **Highly Engaged**\n\nStrong relationship! High response rate with multiple interactions. Keep the momentum going."
                        elif response_rate > 0.5:
                            engagement = "✅ **Good Engagement**\n\nSolid relationship building. They're responsive and interested. Continue current approach."
                        elif response_rate > 0.3:
                            engagement = "📊 **Moderate Engagement**\n\nRoom for improvement. Some interest but not fully engaged. Consider refining messaging or value proposition."
                        else:
                            engagement = "⚠️ **Low Engagement**\n\nWeak response pattern. Need to reassess approach, timing, or value proposition. Consider different angle."

                        st.success(engagement)

                    st.markdown("---")

                    # Actionable recommendations
                    st.markdown("### 💡 Actionable Recommendations")

                    recommendations = []

                    # Timing recommendation
                    recommendations.append(f"⏰ **Optimal Send Time:** {preferred_day} at {preferred_hour}:00")

                    # Follow-up timing
                    if avg_hours < 24:
                        recommendations.append(f"⚡ **Follow-up Window:** Within {int(avg_hours)} hours - they respond quickly")
                    else:
                        recommendations.append(f"⏳ **Follow-up Window:** Wait {int(avg_hours/24)} days before following up")

                    # Content strategy
                    if avg_hours < 4:
                        recommendations.append("✍️ **Content Strategy:** Keep emails concise - they respond fast, likely reviewing on mobile")
                    else:
                        recommendations.append("✍️ **Content Strategy:** Detailed emails OK - they take time to read thoroughly")

                    # Engagement strategy
                    if response_rate > 0.5:
                        recommendations.append("🎯 **Engagement Strategy:** High priority lead - maintain regular cadence")
                    else:
                        recommendations.append("🎯 **Engagement Strategy:** Low engagement - try different hook or value prop")

                    # Next action timing
                    if ctx.last_contact_date:
                        days_since = (datetime.now() - ctx.last_contact_date.replace(tzinfo=None)).days
                        if days_since < 7:
                            recommendations.append(f"📧 **Next Contact:** Recent contact ({days_since}d ago) - wait a few more days")
                        else:
                            recommendations.append(f"📧 **Next Contact:** {days_since} days since last contact - good time to reach out!")

                    for rec in recommendations:
                        st.markdown(f"- {rec}")

                else:
                    st.info("No timing data available for this investor")
            else:
                st.info("No timing patterns available. Run analysis to generate insights.")

        with tab4:
            st.subheader("📈 Investor Relationship Report")

            if results.retrospective_report:
                st.markdown(results.retrospective_report)

                st.download_button(
                    label="📥 Download Report",
                    data=results.retrospective_report,
                    file_name=f"advanced_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
            else:
                st.info("No report generated")

elif analysis_mode == "Complete Intelligence Audit":
    st.header("🧠 Complete Fundraising Intelligence Audit")
    st.markdown("**Multi-Step LangGraph Analysis** • Comprehensive investor analysis across all conversations")
    
    # Clear any campaign dependencies - this analysis is independent
    if "selected_campaign" in st.session_state:
        del st.session_state["selected_campaign"]
    
    # No prerequisites needed - Complete Intelligence Audit works with existing thread data
    
    # Main analysis button
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("🚀 Run Complete Intelligence Analysis", type="primary", use_container_width=True):
            st.session_state["run_intelligence_analysis"] = True
            st.rerun()
    
    with col2:
        if st.button("🔄 Reset Analysis"):
            # Clear all analysis data
            keys_to_clear = [k for k in st.session_state.keys() if k.startswith("intelligence_")]
            for key in keys_to_clear:
                del st.session_state[key]
            st.success("Analysis data cleared!")
            st.rerun()
    
    # Run the complete intelligence analysis
    if st.session_state.get("run_intelligence_analysis", False):
        st.markdown("---")
        
        # Progress tracking
        progress_container = st.container()
        status_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        # Run analysis
        if "intelligence_results" not in st.session_state:
            try:
                with status_container:
                    st.info("🔄 Initializing Fundraising Intelligence Engine...")
                
                # Initialize engine
                engine = get_fundraising_intelligence_engine()
                gmail_client = GmailClient()
                
                status_text.text("🧠 Phase 1: Analyzing existing thread data...")
                progress_bar.progress(10)
                
                # Get the actual mailbox from thread data for authentication
                # This ensures we use the same authenticated mailbox that retrieved the threads
                thread_data = st.session_state.get("selected_thread", {})
                actual_mailbox = thread_data.get("mailbox") or st.session_state.get("user_email", "")
                
                if not actual_mailbox:
                    st.error("Could not determine mailbox for analysis. Please select a thread from Email Search first.")
                    st.stop()
                
                # Run complete analysis
                async def run_analysis():
                    return await engine.run_intelligence_analysis(
                        gmail_client=gmail_client,
                        mailbox=actual_mailbox,
                        user_email=actual_mailbox,
                        company_context=company_context or "No specific company context provided",
                        time_window_days=time_window
                    )
                
                # Execute async analysis
                results = asyncio.run(run_analysis())
                
                progress_bar.progress(100)
                status_text.text("✅ Analysis complete!")
                
                # Store results
                st.session_state["intelligence_results"] = results
                st.session_state["run_intelligence_analysis"] = False
                
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Analysis failed: {str(e)}")
                st.session_state["run_intelligence_analysis"] = False
    
    # Display results if available
    if "intelligence_results" in st.session_state:
        results = st.session_state["intelligence_results"]
        
        # Overview metrics
        st.markdown("### 📊 Intelligence Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            investor_contexts = results.get("investor_contexts", {}) if isinstance(results, dict) else (results.investor_contexts or {})
            total_investors = len(investor_contexts)
            st.metric("Total Investors", total_investors)
        
        with col2:
            total_emails = sum(ctx.total_emails_sent for ctx in investor_contexts.values()) if investor_contexts else 0
            st.metric("Emails Sent", total_emails)
        
        with col3:
            total_replies = sum(ctx.total_replies_received for ctx in investor_contexts.values()) if investor_contexts else 0
            st.metric("Replies Received", total_replies)
        
        with col4:
            reply_rate = (total_replies / total_emails * 100) if total_emails > 0 else 0
            st.metric("Reply Rate", f"{reply_rate:.1f}%")
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["👥 Investor Insights", "📧 Campaign Strategies", "📈 Retrospective Report", "⏰ Timing Analysis"])
        
        with tab1:
            st.subheader("👥 Investor Relationship Insights")
            
            if investor_contexts:
                # Relationship stage breakdown
                stage_data = {}
                for ctx in investor_contexts.values():
                    stage = ctx.relationship_stage
                    stage_data[stage] = stage_data.get(stage, 0) + 1
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Relationship Stages:**")
                    for stage, count in stage_data.items():
                        st.write(f"• {stage.title()}: {count} investors")
                
                with col2:
                    sentiment_data = {}
                    for ctx in investor_contexts.values():
                        sentiment = ctx.sentiment_trend
                        sentiment_data[sentiment] = sentiment_data.get(sentiment, 0) + 1
                    
                    st.markdown("**Sentiment Distribution:**")
                    for sentiment, count in sentiment_data.items():
                        emoji = "😊" if sentiment == "positive" else "😐" if sentiment == "neutral" else "😔"
                        st.write(f"• {emoji} {sentiment.title()}: {count} investors")
                
                # Individual investor details
                st.markdown("### 📋 Individual Investor Contexts")
                
                for email, ctx in investor_contexts.items():
                    with st.expander(f"{ctx.name or email} - {ctx.firm or 'Unknown Firm'} ({ctx.relationship_stage})"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Email:** {ctx.email}")
                            st.write(f"**Sentiment:** {ctx.sentiment_trend}")
                            st.write(f"**Emails Sent:** {ctx.total_emails_sent}")
                            st.write(f"**Replies:** {ctx.total_replies_received}")
                            if ctx.last_contact_date:
                                st.write(f"**Last Contact:** {ctx.last_contact_date.strftime('%Y-%m-%d')}")
                        
                        with col2:
                            if ctx.key_interests:
                                st.write(f"**Interests:** {', '.join(ctx.key_interests)}")
                            if ctx.questions_asked:
                                st.write(f"**Questions:** {', '.join(ctx.questions_asked)}")
                            if ctx.next_action_suggested:
                                st.write(f"**Next Action:** {ctx.next_action_suggested}")
                        
                        if ctx.conversation_summary:
                            st.markdown(f"**Summary:** {ctx.conversation_summary}")
        
        with tab2:
            st.subheader("📧 Generated Campaign Strategies")
            
            campaign_strategies = results.get("campaign_strategies", []) if isinstance(results, dict) else (results.campaign_strategies or [])
            
            
            if campaign_strategies:
                for i, strategy in enumerate(campaign_strategies):
                    with st.expander(f"{strategy.investor_email} - {strategy.strategy_type.replace('_', ' ').title()}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown("**📧 Email Draft:**")
                            st.text_area("Email Content", strategy.email_draft, height=150, key=f"email_{i}", label_visibility="collapsed")
                            
                            if strategy.linkedin_message:
                                st.markdown("**💼 LinkedIn Message:**")
                                st.text_area("LinkedIn Content", strategy.linkedin_message, height=100, key=f"linkedin_{i}", label_visibility="collapsed")
                        
                        with col2:
                            st.markdown("**📊 Strategy Details:**")
                            st.write(f"**Type:** {strategy.strategy_type.replace('_', ' ').title()}")
                            st.write(f"**Confidence:** {strategy.confidence_score:.1%}")
                            st.write(f"**Expected Response:** {strategy.expected_response_rate:.1%}")
                            st.write(f"**Recommended Time:** {strategy.recommended_timing.strftime('%Y-%m-%d %H:%M')}")
                            
                            if strategy.channel_sequence:
                                st.write(f"**Channel Sequence:** {' → '.join(strategy.channel_sequence)}")
                        
                        if strategy.reasoning:
                            st.markdown("**🧠 Reasoning:**")
                            st.markdown(strategy.reasoning)
                        
                        # Action buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"📋 Copy Email", key=f"copy_email_{i}"):
                                st.success("Email copied to clipboard!")
                        with col2:
                            if st.button(f"📅 Schedule Send", key=f"schedule_{i}"):
                                st.info("Scheduling feature coming soon!")
            else:
                st.info("No campaign strategies generated. Enable strategy generation in settings.")
        
        with tab3:
            st.subheader("📈 Comprehensive Retrospective Report")
            
            retrospective_report = results.get("retrospective_report", "") if isinstance(results, dict) else (results.retrospective_report or "")
            if retrospective_report:
                # Display the report
                st.markdown(retrospective_report)
                
                # Export options
                col1, col2 = st.columns(2)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                with col1:
                    st.download_button(
                        label="📥 Download as Markdown (.md)",
                        data=retrospective_report,
                        file_name=f"fundraising_retrospective_{timestamp}.md",
                        mime="text/markdown"
                    )
                
                with col2:
                    # Convert markdown to plain text for TXT export
                    import re
                    plain_text = re.sub(r'[#*`_]', '', retrospective_report)
                    plain_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', plain_text)
                    plain_text = re.sub(r'\n+', '\n', plain_text).strip()
                    
                    st.download_button(
                        label="📄 Download as Text (.txt)",
                        data=plain_text,
                        file_name=f"fundraising_retrospective_{timestamp}.txt",
                        mime="text/plain"
                    )
                
                # Show key metrics from the report
                st.markdown("---")
                st.markdown("### 📊 Quick Metrics Overview")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Investors", len(investor_contexts))
                with col2:
                    total_emails = sum(ctx.total_emails_sent for ctx in investor_contexts.values()) if investor_contexts else 0
                    st.metric("Total Emails Sent", total_emails)
                with col3:
                    total_replies = sum(ctx.total_replies_received for ctx in investor_contexts.values()) if investor_contexts else 0
                    reply_rate = (total_replies / total_emails * 100) if total_emails > 0 else 0
                    st.metric("Overall Reply Rate", f"{reply_rate:.1f}%")
                    
            else:
                st.info("No retrospective report available. Run the Complete Intelligence Analysis to generate comprehensive reports.")
        
        with tab4:
            st.subheader("⏰ Timing Analysis & Optimization")
            
            timing_patterns = results.get("timing_patterns", {}) if isinstance(results, dict) else (results.timing_patterns or {})
            if timing_patterns:
                # Overall timing insights
                st.markdown("### 🎯 Optimal Send Time Recommendations")
                
                # Calculate best overall times
                all_hours = []
                all_days = []
                fast_responders = []
                
                for investor_email, pattern in timing_patterns.items():
                    if pattern.get("total_replies", 0) > 0:
                        all_hours.append(pattern.get("preferred_hour", 10))
                        all_days.append(pattern.get("preferred_day", "tuesday"))
                        if pattern.get("avg_response_hours", 24) < 24:
                            fast_responders.append(investor_email)
                
                if all_hours and all_days:
                    # Find most common optimal times
                    from collections import Counter
                    hour_counts = Counter(all_hours)
                    day_counts = Counter(all_days)
                    
                    best_hour = hour_counts.most_common(1)[0][0] if hour_counts else 10
                    best_day = day_counts.most_common(1)[0][0] if day_counts else "tuesday"
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("🕒 Best Send Time", f"{best_hour}:00")
                    with col2:
                        st.metric("📅 Best Send Day", best_day.title())
                    with col3:
                        avg_response_time = sum(p.get("avg_response_hours", 24) for p in timing_patterns.values()) / len(timing_patterns)
                        if avg_response_time < 24:
                            st.metric("⚡ Avg Response Time", f"{avg_response_time:.1f}h")
                        else:
                            st.metric("⚡ Avg Response Time", f"{avg_response_time/24:.1f}d")
                    with col4:
                        st.metric("🚀 Fast Responders", len(fast_responders))
                    
                    # Timing recommendations
                    st.markdown("### 💡 Actionable Timing Insights")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**🎯 Send Time Strategy:**")
                        
                        # Generate send time recommendations
                        if best_hour < 9:
                            time_insight = "🌅 Early morning emails work best - investors likely check email before meetings"
                        elif best_hour < 12:
                            time_insight = "☀️ Mid-morning is optimal - catching investors during planning time"
                        elif best_hour < 14:
                            time_insight = "🕐 Lunch time sends work well - brief window between meetings"
                        elif best_hour < 17:
                            time_insight = "🌆 Afternoon sends effective - end of business day review"
                        else:
                            time_insight = "🌙 Evening emails get attention - after-hours reviewing"
                        
                        st.info(time_insight)
                        
                        if best_day in ["monday", "friday"]:
                            day_insight = "⚠️ Consider mid-week alternatives - start/end of week can be busy"
                        elif best_day in ["tuesday", "wednesday", "thursday"]:
                            day_insight = "✅ Excellent choice - mid-week timing typically optimal"
                        else:
                            day_insight = "📋 Weekend timing - consider investor preference for business vs. personal time"
                        
                        st.info(day_insight)
                    
                    with col2:
                        st.markdown("**⚡ Response Speed Insights:**")
                        
                        timing_patterns = results.get("timing_patterns", {}) if isinstance(results, dict) else (results.timing_patterns or {})
                        timing_patterns_count = len(timing_patterns) if timing_patterns else 1  # Avoid division by zero
                        if len(fast_responders) > timing_patterns_count * 0.5:
                            speed_insight = "🚀 High engagement - most investors respond quickly. Strike while hot!"
                        elif len(fast_responders) > 0:
                            speed_insight = f"⚡ {len(fast_responders)} fast responders identified - prioritize follow-ups"
                        else:
                            speed_insight = "🐌 Slow response pattern - consider shorter, more compelling messages"
                        
                        st.info(speed_insight)
                        
                        # Next best action
                        if avg_response_time < 4:
                            action_insight = "🎯 Send follow-ups within 2-3 hours of replies for maximum momentum"
                        elif avg_response_time < 24:
                            action_insight = "📅 Schedule follow-ups for same day to maintain conversation flow"
                        else:
                            action_insight = "⏰ Allow 1-2 days between exchanges - give investors time to process"
                        
                        st.success(action_insight)
                
                st.markdown("---")
                st.markdown("### 📊 Individual Investor Patterns")
                
                timing_patterns_for_display = results.get("timing_patterns", {}) if isinstance(results, dict) else (results.timing_patterns or {})
                for investor_email, pattern in timing_patterns_for_display.items():
                    investor_contexts = results.get("investor_contexts", {}) if isinstance(results, dict) else (results.investor_contexts or {})
                    ctx = investor_contexts.get(investor_email, None)
                    name = ctx.name if ctx and ctx.name else investor_email.split('@')[0].title()
                    
                    with st.expander(f"{name} - Personalized Timing Profile"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            preferred_day = pattern.get("preferred_day", "Unknown").title()
                            st.metric("📅 Preferred Day", preferred_day)
                            
                            # Day-specific recommendation
                            if preferred_day.lower() == "monday":
                                day_tip = "🌟 Monday sends - catch them planning the week"
                            elif preferred_day.lower() == "friday":
                                day_tip = "🎯 Friday timing - end-of-week review opportunity"
                            elif preferred_day.lower() in ["tuesday", "wednesday", "thursday"]:
                                day_tip = "✅ Mid-week optimal - focused attention window"
                            else:
                                day_tip = "📅 Consistent timing builds expectation"
                            
                            st.caption(day_tip)
                        
                        with col2:
                            preferred_hour = pattern.get("preferred_hour", 10)
                            time_str = f"{preferred_hour}:00"
                            st.metric("🕒 Preferred Time", time_str)
                            
                            # Time-specific recommendation
                            if preferred_hour < 8:
                                time_tip = "🌅 Early bird - respects focused morning time"
                            elif preferred_hour < 12:
                                time_tip = "☀️ Morning person - catches peak attention"
                            elif preferred_hour < 17:
                                time_tip = "🌆 Business hours - professional timing"
                            else:
                                time_tip = "🌙 After-hours - may prefer evening review"
                            
                            st.caption(time_tip)
                        
                        with col3:
                            avg_hours = pattern.get("avg_response_hours", 0)
                            if avg_hours < 24:
                                st.metric("⚡ Response Speed", f"{avg_hours:.1f}h")
                                speed_level = "🚀 Fast" if avg_hours < 4 else "⚡ Quick" if avg_hours < 12 else "📅 Same Day"
                            else:
                                st.metric("⚡ Response Speed", f"{avg_hours/24:.1f}d")
                                speed_level = "🐌 Deliberate" if avg_hours < 72 else "🤔 Thoughtful"
                            
                            st.caption(speed_level)
                        
                        # Additional insights
                        response_rate = pattern.get("response_rate", 0)
                        total_replies = pattern.get("total_replies", 0)
                        
                        insight_col1, insight_col2 = st.columns(2)
                        
                        with insight_col1:
                            st.write(f"**📈 Response Rate:** {response_rate:.1%}")
                            if response_rate > 0.7:
                                st.success("🌟 Highly engaged - maintain current approach")
                            elif response_rate > 0.3:
                                st.info("📊 Moderate engagement - room for optimization")
                            else:
                                st.warning("📉 Low engagement - consider strategy change")
                        
                        with insight_col2:
                            st.write(f"**💬 Total Interactions:** {total_replies}")
                            if total_replies > 5:
                                st.success("🔄 Strong conversation history")
                            elif total_replies > 2:
                                st.info("💬 Building relationship")
                            else:
                                st.warning("🆕 Early stage interaction")
                
            else:
                st.info("No timing patterns available yet. Run the Complete Intelligence Analysis with email data to generate timing insights.")
        
        # Errors display
        errors = results.get("errors", []) if isinstance(results, dict) else (results.errors or [])
        if errors:
            st.markdown("### ⚠️ Analysis Warnings")
            for error in errors:
                st.warning(error)
    
    # Quick actions
    if st.button("🏠 Back to Home"):
        st.switch_page("Home.py")
    
    if st.button("🔍 Back to Email Search"):
        st.switch_page("pages/EmailSearch.py")

# Footer
st.markdown("---")
st.markdown("**🤖 AI-Powered Fundraising Intelligence** - Built with LangGraph")

# REMOVED DUPLICATE UI - All analysis now happens in the main sections above
# The Single Thread Analysis section provides comprehensive analysis, strategies, timing patterns, and reports
# The Complete Intelligence Audit section provides multi-investor analysis

# Backup old tab-based UI code (lines 950-1296) has been removed for simplicity
# User feedback: "too many buttons and options...simple and effective"

