"""
Investor Profile Page
Comprehensive view of individual investor relationships
"""

import os
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List, Any
import sys
import plotly.graph_objects as go
import plotly.express as px

# Load environment
_PROJECT_ROOT = Path(__file__).parent.parent
_env_name = os.getenv("ENVIRONMENT", "development")
load_dotenv(_PROJECT_ROOT / f".env.{_env_name}", override=False)
load_dotenv(_PROJECT_ROOT / ".env", override=False)

# Add utils to path
sys.path.append(str(_PROJECT_ROOT))
from utils.investor_crm import InvestorCRM
from utils.gmail_client import GmailClient
from utils.email_composer_ui import show_email_composer

st.set_page_config(page_title="Investor Profile", layout="wide", page_icon="👤")

# Initialize services
try:
    crm = InvestorCRM()
    gmail_client = GmailClient()
except Exception as e:
    st.error(f"Failed to initialize services: {str(e)}")
    st.stop()

# Check if investor is selected
if "selected_investor" not in st.session_state:
    st.warning("No investor selected. Please select an investor from the CRM.")
    if st.button("🏠 Go to CRM", key="goto_crm_no_investor"):
        st.switch_page("pages/InvestorCRM.py")
    st.stop()

investor_record = st.session_state["selected_investor"]
fields = investor_record.get("fields", {})

# Extract investor data
investor_email = fields.get("email", "unknown@example.com")
investor_name = fields.get("name", "Unknown")
firm = fields.get("firm", "")
health_score = fields.get("health_score", 0)
sentiment = fields.get("sentiment", "Neutral")
stage = fields.get("stage", "Unknown")
trending = fields.get("trending", "Stable")
reply_rate = fields.get("reply_rate", 0)
avg_response_hours = fields.get("avg_response_hours", 0)
total_emails_sent = fields.get("total_emails_sent", 0)
total_replies = fields.get("total_replies_received", 0)
last_contact = fields.get("last_contact_date", "Never")
first_contact = fields.get("first_contact_date", "Unknown")
status = fields.get("status", "Active")

# Page Header
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    st.title(f"👤 {investor_name}")
    if firm:
        st.markdown(f"**{firm}**")
    st.caption(f"📧 {investor_email}")

with col2:
    # Health score badge
    if health_score >= 70:
        health_color = "#2ecc71"
        health_emoji = "🔥"
    elif health_score >= 40:
        health_color = "#f39c12"
        health_emoji = "⚡"
    else:
        health_color = "#e74c3c"
        health_emoji = "❄️"

    st.markdown(f"<div style='text-align: center;'><h1 style='color:{health_color}; margin:0;'>{health_emoji} {health_score}</h1><p style='margin:0;'>Health Score</p></div>", unsafe_allow_html=True)

with col3:
    # Trending indicator
    if trending == "Up":
        st.markdown("<div style='text-align: center;'><h1 style='color:#2ecc71; margin:0;'>⬆️</h1><p style='margin:0;'>Trending Up</p></div>", unsafe_allow_html=True)
    elif trending == "Down":
        st.markdown("<div style='text-align: center;'><h1 style='color:#e74c3c; margin:0;'>⬇️</h1><p style='margin:0;'>Trending Down</p></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align: center;'><h1 style='color:#95a5a6; margin:0;'>➡️</h1><p style='margin:0;'>Stable</p></div>", unsafe_allow_html=True)

# Quick Actions Row
st.markdown("---")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if st.button("✉️ Compose Email", use_container_width=True, type="primary", key="btn_compose_email"):
        st.session_state["compose_email_for"] = investor_email
        st.session_state["show_email_composer"] = True
        st.rerun()

with col2:
    if st.button("📝 Add Note", use_container_width=True, key="btn_add_note"):
        st.session_state["show_add_note"] = True
        st.rerun()

with col3:
    if st.button("🔄 Change Stage", use_container_width=True, key="btn_change_stage"):
        st.session_state["show_change_stage"] = True
        st.rerun()

with col4:
    if st.button("📊 Refresh Data", use_container_width=True, key="btn_refresh"):
        st.rerun()

with col5:
    if st.button("🏠 Back to CRM", use_container_width=True, key="btn_back_to_crm"):
        st.switch_page("pages/InvestorCRM.py")

st.markdown("---")

