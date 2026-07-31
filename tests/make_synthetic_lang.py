"""Generate a synthetic second-language dataset for multi-language testing.

Copies coded_data/stan1293 to coded_data/synth0001 with two kinds of changes:

  Structural: by default, ~25% of non-keystone positions are dropped
  (seed=42); the remaining positions are renumbered sequentially from 1,
  preserving order. The keystone (v:verbstem) is always kept and gets a new
  position number. Pass --full-copy to disable dropping entirely (keep_prob=1),
  which also makes new position numbers identical to the old ones -- useful
  when a test needs a stable structural mirror of stan1293 without the
  position-renumbering complexity (e.g. bootstrapping new lang_setup files
  that don't yet have position-drop handling of their own).

  Parametric: ~25% of y/n parameter values in filled TSVs are flipped
  (same seed), independent of --full-copy.

Filled/annotated TSVs come in three row shapes, each handled differently when
positions are dropped:
  - Position_Number column (ordinary per-element rows): row is dropped if its
    position was cut.
  - Position_A + Position_B columns (pair constructions, e.g. coreference):
    each is a "N (name)" reference; row is dropped if EITHER position was cut,
    otherwise both are remapped to their new number with the name unchanged.
  - Neither (pure Element_A/Element_B pairs, e.g. nonpermutability/general.tsv):
    row is dropped only if an element no longer occurs at ANY surviving
    position at all, checked against an index built from the original planar
    structure -- an element with multiple occurrences survives as long as one
    of them does, even if that specific pairing was never itself tested.

The result is a fully valid dataset with a different planar structure, useful
for testing multi-language code paths in collect_all_spans etc.

Usage:
    python tests/make_synthetic_lang.py               # dry run
    python tests/make_synthetic_lang.py --apply        # write files
    python tests/make_synthetic_lang.py --full-copy --apply  # no position drop
    python tests/make_synthetic_lang.py --clean        # remove synth0001 (dry run)
    python tests/make_synthetic_lang.py --clean --apply  # actually remove it
"""

from __future__ import annotations

import argparse
import csv
import io
import random
import re
import shutil
from pathlib import Path

from coding.make_forms import _split_elements

REPO_ROOT  = Path(__file__).parent.parent
SRC_LANG   = "stan1293"
DST_LANG   = "synth0001"
KEEP_PROB  = 0.75
FLIP_PROB  = 0.25
SEED       = 42

_STRUCTURAL = {"Element", "Position_Name", "Position_Number"}
_TRAILING   = {"Comments"}
_FLIPPABLE  = {"y", "n"}

_POS_REF_RE = re.compile(r'^(\d+)\s*\((.+)\)$')


# ---------------------------------------------------------------------------
# Position map
# ---------------------------------------------------------------------------

def _build_position_map(
    planar_path: Path, rng: random.Random, keep_prob: float = KEEP_PROB
) -> dict[int, int]:
    """Return {old_position_number: new_position_number} for kept positions.

    Drops ~(1 - keep_prob) of non-keystone positions at random; always keeps
    the keystone. Survivors are renumbered 1..N preserving left-to-right
    order. keep_prob=1.0 (--full-copy) keeps everything, which also makes the
    map the identity (old positions were already 1..N with no gaps).
    """
    seen: dict[int, str] = {}  # pos -> Position_Name, insertion order = file order
    with planar_path.open() as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            pos = int(row["Position"])
            if pos not in seen:
                seen[pos] = row["Position_Name"]

    keystone_pos = next(p for p, name in seen.items() if name == "v:verbstem")
    non_keystone = [p for p in sorted(seen) if p != keystone_pos]

    n_keep = max(1, round(len(non_keystone) * keep_prob))
    kept = sorted(rng.sample(non_keystone, n_keep))
    kept.append(keystone_pos)
    kept.sort()

    return {old: new for new, old in enumerate(kept, start=1)}


