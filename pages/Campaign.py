"""
Campaign Management Page - Standalone Version
Direct Airtable integration without FastAPI backend
"""

import os
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from typing import Dict, List, Any

# Load environment
_PROJECT_ROOT = Path(__file__).parent.parent
_env_name = os.getenv("ENVIRONMENT", "development")
load_dotenv(_PROJECT_ROOT / f".env.{_env_name}", override=False)
load_dotenv(_PROJECT_ROOT / ".env", override=False)

# Add utils to path
import sys
sys.path.append(str(_PROJECT_ROOT))
from utils.airtable_client import get_airtable_client

st.set_page_config(page_title="Campaign", layout="wide")

# Check if campaign is selected
camp = st.session_state.get("selected_campaign")
if not camp:
    st.warning("No campaign selected. Go back to Home and choose a campaign.")
    if st.button("🏠 Back to Home"):
        st.switch_page("Home.py")
    st.stop()

# Initialize Airtable client
airtable = get_airtable_client()

# Campaign header
st.title(camp["name"])
total_records = camp.get("total_records", 0)
st.caption(
    f"Base: {camp.get('airtable_base_name', 'N/A')} • "
    f"Table: {camp.get('airtable_table_name', 'N/A')} • "
    f"View: {camp.get('airtable_view_name', 'N/A')} • "
    f"Records: {total_records:,}"
)

# Sidebar
with st.sidebar:
    st.markdown("## Campaign Sections")
    section = st.radio(
        "Choose section:",
        ["📧 Email", "🔗 LinkedIn"],
        index=0
    )
    
    st.markdown("---")
    if st.button("🏠 Back to Home"):
        st.switch_page("Home.py")
    
    if st.button("🔄 Refresh Data"):
        # Clear any cached data
        if "records_cache" in st.session_state:
            del st.session_state["records_cache"]
        st.rerun()

# Pagination state initialization
if "current_page" not in st.session_state:
    st.session_state.current_page = 1
if "page_size" not in st.session_state:
    st.session_state.page_size = 100
if "current_records" not in st.session_state:
    st.session_state.current_records = []
if "current_offset" not in st.session_state:
    st.session_state.current_offset = None
if "next_offset" not in st.session_state:
    st.session_state.next_offset = None