# Show Email Composer if triggered
if st.session_state.get("show_email_composer") and st.session_state.get("compose_email_for") == investor_email:
    with st.expander("✉️ Email Composer", expanded=True):
        show_email_composer(
            recipient_email=investor_email,
            investor_record=investor_record
        )
    st.markdown("---")

# Key Metrics Row
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("Stage", stage)

with col2:
    sentiment_emoji = "😊" if sentiment == "Positive" else "😐" if sentiment == "Neutral" else "😔"
    st.metric("Sentiment", f"{sentiment_emoji} {sentiment}")

with col3:
    st.metric("Reply Rate", f"{reply_rate:.0%}")

with col4:
    if avg_response_hours < 24:
        st.metric("Avg Response", f"{avg_response_hours:.1f}h")
    else:
        st.metric("Avg Response", f"{avg_response_hours/24:.1f}d")

with col5:
    st.metric("Emails Sent", total_emails_sent)

with col6:
    st.metric("Replies", total_replies)

st.markdown("---")

# Handle Add Note Modal
if st.session_state.get("show_add_note", False):
    with st.expander("📝 Add Note", expanded=True):
        note_text = st.text_area("Note", placeholder="Add your note here...", height=150, key="note_text_input")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Note", use_container_width=True, key="btn_save_note"):
                if note_text.strip():
                    # Use the CRM add_note method
                    try:
                        result = crm.add_note(investor_email, note_text)
                        if result.get("success"):
                            st.success("✅ Note saved successfully!")
                        else:
                            st.error(f"Failed to save note: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Error saving note: {str(e)}")

                    st.session_state["show_add_note"] = False
                    st.rerun()
                else:
                    st.warning("Please enter a note")

        with col2:
            if st.button("❌ Cancel", use_container_width=True, key="btn_cancel_note"):
                st.session_state["show_add_note"] = False
                st.rerun()

