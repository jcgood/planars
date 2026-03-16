from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Set, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from planars.spans import strict_span, loose_span, position_sets_from_element_mask

DATA_DIR = ""


def _resolve_path(filename: str) -> Path:
    base = Path(DATA_DIR) if DATA_DIR else Path(__file__).resolve().parent
    return base / filename


def derive_subspanrepetition_spans(filled_tsv: str) -> Dict[str, object]:
    """Derive strict/loose and partial/complete spans for subspan repetition.

    Assumptions about the filled TSV structure:
      - Has columns: Element, Position_Name, Position_Number
      - Parameter columns include:
          * widescope_left
          * widescope_right
          * fillable_botheither_conjunct
      - Cell values for parameters are 'y' or 'n' (case-insensitive)
      - Keystone row(s) are identified by Position_Name == 'v:verbroot' (case-insensitive)
        and are excluded from evidence; their Position_Number defines the keystone position.

    Span categories computed (each with strict/loose x partial/complete = 20 total):
      1) maximum_fillable  -> fillable_botheither_conjunct == 'y'
      2) maximum_widescope_left  -> widescope_left == 'y'
      3) maximum_widescope_right -> widescope_right == 'y'
      4) maximum_narrowscope_left  -> widescope_left == 'n' (explicit)
      5) maximum_narrowscope_right -> widescope_right == 'n' (explicit)
    """
    path = _resolve_path(filled_tsv)
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)

    required = {"Element", "Position_Name", "Position_Number"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required column(s): {sorted(missing)}")

    expected_params = {"widescope_left", "widescope_right", "fillable_botheither_conjunct"}
    missing_params = expected_params - set(df.columns)
    if missing_params:
        raise ValueError(
            f"Missing expected parameter column(s): {sorted(missing_params)}. "
            f"Found columns: {list(df.columns)}"
        )

    df["Position_Number"] = df["Position_Number"].astype(str).str.strip()
    if (df["Position_Number"] == "").any():
        raise ValueError("Some rows have blank Position_Number.")
    df["Position_Number"] = df["Position_Number"].astype(int)

    df["Position_Name"] = df["Position_Name"].astype(str).str.strip()
    df["Element"] = df["Element"].astype(str).str.strip()

    for c in expected_params:
        df[c] = df[c].astype(str).str.strip().str.lower()

    keystone_mask = df["Position_Name"].str.lower() == "v:verbroot"
    if not keystone_mask.any():
        raise ValueError("No keystone row found (Position_Name == 'v:verbroot').")

    keystone_positions = sorted(df.loc[keystone_mask, "Position_Number"].unique().tolist())
    if len(keystone_positions) != 1:
        raise ValueError(f"Expected exactly 1 keystone position, found: {keystone_positions}")
    keystone_pos = keystone_positions[0]

    data_df = df.loc[~keystone_mask].copy()

    for c in expected_params:
        if (data_df[c] == "").any():
            bad = data_df.index[data_df[c] == ""].tolist()[:10]
            raise ValueError(f"Blank value(s) found in column '{c}' (example row indices: {bad}).")

    data_df["is_fillable"] = data_df["fillable_botheither_conjunct"] == "y"
    data_df["is_widescope_left"] = data_df["widescope_left"] == "y"
    data_df["is_widescope_right"] = data_df["widescope_right"] == "y"
    data_df["is_narrowscope_left"] = data_df["widescope_left"] == "n"
    data_df["is_narrowscope_right"] = data_df["widescope_right"] == "n"

    categories = {
        "maximum_fillable": "is_fillable",
        "maximum_widescope_left": "is_widescope_left",
        "maximum_widescope_right": "is_widescope_right",
        "maximum_narrowscope_left": "is_narrowscope_left",
        "maximum_narrowscope_right": "is_narrowscope_right",
    }

    results: Dict[str, object] = {
        "keystone_position": keystone_pos,
        "position_number_to_name": (
            df.sort_values(["Position_Number"])
              .groupby("Position_Number")["Position_Name"]
              .first()
              .to_dict()
        ),
        "element_table": data_df,
    }

    for cat_name, flag_col in categories.items():
        element_mask = data_df[flag_col]
        partial_positions, complete_positions = position_sets_from_element_mask(data_df, element_mask)

        results[f"{cat_name}_partial_positions"] = sorted(partial_positions)
        results[f"{cat_name}_complete_positions"] = sorted(complete_positions)

        results[f"strict_partial_{cat_name}_span"] = strict_span(partial_positions, keystone_pos)
        results[f"loose_partial_{cat_name}_span"] = loose_span(partial_positions, keystone_pos)
        results[f"strict_complete_{cat_name}_span"] = strict_span(complete_positions, keystone_pos)
        results[f"loose_complete_{cat_name}_span"] = loose_span(complete_positions, keystone_pos)

    return results


def format_result(result: Dict[str, object]) -> str:
    p = result["position_number_to_name"]

    def fmt(span):
        l, r = span
        return f"positions {l}\u2013{r}  ({p.get(l, '?')} \u2192 {p.get(r, '?')})"

    lines = [
        f"Keystone position: {result['keystone_position']} ({p.get(result['keystone_position'], '?')})",
    ]
    for k in [
        "maximum_fillable",
        "maximum_widescope_left",
        "maximum_widescope_right",
        "maximum_narrowscope_left",
        "maximum_narrowscope_right",
    ]:
        lines += [
            "",
            f"== {k} ==",
            f"{k} complete positions: {result[f'{k}_complete_positions']}",
            f"{k} partial positions:  {result[f'{k}_partial_positions']}",
            "",
            f"Strict complete {k} span: {fmt(result[f'strict_complete_{k}_span'])}",
            f"Loose complete {k} span:  {fmt(result[f'loose_complete_{k}_span'])}",
            f"Strict partial {k} span:  {fmt(result[f'strict_partial_{k}_span'])}",
            f"Loose partial {k} span:   {fmt(result[f'loose_partial_{k}_span'])}",
        ]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys as _sys
    tsv = _sys.argv[1] if len(_sys.argv) > 1 else "subspanrepetition_stan1293_andCoordination_full.tsv"
    result = derive_subspanrepetition_spans(tsv)
    print(format_result(result))
