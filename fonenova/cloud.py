"""Cloud mode: run the routine against OneDrive with the PC switched off.

pull  Lists the OneDrive 'VAT RETURNS' folder and builds a local mirror. Trackers, the
      Receipts Inbox, loose files at the receipts roots and _automation/ are downloaded;
      every other receipt becomes a sparse placeholder of the right size whose fingerprint
      comes from OneDrive's sha1Hash. The normal tooling then runs on the mirror unchanged.
push  Reconciles the mirror back to OneDrive by inode identity:
        same file, new path      -> OneDrive move (no re-upload)
        file not seen at pull    -> upload (folders created as needed)
        changed content          -> replace with If-Match eTag (live tracker and _automation only)
        file gone from mirror    -> error; nothing is ever deleted in OneDrive
      The live tracker goes first; if it changed remotely during the run, nothing is pushed.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .graph import ConflictError, OneDrive

META = ".fn-cloud"
SKIP_DIRS = {"_backups", "_duplicates-review", "VAT-OLD",
             "VAT Return-May-Sept-26/Receipts-Invoice-VAT-Return-May-Sept, 26/a1",
             "Receipts Inbox/processed"}
FULL_PREFIXES = ("Receipts Inbox/", "_automation/")
SEPTDEC_TRACKER = "VAT Return-SEPT-DEC/VAT Return From Sept-Dec, 2026.xlsx"
V18_TRACKER = "VAT Return-May-Sept-26/VATReturn_Automated_v18_delivered_1.xlsx"
RECEIPT_ROOTS = ("VAT Return-SEPT-DEC/Receipts, Invoices-Sept-Dec,2026",
                 "VAT Return-May-Sept-26/Receipts-Invoice-VAT-Return-May-Sept, 26")
WRITABLE = (SEPTDEC_TRACKER,)          # existing files the run may change (plus _automation/)
LOCK = "_automation/run.lock"          # one run at a time; updated in place, never deleted
LOCK_STALE_SECONDS = 45 * 60


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _all_zero(path: Path) -> bool:
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            if chunk.strip(b"\0"):
                return False
    return True


def _wants_full(rel: str) -> bool:
    if rel in (SEPTDEC_TRACKER, V18_TRACKER) or rel.startswith(FULL_PREFIXES):
        return True
    parent = rel.rpartition("/")[0]
    return parent in RECEIPT_ROOTS          # loose files at a receipts root are candidates


# -- pull ----------------------------------------------------------------------------------

def pull(od: OneDrive, dest: Path) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    items = od.list_tree(SKIP_DIRS)
    entries = []
    for it in items:
        p = dest / it.rel
        if it.folder:
            p.mkdir(parents=True, exist_ok=True)
            continue
        if any(it.rel == d or it.rel.startswith(d + "/") for d in SKIP_DIRS) or it.rel == LOCK:
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        full = _wants_full(it.rel)
        if full:
            p.write_bytes(od.download(it.id))
            sha1 = _sha1(p)
        else:
            with open(p, "wb") as fh:          # sparse placeholder, no data downloaded
                fh.truncate(it.size)
            sha1 = it.sha1
        st = p.stat()
        entries.append({"rel": it.rel, "id": it.id, "etag": it.etag, "size": it.size, "sha1": sha1,
                        "full": full, "inode": st.st_ino, "mtime_ns": st.st_mtime_ns})
    meta = dest / META
    meta.mkdir(exist_ok=True)
    manifest = {"base": od.base, "entries": entries}
    (meta / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def load_manifest(dest: Path) -> dict:
    return json.loads((dest / META / "manifest.json").read_text(encoding="utf-8"))


def install_resolver(dest: Path, od_factory=None) -> None:
    """Make content_hash() answer for placeholders from OneDrive metadata (or a lazy download)."""
    from .hashing import set_resolver
    m = load_manifest(dest)
    by_inode = {e["inode"]: e for e in m["entries"]}
    cache: dict[int, str] = {}

    def resolve(path: Path) -> str | None:
        try:
            st = path.stat()
        except OSError:
            return None
        e = by_inode.get(st.st_ino)
        if e is None or e["full"]:
            return None                       # real bytes on disk: hash them
        if e.get("sha1"):
            return e["sha1"]
        if st.st_ino not in cache and od_factory is not None:
            cache[st.st_ino] = hashlib.sha1(od_factory().download(e["id"])).hexdigest()
        return cache.get(st.st_ino)

    set_resolver(resolve)


# -- push ----------------------------------------------------------------------------------

@dataclass
class PushPlan:
    tracker_updates: list = field(default_factory=list)   # (entry, path)
    moves: list = field(default_factory=list)             # (entry, new_rel)
    uploads: list = field(default_factory=list)           # (rel, path)
    automation_updates: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def plan_push(dest: Path) -> PushPlan:
    m = load_manifest(dest)
    by_inode = {e["inode"]: e for e in m["entries"]}
    by_rel = {e["rel"]: e for e in m["entries"]}
    files = [p for p in sorted(dest.rglob("*"))
             if p.is_file() and META not in p.relative_to(dest).parts]
    present = {p.stat().st_ino for p in files}
    seen: set[int] = set()
    plan = PushPlan()
    for p in files:
        rel = p.relative_to(dest).as_posix()
        st = p.stat()
        e = by_inode.get(st.st_ino)
        if e is None and rel in by_rel and by_rel[rel]["inode"] not in present:
            # Saved atomically (temp file renamed over the original): same file, new content.
            e = by_rel[rel]
        if e is None:
            if st.st_size and _all_zero(p):
                plan.errors.append(f"refused to upload {rel}: content is all zero bytes (copied placeholder?)")
            else:
                plan.uploads.append((rel, p))
            continue
        seen.add(e["inode"])
        if rel != e["rel"]:
            plan.moves.append((e, rel))
        changed = (_sha1(p) != e["sha1"]) if e["full"] else (
            st.st_ino != e["inode"] or st.st_size != e["size"] or st.st_mtime_ns != e["mtime_ns"])
        if changed:
            if e["rel"] in WRITABLE and rel == e["rel"]:
                plan.tracker_updates.append((e, p))
            elif e["rel"].startswith("_automation/") and rel == e["rel"]:
                plan.automation_updates.append((e, p))
            else:
                plan.errors.append(f"{e['rel']} was modified locally but is not writable; not pushed")
    for e in m["entries"]:
        if e["inode"] not in seen:
            plan.errors.append(f"{e['rel']} disappeared from the mirror; left untouched in OneDrive")
    return plan


def push(od: OneDrive, dest: Path, dry_run: bool = False) -> dict:
    plan = plan_push(dest)
    report = {"tracker": [], "moved": [], "uploaded": [], "automation": [], "errors": list(plan.errors),
              "aborted": False}
    if dry_run:
        report.update(tracker=[e["rel"] for e, _ in plan.tracker_updates],
                      moved=[f"{e['rel']} -> {n}" for e, n in plan.moves],
                      uploaded=[r for r, _ in plan.uploads],
                      automation=[e["rel"] for e, _ in plan.automation_updates])
        return report
    try:
        for e, p in plan.tracker_updates:
            od.replace(e["id"], p.read_bytes(), e["etag"])
            report["tracker"].append(e["rel"])
    except ConflictError:
        report["aborted"] = True
        report["errors"].append("The live tracker was changed in OneDrive during the run (someone edited it). "
                                "Nothing was pushed; the next run will redo the work.")
        return report
    for e, new_rel in plan.moves:
        try:
            od.move(e["id"], new_rel)
            report["moved"].append(f"{e['rel']} -> {new_rel}")
        except Exception as ex:
            report["errors"].append(f"move {e['rel']} -> {new_rel} failed: {ex}")
    for rel, p in plan.uploads:
        try:
            od.upload_new(rel, p.read_bytes())
            report["uploaded"].append(rel)
        except Exception as ex:
            report["errors"].append(f"upload {rel} failed: {ex}")
    for e, p in plan.automation_updates:
        try:
            od.replace(e["id"], p.read_bytes(), e["etag"])
            report["automation"].append(e["rel"])
        except Exception as ex:
            report["errors"].append(f"update {e['rel']} failed: {ex}")
    return report


# -- run lock (compare-and-swap on the OneDrive eTag) ---------------------------------------

def _now() -> float:
    import time
    return time.time()


def acquire_lock(od: OneDrive, now: float | None = None) -> bool:
    """True if this run may proceed. A busy lock gets rerun=True so the running job runs again."""
    from .graph import GraphError
    now = now if now is not None else _now()
    mine = json.dumps({"state": "running", "since": now, "rerun": False}).encode()
    it = od.item(LOCK)
    if it is None:
        try:
            od.upload_new(LOCK, mine)
            return True
        except GraphError:
            it = od.item(LOCK)              # someone created it a moment ago
            if it is None:
                raise
    cur = json.loads(od.download(it["id"]) or b"{}")
    busy = cur.get("state") == "running" and now - float(cur.get("since", 0)) < LOCK_STALE_SECONDS
    try:
        if busy:
            cur["rerun"] = True
            od.replace(it["id"], json.dumps(cur).encode(), it["eTag"])
            return False
        od.replace(it["id"], mine, it["eTag"])
        return True
    except ConflictError:
        return False                         # lost the race: the other run will see new files


def release_lock(od: OneDrive) -> bool:
    """Mark the lock idle. Returns True if another run was requested while this one held it."""
    it = od.item(LOCK)
    if it is None:
        return False
    cur = json.loads(od.download(it["id"]) or b"{}")
    od.replace(it["id"], json.dumps({"state": "idle", "since": _now(), "rerun": False}).encode(), it["eTag"])
    return bool(cur.get("rerun"))


def new_inbox_files(od: OneDrive, dest: Path) -> list[str]:
    """Inbox files in OneDrive that this run never saw (arrived while it was running)."""
    seen = {e["rel"] for e in load_manifest(dest)["entries"]}
    plan = plan_push(dest)
    seen |= {r for r, _ in plan.uploads} | {n for _, n in plan.moves}
    items = od.list_tree({"processed"}, start="Receipts Inbox")
    return [i.rel for i in items if not i.folder and i.rel.startswith("Receipts Inbox/")
            and "/processed/" not in i.rel and i.rel not in seen]


# -- session: tokens and wiring ---------------------------------------------------------

STATE_DOC = "fonenova-cloud.json"


def save_access(dest: Path, od: OneDrive) -> None:
    (dest / META / "access.json").write_text(json.dumps(
        {"token": od.s.headers["Authorization"].split(" ", 1)[1], "base": od.base}), encoding="utf-8")


def install_mirror_resolver(dest: Path) -> None:
    """Used by CLI processes run with --mirror; lazy downloads reuse the session's access token."""
    def factory():
        a = json.loads((dest / META / "access.json").read_text(encoding="utf-8"))
        return OneDrive(a["token"], a["base"])
    install_resolver(dest, factory)


