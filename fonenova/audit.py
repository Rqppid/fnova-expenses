"""Two-way reconciliation of trackers against their receipt folders, as a markdown report."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import openpyxl

from .layout import Layout
from .receipts import ReceiptFile, ReceiptIndex, build_index, tokens
from .sheet import Row, Snapshot, read_snapshot_ws
from .verify import structural_problems

CITED_RE = re.compile(r"([A-Za-z0-9][\w&'+ .,#()\-]*?\.(?:pdf|png|jpe?g|txt|html?|msg))(?![\w])",
                      re.IGNORECASE)
CITE_PREFIX_RE = re.compile(r"^.*?\b(?:matched to|and|filed as|as)\s+", re.IGNORECASE)
KNOWN_COLS = set("DEGIKNPQR")


@dataclass
class Match:
    row: Row
    files: list[ReceiptFile]
    how: str                       # cited | cited-stem | vendor+date | date-only | none
    stale_citations: list[str] = field(default_factory=list)


@dataclass
class TrackerAudit:
    layout: Layout
    snap: Snapshot
    index: ReceiptIndex
    structure: list[str]
    row_issues: list[tuple[str, int, str]]
    w_flags: list[str]
    stray_cells: list[str]
    out_of_period: list[str]
    matches: list[Match]
    orphans: list[ReceiptFile]
    pending: list[tuple[ReceiptFile, str]]
    duplicates: list[tuple[ReceiptFile, ReceiptFile]]   # (copy, original)
    junk: list[ReceiptFile]
    loose_root: list[ReceiptFile]


def cited_names(remarks: str) -> list[str]:
    out = []
    for m in CITED_RE.finditer(remarks or ""):
        name = CITE_PREFIX_RE.sub("", m.group(1)).strip(" '\"")
        # A comma inside the capture means it ran across a clause; keep the last piece.
        name = name.split(", ")[-1].strip()
        if name:
            out.append(name)
    return out


def _row_issues(snap: Snapshot) -> tuple[list[tuple[str, int, str]], list[str], list[str]]:
    """Returns (issues as (kind, row, label), W-flag lines, out-of-period lines)."""
    issues, wflags, oop = [], [], []
    lay = snap.layout
    for r in snap.rows:
        label = f"{r.date_text} {r.vendor} {r.amount_raw}"
        add = lambda kind: issues.append((kind, r.r, label))  # noqa: E731
        if not any([r.date_text, r.vendor, r.amount_raw, r.remarks]):
            add("blank row inside the data range")
            continue
        if not r.amount_is_numeric:
            add("amount not numeric" + (" (text, parseable)" if r.amount is not None else " (missing)"))
        if r.date is None:
            add("date not DD.MM.YY")
        elif r.date_text and not re.match(r"^\d\d\.\d\d\.\d\d$", r.date_text):
            add("date not zero-padded")
        if not r.remarks:
            add("Remarks empty")
        if r.receipt != "Receipt:Yes":
            add(f"Receipt column is {r.receipt!r}")
        if r.vat_flag not in ("VAT-Yes", "VAT-No"):
            add(f"VAT flag is {r.vat_flag!r}")
        if r.vat_flag == "VAT-Yes" and not isinstance(r.vat_raw, (int, float)):
            add("VAT-Yes but no VAT amount (reclaim missing)")
        if r.vat_flag == "VAT-No" and isinstance(r.vat_raw, (int, float)) and r.vat_raw:
            add("VAT-No but a VAT amount is present")
        bad = [col for col, f in lay.helper_formulas(r.r).items() if r.helpers.get(col) != f]
        if bad:
            add(f"helper formulas missing/wrong ({','.join(bad)})")
        if (r.vat_flag == "VAT-Yes" and r.amount is not None and isinstance(r.vat_raw, (int, float))
                and abs(r.vat_raw - round(r.amount / 6, 2)) >= 0.02):
            wflags.append(f"row {r.r} {r.date_text} {r.vendor} £{r.amount:.2f}: VAT £{r.vat_raw:.2f} "
                          f"vs 20% auto-calc £{round(r.amount / 6, 2):.2f} (W shows 'Check VAT amount')")
        if r.date and not (lay.period_start <= r.date <= lay.period_end):
            oop.append(f"row {r.r} {label}: dated outside the tracker period")
    return issues, wflags, oop


def _group_issues(issues: list[tuple[str, int, str]]) -> list[str]:
    groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for kind, r, label in issues:
        groups[kind].append((r, label))
    out = []
    for kind, items in groups.items():
        if len(items) <= 4:
            out.append(f"{kind}: " + "; ".join(f"row {r} ({lab})" for r, lab in items))
        else:
            out.append(f"{kind} ({len(items)} rows): " + ", ".join(str(r) for r, _ in items))
    return out


def _stray_cells(wb, snap: Snapshot) -> list[str]:
    ws = wb[snap.layout.log_sheet]
    allowed = KNOWN_COLS | set(snap.layout.helpers) | set(snap.layout.side_cols)
    out = []
    for r in range(snap.layout.first_row, snap.total_row):
        for c in ws[r]:
            if c.value is not None and str(c.value).strip() and c.column_letter not in allowed:
                out.append(f"{c.coordinate} = {c.value!r}")
    for r in range(snap.total_row + 2, ws.max_row + 1):
        vals = [f"{c.coordinate}={c.value!r}" for c in ws[r]
                if c.value is not None and str(c.value).strip() and c.column_letter not in snap.layout.side_cols]
        if vals:
            out.append(f"below Net Total, row {r}: " + ", ".join(vals[:6]))
    return out


REF_TOKEN_RE = re.compile(r"[A-Za-z0-9\-]{6,}")


def _ref_tokens(ref: str) -> set[str]:
    """Distinctive reference numbers (booking refs, invoice numbers) from the Ref column."""
    out = set()
    for t in REF_TOKEN_RE.findall(ref or ""):
        if sum(ch.isdigit() for ch in t) >= 2 and not re.fullmatch(r"\d{1,2}-\d{1,2}-\d{2,4}", t):
            out.add(t.lower())
    return out


AMOUNT_IN_NAME_RE = re.compile(r"(?<![\d.])(\d{1,4}\.\d{2})(?![\d])")


def _match(snap: Snapshot, idx: ReceiptIndex) -> list[Match]:
    """File-centric matching, strongest evidence first.

    1. The row's Remarks cite the file by name (or by stem, if the extension changed).
    2. A reference number from the Ref column appears in the file name.
    3. Same date, scored on vendor tokens (x2) and description tokens; best row wins.
    4. The file name contains the row's exact amount, within 3 days (receipt date vs debit date).
    5. Vendor tokens match within 3 days.
    6. A row still without a file takes the only unclaimed file with its date.
    """
    cands = idx.candidates()
    by_name = {f.name.lower(): f for f in cands}
    by_stem = defaultdict(list)
    for f in cands:
        by_stem[f.stem.lower()].append(f)
    files_of: dict[int, list[ReceiptFile]] = defaultdict(list)
    how_of: dict[int, str] = {}
    stale_of: dict[int, list[str]] = defaultdict(list)
    claimed: set[str] = set()

    def claim(r: Row, f: ReceiptFile, how: str):
        if f not in files_of[r.r]:
            files_of[r.r].append(f)
        how_of.setdefault(r.r, how)
        claimed.add(f.rel)

    for r in snap.rows:
        for name in cited_names(r.remarks):
            name = name.lstrip("'\"(")
            f = by_name.get(name.lower())
            if f:
                claim(r, f, "cited")
            elif by_stem.get(Path(name).stem.lower()):
                for f in by_stem[Path(name).stem.lower()]:
                    claim(r, f, "cited-stem")
                stale_of[r.r].append(name)
            else:
                stale_of[r.r].append(name)
        refs = _ref_tokens(r.ref)
        if refs:
            for f in cands:
                if any(t in f.name.lower() for t in refs):
                    claim(r, f, "ref")

    rows_by_date = defaultdict(list)
    for r in snap.rows:
        if r.date:
            rows_by_date[r.date].append(r)
    for f in cands:
        if f.rel in claimed or not f.date:
            continue
        best, score = None, 0
        for r in rows_by_date.get(f.date, []):
            sc = 2 * len(tokens(r.vendor) & f.tokens) + len(tokens(r.desc) & f.tokens)
            if sc > score:
                best, score = r, sc
        if best is not None:
            claim(best, f, "vendor+date")

    def near(f, r):
        return f.date and r.date and abs((f.date - r.date).days) <= 3

    for f in cands:
        if f.rel in claimed:
            continue
        amounts = {float(a) for a in AMOUNT_IN_NAME_RE.findall(f.name)}
        if not amounts:
            continue
        hits = [r for r in snap.rows if r.amount is not None and round(r.amount, 2) in amounts
                and (near(f, r) or not f.date)]
        if len(hits) >= 1:
            hits.sort(key=lambda r: (-len(tokens(r.vendor) & f.tokens),
                                     abs((f.date - r.date).days) if f.date and r.date else 9))
            claim(hits[0], f, "amount")

    for f in cands:
        if f.rel in claimed or not f.date:
            continue
        best, score = None, 0
        for r in snap.rows:
            if near(f, r) and not files_of[r.r]:
                sc = len(tokens(r.vendor) & f.tokens)
                if sc > score:
                    best, score = r, sc
        if best is not None:
            claim(best, f, "vendor+near-date")

    for r in snap.rows:
        if files_of[r.r] or not r.date:
            continue
        free = [f for f in cands if f.date == r.date and f.rel not in claimed]
        if len(free) == 1:
            claim(r, free[0], "date-only")

    out = []
    for r in snap.rows:
        how = how_of.get(r.r, "none")
        # A stale citation only matters when the row has no correctly cited file.
        stale = stale_of[r.r] if how != "cited" else []
        out.append(Match(r, files_of[r.r], how, stale))
    return out


@dataclass
class TrackerHealth:
    snap: Snapshot
    row_issues: list[tuple[str, int, str]]
    structure: list[str]


def tracker_health(layout: Layout) -> TrackerHealth:
    """Row and structure checks only: no receipt-folder scan, so no file fingerprints are needed.
    The routine uses this; the full audit_tracker() stays for reports and the return pack."""
    wb = openpyxl.load_workbook(layout.path)
    snap = read_snapshot_ws(wb, layout)
    structure = [p for p in structural_problems(snap) if not p.startswith("row ")]
    issues, _, _ = _row_issues(snap)
    return TrackerHealth(snap, issues, structure)


def audit_tracker(layout: Layout) -> TrackerAudit:
    wb = openpyxl.load_workbook(layout.path)
    snap = read_snapshot_ws(wb, layout)
    idx = build_index(layout.receipts, layout.ignore_dirs)
    structure = [p for p in structural_problems(snap) if not p.startswith("row ")]
    issues, wflags, oop = _row_issues(snap)
    matches = _match(snap, idx)

    matched = {f.rel: f for m in matches for f in m.files}
    by_hash: dict[str, ReceiptFile] = {}
    for f in matched.values():
        by_hash.setdefault(f.sha, f)
    pending_cfg = {k.replace("\\", "/"): v for k, v in layout.pending.items()}

    orphans, pending, dups = [], [], []
    seen_hash: dict[str, ReceiptFile] = {}
    for f in idx.candidates():
        if f.rel in matched:
            continue
        if f.rel in pending_cfg:
            pending.append((f, pending_cfg[f.rel]))
            continue
        orig = by_hash.get(f.sha) or seen_hash.get(f.sha)
        if orig is not None:
            dups.append((f, orig))
            continue
        seen_hash.setdefault(f.sha, f)
        orphans.append(f)
    # Exact copies among matched files too (e.g. two files cited by one row are the same bytes).
    groups = defaultdict(list)
    for f in matched.values():
        groups[f.sha].append(f)
    for g in groups.values():
        for extra in g[1:]:
            dups.append((extra, g[0]))

    junk = [f for f in idx.files if f.junk]
    loose = [f for f in idx.files if f.at_root]
    return TrackerAudit(layout, snap, idx, structure, issues, wflags, _stray_cells(wb, snap), oop,
                        matches, orphans, pending, dups, junk, loose)


def cross_duplicates(a: TrackerAudit, b: TrackerAudit) -> list[str]:
    out = []
    idx = defaultdict(list)
    for r in b.snap.rows:
        if r.date and r.amount is not None:
            idx[(r.date, round(r.amount, 2))].append(r)
    for r in a.snap.rows:
        if r.date and r.amount is not None:
            for o in idx.get((r.date, round(r.amount, 2)), []):
                out.append(f"{a.layout.key} row {r.r} and {b.layout.key} row {o.r}: "
                           f"{r.date_text} £{r.amount:.2f} ({r.vendor} / {o.vendor})")
    return out


# -- rendering -------------------------------------------------------------------------

def _bullets(items, empty="none") -> str:
    items = list(items)
    return "\n".join(f"- {i}" for i in items) if items else f"- {empty}"


def render_tracker(t: TrackerAudit, detail_matches: bool) -> str:
    s, lay = t.snap, t.layout
    month = "\n".join(f"| {y}-{m:02d} | {g:,.2f} | {v:,.2f} | {g - v:,.2f} |"
                      for (y, m), (g, v) in s.monthly().items())
    weak = [m for m in t.matches if m.how in ("date-only", "vendor+near-date")]
    none = [m for m in t.matches if m.how == "none"]
    stale = [m for m in t.matches if m.stale_citations]
    transcript = [m for m in t.matches if m.files and all(f.is_transcript for f in m.files)]
    lines = [
        f"## {lay.key}: {lay.path.name}",
        f"Data rows {lay.first_row} to {s.last_row}, Total row {s.total_row}, Net Total row {s.total_row + 1}. "
        f"**Gross £{s.gross:,.2f} / VAT £{s.vat:,.2f} / Net £{s.net:,.2f}.**",
        "", "| Month | Gross | VAT | Net |", "|---|---|---|---|", month, "",
        "### Structure (Total, Net Total, summary ranges)", _bullets(t.structure, "OK"),
        "", "### Row problems", _bullets(_group_issues(t.row_issues)),
        "", "### Stray cells (outside the log columns, or below Net Total)", _bullets(t.stray_cells),
        "", "### Rows dated outside the tracker period", _bullets(t.out_of_period),
        "", "### VAT amount differs from 20% auto-calc (W column flag)", _bullets(t.w_flags),
        "", "### Rows with no receipt file found",
        _bullets(f"row {m.row.r} {m.row.date_text} {m.row.vendor} £{m.row.amount_raw}" for m in none),
        "", "### Weak matches (date only, or vendor within 3 days): check",
        _bullets(f"row {m.row.r} [{m.how}] {m.row.date_text} {m.row.vendor}: {m.files[0].rel}" for m in weak),
        "", "### Evidence is only a transcription or saved page (.txt/.html), not the original receipt",
        _bullets(f"row {m.row.r} {m.row.date_text} {m.row.vendor} £{m.row.amount_raw}"
                 f"{f' (VAT £{m.row.vat_raw})' if m.row.vat_flag == 'VAT-Yes' else ''}: "
                 + ", ".join(f.rel for f in m.files) for m in transcript),
        "", "### Remarks cite a file name that no longer exists (renamed since)",
        _bullets(f"row {m.row.r}: {', '.join(m.stale_citations)}" for m in stale),
        "", "### Receipt files with no tracker row (orphans)",
        _bullets(f"{f.rel} ({f.size:,} bytes)" for f in t.orphans),
        "", "### Known pending (config.toml), not logged on purpose",
        _bullets(f"{f.rel}: {why}" for f, why in t.pending),
        "", "### Exact duplicate copies (same bytes), safe to delete with your OK",
        _bullets(f"{d.rel} = {o.rel}" for d, o in t.duplicates),
        "", "### Junk (zero-byte, shortcuts, ignored folders)",
        _bullets(f"{f.rel}: {f.junk}" for f in t.junk if not f.junk.startswith("in ignored"))
        + (f"\n- {sum(1 for f in t.junk if f.junk.startswith('in ignored'))} files in ignored folders "
           f"{', '.join(lay.ignore_dirs)}" if lay.ignore_dirs else ""),
        "", "### Saved web-page folders", _bullets(f"{k} ({n} files)" for k, n in t.index.saved_page_dirs.items()),
        "", "### Loose files at the receipts root", _bullets(f"{f.rel} ({f.size:,} bytes)" for f in t.loose_root),
    ]
    if detail_matches:
        lines += ["", "### Row to file matches", _bullets(
            f"row {m.row.r} [{m.how}] {m.row.date_text} {m.row.vendor}: " + ", ".join(f.rel for f in m.files)
            for m in t.matches)]
    return "\n".join(lines)


def run_audit(layouts: dict[str, Layout], detail_matches: bool = False) -> tuple[str, dict[str, TrackerAudit]]:
    audits = {k: audit_tracker(l) for k, l in layouts.items()}
    parts = [f"# Expense audit {datetime.now():%Y-%m-%d %H:%M}"]
    if "septdec" in audits and "v18" in audits:
        parts += ["", "## Cross-tracker duplicates (same date and amount in both trackers)",
                  _bullets(cross_duplicates(audits["septdec"], audits["v18"]))]
    for t in audits.values():
        parts += ["", render_tracker(t, detail_matches)]
    return "\n".join(parts) + "\n", audits
