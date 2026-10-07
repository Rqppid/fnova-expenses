"""Daily routine, shared by the PC task (local) and the cloud job (OneDrive mirror).

collect()   Gmail fetch into the Receipts Inbox, candidate scan, live-tracker health check.
            Returns a work summary; `work_needed` says whether there is anything to do.
(work)      Claude logs, files and verifies with the CLI (headless on the PC, or the cloud
            agent itself), writing a result JSON.
finalize()  Alerts, deadline reminders, run state and one run-log line. Notification is
            sent only when something needs Hamza.

State and the run log live in VAT RETURNS/_automation/ so both modes share them.
"""
from __future__ import annotations

import json
import subprocess
from datetime import date, datetime
from pathlib import Path

from .backup import excel_lock_file
from .intake import inbox_dir
from .layout import REPO, layouts, load_config

SECRETS = REPO / "secrets"
PROMPT = REPO / "routine" / "daily-prompt.md"
DEADLINE = date(2026, 11, 7)
REMINDERS = {date(2026, 10, 31): "VAT return due 7 Nov (1 week). Pack: python -m fonenova.cli pack",
             date(2026, 11, 5): "VAT return due in 2 days (7 Nov). Send the pack to the accountant."}
CLAUDE = Path.home() / ".local" / "bin" / "claude.exe"
# Commands the unattended run may use. Deliberately excludes delete: removing rows is Hamza's call.
ALLOWED_CLI = ("find", "add", "complete", "file", "statement", "fx", "archive", "verify", "audit", "status")


class Paths:
    def __init__(self, root: Path):
        self.root = root
        self.auto = root / "_automation"
        self.state = self.auto / "state"
        self.run_log = self.auto / "run-log.md"

    def load(self, name: str, default):
        p = self.state / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

    def save(self, name: str, data) -> None:
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / name).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def log(self, line: str) -> None:
        self.auto.mkdir(parents=True, exist_ok=True)
        with open(self.run_log, "a", encoding="utf-8") as fh:
            fh.write(f"- {datetime.now():%Y-%m-%d %H:%M} {line}\n")


def collect(cfg: dict, gmail_svc=None, gmail_error: str | None = None, today: date | None = None) -> dict:
    today = today or date.today()
    root = Path(cfg["root"])
    P = Paths(root)
    lays = layouts(cfg)
    summary: dict = {"date": str(today), "root": str(root), "gmail": None, "candidates": [],
                     "duplicates": [], "row_issues": [], "alerts": []}

    if gmail_svc is not None:
        try:
            from .gmail import fetch
            got = fetch(gmail_svc, inbox_dir(root) / "gmail", P.state / "gmail_seen.json")
            summary["gmail"] = {"messages": len(got), "skipped": [e["subject"] for e in got if e["skipped"]]}
        except Exception as e:
            gmail_error = str(e)
    if gmail_error:
        summary["gmail"] = {"error": gmail_error}
        if P.load("last_gmail_error_day.json", "") != str(today):
            summary["alerts"].append(f"Gmail access problem: {gmail_error}")
            P.save("last_gmail_error_day.json", str(today))

    from .intake import scan
    cands = scan(lays, root)
    new = [c for c in cands if c.duplicate_of is None]
    summary["candidates"] = [{"path": str(c.path), "source": c.source, "size": c.size} for c in new]
    summary["duplicates"] = [{"path": str(c.path), "same_as": c.duplicate_of}
                             for c in cands if c.duplicate_of]

    from .audit import tracker_health
    a = tracker_health(lays["septdec"])
    known = {int(k) for k in cfg.get("known_issues", {}).get("septdec", {})}
    issues = [f"row {r}: {k}" for k, r, _ in a.row_issues if r not in known] + a.structure
    summary["row_issues"] = issues
    summary["totals"] = {"last_row": a.snap.last_row, "gross": a.snap.gross, "vat": a.snap.vat}

    fingerprint = sorted([c.sha for c in new] + issues)
    summary["work_needed"] = bool(new or issues) and fingerprint != P.load("last_fingerprint.json", [])
    summary["_fingerprint"] = fingerprint
    return summary


