"""WhatsApp Cloud API: receive receipts from Hamza and Wahidullah, reply, trigger an instant run.

Env (Vercel webhook and the cloud routine):
  WA_TOKEN            permanent System User token (whatsapp_business_messaging)
  WA_APP_SECRET       Meta app secret, for X-Hub-Signature-256
  WA_VERIFY_TOKEN     any string, also typed into Meta's webhook settings
  WA_PHONE_NUMBER_ID  the sending number's ID (test number now, own number later)
  WA_ALLOWED          "Hamza:447700900000,Wahidullah:447700900001" (international, no +)
  ROUTINE_TRIGGER_URL / ROUTINE_TRIGGER_TOKEN   claude.ai routine API trigger (instant runs)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import os
import re
from datetime import datetime, timezone

import requests

GRAPH = "https://graph.facebook.com/v21.0"
INBOX = "Receipts Inbox/whatsapp"
DEBOUNCE_SECONDS = 180
STATE_DOC = "fonenova-trigger.json"   # separate from the token doc: no read-modify-write race


def allowed() -> dict[str, str]:
    """number -> label"""
    out = {}
    for part in os.environ.get("WA_ALLOWED", "").split(","):
        if ":" in part:
            label, num = part.split(":", 1)
            out[re.sub(r"\D", "", num)] = re.sub(r"[^A-Za-z0-9]", "", label) or "Unknown"
    return out


def number_for(label: str) -> str | None:
    return next((n for n, l in allowed().items() if l.lower() == label.lower()), None)


def valid_signature(body: bytes, header: str | None, secret: str | None = None) -> bool:
    secret = secret if secret is not None else os.environ.get("WA_APP_SECRET", "")
    if not secret or not header or not header.startswith("sha256="):
        return False
    want = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(want, header.split("=", 1)[1])


def _auth():
    return {"Authorization": f"Bearer {os.environ['WA_TOKEN']}"}


def download_media(media_id: str) -> tuple[bytes, str]:
    meta = requests.get(f"{GRAPH}/{media_id}", headers=_auth(), timeout=30)
    meta.raise_for_status()
    m = meta.json()
    data = requests.get(m["url"], headers=_auth(), timeout=60)
    data.raise_for_status()
    return data.content, m.get("mime_type", "application/octet-stream")


def send_text(to_number: str, body: str) -> None:
    r = requests.post(f"{GRAPH}/{os.environ['WA_PHONE_NUMBER_ID']}/messages", headers=_auth(), timeout=30,
                      json={"messaging_product": "whatsapp", "to": to_number, "type": "text",
                            "text": {"body": body[:4000]}})
    r.raise_for_status()


def _safe(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\r\n]+', "_", name).strip(" .")
    return name[:80] or "file"


def file_name(msg: dict, label: str, mime: str | None) -> str:
    ts = datetime.fromtimestamp(int(msg.get("timestamp", 0)) or datetime.now().timestamp(),
                                tz=timezone.utc).strftime("%Y%m%d-%H%M")
    mid = re.sub(r"[^A-Za-z0-9]", "", msg.get("id", ""))[-8:] or "nomsgid"
    kind = msg.get("type")
    if kind == "document" and msg["document"].get("filename"):
        base = _safe(msg["document"]["filename"])
    elif kind == "text":
        base = "note.txt"
    else:
        ext = mimetypes.guess_extension((mime or "").split(";")[0]) or ".jpg"
        base = f"{kind}{'.jpg' if ext == '.jpe' else ext}"
    return f"{ts}_{label}_{mid}_{base}"


def extract_messages(payload: dict) -> list[dict]:
    out = []
    for entry in payload.get("entry", []):
        for ch in entry.get("changes", []):
            for m in (ch.get("value") or {}).get("messages", []) or []:
                out.append(m)
    return out


def handle(payload: dict, od, send=send_text, fetch=download_media) -> list[dict]:
    """Save every allowed message into the OneDrive inbox and acknowledge it. Returns a log."""
    who = allowed()
    log = []
    for m in extract_messages(payload):
        num = re.sub(r"\D", "", m.get("from", ""))
        label = who.get(num)
        if not label:
            log.append({"from": num, "status": "ignored (not on the allowlist)"})
            continue
        kind = m.get("type")
        try:
            if kind in ("image", "document"):
                data, mime = fetch(m[kind]["id"])
                name = file_name(m, label, mime)
                caption = m[kind].get("caption")
            elif kind == "text":
                data, name, caption = m["text"]["body"].encode("utf-8"), file_name(m, label, None), None
            else:
                send(num, "Please send a photo, PDF or bank statement (CSV/PDF).")
                log.append({"from": label, "status": f"unsupported type {kind}"})
                continue
            created = _upload_once(od, f"{INBOX}/{name}", data)
            if caption:
                _upload_once(od, f"{INBOX}/{name.rsplit('.', 1)[0]}_note.txt", caption.encode("utf-8"))
            if created and kind != "text":
                send(num, f"Got it ({name.split('_', 3)[-1]}). Logging it now; I'll message you when it's in.")
            log.append({"from": label, "file": name, "status": "saved" if created else "duplicate (retry)"})
        except Exception as e:  # keep going for the other messages
            log.append({"from": label, "status": f"error: {e}"})
            try:
                send(num, "Sorry, I couldn't save that. Please send it again.")
            except Exception:
                pass
    return log


def _upload_once(od, rel: str, data: bytes) -> bool:
    from .graph import GraphError
    try:
        od.upload_new(rel, data)
        return True
    except GraphError as e:
        if "409" in str(e) or "nameAlreadyExists" in str(e):
            return False                     # Meta re-delivered the same message
        raise


# -- instant runs ----------------------------------------------------------------------------

def fire_trigger(reason: str) -> bool:
    url, tok = os.environ.get("ROUTINE_TRIGGER_URL"), os.environ.get("ROUTINE_TRIGGER_TOKEN")
    if not url or not tok:
        return False
    r = requests.post(url, timeout=30, headers={"Authorization": f"Bearer {tok}",
                                                "Content-Type": "application/json"},
                      json={"text": f"Instant run: {reason}"})
    return r.ok


def maybe_trigger(store, reason: str, now: float | None = None, fire=fire_trigger) -> bool:
    """Debounced: fire at most once per DEBOUNCE_SECONDS. A file that arrives inside the window is
    picked up by the run already requested, or by its finish step's re-check of the inbox."""
    now = now if now is not None else datetime.now(timezone.utc).timestamp()
    state = store.get(STATE_DOC) or {}
    if now - float(state.get("last_trigger", 0)) < DEBOUNCE_SECONDS:
        return False
    state["last_trigger"] = now
    store.put(STATE_DOC, state)
    return fire(reason)
