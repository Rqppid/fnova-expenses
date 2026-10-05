"""Post-write verification: re-open the saved file from disk and assert its structure."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .sheet import Snapshot, read_snapshot, sumifs_end_rows
from .layout import Layout


@dataclass
class VerifyResult:
    ok: bool
    problems: list[str] = field(default_factory=list)
    snapshot: Snapshot | None = None

    def raise_if_failed(self):
        if not self.ok:
            raise AssertionError("verify failed:\n  " + "\n  ".join(self.problems))


def structural_problems(snap: Snapshot) -> list[str]:
    """Checks that hold for any healthy tracker, independent of expected totals."""
    lay, t, last = snap.layout, snap.total_row, snap.last_row
    p: list[str] = []
    want = lay.total_formulas(t, last)
    for col, f in want["total"].items():
        if snap.total_formulas.get(col) != f:
            p.append(f"Total row {t} {col}: {snap.total_formulas.get(col)!r}, expected {f!r}")
    for col, f in want["net"].items():
        if snap.net_formulas.get(col) != f:
            p.append(f"Net Total row {t + 1} {col}: {snap.net_formulas.get(col)!r}, expected {f!r}")
    if len(snap.sumifs) != lay.sumifs_count:
        p.append(f"Summary sheet has {len(snap.sumifs)} SUMIFS, expected {lay.sumifs_count}")
    for coord, f in sorted(snap.sumifs.items()):
        ends = sumifs_end_rows(f)
        if ends != {last}:
            p.append(f"{lay.summary_sheet}!{coord} SUMIFS ranges end at {sorted(ends)}, expected {last}")
    for row in snap.rows:
        for col, f in lay.helper_formulas(row.r).items():
            if row.helpers.get(col) != f:
                p.append(f"row {row.r} helper {col} missing or wrong")
        if not row.amount_is_numeric:
            p.append(f"row {row.r} amount not numeric: {row.amount_raw!r}")
    return p


def verify(path: Path, layout: Layout, *, expected_last_row: int | None = None,
           expected_gross: float | None = None, expected_vat: float | None = None,
           preexisting: set[str] | frozenset = frozenset()) -> VerifyResult:
    """preexisting: structural problems already present before a write (e.g. a half-finished
    row typed by hand elsewhere). They are not blamed on the write; audit reports them."""
    snap = read_snapshot(path, layout)
    p = [x for x in structural_problems(snap) if x not in preexisting]
    if expected_last_row is not None and snap.last_row != expected_last_row:
        p.append(f"last data row {snap.last_row}, expected {expected_last_row}")
    if expected_gross is not None and abs(snap.gross - expected_gross) > 0.005:
        p.append(f"gross {snap.gross:.2f}, expected {expected_gross:.2f}")
    if expected_vat is not None and abs(snap.vat - expected_vat) > 0.005:
        p.append(f"VAT {snap.vat:.2f}, expected {expected_vat:.2f}")
    return VerifyResult(ok=not p, problems=p, snapshot=snap)
