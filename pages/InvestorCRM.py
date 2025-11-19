"""
Investor CRM Dashboard
Relationship management and health tracking for analyzed investors
"""

import os
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Load environment
_PROJECT_ROOT = Path(__file__).parent.parent
_env_name = os.getenv("ENVIRONMENT", "development")
load_dotenv(_PROJECT_ROOT / f".env.{_env_name}", override=False)
load_dotenv(_PROJECT_ROOT / ".env", override=False)

# Add utils to path
sys.path.append(str(_PROJECT_ROOT))
from utils.investor_crm import InvestorCRM

st.set_page_config(page_title="Investor CRM", layout="wide", page_icon="💼")

# Page header
st.title("💼 Investor Relationship Manager")
st.markdown("Track and manage your active investor pipeline with health scores and insights")

# Initialize CRM
try:
    crm = InvestorCRM()
except Exception as e:
    st.error(f"Failed to initialize CRM: {str(e)}")
    st.info("Make sure you have created the 'Investors' table in your Airtable base")
    st.stop()

# Sidebar filters
with st.sidebar:
    # st.markdown("## 🎯 Filters")

    # view_mode = st.radio(
    #     "View:",
    #     ["All Investors", "Needs Attention", "Hot Leads", "By Stage", "By Firm"],
    #     index=0
    # )

    # if view_mode == "By Stage":
    #     selected_stage = st.selectbox(
    #         "Select Stage:",
    #         ["Cold Outreach", "Follow Up", "Engaged", "Due Diligence", "Negotiation", "Closed Won", "Closed Lost"]
    #     )

    # st.markdown("---")

    # status_filter = st.selectbox(
    #     "Status:",
    #     ["Active", "Paused", "Closed", "All"],
    #     index=0
    # )

    # Default values when filters are commented out
    view_mode = "All Investors"
    status_filter = "Active"
    selected_stage = None

    st.markdown("---")

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

    st.markdown("---")

    # Retrospective Intelligence Report Section
    st.markdown("### 📊 Pipeline Reports")

    if st.button("📈 Retrospective Report", use_container_width=True, type="primary", key="sidebar_report_btn"):
        st.session_state["generate_monthly_report"] = True
        st.rerun()

    st.caption("Analyzes all investors with AI insights")

    st.markdown("---")

    if st.button("🏠 Back to Home", use_container_width=True):
        st.switch_page("Home.py")

# Load investors based on view mode
with st.spinner("Loading investor data..."):
    if view_mode == "All Investors":
        status_value = None if status_filter == "All" else status_filter
        investors = crm.get_all_investors(status=status_value)
    elif view_mode == "Needs Attention":
        investors = crm.get_needs_attention()
    elif view_mode == "Hot Leads":
        investors = crm.get_investors_by_health(70, 100)
    elif view_mode == "By Stage":
        investors = crm.get_investors_by_stage(selected_stage)
    else:  # By Firm
        investors = crm.get_all_investors(status=status_filter if status_filter != "All" else None)

# Pipeline Overview
st.markdown("### 📊 Pipeline Health Overview")

if investors:
    # Calculate metrics
    total_count = len(investors)
    hot_count = len([i for i in investors if i.get('fields', {}).get('health_score', 0) >= 70])
    warm_count = len([i for i in investors if 40 <= i.get('fields', {}).get('health_score', 0) < 70])
    cold_count = len([i for i in investors if i.get('fields', {}).get('health_score', 0) < 40])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Tracked", total_count)
    with col2:
        st.metric("🔥 Hot (70-100)", hot_count)
    with col3:
        st.metric("⚡ Warm (40-69)", warm_count)
    with col4:
        st.metric("❄️ Cold (0-39)", cold_count)

    # Health distribution bar
    if total_count > 0:
        hot_pct = (hot_count / total_count) * 100
        warm_pct = (warm_count / total_count) * 100
        cold_pct = (cold_count / total_count) * 100

        st.markdown("**Pipeline Distribution:**")
        st.progress(hot_pct / 100, text=f"🔥 Hot: {hot_pct:.0f}%")
        st.progress(warm_pct / 100, text=f"⚡ Warm: {warm_pct:.0f}%")
        st.progress(cold_pct / 100, text=f"❄️ Cold: {cold_pct:.0f}%")

    st.markdown("---")

    # Prominent Report Generation Button
    st.markdown("### 📊 Pipeline Intelligence Report")
    st.markdown("Generate a comprehensive retrospective report analyzing all investors you're tracking")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if st.button("📈 Generate Retrospective Report", type="primary", use_container_width=True, key="main_report_btn"):
            st.session_state["generate_monthly_report"] = True
            st.rerun()

    with col2:
        st.caption("Analyzes all tracked investors with AI-powered insights, specific recommendations by investor name, and actionable priorities")

