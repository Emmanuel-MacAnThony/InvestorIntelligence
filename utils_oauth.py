import os
import json
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from cryptography.fernet import Fernet
import requests
from dotenv import load_dotenv


class EncryptedTokenStore:
    def __init__(self, directory: str, enc_key_b64: str) -> None:
        self.dir = directory
        os.makedirs(self.dir, exist_ok=True)
        self.fernet = Fernet(enc_key_b64.encode("utf-8"))

    def _path(self, mailbox: str) -> str:
        safe = mailbox.replace("@", "_at_").replace("/", "_")
        return os.path.join(self.dir, f"{safe}.token")

    def save(self, mailbox: str, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        token = self.fernet.encrypt(data)
        with open(self._path(mailbox), "wb") as f:
            f.write(token)

    def load(self, mailbox: str) -> Optional[Dict[str, Any]]:
        path = self._path(mailbox)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            raw = f.read()
        try:
            decrypted = self.fernet.decrypt(raw)
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            return None

    def delete(self, mailbox: str) -> None:
        path = self._path(mailbox)
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    def list_mailboxes(self) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        try:
            for name in os.listdir(self.dir):
                if not name.endswith(".token"):
                    continue
                # reverse of _path mapping for display only
                key = name[:-6].replace("_at_", "@")
                data = self.load(key)
                if data:
                    results[key] = data
        except Exception:
            pass
        return results


def _ensure_env_loaded() -> None:
    # Always try to load from project root .env files
    try:
        here = Path(__file__).resolve()
        project_root = here.parent.parent  # streamlit_app/ -> project root
        env_name = os.getenv("ENVIRONMENT", "development")
        load_dotenv(project_root / f".env.{env_name}", override=False)
        load_dotenv(project_root / ".env", override=False)
    except Exception:
        pass


def get_oauth_config() -> Dict[str, str]:
    _ensure_env_loaded()
    cid = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
    # Default to readonly only to avoid ambiguous tokens; metadata is unnecessary when readonly is present
    scopes = os.environ.get(
        "GMAIL_SCOPES",
        "https://www.googleapis.com/auth/gmail.readonly",
    )
    token_dir = os.environ.get("TOKEN_STORE_DIR", ".tokens")
    enc_key = (os.environ.get("OAUTH_TOKEN_ENC_KEY", "") or "").strip()
    return {
        "client_id": cid,
        "client_secret": secret,
        "scopes_csv": scopes,
        "token_dir": token_dir,
        "enc_key": enc_key,
    }


def is_valid_fernet_key(enc_key_b64: str) -> bool:
    try:
        if not enc_key_b64:
            return False
        Fernet(enc_key_b64.encode("utf-8"))
        return True
    except Exception:
        return False


def exchange_code_for_tokens(code: str, redirect_uri: str) -> Dict[str, Any]:
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


def get_token_scopes(store: EncryptedTokenStore, mailbox: str) -> set:
    token = store.load(mailbox)
    if not token:
        return set()
    scopes = set()
    try:
        scope_str = token.get("scope") or ""
        scopes |= {s.strip() for s in scope_str.split() if s.strip()}
    except Exception:
        pass
    access_token = token.get("access_token")
    if access_token:
        try:
            r = requests.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": access_token},
                timeout=10,
            )
            if r.status_code == 200:
                live = r.json().get("scope") or ""
                live_set = {s.strip() for s in live.split() if s.strip()}
                scopes |= live_set
                token["scope"] = " ".join(sorted(scopes))
                try:
                    store.save(mailbox, token)
                except Exception:
                    pass
        except Exception:
            pass
    return scopes
