"""Content fingerprint used for duplicate detection (SHA-1, matching OneDrive's sha1Hash).

In cloud mode most receipts are zero-byte placeholders; a resolver installed by
fonenova.cloud answers with OneDrive's stored hash instead of reading the bytes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

_resolver: Callable[[Path], str | None] | None = None


def set_resolver(fn: Callable[[Path], str | None] | None) -> None:
    global _resolver
    _resolver = fn


def content_hash(path: Path) -> str:
    if _resolver is not None:
        h = _resolver(Path(path))
        if h:
            return h.lower()
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
