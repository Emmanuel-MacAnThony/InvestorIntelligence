import os
import sys
from datetime import datetime, timedelta
import streamlit as st
from urllib.parse import urlencode
from pathlib import Path

from dotenv import load_dotenv

# Ensure parent directory is importable when running via Streamlit
_THIS_DIR = os.path.dirname(__file__)
_APP_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from utils_oauth import (
    get_oauth_config,
    exchange_code_for_tokens,
    get_token_scopes,
    is_valid_fernet_key,
    get_token_store,
)

# Load environment from project root .env files
PROJECT_ROOT = Path(_APP_DIR).parent
env_name = os.getenv("ENVIRONMENT", "development")
load_dotenv(PROJECT_ROOT / f".env.{env_name}", override=False)
load_dotenv(PROJECT_ROOT / ".env", override=False)

st.set_page_config(page_title="Mailboxes", layout="wide")

org_name = os.environ.get("ORG_NAME", "Two Lions")
allowed_env = os.environ.get(
    "ALLOWED_MAILBOXES",
    "bradford@twolions.co,newsletter@codewithmosh.com,bradford@ceai.io,bradford@alphacity.io,bradford@2lambda.co,patri@pronomos.vc",
)
allowed_mailboxes = [m.strip() for m in allowed_env.split(",") if m.strip()]

st.title(f"Mailboxes · {org_name}")
st.caption("Connect company mailboxes to enable correspondence view.")


def oauth_authorize_url(state: str) -> str:
    cfg = get_oauth_config()
    base = "https://accounts.google.com/o/oauth2/v2/auth"
    scopes = cfg["scopes_csv"].split(",")
    redirect_uri = os.environ.get("OAUTH_REDIRECT_BASE", "http://localhost:8501")
    params = {
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri,
        "access_type": "offline",
        "prompt": "consent select_account",
        "scope": " ".join(s.strip() for s in scopes if s.strip()),
        "state": state,
        "include_granted_scopes": "false",
    }
    return f"{base}?{urlencode(params)}"


def exchange_code_for_tokens(code: str, redirect_uri: str) -> dict:
    import requests

    cfg = get_oauth_config()
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    resp = requests.post(token_url, data=data, timeout=20)
    resp.raise_for_status()
    return resp.json()


def status_row(addr: str, store):
    col1, col2, col3, col4 = st.columns([4, 3, 3, 2])
    col1.write(addr)
    token = store.load(addr)
    if token:
        obtained = token.get("obtained_at")
        try:
            connected_at = (
                datetime.fromisoformat(obtained) if obtained else datetime.utcnow()
            )
        except Exception:
            connected_at = datetime.utcnow()
        # In testing mode we show approx 6 days remaining
        scopes = get_token_scopes(store, addr)
        has_ro = "https://www.googleapis.com/auth/gmail.readonly" in scopes
        badge = "Connected (full)" if has_ro else "Connected (metadata-only)"
        col2.success(badge)
        col3.write(connected_at.strftime("%Y-%m-%d %H:%M"))
        if col4.button("Disconnect", key=f"dc_{addr}"):
            try:
                store.delete(addr)
            except Exception:
                pass
            st.rerun()
    else:
        col2.warning("Not connected")
        col3.write("-")
        if col4.button("Connect", key=f"co_{addr}"):
            st.session_state["oauth_intent_mailbox"] = addr
            auth_url = oauth_authorize_url(state=addr)
            st.info(f"Click the link below to authorize {addr}")
            st.markdown(f"[🔗 Continue to Google OAuth]({auth_url})")
            st.caption(
                "After authorization, you'll be redirected back here automatically."
            )


hdr = st.columns([4, 3, 3, 2])
hdr[0].markdown("**Mailbox**")
hdr[1].markdown("**Status**")
hdr[2].markdown("**Last authorized**")
hdr[3].markdown("**Action**")

cfg = get_oauth_config()
if not cfg["client_id"] or not cfg["client_secret"] or not cfg["enc_key"]:
    st.error(
        "Missing OAuth env vars. Please set GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, OAUTH_TOKEN_ENC_KEY."
    )
elif not is_valid_fernet_key(cfg["enc_key"]):
    st.error(
        'Invalid OAUTH_TOKEN_ENC_KEY. Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
    )
else:
    store = get_token_store()

    # Handle OAuth callback with code
    code = None
    try:
        qp = st.query_params
        code = qp.get("code")
        # Some Streamlit versions may return lists; normalize
        if isinstance(code, list):
            code = code[0] if code else None
    except Exception:
        code = None

    # Support being forwarded from Home with stored code/state
    if not code:
        code = st.session_state.get("oauth_pending_code")
        if code:
            st.session_state.pop("oauth_pending_code", None)
            st.session_state["oauth_intent_mailbox"] = (
                st.session_state.get("oauth_pending_state")
                or st.session_state.get("oauth_intent_mailbox")
                or ""
            )
            st.session_state.pop("oauth_pending_state", None)

    if code:
        try:
            mailbox = st.session_state.get("oauth_intent_mailbox") or ""
            redirect_uri = os.environ.get(
                "OAUTH_REDIRECT_BASE", "http://localhost:8501"
            )
            tokens = exchange_code_for_tokens(code, redirect_uri)
            payload = {
                "obtained_at": datetime.utcnow().isoformat(),
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens.get("expires_in"),
                "scope": tokens.get("scope"),
                "token_type": tokens.get("token_type"),
            }
            if not mailbox:
                # Fallback to state param as mailbox if session lost
                try:
                    state_val = st.query_params.get("state")
                    if isinstance(state_val, list):
                        state_val = state_val[0] if state_val else None
                    mailbox = state_val or mailbox
                except Exception:
                    pass

            if mailbox:
                store.save(mailbox, payload)
                st.success(f"Connected {mailbox}")
                # Clear query params to avoid re-processing on rerun
                try:
                    if "code" in st.query_params:
                        del st.query_params["code"]
                    if "state" in st.query_params:
                        del st.query_params["state"]
                    if "oauth_start" in st.query_params:
                        del st.query_params["oauth_start"]
                except Exception:
                    pass
                st.rerun()
        except Exception as e:
            st.error(f"OAuth exchange failed: {e}")

    for m in allowed_mailboxes:
        status_row(m, store)

st.caption(
    "Tokens are stored encrypted (disk or Airtable, depending on configuration). In Testing mode, re-auth is needed weekly."
)
