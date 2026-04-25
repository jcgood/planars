from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from planars.spans import fmt_span, strict_span

_REQUIRED_CRITERIA = {"scopal"}
_KEYSTONE_NAME = "v:verbstem"
_TRAILING_COLS = {"Source", "Comments"}

# Only the pair-row (general) construction can be derived by this module.
# element_prescreening uses a different schema (Element, scopal) and is not
# a valid input to derive_nonpermutability_domains.
_SNAPSHOT_CONSTRUCTIONS = frozenset({"general"})


# ---------------------------------------------------------------------------
# Planar helpers
# ---------------------------------------------------------------------------

def _split_elements(raw: str) -> List[str]:
    """Brace-aware comma split for element strings."""
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


def _load_planar(planar_path: Path, lang_id: str):
    """Read planar TSV; return planar data structures needed for span derivation.

    Returns:
        keystone_pos     : int
        pos_to_name      : {pos: name}
        pos_type         : {pos: "Slot"|"Zone"}
        pos_to_elements  : {pos: [elem, ...]}  (keystone excluded)
        elem_to_positions: {elem: set(pos)}    (keystone excluded)
        all_positions    : set of all position numbers (keystone included)
    """
    df = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
    df = df[df["Language_ID"] == lang_id]

    pos_to_name: Dict[int, str] = {}
    pos_type: Dict[int, str] = {}
    pos_to_elements: Dict[int, List[str]] = {}
    elem_to_positions: Dict[str, Set[int]] = {}
    keystone_pos: Optional[int] = None

    for _, row in df.iterrows():
        pos = int(row["Position"])
        pname = row["Position_Name"].strip()
        ptype = row["Position_Type"].strip()
        pos_to_name[pos] = pname
        pos_type[pos] = ptype

        raw_elements = _split_elements(row.get("Elements", "") or "")
        # Apply the same bracket-wrapping used in Google Sheets to match
        # element names in imported TSVs (element_prescreening, general).
        elements = [
            f"[{e}]" if (e.startswith("-") or e.endswith("-")) else e
            for e in raw_elements
        ]

        if pname.lower() == _KEYSTONE_NAME:
            keystone_pos = pos
            continue

        pos_to_elements[pos] = elements
        for elem in elements:
            elem_to_positions.setdefault(elem, set()).add(pos)

    if keystone_pos is None:
        raise ValueError(f"No keystone row (Position_Name == '{_KEYSTONE_NAME}') in planar.")

    return keystone_pos, pos_to_name, pos_type, pos_to_elements, elem_to_positions


def structurally_expected_pair_elements(planar_path: Path, lang_id: str) -> Set[str]:
    """Return elements that can appear in at least one nonpermutability pair.

    An element is expected if it would be included in at least one pair by
    _build_nonperm_pairs (i.e., it is not excluded because it shares only a
    same Slot position with every other element or has fixed structural order
    with all others). Uses bracket-wrapped names to match imported TSV format.
    """
    _, _, pos_type, _, elem_to_positions = _load_planar(planar_path, lang_id)
    all_elems = list(elem_to_positions.keys())
    expected: Set[str] = set()
    for i, ea in enumerate(all_elems):
        for eb in all_elems[i + 1:]:
            pa, pb = elem_to_positions[ea], elem_to_positions[eb]
            shared = pa & pb
            if any(pos_type.get(p) == "Zone" for p in shared):
                expected.add(ea); expected.add(eb)
            elif max(pa) < min(pb) or max(pb) < min(pa):
                continue
            elif pa == pb and all(pos_type.get(p) == "Slot" for p in pa):
                continue
            else:
                expected.add(ea); expected.add(eb)
    return expected


# ---------------------------------------------------------------------------
# Maximal flexible span computation
# ---------------------------------------------------------------------------

def _maximal_flexible_span(
    all_positions: Set[int],
    free_perm_positions: Set[int],
    keystone_pos: int,
) -> Tuple[int, int]:
    """Largest contiguous span from keystone where edge positions are not free-permutable.

    Walks outward through all positions (including free-permutable ones), stops only
    at structural gaps. The edge of the returned span is always a non-free-permutable
    position. If all positions on one side are free-permutable, that edge stays at
    the keystone.
    """
    left_edge = keystone_pos
    prev = keystone_pos
    for pos in sorted([p for p in all_positions if p < keystone_pos], reverse=True):
        if pos != prev - 1:
            break
        prev = pos
        if pos not in free_perm_positions:
            left_edge = pos

    right_edge = keystone_pos
    prev = keystone_pos
    for pos in sorted([p for p in all_positions if p > keystone_pos]):
        if pos != prev + 1:
            break
        prev = pos
        if pos not in free_perm_positions:
            right_edge = pos

    return left_edge, right_edge


# ---------------------------------------------------------------------------
# Main derive function
# ---------------------------------------------------------------------------