# Calculate total pages from campaign data
total_records = camp.get("total_records", 0)
page_size = st.session_state.page_size
total_pages = max(1, (total_records + page_size - 1) // page_size)

# Data loading function for single page
@st.cache_data(ttl=60)
def load_single_page(base_id: str, table_id: str, view_name: str, offset: str = None, page_size: int = 100):
    """Load a single page of records from Airtable."""
    batch = airtable.get_records(
        base_id=base_id,
        table_id=table_id, 
        view_name=view_name if view_name != "All Records (Grid view)" else None,
        page_size=page_size,
        offset=offset
    )
    return batch

# Load current page data
def load_page_data(page_num: int):
    """Load data for specific page number."""
    if page_num == 1:
        # First page - no offset needed
        batch = load_single_page(
            camp["airtable_base_id"],
            camp["airtable_table_id"],
            camp["airtable_view_name"],
            offset=None,
            page_size=page_size
        )
    else:
        # For other pages, we need to navigate from first page
        # This is a limitation of Airtable API - no direct page jumping
        # We'll store offsets as we navigate
        if f"offset_page_{page_num}" in st.session_state:
            offset = st.session_state[f"offset_page_{page_num}"]
            batch = load_single_page(
                camp["airtable_base_id"],
                camp["airtable_table_id"],
                camp["airtable_view_name"],
                offset=offset,
                page_size=page_size
            )
        else:
            # Need to navigate sequentially to this page
            st.warning(f"Need to navigate to page {page_num} sequentially. Use Next/Previous buttons.")
            return None
    
    records = batch.get("records", [])
    next_offset = batch.get("offset")
    
    # Store offset for next page
    if next_offset:
        st.session_state[f"offset_page_{page_num + 1}"] = next_offset
    
    return {"records": records, "next_offset": next_offset}

# Load initial page if needed
if not st.session_state.current_records or st.session_state.current_page != st.session_state.get("last_loaded_page", 0):
    with st.spinner(f"Loading page {st.session_state.current_page}..."):
        page_data = load_page_data(st.session_state.current_page)
        if page_data:
            st.session_state.current_records = page_data["records"]
            st.session_state.next_offset = page_data["next_offset"]
            st.session_state.last_loaded_page = st.session_state.current_page

records = st.session_state.current_records

# Pagination Controls
st.markdown("---")
col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

with col1:
    if st.button("⬅️ Previous", disabled=(st.session_state.current_page <= 1)):
        st.session_state.current_page -= 1
        st.rerun()

with col2:
    if st.button("➡️ Next", disabled=(st.session_state.current_page >= total_pages or not st.session_state.next_offset)):
        st.session_state.current_page += 1
        st.rerun()

with col3:
    st.write(f"**Page {st.session_state.current_page} of {total_pages}** ({total_records:,} total records)")

with col4:
    # Page jump input
    jump_page = st.number_input("Go to page:", min_value=1, max_value=total_pages, value=st.session_state.current_page, key="page_jump")

with col5:
    if st.button("Go") and jump_page != st.session_state.current_page:
        if jump_page > st.session_state.current_page:
            st.warning("Can only navigate forward sequentially due to Airtable API limitations. Use Next button.")
        else:
            st.session_state.current_page = jump_page
            st.rerun()

st.markdown("---")

# Global search
search_query = st.text_input(
    "🔍 Search current page",
    placeholder="Search by name, email, company...",
    help="Search within currently loaded records on this page"
)

# Filter records based on search
filtered_records = records
if search_query:
    search_lower = search_query.lower()
    filtered_records = []
    
    for record in records:
        fields = record.get("fields", {})
        # Search in common fields
        searchable_text = " ".join([
            str(fields.get("Name", "")),
            str(fields.get("Full Name", "")),
            str(fields.get("Email", "")),
            str(fields.get("Company", "")),
            str(fields.get("Organization", "")),
            str(fields.get("LinkedIn", "")),
            str(fields.get("Realtime company name", "")),
        ]).lower()
        
        if search_lower in searchable_text:
            filtered_records.append(record)

# Show record count
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Records", len(records))
with col2:
    if search_query:
        st.metric("Filtered Records", len(filtered_records))
    else:
        st.metric("Loaded Records", len(filtered_records))
with col3:
    email_count = sum(1 for r in filtered_records if r.get("fields", {}).get("Email"))
    st.metric("With Email", email_count)

# Main content based on section
if section == "📧 Email":
    st.subheader("📧 Email Correspondence")
    
    # Filter for records with email
    email_records = [r for r in filtered_records if r.get("fields", {}).get("Email")]
    
    if not email_records:
        if search_query:
            st.warning(f"No contacts with email found matching '{search_query}'")
        else:
            st.warning("No contacts with email addresses found in this campaign")
    else:
        st.success(f"Found {len(email_records)} contacts with email addresses")
        
        # Pagination
        page_size = 20
        total_pages = max(1, (len(email_records) - 1) // page_size + 1)
        
        if f"email_page_{camp['campaign_id']}" not in st.session_state:
            st.session_state[f"email_page_{camp['campaign_id']}"] = 1
        
        current_page = st.session_state[f"email_page_{camp['campaign_id']}"]
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, len(email_records))
        
        # Pagination controls
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅️ Previous", disabled=current_page <= 1, key="email_prev"):
                st.session_state[f"email_page_{camp['campaign_id']}"] = max(1, current_page - 1)
                st.rerun()
        
        with col2:
            st.write(f"Page {current_page} of {total_pages}")
        
        with col3:
            if st.button("Next ➡️", disabled=current_page >= total_pages, key="email_next"):
                st.session_state[f"email_page_{camp['campaign_id']}"] = min(total_pages, current_page + 1)
                st.rerun()
        
        # Display records
        st.markdown("---")
        
        for i, record in enumerate(email_records[start_idx:end_idx]):
            fields = record.get("fields", {})
            name = fields.get("Name") or fields.get("Full Name") or "Unknown"
            email = fields.get("Email", "")
            company = fields.get("Company") or fields.get("Organization") or fields.get("Realtime company name") or ""
            
            col1, col2, col3, col4 = st.columns([3, 4, 3, 2])
            
            with col1:
                st.write(f"**{name}**")
            with col2:
                st.write(email)
            with col3:
                st.write(company)
            with col4:
                if st.button("📧 Email", key=f"email_{start_idx + i}"):
                    st.session_state["selected_record"] = {
                        "name": name,
                        "email": email,
                        "company": company
                    }
                    st.switch_page("pages/Correspondence.py")

elif section == "🔗 LinkedIn":
    st.subheader("🔗 LinkedIn Profiles")
    
    # Create DataFrame for display
    linkedin_data = []
    for record in filtered_records:
        fields = record.get("fields", {})
        linkedin_data.append({
            "Name": fields.get("Name") or fields.get("Full Name") or "",
            "LinkedIn": fields.get("LinkedIn") or fields.get("Linkedin") or "",
            "Company": fields.get("Realtime company name") or fields.get("Company") or "",
            "Role": fields.get("Realtime role") or "",
            "Location": fields.get("Realtime location") or "",
            "Last 3 Companies": fields.get("Realtime last 3 companies") or "",
            "Last 3 Industries": fields.get("Realtime last 3 industries") or "",
        })
    
    if linkedin_data:
        df = pd.DataFrame(linkedin_data)
        
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            show_only_linkedin = st.checkbox("Show only records with LinkedIn URLs")
        with col2:
            show_only_company = st.checkbox("Show only records with company data")
        
        # Apply filters
        if show_only_linkedin:
            df = df[df["LinkedIn"].str.len() > 0]
        if show_only_company:
            df = df[df["Company"].str.len() > 0]
        
        # LinkedIn section pagination
        linkedin_page_size = 50  # Show 50 LinkedIn profiles per page
        linkedin_total_records = len(df)
        linkedin_total_pages = max(1, (linkedin_total_records - 1) // linkedin_page_size + 1)
        
        # Initialize LinkedIn page state
        if f"linkedin_page_{camp['campaign_id']}" not in st.session_state:
            st.session_state[f"linkedin_page_{camp['campaign_id']}"] = 1
        
        linkedin_current_page = st.session_state[f"linkedin_page_{camp['campaign_id']}"]
        linkedin_start_idx = (linkedin_current_page - 1) * linkedin_page_size
        linkedin_end_idx = min(linkedin_start_idx + linkedin_page_size, linkedin_total_records)
        
        # Display pagination info and controls
        st.success(f"Showing {linkedin_total_records} LinkedIn profiles")
        
        if linkedin_total_pages > 1:
            # Pagination controls
            col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
            
            with col1:
                if st.button("⬅️ Previous", disabled=linkedin_current_page <= 1, key="linkedin_prev"):
                    st.session_state[f"linkedin_page_{camp['campaign_id']}"] = max(1, linkedin_current_page - 1)
                    st.rerun()
            
            with col2:
                if st.button("➡️ Next", disabled=linkedin_current_page >= linkedin_total_pages, key="linkedin_next"):
                    st.session_state[f"linkedin_page_{camp['campaign_id']}"] = min(linkedin_total_pages, linkedin_current_page + 1)
                    st.rerun()
            
            with col3:
                st.write(f"**Page {linkedin_current_page} of {linkedin_total_pages}** (showing {linkedin_end_idx - linkedin_start_idx} of {linkedin_total_records} profiles)")
            
            with col4:
                # LinkedIn page jump
                linkedin_jump_page = st.number_input("Go to page:", min_value=1, max_value=linkedin_total_pages, value=linkedin_current_page, key="linkedin_page_jump")
            
            with col5:
                if st.button("Go", key="linkedin_go") and linkedin_jump_page != linkedin_current_page:
                    st.session_state[f"linkedin_page_{camp['campaign_id']}"] = linkedin_jump_page
                    st.rerun()
            
            st.markdown("---")
        
        # Get paginated data
        df_page = df.iloc[linkedin_start_idx:linkedin_end_idx]
        
        # Display as native Streamlit dataframe (instead of AgGrid)
        st.dataframe(
            df_page,
            use_container_width=True,
            height=600,
            column_config={
                "LinkedIn": st.column_config.LinkColumn("LinkedIn URL"),
                "Last 3 Companies": st.column_config.TextColumn("Last 3 Companies", width="medium"),
                "Last 3 Industries": st.column_config.TextColumn("Last 3 Industries", width="medium"),
            }
        )
        
        # Show pagination info at bottom too
        if linkedin_total_pages > 1:
            st.caption(f"Showing records {linkedin_start_idx + 1}-{linkedin_end_idx} of {linkedin_total_records} total LinkedIn profiles")
    else:
        st.info("No LinkedIn data available")


# Footer
st.markdown("---")
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🏠 Back to Home", key="footer_home_btn"):
        st.switch_page("Home.py")
with col2:
    if st.button("📧 Email Search", key="footer_email_btn"):
        st.switch_page("pages/EmailSearch.py")