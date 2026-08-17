from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd
import yaml
from importlib.resources import files as _res_files
from pandera.errors import SchemaError

from planars.contracts import (
    CHECK_COREFERENCE_POSITION_INTEGER,
    coreference_planar_rows_schema,
    coreference_position_is_integer,
)
from planars.spans import fmt_span, loose_span, strict_span

_KEYSTONE_NAME = "v:verbstem"
_TRAILING_COLS = {"Source", "Comments"}
_REQUIRED_CRITERIA: Set[str] = {"reflexive_allowed"}

_SNAPSHOT_CONSTRUCTIONS = frozenset({"reflexivization", "pronominalization", "np_reference"})

_PAIR_CRITERIA = {"reflexive_allowed", "pronoun_allowed", "np_allowed"}

# Which criterion each pair construction is about. Source of truth is
# schemas/diagnostic_classes.yaml's per-construction `criterion` field; this
# map is derived from it at import time, not restated.
_CONSTRUCTION_CRITERION: Dict[str, str] = {}


def _construction_criterion_map() -> Dict[str, str]:
    """{construction_name: criterion} for coreference, from the schema."""
    global _CONSTRUCTION_CRITERION
    if not _CONSTRUCTION_CRITERION:
        text = (_res_files("schemas")
                .joinpath("diagnostic_classes.yaml").read_text(encoding="utf-8"))
        classes = {c["name"]: c for c in (yaml.safe_load(text) or {}).get("classes", [])}
        _CONSTRUCTION_CRITERION = {
            con["name"]: con["criterion"]
            for con in (classes.get("coreference", {}).get("constructions") or [])
            if isinstance(con, dict) and "criterion" in con
        }
    return _CONSTRUCTION_CRITERION


def _criterion_column(tsv_path: Path, pair_cols: Set[str]) -> str:
    """Return the criterion column this construction's judgments live in.

    The construction is what decides: ``reflexivization.tsv`` is about
    ``reflexive_allowed`` whatever else the sheet happens to carry. Identity
    comes from the filename (which encodes the construction, per the project's
    ``{construction}.tsv`` convention) resolved through
    ``diagnostic_classes.yaml``.

    This used to be ``next(c for c in _PAIR_CRITERIA if c in pair_cols)`` —
    pick whichever of the three criterion columns is present. That is correct
    only while a tab carries exactly one of them. When a tab carries all three
    (as synth0001's coreference tabs did after 2026-08-02's import), ``next()``
    over a **set** returns an arbitrary member, and Python randomises string
    hashing per process — so the same file analysed twice gave different
    answers, silently. Two of the three snapshots failed on any given run, and
    *which* two changed between runs.

    Falls back to the single criterion column present (the one-criterion-per-tab
    layout), then to ``reflexive_allowed``, so a tab whose name is not a known
    construction still behaves as before.
    """
    construction = tsv_path.stem
    declared = _construction_criterion_map().get(construction)
    if declared and declared in pair_cols:
        return declared
    present = sorted(_PAIR_CRITERIA & pair_cols)
    if len(present) == 1:
        return present[0]
    if declared:
        return declared
    # Sorted, so that an ambiguous tab is at least deterministic rather than
    # randomised — a wrong-but-stable answer is debuggable; a wrong-and-shifting
    # one is what made this bug invisible for as long as it was.
    return present[0] if present else "reflexive_allowed"


