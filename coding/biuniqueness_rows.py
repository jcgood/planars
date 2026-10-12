"""Row building for the biuniqueness_deviations class sheet (issue #254).

Logic only, no Drive calls: generate_sheets.py dispatches here for this class
and does the writing. Three tabs, each generated from the one before:

  prescreening  element rows (Element, Position_Name, Position_Number), the
                standard shape, restricted to elements the planar's
                Biuniqueness_Scope column puts in scope. has_allomorphs is
                pre-set to NA on open-category rows: those rows want members
                (known members of the category), not a y/n.
  morphemes     keyed rows, one per morpheme found in prescreening:
                a filled element marked has_allomorphs=y, a listed member of
                an open category, or an element with co_exponents (a label
                "{element} + {positions}" whose forms co-occur).
  morphs        keyed rows, one per (morpheme, position, form): every planar
                position the morpheme sits at, crossed with its forms.

Keyed rows carry an Origin column saying where each row came from
(filled / open_category / co_exponent), written by the generator. A row with
no Origin was added by hand; it is marked hand-added and survives every
regeneration. A generated row whose source has disappeared is dropped if
empty; if it holds answers, carry_over() reports it so regeneration can refuse
(the same guard --regen-construction applies to pair tabs, issue #241).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from .validate_planar import _tokenize_elements

CLASS_NAME = "biuniqueness_deviations"

MORPHEMES_STRUCT = ["Morpheme", "Origin", "Found_At"]
MORPHEMES_KEY = ["Morpheme"]
MORPHS_STRUCT = ["Morpheme", "Position_Name", "Form", "Origin"]
MORPHS_KEY = ["Morpheme", "Position_Name", "Form"]

FILLED, OPEN_CATEGORY, CO_EXPONENT, HAND_ADDED = (
    "filled", "open_category", "co_exponent", "hand-added")
GENERATED_ORIGINS = (FILLED, OPEN_CATEGORY, CO_EXPONENT)
_ORIGIN_RANK = {FILLED: 0, OPEN_CATEGORY: 1, CO_EXPONENT: 2}

# Key and structural columns per keyed construction. The schema's
# keyed_columns for each construction must match (a test holds them together).
KEYED = {
    "morphemes": (MORPHEMES_STRUCT, MORPHEMES_KEY),
    "morphs": (MORPHS_STRUCT, MORPHS_KEY),
}


def wrap(element: str) -> str:
    """Bracket a hyphen-initial/final element, as every sheet does (Sheets
    would otherwise read '-ing' as a formula)."""
    element = element.strip()
    return f"[{element}]" if (element.startswith("-") or element.endswith("-")) else element


def _split_list(cell) -> List[str]:
    return [p.strip() for p in str(cell or "").split(",") if p.strip()]


def _dedupe(items: Iterable[str]) -> List[str]:
    seen, out = set(), []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ---------------------------------------------------------------------------
# The planar
# ---------------------------------------------------------------------------

def scoped_elements(planar_df: pd.DataFrame, lang_id: str) -> List[Tuple[int, str, str, str]]:
    """(position_number, position_name, element, scope) for every element the
    planar's Biuniqueness_Scope column puts in scope (anything but excluded),
    in planar order. Raises ValueError if the column is missing or out of
    step with Elements."""
    if "Biuniqueness_Scope" not in planar_df.columns:
        raise ValueError(
            f"planar_{lang_id}.tsv has no Biuniqueness_Scope column, which decides "
            f"which elements this class screens. Backfill it first (see #254 Part 2b "
            f"and migrations/backfill_biuniqueness_scope_synth0001.py).")
    out = []
    df = planar_df[planar_df["Language_ID"] == lang_id] if "Language_ID" in planar_df else planar_df
    for _, row in df.iterrows():
        pos_name = str(row["Position_Name"]).strip()
        elements = _tokenize_elements(str(row["Elements"]).strip())
        scopes = _tokenize_elements(str(row["Biuniqueness_Scope"]).strip())
        if len(elements) != len(scopes):
            raise ValueError(
                f"{pos_name}: Elements has {len(elements)} item(s) but Biuniqueness_Scope "
                f"has {len(scopes)}; they must line up one to one.")
        for element, scope in zip(elements, scopes):
            if scope != "excluded":
                out.append((int(row["Position"]), pos_name, element.strip(), scope))
    return out


def positions_of(planar_df: pd.DataFrame, lang_id: str) -> Dict[str, List[str]]:
    """{wrapped element: [position names it is listed at]}, in planar order."""
    df = planar_df[planar_df["Language_ID"] == lang_id] if "Language_ID" in planar_df else planar_df
    df = df.assign(_n=df["Position"].astype(int)).sort_values("_n")
    out: Dict[str, List[str]] = {}
    for _, row in df.iterrows():
        for element in _tokenize_elements(str(row["Elements"]).strip()):
            out.setdefault(wrap(element), []).append(str(row["Position_Name"]).strip())
    return out


def elements_at(planar_df: pd.DataFrame, lang_id: str) -> Dict[str, List[str]]:
    """{position name: [wrapped elements listed there]}."""
    df = planar_df[planar_df["Language_ID"] == lang_id] if "Language_ID" in planar_df else planar_df
    return {str(r["Position_Name"]).strip(): [wrap(e) for e in _tokenize_elements(str(r["Elements"]))]
            for _, r in df.iterrows()}


def position_order(planar_df: pd.DataFrame, lang_id: str) -> Dict[str, int]:
    df = planar_df[planar_df["Language_ID"] == lang_id] if "Language_ID" in planar_df else planar_df
    return {str(r["Position_Name"]).strip(): int(r["Position"]) for _, r in df.iterrows()}


# ---------------------------------------------------------------------------
# Tab 1: prescreening
# ---------------------------------------------------------------------------

def prescreening_rows(planar_df: pd.DataFrame, lang_id: str,
                      param_names: Sequence[str]) -> List[List[object]]:
    """Standard element rows ([Element, Position_Name, Position_Number,
    *criteria]) for in-scope elements only. Open-category rows get NA in
    has_allomorphs: they are answered through members instead."""
    rows = []
    for pos_num, pos_name, element, scope in scoped_elements(planar_df, lang_id):
        vals = ["NA" if (p == "has_allomorphs" and scope == "open_category") else ""
                for p in param_names]
        rows.append([wrap(element), pos_name, pos_num] + vals)
    return rows


# ---------------------------------------------------------------------------
# Tab 2: morphemes
# ---------------------------------------------------------------------------

def _co_label(element: str, co_positions: Sequence[str]) -> str:
    return f"{element} + {', '.join(co_positions)}"


def morpheme_rows(prescreening: pd.DataFrame, planar_df: pd.DataFrame,
                  lang_id: str) -> List[Dict[str, str]]:
    """One row per morpheme found in the prescreening answers.

    A filled element marked has_allomorphs=y is a morpheme; so is each member
    listed on an open-category row; so is each element with co_exponents
    (labelled "{element} + {positions}", forms_relation pre-set to co-occur).
    The same morpheme found at several positions is one row; Found_At lists
    them in planar order.
    """
    order = position_order(planar_df, lang_id)
    found: Dict[str, Dict] = {}

    def add(morpheme: str, origin: str, pos: str, prefill: Optional[Dict] = None):
        entry = found.setdefault(morpheme, {"origin": origin, "at": [], "prefill": prefill or {}})
        if _ORIGIN_RANK[origin] < _ORIGIN_RANK[entry["origin"]]:
            entry["origin"] = origin
        if pos not in entry["at"]:
            entry["at"].append(pos)

    for _, r in prescreening.iterrows():
        element, pos = str(r["Element"]).strip(), str(r["Position_Name"]).strip()
        has = str(r.get("has_allomorphs", "")).strip().lower()
        if has == "y":
            add(element, FILLED, pos)
        elif has == "na":
            for member in _split_list(r.get("members", "")):
                add(wrap(member), OPEN_CATEGORY, pos)
        co = _split_list(r.get("co_exponents", ""))
        if co:
            add(_co_label(element, co), CO_EXPONENT, pos, {"forms_relation": "co-occur"})

    rows = []
    for morpheme, e in found.items():
        at = sorted(e["at"], key=lambda p: order.get(p, 10**6))
        rows.append({"Morpheme": morpheme, "Origin": e["origin"],
                     "Found_At": ", ".join(at), **e["prefill"]})
    rows.sort(key=lambda d: (_ORIGIN_RANK[d["Origin"]],
                             order.get(d["Found_At"].split(",")[0].strip(), 10**6),
                             d["Morpheme"].lower()))
    return rows


# ---------------------------------------------------------------------------
# Tab 3: morphs
# ---------------------------------------------------------------------------

def morph_rows(morphemes: pd.DataFrame, prescreening: pd.DataFrame,
               planar_df: pd.DataFrame, lang_id: str) -> List[Dict[str, str]]:
    """One row per (morpheme, position, form) to be judged.

    filled morphemes: every planar position listing the element, crossed with
    its forms (the element plus the variant forms its prescreening rows
    listed in members). open_category members: the positions where they were
    listed, with the member itself as the one form (other forms are added by
    hand). co_exponent morphemes: the element at its own position plus every
    element listed at each co-exponent position, each to be marked
    occurs_here y/n.
    """
    pos_of = positions_of(planar_df, lang_id)
    at = elements_at(planar_df, lang_id)
    order = position_order(planar_df, lang_id)

    variants: Dict[str, List[str]] = {}
    co_source: Dict[str, Tuple[str, str, List[str]]] = {}
    for _, r in prescreening.iterrows():
        element, pos = str(r["Element"]).strip(), str(r["Position_Name"]).strip()
        if str(r.get("has_allomorphs", "")).strip().lower() == "y":
            variants.setdefault(element, []).extend(wrap(m) for m in _split_list(r.get("members", "")))
        co = _split_list(r.get("co_exponents", ""))
        if co:
            co_source[_co_label(element, co)] = (element, pos, co)

    rows: List[Dict[str, str]] = []
    for _, m in morphemes.iterrows():
        morpheme, origin = str(m["Morpheme"]).strip(), str(m.get("Origin", "")).strip()
        if origin == FILLED:
            forms = _dedupe([morpheme] + variants.get(morpheme, []))
            for pos in pos_of.get(morpheme, []):
                rows += [{"Morpheme": morpheme, "Position_Name": pos, "Form": f, "Origin": FILLED}
                         for f in forms]
        elif origin == OPEN_CATEGORY:
            for pos in _split_list(m.get("Found_At", "")):
                rows.append({"Morpheme": morpheme, "Position_Name": pos, "Form": morpheme,
                             "Origin": OPEN_CATEGORY})
        elif origin == CO_EXPONENT and morpheme in co_source:
            element, pos, co = co_source[morpheme]
            rows.append({"Morpheme": morpheme, "Position_Name": pos, "Form": element,
                         "Origin": CO_EXPONENT})
            for c in co:
                rows += [{"Morpheme": morpheme, "Position_Name": c, "Form": e,
                          "Origin": CO_EXPONENT} for e in at.get(c, [])]
        # hand-added morphemes: their forms are added by hand on this tab too.

    seen = set()
    unique = []
    for r in rows:
        k = (r["Morpheme"], r["Position_Name"], r["Form"])
        if k not in seen:
            seen.add(k)
            unique.append(r)
    return unique


# ---------------------------------------------------------------------------
# Carrying answers over on regeneration
# ---------------------------------------------------------------------------

def carry_over(
    generated: List[Dict[str, str]],
    existing_rows: List[List[str]],
    key_cols: Sequence[str],
    answer_cols: Sequence[str],
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], Dict[str, int]]:
    """Merge freshly generated rows with what the tab already holds.

    Returns (rows, annotated_drops, counts):
      rows             generated rows with their existing answers carried over
                       by key, then hand-added rows (no Origin, or
                       hand-added), which are always kept;
      annotated_drops  previously generated rows whose source is gone and
                       that hold an answer -- the caller refuses to write
                       unless the coordinator confirms;
      counts           retained / added / removed / hand_added.
    existing_rows is the tab as read (header first), or [] for a new tab.
    """
    existing: Dict[Tuple, Dict[str, str]] = {}
    order: List[Tuple] = []
    if existing_rows:
        header = existing_rows[0]
        for raw in existing_rows[1:]:
            rec = dict(zip(header, list(raw) + [""] * (len(header) - len(raw))))
            key = tuple(str(rec.get(k, "")).strip() for k in key_cols)
            if not any(key):
                continue
            existing[key] = rec
            order.append(key)

    out, new_keys = [], set()
    for g in generated:
        key = tuple(g[k] for k in key_cols)
        new_keys.add(key)
        prior = existing.get(key, {})
        merged = dict(g)
        for col in answer_cols:
            # An answer already in the tab always wins over a generated
            # pre-fill (the annotator may have changed co-occur, say).
            if str(prior.get(col, "")).strip():
                merged[col] = prior[col]
        out.append(merged)

    drops, hand = [], []
    for key in order:
        if key in new_keys:
            continue
        rec = existing[key]
        origin = str(rec.get("Origin", "")).strip()
        if origin in GENERATED_ORIGINS:
            if any(str(rec.get(c, "")).strip() for c in answer_cols):
                drops.append(rec)
        else:
            hand.append({**rec, "Origin": HAND_ADDED})

    counts = {"retained": len(new_keys & set(order)),
              "added": len(new_keys - set(order)),
              "removed": sum(1 for k in order if k not in new_keys
                             and str(existing[k].get("Origin", "")).strip() in GENERATED_ORIGINS),
              "hand_added": len(hand)}
    return out + hand, drops, counts


def describe_drop(rec: Dict[str, str], key_cols: Sequence[str],
                  answer_cols: Sequence[str]) -> str:
    """One line naming a dropped row and the answers it holds, for the abort message."""
    who = " / ".join(rec.get(k, "") for k in key_cols)
    answers = ", ".join(f"{c}={rec[c]!r}" for c in answer_cols if str(rec.get(c, "")).strip())
    return f"  {who}: {answers}"
