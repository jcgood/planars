from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from planars.spans import fmt_span, loose_span, strict_span

_KEYSTONE_NAME = "v:verbstem"
_TRAILING_COLS = {"Source", "Comments"}

# No required criteria — pair presence is the annotation.
_REQUIRED_CRITERIA: Set[str] = set()


def _load_planar_minimal(planar_path: Path, lang_id: str) -> Tuple[int, Dict[int, str]]:
    """Return (keystone_pos, pos_to_name) from a planar TSV."""
    df = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
    df = df[df["Language_ID"] == lang_id]
    keystone_pos: Optional[int] = None
    pos_to_name: Dict[int, str] = {}
    for _, row in df.iterrows():
        pos = int(row["Position"])
        pname = row["Position_Name"].strip()
        pos_to_name[pos] = pname
        if pname.lower() == _KEYSTONE_NAME:
            keystone_pos = pos
    if keystone_pos is None:
        raise ValueError(
            f"No keystone row (Position_Name == '{_KEYSTONE_NAME}') in planar."
        )
    return keystone_pos, pos_to_name


def derive_reflexivization_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    planar_path: Optional[Path] = None,
    _data=None,
) -> Dict[str, object]:
    """Derive binding domain spans from a filled reflexivization pair TSV.

    [AUTO-DERIVED: NEEDS REVIEW] Qualification rules proposed in issue #163 (Apr 2026).
    Coordinator linguistic sign-off required before promoting to stable.

    Data model: pair rows (Element_A, Position_A, Element_B, Position_B) where
    Position_A is the binder (antecedent) and Position_B is the bindee (anaphor).
    Each row asserts an attested binding relation for this construction. Rows absent
    from the table are implied non-binding for this construction.

    Used for both morphological reflexive voice (keystone is common bindee) and
    pronominal anaphora (both positions are argument positions).

    Qualification rule (mirrors diagnostic_classes.yaml)
    -----------------------------------------------------
    Binder positions: any position appearing as Position_A in at least one pair.
    Bindee positions: any position appearing as Position_B in at least one pair.

    BINDER DOMAIN (strict): contiguous expansion from keystone through binder positions.
    BINDER DOMAIN (loose):  leftmost to rightmost binder position (gaps allowed).
    BINDEE DOMAIN (strict): contiguous expansion from keystone through bindee positions.
    BINDEE DOMAIN (loose):  leftmost to rightmost bindee position (gaps allowed).

    Asymmetry (secondary output; see issue #163):
      Binder-only positions (structurally high): in binder set but not bindee set.
      Bindee-only positions (structurally low):  in bindee set but not binder set.
      Shared positions (either role):            in both sets.

    Args:
        tsv_path:    Path to pair TSV (Element_A, Position_A, Element_B, Position_B, ...).
        strict:      If True, raise on missing or invalid Position_A/Position_B values.
        planar_path: Optional explicit path to planar TSV. If None, derived from tsv_path.
        _data:       (pair_df, keystone_pos, pos_to_name) for Colab/sheets path.

    Returns dict with:
        keystone_position, position_number_to_name, pair_table, missing_data,
        binder_positions, bindee_positions,
        binder_strict_span, binder_loose_span,
        bindee_strict_span, bindee_loose_span.
    """
    if _data is not None:
        pair_df, keystone_pos, pos_to_name = _data
    else:
        lang_id = tsv_path.parent.parent.name
        if planar_path is None:
            planar_path = (
                tsv_path.parent.parent / "lang_setup" / f"planar_{lang_id}.tsv"
            )
        keystone_pos, pos_to_name = _load_planar_minimal(planar_path, lang_id)
        pair_df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)

    binder_positions: Set[int] = set()
    bindee_positions: Set[int] = set()
    bad_rows: List[str] = []
    for _, row in pair_df.iterrows():
        ea = row.get("Element_A", "").strip()
        pa_raw = row.get("Position_A", "").strip()
        eb = row.get("Element_B", "").strip()
        pb_raw = row.get("Position_B", "").strip()

        if not pa_raw or not pb_raw:
            bad_rows.append(
                f"{ea or '?'} @ {pa_raw or '?'} → {eb or '?'} @ {pb_raw or '?'}"
            )
            continue
        try:
            binder_positions.add(int(pa_raw))
            bindee_positions.add(int(pb_raw))
        except ValueError:
            bad_rows.append(f"{ea} @ {pa_raw} → {eb} @ {pb_raw}")

    if bad_rows and strict:
        raise ValueError(f"Missing or invalid position values: {bad_rows}")

    missing_data: Dict[str, list] = {}
    if bad_rows:
        missing_data["position_values"] = bad_rows

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
    """Format a derive_reflexivization_domains result as a human-readable string."""
    p = result["position_number_to_name"]
    fmt = lambda span: fmt_span(span, p)

    lines = []
    missing = result.get("missing_data", {})
    if missing:
        lines.append("NOTE: Some pairs have missing or invalid position values.")
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
derive = derive_reflexivization_domains