def _split_elements(raw: str) -> List[str]:
    """Split comma-separated elements string, ignoring commas inside braces."""
    parts: List[str] = []
    current: List[str] = []
    depth = 0
    for ch in raw:
        if ch == "{":
            depth += 1
            current.append(ch)
        elif ch == "}":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def _load_planar_for_coreference(
    planar_path: Path, lang_id: str
):
    """Return (keystone_pos, pos_to_name, elem_to_positions) from a planar TSV.

    The planar TSV has one row per position with a comma-separated Elements column.
    """
    df = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)

    # Column presence stays a plain check, ahead of everything else that
    # assumes these columns exist -- without it, a missing column (e.g. a
    # typo'd header) doesn't crash here, it silently makes every row look
    # like it belongs to no language via row.get()'s "" fallback. See
    # contracts.py's module docstring, section 2.
    required_cols = {"Language_ID", "Position", "Position_Name", "Elements"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required column(s): {sorted(missing)}")

    df = df[df["Language_ID"] == lang_id].copy()
    for col in ("Position", "Position_Name", "Elements"):
        df[col] = df[col].astype(str).str.strip()

    try:
        coreference_planar_rows_schema().validate(df)
    except SchemaError as e:
        if e.check.name == CHECK_COREFERENCE_POSITION_INTEGER:
            bad = df.loc[~coreference_position_is_integer(df["Position"]), "Position"].iloc[0]
            raise ValueError(f"{e.check.error} Found: '{bad}'.") from e
        raise ValueError(e.check.error) from e

    pos_to_name: Dict[int, str] = {}
    elem_to_positions: Dict[str, Set[int]] = {}
    keystone_pos: Optional[int] = None

    def _wrap(e: str) -> str:
        return f"[{e}]" if (e.startswith("-") or e.endswith("-")) else e

    for _, row in df.iterrows():
        pos = int(row["Position"])
        pname = row["Position_Name"]
        pos_to_name[pos] = pname
        if pname.lower() == _KEYSTONE_NAME:
            keystone_pos = pos
        for elem_plain in _split_elements(row["Elements"]):
            elem_to_positions.setdefault(_wrap(elem_plain), set()).add(pos)

    return keystone_pos, pos_to_name, elem_to_positions


def derive_coreference_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    planar_path: Optional[Path] = None,
    _data=None,
) -> Dict[str, object]:
    """Derive binding domain spans from a filled coreference pair TSV.

    [AUTO-DERIVED: NEEDS REVIEW] Qualification rules proposed in issue #163 (Apr 2026).
    Coordinator linguistic sign-off required before promoting to stable.

    Data model: pair rows (Element_A, Position_A, Position_B, Direction,
    reflexive_allowed) where Element_A is the antecedent (binder) at Position_A, and
    Position_B is the structural position of the anaphor (bindee). Only pairs with
    reflexive_allowed=y contribute to span computation. Rows with referential=n in the
    upstream prescreening sheet are excluded before pair rows are generated.

    Qualification rule (mirrors diagnostic_classes.yaml)
    -----------------------------------------------------
    Prescreening: elements are annotated referential=y (can participate as binder
    or bindee in this construction) or =n (cannot). Only referential elements generate pair rows.

    Each pair row (Element_A, Position_A, Position_B) represents a potential coreference
    relation where Element_A is the antecedent (binder) at Position_A, and Position_B is
    the structural position of the anaphor (bindee). The annotator marks reflexive_allowed=y
    if the construction exhibits anaphoric binding for this pair, or =n.

    Binder positions: the set of positions for Element_A across all pairs with reflexive_allowed=y.
    Bindee positions: the set of Position_B values across all pairs with reflexive_allowed=y.

    BINDER DOMAIN (strict): contiguous expansion from keystone through binder positions.
    BINDER DOMAIN (loose):  leftmost to rightmost binder position (gaps allowed).
    BINDEE DOMAIN (strict): contiguous expansion from keystone through bindee positions.
    BINDEE DOMAIN (loose):  leftmost to rightmost bindee position (gaps allowed).

    Asymmetry (secondary output):
      Binder-only positions (structurally high): appear as binder position but not bindee position.
      Bindee-only positions (structurally low):  appear as bindee position but not binder position.
      Shared positions (either role):            appear in both sets.
    The asymmetry between binder-only and bindee-only positions approximates c-command
    without presupposing tree structure (see issue #163).

    Args:
        tsv_path:    Path to pair TSV (Element_A, ..., reflexive_allowed, ...).
        strict:      If True, raise on unknown elements.
        planar_path: Optional explicit path to planar TSV. If None, derived from tsv_path.
        _data:       (pair_df, keystone_pos, pos_to_name, elem_to_positions) for Colab.

    Returns dict with:
        keystone_position, position_number_to_name, pair_table, missing_data,
        binder_positions, bindee_positions,
        binder_strict_span, binder_loose_span,
        bindee_strict_span, bindee_loose_span.
    """
    if _data is not None:
        pair_df, keystone_pos, pos_to_name, elem_to_positions = _data
    else:
        lang_id = tsv_path.parent.parent.name
        if planar_path is None:
            planar_path = (
                tsv_path.parent.parent / "lang_setup" / f"planar_{lang_id}.tsv"
            )
        keystone_pos, pos_to_name, elem_to_positions = _load_planar_for_coreference(
            planar_path, lang_id
        )
        pair_df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)

    binder_positions: Set[int] = set()
    bindee_positions: Set[int] = set()
    bad_rows: List[str] = []

    pair_cols = set(pair_df.columns) if hasattr(pair_df, "columns") else set()
    criterion_col = _criterion_column(tsv_path, pair_cols)

    # Column presence stays a plain check, ahead of the loop below -- without
    # it, a missing column doesn't crash, it silently makes every row look
    # unknown via row.get()'s "" fallback, producing a wrong-but-plausible
    # empty result instead of an error. See contracts.py's module docstring,
    # section 2.
    required_pair_cols = {"Element_A", "Position_B", criterion_col}
    missing_pair_cols = required_pair_cols - pair_cols
    if missing_pair_cols:
        raise ValueError(f"Missing required column(s): {sorted(missing_pair_cols)}")

    for _, row in pair_df.iterrows():
        ea      = row.get("Element_A", "").strip()
        pos_b_s = row.get("Position_B", "").strip()
        allowed = row.get(criterion_col, "").strip().lower()

        if allowed != "y":
            continue

        if ea not in elem_to_positions:
            bad_rows.append(f"Element_A '{ea}' not in planar")
            continue

        try:
            pos_b_num = int(pos_b_s.split()[0])
        except (ValueError, IndexError):
            bad_rows.append(f"Could not parse Position_B '{pos_b_s}'")
            continue

        binder_positions.update(elem_to_positions[ea])
        bindee_positions.add(pos_b_num)

    if bad_rows and strict:
        raise ValueError(f"Unknown elements in pair rows: {bad_rows}")

    missing_data: Dict[str, list] = {}
    if bad_rows:
        missing_data["unknown_elements"] = bad_rows

    binder_strict = strict_span(binder_positions, keystone_pos)
    binder_loose  = loose_span(binder_positions, keystone_pos)
    bindee_strict = strict_span(bindee_positions, keystone_pos)
    bindee_loose  = loose_span(bindee_positions, keystone_pos)

    return {
        "keystone_position":        keystone_pos,
        "position_number_to_name":  pos_to_name,
        "pair_table":               pair_df,
        "missing_data":             missing_data,
        "binder_positions":         sorted(binder_positions),
        "bindee_positions":         sorted(bindee_positions),
        "binder_strict_span":       binder_strict,
        "binder_loose_span":        binder_loose,
        "bindee_strict_span":       bindee_strict,
        "bindee_loose_span":        bindee_loose,
    }