def derive_nonpermutability_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    planar_path: Optional[Path] = None,
    _data=None,
) -> Dict[str, object]:
    """Derive non-permutability spans from a filled nonpermutability pair TSV.

    [AUTO-DERIVED: NEEDS REVIEW] Qualification rules designed in issue #116 (Apr 2026).
    Verify before use for annotation or analysis.

    Data model: pair rows (Element_A, Element_B, scopal) from Stage 2 of the
    two-stage annotation workflow. Stage 1 (element_prescreening) filters elements with
    scopal=n (no meaningful variable ordering) before Stage 2 is generated.
    Each pair row asserts that the two elements can be variably ordered.
    Pairs not listed are assumed fixed-order by structure.
    scopal=y means variable order carries an obligatory scope difference;
    scopal=n means freely variable (no meaning difference).

    Qualification rule (mirrors diagnostic_classes.yaml)
    -----------------------------------------------------
    Three span types (all strict — non-permutability domains are inherently
    contiguous). Qualification is evaluated per-position w.r.t. the keystone anchor.

    STRICT NON-PERMUTABLE SPAN (structurally derived; no annotation required):
      A position qualifies iff:
        (1) It is a Slot (Zones are always excluded).
        (2) All elements at that position appear in only one position in the planar
            (multi-slot elements have structurally variable order, so they cannot
            anchor a strictly fixed chain).
      The span is the largest contiguous chain of qualifying positions from the
      keystone outward; the first gap or non-qualifying position halts expansion.

    FREE-PERMUTABLE POSITION (blocking condition; derived from annotation):
      A position is free-permutable if ANY element at that position appears in a
      pair with scopal=n (freely variable order, no scope difference).
      An element appearing in both scopal=n and scopal=y pairs is treated as
      partially non-permutable; its position is free-permutable for the minimal
      span but may be interior in the maximal span.

    MINIMAL FLEXIBLE NON-PERMUTABLE SPAN:
      Extends the strict span outward through additional contiguous positions that
      are not free-permutable. No free-permutable positions appear anywhere in
      the span. Computed as strict_span(all_positions - free_permutable_positions).

    MAXIMAL FLEXIBLE NON-PERMUTABLE SPAN:
      Extends the minimal span outward through free-permutable interior positions,
      as long as the outermost (edge) positions of the span are not free-permutable.
      Computed by walking outward from keystone through all positions (including
      free-permutable), stopping only at structural gaps, and recording the outermost
      non-free-permutable position as the span edge.

    Args:
        tsv_path:    Path to the pair TSV (Element_A, Element_B, scopal, ...).
        strict:      If True, raise on missing scopal values; otherwise leave blanks.
        planar_path: Optional explicit path to planar TSV. If None, derived from
                     tsv_path: coded_data/{lang_id}/lang_setup/planar_{lang_id}.tsv.
        _data:       Not yet supported for this module (pair-row sheets require a
                     separate loading path). Will raise NotImplementedError.

    Returns dict with:
        keystone_position, position_number_to_name, pair_table, missing_data,
        strict_positions, free_permutable_positions,
        strict_span, minimal_flexible_span, maximal_flexible_span.
    """
    stale_dependent: Optional[str] = None

    if _data is not None:
        # _data = (pair_df, keystone_pos, pos_to_name, pos_type,
        #          pos_to_elements, elem_to_positions)
        # Used for synthetic testing; live-sheet loading is not yet supported.
        pair_df, keystone_pos, pos_to_name, pos_type, pos_to_elements, elem_to_positions = _data
    else:
        lang_id = tsv_path.parent.parent.name
        if planar_path is None:
            planar_path = tsv_path.parent.parent / "lang_setup" / f"planar_{lang_id}.tsv"
        keystone_pos, pos_to_name, pos_type, pos_to_elements, elem_to_positions = \
            _load_planar(planar_path, lang_id)
        pair_df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)

        # Staleness check: compare element sets against element_prescreening.tsv.
        prescreening_path = tsv_path.parent / "element_prescreening.tsv"
        if prescreening_path.exists():
            pre_df = pd.read_csv(prescreening_path, sep="\t", dtype=str, keep_default_na=False)
            if "Element" in pre_df.columns and "scopal" in pre_df.columns:
                # Elements expected in pairs: structurally reachable by the
                # pair algorithm (i.e., not excluded for being same-Slot only).
                structurally_expected: Set[str] = set()
                all_elems = list(elem_to_positions.keys())
                for i, ea in enumerate(all_elems):
                    for eb in all_elems[i + 1:]:
                        pa, pb = elem_to_positions[ea], elem_to_positions[eb]
                        shared = pa & pb
                        if any(pos_type.get(p) == "Zone" for p in shared):
                            structurally_expected.add(ea)
                            structurally_expected.add(eb)
                        elif max(pa) < min(pb) or max(pb) < min(pa):
                            continue
                        elif pa == pb and all(pos_type.get(p) == "Slot" for p in pa):
                            continue
                        else:
                            structurally_expected.add(ea)
                            structurally_expected.add(eb)

                source_set = {
                    r["Element"].strip()
                    for _, r in pre_df.iterrows()
                    if r.get("scopal", "").strip() not in ("n", "na")
                } & structurally_expected
                dep_set = set()
                for col in ("Element_A", "Element_B"):
                    if col in pair_df.columns:
                        dep_set.update(pair_df[col].str.strip())
                dep_set.discard("")
                if dep_set and source_set != dep_set:
                    stale_dependent = (
                        "general.tsv is out of sync with element_prescreening.tsv — "
                        "run python -m coding generate-sheets --lang " + lang_id
                    )

    all_positions = set(pos_to_name.keys())

    trailing = _TRAILING_COLS
    param_cols = [c for c in pair_df.columns if c not in {"Element_A", "Element_B"} and c not in trailing]

    missing_data: Dict[str, list] = {}
    if not strict:
        for col in param_cols:
            blanks = [
                f"{r['Element_A']} × {r['Element_B']}"
                for _, r in pair_df.iterrows()
                if r.get(col, "") == ""
            ]
            if blanks:
                missing_data[col] = blanks
    elif "scopal" in param_cols:
        blank_pairs = [
            f"{r['Element_A']} × {r['Element_B']}"
            for _, r in pair_df.iterrows()
            if r.get("scopal", "") == ""
        ]
        if blank_pairs:
            raise ValueError(f"Missing scopal values for: {blank_pairs}")

    # Build pair lookup: element → frozenset of (partner, scopal) tuples.
    elem_scopal: Dict[str, list] = {}
    for _, row in pair_df.iterrows():
        ea, eb, sc = row.get("Element_A", ""), row.get("Element_B", ""), row.get("scopal", "")
        if ea:
            elem_scopal.setdefault(ea, []).append(sc)
        if eb:
            elem_scopal.setdefault(eb, []).append(sc)

    # Free-permutable elements: appear in any scopal=n pair.
    free_perm_elems: Set[str] = {
        elem for elem, scopals in elem_scopal.items() if "n" in scopals
    }

    # Free-permutable positions: any element at the position is free-permutable.
    non_keystone_positions = set(pos_to_elements.keys())
    free_perm_positions: Set[int] = {
        pos for pos in non_keystone_positions
        if any(e in free_perm_elems for e in pos_to_elements.get(pos, []))
    }

    # Strict non-permutable positions (structural).
    # Condition 1: Slot. Condition 2: all elements appear in exactly one position.
    strict_positions: Set[int] = {
        pos for pos in non_keystone_positions
        if pos_type.get(pos) == "Slot"
        and all(len(elem_to_positions.get(e, set())) == 1 for e in pos_to_elements.get(pos, []))
    }

    # Spans.
    strict_span_result = strict_span(strict_positions, keystone_pos)

    # Minimal flexible: strict span extended through non-free-permutable positions.
    minimal_flex_qual = non_keystone_positions - free_perm_positions
    minimal_flex_span_result = strict_span(minimal_flex_qual, keystone_pos)

    # Maximal flexible: can pass through free-permutable interior positions.
    maximal_flex_span_result = _maximal_flexible_span(
        all_positions, free_perm_positions, keystone_pos
    )

    return {
        "keystone_position":           keystone_pos,
        "position_number_to_name":     pos_to_name,
        "pair_table":                  pair_df,
        "missing_data":                missing_data,
        "strict_positions":            sorted(strict_positions),
        "free_permutable_positions":   sorted(free_perm_positions),
        "strict_span":                 strict_span_result,
        "minimal_flexible_span":       minimal_flex_span_result,
        "maximal_flexible_span":       maximal_flex_span_result,
        "stale_dependent_construction": stale_dependent,
    }


