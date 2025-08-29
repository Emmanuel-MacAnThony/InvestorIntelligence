"""
Investor Intelligence Engine - Standalone Streamlit App
All functionality built directly into Streamlit without FastAPI backend
"""

import os
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any
from utils.airtable_client import get_airtable_client

# Configure page
st.set_page_config(
    page_title="Investor Intelligence Engine",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Handle OAuth callback - if OAuth returned to root, capture code/state and forward to Mailboxes
try:
    qp = st.query_params
    code = qp.get("code")
    state = qp.get("state")
    if isinstance(code, list):
        code = code[0] if code else None
    if isinstance(state, list):
        state = state[0] if state else None
    if code:
        st.session_state["oauth_pending_code"] = code
        st.session_state["oauth_pending_state"] = state
        try:
            if "code" in st.query_params:
                del st.query_params["code"]
            if "state" in st.query_params:
                del st.query_params["state"]
        except Exception:
            pass
        st.switch_page("pages/Mailboxes.py")
except Exception:
    pass

# Load environment variables
_PROJECT_ROOT = Path(__file__).parent
_env_name = os.getenv("ENVIRONMENT", "development") 
load_dotenv(_PROJECT_ROOT / f".env.{_env_name}", override=False)
load_dotenv(_PROJECT_ROOT / ".env", override=False)

# Initialize clients
airtable = get_airtable_client()

# App header
st.title("🚀 Investor Intelligence Engine")
st.markdown("**Standalone Streamlit App** - Campaign-driven automated investor intelligence")

# Sidebar for navigation
with st.sidebar:
    st.markdown("## 📋 Navigation")
    st.markdown("- 🏠 **Home** (Current)")
    st.markdown("- 📊 **Campaign** (Select campaign first)")
    st.markdown("- 📧 **Email Search**")
    st.markdown("- 📬 **Mailboxes**")
    st.markdown("- 🏢 **Organization**")
    
    st.markdown("---")
    st.markdown("## 💾 Data Storage")
    st.info("**Mode:** Direct Airtable Integration")
    
    # Show environment
    env = os.getenv("ENVIRONMENT", "development")
    st.info(f"**Environment:** {env}")

# Main content
tab1, tab2 = st.tabs(["📊 Campaign Builder", "⚙️ Settings"])

with tab1:
    st.header("📊 Campaign Builder")
    st.markdown("Create campaigns by selecting Airtable base, table, and view directly.")
    
    # Step 1: Select Base
    st.subheader("1️⃣ Select Airtable Base")
    
    with st.spinner("Loading your Airtable bases..."):
        bases = airtable.get_bases()
    
    if not bases:
        st.error("No Airtable bases found. Check your API key configuration.")
        st.stop()
    
    # Base selection
    base_options = {base["name"]: base["id"] for base in bases}
    selected_base_name = st.selectbox(
        "Choose your base:",
        options=list(base_options.keys()),
        help="Select the Airtable base containing your investor data"
    )
    
    if selected_base_name:
        selected_base_id = base_options[selected_base_name]
        st.success(f"✅ Selected base: **{selected_base_name}**")
        
        # Step 2: Select Table  
        st.subheader("2️⃣ Select Table")
        
        with st.spinner("Loading tables..."):
            tables = airtable.get_tables(selected_base_id)
        
        if tables:
            table_options = {table["name"]: table["id"] for table in tables}
            selected_table_name = st.selectbox(
                "Choose your table:",
                options=list(table_options.keys()),
                help="Select the table containing your campaign data"
            )
            
            if selected_table_name:
                selected_table_id = table_options[selected_table_name]
                selected_table = next(t for t in tables if t["id"] == selected_table_id)
                st.success(f"✅ Selected table: **{selected_table_name}**")
                
                # Step 3: Select View
                st.subheader("3️⃣ Select View")
                
                views = selected_table.get("views", [])
                view_options = {view["name"]: view["id"] for view in views}
                view_options["All Records (Grid view)"] = None  # Default view
                
                selected_view_name = st.selectbox(
                    "Choose your view:",
                    options=list(view_options.keys()),
                    help="Select the view to use for this campaign"
                )
                
                selected_view_id = view_options[selected_view_name]
                st.success(f"✅ Selected view: **{selected_view_name}**")
                
                # Step 4: Campaign Configuration
                st.subheader("4️⃣ Campaign Setup")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    campaign_name = st.text_input(
                        "Campaign Name:",
                        value=f"{selected_base_name} - {selected_table_name}",
                        help="Give your campaign a descriptive name"
                    )
                
                with col2:
                    campaign_description = st.text_area(
                        "Description (Optional):",
                        placeholder="Describe your campaign goals...",
                        height=100
                    )
                
                # Step 5: Preview Data
                st.subheader("5️⃣ Data Preview")
                
                if st.button("🔍 Preview Records", use_container_width=True):
                    with st.spinner("Loading preview data..."):
                        # Get first 10 records to preview
                        preview_data = airtable.get_records(
                            selected_base_id, 
                            selected_table_id, 
                            selected_view_name if selected_view_name != "All Records (Grid view)" else None,
                            page_size=10
                        )
                    
                    records = preview_data.get("records", [])
                    if records:
                        st.success(f"✅ Found {len(records)} records (showing first 10)")
                        
                        # Show field analysis
                        all_fields = set()
                        for record in records:
                            all_fields.update(record.get("fields", {}).keys())
                        
                        st.info(f"📊 **Available fields:** {len(all_fields)}")
                        
                        # Show important fields we look for
                        important_fields = ["Name", "Full Name", "Email", "Company", "LinkedIn", "Linkedin"]
                        found_important = [f for f in important_fields if f in all_fields]
                        
                        if found_important:
                            st.success(f"🎯 **Key fields found:** {', '.join(found_important)}")
                        else:
                            st.warning("⚠️ No standard name/email fields found. You may need to map fields manually.")
                        
                        # Show sample records in expandable format
                        with st.expander("📋 Sample Records", expanded=True):
                            for i, record in enumerate(records[:3], 1):
                                fields = record.get("fields", {})
                                st.write(f"**Record {i}:**")
                                
                                # Show key fields if they exist
                                for field in ["Name", "Full Name", "Email", "Company", "LinkedIn"]:
                                    if field in fields:
                                        st.write(f"• **{field}:** {fields[field]}")
                                
                                st.markdown("---")
                    else:
                        st.warning("No records found in this view.")
                
                # Step 6: Create Campaign
                st.subheader("6️⃣ Launch Campaign")
                
                if st.button("🚀 Create Campaign", type="primary", use_container_width=True):
                    if not campaign_name:
                        st.error("Please enter a campaign name")
                    else:
                        with st.spinner("Creating campaign in Airtable..."):
                            # Generate unique campaign ID
                            import uuid
                            import datetime
                            campaign_id = f"camp_{str(uuid.uuid4())[:8]}"
                            
                            # Get campaigns base and table from environment
                            campaigns_base_id = os.getenv("campaigns_base_id", "appEwtde6ov22a2TS")
                            campaigns_table = os.getenv("campaigns_table", "Campaigns")
                            
                            # Create campaign as DRAFT first (like API) - record counting happens in background
                            # Prepare Airtable fields based on original API implementation  
                            airtable_fields = {
                                "Campaign ID": campaign_id,
                                "Campaign Name": campaign_name,
                                "Description": campaign_description or "",
                                "Airtable Base ID": selected_base_id,
                                "Airtable Table ID": selected_table_id,
                                "Airtable View Name": selected_view_name if selected_view_name != "All Records (Grid view)" else "",
                                "Total Target Records": 0,  # Start with 0, will be updated by background job
                                "Status": "Draft",  # Start as Draft, activate after counting
                                "Schedule Frequency": "Weekly",
                                "Total Executions": 0,
                                "Success Rate": 0.0,
                            }
                            
                            # Create record in Airtable
                            result = airtable.create_record(campaigns_base_id, campaigns_table, airtable_fields)
                            
                            if "error" in result:
                                st.error(f"❌ Failed to create campaign: {result['error']}")
                            else:
                                # Campaign created successfully as DRAFT
                                st.success(f"🎉 Campaign created as DRAFT! Campaign ID: {campaign_id}")
                                
                                # Store campaign data in session state for local reference
                                campaign_data = {
                                    "campaign_id": campaign_id,
                                    "airtable_record_id": result["id"],
                                    "name": campaign_name,
                                    "description": campaign_description,
                                    "airtable_base_id": selected_base_id,
                                    "airtable_base_name": selected_base_name,
                                    "airtable_table_id": selected_table_id,
                                    "airtable_table_name": selected_table_name,
                                    "airtable_view_name": selected_view_name,
                                    "airtable_view_id": selected_view_id,
                                    "status": "draft",
                                    "total_records": 0  # Will be updated by background counting
                                }
                                
                                st.session_state["selected_campaign"] = campaign_data
                                
                                # Mark this specific campaign as being counted
                                st.session_state[f"counting_{campaign_id}"] = True
                                
                                # Start background record counting with better logging
                                import threading
                                import time
                                def count_records_background():
                                    try:
                                        print(f"[DEBUG] Starting count for {campaign_id}")
                                        record_count = 0
                                        start_time = time.time()
                                        
                                        # Get actual record count from view - PROPER COUNTING
                                        view_data = airtable.get_records(
                                            selected_base_id, 
                                            selected_table_id, 
                                            selected_view_name if selected_view_name != "All Records (Grid view)" else None,
                                            page_size=100
                                        )
                                        record_count = len(view_data.get("records", []))
                                        print(f"[DEBUG] First page: {record_count} records")
                                        
                                        # For large datasets, get ACTUAL full count by pagination
                                        if record_count == 100:  # More records available
                                            total_count = record_count
                                            offset = view_data.get("offset")
                                            page_num = 1
                                            while offset and page_num < 100:  # Allow more pages for real counting
                                                time.sleep(0.5)  # Rate limiting to avoid API limits
                                                print(f"[DEBUG] Fetching page {page_num + 1}")
                                                next_page = airtable.get_records(
                                                    selected_base_id, 
                                                    selected_table_id,
                                                    selected_view_name if selected_view_name != "All Records (Grid view)" else None,
                                                    page_size=100,
                                                    offset=offset
                                                )
                                                page_records = len(next_page.get("records", []))
                                                total_count += page_records
                                                offset = next_page.get("offset")
                                                page_num += 1
                                                print(f"[DEBUG] Page {page_num}: {page_records} records, total: {total_count}")
                                                if page_records < 100:
                                                    break
                                            record_count = total_count
                                        
                                        elapsed = time.time() - start_time
                                        print(f"[DEBUG] Counting completed: {record_count} records in {elapsed:.2f}s")
                                        
                                        # Update campaign with record count and activate
                                        update_result = airtable.update_record(
                                            campaigns_base_id,
                                            campaigns_table, 
                                            result["id"],
                                            {
                                                "Total Target Records": record_count,
                                                "Status": "Active"
                                            }
                                        )
                                        print(f"[DEBUG] Update result: {update_result}")
                                        
                                        # Mark counting as complete
                                        if f"counting_{campaign_id}" in st.session_state:
                                            del st.session_state[f"counting_{campaign_id}"]
                                        
                                    except Exception as e:
                                        # If counting fails, keep as draft
                                        print(f"[DEBUG] Background counting failed: {e}")
                                        import traceback
                                        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                                        if f"counting_{campaign_id}" in st.session_state:
                                            del st.session_state[f"counting_{campaign_id}"]
                                
                                # Start counting in background thread
                                counting_thread = threading.Thread(target=count_records_background)
                                counting_thread.daemon = True
                                counting_thread.start()
                                
                                st.info("📊 Records are being counted in the background. Campaign will activate automatically once counting completes.")
                                
                                # Auto-refresh message
                                st.info("🔄 Refresh this page to see updated campaign status.")

# Load and show existing campaigns from Airtable
st.markdown("---")
st.subheader("📁 Your Campaigns")

# Load campaigns from Airtable
@st.cache_data(ttl=5)  # Cache for only 5 seconds to see updates faster
def load_campaigns_from_airtable():
    try:
        campaigns_base_id = os.getenv("campaigns_base_id", "appEwtde6ov22a2TS")
        campaigns_table = os.getenv("campaigns_table", "Campaigns")
        
        # Get all campaign records from Airtable
        campaigns_data = airtable.get_records(campaigns_base_id, campaigns_table, page_size=100)
        campaigns = []
        
        for record in campaigns_data.get("records", []):
            fields = record.get("fields", {})
            if fields.get("Campaign ID"):  # Only include records with Campaign ID
                campaign = {
                    "campaign_id": fields.get("Campaign ID"),
                    "airtable_record_id": record["id"],
                    "name": fields.get("Campaign Name", "Unnamed Campaign"),
                    "description": fields.get("Description", ""),
                    "airtable_base_id": fields.get("Airtable Base ID", ""),
                    "airtable_base_name": fields.get("Airtable Base Name", "Unknown"),
                    "airtable_table_id": fields.get("Airtable Table ID", ""),
                    "airtable_table_name": fields.get("Airtable Table Name", "Unknown"),
                    "airtable_view_name": fields.get("Airtable View Name", ""),
                    "status": fields.get("Status", "Unknown").lower(),
                    "total_records": fields.get("Total Target Records", 0),
                    "total_executions": fields.get("Total Executions", 0),
                    "success_rate": fields.get("Success Rate", 0.0)
                }
                campaigns.append(campaign)
        
        return campaigns
    except Exception as e:
        st.error(f"Error loading campaigns: {e}")
        return []

# Load campaigns
existing_campaigns = load_campaigns_from_airtable()

if existing_campaigns:
    # Update session state with Airtable campaigns
    st.session_state["campaigns"] = existing_campaigns
    
    for campaign in existing_campaigns:
        status_color = {"active": "🟢", "draft": "🟡", "paused": "🟠", "completed": "🔵", "failed": "🔴"}.get(campaign['status'], "⚪")
        
        with st.expander(f"{status_color} {campaign['name']} ({campaign['status'].title()})", expanded=False):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**Campaign ID:** {campaign['campaign_id']}")
                if campaign.get('airtable_base_name') and campaign['airtable_base_name'] != 'Unknown':
                    st.write(f"**Base:** {campaign['airtable_base_name']}")
                if campaign.get('airtable_table_name') and campaign['airtable_table_name'] != 'Unknown':
                    st.write(f"**Table:** {campaign['airtable_table_name']}")
                st.write(f"**View:** {campaign['airtable_view_name'] or 'Default'}")
            
            with col2:
                st.metric("Records", campaign.get('total_records', 0))
                if campaign.get('success_rate', 0) > 0:
                    st.metric("Success Rate", f"{campaign['success_rate']:.1%}")
            
            with col3:
                # Check if campaign is actually still counting by looking at status and record count
                is_actually_counting = (
                    campaign['status'] == 'draft' and 
                    campaign.get('total_records', 0) == 0 and
                    st.session_state.get(f"counting_{campaign['campaign_id']}", False)
                )
                
                # Clear counting state if campaign is now active or has records
                if (campaign['status'] != 'draft' or campaign.get('total_records', 0) > 0):
                    if f"counting_{campaign['campaign_id']}" in st.session_state:
                        del st.session_state[f"counting_{campaign['campaign_id']}"]
                    is_actually_counting = False
                
                if is_actually_counting:
                    st.button("⏳ Counting Records...", disabled=True, key=f"disabled_{campaign['campaign_id']}")
                    st.caption("Please wait for record counting to complete")
                else:
                    # Allow opening campaign regardless of draft/active status
                    if st.button("📊 Open", key=f"open_{campaign['campaign_id']}"):
                        st.session_state["selected_campaign"] = campaign
                        st.switch_page("pages/Campaign.py")
else:
    st.info("No campaigns found. Create your first campaign above! 👆")

with tab2:
    st.header("⚙️ Settings")
    
    st.subheader("🔑 Airtable Configuration")
    api_key = os.getenv("AIRTABLE_API_KEY") or os.getenv("AIRTABLE_ACCESS_TOKEN") or os.getenv("AIRTABLE_PAT")
    if api_key:
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        st.success(f"✅ **API Key:** {masked_key}")
    else:
        st.error("❌ **No Airtable API key found**")
        st.info("Set AIRTABLE_API_KEY in your .env file")
    
    st.subheader("📧 Email Configuration")
    allowed_mailboxes = os.getenv("ALLOWED_MAILBOXES", "")
    if allowed_mailboxes:
        mailboxes = [m.strip() for m in allowed_mailboxes.split(",") if m.strip()]
        st.success(f"✅ **Configured Mailboxes:** {len(mailboxes)}")
        for mb in mailboxes:
            st.write(f"• {mb}")
    else:
        st.warning("⚠️ No mailboxes configured")
    
    if st.button("📬 Configure Mailboxes"):
        st.switch_page("pages/Mailboxes.py")
    
    st.subheader("🧹 Session Management")
    if st.button("🗑️ Clear All Data"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("✅ All session data cleared!")
        st.rerun()

# Footer
st.markdown("---")
st.markdown("**🚀 Investor Intelligence Engine** - Standalone Streamlit App (No Backend Required)")