def ms_client_id() -> str:
    cid = os.environ.get("MS_CLIENT_ID")
    if not cid:
        from .layout import load_config
        cid = load_config().get("cloud", {}).get("ms_client_id", "")
    if not cid:
        raise RuntimeError("MS_CLIENT_ID is not set (config.toml [cloud] ms_client_id)")
    return cid


def onedrive_session(google_creds, base: str) -> OneDrive:
    """Exchange the stored Microsoft refresh token, persist the rotated one, return a client."""
    from .gmail import AppData
    from .graph import refresh
    store = AppData(google_creds)
    state = store.get(STATE_DOC) or {}
    rt = state.get("ms_refresh_token") or os.environ.get("MS_REFRESH_TOKEN")
    if not rt:
        raise RuntimeError("No Microsoft token stored yet. Run: python -m fonenova.cloud ms-auth (on the PC, once)")
    tok = refresh(ms_client_id(), rt)
    state["ms_refresh_token"] = tok.get("refresh_token", rt)
    store.put(STATE_DOC, state)
    return OneDrive(tok["access_token"], base)


# -- command line: python -m fonenova.cloud <cmd> ----------------------------------------

def _google():
    from .gmail import credentials
    from .layout import REPO
    return credentials(REPO / "secrets")


def _base(cfg: dict) -> str:
    return cfg.get("cloud", {}).get("onedrive_base", "Desktop/VAT RETURNS")


