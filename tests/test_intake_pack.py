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
