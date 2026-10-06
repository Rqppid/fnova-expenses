"""Write operations on a tracker: add, delete and complete rows.

Every public operation runs as a transaction: refuse if Excel has the file open,
back up, edit, save atomically, re-open from disk and verify, and restore the backup
if verification fails.

Rows are never inserted with ``ws.insert_rows``: openpyxl does not shift formulas,
data validations or merged ranges when it does that. Instead the Total and Net Total
rows are moved by rewriting them, and helper formulas are regenerated per row.
"""
from __future__ import annotations

import os
import shutil
from copy import copy
from dataclasses import dataclass
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from .backup import backup, excel_lock_file, sha256
from .layout import (COL_AMOUNT, COL_DATE, COL_DESC, COL_RECEIPT, COL_REF, COL_REMARKS,
                     COL_VAT, COL_VATFLAG, COL_VENDOR, NET_LABEL, TOTAL_LABEL, Layout)
from .sheet import (SUMIFS_RANGE_RE, TrackerError, find_total_row, parse_amount,
                    parse_ddmmyy, read_snapshot_ws)
from .verify import structural_problems, verify

VAT_FLAGS = ("VAT-Yes", "VAT-No")


@dataclass
class WriteResult:
    path: Path
    backup_dir: Path
    last_row: int
    gross: float
    vat: float
    net: float
    sha_before: str
    sha_after: str
    note: str = ""


# -- low-level row helpers -----------------------------------------------------

def _max_col(ws: Worksheet) -> int:
    return max(ws.max_column, 26)


def _row_snapshot(ws: Worksheet, r: int) -> dict:
    return {
        "height": ws.row_dimensions[r].height,
        "cells": {c: (copy(ws.cell(r, c)._style), ws.cell(r, c).value)
                  for c in range(1, _max_col(ws) + 1)},
    }


def _apply_row(ws: Worksheet, r: int, snap: dict, with_values: bool) -> None:
    ws.row_dimensions[r].height = snap["height"]
    for c, (style, value) in snap["cells"].items():
        cell = ws.cell(r, c)
        cell._style = copy(style)
        cell.value = value if with_values else None


def _row_values(ws: Worksheet, r: int) -> dict[str, object]:
    return {get_column_letter(c): ws.cell(r, c).value for c in range(1, _max_col(ws) + 1)
            if ws.cell(r, c).value is not None}


def _write_totals(ws: Worksheet, layout: Layout, total_row: int, last: int) -> None:
    f = layout.total_formulas(total_row, last)
    ws[f"{COL_DATE}{total_row}"] = TOTAL_LABEL
    for col, formula in f["total"].items():
        ws[f"{col}{total_row}"] = formula
    ws[f"{COL_DATE}{total_row + 1}"] = NET_LABEL
    for col, formula in f["net"].items():
        ws[f"{col}{total_row + 1}"] = formula


def _check_total_rows_plain(ws: Worksheet, layout: Layout, t: int) -> None:
    """Total/Net rows may only hold the label and the known formula cells."""
    allowed = {COL_DATE, COL_AMOUNT} | ({COL_VAT} if layout.total_has_q else set())
    for r in (t, t + 1):
        extra = set(_row_values(ws, r)) - allowed
        if extra:
            raise TrackerError(f"Row {r} (totals) has unexpected cells {sorted(extra)}; fix by hand first")


def _write_helpers(ws: Worksheet, layout: Layout, r: int) -> None:
    for col, f in layout.helper_formulas(r).items():
        ws[f"{col}{r}"] = f


def _rewrite_sumifs(wb, layout: Layout, last: int) -> int:
    s1 = wb[layout.summary_sheet]
    n = 0
    for row in s1.iter_rows():
        for c in row:
            if isinstance(c.value, str) and "SUMIFS(" in c.value:
                c.value = SUMIFS_RANGE_RE.sub(lambda m: f"{m.group(1)}{last}", c.value)
                n += 1
    if n != layout.sumifs_count:
        raise TrackerError(f"Rewrote {n} SUMIFS on {layout.summary_sheet}, expected {layout.sumifs_count}")
    return n