def format_result(result: Dict[str, object]) -> str:
    """Format a derive_nonpermutability_domains result dict as a human-readable string."""
    p = result["position_number_to_name"]
    fmt = lambda span: fmt_span(span, p)
    lines = []

    stale = result.get("stale_dependent_construction")
    if stale:
        lines.append(f"WARNING: {stale}")
        lines.append("")

    missing = result.get("missing_data", {})
    if missing:
        lines.append("NOTE: Some pairs have unannotated scopal values.")
        for col, pairs in missing.items():
            preview = pairs[:5]
            suffix = f" … ({len(pairs)} total)" if len(pairs) > 5 else ""
            lines.append(f"  {col}: {preview}{suffix}")
        lines.append("")

    lines += [
        f"Keystone position: {result['keystone_position']} ({p.get(result['keystone_position'], '?')})",
        "",
        f"Strictly non-permutable positions (structural): {result['strict_positions']}",
        f"Free-permutable positions (scopal=n pairs):     {result['free_permutable_positions']}",
        "",
        f"Strict non-permutable span:           {fmt(result['strict_span'])}",
        f"Minimal flexible non-permutable span: {fmt(result['minimal_flexible_span'])}",
        f"Maximal flexible non-permutable span: {fmt(result['maximal_flexible_span'])}",
    ]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py.
derive = derive_nonpermutability_domains