# Handle Change Stage Modal
if st.session_state.get("show_change_stage", False):
    with st.expander("🔄 Change Stage", expanded=True):
        new_stage = st.selectbox(
            "Select New Stage:",
            ["Cold Outreach", "Follow Up", "Engaged", "Due Diligence", "Negotiation", "Closed Won", "Closed Lost"],
            index=["Cold Outreach", "Follow Up", "Engaged", "Due Diligence", "Negotiation", "Closed Won", "Closed Lost"].index(stage) if stage in ["Cold Outreach", "Follow Up", "Engaged", "Due Diligence", "Negotiation", "Closed Won", "Closed Lost"] else 0,
            key="stage_selector"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Update Stage", use_container_width=True, key="btn_update_stage"):
                # Update stage in CRM
                try:
                    result = crm.update_investor_field(investor_email, "stage", new_stage)
                    if result.get("success"):
                        st.success(f"✅ Stage updated to {new_stage}!")
                        # Update local session state
                        st.session_state["selected_investor"]["fields"]["stage"] = new_stage
                    else:
                        st.error(f"Failed to update stage: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error updating stage: {str(e)}")

                st.session_state["show_change_stage"] = False
                st.rerun()

        with col2:
            if st.button("❌ Cancel", use_container_width=True, key="btn_cancel_stage"):
                st.session_state["show_change_stage"] = False
                st.rerun()

# Main Content Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "📧 Email Timeline", "📝 Activity Feed", "✏️ Edit Details", "🧠 AI Insights"])

with tab1:
    st.subheader("📊 Overview")

    col1, col2 = st.columns(2)

    with col1:
        # Health Score Visualization
        st.markdown("### 🎯 Health Score Breakdown")

        # Create gauge chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=health_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Relationship Health"},
            delta={'reference': 60, 'increasing': {'color': "#2ecc71"}},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': health_color},
                'steps': [
                    {'range': [0, 40], 'color': "#ffebee"},
                    {'range': [40, 70], 'color': "#fff9e6"},
                    {'range': [70, 100], 'color': "#e8f5e9"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 80
                }
            }
        ))

        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

        # Timeline Info
        st.markdown("### 📅 Timeline")
        st.write(f"**First Contact:** {first_contact}")
        st.write(f"**Last Contact:** {last_contact}")

        if last_contact != "Never":
            try:
                last_dt = datetime.fromisoformat(last_contact) if "T" in last_contact else datetime.strptime(last_contact, "%Y-%m-%d")
                days_since = (datetime.now() - last_dt).days

                if days_since == 0:
                    st.info("💬 Contacted today!")
                elif days_since == 1:
                    st.info("💬 Contacted yesterday")
                elif days_since < 7:
                    st.success(f"✅ Contacted {days_since} days ago")
                elif days_since < 14:
                    st.warning(f"⚠️ {days_since} days since last contact")
                else:
                    st.error(f"🚨 {days_since} days since last contact - follow up needed!")
            except:
                pass

    with col2:
        # Engagement Metrics
        st.markdown("### 📈 Engagement Metrics")

        # Create bar chart for email metrics
        metrics_data = {
            'Metric': ['Emails Sent', 'Replies Received'],
            'Count': [total_emails_sent, total_replies]
        }

        fig2 = px.bar(
            metrics_data,
            x='Metric',
            y='Count',
            title="Email Activity",
            color='Metric',
            color_discrete_sequence=['#3498db', '#2ecc71']
        )
        fig2.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig2, use_container_width=True)

        # Status and Context
        st.markdown("### ℹ️ Status")
        st.write(f"**Current Status:** {status}")

        # Alerts
        alerts = investor_record.get("alerts", [])
        if alerts:
            st.markdown("### 🚨 Alerts")
            for alert in alerts:
                priority = alert.get("priority", "medium")
                message = alert.get("message", "No message")

                if priority == "high":
                    st.error(f"🔴 {message}")
                else:
                    st.warning(f"🟡 {message}")
        else:
            st.success("✅ No alerts - relationship healthy!")

    # Interests and Concerns
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🎯 Key Interests")
        interests = fields.get("interests", "")
        if interests:
            for interest in interests.split("\n"):
                if interest.strip():
                    st.write(f"• {interest}")
        else:
            st.info("No interests recorded yet")

    with col2:
        st.markdown("### ⚠️ Concerns Raised")
        concerns = fields.get("concerns", "")
        if concerns:
            for concern in concerns.split("\n"):
                if concern.strip():
                    st.write(f"• {concern}")
        else:
            st.info("No concerns recorded")

    # Summary and Next Actions
    st.markdown("---")
    st.markdown("### 📝 Conversation Summary")
    summary = fields.get("conversation_summary", "No summary available")
    st.write(summary)

    st.markdown("### 💡 Recommended Next Action")
    next_action = fields.get("next_action", "")

    # Generate smart recommendation if none exists
    if not next_action or next_action.strip() == "":
        # Generate based on current state
        recommendations = []

        # Check last contact date
        if last_contact and last_contact != "Never":
            try:
                if "T" in last_contact:
                    last_dt = datetime.fromisoformat(last_contact)
                else:
                    last_dt = datetime.strptime(last_contact, "%Y-%m-%d")

                days_since = (datetime.now() - last_dt).days

                if days_since >= 14:
                    recommendations.append(f"⏰ Follow up immediately - {days_since} days since last contact")
                elif days_since >= 7:
                    recommendations.append(f"📧 Send a check-in email - {days_since} days since last contact")
            except:
                pass

        # Based on stage
        if stage == "Cold Outreach":
            recommendations.append("🎯 Send personalized introduction highlighting relevant portfolio fit")
        elif stage == "Follow Up":
            recommendations.append("🔄 Send value-add content or recent company milestone")
        elif stage == "Engaged":
            recommendations.append("📅 Schedule a meeting to dive deeper into opportunity")
        elif stage == "Due Diligence":
            recommendations.append("📊 Provide requested materials and address any concerns")
        elif stage == "Negotiation":
            recommendations.append("💼 Review terms and prepare for close")

        # Based on sentiment
        if sentiment == "Negative":
            recommendations.append("⚠️ Address concerns raised and rebuild trust")
        elif sentiment == "Positive" and health_score >= 70:
            recommendations.append("🔥 Strike while hot - push for next steps")

        # Based on health score
        if health_score < 40:
            recommendations.append("🚨 Urgent: Relationship at risk - personalized outreach needed")

        # Show recommendations
        if recommendations:
            next_action = "\n".join([f"• {rec}" for rec in recommendations])
        else:
            next_action = "✅ Continue monitoring relationship and engage when appropriate timing signals appear"

    # Display next action
    if next_action:
        st.markdown(next_action)
    else:
        st.info("No specific action recommended at this time")

    # Tip about where recommendations come from
    st.caption("💡 Tip: Run Thread Analysis to generate AI-powered, context-aware recommendations based on actual email conversations")