def _extend_validations(ws: Worksheet, last: int) -> None:
    """Extend any data validation that covers the log column down to the new last row."""
    for dv in ws.data_validations.dataValidation:
        new = []
        for rng in dv.sqref.ranges:
            if rng.min_row <= 5 <= rng.max_row and rng.max_row < last:
                new.append(f"{get_column_letter(rng.min_col)}{rng.min_row}:"
                           f"{get_column_letter(rng.max_col)}{last}")
            else:
                new.append(rng.coord)
        dv.sqref = openpyxl.worksheet.cell_range.MultiCellRange(" ".join(new))


def _validate_fields(date_text: str, amount, vat_flag: str, vat_amount) -> None:
    if parse_ddmmyy(date_text) is None:
        raise TrackerError(f"Date must be DD.MM.YY, got {date_text!r}")
    if not isinstance(amount, (int, float)):
        raise TrackerError(f"Amount must be numeric, got {amount!r}")
    if vat_flag not in VAT_FLAGS:
        raise TrackerError(f"VAT flag must be one of {VAT_FLAGS}, got {vat_flag!r}")
    if vat_flag == "VAT-Yes" and not isinstance(vat_amount, (int, float)):
        raise TrackerError("VAT-Yes needs a numeric VAT amount")
    if vat_flag == "VAT-No" and vat_amount not in (None, 0, 0.0):
        raise TrackerError("VAT-No must not carry a VAT amount")


# -- transaction -----------------------------------------------------------------

def _transaction(layout: Layout, backup_root: Path, label: str, edit, *,
                 expect_last_delta: int, expect_gross_delta: float, expect_vat_delta: float,
                 path: Path | None = None) -> WriteResult:
    path = Path(path or layout.path)
    if not layout.writable:
        raise TrackerError(f"{layout.key} tracker is read-only (flag new items, do not auto-add)")
    lock = excel_lock_file(path)
    if lock:
        raise TrackerError(f"Excel has the file open ({lock.name}). Close Excel and retry.")

    wb = openpyxl.load_workbook(path)
    before = read_snapshot_ws(wb, layout)
    sha_before = sha256(path)
    # Problems on rows the edit doesn't touch stay as they were; row numbers can shift on
    # add/delete, so only row-independent checks are compared after a structural change.
    preexisting = set(structural_problems(before)) if expect_last_delta == 0 else {
        x for x in structural_problems(before) if x.startswith("row ")}
    bdir = backup([path], backup_root, label)

    note = edit(wb, before)

    tmp = path.with_name(path.stem + ".~tmp.xlsx")
    wb.save(tmp)
    os.replace(tmp, path)

    res = verify(path, layout,
                 expected_last_row=before.last_row + expect_last_delta,
                 expected_gross=round(before.gross + expect_gross_delta, 2),
                 expected_vat=round(before.vat + expect_vat_delta, 2),
                 preexisting=preexisting)
    sha_after = sha256(path)
    if sha_after == sha_before:
        res.ok = False
        res.problems.append("file hash unchanged after save (write did not persist)")
    if not res.ok:
        shutil.copy2(bdir / path.name, path)
        raise TrackerError("Write failed verification, original restored from "
                           f"{bdir}:\n  " + "\n  ".join(res.problems))
    s = res.snapshot
    return WriteResult(path, bdir, s.last_row, s.gross, s.vat, s.net, sha_before, sha_after, note or "")


# -- public operations ---------------------------------------------------------------