def _build_element_positions(planar_path: Path) -> dict[str, set[int]]:
    """Map each element label to the set of (old) positions it occurs at.

    Used to decide whether a pure Element_A/Element_B pair row (no explicit
    position column) still makes sense post-drop: the element survives as
    long as it occurs at at least one surviving position, even if that's not
    the specific occurrence the row was originally about.
    """
    positions: dict[str, set[int]] = {}
    with planar_path.open() as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            pos = int(row["Position"])
            for element in _split_elements(row.get("Elements", "") or ""):
                positions.setdefault(element, set()).add(pos)
    return positions


def _remap_position_ref(value: str, pos_map: dict[int, int]) -> str | None:
    """Remap a "N (name)" position reference (e.g. coreference's Position_A/B).

    Returns the remapped string with the new number and unchanged name, or
    None if the referenced position was dropped -- there is no honest way to
    remap a reference whose position no longer exists, since numbers get
    reassigned to *different* positions rather than simply going unused.
    """
    m = _POS_REF_RE.match(value.strip())
    if not m:
        return value  # not a recognized position-ref string; leave untouched
    old_pos, name = int(m.group(1)), m.group(2)
    new_pos = pos_map.get(old_pos)
    if new_pos is None:
        return None
    return f"{new_pos} ({name})"


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


def _transform_filled_tsv(
    text: str,
    pos_map: dict[int, int],
    rng: random.Random,
    element_positions: dict[str, set[int]],
) -> tuple[str, int, int, int]:
    """Transform one filled/annotated TSV for the synthetic language.

    Returns (new_text, n_kept, n_dropped, n_flips). See module docstring for
    how each of the three row shapes (Position_Number / Position_A+B /
    Element_A+B only) decides whether a row survives the position drop.
    """
    lines = text.splitlines(keepends=True)
    if not lines:
        return text, 0, 0, 0
    header = lines[0].rstrip("\n").split("\t")
    non_criterion = _STRUCTURAL | _TRAILING | {"Position_A", "Position_B",
                                                "Element_A", "Element_B"}
    criterion_cols = [i for i, h in enumerate(header) if h not in non_criterion]

    has_position_number = "Position_Number" in header
    has_position_pair = "Position_A" in header and "Position_B" in header

    out = [lines[0]]
    n_kept = n_dropped = n_flips = 0

    for line in lines[1:]:
        parts = line.rstrip("\n").split("\t")
        while len(parts) < len(header):
            parts.append("")

        keep = True

        if has_position_number:
            idx = header.index("Position_Number")
            pos = int(parts[idx])
            if pos not in pos_map:
                keep = False
            else:
                parts[idx] = str(pos_map[pos])

        elif has_position_pair:
            ia, ib = header.index("Position_A"), header.index("Position_B")
            new_a = _remap_position_ref(parts[ia], pos_map)
            new_b = _remap_position_ref(parts[ib], pos_map)
            if new_a is None or new_b is None:
                keep = False
            else:
                parts[ia], parts[ib] = new_a, new_b

        else:
            # Pure Element_A/Element_B pairs (e.g. nonpermutability/general.tsv):
            # drop only if an element no longer occurs at any surviving position.
            for col in ("Element_A", "Element_B"):
                if col not in header:
                    continue
                element = parts[header.index(col)]
                old_positions = element_positions.get(element, set())
                if old_positions and not any(p in pos_map for p in old_positions):
                    keep = False

        if not keep:
            n_dropped += 1
            continue

        for i in criterion_cols:
            if parts[i] in _FLIPPABLE and rng.random() < FLIP_PROB:
                parts[i] = "n" if parts[i] == "y" else "y"
                n_flips += 1

        out.append("\t".join(parts) + "\n")
        n_kept += 1

    return "".join(out), n_kept, n_dropped, n_flips


# ---------------------------------------------------------------------------
# Plan builder
# ---------------------------------------------------------------------------

