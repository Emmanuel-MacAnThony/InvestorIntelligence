import os
import sys
from datetime import datetime, timedelta
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

# Make gmail client importable
_THIS_DIR = os.path.dirname(__file__)
_APP_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from gmail_client import GmailClient
from utils_oauth import (
    get_oauth_config,
    is_valid_fernet_key,
    EncryptedTokenStore,
    get_token_scopes,
)
import base64
from bs4 import BeautifulSoup
import bleach
import streamlit.components.v1 as components

st.set_page_config(page_title="Correspondence", layout="wide")

# Load environment from project root .env files
PROJECT_ROOT = Path(_APP_DIR).parent
env_name = os.getenv("ENVIRONMENT", "development")
load_dotenv(PROJECT_ROOT / f".env.{env_name}", override=False)
load_dotenv(PROJECT_ROOT / ".env", override=False)


record = st.session_state.get("selected_record")
if not record:
    st.warning("No record selected. Go back to Home and choose a record.")
    st.stop()

st.title("Correspondence")
st.caption(f"Contact: {record['name']} · {record['email']}")

allowed_env = os.environ.get(
    "ALLOWED_MAILBOXES",
    "bradford@twolions.co,newsletter@codewithmosh.com,bradford@ceai.io,bradford@alphacity.io,bradford@2lambda.co,patri@pronomos.vc",
)
mailboxes = [m.strip() for m in allowed_env.split(",") if m.strip()]

cfg = get_oauth_config()
if not is_valid_fernet_key(cfg.get("enc_key", "")):
    st.error(
        'Invalid OAUTH_TOKEN_ENC_KEY. It must be a 32-byte url-safe base64 string. Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" and set OAUTH_TOKEN_ENC_KEY to the printed value.'
    )
    st.stop()

client = GmailClient()
lookback_days = int(os.environ.get("THREAD_LOOKBACK_DAYS", "1095"))