def _insert_row(wb, layout: Layout, r: dict) -> int:
    """Write one expense row where the Total row is and move Total/Net Total down. Returns row."""
    ws = wb[layout.log_sheet]
    t = find_total_row(ws, layout)
    _check_total_rows_plain(ws, layout, t)
    if _row_values(ws, t + 2):
        raise TrackerError(f"Row {t + 2} below Net Total is not empty; check for hand-typed rows")
    data_snap = _row_snapshot(ws, t - 1)
    total_snap = _row_snapshot(ws, t)
    net_snap = _row_snapshot(ws, t + 1)

    new = t
    _apply_row(ws, new, data_snap, with_values=False)
    _apply_row(ws, new + 1, total_snap, with_values=False)
    _apply_row(ws, new + 2, net_snap, with_values=False)
    values = {COL_DATE: r["date"], COL_VENDOR: r["vendor"], COL_DESC: r["desc"],
              COL_AMOUNT: float(r["amount"]), COL_REF: r["ref"],
              COL_RECEIPT: r.get("receipt", "Receipt:Yes"), COL_VATFLAG: r["vat_flag"],
              COL_VAT: float(r["vat_amount"]) if r["vat_flag"] == "VAT-Yes" else None,
              COL_REMARKS: r["remarks"]}
    for col, v in values.items():
        ws[f"{col}{new}"] = v
    _write_helpers(ws, layout, new)
    _write_totals(ws, layout, new + 1, new)
    _rewrite_sumifs(wb, layout, new)
    _extend_validations(ws, new)
    return new


def _check_new(r: dict) -> None:
    _validate_fields(r["date"], r["amount"], r["vat_flag"], r.get("vat_amount"))
    if not str(r.get("remarks", "")).strip():
        raise TrackerError("Remarks are required")


def add_row(layout: Layout, backup_root: Path, *, date: str, vendor: str, desc: str,
            amount: float, ref: str, vat_flag: str, vat_amount: float | None, remarks: str,
            path: Path | None = None) -> WriteResult:
    """Append an expense row directly above the Total row."""
    row = dict(date=date, vendor=vendor, desc=desc, amount=amount, ref=ref, vat_flag=vat_flag,
               vat_amount=vat_amount, remarks=remarks)
    _check_new(row)

    def edit(wb, before):
        new = _insert_row(wb, layout, row)
        return f"added row {new}: {date} {vendor} £{amount:.2f} {vat_flag}"

    return _transaction(layout, backup_root, "add", edit, expect_last_delta=1,
                        expect_gross_delta=float(amount),
                        expect_vat_delta=float(vat_amount) if vat_flag == "VAT-Yes" else 0.0,
                        path=path)


def add_rows(layout: Layout, backup_root: Path, rows: list[dict], *, fx: list[dict] = (),
             label: str = "add-batch", path: Path | None = None) -> WriteResult:
    """Append several expense rows (and optional FX-sheet entries) in ONE backed-up, verified write.

    rows: dicts with date, vendor, desc, amount, ref, vat_flag, vat_amount, remarks[, receipt].
    fx:   dicts with date, eur, gbp, rate, fee, note (see append_fx).
    """
    for r in rows:
        _check_new(r)
    if not rows and not fx:
        raise TrackerError("Nothing to add")

    def edit(wb, before):
        added = [_insert_row(wb, layout, r) for r in rows]
        for f in fx:
            append_fx(wb, **f)
        return f"added rows {added}" + (f" and {len(fx)} FX entr{'y' if len(fx) == 1 else 'ies'}" if fx else "")

    return _transaction(layout, backup_root, label, edit, expect_last_delta=len(rows),
                        expect_gross_delta=round(sum(float(r["amount"]) for r in rows), 2),
                        expect_vat_delta=round(sum(float(r["vat_amount"]) for r in rows
                                                   if r["vat_flag"] == "VAT-Yes"), 2),
                        path=path)


FX_SHEET = "FX Exchanges (Reference)"
FX_PLACEHOLDER = "No FX exchanges recorded yet"


def fx_entries(wb) -> set[tuple[str, float]]:
    """{(DD.MM.YY, EUR amount)} already on the FX reference sheet."""
    ws = wb[FX_SHEET]
    out = set()
    for r in range(1, ws.max_row + 1):
        d, e = ws.cell(r, 1).value, ws.cell(r, 2).value
        if isinstance(d, str) and parse_ddmmyy(d) and isinstance(e, (int, float)):
            out.add((d, round(float(e), 2)))
    return out