def finalize(cfg: dict, summary: dict, result: dict | None, extra_errors=(),
             today: date | None = None) -> tuple[str, str] | None:
    """Records state and the run log. Returns (title, body) when Hamza should be notified."""
    today = today or date.today()
    P = Paths(Path(cfg["root"]))
    alerts = list(summary.get("alerts", []))
    res = result or {}
    alerts += [f"Logged: {x}" for x in res.get("logged", [])]
    alerts += [f"Fixed: {x}" for x in res.get("completed", [])]
    alerts += [f"Needs you: {x}" for x in res.get("needs_hamza", [])]
    alerts += [f"Receipt missing (logged from bank statement): {x}" for x in res.get("missing_receipts", [])]
    alerts += [f"Error: {x}" for x in list(res.get("errors", [])) + list(extra_errors)]
    P.save("last_fingerprint.json", summary.get("_fingerprint", []))

    sent = set(P.load("reminders_sent.json", []))
    for d, msg in REMINDERS.items():
        if today >= d and str(d) not in sent and today <= DEADLINE:
            alerts.append(msg)
            sent.add(str(d))
    P.save("reminders_sent.json", sorted(sent))
    P.save("last_run.json", {**summary, "result": res, "alerts": alerts})

    t = summary.get("totals", {})
    P.log(f"{'cloud' if cfg.get('cloud_mode') else 'pc'} run: {len(summary['candidates'])} new candidate(s), "
          f"{len(summary['duplicates'])} duplicate(s), {len(summary['row_issues'])} tracker issue(s), "
          f"logged {len(res.get('logged', []))}, alerts {len(alerts)}, gmail {summary.get('gmail')}")
    if not alerts:
        return None
    urgent = any(x.startswith(("Needs", "Error", "Gmail", "Excel")) for x in alerts)
    body = "\n".join(f"- {x}" for x in alerts)
    if t:
        body += (f"\n\nTracker: rows to {t.get('last_row')}, £{t.get('gross', 0):,.2f} gross / "
                 f"£{t.get('vat', 0):,.2f} VAT.")
    return ("Expenses: " + ("action needed" if urgent else "update"), body)


# -- PC mode -------------------------------------------------------------------------------

def run(today: date | None = None, use_claude: bool = True) -> dict:
    cfg = load_config()
    svc, gerr = None, None
    try:
        from .gmail import service
        svc = service(SECRETS)
    except Exception as e:
        gerr = str(e)
    summary = collect(cfg, svc, gerr, today)
    result, extra = None, []
    if summary["work_needed"] and use_claude:
        if excel_lock_file(layouts(cfg)["septdec"].path):
            extra.append("Excel has the live tracker open, so nothing could be logged. Close Excel; "
                         "the next run will pick it up.")
        else:
            out = _run_claude(summary, Paths(Path(cfg["root"])))
            result = out.get("result")
            if out.get("error"):
                extra.append(out["error"])
    note = finalize(cfg, summary, result, extra, today)
    if note:
        from .notify import notify
        summary["notified"] = notify(*note, gmail_svc=svc)
    return summary


def _run_claude(summary: dict, P: Paths) -> dict:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    work = P.state / f"work-{stamp}.json"
    result = P.state / f"result-{stamp}.json"
    P.save(work.name, {**summary, "result_file": str(result)})
    prompt = (PROMPT.read_text(encoding="utf-8").replace("{WORK_FILE}", str(work))
              .replace("{RESULT_FILE}", str(result))
              .replace("{CLI}", ".venv/Scripts/python.exe -m fonenova.cli"))
    cmd = [str(CLAUDE), "-p", prompt, "--permission-mode", "acceptEdits", "--add-dir", str(P.root),
           "--allowedTools", "Read", "Glob", "Grep", "Write", "Edit",
           *[f"Bash(.venv/Scripts/python.exe -m fonenova.cli {c}:*)" for c in ALLOWED_CLI]]
    try:
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=1800,
                           encoding="utf-8", errors="replace")
        (P.state / f"claude-{stamp}.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr,
                                                    encoding="utf-8")
        if result.exists():
            return {"result": json.loads(result.read_text(encoding="utf-8"))}
        return {"error": f"Claude run ended (code {r.returncode}) without writing a result file"}
    except Exception as e:
        return {"error": str(e)}
