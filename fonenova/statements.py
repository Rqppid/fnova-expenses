"""Revolut Business statements and FX confirmations -> tracker rows.

The bank statement is authoritative. Card payments and Revolut fees with no matching row in
either tracker are logged VAT-No with "RECEIPT MISSING"; EUR->GBP exchanges go to the FX
reference sheet and their fee becomes an expense row. Transfers, top-ups, refunds and wholesale
counterparties are never logged automatically: they are listed for Hamza.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from .layout import Layout
from .sheet import Snapshot

WHOLESALE = ("mobile one", "mobileone", "wavephone", "wave phone", "phone-zone", "phonezone",
             "phone zone", "tradewise", "eu telecoms")
LOGGABLE = {"CARD_PAYMENT", "FEE"}
MATCH_DAYS = 3


@dataclass
class Txn:
    date: date                 # completed date
    started: date | None
    id: str
    type: str                  # CARD_PAYMENT, TRANSFER, EXCHANGE, FEE, TOPUP, CARD_REFUND, ...
    state: str
    description: str
    reference: str
    currency: str              # payment currency
    amount: float              # signed total in payment currency (negative = money out)
    fee: float                 # positive fee in fee currency
    orig_currency: str = ""
    orig_amount: float = 0.0
    rate: float | None = None
    card: str = ""

    @property
    def short_id(self) -> str:
        return self.id.replace("-", "")[:10] if self.id else ""

    @property
    def ddmmyy(self) -> str:
        return self.date.strftime("%d.%m.%y")


def _f(v) -> float:
    try:
        return float(str(v).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def _d(v) -> date | None:
    v = (v or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            pass
    return None


def parse_csv(path: Path) -> list[Txn]:
    """Revolut Business 'Transactions' CSV export (Statements > Excel/CSV)."""
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or "Type" not in rows[0] or not any(k.startswith("Date completed") for k in rows[0]):
        raise ValueError(f"{Path(path).name} is not a Revolut Business transactions CSV")
    dc = next(k for k in rows[0] if k.startswith("Date completed"))
    ds = next((k for k in rows[0] if k.startswith("Date started")), dc)
    out = []
    for r in rows:
        when = _d(r.get(dc)) or _d(r.get(ds))
        if when is None:
            continue
        out.append(Txn(
            date=when, started=_d(r.get(ds)), id=r.get("ID", ""), type=r.get("Type", "").strip(),
            state=r.get("State", "").strip(), description=r.get("Description", "").strip(),
            reference=r.get("Reference", "").strip(), currency=r.get("Payment currency", "GBP").strip(),
            amount=_f(r.get("Total amount") or r.get("Amount")), fee=abs(_f(r.get("Fee"))),
            orig_currency=r.get("Orig currency", "").strip(), orig_amount=_f(r.get("Orig amount")),
            rate=_f(r.get("Exchange rate")) or None, card=r.get("Card number", "").strip()))
    return out


FX_PDF_RE = re.compile(
    r"Transaction of (\d{1,2} \w+ \d{4}).*?EUR\s*.?>\s*Main.*?GBP.*?([\d ]+\.\d\d).*?"
    r"FX Rate EUR 1 = GBP ([\d.]+), Fee: .?([\d ]+\.\d\d).*?([\d ]+\.\d\d)", re.S)


def parse_fx_confirmation(text: str) -> dict | None:
    """Revolut single-transaction statement for an EUR->GBP exchange (like the 19.09.26 PDF)."""
    m = FX_PDF_RE.search(text)
    if not m:
        return None
    when = None
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            when = datetime.strptime(m.group(1).replace("Sept", "Sep"), fmt).date()
            break
        except ValueError:
            pass
    if when is None:
        return None
    eur = _f(m.group(2).replace(" ", ""))
    gbp_rate = float(m.group(3))
    return {"date": when.strftime("%d.%m.%y"), "eur": eur, "gbp": _f(m.group(5).replace(" ", "")),
            "rate": round(1 / gbp_rate, 6) if gbp_rate else None, "fee": _f(m.group(4).replace(" ", ""))}


# -- reconcile -----------------------------------------------------------------------------

@dataclass
class Reconciliation:
    snaps: dict = field(default_factory=dict, repr=False)
    matched: list = field(default_factory=list)       # (txn, "tracker row N")
    to_log: list = field(default_factory=list)        # txn (card payments, fees)
    fx: list = field(default_factory=list)            # txn (exchanges)
    review: list = field(default_factory=list)        # (txn, reason)
    v18_period: list = field(default_factory=list)    # txn: unmatched but dated before the tracker


def _is_wholesale(t: Txn) -> bool:
    s = f"{t.description} {t.reference}".lower()
    return any(w in s for w in WHOLESALE)


def reconcile(txns: list[Txn], snaps: dict[str, Snapshot], live: Layout) -> Reconciliation:
    rec = Reconciliation(snaps=snaps)
    rows = [(k, r) for k, s in snaps.items() for r in s.rows if r.amount is not None]
    used: set[tuple[str, int]] = set()

    def find(t: Txn):
        amt = round(abs(t.amount), 2)
        if t.short_id:
            for k, r in rows:
                if t.short_id in f"{r.ref} {r.remarks}".replace("-", ""):
                    return k, r
        best = None
        for k, r in rows:
            if (k, r.r) in used or r.date is None or abs(round(r.amount, 2) - amt) > 0.005:
                continue
            days = min(abs((r.date - d).days) for d in (t.date, t.started) if d)
            if days <= MATCH_DAYS and (best is None or days < best[0]):
                best = (days, k, r)
        return (best[1], best[2]) if best else None

    for t in sorted(txns, key=lambda x: x.date):
        if t.state and t.state.upper() not in ("COMPLETED", ""):
            continue
        if t.type == "EXCHANGE":
            if t.date < live.period_start:
                rec.v18_period.append(t)
            else:
                rec.fx.append(t)
            continue
        if t.amount >= 0:
            if t.type == "CARD_REFUND":
                rec.review.append((t, "refund: check whether it reverses a logged expense"))
            continue                                  # money in: top-ups, sales receipts
        if t.currency != "GBP":
            rec.review.append((t, f"payment in {t.currency}: not logged automatically"))
            continue
        hit = find(t)
        if hit:
            used.add((hit[0], hit[1].r))
            rec.matched.append((t, f"{hit[0]} row {hit[1].r}"))
            continue
        if _is_wholesale(t):
            rec.review.append((t, "wholesale counterparty: not an expense for this tracker"))
        elif t.type not in LOGGABLE:
            rec.review.append((t, f"{t.type.lower()}: not logged automatically"))
        elif t.date < live.period_start:
            rec.v18_period.append(t)
        elif t.date > live.period_end:
            rec.review.append((t, "after the tracker period"))
        else:
            rec.to_log.append(t)
    return rec


def vendor_name(t: Txn) -> str:
    """'Asda Stores Ltd 4286' -> 'Asda Stores Ltd'; 'Revolut Business Fee' stays."""
    name = re.sub(r"\s+\d{3,}$", "", t.description).strip()
    name = re.sub(r"^(To|From)\s+", "", name)
    return name[:60] or "Unknown"


def fee_already_logged(rec: Reconciliation, t: Txn) -> str | None:
    for k, s in rec.snaps.items():
        for r in s.rows:
            if (r.amount is not None and r.date and abs(r.amount - t.fee) < 0.005
                    and abs((r.date - t.date).days) <= MATCH_DAYS):
                return f"{k} row {r.r}"
    return None


def rows_for(rec: Reconciliation, source_name: str, existing_fx: set = frozenset()
             ) -> tuple[list[dict], list[dict]]:
    """Tracker rows and FX entries to add. existing_fx: {(DD.MM.YY, eur)} already on the FX sheet."""
    rows, fx = [], []
    for t in rec.to_log:
        rows.append(dict(
            date=t.ddmmyy, vendor=vendor_name(t),
            desc="Revolut business fee" if t.type == "FEE" else "Card payment (from bank statement)",
            amount=round(abs(t.amount), 2), ref=f"Revolut txn {t.short_id}",
            vat_flag="VAT-No", vat_amount=None,
            remarks=(f"From Revolut statement {source_name}, txn {t.id}, {t.description}"
                     f"{', ' + t.reference if t.reference else ''}"
                     f"{', card ' + t.card[-4:] if t.card else ''}. "
                     + ("Revolut plan/service fee, VAT-No (financial services, exempt)."
                        if t.type == "FEE" else
                        "RECEIPT MISSING: logged from the bank statement (authoritative); no VAT "
                        "reclaimed until a receipt is filed."))))
    for t in rec.fx:
        eur = abs(t.orig_amount) if t.orig_currency == "EUR" else 0.0
        gbp = abs(t.amount)
        if (t.ddmmyy, round(eur, 2)) in existing_fx:
            continue
        fee_row = fee_already_logged(rec, t) if t.fee else None
        fx.append(dict(date=t.ddmmyy, eur=round(eur, 2), gbp=round(gbp, 2), rate=t.rate,
                       fee=round(t.fee, 2) or None,
                       note=f"Revolut exchange {t.description}, txn {t.id} ({source_name})"))
        if t.fee and not fee_row:
            rows.append(dict(
                date=t.ddmmyy, vendor="Revolut", desc="FX conversion fee (EUR to GBP)",
                amount=round(t.fee, 2), ref=f"Revolut txn {t.short_id}", vat_flag="VAT-No",
                vat_amount=None,
                remarks=(f"From Revolut statement {source_name}, txn {t.id}: EUR {eur:,.2f} converted "
                         f"to GBP {gbp:,.2f} (rate {t.rate}), fee £{t.fee:.2f}. Conversion recorded on "
                         "the FX Exchanges (Reference) sheet. VAT-No: financial services, exempt.")))
    return rows, fx


def describe(rec: Reconciliation) -> str:
    def line(t):
        return f"{t.ddmmyy} {t.description} £{abs(t.amount):,.2f} ({t.type.lower()})"
    out = [f"matched to existing rows: {len(rec.matched)}",
           f"to log (no receipt found): {len(rec.to_log)}"] + [f"  - {line(t)}" for t in rec.to_log]
    out += [f"FX exchanges: {len(rec.fx)}"] + [
        f"  - {t.ddmmyy} EUR {abs(t.orig_amount):,.2f} -> GBP {abs(t.amount):,.2f}, fee £{t.fee:.2f}" for t in rec.fx]
    out += [f"V18 period, not logged (flag only): {len(rec.v18_period)}"] + [f"  - {line(t)}" for t in rec.v18_period]
    out += [f"for Hamza to review: {len(rec.review)}"] + [f"  - {line(t)}: {why}" for t, why in rec.review]
    return "\n".join(out)