st.markdown("---")

# Quick Action Views
if view_mode == "Needs Attention":
    st.markdown("### 🚨 Investors Needing Attention")

    if not investors:
        st.success("🎉 All relationships are healthy! No immediate actions needed.")
    else:
        st.warning(f"⚠️ {len(investors)} investors need your attention")

        for record in investors:
            fields = record.get('fields', {})
            alerts = record.get('alerts', [])

            health_score = fields.get('health_score', 0)
            name = fields.get('name', 'Unknown')
            email = fields.get('email', '')
            firm = fields.get('firm', '')

            # Health score emoji
            if health_score >= 80:
                health_emoji = "🔥"
            elif health_score >= 60:
                health_emoji = "⚡"
            elif health_score >= 40:
                health_emoji = "📋"
            else:
                health_emoji = "❄️"

            with st.expander(f"{health_emoji} {name} ({firm}) - Score: {health_score}", expanded=True):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.write(f"**Email:** {email}")
                    st.write(f"**Stage:** {fields.get('stage', 'Unknown')}")
                    st.write(f"**Sentiment:** {fields.get('sentiment', 'Unknown')}")
                    st.write(f"**Last Contact:** {fields.get('last_contact_date', 'Never')}")

                    # Show alerts
                    if alerts:
                        st.markdown("**🚨 Alerts:**")
                        for alert in alerts:
                            priority_emoji = "🔴" if alert['priority'] == 'high' else "🟡"
                            st.markdown(f"- {priority_emoji} {alert['message']}")

                with col2:
                    if st.button("📧 Draft Follow-up", key=f"draft_{record['id']}"):
                        st.session_state["selected_investor"] = record
                        st.session_state["compose_email_for"] = email
                        st.session_state["show_email_composer"] = True
                        st.switch_page("pages/InvestorProfile.py")

                    if st.button("📊 View Full Profile", key=f"profile_{record['id']}"):
                        st.session_state["selected_investor"] = record
                        st.switch_page("pages/InvestorProfile.py")

elif view_mode == "Hot Leads":
    st.markdown("### 🔥 Hot Leads - Strike While Hot!")

    if not investors:
        st.info("No hot leads at the moment. Keep nurturing your pipeline!")
    else:
        st.success(f"🔥 {len(investors)} hot leads ready for action")

        for record in investors:
            fields = record.get('fields', {})

            health_score = fields.get('health_score', 0)
            name = fields.get('name', 'Unknown')
            email = fields.get('email', '')
            firm = fields.get('firm', '')
            trending = fields.get('trending', 'Stable')

            trending_emoji = "⬆️" if trending == "Up" else "⬇️" if trending == "Down" else "➡️"

            with st.expander(f"🔥 {health_score} {trending_emoji} {name} ({firm})", expanded=False):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**Email:** {email}")
                    st.write(f"**Stage:** {fields.get('stage', 'Unknown')}")
                    st.write(f"**Sentiment:** {fields.get('sentiment', 'Unknown')}")

                with col2:
                    st.write(f"**Reply Rate:** {fields.get('reply_rate', 0):.0%}")
                    st.write(f"**Avg Response:** {fields.get('avg_response_hours', 0):.1f}h")
                    st.write(f"**Last Contact:** {fields.get('last_contact_date', 'Never')}")

                with col3:
                    if st.button("📧 Reply Now", key=f"reply_{record['id']}", type="primary"):
                        st.session_state["selected_investor"] = record
                        st.session_state["compose_email_for"] = email
                        st.session_state["show_email_composer"] = True
                        st.switch_page("pages/InvestorProfile.py")

                    if st.button("📊 View Profile", key=f"view_{record['id']}"):
                        st.session_state["selected_investor"] = record
                        st.switch_page("pages/InvestorProfile.py")

