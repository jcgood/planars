from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import csv

DATA_DIR = ""


def _resolve_path(filename: str) -> Path:
    base = Path(DATA_DIR) if DATA_DIR else Path(__file__).resolve().parent
    return base / filename


def _infer_language_id_from_planar_filename(planar_filename: str) -> str:
    stem = Path(planar_filename).stem
    prefix = "planar_"
    if not stem.startswith(prefix):
        raise ValueError(
            f"Expected planar filename to start with '{prefix}', got '{planar_filename}'"
        )
    lang_id = stem[len(prefix):].strip()
    if not lang_id:
        raise ValueError(f"Could not infer language id from '{planar_filename}'")
    return lang_id


# value tuple: (Position_Number, Position_Name, Language_ID, Element_Plain)
ElementIndex = Dict[str, Tuple[int, str, str, str]]


def build_element_index(filename: str) -> ElementIndex:
    """
    Build mapping with *unique keys* per element occurrence:
        key   = f"{element_plain}@{position_number}"
        value = (position_number, position_name, language_id, element_plain)

    This allows the same element_plain to appear in multiple positions.
    """
    lang_id = _infer_language_id_from_planar_filename(filename)
    path = _resolve_path(filename)

    df = pd.read_csv(path, sep="\t", header=0, dtype=str, keep_default_na=False)

    required_cols = {"Class_Type", "Elements", "Position_Name"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required column(s): {sorted(missing)}")

    element_to_info: ElementIndex = {}

    def add_element(element_plain: str, pos: int, position_name: str) -> None:
        element_plain = (element_plain or "").strip()
        if not element_plain:
            return

        key = f"{element_plain}@{pos}"
        if key in element_to_info:
            raise ValueError(f"Duplicate unique key '{key}' (element repeated within same position?)")

        element_to_info[key] = (pos, position_name, lang_id, element_plain)

    for pos, row in enumerate(df.itertuples(index=False), start=1):
        class_type = (getattr(row, "Class_Type") or "").strip().lower()
        elements_raw = (getattr(row, "Elements") or "").strip()
        position_name = (getattr(row, "Position_Name") or "").strip()

        if not elements_raw:
            continue

        if class_type == "open":
            add_element(elements_raw, pos, position_name)

        elif class_type == "list":
            for element_plain in elements_raw.split(","):
                add_element(element_plain, pos, position_name)

        else:
            raise ValueError(f"Unexpected Class_Type '{class_type}' at position {pos}")

    return element_to_info


def generate_test_files(
    test_type: str,
    element_index: ElementIndex,
) -> List[Path]:
    """
    Load `{test_type}_parameters.tsv` (no header):
      col0 = language id
      col1.. = parameter NAMES (used as header columns)

    For each language present in element_index, write `{test_type}_{lang}.tsv`.

    Output columns:
      Element, Position_Name, Position_Number, <param headers...>

    Rows are ordered by Position_Number, then Element (alphabetical).
    """
    param_path = _resolve_path(f"{test_type}_parameters.tsv")
    params_df = pd.read_csv(param_path, sep="\t", header=None, dtype=str, keep_default_na=False)

    if params_df.shape[1] < 2:
        raise ValueError(
            f"{param_path.name} must have at least 2 columns: language_id + >=1 parameter name."
        )

    # lang -> param headers
    lang_to_paramnames: Dict[str, List[str]] = {}
    for _, row in params_df.iterrows():
        lang = str(row.iloc[0]).strip()
        if not lang:
            continue
        param_names = [str(v).strip() for v in row.iloc[1:].tolist()]
        param_names = [p for p in param_names if p]
        if param_names:
            lang_to_paramnames[lang] = param_names

    # Group entries by language (note: element_index keys are unique IDs)
    lang_to_items: Dict[str, List[Tuple[int, str, str]]] = {}
    # store as (pos, element_plain, position_name)
    for _, (pos, pos_name, lang_id, element_plain) in element_index.items():
        lang_to_items.setdefault(lang_id, []).append((pos, element_plain, pos_name))

    written: List[Path] = []

    for lang_id, items in lang_to_items.items():
        if lang_id not in lang_to_paramnames:
            raise ValueError(
                f"No parameter row found in {param_path.name} for language '{lang_id}'."
            )

        param_names = lang_to_paramnames[lang_id]

        # Sort by Position_Number asc, then element_plain alpha
        items_sorted = sorted(items, key=lambda t: (t[0], t[1].lower(), t[1]))

        out_rows = []
        for pos, element_plain, pos_name in items_sorted:

			# Clean up an issue with Excel and an element that begins with a hyphen
            if element_plain.startswith("-")or element_plain.endswith("-"):
            	element_plain = f'[{element_plain}]'
                

            # Add NA to keystone rows entirely
            if pos_name.strip() == "Keystone":
                out_rows.append([element_plain, pos_name, pos, *(["NA"] * 
                                len(param_names))])

			
            else: out_rows.append([element_plain, pos_name, pos, *([""] * len(param_names))])

        out_df = pd.DataFrame(
            out_rows,
            columns=["Element", "Position_Name", "Position_Number", *param_names],
        )

        out_path = _resolve_path(f"{test_type}_{lang_id}_blank.tsv")
        out_df.to_csv(out_path, sep="\t", index=False, quoting=csv.QUOTE_NONE,)
        written.append(out_path)

    return written

# we need to add validation to the parameters: e.g., yes-no, ...
# in cis, v-combines is redundant for now, but maybe needed for a project also doing NPs?
# root can't combine with itself, remove from list, use keystone category
# need to think about fractures


if __name__ == "__main__":
    # Build once, reuse for many tests
    element_index = build_element_index("planar_stan1293.tsv")

    written = generate_test_files("ciscategorial", element_index)
    for p in written:
        print("Wrote:", p)
