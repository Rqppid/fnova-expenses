import shutil
from pathlib import Path

import pytest

from fonenova.layout import backup_root, layouts, load_config

SEPTDEC_NAME = "VAT Return From Sept-Dec, 2026.xlsx"
V18_NAME = "VATReturn_Automated_v18_delivered_1.xlsx"
# The untouched 5 Oct state, used as the reference fixture.
REFERENCE = "2026-10-05_205132"


def _reference(name: str) -> Path:
    p = backup_root(load_config()) / REFERENCE / name
    if not p.exists():
        pytest.skip(f"reference backup not found: {p}")
    return p


@pytest.fixture
def lays():
    return layouts(load_config())


@pytest.fixture
def septdec_copy(tmp_path):
    dst = tmp_path / SEPTDEC_NAME
    shutil.copy2(_reference(SEPTDEC_NAME), dst)
    return dst


@pytest.fixture
def v18_ref():
    return _reference(V18_NAME)


@pytest.fixture
def bdir(tmp_path):
    d = tmp_path / "backups"
    d.mkdir()
    return d
