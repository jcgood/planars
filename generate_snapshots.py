#!/usr/bin/env python3
"""Generate text snapshots of all analysis results for regression testing.

Runs every analysis in planars.reports' registry against every matching
filled TSV in coded_data/. The resulting .txt files in tests/snapshots/ serve
as the baseline for pytest snapshot tests (tests/test_snapshots.py). A
snapshot whose tab no longer exists (a retired class or construction) is
deleted, so the folder holds exactly one file per tab.

Run from the repo root:
    python generate_snapshots.py

Run after any intentional change to analysis output (bug fix, logic change,
new data). Review the diff with `git diff tests/snapshots/` before committing.
"""
from __future__ import annotations

import importlib
import re
from pathlib import Path

from planars.languages import get_entry
from planars.reports import _CLASS_HANDLERS as _REPORT_HANDLERS, span_constructions

ROOT = Path(__file__).resolve().parent
SNAPSHOTS_DIR = ROOT / "tests" / "snapshots"

_FILLED_RE  = re.compile(r"\.tsv$", re.IGNORECASE)
_LEGACY_RE  = re.compile(r"_(fill(?:ed)?|full|test)\.tsv$", re.IGNORECASE)
_SUFFIX_RE  = re.compile(r"_(filled?|full|test|blank)$", re.IGNORECASE)
_CAMEL_RE   = re.compile(r"(?<=[a-z])(?=[A-Z])")

# The analyses are the reports' registry, the one list of them. Until
# 2026-10-17 this script imported every planars/*.py and skipped any that
# failed to import, so a broken analysis module silently lost its snapshots.
def _build_handlers() -> list[tuple[str, object, object, frozenset | None]]:
    handlers = []
    for class_name in sorted(_REPORT_HANDLERS):
        mod = importlib.import_module(f"planars.{class_name}")
        handlers.append((class_name, mod.derive, mod.format_result,
                         span_constructions(class_name)))
    return handlers


_CLASS_HANDLERS = _build_handlers()

# Build the task list: one entry per (tsv_path, derive_fn, fmt_fn).
# A class with feeder tabs (`produces_spans: false` in diagnostic_classes.yaml)
# only has its span-producing tabs included (feeders like nonpermutability's
# element_prescreening.tsv use a different schema and would crash derive).
TASKS = [
    (tsv_path, derive_fn, fmt_fn)
    for class_name, derive_fn, fmt_fn, snap_constructions in _CLASS_HANDLERS
    for lang_dir in sorted((ROOT / "coded_data").iterdir())
    if lang_dir.is_dir()
    for tsv_path in sorted((lang_dir / class_name).glob("*.tsv"))
    if (lang_dir / class_name).exists()
    and _FILLED_RE.search(tsv_path.name)
    and not _LEGACY_RE.search(tsv_path.name)
    and (snap_constructions is None or tsv_path.stem in snap_constructions)
]


def snapshot_stem(tsv_path: Path) -> str:
    """Return snapshot filename stem: {lang_id}_{class_name}_{tsv_stem}."""
    class_name = tsv_path.parent.name
    lang_id    = tsv_path.parent.parent.name
    return f"{lang_id}_{class_name}_{tsv_path.stem}"


def tsv_to_title(tsv_path: Path) -> str:
    """Snapshot heading: the language's Glottolog name (from languages.yaml; the
    bare code for a language not in it, e.g. synth0001), then class and
    construction. Until 2026-10-12 only English got a name, typed in here."""
    lang_id = tsv_path.parent.parent.name
    name = ((get_entry(lang_id) or {}).get("glottolog") or {}).get("name") or lang_id
    stem = snapshot_stem(tsv_path)[len(lang_id):]
    stem = _SUFFIX_RE.sub("", stem)
    stem = _CAMEL_RE.sub("-", stem)
    stem = stem.replace("_", " ").lower()
    return (name.lower() + stem).title()


def stale_snapshots() -> list[Path]:
    """Snapshot files that no task writes: their tab has gone."""
    wanted = {snapshot_stem(t[0]) + ".txt" for t in TASKS}
    return sorted(p for p in SNAPSHOTS_DIR.glob("*.txt") if p.name not in wanted)


def main() -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    for stale in stale_snapshots():
        stale.unlink()
        print(f"Removed (no such tab): {stale.relative_to(ROOT)}")
    for tsv_path, derive_fn, fmt_fn in TASKS:
        title  = tsv_to_title(tsv_path)
        result = derive_fn(tsv_path, strict=False)
        body   = fmt_fn(result)
        text   = f"{title}\n{'=' * len(title)}\n\n{body}\n"
        out    = SNAPSHOTS_DIR / (snapshot_stem(tsv_path) + ".txt")
        out.write_text(text, encoding="utf-8")
        print(f"Wrote: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
