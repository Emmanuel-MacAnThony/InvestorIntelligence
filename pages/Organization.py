import os
from datetime import datetime
import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

# Make token store importable
_THIS_DIR = os.path.dirname(__file__)
_APP_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from utils_oauth import get_oauth_config, is_valid_fernet_key, get_token_store

st.set_page_config(page_title="Organization", layout="wide")

# Load environment from project root .env files
_PROJECT_ROOT = Path(_APP_DIR).parent
_env_name = os.getenv("ENVIRONMENT", "development")
load_dotenv(_PROJECT_ROOT / f".env.{_env_name}", override=False)
load_dotenv(_PROJECT_ROOT / ".env", override=False)

org_name = os.environ.get("ORG_NAME", "Two Lions")
st.title(f"Organization · {org_name}")

st.caption("Connected mailboxes overview.")

allowed_mailboxes = [
    m.strip()
    for m in os.environ.get(
        "ALLOWED_MAILBOXES",
        "bradford@twolions.co,newsletter@codewithmosh.com,bradford@ceai.io,bradford@alphacity.io,bradford@2lambda.co,patri@pronomos.vc",
    ).split(",")
    if m.strip()
]

cfg_client = get_oauth_config()
store = None
if cfg_client.get("enc_key"):
    if is_valid_fernet_key(cfg_client["enc_key"]):
        store = get_token_store()
    else:
        st.error(
            'Invalid OAUTH_TOKEN_ENC_KEY. Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )

connected = []
for m in allowed_mailboxes:
    if store and store.load(m):
        connected.append(m)
expired = []  # Not tracking real expiry; Testing mode tokens rotate weekly
active = connected

colA, colB, colC = st.columns(3)
colA.metric("Total allowed", len(allowed_mailboxes))
colB.metric("Connected", len(connected))
colC.metric("Reauth needed", len(expired))

st.subheader("Details")
for m in allowed_mailboxes:
    if m in connected:
        st.success(f"{m} — Connected")
    else:
        st.write(f"{m} — Not connected")

st.caption("Status is based on presence of encrypted token files in the token store.")
