"""Tracker layouts and config loading.

Each tracker workbook has an expense log sheet (Sheet2) with the same core columns,
but the helper columns and the Total rows differ between the Sept-Dec tracker and V18.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO / "config.toml"

# Core log columns, shared by both trackers.
COL_DATE, COL_VENDOR, COL_DESC, COL_AMOUNT = "D", "E", "G", "I"
COL_REF, COL_RECEIPT, COL_VATFLAG, COL_VAT, COL_REMARKS = "K", "N", "P", "Q", "R"
CORE_COLS = (COL_DATE, COL_VENDOR, COL_DESC, COL_AMOUNT, COL_REF, COL_RECEIPT,
             COL_VATFLAG, COL_VAT, COL_REMARKS)

TOTAL_LABEL = "Total :"
NET_LABEL = "Net Total (Gross - VAT):"


@dataclass(frozen=True)
class Layout:
    key: str
    path: Path                # workbook
    receipts: Path            # receipts root folder
    period_start: date
    period_end: date          # inclusive
    helpers: tuple[str, str, str]   # (date-parse, VAT auto-calc, VAT check)
    total_has_q: bool         # V18: Total row also sums Q and Net = I-Q
    sumifs_count: int         # number of SUMIFS formulas on the summary sheet
    writable: bool
    log_sheet: str = "Sheet2"
    summary_sheet: str = "Sheet1"
    first_row: int = 5
    ignore_dirs: tuple[str, ...] = ()   # receipt sub-folders treated as junk, not matched
    side_cols: str = ""       # columns holding a legitimate side ledger (V18 T..Z)
    pending: dict = field(default_factory=dict, hash=False, compare=False)

    # -- formula templates -------------------------------------------------
    def helper_formulas(self, r: int) -> dict[str, str]:
        u, v, w = self.helpers
        return {
            u: f"=IFERROR(DATE(2000+VALUE(RIGHT(D{r},2)),VALUE(MID(D{r},4,2)),VALUE(LEFT(D{r},2))),0)",
            v: f'=IF(P{r}="VAT-Yes",ROUND(I{r}/6,2),IF(P{r}="VAT-No",0,""))',
            w: (f'=IF(P{r}="VAT-Yes",IF(ABS(Q{r}-{v}{r})<0.02,"OK","Check VAT amount"),'
                f'IF(OR(P{r}="VAT-No",P{r}=""),"","Check VAT flag"))'),
        }

    def total_formulas(self, total_row: int, last: int) -> dict[str, dict[str, str]]:
        """Formulas for the Total row and the Net Total row (keyed by column)."""
        f = self.first_row
        total = {COL_AMOUNT: f"=SUM(I{f}:I{last})"}
        if self.total_has_q:
            total[COL_VAT] = f"=SUM(Q{f}:Q{last})"
            net = {COL_AMOUNT: f"=I{total_row}-Q{total_row}"}
        else:
            net = {COL_AMOUNT: f"=I{total_row}-SUM(Q{f}:Q{last})"}
        return {"total": total, "net": net}


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def layouts(cfg: dict | None = None, root: Path | None = None) -> dict[str, Layout]:
    cfg = cfg if cfg is not None else load_config()
    root = Path(root or cfg["root"])
    pending = cfg.get("pending", {})
    sd = root / "VAT Return-SEPT-DEC"
    v18 = root / "VAT Return-May-Sept-26"
    return {
        "septdec": Layout(
            key="septdec",
            path=sd / "VAT Return From Sept-Dec, 2026.xlsx",
            receipts=sd / "Receipts, Invoices-Sept-Dec,2026",
            period_start=date(2026, 9, 1), period_end=date(2026, 12, 31),
            helpers=("U", "V", "W"), total_has_q=False, sumifs_count=8, writable=True,
            pending=pending.get("septdec", {}),
        ),
        "v18": Layout(
            key="v18",
            path=v18 / "VATReturn_Automated_v18_delivered_1.xlsx",
            receipts=v18 / "Receipts-Invoice-VAT-Return-May-Sept, 26",
            period_start=date(2026, 5, 1), period_end=date(2026, 9, 30),
            helpers=("AB", "AC", "AD"), total_has_q=True, sumifs_count=10, writable=False,
            ignore_dirs=("a1",), side_cols="TUVWXYZ", pending=pending.get("v18", {}),
        ),
    }


def backup_root(cfg: dict | None = None) -> Path:
    cfg = cfg if cfg is not None else load_config()
    return Path(cfg["root"]) / cfg.get("backup_dir", "_backups")
