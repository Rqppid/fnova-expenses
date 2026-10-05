"""Rename and move a receipt into its vendor folder: <Vendor>-DD.MM.YY[-Descriptor].ext"""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from .backup import sha256
from .sheet import parse_ddmmyy


class FilingError(Exception):
    pass


@dataclass
class FileResult:
    status: str          # "moved" | "duplicate"
    src: Path
    dest: Path
    note: str = ""


def _clean(part: str) -> str:
    part = re.sub(r'[<>:"/\\|?*]+', "", part).strip()
    return re.sub(r"\s+", "-", part)


def receipt_name(vendor: str, date_text: str, ext: str, descriptor: str | None = None) -> str:
    if parse_ddmmyy(date_text) is None:
        raise FilingError(f"Date must be DD.MM.YY, got {date_text!r}")
    ext = ext if ext.startswith(".") else "." + ext
    v = _clean(vendor)
    if not v:
        raise FilingError("Vendor is empty")
    mid = f"-{_clean(descriptor)}" if descriptor else ""
    return f"{v}{mid}-{date_text}{ext.lower()}"


def resolve_folder(receipts_root: Path, vendor: str) -> str:
    """Existing vendor folder whose name shares the most tokens with the vendor, else a new name."""
    from .receipts import tokens
    want = tokens(vendor)
    best, score = None, 0
    if receipts_root.is_dir():
        for d in receipts_root.iterdir():
            if d.is_dir():
                s = len(want & tokens(d.name))
                if s > score:
                    best, score = d.name, s
    return best or _clean(vendor)


def file_receipt(src: Path, receipts_root: Path, *, vendor: str, date: str,
                 folder: str | None = None, descriptor: str | None = None) -> FileResult:
    """Move src to receipts_root/<folder or vendor>/<Vendor>[-Descriptor]-DD.MM.YY.ext.

    Never overwrites and never deletes. If an identical file (same hash) already sits at
    the target, or anywhere in the target folder, the source is left in place and reported
    as a duplicate so a person can decide whether to delete it.
    """
    src = Path(src)
    if not src.is_file():
        raise FilingError(f"Source not found: {src}")
    folder_path = receipts_root / (folder or resolve_folder(receipts_root, vendor))
    dest = folder_path / receipt_name(vendor, date, src.suffix, descriptor)
    src_hash = sha256(src)

    if folder_path.is_dir():
        for existing in folder_path.iterdir():
            if (existing.is_file() and existing.resolve() != src.resolve()
                    and existing.stat().st_size == src.stat().st_size and sha256(existing) == src_hash):
                return FileResult("duplicate", src, existing, f"identical to {existing.name}; source left in place")
    if dest.exists():
        raise FilingError(f"{dest.name} already exists with different content; pass a descriptor")
    if src.resolve() == dest.resolve():
        return FileResult("moved", src, dest, "already correctly named")

    folder_path.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(src, dest)          # same volume: atomic rename
    except OSError:
        shutil.move(str(src), str(dest))
    if src.exists() or not dest.exists() or sha256(dest) != src_hash:
        raise FilingError(f"Move of {src} to {dest} did not complete cleanly")
    return FileResult("moved", src, dest)
