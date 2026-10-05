"""Timestamped backups and file-safety helpers."""
from __future__ import annotations

import hashlib
import shutil
from datetime import datetime
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def excel_lock_file(path: Path) -> Path | None:
    """Excel writes '~$<name>' next to a workbook it has open."""
    lock = path.with_name("~$" + path.name)
    return lock if lock.exists() else None


def backup(paths: list[Path], dest_root: Path, label: str = "") -> Path:
    """Copy files into dest_root/<timestamp>[_label]/ and confirm each copy's hash."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base = stamp + (f"_{label}" if label else "")
    dest, n = dest_root / base, 1
    while dest.exists():
        n += 1
        dest = dest_root / f"{base}-{n}"
    dest.mkdir(parents=True)
    for p in paths:
        out = dest / p.name
        shutil.copy2(p, out)
        if sha256(out) != sha256(p):
            raise IOError(f"Backup hash mismatch for {p}")
    return dest
