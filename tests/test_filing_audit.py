import pytest

from fonenova.audit import cited_names, cross_duplicates, audit_tracker
from fonenova.filing import FilingError, file_receipt, receipt_name
from fonenova.receipts import date_from_name
from datetime import date


def test_receipt_name():
    assert receipt_name("Tesco", "06.10.26", "PDF") == "Tesco-06.10.26.pdf"
    assert receipt_name("Asda", "16.09.26", ".pdf", "Bath Sheets") == "Asda-Bath-Sheets-16.09.26.pdf"
    with pytest.raises(FilingError):
        receipt_name("Tesco", "2026-10-06", ".pdf")


def test_file_receipt_moves_and_creates_folder(tmp_path):
    root = tmp_path / "receipts"
    root.mkdir()
    src = tmp_path / "Scan from 2026-10-06.pdf"
    src.write_bytes(b"receipt-a")
    r = file_receipt(src, root, vendor="New Vendor", date="06.10.26")
    assert r.status == "moved"
    assert not src.exists()
    assert (root / "New-Vendor" / "New-Vendor-06.10.26.pdf").read_bytes() == b"receipt-a"


def test_file_receipt_uses_existing_folder_and_detects_duplicate(tmp_path):
    root = tmp_path / "receipts"
    (root / "Tesco").mkdir(parents=True)
    (root / "Tesco" / "Tesco-06.10.26.pdf").write_bytes(b"same")
    src = tmp_path / "scan.pdf"
    src.write_bytes(b"same")
    r = file_receipt(src, root, vendor="Tesco Express", date="06.10.26")
    assert r.status == "duplicate" and src.exists()


def test_file_receipt_never_overwrites(tmp_path):
    root = tmp_path / "receipts"
    (root / "Tesco").mkdir(parents=True)
    (root / "Tesco" / "Tesco-06.10.26.pdf").write_bytes(b"one")
    src = tmp_path / "scan.pdf"
    src.write_bytes(b"two")
    with pytest.raises(FilingError, match="already exists"):
        file_receipt(src, root, vendor="Tesco", date="06.10.26")
    assert src.exists()


def test_date_from_name():
    assert date_from_name("Tesco-01.10.26.png") == date(2026, 10, 1)
    assert date_from_name("Tesco Express-20.09.2026.jpeg") == date(2026, 9, 20)
    assert date_from_name("Scan from 2026-10-04 07_40_31 PM.pdf") == date(2026, 10, 4)
    assert date_from_name("Asda-4337-29.08.26.pdf") == date(2026, 8, 29)
    assert date_from_name("Boarding_Pass_KD9GKD2.pdf") is None


def test_cited_names():
    assert cited_names("Matched to Tesco-02.09.26.pdf (Belfast)") == ["Tesco-02.09.26.pdf"]


def test_audit_on_reference_finds_known_issues(lays, septdec_copy, v18_ref):
    from dataclasses import replace
    sd = audit_tracker(replace(lays["septdec"], path=septdec_copy))
    v18 = audit_tracker(replace(lays["v18"], path=v18_ref))
    assert sd.structure == []
    assert any("septdec row 5" in d and "v18 row 313" in d for d in cross_duplicates(sd, v18))
    assert ("Remarks empty", 5) in {(k, r) for k, r, _ in sd.row_issues}
    hq = next(m for m in sd.matches if m.row.r == 29)
    assert hq.files and all(f.is_transcript for f in hq.files)
    assert {r for k, r, _ in v18.row_issues if k.startswith("amount not numeric")} == {214, 221, 234}