with tab2:
    st.subheader("📧 Email Timeline")
    st.info("🔄 Loading email threads with this investor...")

    # Get thread IDs from investor record
    thread_ids_str = fields.get("thread_ids", "")

    if thread_ids_str:
        # Handle different formats of thread_ids
        # Could be: "thread123,thread456" or "['thread123','thread456']" or just "thread123"
        import re

        # Remove brackets and quotes if present
        cleaned = thread_ids_str.replace("[", "").replace("]", "").replace("'", "").replace('"', '')

        # Split by comma and clean
        thread_ids = [tid.strip() for tid in cleaned.split(",") if tid.strip()]

        # Debug output
        st.write(f"Found {len(thread_ids)} email thread(s)")
        if st.checkbox("Show thread IDs for debugging", key="debug_thread_ids"):
            st.code(f"Raw: {thread_ids_str}\nParsed: {thread_ids}")

        # Get mailbox - try multiple sources
        mailbox = st.session_state.get("selected_mailbox")

        # If not in session, try to get from environment (all authenticated mailboxes)
        if not mailbox:
            allowed_env = os.getenv("ALLOWED_MAILBOXES", "")
            mailboxes_list = [m.strip() for m in allowed_env.split(",") if m.strip()]

            if mailboxes_list:
                # Use the first authenticated mailbox
                mailbox = mailboxes_list[0]
                st.info(f"Using mailbox: {mailbox}")

        if not mailbox:
            st.warning("No mailbox configured. Please authenticate a mailbox first.")
            if st.button("📬 Go to Mailboxes", key="goto_mailboxes_tab2"):
                st.switch_page("pages/Mailboxes.py")
        else:
            # Display each thread
            for i, thread_id in enumerate(thread_ids[:10], 1):  # Limit to 10 most recent
                with st.expander(f"Thread {i} - {thread_id[:12]}...", expanded=i == 1):
                    try:
                        thread_data = gmail_client.get_thread(mailbox, thread_id)

                        if "error" in thread_data:
                            st.error(f"Error loading thread: {thread_data['error']}")
                        else:
                            messages = thread_data.get("messages", [])
                            st.write(f"**Messages:** {len(messages)}")

                            # Show basic info for each message
                            for msg in messages:
                                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

                                from_addr = headers.get("From", "Unknown")
                                date = headers.get("Date", "Unknown")
                                subject = headers.get("Subject", "No subject")

                                st.markdown(f"**From:** {from_addr}")
                                st.markdown(f"**Date:** {date}")
                                st.markdown(f"**Subject:** {subject}")
                                st.markdown("---")

                    except Exception as e:
                        st.error(f"Failed to load thread: {str(e)}")
    else:
        st.info("No email threads recorded yet. Analyze email threads from Email Search to populate this section.")

        if st.button("🔍 Go to Email Search", key="goto_email_search_tab2"):
            st.switch_page("pages/EmailSearch.py")

with tab3:
    st.subheader("📝 Activity Feed")

    st.info("Activity feed coming soon - will show all interactions, status changes, notes, and emails")

    # Placeholder activity items
    st.markdown("### Recent Activity")

    # Show last analyzed date if available
    last_analyzed = fields.get("last_analyzed_date", "")
    if last_analyzed:
        st.write(f"🤖 **Analysis run:** {last_analyzed}")

    if last_contact != "Never":
        st.write(f"📧 **Last email contact:** {last_contact}")

    if first_contact != "Unknown":
        st.write(f"🎯 **First contact made:** {first_contact}")

