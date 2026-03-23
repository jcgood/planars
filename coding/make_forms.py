from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

DATA_DIR = ""


def _resolve_path(filename: str) -> Path:
    """Resolve a filename against DATA_DIR, falling back to the script directory."""
    base = Path(DATA_DIR) if DATA_DIR else Path(__file__).resolve().parent
    return base / filename


def _infer_language_id_from_planar_filename(planar_filename: str) -> str:
    """Extract the language ID from a planar filename.

    Accepts both bare (planar_<lang>.tsv) and dated (planar_<lang>-<date>.tsv)
    filenames. Only the portion before the first hyphen after the 'planar_' prefix
    is treated as the language ID.

    Args:
        planar_filename: basename or path of the planar TSV file.

    Returns:
        The language ID string (e.g. 'stan1293').

    Raises:
        ValueError: if the filename doesn't start with 'planar_' or the ID is empty.
    """
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
    """Build a mapping with unique keys per element occurrence in a planar TSV.

    Each element that appears in the planar structure gets a key of the form
    ``f"{element_plain}@{position_number}"`` so the same element name can appear
    in multiple positions without collision.

    Args:
        planar_filename: basename of the planar TSV file (resolved via DATA_DIR
            or the script directory). Must have columns: Class_Type, Elements,
            Position_Name, Position.

    Returns:
        Dict mapping ``"element@pos"`` keys to
        ``(position_number, position_name, language_id, element_plain)`` tuples.

    Raises:
        ValueError: if required columns are missing, Position is non-integer,
            a duplicate key is found, or Class_Type is unexpected.
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
        """Register one element occurrence; raise if the (element, pos) key is duplicate."""
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
        # Skip rows that belong to a different language (multi-language planar files).
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

        # Both "open" and "list" class types enumerate individual elements;
        # the distinction matters for form generation but not for indexing.
        if class_type == "open":
            for element_plain in _split_elements(elements_raw):
                add_element(element_plain, pos, position_name)

        elif class_type == "list":
            for element_plain in _split_elements(elements_raw):
                add_element(element_plain, pos, position_name)

        else:
            raise ValueError(f"Unexpected Class_Type '{class_type}' at position {pos}")

    return element_to_info


def _resolve_diagnostics_path(lang_id: str) -> Path:
    """Find the language-specific diagnostics file in the planar_input folder.

    Expected name: diagnostics_{lang_id}.tsv
    """
    base = Path(DATA_DIR) if DATA_DIR else Path(__file__).resolve().parent
    p = base / f"diagnostics_{lang_id}.tsv"
    if p.exists():
        return p
    raise FileNotFoundError(f"Could not find diagnostics_{lang_id}.tsv in {base}")


def _parse_csv_list(value: str) -> List[str]:
    """Split a comma-separated string into a list of non-empty stripped tokens."""
    return [v.strip() for v in (value or "").split(",") if v.strip()]


_DEFAULT_CRITERION_VALUES = ["y", "n"]


def _parse_criterion_spec(spec: str) -> Tuple[str, List[str]]:
    """Parse a parameter specification into (name, allowed_values).

    Examples:
        'free'              -> ('free', ['y', 'n'])
        'stressable{y/n/both}' -> ('stressable', ['y', 'n', 'both'])
    """
    spec = spec.strip()
    if "{" in spec:
        if not spec.endswith("}"):
            raise ValueError(f"Malformed parameter spec (missing closing brace): '{spec}'")
        name, _, values_str = spec[:-1].partition("{")
        values = [v.strip() for v in values_str.split("/") if v.strip()]
        if not values:
            raise ValueError(f"Parameter spec has empty value list: '{spec}'")
        return name.strip(), values
    return spec, list(_DEFAULT_CRITERION_VALUES)


def _parse_criterion_specs(value: str) -> Tuple[List[str], Dict[str, List[str]]]:
    """Parse a comma-separated criterion specs string.

    Returns (criterion_names, criterion_values) where criterion_values maps each name
    to its allowed values list.
    """
    criterion_names: List[str] = []
    criterion_values: Dict[str, List[str]] = {}
    for spec in _parse_csv_list(value):
        name, values = _parse_criterion_spec(spec)
        criterion_names.append(name)
        criterion_values[name] = values
    return criterion_names, criterion_values


def _read_diagnostics_for_language(
    language_id: str,
) -> List[Tuple[str, str, List[str], Dict[str, List[str]]]]:
    """Read diagnostics_{lang_id}.tsv and return rows for a language.

    Each row is (class_name, construction, criterion_names, criterion_values) where
    criterion_values maps each criterion name to its list of allowed values.
    """
    diag_path = _resolve_diagnostics_path(language_id)
    df = pd.read_csv(diag_path, sep="\t", header=0, dtype=str, keep_default_na=False)

    required = {"Class", "Language", "Constructions", "Criteria"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Diagnostics file missing required columns: {sorted(missing)}")

    out: List[Tuple[str, str, List[str], Dict[str, List[str]]]] = []

    for _, row in df.iterrows():
        lang = (row.get("Language", "") or "").strip()
        if lang != language_id:
            continue

        class_name = (row.get("Class", "") or "").strip()
        constructions = _parse_csv_list(row.get("Constructions", ""))
        criterion_names, criterion_values = _parse_criterion_specs(row.get("Criteria", ""))

        if not class_name:
            raise ValueError("Diagnostics file has a row with empty Class.")
        if not constructions:
            continue
        if not criterion_names:
            raise ValueError(f"Diagnostics row for class '{class_name}' has no Criteria.")

        for construction in constructions:
            out.append((class_name, construction, criterion_names, criterion_values))

    return out

