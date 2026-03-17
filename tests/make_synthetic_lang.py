"""Generate a synthetic second-language dataset for multi-language testing.

Copies coded_data/stan1293 to coded_data/synth0001 with two kinds of changes:

  Structural: ~25% of non-keystone positions are dropped (seed=42); the
  remaining positions are renumbered sequentially from 1, preserving order.
  The keystone (v:verbroot) is always kept and gets a new position number.

  Parametric: ~25% of y/n parameter values in filled TSVs are flipped
  (same seed). Rows for dropped positions are removed.

The result is a fully valid dataset with a different planar structure, useful
for testing multi-language code paths in collect_all_spans etc.

Usage:
    python tests/make_synthetic_lang.py           # dry run
    python tests/make_synthetic_lang.py --apply   # write files
    python tests/make_synthetic_lang.py --clean   # remove synth0001 (dry run)
    python tests/make_synthetic_lang.py --clean --apply  # actually remove it
"""

from __future__ import annotations

import argparse
import csv
import io
import random
import shutil
from pathlib import Path

REPO_ROOT  = Path(__file__).parent.parent
SRC_LANG   = "stan1293"
DST_LANG   = "synth0001"
KEEP_PROB  = 0.75
FLIP_PROB  = 0.25
SEED       = 42

_STRUCTURAL = {"Element", "Position_Name", "Position_Number"}
_TRAILING   = {"Comments"}
_FLIPPABLE  = {"y", "n"}


# ---------------------------------------------------------------------------
# Position map
# ---------------------------------------------------------------------------

def _build_position_map(planar_path: Path, rng: random.Random) -> dict[int, int]:
    """Return {old_position_number: new_position_number} for kept positions.

    Drops ~25% of non-keystone positions at random; always keeps the keystone.
    Survivors are renumbered 1..N preserving left-to-right order.
    """
    seen: dict[int, str] = {}  # pos -> Position_Name, insertion order = file order
    with planar_path.open() as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            pos = int(row["Position"])
            if pos not in seen:
                seen[pos] = row["Position_Name"]

    keystone_pos = next(p for p, name in seen.items() if name == "v:verbroot")
    non_keystone = [p for p in sorted(seen) if p != keystone_pos]

    n_keep = max(1, round(len(non_keystone) * KEEP_PROB))
    kept = sorted(rng.sample(non_keystone, n_keep))
    kept.append(keystone_pos)
    kept.sort()

    return {old: new for new, old in enumerate(kept, start=1)}


# ---------------------------------------------------------------------------
# TSV transformers
# ---------------------------------------------------------------------------

def _transform_planar_tsv(text: str, pos_map: dict[int, int], dst_lang: str) -> str:
    lines = text.splitlines(keepends=True)
    out = [lines[0]]  # header unchanged
    for line in lines[1:]:
        parts = line.rstrip("\n").split("\t")
        pos = int(parts[2])  # Position column
        if pos not in pos_map:
            continue
        parts[0] = dst_lang           # Language_ID
        parts[2] = str(pos_map[pos])  # Position
        out.append("\t".join(parts) + "\n")
    return "".join(out)


def _transform_filled_tsv(text: str, pos_map: dict[int, int], rng: random.Random) -> str:
    lines = text.splitlines(keepends=True)
    if not lines:
        return text
    header = lines[0].rstrip("\n").split("\t")
    param_cols = [i for i, h in enumerate(header)
                  if h not in _STRUCTURAL and h not in _TRAILING]
    out = [lines[0]]
    for line in lines[1:]:
        parts = line.rstrip("\n").split("\t")
        while len(parts) < len(header):
            parts.append("")
        pos = int(parts[header.index("Position_Number")])
        if pos not in pos_map:
            continue
        parts[header.index("Position_Number")] = str(pos_map[pos])
        for i in param_cols:
            if parts[i] in _FLIPPABLE and rng.random() < FLIP_PROB:
                parts[i] = "n" if parts[i] == "y" else "y"
        out.append("\t".join(parts) + "\n")
    return "".join(out)


