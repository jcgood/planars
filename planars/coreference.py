from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd

from planars.spans import fmt_span, loose_span, strict_span

_KEYSTONE_NAME = "v:verbstem"
_TRAILING_COLS = {"Source", "Comments"}
_REQUIRED_CRITERIA: Set[str] = {"reflexive_allowed"}

_SNAPSHOT_CONSTRUCTIONS = frozenset({"reflexivization"})


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
    df = df[df["Language_ID"] == lang_id]
    keystone_pos: Optional[int] = None
    pos_to_name: Dict[int, str] = {}
    elem_to_positions: Dict[str, Set[int]] = {}

    def _wrap(e: str) -> str:
        return f"[{e}]" if (e.startswith("-") or e.endswith("-")) else e

    for _, row in df.iterrows():
        pos = int(row["Position"])
        pname = row["Position_Name"].strip()
        pos_to_name[pos] = pname
        if pname.lower() == _KEYSTONE_NAME:
            keystone_pos = pos
        for elem_plain in _split_elements((row.get("Elements", "") or "").strip()):
            elem_to_positions.setdefault(_wrap(elem_plain), set()).add(pos)

    if keystone_pos is None:
        raise ValueError(
            f"No keystone row (Position_Name == '{_KEYSTONE_NAME}') in planar."
        )
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

    Data model: pair rows (Element_A, Position_A, Element_B, Position_B, Direction,
    reflexive_allowed) where Element_A is the antecedent (binder) and Element_B is the
    anaphor (bindee). Only pairs with reflexive_allowed=y contribute to span computation.
    Rows with referential=n in the upstream prescreening sheet are excluded before pair
    rows are generated.

    Qualification rule (mirrors diagnostic_classes.yaml)
    -----------------------------------------------------
    Prescreening: elements are annotated referential=y (can participate as binder
    or bindee in this construction) or =n (cannot). Only referential elements generate pair rows.

    Each pair row (Element_A, Element_B) represents a potential coreference relation where
    Element_A is the antecedent (binder) and Element_B is the anaphor (bindee). The annotator
    marks reflexive_allowed=y if the construction exhibits anaphoric binding for this pair, or =n.

    Binder positions: the set of positions for Element_A across all pairs with reflexive_allowed=y.
    Bindee positions: the set of positions for Element_B across all pairs with reflexive_allowed=y.

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

    for _, row in pair_df.iterrows():
        ea = row.get("Element_A", "").strip()
        eb = row.get("Element_B", "").strip()
        allowed = row.get("reflexive_allowed", "").strip().lower()

        if allowed != "y":
            continue

        unknown = []
        if ea not in elem_to_positions:
            unknown.append(f"Element_A '{ea}' not in planar")
        if eb not in elem_to_positions:
            unknown.append(f"Element_B '{eb}' not in planar")
        if unknown:
            bad_rows.extend(unknown)
            continue

        binder_positions.update(elem_to_positions[ea])
        bindee_positions.update(elem_to_positions[eb])

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