def format_result(result: Dict[str, object]) -> str:
    """Format a derive_coreference_domains result as a human-readable string."""
    p = result["position_number_to_name"]
    fmt = lambda span: fmt_span(span, p)

    lines = []
    missing = result.get("missing_data", {})
    if missing:
        lines.append("NOTE: Some pairs have unknown elements.")
        for col, items in missing.items():
            preview = items[:5]
            suffix = f" … ({len(items)} total)" if len(items) > 5 else ""
            lines.append(f"  {col}: {preview}{suffix}")
        lines.append("")

    binder_set = set(result["binder_positions"])
    bindee_set = set(result["bindee_positions"])
    binder_only = sorted(binder_set - bindee_set)
    bindee_only = sorted(bindee_set - binder_set)
    shared      = sorted(binder_set & bindee_set)

    lines += [
        f"Keystone position: {result['keystone_position']}"
        f" ({p.get(result['keystone_position'], '?')})",
        "",
        f"Binder positions (antecedent): {result['binder_positions']}",
        f"Bindee positions (anaphor):    {result['bindee_positions']}",
        "",
        f"Binder-only positions (structurally high): {binder_only}",
        f"Bindee-only positions (structurally low):  {bindee_only}",
        f"Shared positions (either role):            {shared}",
        "",
        f"Binder domain (strict): {fmt(result['binder_strict_span'])}",
        f"Binder domain (loose):  {fmt(result['binder_loose_span'])}",
        f"Bindee domain (strict): {fmt(result['bindee_strict_span'])}",
        f"Bindee domain (loose):  {fmt(result['bindee_loose_span'])}",
    ]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py.
derive = derive_coreference_domains