# ---------------------------------------------------------------------------
# Plan builder
# ---------------------------------------------------------------------------

def build_plan(
    src_root: Path,
    dst_root: Path,
    pos_map: dict[int, int],
    rng: random.Random,
) -> list[tuple[Path, str]]:
    """Return list of (dst_path, content) pairs."""
    plan = []
    src_pi = src_root / "planar_input"
    dst_pi = dst_root / "planar_input"

    # diagnostics.tsv — only lang ID changes
    diag_text = (src_pi / "diagnostics.tsv").read_text().replace(SRC_LANG, DST_LANG)
    plan.append((dst_pi / "diagnostics.tsv", diag_text))

    # planar TSV — drop positions, renumber, update lang ID
    planar_src = next(src_pi.glob("planar_*.tsv"))
    planar_text = _transform_planar_tsv(planar_src.read_text(), pos_map, DST_LANG)
    plan.append((dst_pi / planar_src.name.replace(SRC_LANG, DST_LANG), planar_text))

    # filled TSVs — drop rows, renumber, flip values
    for class_dir in sorted(src_root.iterdir()):
        if not class_dir.is_dir() or class_dir.name in ("planar_input", "archive", ".DS_Store"):
            continue
        for tsv in sorted(class_dir.glob("*_filled.tsv")):
            content = _transform_filled_tsv(tsv.read_text(), pos_map, rng)
            plan.append((dst_root / class_dir.name / tsv.name, content))

    return plan


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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

    rng = random.Random(SEED)
    planar_src = next((src_root / "planar_input").glob("planar_*.tsv"))
    pos_map = _build_position_map(planar_src, rng)

    new_keystone = pos_map[next(
        int(row["Position"])
        for row in csv.DictReader(planar_src.open(), delimiter="\t")
        if row["Position_Name"] == "v:verbroot"
    )]

    n_src = len(pos_map)
    print(f"Positions: {len(pos_map)} kept of 37  "
          f"(dropped {37 - n_src})  "
          f"keystone renumbered to {new_keystone}")
    print(f"Old→new map: {pos_map}\n")

    plan = build_plan(src_root, dst_root, pos_map, rng)

    flips = 0
    for dst, content in plan:
        rel = dst.relative_to(REPO_ROOT)
        if args.apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content)
            print(f"  wrote  {rel}")
        else:
            print(f"  would write  {rel}")
        if "filled" in dst.name:
            src_tsv = src_root / dst.parent.name / dst.name
            if src_tsv.exists():
                src_lines = src_tsv.read_text().splitlines()[1:]
                dst_lines = content.splitlines()[1:]
                # compare only rows present in dst
                src_by_pos: dict[tuple, list] = {}
                header = src_tsv.read_text().splitlines()[0].split("\t")
                pi = header.index("Position_Number")
                ei = header.index("Element")
                for sl in src_lines:
                    p = sl.split("\t")
                    key = (p[pi], p[ei])
                    src_by_pos[key] = p
                for dl in dst_lines:
                    dp = dl.split("\t")
                    key = (str(pos_map.get(int(dp[pi]), -1)), dp[ei]) if dp[pi].isdigit() else ("?", "?")
                    # find matching src row by element+orig pos
                    orig_pos = next((k for k, v in pos_map.items() if v == int(dp[pi])), None) if dp[pi].isdigit() else None
                    if orig_pos is not None:
                        src_key = (str(orig_pos), dp[ei])
                        sp = src_by_pos.get(src_key, [])
                        flips += sum(1 for a, b in zip(sp, dp) if a != b and a in _FLIPPABLE)

    print(f"\n{'Applied' if args.apply else 'Dry run'}:"
          f" {len(plan)} files, ~{flips} value flips across filled TSVs")
    if not args.apply:
        print("Run with --apply to write files.")


if __name__ == "__main__":
    main()