def main(argv=None) -> int:
    import argparse
    import sys
    from datetime import datetime as _dt
    from .layout import load_config

    ap = argparse.ArgumentParser(prog="fonenova.cloud")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ms-auth", help="PC, once: Microsoft sign-in; stores the token in Google appData")
    pp = sub.add_parser("prep", help="cloud: pull OneDrive mirror, fetch Gmail, write the work file")
    pp.add_argument("--dest", required=True)
    fp = sub.add_parser("finish", help="cloud: record the run, push to OneDrive, notify")
    fp.add_argument("--dest", required=True); fp.add_argument("--result")
    up = sub.add_parser("push", help="push the mirror back to OneDrive")
    up.add_argument("--dest", required=True); up.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    cfg = load_config()

    if args.cmd == "ms-auth":
        from .gmail import AppData
        from .graph import device_code_login
        tok = device_code_login(ms_client_id())
        store = AppData(_google())
        state = store.get(STATE_DOC) or {}
        state["ms_refresh_token"] = tok["refresh_token"]
        store.put(STATE_DOC, state)
        od = OneDrive(tok["access_token"], _base(cfg))
        print("Microsoft sign-in stored. OneDrive folder visible:", od.item("") is not None)
        return 0

    dest = Path(args.dest).resolve()
    cfg.update(root=str(dest), cloud_mode=True)   # not "cloud": that key holds the [cloud] settings

    if args.cmd == "prep":
        creds = _google()
        od = onedrive_session(creds, _base(cfg))
        if not acquire_lock(od):
            print(json.dumps({"busy": True, "work_needed": False,
                              "note": "another run is in progress; it will run again afterwards"}))
            return 0
        try:
            m = pull(od, dest)
        except Exception:
            release_lock(od)
            raise
        save_access(dest, od)
        install_mirror_resolver(dest)
        from .daily import Paths, collect
        from .gmail import service
        svc, gerr = None, None
        try:
            svc = service(Path("."), creds=creds)
        except Exception as e:
            gerr = str(e)
        summary = collect(cfg, svc, gerr)
        stamp = _dt.now().strftime("%Y%m%d-%H%M%S")
        P = Paths(dest)
        result = P.state / f"result-{stamp}.json"
        summary["result_file"] = str(result)
        import sys as _sys
        summary["cli"] = f"{_sys.executable} -m fonenova.cli --mirror \"{dest}\""
        P.save(f"work-{stamp}.json", summary)
        (dest / META / "current.json").write_text(json.dumps(
            {"work": str(P.state / f"work-{stamp}.json"), "result": str(result)}), encoding="utf-8")
        print(json.dumps({"files_listed": len(m["entries"]), "work_needed": summary["work_needed"],
                          "work_file": str(P.state / f"work-{stamp}.json"), "result_file": str(result),
                          "cli": summary["cli"], "candidates": summary["candidates"],
                          "row_issues": summary["row_issues"], "gmail": summary["gmail"]}, indent=2))
        return 0

    install_mirror_resolver(dest)
    if args.cmd == "push":
        a = json.loads((dest / META / "access.json").read_text(encoding="utf-8"))
        print(json.dumps(push(OneDrive(a["token"], a["base"]), dest, args.dry_run), indent=2))
        return 0

    if args.cmd == "finish":
        from .daily import finalize
        cur = json.loads((dest / META / "current.json").read_text(encoding="utf-8"))
        summary = json.loads(Path(cur["work"]).read_text(encoding="utf-8"))
        rpath = Path(args.result or cur["result"])
        result = json.loads(rpath.read_text(encoding="utf-8")) if rpath.exists() else None
        extra = [] if (result is not None or not summary.get("work_needed")) else \
            ["The cloud run did not produce a result file"]
        note = finalize(cfg, summary, result, extra)
        creds = _google()
        od = onedrive_session(creds, _base(cfg))       # fresh token: the run may have taken a while
        report = push(od, dest)
        if report["errors"]:
            title, body = note or ("Expenses: action needed", "")
            note = ("Expenses: action needed", body + "\n\nOneDrive sync problems:\n" +
                    "\n".join(f"- {e}" for e in report["errors"]))
        if note:
            from .gmail import send_self, service
            send_self(service(Path("."), creds=creds), f"[Fone Nova expenses] {note[0]}", note[1])
        replies = []
        if result and not report["aborted"]:
            from . import whatsapp as wa
            for rep in result.get("whatsapp_replies", []):
                num = wa.number_for(rep.get("to", ""))
                try:
                    if num:
                        wa.send_text(num, rep["text"])
                        replies.append(rep.get("to"))
                except Exception as ex:
                    report["errors"].append(f"WhatsApp reply to {rep.get('to')} failed: {ex}")
        late = new_inbox_files(od, dest)
        rerun = release_lock(od)
        retriggered = False
        if late or rerun:
            from .whatsapp import fire_trigger
            retriggered = fire_trigger(f"{len(late)} file(s) arrived during the previous run")[0]
        print(json.dumps({"push": report, "notified": bool(note), "whatsapp_replies": replies,
                          "late_files": late, "retriggered": retriggered}, indent=2))
        return 1 if report["aborted"] else 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
