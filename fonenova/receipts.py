"""Receipt-folder index: dates from filenames, vendor tokens, hashes, junk detection."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from functools import cached_property
from pathlib import Path

from .hashing import content_hash

ISO_RE = re.compile(r"(?<!\d)(20\d\d)-(\d\d)-(\d\d)(?!\d)")
DMY_RE = re.compile(r"(?<!\d)(\d{1,2})[.\-](\d{1,2})[.\-](\d{4}|\d{2})(?!\d)")
TRANSCRIPT_EXT = {".txt", ".html", ".htm", ".url"}
STOP = {"ltd", "limited", "the", "and", "store", "stores", "express", "service", "services",
        "receipt", "receipts", "invoice", "shop", "shopping", "super", "uk", "int", "image",
        "scan", "from", "copy", "payment", "pdf", "jpeg", "jpg", "png", "various"}


def date_from_name(name: str) -> date | None:
    for rx, order in ((ISO_RE, "ymd"), (DMY_RE, "dmy")):
        for m in rx.finditer(name):
            a, b, c = m.groups()
            try:
                if order == "ymd":
                    return date(int(a), int(b), int(c))
                y = int(c) if len(c) == 4 else 2000 + int(c)
                return date(y, int(b), int(a))
            except ValueError:
                continue
    return None


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", text.lower().replace("'", ""))
    return {w for w in words if len(w) >= 3 and w not in STOP}


@dataclass
class ReceiptFile:
    path: Path
    rel: str            # relative to receipts root, forward slashes
    size: int
    date: date | None
    junk: str | None    # reason this is not a receipt candidate

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def stem(self) -> str:
        return self.path.stem

    @property
    def folder(self) -> str:
        return self.rel.split("/")[0] if "/" in self.rel else ""

    @property
    def at_root(self) -> bool:
        return "/" not in self.rel

    @property
    def is_transcript(self) -> bool:
        return self.path.suffix.lower() in TRANSCRIPT_EXT

    @cached_property
    def sha(self) -> str:
        return content_hash(self.path)

    @cached_property
    def tokens(self) -> set[str]:
        return tokens(self.rel)


@dataclass
class ReceiptIndex:
    root: Path
    files: list[ReceiptFile]
    saved_page_dirs: dict[str, int]    # "<rel dir>" -> file count (browser "_files" folders)

    def candidates(self) -> list[ReceiptFile]:
        return [f for f in self.files if f.junk is None]


def build_index(root: Path, ignore_dirs: tuple[str, ...] = ()) -> ReceiptIndex:
    files: list[ReceiptFile] = []
    saved: dict[str, int] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        parts = rel.split("/")
        page_dir = next((i for i, part in enumerate(parts[:-1]) if part.endswith("_files")), None)
        if page_dir is not None:
            key = "/".join(parts[:page_dir + 1])
            saved[key] = saved.get(key, 0) + 1
            continue
        size = p.stat().st_size
        junk = None
        if parts[0] in ignore_dirs and len(parts) > 1:
            junk = f"in ignored folder {parts[0]}"
        elif size == 0:
            junk = "zero bytes"
        elif p.suffix.lower() == ".url":
            junk = "shortcut file"
        elif p.name.startswith("~$") or p.name.endswith(".~tmp.xlsx"):
            junk = "temp/lock file"
        files.append(ReceiptFile(p, rel, size, date_from_name(p.name), junk))
    return ReceiptIndex(root, files, saved)
