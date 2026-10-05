"""Command line: python -m fonenova.cli <command> ...

Commands
  audit    [--out FILE] [--matches]         reconciliation report (read-only)
  status                                    last row and totals per tracker (read-only)
  add      --date DD.MM.YY --vendor V --desc D --amount N --ref R --vat Yes|No
           [--vat-amount N] --remarks TEXT  append a row above Total
  delete   --row N --expect-date D --expect-vendor V --expect-amount N
  complete --row N [--amount N] [--vat Yes|No] [--vat-amount N] [--remarks TEXT] ...
  file     --src PATH --vendor V --date DD.MM.YY [--folder F] [--descriptor X] [--tracker septdec]
  verify   [--tracker septdec]
  backup
  diff     BEFORE AFTER
  pack     [--out DIR]                      VAT return pack for the accountant (read-only)
  find     [--date DD.MM.YY] [--amount N] [--ref TEXT] [--days 3]   search both trackers
  archive  --path FILE                      move a Receipts Inbox file to Receipts Inbox/processed/<date>/
  gmail-auth                                one-time browser sign-in for the Gmail API
  daily    [--no-claude]                    run the unattended daily routine
Write commands accept --path to operate on a copy instead of the live file.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .layout import backup_root, layouts, load_config


def _vat_flag(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip().lower()
    return {"yes": "VAT-Yes", "vat-yes": "VAT-Yes", "no": "VAT-No", "vat-no": "VAT-No"}[v]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="fonenova")
    ap.add_argument("--mirror", help="cloud mode: operate on this OneDrive mirror (from `cloud prep`) "
                                     "instead of the local VAT RETURNS folder")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit"); a.add_argument("--out"); a.add_argument("--matches", action="store_true")
    sub.add_parser("status")

    for name in ("add", "delete", "complete", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--tracker", default="septdec")
        p.add_argument("--path", help="operate on this file instead of the live tracker")
        p.add_argument("--backup-dir", help="override backup folder")
        if name == "add":
            for f in ("date", "vendor", "desc", "ref", "remarks"):
                p.add_argument(f"--{f}", required=True)
            p.add_argument("--amount", type=float, required=True)
            p.add_argument("--vat", required=True)
            p.add_argument("--vat-amount", type=float)
        elif name == "delete":
            p.add_argument("--row", type=int, required=True)
            p.add_argument("--expect-date", required=True)
            p.add_argument("--expect-vendor", required=True)
            p.add_argument("--expect-amount", type=float, required=True)
        elif name == "complete":
            p.add_argument("--row", type=int, required=True)
            for f in ("date", "vendor", "desc", "ref", "remarks"):
                p.add_argument(f"--{f}")
            p.add_argument("--amount", type=float)
            p.add_argument("--vat")
            p.add_argument("--vat-amount", type=float)

    f = sub.add_parser("file")
    f.add_argument("--src", required=True); f.add_argument("--vendor", required=True)
    f.add_argument("--date", required=True); f.add_argument("--folder"); f.add_argument("--descriptor")
    f.add_argument("--tracker", default="septdec")

    sub.add_parser("backup")
    d = sub.add_parser("diff"); d.add_argument("before"); d.add_argument("after")
    fd = sub.add_parser("find"); fd.add_argument("--date"); fd.add_argument("--amount", type=float)
    fd.add_argument("--ref"); fd.add_argument("--days", type=int, default=3)
    ar = sub.add_parser("archive"); ar.add_argument("--path", required=True)
    sub.add_parser("gmail-auth")
    dl = sub.add_parser("daily"); dl.add_argument("--no-claude", action="store_true")
    pk = sub.add_parser("pack"); pk.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "out"))

    args = ap.parse_args(argv)
    cfg = load_config()
    if args.mirror:
        from .cloud import install_mirror_resolver
        cfg["root"] = str(Path(args.mirror))
        install_mirror_resolver(Path(args.mirror))
    lays = layouts(cfg)

    if args.cmd == "audit":
        from .audit import run_audit
        md, _ = run_audit(lays, detail_matches=args.matches)
        if args.out:
            Path(args.out).write_text(md, encoding="utf-8")
            print(f"written {args.out}")
        else:
            print(md)
        return 0

    if args.cmd == "status":
        from .sheet import read_snapshot
        for k, lay in lays.items():
            s = read_snapshot(lay.path, lay)
            print(f"{k}: rows {lay.first_row}-{s.last_row}, Total row {s.total_row}, "
                  f"gross {s.gross:,.2f} / VAT {s.vat:,.2f} / net {s.net:,.2f}")
        return 0

    if args.cmd == "backup":
        from .backup import backup
        print(backup([l.path for l in lays.values()], backup_root(cfg), "manual"))
        return 0

    if args.cmd == "diff":
        from .xlsx_diff import diff, render
        print(render(diff(Path(args.before), Path(args.after))))
        return 0

    if args.cmd == "find":
        from .sheet import parse_ddmmyy, read_snapshot
        want = parse_ddmmyy(args.date) if args.date else None
        hits = 0
        for k, lay in lays.items():
            for r in read_snapshot(lay.path, lay).rows:
                if want and (not r.date or abs((r.date - want).days) > args.days):
                    continue
                if args.amount is not None and (r.amount is None or abs(r.amount - args.amount) > 0.005):
                    continue
                if args.ref and args.ref.lower() not in (r.ref + " " + r.remarks).lower():
                    continue
                hits += 1
                print(f"{k} row {r.r}: {r.date_text} | {r.vendor} | {r.desc} | {r.amount_raw} | "
                      f"{r.vat_flag} {r.vat_raw or ''} | ref {r.ref} | {r.remarks[:120]}")
        print(f"{hits} match(es)")
        return 0

    if args.cmd == "archive":
        import os
        from datetime import date as _d
        from .intake import inbox_dir
        src = Path(args.path).resolve()
        ib = inbox_dir(Path(cfg["root"])).resolve()
        if ib not in src.parents:
            print(f"refused: {src} is not inside {ib}")
            return 2
        dest = ib / "processed" / f"{_d.today():%Y-%m-%d}" / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            print(f"refused: {dest} exists")
            return 2
        os.replace(src, dest)
        print(f"archived {src.name} -> {dest}")
        return 0

    if args.cmd == "gmail-auth":
        from .gmail import service
        from .layout import REPO
        service(REPO / "secrets", interactive=True)
        print("Gmail token saved to secrets/token.json")
        return 0

    if args.cmd == "daily":
        from .daily import run
        import json as _j
        print(_j.dumps(run(use_claude=not args.no_claude), indent=2, default=str))
        return 0

    if args.cmd == "pack":
        from .pack import build_pack
        x, m = build_pack(lays, Path(args.out))
        print(x)
        print(m.read_text(encoding="utf-8"))
        return 0

    if args.cmd == "file":
        from .filing import file_receipt
        r = file_receipt(Path(args.src), lays[args.tracker].receipts, vendor=args.vendor,
                         date=args.date, folder=args.folder, descriptor=args.descriptor)
        print(f"{r.status}: {r.src} -> {r.dest} {r.note}")
        return 0 if r.status == "moved" else 2

    lay = lays[args.tracker]
    path = Path(args.path) if args.path else None
    broot = Path(args.backup_dir) if args.backup_dir else backup_root(cfg)

    if args.cmd == "verify":
        from .verify import verify
        res = verify(path or lay.path, lay)
        s = res.snapshot
        print(f"rows to {s.last_row}, gross {s.gross:,.2f} / VAT {s.vat:,.2f} / net {s.net:,.2f}")
        print("OK" if res.ok else "PROBLEMS:\n  " + "\n  ".join(res.problems))
        return 0 if res.ok else 1

    from . import tracker
    if args.cmd == "add":
        res = tracker.add_row(lay, broot, date=args.date, vendor=args.vendor, desc=args.desc,
                              amount=args.amount, ref=args.ref, vat_flag=_vat_flag(args.vat),
                              vat_amount=args.vat_amount, remarks=args.remarks, path=path)
    elif args.cmd == "delete":
        res = tracker.delete_row(lay, broot, row=args.row, expect_date=args.expect_date,
                                 expect_vendor=args.expect_vendor, expect_amount=args.expect_amount,
                                 path=path)
    else:
        fields = {k: getattr(args, k) for k in ("date", "vendor", "desc", "ref", "remarks", "amount")
                  if getattr(args, k) is not None}
        if args.vat is not None:
            fields["vat_flag"] = _vat_flag(args.vat)
        if args.vat_amount is not None:
            fields["vat_amount"] = args.vat_amount
        res = tracker.complete_row(lay, broot, row=args.row, path=path, **fields)
    print(f"{res.note}\nverified: rows to {res.last_row}, gross {res.gross:,.2f} / VAT {res.vat:,.2f} / "
          f"net {res.net:,.2f}\nbackup: {res.backup_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