else:  # All Investors, By Stage, or By Firm
    st.markdown(f"### 👥 {view_mode}")

    if not investors:
        st.info("No investors found. Analyze some email threads to populate your CRM!")
        if st.button("🔍 Go to Thread Analysis"):
            st.switch_page("pages/ThreadAnalysis.py")
    else:
        # Search functionality
        search_query = st.text_input("🔍 Search investors", placeholder="Search by name, email, or firm...")

        # Filter by search
        if search_query:
            filtered_investors = []
            for inv in investors:
                fields = inv.get('fields', {})
                searchable = f"{fields.get('name', '')} {fields.get('email', '')} {fields.get('firm', '')}".lower()
                if search_query.lower() in searchable:
                    filtered_investors.append(inv)
        else:
            filtered_investors = investors

        st.info(f"Showing {len(filtered_investors)} of {len(investors)} investors")

        # Display investors in a clean list
        for record in filtered_investors:
            fields = record.get('fields', {})

            health_score = fields.get('health_score', 0)
            name = fields.get('name', 'Unknown')
            email = fields.get('email', '')
            firm = fields.get('firm', '')
            stage = fields.get('stage', 'Unknown')
            sentiment = fields.get('sentiment', 'Unknown')
            trending = fields.get('trending', 'Stable')
            last_contact = fields.get('last_contact_date', 'Never')

            # Health emoji
            if health_score >= 70:
                health_emoji = "🔥"
                health_color = "#00ff00"
            elif health_score >= 40:
                health_emoji = "⚡"
                health_color = "#ffaa00"
            else:
                health_emoji = "❄️"
                health_color = "#ff0000"

            # Trending emoji
            trending_emoji = "⬆️" if trending == "Up" else "⬇️" if trending == "Down" else "➡️"

            # Sentiment emoji
            sentiment_emoji = "😊" if sentiment == "Positive" else "😐" if sentiment == "Neutral" else "😔"

            # Container for each investor
            with st.container():
                col1, col2, col3, col4, col5, col6 = st.columns([0.5, 2, 1.5, 1, 1, 1])

                with col1:
                    st.markdown(f"<h2 style='color:{health_color};'>{health_emoji} {health_score}</h2>", unsafe_allow_html=True)
                    st.caption(f"{trending_emoji}")

                with col2:
                    st.markdown(f"**{name}**")
                    st.caption(f"{firm}")
                    st.caption(f"📧 {email}")

                with col3:
                    st.write(f"**Stage:** {stage}")
                    st.caption(f"{sentiment_emoji} {sentiment}")

                with col4:
                    st.write(f"**Reply Rate:** {fields.get('reply_rate', 0):.0%}")
                    st.caption(f"Avg: {fields.get('avg_response_hours', 0):.0f}h")

                with col5:
                    st.write(f"**Last Contact:**")
                    st.caption(f"{last_contact}")

                with col6:
                    if st.button("View", key=f"btn_{record['id']}", use_container_width=True):
                        st.session_state["selected_investor"] = record
                        # For now, show in expander since we haven't built the profile page yet
                        st.session_state[f"expand_{record['id']}"] = True
                        st.rerun()

                # Expandable details
                if st.session_state.get(f"expand_{record['id']}", False):
                    with st.expander("📋 Details", expanded=True):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("**🎯 Interests:**")
                            interests = fields.get('interests', '')
                            if interests:
                                for interest in interests.split('\n'):
                                    if interest.strip():
                                        st.write(f"• {interest}")
                            else:
                                st.write("No interests recorded")

                            st.markdown("**⚠️ Concerns:**")
                            concerns = fields.get('concerns', '')
                            if concerns:
                                for concern in concerns.split('\n'):
                                    if concern.strip():
                                        st.write(f"• {concern}")
                            else:
                                st.write("No concerns recorded")

                        with col2:
                            st.markdown("**📝 Conversation Summary:**")
                            summary = fields.get('conversation_summary', 'No summary available')
                            st.write(summary)

                            st.markdown("**💡 Next Action:**")
                            next_action = fields.get('next_action', 'No action suggested')
                            st.write(next_action)

                        # Close button
                        if st.button("Close", key=f"close_{record['id']}"):
                            st.session_state[f"expand_{record['id']}"] = False
                            st.rerun()

                st.markdown("---")

