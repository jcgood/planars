"""Biuniqueness deviation domains (issue #254; replaces biuniqueness_exponence).

Biuniqueness is a one-to-one match between form and meaning. Tallman &
Auderset (2023) list six ways it can fail (#238). Four of them can be told
apart from one set of facts -- which forms a morpheme has, where each sits,
and what conditions it -- so this one class covers all four:

  extended_exponence    one meaning, several pieces at once (be ... -ing)
  allomorphy            one meaning, different forms by context (do/does)
  cumulative_exponence  one form, two meanings fused (went = go+PAST)
  zero_morph            a meaning with no form of its own (cut, past)

Syncretism and empty morphs are registered in diagnostic_classes.yaml but not
derived here (deferred, per #238).

Input: two TSVs of the class, imported from its sheet like any annotation --
morphemes.tsv (one row per morpheme) and morphs.tsv (one row per form at a
position) -- plus the language's planar TSV for position numbers. The
deviation type is derived from the form rows, never annotated.

[AUTO-DERIVED: NEEDS REVIEW] Span definition and type rules designed with the
coordinator on 2026-10-11 (#254); Adam's review required before promotion.

Span rule (mirrors diagnostic_classes.yaml)
-------------------------------------------
Each form row of morphs.tsv with occurs_here=y gets a deviation type, derived
in this order: if its morpheme's forms_relation is co-occur, the type is
extended_exponence; otherwise a row whose conditioning_type is phonological
is excluded (predictable alternation is not a deviation); a row whose
conditioning_features is elsewhere is the elsewhere form and carries no
deviation of its own; trigger_filled=y gives allomorphy; trigger_filled=n
gives zero_morph when the form is identical to the elsewhere form of the same
morpheme at the same position, and cumulative_exponence otherwise. A row the
rules cannot place is an error, never a silent default.

A domain is one morpheme at one position for one deviation type (for
extended_exponence, one morpheme across all the positions of its pieces). Its
positions are that position plus every conditioned_by position of its forms
of that type. Two spans per domain: the raw span, leftmost to rightmost of
those positions, which contains the keystone only if it falls inside; and the
keystone-anchored span, the same positions expanded to include the keystone,
so it can be compared with every other class. No strict/loose or
partial/complete variants.
"""
from __future__ import annotations

from importlib.resources import files as _res_files
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
import yaml

from planars.coreference import _load_planar_for_coreference
from planars.position_cells import as_names
from planars.spans import fmt_span, loose_span

CLASS_NAME = "biuniqueness_deviations"

# Criteria this module reads (check-codebook check 1: each must be defined in
# diagnostic_criteria.yaml).
_REQUIRED_CRITERIA = {
    "forms_relation", "occurs_here", "conditioning_type",
    "conditioning_features", "conditioned_by", "trigger_filled",
}


def _tab_chain() -> Tuple[str, str, str]:
    """The class's three tabs in generation order, read from its depends_on
    chain in schemas/diagnostic_classes.yaml: the one with no depends_on, the
    one depending on it, the one depending on that. Raises ValueError unless
    that chain is exactly the class's constructions."""
    text = _res_files("schemas").joinpath("diagnostic_classes.yaml").read_text(encoding="utf-8")
    cls = next((c for c in (yaml.safe_load(text) or {}).get("classes", [])
                if c.get("name") == CLASS_NAME), None)
    if cls is None:
        raise ValueError(f"{CLASS_NAME} is not in schemas/diagnostic_classes.yaml")
    cons = cls.get("constructions", [])
    step = [c["name"] for c in cons if not c.get("depends_on")]
    chain = list(step)
    while len(step) == 1:
        step = [c["name"] for c in cons if c.get("depends_on") == chain[-1]]
        chain += step
    if len(chain) != 3 or len(chain) != len(cons):
        raise ValueError(
            f"{CLASS_NAME}'s constructions in schemas/diagnostic_classes.yaml must form "
            f"one depends_on chain of three tabs (elements -> morphemes -> morphs); "
            f"found {[c['name'] for c in cons]} chained as {chain}.")
    return chain[0], chain[1], chain[2]


