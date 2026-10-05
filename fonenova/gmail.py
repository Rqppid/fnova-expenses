"""Gmail API: fetch receipt emails with attachments, and send notifications to self.

One-time setup (Hamza): put the Desktop OAuth client as secrets/credentials.json, then run
    .venv\\Scripts\\python.exe -m fonenova.cli gmail-auth
which opens a browser once and saves secrets/token.json. Unattended runs only refresh it.
"""
from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from email.mime.text import MIMEText
from html import unescape
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.send"]
SELF = "fonenovaltd@gmail.com"
QUERY = ('newer_than:2d (receipt OR invoice OR order OR confirmation OR payment OR booking OR '
         '"tax invoice" OR "e-ticket") -in:spam -in:trash')
# Wholesale stock trading is a different category and never logged here.
EXCLUDE_SENDERS = ("mobileone", "mobile one", "mobile-one", "wavephone", "wave phone",
                   "phone-zone", "phonezone", "phone zone")
KEEP_MIME = ("application/pdf", "image/jpeg", "image/png", "image/heic", "image/webp")
MIN_IMAGE_BYTES = 15_000      # skip logos and tracking pixels


class GmailAuthError(Exception):
    pass


def service(secrets_dir: Path, interactive: bool = False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token = secrets_dir / "token.json"
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:  # revoked or expired refresh token
            if not interactive:
                raise GmailAuthError(f"Gmail token refresh failed: {e}") from e
            creds = None
    if not creds or not creds.valid:
        if not interactive:
            raise GmailAuthError("No valid Gmail token. Run: python -m fonenova.cli gmail-auth")
        from google_auth_oauthlib.flow import InstalledAppFlow
        client = secrets_dir / "credentials.json"
        if not client.exists():
            raise GmailAuthError(f"Missing {client}")
        creds = InstalledAppFlow.from_client_secrets_file(str(client), SCOPES).run_local_server(port=0)
    token.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _safe(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\r\n]+', "_", name).strip()[:120] or "attachment"


def _walk(part):
    yield part
    for p in part.get("parts", []) or []:
        yield from _walk(p)


def _body_text(payload) -> str:
    plain, html = [], []
    for p in _walk(payload):
        data = (p.get("body") or {}).get("data")
        if not data:
            continue
        text = base64.urlsafe_b64decode(data).decode("utf-8", "replace")
        if p.get("mimeType") == "text/plain":
            plain.append(text)
        elif p.get("mimeType") == "text/html":
            html.append(text)
    if plain:
        return "\n".join(plain)
    raw = "\n".join(html)
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</tr>|</div>", "\n", raw)
    return re.sub(r"[ \t]+", " ", unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def fetch(svc, dest: Path, seen_path: Path, query: str = QUERY) -> list[dict]:
    """Download new matching messages into dest. Returns one manifest entry per message."""
    dest.mkdir(parents=True, exist_ok=True)
    seen = set(json.loads(seen_path.read_text())) if seen_path.exists() else set()
    out = []
    resp = svc.users().messages().list(userId="me", q=query, maxResults=100).execute()
    for ref in resp.get("messages", []):
        mid = ref["id"]
        if mid in seen:
            continue
        msg = svc.users().messages().get(userId="me", id=mid, format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        sender = headers.get("from", "")
        entry = {"id": mid, "from": sender, "subject": headers.get("subject", ""),
                 "date": headers.get("date", ""), "files": [], "skipped": None}
        seen.add(mid)
        if any(x in sender.lower() for x in EXCLUDE_SENDERS):
            entry["skipped"] = "wholesale sender"
            out.append(entry)
            continue
        day = datetime.fromtimestamp(int(msg["internalDate"]) / 1000).strftime("%Y%m%d")
        prefix = f"{day}_{mid[-8:]}"
        body = dest / f"{prefix}_email.txt"
        body.write_text(f"From: {sender}\nSubject: {entry['subject']}\nDate: {entry['date']}\n\n"
                        + _body_text(msg["payload"]), encoding="utf-8")
        entry["files"].append(str(body))
        for p in _walk(msg["payload"]):
            fn, att = p.get("filename"), (p.get("body") or {}).get("attachmentId")
            if not fn or not att or p.get("mimeType") not in KEEP_MIME:
                continue
            if p["mimeType"].startswith("image/") and int(p["body"].get("size", 0)) < MIN_IMAGE_BYTES:
                continue
            data = svc.users().messages().attachments().get(userId="me", messageId=mid, id=att).execute()
            path = dest / f"{prefix}_{_safe(fn)}"
            path.write_bytes(base64.urlsafe_b64decode(data["data"]))
            entry["files"].append(str(path))
        out.append(entry)
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(sorted(seen)))
    with open(dest / "manifest.jsonl", "a", encoding="utf-8") as fh:
        for e in out:
            fh.write(json.dumps(e) + "\n")
    return out


def send_self(svc, subject: str, body: str) -> None:
    """Notification email, only ever to the company's own address."""
    m = MIMEText(body, "plain", "utf-8")
    m["to"], m["from"], m["subject"] = SELF, SELF, subject
    raw = base64.urlsafe_b64encode(m.as_bytes()).decode()
    svc.users().messages().send(userId="me", body={"raw": raw}).execute()
