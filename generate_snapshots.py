#!/usr/bin/env python3
"""Generate text snapshots of all analysis results for regression testing.

Discovers every planars analysis module that exposes both `derive` and
`format_result`, then runs each against every matching filled TSV in
coded_data/. The resulting .txt files in tests/snapshots/ serve as the
baseline for pytest snapshot tests (tests/test_snapshots.py).

Run from the repo root:
    python generate_snapshots.py

Run after any intentional change to analysis output (bug fix, logic change,
new data). Review the diff with `git diff tests/snapshots/` before committing.
"""
from __future__ import annotations

import importlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SNAPSHOTS_DIR = ROOT / "tests" / "snapshots"

_FILLED_RE  = re.compile(r"\.tsv$", re.IGNORECASE)
_LEGACY_RE  = re.compile(r"_(fill(?:ed)?|full|test)\.tsv$", re.IGNORECASE)
_SUFFIX_RE  = re.compile(r"_(filled?|full|test|blank)$", re.IGNORECASE)
_CAMEL_RE   = re.compile(r"(?<=[a-z])(?=[A-Z])")

# Auto-discover all analysis modules: any planars/*.py that exposes both
# `derive` (primary derive function alias) and `format_result`.
_ANALYSIS_SKIP = {"charts", "cli", "io", "spans"}


def _build_handlers() -> list[tuple[str, object, object, frozenset | None]]:
    handlers = []
    planars_dir = ROOT / "planars"
    for path in sorted(planars_dir.glob("*.py")):
        if path.stem.startswith("_") or path.stem in _ANALYSIS_SKIP:
            continue
        try:
            mod = importlib.import_module(f"planars.{path.stem}")
            if hasattr(mod, "derive") and hasattr(mod, "format_result"):
                snap = getattr(mod, "_SNAPSHOT_CONSTRUCTIONS", None)
                handlers.append((path.stem, mod.derive, mod.format_result, snap))
        except Exception:
            pass
    return handlers


_CLASS_HANDLERS = _build_handlers()

# Build the task list: one entry per (tsv_path, derive_fn, fmt_fn).
# If a module defines _SNAPSHOT_CONSTRUCTIONS, only TSVs whose stem matches
# one of those names are included (guards against multi-format class dirs like
# nonpermutability, where element_prescreening.tsv uses a different schema).
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
    stem = snapshot_stem(tsv_path)
    stem = _SUFFIX_RE.sub("", stem)
    stem = stem.replace("stan1293", "English")
    stem = _CAMEL_RE.sub("-", stem)
    stem = stem.replace("_", " ").lower()
    return stem.title()


def main() -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
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
