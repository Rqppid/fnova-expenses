"""Find receipt candidates: loose files at both receipts roots and anything in the Receipts Inbox.

A candidate whose bytes match an already-filed receipt (either tracker) is a duplicate,
not a new expense. Size is checked first, then the SHA-1 fingerprint.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .hashing import content_hash
from .layout import Layout
from .receipts import build_index

SKIP_NAMES = {"manifest.jsonl", "desktop.ini", "thumbs.db"}


@dataclass
class Candidate:
    path: Path
    size: int
    sha: str
    source: str               # "septdec-root" | "v18-root" | "inbox"
    duplicate_of: str | None  # receipts-relative path of an identical filed file


INBOX_NAME = "Receipts Inbox"


def inbox_dir(root: Path) -> Path:
    """Where Hamza scans receipts to (OneDrive app > Scan) and where Gmail downloads land."""
    return root / INBOX_NAME


def scan(layouts: dict[str, Layout], root: Path) -> list[Candidate]:
    filed: dict[int, list] = {}
    loose: list[tuple[Path, str]] = []
    for key, lay in layouts.items():
        idx = build_index(lay.receipts, lay.ignore_dirs)
        for f in idx.files:
            if f.at_root:
                if f.junk is None and f.path.suffix.lower() not in (".xlsx", ".zip"):
                    loose.append((f.path, f"{key}-root"))
            elif f.junk is None:
                filed.setdefault(f.size, []).append((key, f))
    ib = inbox_dir(root)
    if ib.exists():
        for p in sorted(ib.rglob("*")):
            if p.is_file() and p.name.lower() not in SKIP_NAMES and "processed" not in p.parts:
                loose.append((p, "inbox"))

    out = []
    for path, source in loose:
        size = path.stat().st_size
        if size == 0:
            continue
        sha = content_hash(path)
        dup = None
        for key, f in filed.get(size, []):
            if f.sha == sha:
                dup = f"{key}:{f.rel}"
                break
        out.append(Candidate(path, size, sha, source, dup))
    return out