def append_fx(wb, *, date: str, eur: float, gbp: float, rate: float | None, fee: float | None,
              note: str) -> int:
    """Record an EUR->GBP conversion on the reference sheet (never part of the VAT totals)."""
    if parse_ddmmyy(date) is None:
        raise TrackerError(f"FX date must be DD.MM.YY, got {date!r}")
    ws = wb[FX_SHEET]
    header = next((c.row for c in ws["A"] if c.value == "Date"
                   and ws.cell(c.row, 2).value == "EUR Converted"), None)
    if header is None:
        raise TrackerError(f"Header row not found on {FX_SHEET}")
    r = header + 1
    while ws.cell(r, 1).value not in (None, "") and FX_PLACEHOLDER not in str(ws.cell(r, 1).value):
        if ws.cell(r, 1).value == date and abs((ws.cell(r, 2).value or 0) - eur) < 0.005:
            raise TrackerError(f"FX entry {date} EUR {eur:.2f} already recorded (row {r})")
        r += 1
    for col, v in enumerate([date, round(eur, 2), round(gbp, 2), rate, fee, note], start=1):
        ws.cell(r, col).value = v
    return r


def delete_row(layout: Layout, backup_root: Path, *, row: int, expect_date: str,
               expect_amount: float, expect_vendor: str, path: Path | None = None) -> WriteResult:
    """Remove a data row and close the gap. The expect_* guards must match the row."""
    def edit(wb, before):
        ws = wb[layout.log_sheet]
        t = find_total_row(ws, layout)
        _check_total_rows_plain(ws, layout, t)
        if not (layout.first_row <= row < t):
            raise TrackerError(f"Row {row} is not a data row (data is {layout.first_row}..{t - 1})")
        target = next(r for r in before.rows if r.r == row)
        if (target.date_text != expect_date or target.amount is None
                or abs(target.amount - expect_amount) > 0.005
                or expect_vendor.lower() not in target.vendor.lower()):
            raise TrackerError(f"Row {row} is {target.date_text} {target.vendor!r} {target.amount_raw!r}, "
                               f"not {expect_date} {expect_vendor!r} {expect_amount}")

        total_snap, net_snap = _row_snapshot(ws, t), _row_snapshot(ws, t + 1)
        blank_snap = _row_snapshot(ws, t + 2)
        if any(v for _, v in blank_snap["cells"].values()):
            raise TrackerError(f"Row {t + 2} below Net Total is not empty")
        for r in range(row, t - 1):
            _apply_row(ws, r, _row_snapshot(ws, r + 1), with_values=True)
            _write_helpers(ws, layout, r)
        last = t - 2
        _apply_row(ws, t - 1, total_snap, with_values=False)
        _apply_row(ws, t, net_snap, with_values=False)
        _apply_row(ws, t + 1, blank_snap, with_values=False)
        _write_totals(ws, layout, t - 1, last)
        _rewrite_sumifs(wb, layout, last)
        return f"deleted row {row}: {target.date_text} {target.vendor} £{target.amount:.2f}"

    # Deltas depend on the row, so read them first.
    wb = openpyxl.load_workbook(Path(path or layout.path))
    snap = read_snapshot_ws(wb, layout)
    tgt = next((r for r in snap.rows if r.r == row), None)
    if tgt is None or not tgt.amount_is_numeric:
        raise TrackerError(f"Row {row} not found or has no numeric amount")
    vat_num = tgt.vat_raw if isinstance(tgt.vat_raw, (int, float)) else 0.0
    return _transaction(layout, backup_root, "delete", edit, expect_last_delta=-1,
                        expect_gross_delta=-tgt.amount, expect_vat_delta=-vat_num,
                        path=path)


