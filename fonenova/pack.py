"""VAT return pack for the accountant: May to Oct 2026 (V18 + Sept-Dec's Sept/Oct rows).

Read-only on the trackers. Writes a new workbook plus a markdown summary.
Cross-tracker duplicates (same date and amount, same receipt) are counted once, from V18.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .audit import Match, TrackerAudit, audit_tracker
from .layout import Layout

REMARK_FLAGS = ("accountant", "not independently verified", "reclassif", "standard-rated",
                "no vat number", "donation", "charity", "check", "unconfirmed", "understat")


@dataclass
class PackRow:
    source: str
    row: int
    date: date
    vendor: str
    desc: str
    gross: float
    vat_flag: str
    vat: float
    evidence: str
    evidence_status: str
    remarks: str
    match: Match


def _evidence_status(m: Match) -> str:
    if not m.files:
        return "MISSING"
    if all(f.is_transcript for f in m.files):
        return "transcription only"
    if m.how in ("date-only", "vendor+near-date"):
        return "weak match, check"
    return "OK"


def collect(audits: dict[str, TrackerAudit], start: date, end: date) -> tuple[list[PackRow], list[str]]:
    rows: list[PackRow] = []
    notes: list[str] = []
    seen: dict[tuple, PackRow] = {}
    for key in ("v18", "septdec"):
        a = audits[key]
        for m in a.matches:
            r = m.row
            if not r.date or not (start <= r.date <= end):
                continue
            gross = r.amount if r.amount_is_numeric else 0.0
            vat = r.vat_raw if isinstance(r.vat_raw, (int, float)) else 0.0
            pr = PackRow(key, r.r, r.date, r.vendor, r.desc, gross, r.vat_flag, vat,
                         "; ".join(f.rel for f in m.files), _evidence_status(m), r.remarks, m)
            dk = (r.date, round(gross, 2), r.vendor.strip().lower())
            if dk in seen and seen[dk].source != key:
                o = seen[dk]
                notes.append(f"Excluded {key} row {r.r} ({r.date_text} {r.vendor} £{gross:.2f}): "
                             f"duplicate of {o.source} row {o.row}, same receipt")
                continue
            seen[dk] = pr
            rows.append(pr)
    rows.sort(key=lambda p: (p.date, p.source, p.row))
    return rows, notes


def exceptions(rows: list[PackRow], audits: dict[str, TrackerAudit]) -> list[tuple[str, str, str]]:
    """(row reference, issue, detail)."""
    out = []
    for p in rows:
        ref = f"{p.source} r{p.row} {p.date:%d.%m.%y} {p.vendor} £{p.gross:.2f}"
        r = p.match.row
        if not r.amount_is_numeric:
            out.append((ref, "Amount missing or not numeric", repr(r.amount_raw)))
        if p.vat_flag == "VAT-Yes" and not isinstance(r.vat_raw, (int, float)):
            out.append((ref, "VAT-Yes with no VAT amount", "reclaim missing from totals"))
        if p.vat_flag not in ("VAT-Yes", "VAT-No"):
            out.append((ref, "VAT flag not set", repr(p.vat_flag)))
        if (p.vat_flag == "VAT-Yes" and isinstance(r.vat_raw, (int, float)) and p.gross
                and abs(r.vat_raw - round(p.gross / 6, 2)) >= 0.02):
            out.append((ref, "VAT differs from 20% of gross",
                        f"£{r.vat_raw:.2f} vs £{round(p.gross / 6, 2):.2f} (split-rate or partial-VAT receipt?)"))
        if p.evidence_status != "OK":
            out.append((ref, f"Evidence: {p.evidence_status}", p.evidence or "no file found"))
        low = p.remarks.lower()
        hits = [k for k in REMARK_FLAGS if k in low]
        if hits:
            out.append((ref, "Remarks flag for review", ", ".join(hits)))
        if not p.remarks:
            out.append((ref, "No Remarks", ""))
    return out


def _sheet(wb: Workbook, title: str, header: list[str], data: list[list], widths: list[int]):
    ws = wb.create_sheet(title)
    ws.append(header)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="305496")
        c.alignment = Alignment(wrap_text=True, vertical="top")
    for row in data:
        ws.append(row)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    return ws


def build_pack(layouts: dict[str, Layout], out_dir: Path, start=date(2026, 5, 1),
               end=date(2026, 10, 31), due=date(2026, 11, 7)) -> tuple[Path, Path]:
    audits = {k: audit_tracker(layouts[k]) for k in ("v18", "septdec")}
    rows, notes = collect(audits, start, end)
    exc = exceptions(rows, audits)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")

    months: dict[tuple[int, int], list[float]] = {}
    for p in rows:
        acc = months.setdefault((p.date.year, p.date.month), [0.0, 0.0, 0])
        acc[0] += p.gross; acc[1] += p.vat; acc[2] += 1
    tg, tv = sum(p.gross for p in rows), sum(p.vat for p in rows)

    wb = Workbook()
    wb.remove(wb.active)
    s = _sheet(wb, "Summary", ["Month", "Rows", "Gross £", "VAT reclaimable £", "Net £"],
               [[f"{date(y, m, 1):%B %Y}", n, round(g, 2), round(v, 2), round(g - v, 2)]
                for (y, m), (g, v, n) in sorted(months.items())]
               + [["TOTAL", len(rows), round(tg, 2), round(tv, 2), round(tg - tv, 2)]],
               [18, 8, 14, 18, 14])
    for c in s[s.max_row]:
        c.font = Font(bold=True)
    s.append([])
    s.append([f"Fonenova Ltd (VAT XI516452304), VAT return {start:%d %b %Y} to {end:%d %b %Y}, due {due:%d %b %Y}."])
    s.append([f"Built {datetime.now():%d %b %Y %H:%M} from V18 and the Sept-Dec tracker. Expense side only; "
              "sales, margin scheme and Mobile One reverse-charge purchases are not in this pack."])
    for n in notes:
        s.append([n])

    _sheet(wb, "VAT reclaim list", ["Date", "Vendor", "Description", "Gross £", "VAT £", "Evidence",
                                    "Evidence status", "Source"],
           [[p.date, p.vendor, p.desc, p.gross, p.vat, p.evidence, p.evidence_status, f"{p.source} r{p.row}"]
            for p in rows if p.vat_flag == "VAT-Yes"],
           [11, 26, 34, 10, 9, 50, 18, 12])
    _sheet(wb, "Exceptions", ["Row", "Issue", "Detail"], [list(e) for e in exc], [55, 34, 60])
    _sheet(wb, "Receipt completeness", ["Date", "Vendor", "Gross £", "VAT flag", "Evidence status",
                                        "Evidence", "Source"],
           [[p.date, p.vendor, p.gross, p.vat_flag, p.evidence_status, p.evidence, f"{p.source} r{p.row}"]
            for p in rows],
           [11, 26, 10, 9, 18, 60, 12])
    _sheet(wb, "All expenses", ["Date", "Vendor", "Description", "Gross £", "VAT flag", "VAT £", "Remarks",
                                "Source"],
           [[p.date, p.vendor, p.desc, p.gross, p.vat_flag, p.vat, p.remarks, f"{p.source} r{p.row}"]
            for p in rows],
           [11, 26, 34, 10, 9, 9, 80, 12])
    for ws in wb.worksheets:
        for row in ws.iter_rows(min_row=2):
            for c in row:
                if isinstance(c.value, date):
                    c.number_format = "DD.MM.YY"
                elif isinstance(c.value, float):
                    c.number_format = "#,##0.00"

    xlsx = out_dir / f"VAT-Return-Pack-May-Oct-2026_{stamp}.xlsx"
    wb.save(xlsx)

    status = {}
    for p in rows:
        status[p.evidence_status] = status.get(p.evidence_status, 0) + 1
    md = [f"# VAT return pack, May to Oct 2026 (built {stamp})", "",
          f"Due **{due:%d %B %Y}** ({(due - date.today()).days} days).", "",
          "| Month | Rows | Gross | VAT | Net |", "|---|---|---|---|---|"]
    md += [f"| {date(y, m, 1):%b %Y} | {n} | {g:,.2f} | {v:,.2f} | {g - v:,.2f} |"
           for (y, m), (g, v, n) in sorted(months.items())]
    md += [f"| **Total** | {len(rows)} | **{tg:,.2f}** | **{tv:,.2f}** | **{tg - tv:,.2f}** |", "",
           "Evidence: " + ", ".join(f"{k} {v}" for k, v in sorted(status.items())), "",
           f"Exceptions: {len(exc)} (see the Exceptions sheet).", ""]
    md += [f"- {n}" for n in notes]
    mdp = out_dir / f"VAT-Return-Pack-May-Oct-2026_{stamp}.md"
    mdp.write_text("\n".join(md) + "\n", encoding="utf-8")
    return xlsx, mdp
