"""Compare two workbooks for feature loss and cell-level changes.

Used before/after the first openpyxl write to prove nothing Excel-specific was dropped.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import openpyxl


def _parts(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as z:
        return set(z.namelist())


def _style_key(c) -> tuple:
    return (repr(c.font), repr(c.fill), repr(c.border), c.number_format, repr(c.alignment),
            repr(c.protection))


def _sheet_features(ws) -> dict[str, object]:
    return {
        "merged": sorted(str(r) for r in ws.merged_cells.ranges),
        "validations": sorted((str(d.sqref), d.type, d.formula1) for d in ws.data_validations.dataValidation),
        "conditional_formats": sorted(str(r.sqref) for r in ws.conditional_formatting),
        "col_widths": {k: v.width for k, v in sorted(ws.column_dimensions.items())},
        "freeze_panes": ws.freeze_panes,
        "auto_filter": ws.auto_filter.ref,
        "print_area": ws.print_area,
        "page_setup": (ws.page_setup.orientation, ws.page_setup.paperSize, ws.page_setup.fitToWidth),
        "images": len(getattr(ws, "_images", [])),
        "charts": len(getattr(ws, "_charts", [])),
        "tables": sorted(ws.tables.keys()),
    }


def diff(before: Path, after: Path, max_cells: int = 200) -> dict[str, list[str]]:
    """Returns {'features': [...], 'cells': [...]} describing every difference."""
    out: dict[str, list[str]] = {"features": [], "cells": []}
    pa, pb = _parts(before), _parts(after)
    for p in sorted(pa - pb):
        out["features"].append(f"package part removed: {p}")
    for p in sorted(pb - pa):
        out["features"].append(f"package part added: {p}")

    wa, wb = openpyxl.load_workbook(before), openpyxl.load_workbook(after)
    if wa.sheetnames != wb.sheetnames:
        out["features"].append(f"sheets {wa.sheetnames} -> {wb.sheetnames}")
    if sorted(wa.defined_names.keys()) != sorted(wb.defined_names.keys()):
        out["features"].append("defined names differ")
    for name in wa.sheetnames:
        if name not in wb.sheetnames:
            continue
        a, b = wa[name], wb[name]
        fa, fb = _sheet_features(a), _sheet_features(b)
        for k in fa:
            if fa[k] != fb[k]:
                out["features"].append(f"{name}: {k} {fa[k]} -> {fb[k]}")
        coords = set(a._cells) | set(b._cells)
        for rc in sorted(coords):
            ca, cb = a.cell(*rc), b.cell(*rc)
            if ca.value != cb.value:
                out["cells"].append(f"{name}!{ca.coordinate}: {ca.value!r} -> {cb.value!r}")
            elif ca.has_style or cb.has_style:
                if _style_key(ca) != _style_key(cb):
                    out["cells"].append(f"{name}!{ca.coordinate}: style changed")
            if len(out["cells"]) >= max_cells:
                out["cells"].append("... (truncated)")
                return out
    return out


def render(d: dict[str, list[str]]) -> str:
    lines = ["Feature differences:"] + ([f"  - {x}" for x in d["features"]] or ["  none"])
    lines += [f"Cell differences ({len(d['cells'])}):"] + ([f"  - {x}" for x in d["cells"]] or ["  none"])
    return "\n".join(lines)
