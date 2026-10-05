"""Unattended daily routine.

1. Fetch receipt emails (Gmail API) into VAT RETURNS/_inbox/gmail.
2. Scan both receipts roots and the inbox for candidates; drop exact duplicates of filed receipts.
3. Audit the live tracker for half-finished rows and structural damage.
4. If there is work, hand it to Claude Code headless (routine/daily-prompt.md), which logs,
   files and verifies using the CLI, then writes a result JSON.
5. Notify only when something needs Hamza. Always append one line to docs/run-log.md.
"""
from __future__ import annotations

import json
import subprocess
from datetime import date, datetime
from pathlib import Path

from .backup import excel_lock_file
from .layout import REPO, layouts, load_config

STATE = REPO / "state"
SECRETS = REPO / "secrets"
RUN_LOG = REPO / "docs" / "run-log.md"
PROMPT = REPO / "routine" / "daily-prompt.md"
DEADLINE = date(2026, 11, 7)
REMINDERS = {date(2026, 10, 31): "VAT return due 7 Nov (1 week). Pack: python -m fonenova.cli pack",
             date(2026, 11, 5): "VAT return due in 2 days (7 Nov). Send the pack to the accountant."}
CLAUDE = Path.home() / ".local" / "bin" / "claude.exe"


def _load(name: str, default):
    p = STATE / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _save(name: str, data) -> None:
    STATE.mkdir(exist_ok=True)
    (STATE / name).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _log(line: str) -> None:
    with open(RUN_LOG, "a", encoding="utf-8") as fh:
        fh.write(f"- {datetime.now():%Y-%m-%d %H:%M} {line}\n")


def run(today: date | None = None, use_claude: bool = True) -> dict:
    today = today or date.today()
    cfg = load_config()
    root = Path(cfg["root"])
    lays = layouts(cfg)
    alerts: list[str] = []
    summary: dict = {"date": str(today), "gmail": None, "candidates": [], "row_issues": [],
                     "claude": None}

    # 1. Gmail
    svc = None
    try:
        from .gmail import fetch, service
        svc = service(SECRETS)
        got = fetch(svc, root / "_inbox" / "gmail", STATE / "gmail_seen.json")
        summary["gmail"] = {"messages": len(got),
                            "skipped": [e["subject"] for e in got if e["skipped"]]}
    except Exception as e:
        summary["gmail"] = {"error": str(e)}
        if _load("last_gmail_error_day.json", "") != str(today):
            alerts.append(f"Gmail access problem: {e}")
            _save("last_gmail_error_day.json", str(today))

    # 2. Candidates
    from .intake import scan
    cands = scan(lays, root)
    new = [c for c in cands if c.duplicate_of is None]
    dups = [c for c in cands if c.duplicate_of]
    summary["candidates"] = [{"path": str(c.path), "source": c.source, "size": c.size} for c in new]
    summary["duplicates"] = [{"path": str(c.path), "same_as": c.duplicate_of} for c in dups]

    # 3. Live tracker health
    from .audit import audit_tracker
    a = audit_tracker(lays["septdec"])
    issues = [f"row {r}: {k}" for k, r, _ in a.row_issues] + a.structure
    summary["row_issues"] = issues
    summary["totals"] = {"last_row": a.snap.last_row, "gross": a.snap.gross, "vat": a.snap.vat}

    # Silence when nothing changed since the last run.
    fingerprint = sorted([c.sha for c in new] + issues)
    changed = fingerprint != _load("last_fingerprint.json", [])
    work = bool(new or issues)

    # 4. Claude
    if work and changed and use_claude:
        lock = excel_lock_file(lays["septdec"].path)
        if lock:
            alerts.append("Excel has the live tracker open, so nothing could be logged. Close Excel; "
                          "the next run will pick it up.")
        else:
            summary["claude"] = _run_claude(summary)
            res = summary["claude"].get("result") or {}
            for item in res.get("logged", []):
                alerts.append(f"Logged: {item}")
            for item in res.get("needs_hamza", []):
                alerts.append(f"Needs you: {item}")
            for item in res.get("errors", []):
                alerts.append(f"Error: {item}")
            if summary["claude"].get("error"):
                alerts.append(f"Daily run error: {summary['claude']['error']}")
    _save("last_fingerprint.json", fingerprint)

    # 5. Deadline reminders, once each
    sent = set(_load("reminders_sent.json", []))
    for d, msg in REMINDERS.items():
        if today >= d and str(d) not in sent and today <= DEADLINE:
            alerts.append(msg)
            sent.add(str(d))
    _save("reminders_sent.json", sorted(sent))

    if alerts:
        title = "Expenses: " + ("action needed" if any(x.startswith(("Needs", "Error", "Gmail", "Excel", "Daily"))
                                                        for x in alerts) else "update")
        body = "\n".join(f"- {x}" for x in alerts) + (
            f"\n\nTracker: rows to {a.snap.last_row}, £{a.snap.gross:,.2f} gross / £{a.snap.vat:,.2f} VAT.")
        summary["notified"] = __import__("fonenova.notify", fromlist=["notify"]).notify(title, body, svc)

    _save("last_run.json", summary)
    _log(f"daily: gmail {summary['gmail']}, {len(new)} new candidate(s), {len(dups)} duplicate(s), "
         f"{len(issues)} tracker issue(s), {'claude ran' if summary['claude'] else 'no claude run'}, "
         f"{len(alerts)} alert(s)")
    return summary


def _run_claude(summary: dict) -> dict:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    work = STATE / f"work-{stamp}.json"
    result = STATE / f"result-{stamp}.json"
    _save(work.name, {**summary, "result_file": str(result)})
    prompt = PROMPT.read_text(encoding="utf-8").replace("{WORK_FILE}", str(work)).replace(
        "{RESULT_FILE}", str(result))
    root = load_config()["root"]
    cmd = [str(CLAUDE), "-p", prompt, "--permission-mode", "acceptEdits",
           "--add-dir", root,
           "--allowedTools", "Read", "Glob", "Grep", "Write", "Edit",
           "Bash(.venv/Scripts/python.exe -m fonenova.cli:*)"]
    try:
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=1800,
                           encoding="utf-8", errors="replace")
        (STATE / f"claude-{stamp}.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr,
                                                   encoding="utf-8")
        out = {"returncode": r.returncode}
        if result.exists():
            out["result"] = json.loads(result.read_text(encoding="utf-8"))
        else:
            out["error"] = f"Claude run ended (code {r.returncode}) without writing a result file"
        return out
    except Exception as e:
        return {"error": str(e)}
