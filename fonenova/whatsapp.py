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


class OutsideWindow(Exception):
    """WhatsApp error 131047: the recipient hasn't messaged in 24h, so only templates are allowed."""


def send_text(to_number: str, body: str) -> None:
    r = requests.post(f"{GRAPH}/{os.environ['WA_PHONE_NUMBER_ID']}/messages", headers=_auth(), timeout=30,
                      json={"messaging_product": "whatsapp", "to": to_number, "type": "text",
                            "text": {"body": body[:4000]}})
    if not r.ok and '"code":131047' in r.text.replace(" ", ""):
        raise OutsideWindow(to_number)
    r.raise_for_status()


def send_template(to_number: str, name: str, text: str, lang: str = "en_GB") -> None:
    """One-parameter utility template, e.g. body 'Fone Nova expenses: {{1}}'. Allowed any time."""
    param = re.sub(r"\s+", " ", text).strip()[:900]          # template params: no newlines/tabs
    r = requests.post(f"{GRAPH}/{os.environ['WA_PHONE_NUMBER_ID']}/messages", headers=_auth(), timeout=30,
                      json={"messaging_product": "whatsapp", "to": to_number, "type": "template",
                            "template": {"name": name, "language": {"code": lang},
                                         "components": [{"type": "body",
                                                         "parameters": [{"type": "text", "text": param}]}]}})
    r.raise_for_status()


def send_any(to_number: str, text: str, send=None, template=None) -> str:
    """Free text if the 24h window is open, else the copy template if configured. Returns how."""
    send = send or send_text
    template = template or send_template
    try:
        send(to_number, text)
        return "text"
    except OutsideWindow:
        name = os.environ.get("WA_COPY_TEMPLATE", "").strip()
        if not name:
            return "skipped (outside 24h window, no WA_COPY_TEMPLATE set)"
        template(to_number, name, text, os.environ.get("WA_COPY_TEMPLATE_LANG", "en_GB"))
        return "template"


def _no_copy() -> dict[str, list[str]]:
    try:
        from .layout import load_config
        return load_config().get("whatsapp", {}).get("no_copy", {})
    except Exception:                                       # never let config break delivery
        return {}


def deliver_replies(replies: list[dict], send=None, template=None,
                    no_copy: dict | None = None) -> tuple[list[str], list[str]]:
    """Send each run result to the person who sent the file, and a copy to everyone else allowed,
    except the people config.toml [whatsapp.no_copy] mutes for that sender.

    Returns (delivered, problems). Problems with copies are informational, never errors for Hamza.
    """
    who = allowed()                                         # number -> label
    mute = {s.lower(): {x.lower() for x in v} for s, v in (_no_copy() if no_copy is None else no_copy).items()}
    delivered, problems = [], []
    for rep in replies:
        sender, text = rep.get("to", ""), rep.get("text", "")
        sender_num = number_for(sender)
        for num, label in who.items():
            if num != sender_num and label.lower() in mute.get(sender.lower(), set()):
                continue
            body = text if num == sender_num else f"[{sender or 'Someone'}] {text}"
            try:
                how = send_any(num, body, send, template)
                (delivered if how in ("text", "template") else problems).append(f"{label}: {how}")
            except Exception as e:
                problems.append(f"{label}: failed ({e})")
    return delivered, problems


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
            if created:
                if kind == "text":
                    send(num, "Noted. I'll use this as the description for the receipt you send with it. "
                              "Send a photo or PDF of the receipt (or a bank statement / FX confirmation) to log it.")
                else:
                    send(num, f"Got it ({name.split('_', 3)[-1]}). It will be logged, filed and added to the "
                              "VAT tracker; I'll message you when it's in.")
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

ROUTINE_HEADERS = {"anthropic-version": "2023-06-01",
                   "anthropic-beta": "experimental-cc-routine-2026-04-01"}


def fire_trigger(reason: str) -> tuple[bool, str]:
    """Start the cloud routine via its API trigger. Returns (started, detail) for diagnostics."""
    url, tok = os.environ.get("ROUTINE_TRIGGER_URL", "").strip(), os.environ.get("ROUTINE_TRIGGER_TOKEN", "").strip()
    if not url.startswith("https://") or not tok or "PASTE" in url or "PASTE" in tok:
        return False, "not configured (ROUTINE_TRIGGER_URL/TOKEN missing or placeholder)"
    try:
        r = requests.post(url, timeout=30, json={"text": f"Instant run: {reason}"},
                          headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
                                   **ROUTINE_HEADERS})
        return r.ok, f"HTTP {r.status_code} {r.text[:200]}"
    except requests.RequestException as e:
        return False, f"request failed: {e}"


def maybe_trigger(store, reason: str, now: float | None = None, fire=fire_trigger) -> bool:
    """Debounced: fire at most once per DEBOUNCE_SECONDS. A file that arrives inside the window is
    picked up by the run already requested, or by its finish step's re-check of the inbox."""
    now = now if now is not None else datetime.now(timezone.utc).timestamp()
    state = store.get(STATE_DOC) or {}
    if now - float(state.get("last_trigger", 0)) < DEBOUNCE_SECONDS:
        return False
    state["last_trigger"] = now
    store.put(STATE_DOC, state)
    ok, detail = fire(reason)
    state["last_result"] = {"ok": ok, "detail": detail, "at": now}
    if not ok:
        state["last_trigger"] = 0            # failed: let the next upload try again straight away
    store.put(STATE_DOC, state)
    return ok
