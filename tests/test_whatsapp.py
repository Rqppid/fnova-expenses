import hashlib
import hmac
import json

import pytest

from fonenova import whatsapp as wa
from fonenova.graph import GraphError


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("WA_ALLOWED", "Hamza:447700900000, Wahidullah:+44 7700 900001")
    monkeypatch.setenv("WA_APP_SECRET", "s3cret")


class Drive:
    def __init__(self):
        self.files = {}

    def upload_new(self, rel, data):
        if rel in self.files:
            raise GraphError(f"PUT {rel}: 409 nameAlreadyExists")
        self.files[rel] = data


def payload(*msgs):
    return {"entry": [{"changes": [{"value": {"messages": list(msgs)}}]}]}


IMG = {"from": "447700900000", "id": "wamid.ABCDEFGH12345678", "timestamp": "1791288000", "type": "image",
       "image": {"id": "media1", "mime_type": "image/jpeg", "caption": "Tesco lunch"}}


def test_signature():
    body = b'{"x":1}'
    sig = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert wa.valid_signature(body, sig)
    assert not wa.valid_signature(body + b" ", sig)
    assert not wa.valid_signature(body, None)


def test_allowlist_parsing():
    assert wa.allowed() == {"447700900000": "Hamza", "447700900001": "Wahidullah"}
    assert wa.number_for("wahidullah") == "447700900001"


def test_image_saved_acknowledged_and_retry_is_noop():
    d, sent = Drive(), []
    fetch = lambda mid: (b"\xff\xd8jpegbytes", "image/jpeg")  # noqa: E731
    log = wa.handle(payload(IMG), d, send=lambda n, t: sent.append((n, t)), fetch=fetch)
    name = "Receipts Inbox/whatsapp/20261006-1200_Hamza_12345678_image.jpg"
    assert log == [{"from": "Hamza", "file": name.rsplit("/", 1)[1], "status": "saved"}]
    assert d.files[name] == b"\xff\xd8jpegbytes"
    assert d.files[name.replace("_image.jpg", "_image_note.txt")] == b"Tesco lunch"
    assert sent and sent[0][0] == "447700900000" and "Got it" in sent[0][1]
    # Meta re-delivers the same webhook: nothing duplicated, no second acknowledgement.
    log2 = wa.handle(payload(IMG), d, send=lambda n, t: sent.append((n, t)), fetch=fetch)
    assert log2[0]["status"] == "duplicate (retry)" and len(sent) == 1


def test_stranger_ignored_silently():
    d, sent = Drive(), []
    m = dict(IMG, **{"from": "15550001111"})
    log = wa.handle(payload(m), d, send=lambda n, t: sent.append(t), fetch=lambda i: (b"x", "image/jpeg"))
    assert d.files == {} and sent == [] and "ignored" in log[0]["status"]


def test_document_keeps_its_name_and_text_becomes_note():
    d = Drive()
    doc = {"from": "447700900001", "id": "wamid.XYZ00000099", "timestamp": "1791288000", "type": "document",
           "document": {"id": "m2", "filename": "account-statement_Oct.csv", "mime_type": "text/csv"}}
    txt = {"from": "447700900001", "id": "wamid.TXT00000001", "timestamp": "1791288060", "type": "text",
           "text": {"body": "Ryanair KCZ6XR"}}
    wa.handle(payload(doc, txt), d, send=lambda n, t: None, fetch=lambda i: (b"a,b\n", "text/csv"))
    names = sorted(d.files)
    assert names[0].endswith("_Wahidullah_00000099_account-statement_Oct.csv")
    assert names[1].endswith("_Wahidullah_00000001_note.txt") and d.files[names[1]] == b"Ryanair KCZ6XR"


class Store:
    def __init__(self):
        self.docs = {}

    def get(self, n):
        return self.docs.get(n)

    def put(self, n, v):
        self.docs[n] = json.loads(json.dumps(v))


def test_trigger_is_debounced():
    s, fired = Store(), []
    fire = lambda r: (fired.append(r) or True, "HTTP 200")  # noqa: E731
    assert wa.maybe_trigger(s, "a", now=1000, fire=fire) is True
    assert wa.maybe_trigger(s, "b", now=1100, fire=fire) is False      # inside 3 minutes
    assert wa.maybe_trigger(s, "c", now=1000 + wa.DEBOUNCE_SECONDS + 1, fire=fire) is True
    assert fired == ["a", "c"]


def test_text_message_gets_a_reply():
    d, sent = Drive(), []
    txt = {"from": "447700900000", "id": "wamid.TXT0000000A", "timestamp": "1791288000", "type": "text",
           "text": {"body": "hello"}}
    wa.handle(payload(txt), d, send=lambda n, t: sent.append(t), fetch=lambda i: (b"", ""))
    assert len(sent) == 1 and sent[0].startswith("Noted")


def test_trigger_skips_placeholder(monkeypatch):
    monkeypatch.setenv("ROUTINE_TRIGGER_URL", "PASTE_FROM_ROUTINE_API_TRIGGER")
    monkeypatch.setenv("ROUTINE_TRIGGER_TOKEN", "PASTE_FROM_ROUTINE_API_TRIGGER")
    assert wa.fire_trigger("x")[0] is False


def test_failed_trigger_is_recorded_and_retried():
    s = Store()
    assert wa.maybe_trigger(s, "a", now=1000, fire=lambda r: (False, "HTTP 400 bad")) is False
    st = s.get(wa.STATE_DOC)
    assert st["last_result"]["detail"] == "HTTP 400 bad" and st["last_trigger"] == 0
    assert wa.maybe_trigger(s, "b", now=1010, fire=lambda r: (True, "HTTP 200")) is True   # not debounced


def test_fire_sends_routine_headers(monkeypatch):
    monkeypatch.setenv("ROUTINE_TRIGGER_URL", "https://api.anthropic.com/v1/claude_code/routines/trig_x/fire")
    monkeypatch.setenv("ROUTINE_TRIGGER_TOKEN", "tok")
    seen = {}

    class R:
        ok, status_code, text = True, 200, "{}"

    def post(url, **kw):
        seen.update(kw["headers"], url=url)
        return R()
    monkeypatch.setattr(wa.requests, "post", post)
    assert wa.fire_trigger("x") == (True, "HTTP 200 {}")
    assert seen["anthropic-beta"].startswith("experimental-cc-routine") and seen["Authorization"] == "Bearer tok"