# The tab names, never typed elsewhere: renaming a tab is a schema edit only.
# derive reads only the morphs tab (it finds the morphemes tab's TSV beside
# it); elements and morphemes are feeder tabs (`produces_spans: false`, read
# by planars.reports.span_constructions).
ELEMENTS_TAB, MORPHEMES_TAB, MORPHS_TAB = _tab_chain()

# The derived deviation types, in the order they are reported. Must equal the
# `derived: true` entries of the class's deviation_types registry in
# schemas/diagnostic_classes.yaml (a test holds the two together).
DERIVED_TYPES = ("extended_exponence", "allomorphy", "cumulative_exponence", "zero_morph")

ELSEWHERE = "elsewhere"
_PHONOLOGICAL = "phonological"


def classify_form(row: Dict[str, str], forms_relation: str,
                  elsewhere_form: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Return (deviation_type, problem) for one occurring form row.

    deviation_type is one of DERIVED_TYPES, or None for a form that carries no
    deviation (phonologically conditioned, or the elsewhere form). problem is
    a message when the row cannot be placed; then deviation_type is None.
    """
    if forms_relation == "co-occur":
        return "extended_exponence", None
    if forms_relation != "alternate":
        return None, f"forms_relation is {forms_relation!r}, expected alternate or co-occur"
    if row["conditioning_type"] == _PHONOLOGICAL:
        return None, None
    if row["conditioning_features"] == ELSEWHERE:
        return None, None
    trigger = row["trigger_filled"]
    if trigger == "y":
        return "allomorphy", None
    if trigger == "n":
        if elsewhere_form is not None and row["Form"] == elsewhere_form:
            return "zero_morph", None
        return "cumulative_exponence", None
    return None, f"trigger_filled is {trigger!r}, expected y or n"


def _load_tables(morphs_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    morphemes_path = morphs_path.parent / f"{MORPHEMES_TAB}.tsv"
    morphemes = pd.read_csv(morphemes_path, sep="\t", dtype=str, keep_default_na=False)
    morphs = pd.read_csv(morphs_path, sep="\t", dtype=str, keep_default_na=False)
    return morphemes, morphs


def derive_biuniqueness_deviations_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    planar_path: Optional[Path] = None,
    _data=None,
) -> Dict[str, object]:
    """Derive biuniqueness deviation domains from a class's morphs TSV.

    Args:
        tsv_path:    path to coded_data/{lang}/biuniqueness_deviations/morphs.tsv;
                     morphemes.tsv is read from the same folder.
        strict:      if True, raise on any row the rules cannot place or any
                     position the planar does not have; if False, collect
                     them in missing_data and skip the row.
        planar_path: explicit planar TSV; derived from tsv_path if None.
        _data:       (morphemes_df, morphs_df, keystone_pos, pos_to_name), for
                     callers that already hold the tables (Colab).

    Returns a dict with keystone_position, position_number_to_name,
    form_table (morphs rows with a derived `deviation_type` column),
    missing_data, and domains: a list of dicts with morpheme, position_name
    (None for extended_exponence, which spans all its pieces), type,
    positions, raw_span and anchored_span.
    """
    if _data is not None:
        morphemes, morphs, keystone_pos, pos_to_name = _data
    else:
        lang_id = tsv_path.parent.parent.name
        if planar_path is None:
            planar_path = tsv_path.parent.parent / "lang_setup" / f"planar_{lang_id}.tsv"
        keystone_pos, pos_to_name, _ = _load_planar_for_coreference(planar_path, lang_id)
        morphemes, morphs = _load_tables(tsv_path)

    name_to_pos = {name: num for num, name in pos_to_name.items()}
    relation = {r["Morpheme"]: r.get("forms_relation", "").strip().lower()
                for _, r in morphemes.iterrows()}

    problems: List[str] = []

    def problem(msg: str) -> None:
        if strict:
            raise ValueError(msg)
        problems.append(msg)

    rows = []
    for _, r in morphs.iterrows():
        row = {k: str(v).strip() for k, v in r.items()}
        for col in ("occurs_here", "conditioning_type", "conditioning_features", "trigger_filled"):
            row[col] = row.get(col, "").lower()
        rows.append(row)

    # The elsewhere form of each (morpheme, position), for the zero_morph test.
    elsewhere: Dict[Tuple[str, str], str] = {}
    for row in rows:
        if row["occurs_here"] == "y" and row["conditioning_features"] == ELSEWHERE:
            elsewhere[(row["Morpheme"], row["Position_Name"])] = row["Form"]

    # (morpheme, position_or_None, type) -> set of position numbers
    domain_positions: Dict[Tuple[str, Optional[str], str], Set[int]] = {}
    types: List[str] = []
    for row in rows:
        morpheme, pos_name = row["Morpheme"], row["Position_Name"]
        where = f"{morpheme} / {row.get('Form', '')} at {pos_name}"
        if row["occurs_here"] != "y":
            types.append("" if row["occurs_here"] == "n" else "unplaced")
            if row["occurs_here"] != "n":
                problem(f"{where}: occurs_here is {row['occurs_here']!r}, expected y or n")
            continue
        if morpheme not in relation:
            problem(f"{where}: morpheme not listed in morphemes.tsv")
            types.append("unplaced")
            continue
        if pos_name not in name_to_pos:
            problem(f"{where}: position {pos_name!r} is not in the planar")
            types.append("unplaced")
            continue
        dtype, msg = classify_form(row, relation[morpheme], elsewhere.get((morpheme, pos_name)))
        if msg:
            problem(f"{where}: {msg}")
            types.append("unplaced")
            continue
        types.append(dtype or "")
        if dtype is None:
            continue
        # conditioned_by takes position numbers or names (planars.position_cells).
        names, unknown = as_names(row.get("conditioned_by", ""), pos_to_name)
        for t in unknown:
            problem(f"{where}: conditioned_by names {t!r}, which is not in the planar")
        triggers = {name_to_pos[t] for t in names}
        key = (morpheme, None if dtype == "extended_exponence" else pos_name, dtype)
        domain_positions.setdefault(key, set()).update({name_to_pos[pos_name]} | triggers)

    form_table = morphs.copy()
    form_table["deviation_type"] = types

    order = {t: i for i, t in enumerate(DERIVED_TYPES)}
    domains = []
    for (morpheme, pos_name, dtype), positions in sorted(
            domain_positions.items(),
            key=lambda kv: (order[kv[0][2]], kv[0][0], kv[0][1] or "")):
        domains.append({
            "morpheme": morpheme,
            "position_name": pos_name,
            "type": dtype,
            "positions": sorted(positions),
            "raw_span": (min(positions), max(positions)),
            "anchored_span": loose_span(positions - {keystone_pos}, keystone_pos),
        })

    return {
        "keystone_position": keystone_pos,
        "position_number_to_name": pos_to_name,
        "form_table": form_table,
        "missing_data": {"unplaced_rows": problems} if problems else {},
        "domains": domains,
    }


def format_result(result: Dict[str, object]) -> str:
    """Format a derive_biuniqueness_deviations_domains result as text."""
    p = result["position_number_to_name"]
    lines = []
    unplaced = result.get("missing_data", {}).get("unplaced_rows", [])
    if unplaced:
        lines.append("NOTE: Some form rows could not be placed and were skipped:")
        lines += [f"  {m}" for m in unplaced]
        lines.append("")
    lines.append(f"Keystone position: {result['keystone_position']} "
                 f"({p.get(result['keystone_position'], '?')})")
    current = None
    for d in result["domains"]:
        if d["type"] != current:
            current = d["type"]
            lines += ["", f"== {current} =="]
        where = d["position_name"] or "(all its pieces)"
        lines.append(f"{d['morpheme']} at {where}:")
        lines.append(f"  raw span:      {fmt_span(d['raw_span'], p)}")
        lines.append(f"  anchored span: {fmt_span(d['anchored_span'], p)}")
    if not result["domains"]:
        lines += ["", "No biuniqueness deviations found."]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py to call each module's main
# derive function without a per-module name mapping.
derive = derive_biuniqueness_deviations_domains
