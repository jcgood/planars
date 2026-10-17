"""Row building for the biuniqueness_deviations class sheet (issue #254).

Logic only, no Drive calls: generate_sheets.py dispatches here for this class
and does the writing. Three tabs, each generated from the one before. Their
names are read from the class's `depends_on` chain in diagnostic_classes.yaml
(ELEMENTS, MORPHEMES, MORPHS, imported from planars.biuniqueness_deviations),
never typed, so renaming a tab is a schema edit only:

  elements      element rows (Element, Position_Name, Position_Number), the
                standard shape, restricted to elements in scope (computed from
                Elements; see scoped_elements). has_allomorphs is
                pre-set to NA on open-category rows: those rows want members
                (known members of the category), not a y/n.
  morphemes     keyed rows, one per morpheme found in the elements tab:
                a filled element marked has_allomorphs=y, a listed member of
                an open category, or an element with co_exponents (a label
                "{element} + {positions}" whose forms co-occur).
  morphs        keyed rows, one per (morpheme, position, form): every planar
                position the morpheme sits at, crossed with its forms.

Keyed rows carry an Origin column saying where each row came from
(filled / open_category / co_exponent), written by the generator. A row with
no Origin was added by hand; it is marked hand-added and survives every
regeneration. A generated row whose source has disappeared is left out of
carry_over()'s rows; if it holds answers, the Drive door refuses the rewrite
(drive_door.replacing's ``kept``, the same guard --regen-construction applies
to pair tabs, issue #241).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from planars.biuniqueness_deviations import CLASS_NAME  # noqa: F401  (re-exported)
from planars.biuniqueness_deviations import ELEMENTS_TAB as ELEMENTS
from planars.biuniqueness_deviations import MORPHEMES_TAB as MORPHEMES
from planars.biuniqueness_deviations import MORPHS_TAB as MORPHS
from planars.schema_values import row_columns, row_key

from .make_forms import wrap_element as wrap  # bracket a hyphenated element, as every sheet does
from .validate_planar import _tokenize_elements

MORPHEMES_STRUCT = row_columns(CLASS_NAME, MORPHEMES)
MORPHEMES_KEY = row_key(CLASS_NAME, MORPHEMES)
MORPHS_STRUCT = row_columns(CLASS_NAME, MORPHS)
MORPHS_KEY = row_key(CLASS_NAME, MORPHS)

FILLED, OPEN_CATEGORY, CO_EXPONENT, HAND_ADDED = (
    "filled", "open_category", "co_exponent", "hand-added")
GENERATED_ORIGINS = (FILLED, OPEN_CATEGORY, CO_EXPONENT)
_ORIGIN_RANK = {FILLED: 0, OPEN_CATEGORY: 1, CO_EXPONENT: 2}

# Structural columns and key per keyed construction: the schema's
# keyed_columns and key, read, not copied.
KEYED = {
    MORPHEMES: (MORPHEMES_STRUCT, MORPHEMES_KEY),
    MORPHS: (MORPHS_STRUCT, MORPHS_KEY),
}


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
    """(position_number, position_name, element, scope) for every element in
    scope (anything but excluded), in planar order.

    The scope is computed from Elements by make_forms.classify_biuniqueness_scope.
    It used to be read from a Biuniqueness_Scope planar column, a copy of the
    same computation; an element added without the column being extended
    crashed every command that builds this tab, and the column was deleted
    (2026-10-13). Raises ValueError for an unregistered ALL CAPS label rather
    than guessing its scope."""
    from .make_forms import classify_biuniqueness_scope
    out = []
    df = planar_df[planar_df["Language_ID"] == lang_id] if "Language_ID" in planar_df else planar_df
    for _, row in df.iterrows():
        pos_name = str(row["Position_Name"]).strip()
        for element in _tokenize_elements(str(row["Elements"]).strip()):
            element = element.strip()
            scope = classify_biuniqueness_scope(element)
            if scope == "unknown":
                raise ValueError(
                    f"{pos_name}: '{element}' is an ALL CAPS label not registered in "
                    f"schemas/planar.yaml, so its biuniqueness scope is unknown; register it.")
            if scope != "excluded":
                out.append((int(row["Position"]), pos_name, element, scope))
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
# Tab 1: elements
# ---------------------------------------------------------------------------

def element_rows(planar_df: pd.DataFrame, lang_id: str,
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


def morpheme_rows(elements: pd.DataFrame, planar_df: pd.DataFrame,
                  lang_id: str) -> List[Dict[str, str]]:
    """One row per morpheme found in the elements tab's answers.

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

    for _, r in elements.iterrows():
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

def morph_rows(morphemes: pd.DataFrame, elements: pd.DataFrame,
               planar_df: pd.DataFrame, lang_id: str) -> List[Dict[str, str]]:
    """One row per (morpheme, position, form) to be judged.

    filled morphemes: every planar position listing the element, crossed with
    its forms (the element plus the variant forms its elements-tab rows
    listed in members). open_category members: the positions where they were
    listed, with the member itself as the one form (other forms are added by
    hand). co_exponent morphemes: the element at its own position plus every
    element listed at each co-exponent position, each to be marked
    occurs_here y/n.
    """
    pos_of = positions_of(planar_df, lang_id)
    at = elements_at(planar_df, lang_id)

    variants: Dict[str, List[str]] = {}
    co_source: Dict[str, Tuple[str, str, List[str]]] = {}
    for _, r in elements.iterrows():
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


def sources_of(construction: str) -> List[str]:
    """The tabs a keyed tab is generated from: morphemes from elements,
    morphs from morphemes plus elements."""
    return [ELEMENTS] + ([MORPHEMES] if construction == MORPHS else [])


def keyed_rows(construction: str, read, planar_df: pd.DataFrame,
               lang_id: str) -> List[Dict[str, str]]:
    """The generated rows for keyed tab `construction`; read(tab) returns the
    imported DataFrame of each tab sources_of(construction) names."""
    if construction == MORPHEMES:
        return morpheme_rows(read(ELEMENTS), planar_df, lang_id)
    if construction == MORPHS:
        return morph_rows(read(MORPHEMES), read(ELEMENTS), planar_df, lang_id)
    raise ValueError(f"{CLASS_NAME} has no keyed tab named {construction!r}")


# ---------------------------------------------------------------------------
# Carrying answers over on regeneration
# ---------------------------------------------------------------------------

def carry_over(
    generated: List[Dict[str, str]],
    existing_rows: List[List[str]],
    key_cols: Sequence[str],
    answer_cols: Sequence[str],
) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    """Merge freshly generated rows with what the tab already holds.

    Returns (rows, counts):
      rows    generated rows with their existing answers carried over by key,
              then hand-added rows (no Origin, or hand-added), which are
              always kept. A previously generated row whose source is gone is
              not among them; if it holds an answer, the Drive door refuses
              the rewrite (the caller passes these rows' keys as ``kept``);
      counts  retained / added / removed / hand_added.
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

    hand = []
    for key in order:
        if key in new_keys:
            continue
        rec = existing[key]
        if not is_generated(rec):
            hand.append({**rec, "Origin": HAND_ADDED})

    counts = {"retained": len(new_keys & set(order)),
              "added": len(new_keys - set(order)),
              "removed": sum(1 for k in order if k not in new_keys and is_generated(existing[k])),
              "hand_added": len(hand)}
    return out + hand, counts


def is_generated(record: Dict[str, str]) -> bool:
    """Whether a keyed tab's row was generated (its Origin says how), as
    opposed to added by hand (no Origin, or hand-added)."""
    return str(record.get("Origin", "")).strip() in GENERATED_ORIGINS

