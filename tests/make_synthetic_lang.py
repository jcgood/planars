"""Generate a synthetic second-language dataset for multi-language testing.

Copies coded_data/stan1293 to coded_data/synth0001, applying deterministic
quasi-random flips to ~25% of y/n parameter values (seed=42) so the two
languages produce different span results. Structural columns, NA/both/?
values, and Comments are left unchanged.

Usage:
    python tests/make_synthetic_lang.py           # dry run
    python tests/make_synthetic_lang.py --apply   # write files
    python tests/make_synthetic_lang.py --clean   # remove synth0001 (dry run)
    python tests/make_synthetic_lang.py --clean --apply  # actually remove it
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

REPO_ROOT   = Path(__file__).parent.parent
SRC_LANG    = "stan1293"
DST_LANG    = "synth0001"
FLIP_PROB   = 0.25
SEED        = 42

_STRUCTURAL = {"Element", "Position_Name", "Position_Number"}
_TRAILING   = {"Comments"}
_FLIPPABLE  = {"y", "n"}


def _flip_tsv(src_text: str, rng: random.Random) -> str:
    lines = src_text.splitlines(keepends=True)
    if not lines:
        return src_text
    header = lines[0].rstrip("\n").split("\t")
    param_cols = [i for i, h in enumerate(header)
                  if h not in _STRUCTURAL and h not in _TRAILING]
    out = [lines[0]]
    for line in lines[1:]:
        parts = line.rstrip("\n").split("\t")
        # Pad to header length in case trailing tabs are missing
        while len(parts) < len(header):
            parts.append("")
        for i in param_cols:
            if parts[i] in _FLIPPABLE and rng.random() < FLIP_PROB:
                parts[i] = "n" if parts[i] == "y" else "y"
        out.append("\t".join(parts) + "\n")
    return "".join(out)


def build_plan(src_root: Path, dst_root: Path) -> list[tuple[str, Path, Path, str | None]]:
    """Return list of (action, src, dst, description) tuples."""
    plan = []

    # planar_input: copy diagnostics, rename + patch planar TSV
    src_pi = src_root / "planar_input"
    dst_pi = dst_root / "planar_input"

    # diagnostics.tsv — replace lang ID in Language column
    src_diag = src_pi / "diagnostics.tsv"
    diag_text = src_diag.read_text().replace(SRC_LANG, DST_LANG)
    plan.append(("write", src_diag, dst_pi / "diagnostics.tsv", diag_text))

    # planar TSV — rename file, replace lang ID in first column
    planar_src = next(src_pi.glob("planar_*.tsv"))
    planar_dst_name = planar_src.name.replace(SRC_LANG, DST_LANG)
    planar_text = planar_src.read_text().replace(SRC_LANG, DST_LANG)
    plan.append(("write", planar_src, dst_pi / planar_dst_name, planar_text))

    # filled TSVs — copy with value flips
    rng = random.Random(SEED)
    for class_dir in sorted(src_root.iterdir()):
        if not class_dir.is_dir() or class_dir.name in ("planar_input", "archive", ".DS_Store"):
            continue
        for tsv in sorted(class_dir.glob("*_filled.tsv")):
            flipped = _flip_tsv(tsv.read_text(), rng)
            dst_tsv = dst_root / class_dir.name / tsv.name
            plan.append(("write", tsv, dst_tsv, flipped))

    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Write files (default is dry run)")
    parser.add_argument("--clean", action="store_true",
                        help="Remove synth0001 instead of creating it")
    args = parser.parse_args()

    src_root = REPO_ROOT / "coded_data" / SRC_LANG
    dst_root = REPO_ROOT / "coded_data" / DST_LANG

    if args.clean:
        if not dst_root.exists():
            print(f"{DST_LANG} does not exist — nothing to remove.")
            return
        if args.apply:
            shutil.rmtree(dst_root)
            print(f"Removed {dst_root}")
        else:
            print(f"[dry run] Would remove {dst_root}/")
        return

    if dst_root.exists() and not args.apply:
        print(f"NOTE: {DST_LANG} already exists; dry run shows what would be overwritten.\n")

    plan = build_plan(src_root, dst_root)

    flips_total = 0
    for action, src, dst, content in plan:
        rel = dst.relative_to(REPO_ROOT)
        if args.apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content)
            print(f"  wrote  {rel}")
        else:
            print(f"  would write  {rel}")
        # Count flipped cells for info
        if "filled" in dst.name and content:
            lines = content.splitlines()[1:]  # skip header
            src_lines = src.read_text().splitlines()[1:]
            for sl, dl in zip(src_lines, lines):
                sp, dp = sl.split("\t"), dl.split("\t")
                flips_total += sum(1 for a, b in zip(sp, dp) if a != b)

    print(f"\n{'Applied' if args.apply else 'Dry run'}:"
          f" {len(plan)} files, ~{flips_total} value flips")
    if not args.apply:
        print("Run with --apply to write files.")


if __name__ == "__main__":
    main()
