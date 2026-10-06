"""Cloud mirror round-trip against an in-memory fake OneDrive."""
import hashlib
import shutil
from pathlib import Path

import pytest

from fonenova import cloud
from fonenova.cli import main as cli
from fonenova.graph import ConflictError, Item
from fonenova.hashing import set_resolver

SD = cloud.SEPTDEC_TRACKER
V18 = cloud.V18_TRACKER
RECEIPTS = cloud.RECEIPT_ROOTS[0]


class FakeDrive:
    base = "Desktop/VAT RETURNS"

    def __init__(self, files: dict[str, bytes]):
        self.files = {}          # rel -> [id, etag, bytes]
        self.n = 0
        for rel, data in files.items():
            self._put(rel, data)
        self.downloads = []
        self.calls = []

    def _put(self, rel, data):
        self.n += 1
        self.files[rel] = [f"id{self.n}", f"etag{self.n}", data]

    def _by_id(self, item_id):
        return next(r for r, v in self.files.items() if v[0] == item_id)

    def item(self, rel):
        v = self.files.get(rel)
        return {"id": v[0], "eTag": v[1]} if v else None

    def list_tree(self, skip_dirs=frozenset(), start=""):
        out, folders = [], set()
        for rel, (i, e, d) in self.files.items():
            if start and not rel.startswith(start.rstrip("/") + "/"):
                continue
            if any(f"/{s}/" in f"/{rel}" for s in skip_dirs):
                continue
            parts = rel.split("/")
            for k in range(1, len(parts)):
                folders.add("/".join(parts[:k]))
            out.append(Item(rel, i, e, len(d), hashlib.sha1(d).hexdigest(), False))
        out += [Item(f, "f" + f, "", 0, None, True) for f in sorted(folders)]
        return out

    def download(self, item_id):
        self.downloads.append(self._by_id(item_id))
        return self.files[self._by_id(item_id)][2]

    def upload_new(self, rel, data):
        assert rel not in self.files, f"would overwrite {rel}"
        self.calls.append(("upload", rel))
        self._put(rel, data)

    def replace(self, item_id, data, etag):
        rel = self._by_id(item_id)
        if self.files[rel][1] != etag:
            raise ConflictError(rel)
        self.calls.append(("replace", rel))
        self.n += 1
        self.files[rel] = [item_id, f"etag{self.n}", data]

    def move(self, item_id, new_rel):
        rel = self._by_id(item_id)
        assert new_rel not in self.files
        self.calls.append(("move", rel, new_rel))
        self.files[new_rel] = self.files.pop(rel)


@pytest.fixture
def drive(septdec_copy, v18_ref):
    return FakeDrive({
        SD: septdec_copy.read_bytes(),
        V18: v18_ref.read_bytes(),
        f"{RECEIPTS}/Tesco/Tesco-04.10.26.pdf": b"%PDF tesco receipt 4 oct",
        f"{RECEIPTS}/Lidl/Lidl-02.10.26.pdf": b"%PDF lidl",
        "Receipts Inbox/Scan 2026-10-06.pdf": b"%PDF new receipt from phone",
        "Receipts Inbox/Scan dup.pdf": b"%PDF lidl",                    # same bytes as a filed receipt
        "_backups/old/x.xlsx": b"skip me",
    })


@pytest.fixture(autouse=True)
def _reset_resolver():
    yield
    set_resolver(None)


def test_pull_downloads_only_what_is_needed(drive, tmp_path):
    dest = tmp_path / "m"
    cloud.pull(drive, dest)
    assert set(drive.downloads) == {SD, V18, "Receipts Inbox/Scan 2026-10-06.pdf", "Receipts Inbox/Scan dup.pdf"}
    ph = dest / RECEIPTS / "Tesco" / "Tesco-04.10.26.pdf"
    assert ph.stat().st_size == len(b"%PDF tesco receipt 4 oct") and ph.read_bytes().strip(b"\0") == b""
    assert not (dest / "_backups").exists() or not any((dest / "_backups").rglob("*.xlsx"))


def test_placeholder_hash_comes_from_onedrive(drive, tmp_path):
    from fonenova.hashing import content_hash
    dest = tmp_path / "m"
    cloud.pull(drive, dest)
    cloud.install_resolver(dest)
    ph = dest / RECEIPTS / "Lidl" / "Lidl-02.10.26.pdf"
    assert content_hash(ph) == hashlib.sha1(b"%PDF lidl").hexdigest()
    # The inbox duplicate is recognised without downloading the filed receipt.
    assert content_hash(dest / "Receipts Inbox" / "Scan dup.pdf") == content_hash(ph)