with tab4:
    st.subheader("✏️ Edit Investor Details")

    st.info("💡 Edit investor information below. Changes will be saved to Airtable.")

    with st.form("edit_investor_form"):
        edit_name = st.text_input("Name", value=investor_name)
        edit_firm = st.text_input("Firm", value=firm)
        edit_stage = st.selectbox(
            "Stage",
            ["Cold Outreach", "Follow Up", "Engaged", "Due Diligence", "Negotiation", "Closed Won", "Closed Lost"],
            index=["Cold Outreach", "Follow Up", "Engaged", "Due Diligence", "Negotiation", "Closed Won", "Closed Lost"].index(stage) if stage in ["Cold Outreach", "Follow Up", "Engaged", "Due Diligence", "Negotiation", "Closed Won", "Closed Lost"] else 0
        )
        edit_sentiment = st.selectbox("Sentiment", ["Positive", "Neutral", "Negative"], index=["Positive", "Neutral", "Negative"].index(sentiment) if sentiment in ["Positive", "Neutral", "Negative"] else 1)
        edit_status = st.selectbox("Status", ["Active", "Paused", "Closed"], index=["Active", "Paused", "Closed"].index(status) if status in ["Active", "Paused", "Closed"] else 0)

        edit_summary = st.text_area("Conversation Summary", value=fields.get("conversation_summary", ""), height=150)
        edit_next_action = st.text_area("Next Action", value=fields.get("next_action", ""), height=100)

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submitted:
            # Update investor record in Airtable
            try:
                update_data = {
                    "name": edit_name,
                    "firm": edit_firm,
                    "stage": edit_stage,
                    "sentiment": edit_sentiment,
                    "status": edit_status,
                    "conversation_summary": edit_summary,
                    "next_action": edit_next_action
                }

                result = crm.client.update_record(
                    crm.base_id,
                    crm.table_id,
                    investor_record["id"],
                    update_data
                )

                if "error" in result:
                    st.error(f"Failed to update: {result['error']}")
                else:
                    st.success("✅ Investor details updated successfully!")
                    # Update session state
                    st.session_state["selected_investor"]["fields"].update(update_data)
                    st.rerun()

            except Exception as e:
                st.error(f"Error updating investor: {str(e)}")

        if cancel:
            st.info("Changes cancelled")

with tab5:
    st.subheader("🧠 AI Insights")

    # Check if we have AI analysis results for this investor
    if "advanced_thread_analysis" in st.session_state:
        results = st.session_state["advanced_thread_analysis"]
        investor_contexts = results.investor_contexts or {}

        # Try to find this investor in the analysis
        investor_ctx = None
        for email_key, ctx in investor_contexts.items():
            if investor_email.lower() in email_key.lower() or email_key.lower() in investor_email.lower():
                investor_ctx = ctx
                break

        if investor_ctx:
            st.success("✅ AI analysis available for this investor")

            # Show timing insights
            timing_patterns = results.timing_patterns or {}
            timing = timing_patterns.get(investor_email.lower(), {})

            if timing:
                st.markdown("### ⏰ Best Time to Contact")

                col1, col2, col3 = st.columns(3)

                with col1:
                    preferred_day = timing.get("preferred_day", "Unknown").title()
                    st.metric("📅 Preferred Day", preferred_day)

                with col2:
                    preferred_hour = timing.get("preferred_hour", 10)
                    st.metric("🕒 Preferred Time", f"{preferred_hour}:00")

                with col3:
                    response_rate = timing.get("response_rate", 0)
                    st.metric("📈 Response Rate", f"{response_rate:.1%}")

            # Show AI insights about this investor
            st.markdown("### 🎯 AI Insights")

            st.info("💡 View the Strategic Action Plans in Thread Analysis for time-based recommendations (weekly/monthly/quarterly)")

            # Show key insights from analysis
            if investor_ctx:
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**🎯 Key Interests:**")
                    if investor_ctx.key_interests:
                        for interest in investor_ctx.key_interests[:5]:
                            st.write(f"• {interest}")
                    else:
                        st.write("None identified yet")

                with col2:
                    st.markdown("**⚠️ Concerns:**")
                    if investor_ctx.objections_raised:
                        for concern in investor_ctx.objections_raised[:5]:
                            st.write(f"• {concern}")
                    else:
                        st.write("None raised")
        else:
            st.info("No AI analysis available for this investor. Run Thread Analysis to generate insights.")
            if st.button("🧠 Go to Thread Analysis", key="goto_thread_analysis_tab5_no_ctx"):
                st.switch_page("pages/ThreadAnalysis.py")
    else:
        st.info("No AI analysis results in session. Analyze this investor's emails to see AI-generated insights here.")

        if st.button("🧠 Go to Thread Analysis", key="goto_thread_analysis_tab5_no_session"):
            st.switch_page("pages/ThreadAnalysis.py")

# Footer
st.markdown("---")
st.caption(f"Investor Profile - Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