# Monthly Intelligence Report Generation
if st.session_state.get("generate_monthly_report", False):
    st.markdown("---")
    st.markdown("# 📊 Monthly Pipeline Intelligence Report")

    with st.spinner("🤖 Generating comprehensive AI-powered intelligence report..."):
        try:
            # Get company context (you can make this configurable)
            company_context = st.session_state.get("company_context", "")

            # Allow user to set date range or use all-time
            col1, col2, col3 = st.columns([1, 1, 1])

            with col1:
                use_date_range = st.checkbox("Filter by date range", value=False)

            if use_date_range:
                with col2:
                    start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
                with col3:
                    end_date = st.date_input("End Date", datetime.now())

                date_range = (datetime.combine(start_date, datetime.min.time()),
                             datetime.combine(end_date, datetime.max.time()))
            else:
                date_range = None

            # Generate report
            report_result = crm.generate_monthly_intelligence_report(
                date_range=date_range,
                include_all_time=not use_date_range,
                company_context=company_context
            )

            if report_result.get("success"):
                metrics = report_result.get("metrics", {})
                visualizations = report_result.get("visualizations", {})
                report_markdown = report_result.get("report", "")

                # Display dashboard visualizations
                st.markdown("## 📊 Dashboard Overview")

                # Key metrics row
                col1, col2, col3, col4, col5 = st.columns(5)

                with col1:
                    st.metric(
                        "Total Investors",
                        metrics.get('total_investors', 0),
                        delta=None
                    )

                with col2:
                    st.metric(
                        "🔥 Hot Leads",
                        metrics.get('hot_leads_count', 0),
                        delta=f"{metrics.get('trending_up_count', 0)} trending up" if metrics.get('trending_up_count', 0) > 0 else None
                    )

                with col3:
                    reply_rate = metrics.get('overall_reply_rate', 0)
                    st.metric(
                        "Reply Rate",
                        f"{reply_rate:.1%}",
                        delta="Good" if reply_rate > 0.4 else "Needs Work",
                        delta_color="normal" if reply_rate > 0.4 else "inverse"
                    )

                with col4:
                    positive_rate = (metrics.get('positive_sentiment_count', 0) / metrics.get('total_investors', 1)) * 100
                    st.metric(
                        "Positive Sentiment",
                        f"{positive_rate:.0f}%",
                        delta="Healthy" if positive_rate > 50 else "Monitor",
                        delta_color="normal" if positive_rate > 50 else "inverse"
                    )

                with col5:
                    avg_response = metrics.get('avg_response_time_hours', 0)
                    st.metric(
                        "Avg Response Time",
                        f"{avg_response:.1f}h",
                        delta="Fast" if avg_response < 48 else "Slow",
                        delta_color="normal" if avg_response < 48 else "inverse"
                    )

                st.markdown("---")

                # Visualizations
                viz_col1, viz_col2 = st.columns(2)

                with viz_col1:
                    # Health Score Distribution
                    st.markdown("### Health Score Distribution")
                    health_scores = visualizations.get('health_scores', [])
                    if health_scores:
                        df_health = pd.DataFrame({"Health Score": health_scores})
                        fig_health = px.histogram(
                            df_health,
                            x="Health Score",
                            nbins=20,
                            title="Distribution of Health Scores",
                            color_discrete_sequence=['#1f77b4']
                        )
                        fig_health.update_layout(
                            xaxis_title="Health Score",
                            yaxis_title="Number of Investors",
                            showlegend=False
                        )
                        st.plotly_chart(fig_health, use_container_width=True)
                    else:
                        st.info("No health score data available")

                    # Stage Funnel
                    st.markdown("### Stage Funnel")
                    stage_funnel = visualizations.get('stage_funnel', {})
                    if stage_funnel:
                        df_stages = pd.DataFrame({
                            'Stage': list(stage_funnel.keys()),
                            'Count': list(stage_funnel.values())
                        })
                        fig_funnel = px.funnel(
                            df_stages,
                            x='Count',
                            y='Stage',
                            title="Investor Stage Funnel"
                        )
                        st.plotly_chart(fig_funnel, use_container_width=True)
                    else:
                        st.info("No stage data available")

                with viz_col2:
                    # Sentiment Pie Chart
                    st.markdown("### Sentiment Distribution")
                    sentiment_dist = visualizations.get('sentiment_distribution', {})
                    if sentiment_dist and any(sentiment_dist.values()):
                        df_sentiment = pd.DataFrame({
                            'Sentiment': list(sentiment_dist.keys()),
                            'Count': list(sentiment_dist.values())
                        })
                        fig_sentiment = px.pie(
                            df_sentiment,
                            values='Count',
                            names='Sentiment',
                            title="Sentiment Breakdown",
                            color='Sentiment',
                            color_discrete_map={
                                'Positive': '#2ecc71',
                                'Neutral': '#95a5a6',
                                'Negative': '#e74c3c'
                            }
                        )
                        st.plotly_chart(fig_sentiment, use_container_width=True)
                    else:
                        st.info("No sentiment data available")

                    # Trending Analysis
                    st.markdown("### Momentum Analysis")
                    trending_data = {
                        'Trending Up': metrics.get('trending_up_count', 0),
                        'Stable': metrics.get('total_investors', 0) - metrics.get('trending_up_count', 0) - metrics.get('trending_down_count', 0),
                        'Trending Down': metrics.get('trending_down_count', 0)
                    }
                    df_trending = pd.DataFrame({
                        'Status': list(trending_data.keys()),
                        'Count': list(trending_data.values())
                    })
                    fig_trending = px.bar(
                        df_trending,
                        x='Status',
                        y='Count',
                        title="Pipeline Momentum",
                        color='Status',
                        color_discrete_map={
                            'Trending Up': '#2ecc71',
                            'Stable': '#95a5a6',
                            'Trending Down': '#e74c3c'
                        }
                    )
                    st.plotly_chart(fig_trending, use_container_width=True)

                st.markdown("---")

                # Display full report
                st.markdown("## 📄 Detailed Report")

                # Add tabs for different sections
                tab1, tab2, tab3 = st.tabs(["📊 Full Report", "🎯 Action Items", "📈 Raw Data"])

                with tab1:
                    st.markdown(report_markdown)

                with tab2:
                    # Extract action items
                    ai_insights = report_result.get("ai_insights", {})
                    top_priorities = ai_insights.get("top_10_priorities", [])

                    if top_priorities:
                        st.markdown("### 🎯 Top 10 Action Priorities")
                        for i, priority in enumerate(top_priorities[:10], 1):
                            with st.expander(f"{i}. {priority.get('investor', 'Unknown')}", expanded=i <= 3):
                                st.write(f"**Action:** {priority.get('action', 'TBD')}")
                                st.write(f"**Timing:** {priority.get('timing', 'TBD')}")
                                st.write(f"**Rationale:** {priority.get('rationale', 'TBD')}")
                    else:
                        st.info("No action items generated")

                with tab3:
                    st.markdown("### 📊 Export Data")

                    # Create downloadable CSV
                    if investors:
                        df_export = pd.DataFrame([
                            {
                                'Name': inv.get('fields', {}).get('name', 'Unknown'),
                                'Email': inv.get('fields', {}).get('email', ''),
                                'Firm': inv.get('fields', {}).get('firm', ''),
                                'Health Score': inv.get('fields', {}).get('health_score', 0),
                                'Stage': inv.get('fields', {}).get('stage', 'Unknown'),
                                'Sentiment': inv.get('fields', {}).get('sentiment', 'Unknown'),
                                'Trending': inv.get('fields', {}).get('trending', 'Stable'),
                                'Reply Rate': inv.get('fields', {}).get('reply_rate', 0),
                                'Last Contact': inv.get('fields', {}).get('last_contact_date', 'Unknown'),
                                'Status': inv.get('fields', {}).get('status', 'Unknown')
                            }
                            for inv in investors
                        ])

                        st.dataframe(df_export, use_container_width=True)

                        # Download buttons
                        col1, col2 = st.columns(2)

                        with col1:
                            csv = df_export.to_csv(index=False)
                            st.download_button(
                                label="📥 Download CSV",
                                data=csv,
                                file_name=f"investor_pipeline_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )

                        with col2:
                            # Download markdown report
                            st.download_button(
                                label="📥 Download Report (MD)",
                                data=report_markdown,
                                file_name=f"monthly_report_{datetime.now().strftime('%Y%m%d')}.md",
                                mime="text/markdown",
                                use_container_width=True
                            )

                # Close report button
                if st.button("✖️ Close Report", use_container_width=True):
                    st.session_state["generate_monthly_report"] = False
                    st.rerun()

            else:
                st.error(f"Failed to generate report: {report_result.get('error', 'Unknown error')}")
                if st.button("✖️ Close"):
                    st.session_state["generate_monthly_report"] = False
                    st.rerun()

        except Exception as e:
            st.error(f"Error generating report: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            if st.button("✖️ Close"):
                st.session_state["generate_monthly_report"] = False
                st.rerun()

# Footer
st.markdown("---")
st.caption("💼 Investor CRM - Auto-populated from Thread Analysis")
