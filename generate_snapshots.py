#!/usr/bin/env python3
"""Generate text snapshots of all analysis results for regression testing.

Run from the repo root:
    python generate_snapshots.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "02_ciscategorial_output"))
sys.path.insert(0, str(ROOT / "03_subspanrepetition_output"))
sys.path.insert(0, str(ROOT / "04_noninterruption"))

import ciscategorial as _cisc
import subspanrepetition as _subspan
import noninterruption as _nonint

SNAPSHOTS_DIR = ROOT / "tests" / "snapshots"

_SUFFIX_RE = re.compile(r"_(filled?|full|test|blank)$", re.IGNORECASE)
_CAMEL_RE = re.compile(r"(?<=[a-z])(?=[A-Z])")


def tsv_to_title(tsv_filename: str) -> str:
    stem = Path(tsv_filename).stem
    stem = _SUFFIX_RE.sub("", stem)
    stem = stem.replace("stan1293", "English")
    stem = _CAMEL_RE.sub("-", stem)
    stem = stem.replace("_", " ").lower()
    return stem.title()


def _fmt(span: tuple, pos_to_name: dict) -> str:
    l, r = span
    return f"positions {l}\u2013{r}  ({pos_to_name.get(l, '?')} \u2192 {pos_to_name.get(r, '?')})"


def _snapshot_ciscategorial(tsv: str) -> str:
    result = _cisc.derive_v_ciscategorial_fractures(tsv)
    p = result["position_number_to_name"]
    f = lambda span: _fmt(span, p)
    lines = [
        f"Keystone position: {result['keystone_position']} ({p.get(result['keystone_position'], '?')})",
        "",
        f"V-ciscategorial complete positions: {result['full_positions']}",
        f"V-ciscategorial partial positions:  {result['partial_positions']}",
        "",
        f"Strict complete v-ciscategorial span: {f(result['strict_complete_v_fracture'])}",
        f"Loose complete v-ciscategorial span:  {f(result['loose_complete_v_fracture'])}",
        f"Strict partial v-ciscategorial span:  {f(result['strict_partial_v_fracture'])}",
        f"Loose partial v-ciscategorial span:   {f(result['loose_partial_v_fracture'])}",
    ]
    return "\n".join(lines)


def _snapshot_subspanrepetition(tsv: str) -> str:
    result = _subspan.derive_subspanrepetition_spans(tsv)
    p = result["position_number_to_name"]
    f = lambda span: _fmt(span, p)
    lines = [
        f"Keystone position: {result['keystone_position']} ({p.get(result['keystone_position'], '?')})",
    ]
    for k in [
        "maximum_fillable",
        "maximum_widescope_left",
        "maximum_widescope_right",
        "maximum_narrowscope_left",
        "maximum_narrowscope_right",
    ]:
        lines += [
            "",
            f"== {k} ==",
            f"{k} complete positions: {result[f'{k}_complete_positions']}",
            f"{k} partial positions:  {result[f'{k}_partial_positions']}",
            "",
            f"Strict complete {k} span: {f(result[f'strict_complete_{k}_span'])}",
            f"Loose complete {k} span:  {f(result[f'loose_complete_{k}_span'])}",
            f"Strict partial {k} span:  {f(result[f'strict_partial_{k}_span'])}",
            f"Loose partial {k} span:   {f(result[f'loose_partial_{k}_span'])}",
        ]
    return "\n".join(lines)


def _snapshot_noninterruption(tsv: str) -> str:
    result = _nonint.derive_noninterruption_domains(tsv)
    p = result["position_number_to_name"]
    f = lambda span: _fmt(span, p)
    lines = [
        f"Keystone position: {result['keystone_position']} ({p.get(result['keystone_position'], '?')})",
        "",
        f"No-free complete positions:      {result['no_free_complete_positions']}",
        f"No-free partial positions:       {result['no_free_partial_positions']}",
        f"Single-free complete positions:  {result['single_free_complete_positions']}",
        f"Single-free partial positions:   {result['single_free_partial_positions']}",
        "",
        f"No-free complete span:      {f(result['no_free_complete_domain'])}",
        f"No-free partial span:       {f(result['no_free_partial_domain'])}",
        f"Single-free complete span:  {f(result['single_free_complete_domain'])}",
        f"Single-free partial span:   {f(result['single_free_partial_domain'])}",
    ]
    return "\n".join(lines)


_FILLED_RE = re.compile(r"_(fill(?:ed)?|full|test)\.tsv$", re.IGNORECASE)

_FOLDER_MAP = [
    (ROOT / "02_ciscategorial_output", _snapshot_ciscategorial),
    (ROOT / "03_subspanrepetition_output", _snapshot_subspanrepetition),
    (ROOT / "04_noninterruption", _snapshot_noninterruption),
]

TASKS = [
    (tsv_path, snap_fn)
    for folder, snap_fn in _FOLDER_MAP
    for tsv_path in sorted(folder.glob("*.tsv"))
    if _FILLED_RE.search(tsv_path.name)
]


def main() -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    for tsv_path, snap_fn in TASKS:
        title = tsv_to_title(tsv_path.name)
        body = snap_fn(tsv_path.name)
        out_text = f"{title}\n{'=' * len(title)}\n\n{body}\n"
        out_path = SNAPSHOTS_DIR / (tsv_path.stem + ".txt")
        out_path.write_text(out_text, encoding="utf-8")
        print(f"Wrote: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
