from dataclasses import replace
from datetime import date

from fonenova.intake import scan
from fonenova.pack import build_pack


def _mini(tmp_path, lays):
    """Two tiny receipt trees with one filed receipt each."""
    out = {}
    for key, lay in lays.items():
        rec = tmp_path / key / "receipts"
        (rec / "Tesco").mkdir(parents=True)
        (rec / "Tesco" / f"Tesco-01.09.26-{key}.pdf").write_bytes(f"filed-{key}".encode())
        out[key] = replace(lay, receipts=rec)
    return out


def test_scan_flags_duplicates_and_new(tmp_path, lays):
    mini = _mini(tmp_path, lays)
    (mini["septdec"].receipts / "Scan from 2026-10-06.pdf").write_bytes(b"filed-v18")  # copy of a V18 file
    inbox = tmp_path / "Receipts Inbox" / "gmail"
    inbox.mkdir(parents=True)
    (inbox / "20261006_abcd_email.txt").write_text("new receipt")
    (inbox / "manifest.jsonl").write_text("{}")
    res = {c.path.name: c for c in scan(mini, tmp_path)}
    assert res["Scan from 2026-10-06.pdf"].duplicate_of.startswith("v18:Tesco/")
    assert res["20261006_abcd_email.txt"].duplicate_of is None
    assert "manifest.jsonl" not in res


def test_pack_counts_cross_tracker_duplicate_once(tmp_path, lays, septdec_copy, v18_ref):
    l2 = {"septdec": replace(lays["septdec"], path=septdec_copy), "v18": replace(lays["v18"], path=v18_ref)}
    xlsx, md = build_pack(l2, tmp_path / "out")
    text = md.read_text(encoding="utf-8")
    assert "Excluded septdec row 5" in text
    # V18 (May-Aug + 01.09) + Sept-Dec Sept/Oct minus the duplicate.
    assert "**43,316.64**" in text and "**2,334.65**" in text
    assert xlsx.exists()


def test_inbox_duplicate_is_archived_and_sender_told(tmp_path, lays):
    from datetime import date
    from fonenova.daily import collect
    from fonenova.layout import load_config
    import shutil
    root = tmp_path
    cfg = load_config(); cfg["root"] = str(root)
    from fonenova.layout import layouts as L
    for k, lay in L(cfg).items():
        lay.receipts.mkdir(parents=True, exist_ok=True)
        lay.path.parent.mkdir(parents=True, exist_ok=True)
    from conftest import _reference, SEPTDEC_NAME, V18_NAME
    shutil.copy2(_reference(SEPTDEC_NAME), L(cfg)["septdec"].path)
    shutil.copy2(_reference(V18_NAME), L(cfg)["v18"].path)
    (L(cfg)["septdec"].receipts / "Tesco").mkdir()
    (L(cfg)["septdec"].receipts / "Tesco" / "Tesco-06.10.26.pdf").write_bytes(b"same receipt")
    wa = root / "Receipts Inbox" / "whatsapp"; wa.mkdir(parents=True)
    f = wa / "20261006-2222_Wahidullah_Q0QzNDMA_receipt.pdf"; f.write_bytes(b"same receipt")
    s = collect(cfg, today=date(2026, 10, 7))
    assert not f.exists() and (root / "Receipts Inbox/processed/2026-10-07" / f.name).exists()
    assert s["auto_replies"][0]["to"] == "Wahidullah" and "Already logged" in s["auto_replies"][0]["text"]


def test_email_only_when_important(tmp_path):
    from datetime import date
    from fonenova.daily import finalize
    cfg = {"root": str(tmp_path)}
    base = {"candidates": [], "duplicates": [], "row_issues": [], "alerts": [], "gmail": None}
    assert finalize(cfg, dict(base), {"logged": ["06.10.26 Tesco £6.00 (row 71)"]}, today=date(2026, 10, 7)) is None
    note = finalize(cfg, dict(base), {"logged": ["x"], "needs_hamza": ["amount unreadable"]}, today=date(2026, 10, 7))
    assert note and "action needed" in note[0] and "amount unreadable" in note[1]
    assert finalize(cfg, dict(base), None, extra_errors=["boom"], today=date(2026, 10, 7))
    assert finalize(cfg, dict(base), None, today=date(2026, 10, 31))           # deadline reminder