tabs = st.tabs(mailboxes)
for tab, mbox in zip(tabs, mailboxes):
    with tab:
        st.subheader(mbox)
        # Show scopes for this mailbox to verify permissions
        try:
            cfg_sc = get_oauth_config()
            store_sc = EncryptedTokenStore(cfg_sc["token_dir"], cfg_sc["enc_key"])
            scopes = get_token_scopes(store_sc, mbox)
            if scopes:
                st.caption("Scopes: " + ", ".join(sorted(scopes)))
        except Exception:
            pass
        # Loading skeleton while fetching threads
        ph = st.empty()
        with ph.container():
            st.markdown("### Loading threads…")
            sk1 = st.empty()
            sk2 = st.empty()
            sk3 = st.empty()
            with sk1.container():
                st.progress(10, text="Preparing mailbox")
            with sk2.container():
                st.progress(35, text="Searching recent threads")
            with sk3.container():
                st.progress(60, text="Fetching thread metadata")
        resp = client.list_threads(mbox, record["email"], lookback_days=lookback_days)
        ph.empty()
        
        if resp.get("error") == "not_connected":
            # Check if this is due to expired/invalid refresh token
            try:
                cfg_debug = get_oauth_config()
                store_debug = EncryptedTokenStore(cfg_debug["token_dir"], cfg_debug["enc_key"])
                token_debug = store_debug.load(mbox)
                if token_debug and token_debug.get('refresh_token'):
                    st.error(f"🔄 **Refresh token expired for {mbox}**")
                    st.info("The saved authentication has expired and needs to be renewed. Go to **Mailboxes** page to re-connect this account.")
                    
                    if st.button(f"🗑️ Clear expired token for {mbox}", key=f"clear_token_{mbox}"):
                        # Delete the expired token so it shows as "not connected" properly
                        store_debug.delete(mbox)
                        st.success(f"Cleared expired token for {mbox}. Please go to Mailboxes to reconnect.")
                        st.rerun()
                else:
                    st.warning("Mailbox not connected. Go to Mailboxes to connect this account.")
            except Exception as e:
                st.warning("Mailbox not connected. Go to Mailboxes to connect this account.")
            continue
        if resp.get("error") == "missing_readonly_scope":
            st.error(
                "This mailbox was authorized without gmail.readonly. Disconnect and reconnect granting full read access."
            )
            continue
        if resp.get("error") == "insufficient_scope":
            st.error(
                "Insufficient permissions for Gmail search. You need 'gmail.readonly' scope (not just 'gmail.metadata'). Please reconnect this mailbox with full read permissions."
            )
            continue
        if resp.get("error"):
            st.error(f"Error: {resp['error']}")
            continue
        threads = resp.get("threads", [])
        if resp.get("extendedWindow"):
            st.caption("Extended search window (up to 3 years) applied.")
        if resp.get("last6"):
            st.caption("Returning up to the last 6 matching threads by messages.")
        if resp.get("fallback"):
            st.warning(
                f"⚠️ Using slow fallback scan mode; scanned {resp.get('scanned', 0)} recent messages. For better performance, ensure you have 'gmail.readonly' scope."
            )
        elif resp.get("search_query"):
            st.success(f"✅ Used efficient Gmail search: {resp.get('search_query')}")
        
        if not threads:
            st.info("No threads found for this contact in the selected timeframe.")
            continue
        # Display basic thread info
        for th in threads[:10]:
            tid = th.get("id")
            with st.expander(f"Thread {tid}"):
                full = client.get_thread(mbox, tid)
                if full.get("error"):
                    st.error(f"Error loading thread: {full['error']}")
                    continue
                msgs = full.get("messages", [])
                has_full_messages = full.get("has_full_messages", False)
                scope_limitation = full.get("scope_limitation")

                if scope_limitation:
                    st.warning(
                        "⚠️ Message bodies not available - 'gmail.readonly' scope required"
                    )
                elif has_full_messages:
                    st.success("✅ Full message content retrieved")

                st.write(f"**Messages: {len(msgs)}**")

                # Helper functions for message processing
                def _b64url_decode(s: str) -> str:
                    try:
                        if not s:
                            return ""
                        pad = "=" * (-len(s) % 4)
                        return base64.urlsafe_b64decode(s + pad).decode(
                            "utf-8", errors="ignore"
                        )
                    except Exception:
                        return ""

                def _extract_bodies(part: dict):
                    html, text = "", ""
                    if not part:
                        return html, text
                    mime = part.get("mimeType", "")
                    data = part.get("body", {}).get("data")

                    # Handle multipart/alternative by preferring HTML part
                    if mime.startswith("multipart/alternative"):
                        parts = part.get("parts", []) or []
                        # Prefer the last part (often richest), then choose HTML over text
                        for child in reversed(parts):
                            ch_html, ch_text = _extract_bodies(child)
                            if ch_html:
                                return ch_html, ch_text or text
                            if ch_text and not text:
                                text = ch_text
                        return html, text

                    if data:
                        decoded = _b64url_decode(data)
                        if decoded:
                            if mime == "text/html" and not html:
                                # Clean and normalize HTML with BeautifulSoup
                                soup = BeautifulSoup(decoded, "html.parser")
                                html = str(soup)
                            elif mime == "text/plain" and not text:
                                text = decoded

                    # Check child parts
                    parts = part.get("parts", []) or []
                    for child in parts:
                        ch_html, ch_text = _extract_bodies(child)
                        if not html and ch_html:
                            html = ch_html
                        if not text and ch_text:
                            text = ch_text
                        if html and text:
                            break
                    return html, text

                # Display each message with clear formatting
                for i, msg in enumerate(msgs[:10], 1):
                    headers = {
                        h["name"].lower(): h["value"]
                        for h in msg.get("payload", {}).get("headers", [])
                    }
                    subj = headers.get("subject", "(no subject)")
                    frm = headers.get("from", "")
                    to = headers.get("to", "")
                    date = headers.get("date", "")

                    # Create a container for each message
                    with st.container():
                        st.markdown("---")  # Separator line

                        # Message header info
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**📧 Message {i}**")
                            st.markdown(f"**Subject:** {subj}")
                        with col2:
                            st.markdown(
                                f"**Date:** {date[:16] if date else 'N/A'}"
                            )  # Truncate long dates

                        # From/To info
                        st.markdown(f"**From:** {frm}")
                        st.markdown(f"**To:** {to}")

                        # Extract and display message body
                        st.markdown("**Message Body:**")
                        payload = msg.get("payload", {})
                        body_html, body_text = _extract_bodies(payload)

                        # Raw HTML email rendering with proper dark mode support
                        def render_email_content(html_content, text_content):
                            if html_content:
                                import re
                                
                                # Basic sanitization - remove dangerous elements
                                safe_html = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
                                safe_html = re.sub(r"<iframe[^>]*>.*?</iframe>", "", safe_html, flags=re.DOTALL | re.IGNORECASE)
                                safe_html = re.sub(r"<object[^>]*>.*?</object>", "", safe_html, flags=re.DOTALL | re.IGNORECASE)
                                safe_html = re.sub(r"<embed[^>]*>", "", safe_html, flags=re.IGNORECASE)
                                safe_html = re.sub(r"<form[^>]*>.*?</form>", "", safe_html, flags=re.DOTALL | re.IGNORECASE)
                                
                                # Strip ALL existing color and background styling
                                safe_html = re.sub(r'style="[^"]*"', '', safe_html, flags=re.IGNORECASE)
                                safe_html = re.sub(r'color="[^"]*"', '', safe_html, flags=re.IGNORECASE)
                                safe_html = re.sub(r'bgcolor="[^"]*"', '', safe_html, flags=re.IGNORECASE)
                                safe_html = re.sub(r'background-color:\s*[^;"\s]+[;">\s]', '', safe_html, flags=re.IGNORECASE)
                                safe_html = re.sub(r'color:\s*[^;"\s]+[;">\s]', '', safe_html, flags=re.IGNORECASE)
                                
                                # Use Streamlit's font with italic styling like thread overview
                                themed_html = f"""
                                <style>
                                * {{
                                    color: #e0e0e0 !important;
                                    background-color: transparent !important;
                                    font-family: "Source Sans Pro", sans-serif !important;
                                    line-height: 1.6 !important;
                                    font-style: italic !important;
                                }}
                                body {{
                                    font-size: 14px !important;
                                }}
                                a, a:visited, a:hover {{
                                    color: #58a6ff !important;
                                }}
                                </style>
                                {safe_html}
                                """
                                
                                components.html(themed_html, height=600, scrolling=True)
                                
                            elif text_content:
                                st.text_area(
                                    "",
                                    value=text_content,
                                    height=400,
                                    label_visibility="collapsed",
                                )
                            else:
                                st.info("📭 No email content available")

                        # Render the email content
                        render_email_content(body_html, body_text)

                        st.markdown("")  # Add some spacing

if st.sidebar.button("Back to Records"):
    st.switch_page("Home.py")