def _transform_element_keyed_tsv(
    text: str, pos_map: dict[int, int], element_positions: dict[str, set[int]]
) -> tuple[str, int, int]:
    """Transform a lang_setup TSV keyed by a single Element column with no
    position column of its own (e.g. a future allomorphs_{lang_id}.tsv).

    Drops a row only if its Element no longer occurs at any surviving
    position; otherwise passes it through unchanged. No value-flipping here --
    these are structural/coordinator-authored facts (per #249's morpheme_id
    resolution), not annotated criteria.
    """
    lines = text.splitlines(keepends=True)
    if not lines:
        return text, 0, 0
    header = lines[0].rstrip("\n").split("\t")
    if "Element" not in header:
        return text, max(0, len(lines) - 1), 0
    ei = header.index("Element")
    out = [lines[0]]
    n_kept = n_dropped = 0
    for line in lines[1:]:
        parts = line.rstrip("\n").split("\t")
        while len(parts) < len(header):
            parts.append("")
        old_positions = element_positions.get(parts[ei], set())
        if old_positions and not any(p in pos_map for p in old_positions):
            n_dropped += 1
            continue
        out.append("\t".join(parts) + "\n")
        n_kept += 1
    return "".join(out), n_kept, n_dropped


def build_plan(
    src_root: Path,
    dst_root: Path,
    pos_map: dict[int, int],
    rng: random.Random,
) -> tuple[list[tuple[Path, str]], dict[str, tuple[int, int, int]]]:
    """Return (plan, stats).

    plan is a list of (dst_path, content) pairs. stats maps each filled TSV's
    relative destination path to (n_kept, n_dropped, n_flips); files with no
    row-level dropping (plain lang-ID substitution only) aren't stat-tracked.
    """
    plan: list[tuple[Path, str]] = []
    stats: dict[str, tuple[int, int, int]] = {}
    src_pi = src_root / "lang_setup"
    dst_pi = dst_root / "lang_setup"

    # planar TSV — drop positions, renumber, update lang ID. Handled first
    # and separately since it needs its own remapping logic, unlike every
    # other lang_setup file.
    planar_src = next(src_pi.glob("planar_*.tsv"))
    planar_text = _transform_planar_tsv(planar_src.read_text(), pos_map, DST_LANG)
    plan.append((dst_pi / planar_src.name.replace(SRC_LANG, DST_LANG), planar_text))

    # Index element -> old positions, from the *source* planar TSV. Used both
    # for pure Element_A/Element_B pair rows below and for any other
    # lang_setup file keyed by a single Element column (e.g. a future
    # allomorphs_{lang_id}.tsv) with no position column of its own to check.
    element_positions = _build_element_positions(planar_src)

    # Every other lang_setup/*.tsv — discovered generically rather than by
    # hardcoded filename, so a new file type (like the allomorphy tables)
    # doesn't require touching this script again. diagnostics_{lang_id}.tsv
    # falls through to plain lang-ID substitution, same as before.
    for tsv in sorted(src_pi.glob("*.tsv")):
        if tsv.name.startswith("planar_"):
            continue  # already handled above
        text = tsv.read_text()
        header = text.splitlines()[0].split("\t") if text else []
        dst_path = dst_pi / tsv.name.replace(SRC_LANG, DST_LANG)
        if "Element" in header and "Position_Number" not in header:
            content, n_kept, n_dropped = _transform_element_keyed_tsv(
                text, pos_map, element_positions
            )
            content = content.replace(SRC_LANG, DST_LANG)
            plan.append((dst_path, content))
            stats[str(dst_path.relative_to(dst_root.parent))] = (n_kept, n_dropped, 0)
        else:
            plan.append((dst_path, text.replace(SRC_LANG, DST_LANG)))

    # lang_setup/*.yaml — e.g. diagnostics_{lang_id}.yaml, the coordinator-
    # facing source of truth diagnostics_{lang_id}.tsv is derived from
    # (data_dependency_schema's diagnostics_scope fact). Plain lang-ID
    # substitution, same as non-Element-keyed TSVs above -- copying the TSV
    # without also copying the YAML it's derived from would leave synth0001
    # with a derived artifact and no source of truth backing it.
    for yml in sorted(src_pi.glob("*.yaml")):
        dst_path = dst_pi / yml.name.replace(SRC_LANG, DST_LANG)
        plan.append((dst_path, yml.read_text().replace(SRC_LANG, DST_LANG)))

    # filled TSVs under class directories — drop rows, renumber, flip values
    for class_dir in sorted(src_root.iterdir()):
        if not class_dir.is_dir() or class_dir.name in ("lang_setup", "archive", ".DS_Store"):
            continue
        for tsv in sorted(class_dir.glob("*.tsv")):
            content, n_kept, n_dropped, n_flips = _transform_filled_tsv(
                tsv.read_text(), pos_map, rng, element_positions
            )
            dst_path = dst_root / class_dir.name / tsv.name
            plan.append((dst_path, content))
            stats[str(dst_path.relative_to(dst_root.parent))] = (n_kept, n_dropped, n_flips)

    return plan, stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Write files (default is dry run)")
    parser.add_argument("--clean", action="store_true",
                        help="Remove synth0001 instead of creating it")
    parser.add_argument("--full-copy", action="store_true",
                        help="Keep all positions (no random structural drop); "
                             "y/n values are still flipped")
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
    planar_src = next((src_root / "lang_setup").glob("planar_*.tsv"))
    keep_prob = 1.0 if args.full_copy else KEEP_PROB
    pos_map = _build_position_map(planar_src, rng, keep_prob=keep_prob)

    total_non_keystone = sum(
        1 for row in csv.DictReader(planar_src.open(), delimiter="\t")
        if row["Position_Name"] != "v:verbstem"
    )
    new_keystone = pos_map[next(
        int(row["Position"])
        for row in csv.DictReader(planar_src.open(), delimiter="\t")
        if row["Position_Name"] == "v:verbstem"
    )]

    n_kept_positions = len(pos_map)
    n_dropped_positions = (total_non_keystone + 1) - n_kept_positions
    mode = "full copy (no structural drop)" if args.full_copy else "random drop"
    print(f"Mode: {mode}")
    print(f"Positions: {n_kept_positions} kept of {total_non_keystone + 1}  "
          f"(dropped {n_dropped_positions})  "
          f"keystone renumbered to {new_keystone}")
    print(f"Old→new map: {pos_map}\n")

    plan, stats = build_plan(src_root, dst_root, pos_map, rng)

    for dst, content in plan:
        rel = dst.relative_to(REPO_ROOT)
        if args.apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content)
            print(f"  wrote  {rel}")
        else:
            print(f"  would write  {rel}")

    total_kept = total_dropped = total_flips = 0
    empty_files: list[str] = []
    print("\nPer-file row survival:")
    for rel, (n_kept, n_dropped, n_flips) in sorted(stats.items()):
        total_kept += n_kept
        total_dropped += n_dropped
        total_flips += n_flips
        pct = f"{100 * n_dropped / (n_kept + n_dropped):.0f}%" if (n_kept + n_dropped) else "n/a"
        flag = "  ⚠ EMPTY — no rows survived" if n_kept == 0 and n_dropped > 0 else ""
        print(f"  {rel}: {n_kept} kept, {n_dropped} dropped ({pct}), {n_flips} flips{flag}")
        if n_kept == 0 and n_dropped > 0:
            empty_files.append(rel)

    print(f"\n{'Applied' if args.apply else 'Dry run'}:"
          f" {len(plan)} files, {total_kept} rows kept, {total_dropped} rows dropped"
          f" ({total_flips} value flips among kept rows)")
    if empty_files:
        print(f"\n⚠ {len(empty_files)} file(s) ended up with zero rows — "
              f"may no longer exercise the code paths they're meant to test:")
        for f in empty_files:
            print(f"    {f}")
    if not args.apply:
        print("\nRun with --apply to write files.")


if __name__ == "__main__":
    main()