def test_full_run_add_file_push(drive, tmp_path):
    dest = tmp_path / "m"
    cloud.pull(drive, dest)
    m = ["--mirror", str(dest)]
    assert cli(m + ["add", "--date", "06.10.26", "--vendor", "Tesco Express", "--desc", "Groceries",
                    "--amount", "7.25", "--ref", "r1", "--vat", "No",
                    "--remarks", "Matched to Tesco-06.10.26.pdf. Test."]) == 0
    assert cli(m + ["file", "--src", str(dest / "Receipts Inbox" / "Scan 2026-10-06.pdf"),
                    "--vendor", "Tesco", "--date", "06.10.26"]) == 0
    plan = cloud.plan_push(dest)
    assert [e["rel"] for e, _ in plan.tracker_updates] == [SD]
    assert [(e["rel"], n) for e, n in plan.moves] == [
        ("Receipts Inbox/Scan 2026-10-06.pdf", f"{RECEIPTS}/Tesco/Tesco-06.10.26.pdf")]
    assert all(r.startswith("_backups/") for r, _ in plan.uploads)     # the pre-write backup
    assert plan.errors == []
    rep = cloud.push(drive, dest)
    assert not rep["aborted"] and rep["errors"] == []
    assert drive.calls[0] == ("replace", SD)                            # tracker first
    assert f"{RECEIPTS}/Tesco/Tesco-06.10.26.pdf" in drive.files
    assert drive.files[f"{RECEIPTS}/Tesco/Tesco-06.10.26.pdf"][2] == b"%PDF new receipt from phone"
    # The uploaded tracker contains the new row.
    import io, openpyxl
    ws = openpyxl.load_workbook(io.BytesIO(drive.files[SD][2]))["Sheet2"]
    assert any(ws.cell(r, 5).value == "Tesco Express" and ws.cell(r, 9).value == 7.25 for r in range(60, 75))


def test_conflict_aborts_everything(drive, tmp_path):
    dest = tmp_path / "m"
    cloud.pull(drive, dest)
    m = ["--mirror", str(dest)]
    cli(m + ["add", "--date", "06.10.26", "--vendor", "V", "--desc", "d", "--amount", "1", "--ref", "r",
             "--vat", "No", "--remarks", "x"])
    cli(m + ["file", "--src", str(dest / "Receipts Inbox" / "Scan 2026-10-06.pdf"), "--vendor", "Tesco",
             "--date", "06.10.26"])
    drive.files[SD][1] = "edited-by-someone"                            # Wahidullah saved meanwhile
    rep = cloud.push(drive, dest)
    assert rep["aborted"] and drive.calls == []
    assert "Receipts Inbox/Scan 2026-10-06.pdf" in drive.files          # receipt not moved either


def test_never_deletes_and_refuses_zero_copies(drive, tmp_path):
    dest = tmp_path / "m"
    cloud.pull(drive, dest)
    (dest / "Receipts Inbox" / "Scan dup.pdf").unlink()
    shutil.copy(dest / RECEIPTS / "Lidl" / "Lidl-02.10.26.pdf", dest / RECEIPTS / "Lidl" / "copy.pdf")
    (dest / V18).write_bytes(b"tampered")
    plan = cloud.plan_push(dest)
    errs = " | ".join(plan.errors)
    assert "Scan dup.pdf disappeared" in errs
    assert "copy.pdf: content is all zero bytes" in errs
    assert "VATReturn_Automated_v18_delivered_1.xlsx was modified locally but is not writable" in errs
    rep = cloud.push(drive, dest)
    assert "Receipts Inbox/Scan dup.pdf" in drive.files and f"{RECEIPTS}/Lidl/copy.pdf" not in drive.files
    assert all(c[0] != "replace" or c[1] != V18 for c in drive.calls)


def test_lock_is_exclusive_and_records_rerun(drive):
    assert cloud.acquire_lock(drive, now=1000.0) is True
    assert cloud.acquire_lock(drive, now=1100.0) is False          # second run backs off
    import json
    assert json.loads(drive.files[cloud.LOCK][2])["rerun"] is True
    assert cloud.release_lock(drive) is True                        # finish learns a rerun is due
    assert json.loads(drive.files[cloud.LOCK][2])["state"] == "idle"
    assert cloud.acquire_lock(drive, now=1200.0) is True            # free again
    assert cloud.acquire_lock(drive, now=1200.0 + cloud.LOCK_STALE_SECONDS + 1) is True   # stale lock


def test_lock_file_is_not_mirrored(drive, tmp_path):
    cloud.acquire_lock(drive, now=1.0)
    cloud.pull(drive, tmp_path / "m")
    assert not (tmp_path / "m" / cloud.LOCK).exists()


def test_late_inbox_file_detected(drive, tmp_path):
    dest = tmp_path / "m"
    cloud.pull(drive, dest)
    assert cloud.new_inbox_files(drive, dest) == []
    drive._put("Receipts Inbox/whatsapp/20261006-1201_Hamza_abc_image.jpg", b"jpeg")
    drive._put("Receipts Inbox/processed/2026-10-06/old.jpg", b"old")
    assert cloud.new_inbox_files(drive, dest) == ["Receipts Inbox/whatsapp/20261006-1201_Hamza_abc_image.jpg"]
