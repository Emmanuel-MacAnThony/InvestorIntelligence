import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from utils_oauth import get_oauth_config, get_token_store


class GmailClient:
    def __init__(self) -> None:
        cfg = get_oauth_config()
        self.client_id = cfg["client_id"]
        self.client_secret = cfg["client_secret"]
        self.store = get_token_store()

        # Set up logging
        self.logger = logging.getLogger("gmail_client")
        if not self.logger.handlers:
            # Create logs directory if it doesn't exist
            log_dir = Path(__file__).parent.parent / "logs"
            log_dir.mkdir(exist_ok=True)

            # Create file handler
            handler = logging.FileHandler(log_dir / "gmail_client.log")
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)

    def _is_token_expired(self, token: Dict[str, Any]) -> bool:
        try:
            obtained_at = token.get("obtained_at")
            expires_in = int(token.get("expires_in") or 3600)
            obtained_dt = (
                datetime.fromisoformat(obtained_at)
                if obtained_at
                else datetime.utcnow()
            )
            return datetime.utcnow() >= (
                obtained_dt + timedelta(seconds=expires_in - 60)
            )
        except Exception:
            return True

    def _refresh_access_token(
        self, mailbox: str, token: Dict[str, Any]
    ) -> Optional[str]:
        refresh_token = token.get("refresh_token")
        if not refresh_token:
            return None
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        resp = requests.post(
            "https://oauth2.googleapis.com/token", data=data, timeout=20
        )
        if resp.status_code != 200:
            return None
        payload = resp.json()
        access_token = payload.get("access_token")
        if not access_token:
            return None
        # Update stored token
        token["access_token"] = access_token
        token["obtained_at"] = datetime.utcnow().isoformat()
        token["expires_in"] = payload.get("expires_in", token.get("expires_in", 3600))
        try:
            self.store.save(mailbox, token)
        except Exception:
            pass
        return access_token

    def get_access_token(self, mailbox: str) -> Optional[str]:
        token = self.store.load(mailbox)
        if not token:
            return None
        if self._is_token_expired(token):
            return self._refresh_access_token(mailbox, token)
        return token.get("access_token")

    def get_simple_message_text(self, mailbox: str, message_id: str) -> Dict[str, Any]:
        """Get simple plain text from a message using the raw format."""
        access_token = self.get_access_token(mailbox)
        if not access_token:
            return {"error": "not_connected", "content": ""}

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"

        try:
            # Get message in raw format (base64url encoded RFC 2822)
            resp = requests.get(
                url, headers=headers, params={"format": "raw"}, timeout=15
            )

            if resp.status_code == 401:
                access_token = self._refresh_access_token(
                    mailbox, self.store.load(mailbox) or {}
                )
                if not access_token:
                    return {"error": "unauthorized", "content": ""}
                headers["Authorization"] = f"Bearer {access_token}"
                resp = requests.get(
                    url, headers=headers, params={"format": "raw"}, timeout=15
                )

            if resp.status_code >= 400:
                return {"error": f"API error {resp.status_code}", "content": ""}

            message_data = resp.json()
            raw_message = message_data.get("raw", "")

            if not raw_message:
                return {"error": "No raw content", "content": ""}

            # Decode base64url
            import base64

            try:
                # Add padding if needed
                missing_padding = len(raw_message) % 4
                if missing_padding:
                    raw_message += "=" * (4 - missing_padding)

                decoded_message = base64.urlsafe_b64decode(raw_message).decode(
                    "utf-8", errors="ignore"
                )

                # Extract just the message body (skip headers)
                if "\n\n" in decoded_message:
                    headers_part, body_part = decoded_message.split("\n\n", 1)

                    # Simple extraction - find the first text part
                    lines = body_part.split("\n")
                    text_lines = []
                    in_text_part = False

                    for line in lines:
                        # Look for Content-Type: text/plain
                        if "Content-Type: text/plain" in line:
                            in_text_part = True
                            continue

                        # Skip MIME boundaries and headers
                        if line.startswith("--") or line.startswith("Content-"):
                            in_text_part = False
                            continue

                        # If we're in text part and line isn't empty/mime stuff
                        if in_text_part and line.strip():
                            text_lines.append(line)

                    if text_lines:
                        return {
                            "content": "\n".join(text_lines).strip(),
                            "format": "simple_text",
                        }
                    else:
                        # Fallback - just return the body part
                        return {"content": body_part.strip(), "format": "raw_body"}
                else:
                    return {"content": decoded_message.strip(), "format": "raw_full"}

            except Exception as e:
                return {"error": f"Decode error: {e}", "content": ""}

        except Exception as e:
            return {"error": str(e), "content": ""}

    def _token_has_scope(self, mailbox: str, required_scope: str) -> bool:
        token = self.store.load(mailbox)
        if not token:
            self.logger.warning(f"No token found for mailbox {mailbox}")
            return False

        # Check cached scopes first
        scope_str = token.get("scope") or ""
        scopes = {s.strip() for s in scope_str.split() if s.strip()}
        self.logger.debug(f"Cached scopes for {mailbox}: {scopes}")

        if required_scope in scopes:
            self.logger.debug(f"Found {required_scope} in cached scopes")
            return True

        # Introspect access token to get live scopes
        access_token = token.get("access_token")
        if not access_token:
            self.logger.warning(f"No access token for {mailbox}")
            return False

        try:
            self.logger.debug(
                f"Introspecting token for {mailbox} to check scope {required_scope}"
            )
            resp = requests.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": access_token},
                timeout=10,
            )
            if resp.status_code == 200:
                info = resp.json()
                live_scopes = {
                    s.strip() for s in (info.get("scope") or "").split() if s.strip()
                }
                self.logger.info(f"Live scopes for {mailbox}: {live_scopes}")

                # Persist scopes for future checks
                token["scope"] = " ".join(sorted(live_scopes))
                try:
                    self.store.save(mailbox, token)
                except Exception as e:
                    self.logger.warning(f"Failed to save updated scopes: {e}")

                has_scope = required_scope in live_scopes
                self.logger.info(f"Scope check for {required_scope}: {has_scope}")
                return has_scope
            else:
                self.logger.error(
                    f"Token introspection failed: {resp.status_code} - {resp.text}"
                )
        except Exception as e:
            self.logger.error(f"Exception during token introspection: {e}")

        return False

    def _get_attachment(
        self,
        mailbox: str,
        message_id: str,
        attachment_id: str,
        headers: Dict[str, str],
    ) -> Optional[str]:
        try:
            url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/attachments/{attachment_id}"
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 401:
                access_token = self._refresh_access_token(
                    mailbox, self.store.load(mailbox) or {}
                )
                if not access_token:
                    return None
                headers["Authorization"] = f"Bearer {access_token}"
                r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                return (r.json() or {}).get("data")
            return None
        except Exception as e:
            try:
                self.logger.warning(f"Attachment fetch failed: {e}")
            except Exception:
                pass
            return None

    def _hydrate_text_parts_inplace(
        self,
        mailbox: str,
        message: Dict[str, Any],
        headers: Dict[str, str],
    ) -> None:
        def _walk(part: Dict[str, Any]) -> None:
            if not isinstance(part, dict):
                return
            mime = part.get("mimeType")
            body = part.get("body", {})
            data = body.get("data")
            attachment_id = body.get("attachmentId")
            if not data and attachment_id and mime in ("text/html", "text/plain"):
                fetched = self._get_attachment(
                    mailbox, message.get("id", ""), attachment_id, headers
                )
                if fetched:
                    body["data"] = fetched
                    part["body"] = body
            for child in part.get("parts", []) or []:
                _walk(child)

        try:
            payload = message.get("payload")
            if isinstance(payload, dict):
                _walk(payload)
        except Exception:
            return

    def has_readonly(self, mailbox: str) -> bool:
        return self._token_has_scope(
            mailbox, "https://www.googleapis.com/auth/gmail.readonly"
        )

    def list_threads(
        self,
        mailbox: str,
        contact_email: str,
        lookback_days: int = 365,
        max_results: int = 50,
    ) -> Dict[str, Any]:
        access_token = self.get_access_token(mailbox)
        if not access_token:
            return {"threads": [], "error": "not_connected"}
        after_date = (datetime.utcnow() - timedelta(days=lookback_days)).strftime(
            "%Y/%m/%d"
        )
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        url = "https://gmail.googleapis.com/gmail/v1/users/me/threads"

        # Use Gmail search query for efficient retrieval when readonly scope is available
        used_fallback = False
        disable_query = os.environ.get("GMAIL_DISABLE_QUERY", "0") == "1"

        # Normalize one or multiple comma/semicolon-separated emails
        def _split_emails(raw: str) -> List[str]:
            if not raw:
                return []
            parts = [p.strip() for p in raw.replace(";", ",").split(",")]
            emails = [p.lower() for p in parts if p and "@" in p]
            # de-duplicate while preserving order
            seen = set()
            uniq: List[str] = []
            for e in emails:
                if e not in seen:
                    seen.add(e)
                    uniq.append(e)
            return uniq

        emails = _split_emails(contact_email)
        if not emails:
            return {"threads": [], "error": "invalid_email"}

        # First try: Use Gmail search with readonly scope for optimal performance
        readonly_scope_check = self._token_has_scope(
            mailbox, "https://www.googleapis.com/auth/gmail.readonly"
        )
        self.logger.info(
            f"Gmail search attempt - disable_query: {disable_query}, has_readonly: {readonly_scope_check}"
        )

        if not disable_query and readonly_scope_check:
            try:
                # Build search query that matches any of the provided emails
                address_clause = " OR ".join(
                    [f"(to:{addr} OR from:{addr})" for addr in emails]
                )
                query_parts = [f"({address_clause})"]

                # Add date filter - Gmail prefers 'after:' and 'before:' over 'newer_than:'
                if lookback_days > 0:
                    after_date = (
                        datetime.utcnow() - timedelta(days=lookback_days)
                    ).strftime("%Y/%m/%d")
                    query_parts.append(f"after:{after_date}")

                query = " ".join(query_parts)
                params = {"q": query, "maxResults": max_results}

                self.logger.info(f"Gmail search query: {query}")

                resp = requests.get(url, headers=headers, params=params, timeout=20)
                if resp.status_code == 401:
                    access_token = self._refresh_access_token(
                        mailbox, self.store.load(mailbox) or {}
                    )
                    if not access_token:
                        return {"threads": [], "error": "unauthorized"}
                    headers["Authorization"] = f"Bearer {access_token}"
                    resp = requests.get(url, headers=headers, params=params, timeout=20)

                if resp.status_code == 200:
                    data = resp.json()
                    threads = data.get("threads", []) or []
                    self.logger.info(f"Gmail search returned {len(threads)} threads")
                    return {
                        "threads": threads,
                        "resultSizeEstimate": data.get("resultSizeEstimate", 0),
                        "search_query": query,
                    }
                elif resp.status_code == 403:
                    self.logger.warning("Gmail search forbidden - likely scope issue")
                    return {"threads": [], "error": "insufficient_scope"}
                else:
                    self.logger.error(
                        f"Gmail search failed: {resp.status_code} - {resp.text}"
                    )

            except Exception as e:
                self.logger.error(f"Gmail search exception: {e}")
                pass

        # Fallback: scan recent messages (paged) and filter client-side by headers, then group by thread
        try:
            from time import monotonic

            messages_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
            matched_thread_ids: List[str] = []
            matched_set = set()
            scanned_msgs = 0
            page_token: Optional[str] = None
            time_budget_seconds = int(os.environ.get("THREAD_SCAN_BUDGET_S", "10"))
            start_t = monotonic()
            per_page = int(os.environ.get("THREAD_LIST_PAGE_SIZE", "100"))
            max_scan_msgs = int(
                os.environ.get("THREAD_MAX_SCAN_MSGS", str(max(600, max_results * 20)))
            )
            while (
                scanned_msgs < max_scan_msgs and len(matched_thread_ids) < max_results
            ):
                if monotonic() - start_t > time_budget_seconds:
                    break
                params2: Dict[str, Any] = {"maxResults": per_page}
                if page_token:
                    params2["pageToken"] = page_token
                resp2 = requests.get(
                    messages_url, headers=headers, params=params2, timeout=10
                )
                if resp2.status_code == 401:
                    access_token = self._refresh_access_token(
                        mailbox, self.store.load(mailbox) or {}
                    )
                    if not access_token:
                        return {"threads": [], "error": "unauthorized"}
                    headers["Authorization"] = f"Bearer {access_token}"
                    resp2 = requests.get(
                        messages_url, headers=headers, params=params2, timeout=10
                    )
                resp2.raise_for_status()
                data2 = resp2.json()
                msgs_meta = data2.get("messages", []) or []
                scanned_msgs += len(msgs_meta)
                for m in msgs_meta:
                    if monotonic() - start_t > time_budget_seconds:
                        break
                    mid = m.get("id")
                    # Fetch minimal headers only
                    msg_url = f"{messages_url}/{mid}"
                    params_get = (
                        ("format", "metadata"),
                        ("metadataHeaders", "From"),
                        ("metadataHeaders", "To"),
                        ("metadataHeaders", "Cc"),
                        ("metadataHeaders", "Bcc"),
                    )
                    r = requests.get(
                        msg_url, headers=headers, params=params_get, timeout=10
                    )
                    if r.status_code >= 400:
                        continue
                    j = r.json()
                    headers_list = j.get("payload", {}).get("headers", [])
                    hdr = {
                        h.get("name", "").lower(): h.get("value", "")
                        for h in headers_list
                    }
                    hay = (
                        hdr.get("from", "")
                        + ","
                        + hdr.get("to", "")
                        + ","
                        + hdr.get("cc", "")
                        + ","
                        + hdr.get("bcc", "")
                    ).lower()
                    if any(addr in hay for addr in emails):
                        tid = j.get("threadId")
                        if tid and tid not in matched_set:
                            matched_set.add(tid)
                            matched_thread_ids.append(tid)
                        if len(matched_thread_ids) >= max_results:
                            break
                page_token = data2.get("nextPageToken")
                if not page_token:
                    break
            return {
                "threads": [{"id": tid} for tid in matched_thread_ids],
                "resultSizeEstimate": len(matched_thread_ids),
                "fallback": True,
                "scanned": scanned_msgs,
                "timeLimited": True,
            }
        except Exception as e:
            return {"threads": [], "error": str(e)}

        # Final attempt: scan more to find up to last 6 messages with this contact
        try:
            from time import monotonic as _mon

            messages_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
            last_tid: List[str] = []
            seen = set()
            scanned = 0
            page_token = None
            budget = int(os.environ.get("THREAD_LAST6_BUDGET_S", "15"))
            start = _mon()
            per_page2 = int(os.environ.get("THREAD_LIST_PAGE_SIZE", "100"))
            max_scan2 = int(os.environ.get("THREAD_LAST6_MAX_SCAN_MSGS", "2000"))
            while scanned < max_scan2 and len(last_tid) < 6:
                if _mon() - start > budget:
                    break
                params2: Dict[str, Any] = {"maxResults": per_page2}
                if page_token:
                    params2["pageToken"] = page_token
                r = requests.get(
                    messages_url, headers=headers, params=params2, timeout=10
                )
                r.raise_for_status()
                dj = r.json()
                msgs = dj.get("messages", []) or []
                scanned += len(msgs)
                for m in msgs:
                    if _mon() - start > budget:
                        break
                    mid = m.get("id")
                    msg_url = f"{messages_url}/{mid}"
                    params_get = (
                        ("format", "metadata"),
                        ("metadataHeaders", "From"),
                        ("metadataHeaders", "To"),
                        ("metadataHeaders", "Cc"),
                        ("metadataHeaders", "Bcc"),
                    )
                    rr = requests.get(
                        msg_url, headers=headers, params=params_get, timeout=10
                    )
                    if rr.status_code >= 400:
                        continue
                    j = rr.json()
                    headers_list = j.get("payload", {}).get("headers", [])
                    hdr = {
                        h.get("name", "").lower(): h.get("value", "")
                        for h in headers_list
                    }
                    hay = (
                        hdr.get("from", "")
                        + ","
                        + hdr.get("to", "")
                        + ","
                        + hdr.get("cc", "")
                        + ","
                        + hdr.get("bcc", "")
                    ).lower()
                    if any(addr in hay for addr in emails):
                        tid = j.get("threadId")
                        if tid and tid not in seen:
                            seen.add(tid)
                            last_tid.append(tid)
                        if len(last_tid) >= 6:
                            break
                page_token = dj.get("nextPageToken")
                if not page_token:
                    break
            if last_tid:
                return {
                    "threads": [{"id": t} for t in last_tid],
                    "resultSizeEstimate": len(last_tid),
                    "fallback": True,
                    "last6": True,
                }
        except Exception:
            pass
        return {"threads": []}

    def get_thread(self, mailbox: str, thread_id: str) -> Dict[str, Any]:
        access_token = self.get_access_token(mailbox)
        if not access_token:
            return {"error": "not_connected"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}"
        # Step 1: always fetch thread metadata first (safe under all scopes)
        meta_params: List[tuple] = [
            ("format", "metadata"),
            ("metadataHeaders", "From"),
            ("metadataHeaders", "To"),
            ("metadataHeaders", "Cc"),
            ("metadataHeaders", "Bcc"),
            ("metadataHeaders", "Subject"),
            ("metadataHeaders", "Date"),
        ]
        try:
            resp = requests.get(url, headers=headers, params=meta_params, timeout=20)
            if resp.status_code == 401:
                access_token = self._refresh_access_token(
                    mailbox, self.store.load(mailbox) or {}
                )
                if not access_token:
                    return {"error": "unauthorized"}
                headers["Authorization"] = f"Bearer {access_token}"
                resp = requests.get(
                    url, headers=headers, params=meta_params, timeout=20
                )
            if resp.status_code >= 400:
                try:
                    err = resp.json().get("error", {})
                    return {
                        "error": f"{err.get('status') or resp.status_code}: {err.get('message') or 'request failed'}"
                    }
                except Exception:
                    resp.raise_for_status()
            thread = resp.json()
        except Exception as e:
            return {"error": str(e)}

        # Step 2: upgrade messages to FULL individually if readonly scope available
        has_readonly = self._token_has_scope(
            mailbox, "https://www.googleapis.com/auth/gmail.readonly"
        )

        try:
            messages = thread.get("messages", []) or []
            if messages and has_readonly:
                enriched: List[Dict[str, Any]] = []
                for msg in messages[:10]:  # Limit to avoid rate limits
                    mid = msg.get("id")
                    if not mid:
                        enriched.append(msg)
                        continue

                    m_url = (
                        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}"
                    )

                    # Try to get full message with body
                    try:
                        r = requests.get(
                            m_url,
                            headers=headers,
                            params={"format": "full"},
                            timeout=15,
                        )
                        if r.status_code == 200:
                            full_msg = r.json()
                            # Ensure text parts that were returned as attachments are hydrated
                            self._hydrate_text_parts_inplace(mailbox, full_msg, headers)
                            enriched.append(full_msg)
                            self.logger.debug(f"Retrieved full message {mid}")
                        else:
                            # Fallback to metadata version
                            enriched.append(msg)
                            self.logger.warning(
                                f"Failed to get full message {mid}: {r.status_code}"
                            )
                    except Exception as e:
                        # Fallback to metadata version
                        enriched.append(msg)
                        self.logger.warning(
                            f"Exception getting full message {mid}: {e}"
                        )

                thread["messages"] = enriched
                thread["has_full_messages"] = True
            else:
                # Mark that we only have metadata
                thread["has_full_messages"] = False
                if not has_readonly:
                    thread["scope_limitation"] = "readonly_required_for_bodies"

        except Exception as e:
            # On any upgrade error, return metadata-only thread
            self.logger.error(f"Error upgrading thread messages: {e}")
            thread["has_full_messages"] = False
        return thread
