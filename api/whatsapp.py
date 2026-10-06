"""Vercel serverless entry point for the WhatsApp Cloud API webhook.

GET  ?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...  -> echo challenge (Meta setup)
POST signed message notifications -> save media to OneDrive Receipts Inbox/whatsapp, acknowledge,
     and trigger an instant cloud run (debounced). Always answers 200 for valid signatures so
     Meta does not retry; duplicates from retries are harmless (create-only uploads).
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fonenova import whatsapp as wa  # noqa: E402


def _onedrive_and_store():
    from fonenova.cloud import onedrive_session
    from fonenova.gmail import AppData, credentials
    creds = credentials(Path("/tmp"))                    # GOOGLE_TOKEN_JSON from env
    base = os.environ.get("ONEDRIVE_BASE", "Desktop/VAT RETURNS")
    return onedrive_session(creds, base), AppData(creds)


class handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: str = "ok", ctype: str = "text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        if (q.get("hub.mode", [""])[0] == "subscribe"
                and q.get("hub.verify_token", [""])[0] == os.environ.get("WA_VERIFY_TOKEN", "\0")):
            return self._send(200, q.get("hub.challenge", [""])[0])
        return self._send(403, "forbidden")

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
        if not wa.valid_signature(body, self.headers.get("X-Hub-Signature-256")):
            return self._send(401, "bad signature")
        try:
            payload = json.loads(body or b"{}")
            if not wa.extract_messages(payload):
                return self._send(200)                  # delivery/read receipts: nothing to do
            od, store = _onedrive_and_store()
            log = wa.handle(payload, od)
            # Only receipts/documents start a run; text notes ride along with the next one.
            if any(x.get("status") == "saved" and not str(x.get("file", "")).endswith("note.txt") for x in log):
                wa.maybe_trigger(store, "new WhatsApp upload")
            print(json.dumps(log))
        except Exception:
            traceback.print_exc()                       # visible in Vercel logs
        return self._send(200)
