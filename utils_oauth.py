import os
import json
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from cryptography.fernet import Fernet
import requests
from dotenv import load_dotenv
from utils.airtable_client import get_airtable_client


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
    # Try multiple likely roots to be robust to file layout
    try:
        here = Path(__file__).resolve()
        env_name = os.getenv("ENVIRONMENT", "development")
        candidates = [
            here.parent,  # if this file is at project root
            here.parent.parent,  # if this file is in a subfolder
            Path.cwd(),  # current working directory
        ]
        seen = set()
        for base in candidates:
            try:
                if not base or str(base) in seen:
                    continue
                seen.add(str(base))
                load_dotenv(base / f".env.{env_name}", override=False)
                load_dotenv(base / ".env", override=False)
            except Exception:
                continue
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
    token_backend = (os.environ.get("TOKEN_BACKEND", "disk") or "disk").strip().lower()
    token_airtable_base_id = os.environ.get("TOKEN_AIRTABLE_BASE_ID", "")
    token_airtable_table = os.environ.get("TOKEN_AIRTABLE_TABLE", "MailTokens")
    token_airtable_mailbox_field = os.environ.get(
        "TOKEN_AIRTABLE_MAILBOX_FIELD", "Mailbox"
    )
    token_airtable_token_field = os.environ.get("TOKEN_AIRTABLE_TOKEN_FIELD", "Token")
    return {
        "client_id": cid,
        "client_secret": secret,
        "scopes_csv": scopes,
        "token_dir": token_dir,
        "enc_key": enc_key,
        "token_backend": token_backend,
        "token_airtable_base_id": token_airtable_base_id,
        "token_airtable_table": token_airtable_table,
        "token_airtable_mailbox_field": token_airtable_mailbox_field,
        "token_airtable_token_field": token_airtable_token_field,
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


def get_token_scopes(store: Any, mailbox: str) -> set:
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


class AirtableTokenStore:
    """Airtable-backed token store with the same interface as EncryptedTokenStore.

    Stores encrypted token blobs in an Airtable table to survive Streamlit Cloud restarts.
    """

    def __init__(
        self,
        base_id: str,
        table: str,
        mailbox_field: str,
        token_field: str,
        enc_key_b64: str,
    ) -> None:
        self.base_id = base_id
        self.table = table
        self.mailbox_field = mailbox_field
        self.token_field = token_field
        self.fernet = Fernet(enc_key_b64.encode("utf-8"))
        # Reuse existing client config for headers/base_url
        self._client = get_airtable_client()
        self._base_url = f"https://api.airtable.com/v0/{self.base_id}/{self.table}"
        self._headers = self._client.headers

    def _encrypt(self, payload: Dict[str, Any]) -> str:
        data = json.dumps(payload).encode("utf-8")
        token = self.fernet.encrypt(data)
        # Fernet returns URL-safe base64 bytes; store as utf-8 string
        return token.decode("utf-8")

    def _decrypt(self, token_str: str) -> Optional[Dict[str, Any]]:
        try:
            decrypted = self.fernet.decrypt(token_str.encode("utf-8"))
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            return None

    def _find_record_by_mailbox(self, mailbox: str) -> Optional[Dict[str, Any]]:
        try:
            # Use filterByFormula for efficient lookup; json.dumps safely quotes the value
            quoted_value = json.dumps(mailbox)
            formula = f"{{{self.mailbox_field}}} = {quoted_value}"
            params = {"filterByFormula": formula, "pageSize": 1}
            r = requests.get(
                self._base_url, headers=self._headers, params=params, timeout=20
            )
            if r.status_code != 200:
                return None
            recs = (r.json() or {}).get("records", []) or []
            return recs[0] if recs else None
        except Exception:
            return None

    def save(self, mailbox: str, payload: Dict[str, Any]) -> None:
        enc = self._encrypt(payload)
        existing = self._find_record_by_mailbox(mailbox)
        try:
            if existing:
                rec_id = existing.get("id")
                url = f"{self._base_url}/{rec_id}"
                body = {"fields": {self.token_field: enc}}
                requests.patch(url, headers=self._headers, json=body, timeout=20)
            else:
                body = {"fields": {self.mailbox_field: mailbox, self.token_field: enc}}
                requests.post(
                    self._base_url, headers=self._headers, json=body, timeout=20
                )
        except Exception:
            pass

    def load(self, mailbox: str) -> Optional[Dict[str, Any]]:
        rec = self._find_record_by_mailbox(mailbox)
        if not rec:
            return None
        fields = rec.get("fields", {})
        token_str = fields.get(self.token_field)
        if not token_str:
            return None
        return self._decrypt(token_str)

    def delete(self, mailbox: str) -> None:
        rec = self._find_record_by_mailbox(mailbox)
        try:
            if rec and rec.get("id"):
                url = f"{self._base_url}/{rec['id']}"
                requests.delete(url, headers=self._headers, timeout=20)
        except Exception:
            pass

    def list_mailboxes(self) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        try:
            params = {"pageSize": 100}
            offset = None
            while True:
                if offset:
                    params["offset"] = offset
                r = requests.get(
                    self._base_url, headers=self._headers, params=params, timeout=20
                )
                if r.status_code != 200:
                    break
                data = r.json() or {}
                for rec in data.get("records", []) or []:
                    fields = rec.get("fields", {})
                    mailbox = fields.get(self.mailbox_field)
                    token_str = fields.get(self.token_field)
                    if mailbox and token_str:
                        dec = self._decrypt(token_str)
                        if dec:
                            results[mailbox] = dec
                offset = data.get("offset")
                if not offset:
                    break
        except Exception:
            pass
        return results


def get_token_store():
    """Factory to return the appropriate token store based on environment configuration."""
    cfg = get_oauth_config()
    enc_key = cfg.get("enc_key", "")
    backend = cfg.get("token_backend", "disk")
    if backend == "airtable" and enc_key and cfg.get("token_airtable_base_id"):
        return AirtableTokenStore(
            base_id=cfg["token_airtable_base_id"],
            table=cfg["token_airtable_table"],
            mailbox_field=cfg["token_airtable_mailbox_field"],
            token_field=cfg["token_airtable_token_field"],
            enc_key_b64=enc_key,
        )
    # Fallback to disk-based encrypted store
    return EncryptedTokenStore(cfg["token_dir"], enc_key)
