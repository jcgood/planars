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
        raise ValueError(
            f"Expected planar filename to start with 'planar_', got '{planar_filename}'"
        )

    remainder = stem[len("planar_") :]
    # If a date/version suffix exists, drop it (e.g., stan1293-20260209 -> stan1293)
    lang_id = remainder.split("-", 1)[0].strip()
    if not lang_id:
        raise ValueError(f"Could not infer language id from '{planar_filename}'")
    return lang_id


# value tuple: (Position_Number, Position_Name, Language_ID, Element_Plain)
ElementIndex = Dict[str, Tuple[int, str, str, str]]


def _split_elements(elements_raw: str) -> List[str]:
    """Split a comma-separated elements string, ignoring commas inside braces.

    E.g. 'QWORDS, NP{S,A,P}' -> ['QWORDS', 'NP{S,A,P}']
    """
    parts: List[str] = []
    current: List[str] = []
    depth = 0
    for ch in elements_raw:
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
            raise ValueError(
                f"Duplicate unique key '{key}' (element repeated within same position?)"
            )

        element_to_info[key] = (pos, position_name, lang_id, element_plain)

    for _, row in df.iterrows():
        row_lang = (row.get("Language_ID", "") or "").strip()
        if row_lang != lang_id:
            continue

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
            for element_plain in _split_elements(elements_raw):
                add_element(element_plain, pos, position_name)

        elif class_type == "list":
            for element_plain in _split_elements(elements_raw):
                add_element(element_plain, pos, position_name)

        else:
            raise ValueError(f"Unexpected Class_Type '{class_type}' at position {pos}")

    return element_to_info


def _resolve_diagnostics_path() -> Path:
    """Find diagnostics file in the script folder.

    Preferred name: diagnostics.tsv
    Also accepts a common misspelling used earlier: diagnotics.tsv
    """
    base = Path(DATA_DIR) if DATA_DIR else Path(__file__).resolve().parent
    p1 = base / "diagnostics.tsv"
    if p1.exists():
        return p1
    p2 = base / "diagnotics.tsv"
    if p2.exists():
        return p2
    raise FileNotFoundError("Could not find diagnostics.tsv (or diagnotics.tsv) in the script directory.")


def _parse_csv_list(value: str) -> List[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def _read_diagnostics_for_language(language_id: str) -> List[Tuple[str, str, List[str]]]:
    """Read diagnostics.tsv and return (class_name, construction, parameters) rows for a language."""
    diag_path = _resolve_diagnostics_path()
    df = pd.read_csv(diag_path, sep="\t", header=0, dtype=str, keep_default_na=False)

    required = {"Class", "Language", "Constructions", "Parameters"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Diagnostics file missing required columns: {sorted(missing)}")

    out: List[Tuple[str, str, List[str]]] = []

    for _, row in df.iterrows():
        lang = (row.get("Language", "") or "").strip()
        if lang != language_id:
            continue

        class_name = (row.get("Class", "") or "").strip()
        constructions = _parse_csv_list(row.get("Constructions", ""))
        params = _parse_csv_list(row.get("Parameters", ""))

        if not class_name:
            raise ValueError("Diagnostics file has a row with empty Class.")
        if not constructions:
            # Nothing to generate for this row
            continue
        if not params:
            raise ValueError(f"Diagnostics row for class '{class_name}' has no Parameters.")

        for construction in constructions:
            out.append((class_name, construction, params))

    return out


def generate_test_file(
    class_name: str,
    construction: str,
    planar_filename: str,
    element_index: ElementIndex,
    param_names: List[str],
) -> Path:
    """
    Writes `{Class}_{Language}_{Construction}_blank.tsv`.

    Output columns:
      Element, Position_Name, Position_Number, <param headers...>

    Rows are ordered by Position_Number, then Element (alphabetical).
    """
    lang_id = _infer_language_id_from_planar_filename(planar_filename)

    if not param_names:
        raise ValueError("No parameter names found.")

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

    out_path = _resolve_path(f"{class_name}_{lang_id}_{construction}_blank.tsv")
    out_df.to_csv(out_path, sep="\t", index=False, quoting=csv.QUOTE_NONE)
    return out_path


def generate_all_from_diagnostics(planar_filename: str) -> List[Path]:
    """Generate one blank form per (Class, Construction) for the planar language."""
    lang_id = _infer_language_id_from_planar_filename(planar_filename)
    element_index = build_element_index(planar_filename)

    specs = _read_diagnostics_for_language(lang_id)

    out_paths: List[Path] = []
    for class_name, construction, params in specs:
        out_paths.append(
            generate_test_file(
                class_name=class_name,
                construction=construction,
                planar_filename=planar_filename,
                element_index=element_index,
                param_names=params,
            )
        )
    return out_paths


if __name__ == "__main__":
    # Default: use the first planar_*.tsv file in the directory
    base = Path(__file__).resolve().parent
    planar_files = sorted(base.glob("planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in script directory.")

    generated = generate_all_from_diagnostics(planar_files[0].name)
    for p in generated:
        print("Wrote:", p.name)