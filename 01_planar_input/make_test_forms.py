from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import csv
import pandas as pd

DATA_DIR = ""


def _resolve_path(filename: str) -> Path:
    base = Path(DATA_DIR) if DATA_DIR else Path(__file__).resolve().parent
    return base / filename


def _infer_language_id_from_planar_filename(planar_filename: str) -> str:
    # Accept: planar_<lang>.tsv OR planar_<lang>-<date>.tsv
    stem = Path(planar_filename).stem
    if not stem.startswith("planar_"):
        raise ValueError(f"Expected planar filename to start with 'planar_', got '{planar_filename}'")

    remainder = stem[len("planar_"):]
    # If a date/version suffix exists, drop it (e.g., stan1293-20260209 -> stan1293)
    lang_id = remainder.split("-", 1)[0].strip()
    if not lang_id:
        raise ValueError(f"Could not infer language id from '{planar_filename}'")
    return lang_id


# value tuple: (Position_Number, Position_Name, Language_ID, Element_Plain)
ElementIndex = Dict[str, Tuple[int, str, str, str]]


def build_element_index(planar_filename: str) -> ElementIndex:
    """
    Build mapping with *unique keys* per element occurrence:
        key   = f"{element_plain}@{position_number}"
        value = (position_number, position_name, language_id, element_plain)

    Uses the explicit 'Position' column (integer) from the planar TSV.
    """
    lang_id = _infer_language_id_from_planar_filename(planar_filename)
    path = _resolve_path(planar_filename)

    df = pd.read_csv(path, sep="\t", header=0, dtype=str, keep_default_na=False)

    required_cols = {"Class_Type", "Elements", "Position_Name", "Position"}
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

    for _, row in df.iterrows():
        class_type = (row.get("Class_Type", "") or "").strip().lower()
        elements_raw = (row.get("Elements", "") or "").strip()
        position_name = (row.get("Position_Name", "") or "").strip()
        pos_raw = (row.get("Position", "") or "").strip()

        if not pos_raw:
            continue
        try:
            pos = int(pos_raw)
        except ValueError as e:
            raise ValueError(f"Non-integer Position value '{pos_raw}'") from e

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


def _read_parameter_tests(parameters_path: Path) -> List[Tuple[str, str, List[str]]]:
    """
    Read a parameters file with no header.

    Format per row:
        language_id    test_label    param1    param2    ...

    Returns a list of:
        (language_id, test_label, [param1, param2, ...])
    """
    df = pd.read_csv(parameters_path, sep="\t", header=None)

    if df.shape[1] < 3:
        raise ValueError(
            f"{parameters_path} must have at least 3 columns: "
            "language_id, test_label, and at least one parameter."
        )

    tests = []

    for i, row in df.iterrows():
        language_id = row.iloc[0]
        test_label = row.iloc[1]
        parameter_names = list(row.iloc[2:])

        if pd.isna(language_id) or pd.isna(test_label):
            raise ValueError(
                f"Row {i} in {parameters_path} missing language_id or test_label."
            )

        tests.append((language_id, test_label, parameter_names))

    return tests


def generate_test_file(
    test_type: str,
    planar_filename: str,
    element_index: ElementIndex,
) -> Path:
    """
    Writes `{test_type}_{lang}_blank.tsv`.

    Output columns:
      Element, Position_Name, Position_Number, <param headers...>

    Rows are ordered by Position_Number, then Element (alphabetical).
    """
    lang_id = _infer_language_id_from_planar_filename(planar_filename)

    param_names = _read_parameter_tests(f"{test_type}_parameters.tsv")
    if not param_names:
        raise ValueError("No parameter names found.")

    # Remove planar language id column if it was included as a column name
    # (e.g., 'stan1293' in your uploaded file).
    param_names = [p for p in param_names if p != lang_id]

    # Collect items for this language
    items: List[Tuple[int, str, str]] = []
    for _, (pos, pos_name, lang, element_plain) in element_index.items():
        if lang == lang_id:
            items.append((pos, element_plain, pos_name))

    items_sorted = sorted(items, key=lambda t: (t[0], t[1].lower(), t[1]))

    out_rows: List[List[object]] = []
    for pos, element_plain, pos_name in items_sorted:
        # Clean up an issue with Excel and elements that begin or end with a hyphen
        element_plain = element_plain.strip()
        if element_plain.startswith("-") or element_plain.endswith("-"):
            element_plain = f"[{element_plain}]"

        if pos_name.strip() == "Keystone":
            out_rows.append([element_plain, pos_name, pos, *(["NA"] * len(param_names))])
        else:
            out_rows.append([element_plain, pos_name, pos, *([""] * len(param_names))])

    out_df = pd.DataFrame(
        out_rows,
        columns=["Element", "Position_Name", "Position_Number", *param_names],
    )

    out_path = _resolve_path(f"{test_type}_{lang_id}_blank.tsv")
    out_df.to_csv(out_path, sep="\t", index=False, quoting=csv.QUOTE_NONE)
    return out_path


if __name__ == "__main__":
    planar_file = "planar_stan1293-20260209.tsv"
    element_index = build_element_index(planar_file)

    out = generate_test_file("ciscategorial", planar_file, element_index)
    print("Wrote:", out)