EDITABLE = {"date": COL_DATE, "vendor": COL_VENDOR, "desc": COL_DESC, "amount": COL_AMOUNT,
            "ref": COL_REF, "vat_flag": COL_VATFLAG, "vat_amount": COL_VAT, "remarks": COL_REMARKS}


def complete_row(layout: Layout, backup_root: Path, *, row: int, path: Path | None = None,
                 **fields) -> WriteResult:
    """Fix a half-finished row in place: coerce a text amount, rewrite helpers, set fields.

    Fields not passed are kept. A text amount like '£12.50' is converted to 12.5.
    """
    unknown = set(fields) - set(EDITABLE)
    if unknown:
        raise TrackerError(f"Unknown fields {sorted(unknown)}")
    wb = openpyxl.load_workbook(Path(path or layout.path))
    snap = read_snapshot_ws(wb, layout)
    cur = next((r for r in snap.rows if r.r == row), None)
    if cur is None:
        raise TrackerError(f"Row {row} is not a data row")

    new_amount = fields.get("amount", cur.amount)
    if new_amount is None:
        raise TrackerError(f"Row {row} amount {cur.amount_raw!r} is unreadable; pass amount=")
    new_flag = fields.get("vat_flag", cur.vat_flag)
    new_vat = fields.get("vat_amount", cur.vat if new_flag == "VAT-Yes" else None)
    new_date = fields.get("date", cur.date_text)
    _validate_fields(new_date, float(new_amount), new_flag, new_vat)
    remarks = fields.get("remarks", cur.remarks)
    if not str(remarks or "").strip():
        raise TrackerError(f"Row {row} has no Remarks; pass remarks=")

    def edit(wb, before):
        ws = wb[layout.log_sheet]
        vals = {COL_DATE: new_date, COL_AMOUNT: float(new_amount), COL_VATFLAG: new_flag,
                COL_VAT: float(new_vat) if new_flag == "VAT-Yes" else None, COL_REMARKS: remarks,
                COL_RECEIPT: cur.receipt or "Receipt:Yes"}
        for k in ("vendor", "desc", "ref"):
            if k in fields:
                vals[EDITABLE[k]] = fields[k]
        for col, v in vals.items():
            ws[f"{col}{row}"] = v
        _write_helpers(ws, layout, row)
        return f"completed row {row}"

    # A text amount is not counted in before.gross, so the delta is the full new amount.
    gross_delta = float(new_amount) - (cur.amount if cur.amount_is_numeric else 0.0)
    cur_vat = cur.vat_raw if isinstance(cur.vat_raw, (int, float)) else 0.0
    vat_delta = (float(new_vat) if new_flag == "VAT-Yes" else 0.0) - cur_vat
    return _transaction(layout, backup_root, "complete", edit, expect_last_delta=0,
                        expect_gross_delta=gross_delta, expect_vat_delta=vat_delta, path=path)


def update_remarks(layout: Layout, backup_root: Path, changes: dict[int, str], *,
                   expect_vendors: dict[int, str] | None = None, path: Path | None = None) -> WriteResult:
    """Rewrite the Remarks of several rows in one transaction. Amounts and VAT are untouched.

    expect_vendors guards against row numbers having shifted since the changes were prepared.
    """
    def edit(wb, before):
        ws = wb[layout.log_sheet]
        rows = {r.r: r for r in before.rows}
        for r, text in changes.items():
            if r not in rows:
                raise TrackerError(f"Row {r} is not a data row")
            if expect_vendors and expect_vendors.get(r, "").lower() != rows[r].vendor.lower():
                raise TrackerError(f"Row {r} is {rows[r].vendor!r}, expected {expect_vendors.get(r)!r}")
            if not text.strip():
                raise TrackerError(f"Empty Remarks for row {r}")
            ws[f"{COL_REMARKS}{r}"] = text
        return f"updated Remarks on rows {sorted(changes)}"

    return _transaction(layout, backup_root, "remarks", edit, expect_last_delta=0,
                        expect_gross_delta=0.0, expect_vat_delta=0.0, path=path)
