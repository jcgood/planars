"""Check consistency between codebook.yaml, diagnostic_classes.yaml, analysis modules, and charts.py.

Checks:
  1. Every param in each module's _REQUIRED_PARAMS is defined in codebook.yaml
  2. Parameter names in diagnostics.tsv are defined in codebook.yaml
  3. Chart span label keys match the keys returned by each derive function
  4. diagnostics.tsv class names and required parameters match diagnostic_classes.yaml

Run:
    python -m coding check-codebook
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import List

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent


def _load_codebook() -> dict:
    """Load and parse codebook.yaml from the repo root."""
    with open(ROOT / "codebook.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_diagnostic_classes() -> dict:
    """Load and parse diagnostic_classes.yaml from the repo root.

    Returns a dict keyed by class name:
        {class_name: {"required_parameters": [...], "specificity": str, ...}}
    """
    path = ROOT / "diagnostic_classes.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {cls["name"]: cls for cls in data.get("classes", [])}


def _codebook_params(codebook: dict) -> dict[str, set[str]]:
    """Return {analysis_name: {param_name, ...}} from codebook."""
    return {
        a["name"]: {p["name"] for p in a.get("parameters", [])}
        for a in codebook.get("analyses", [])
    }


def _check_required_params(codebook: dict) -> List[str]:
    """Check that every required param in each module is defined in codebook.yaml."""
    import importlib

    cb = _codebook_params(codebook)
    # ciscategorial uses inline required_params rather than a module-level constant.
    # All other modules expose _REQUIRED_PARAMS at module level.
    module_params: dict[str, set] = {
        "ciscategorial": {"V-combines", "N-combines", "A-combines"},
    }
    for name in [
        "subspanrepetition", "noninterruption", "stress", "aspiration",
        "nonpermutability", "free_occurrence", "biuniqueness", "repair",
        "segmental", "suprasegmental", "pausing", "proform", "play_language", "idiom",
    ]:
        mod = importlib.import_module(f"planars.{name}")
        params = getattr(mod, "_REQUIRED_PARAMS", None)
        if params is not None:
            module_params[name] = set(params)

    errors = []
    for name, mod_params in module_params.items():
        cb_params = cb.get(name, set())
        not_in_codebook = mod_params - cb_params
        if not_in_codebook:
            errors.append(
                f"[{name}] required params not in codebook: "
                f"{sorted(not_in_codebook)}"
            )
    return errors


def _check_diagnostics(codebook: dict) -> List[str]:
    """Check that param names in all diagnostics.tsv files are in codebook.yaml."""
    cb = _codebook_params(codebook)
    diag_files = sorted((ROOT / "coded_data").glob("*/planar_input/diagnostics.tsv"))
    if not diag_files:
        return ["No diagnostics.tsv files found under coded_data/"]

    errors = []
    for diag_path in diag_files:
        lang = diag_path.parent.parent.name
        df = pd.read_csv(diag_path, sep="\t", dtype=str, keep_default_na=False)
        for _, row in df.iterrows():
            class_name = row.get("Class", "").strip()
            params_raw = row.get("Parameters", "").strip()
            if not params_raw:
                continue
            for spec in params_raw.split(","):
                spec = spec.strip()
                name = spec[: spec.index("{")] .strip() if "{" in spec else spec
                if name and name not in cb.get(class_name, set()):
                    errors.append(
                        f"[{lang}/{class_name}] diagnostics.tsv param '{name}' "
                        f"not found in codebook"
                    )
    return errors


def _make_minimal_tsv(params: list[str], extra_params: list[str] = None) -> io.StringIO:
    """Build a minimal filled TSV with one keystone row and one data row.

    Used to run derive functions in isolation during consistency checks, without
    needing real annotation data. All data-row params are set to 'y' so every
    qualification condition evaluates to True and all span keys appear in the result.

    Args:
        params: required parameter column names (e.g. ["free", "multiple"]).
        extra_params: additional columns to include (e.g. extra interaction params).

    Returns:
        An io.StringIO object ready to pass to load_filled_tsv.
    """
    all_params = list(params) + (extra_params or [])
    cols = ["Element", "Position_Name", "Position_Number"] + all_params + ["Comments"]
    header = "\t".join(cols)
    keystone = "\t".join(["ROOT", "v:verbstem", "1"] + ["na"] * len(all_params) + [""])
    data    = "\t".join(["x",    "v:test",    "2"] + ["y"]  * len(all_params) + [""])
    return io.StringIO("\n".join([header, keystone, data]) + "\n")


def _check_diagnostics_vs_classes(diag_classes: dict) -> List[str]:
    """Check diagnostics.tsv entries against diagnostic_classes.yaml.

    For each row in every diagnostics.tsv:
      - The class name must appear in diagnostic_classes.yaml.
      - All required_parameters listed for that class must be present as param columns.
    """
    if not diag_classes:
        return ["diagnostic_classes.yaml not found — skipping class schema check"]

    diag_files = sorted((ROOT / "coded_data").glob("*/planar_input/diagnostics.tsv"))
    if not diag_files:
        return []

    errors = []
    for diag_path in diag_files:
        lang = diag_path.parent.parent.name
        df = pd.read_csv(diag_path, sep="\t", dtype=str, keep_default_na=False)
        for _, row in df.iterrows():
            class_name = row.get("Class", "").strip()
            if not class_name:
                continue

            if class_name not in diag_classes:
                errors.append(
                    f"[{lang}] diagnostics.tsv class '{class_name}' not in "
                    f"diagnostic_classes.yaml"
                )
                continue

            # Check required parameters are present
            params_raw = row.get("Parameters", "").strip()
            present = set()
            for spec in params_raw.split(","):
                spec = spec.strip()
                name = spec[: spec.index("{")].strip() if "{" in spec else spec
                if name:
                    present.add(name)

            required = diag_classes[class_name].get("required_parameters", [])
            missing = [p for p in required if p not in present]
            if missing:
                construction = row.get("Constructions", "").strip()
                errors.append(
                    f"[{lang}/{class_name}/{construction}] missing required "
                    f"parameter(s) from diagnostic_classes.yaml: {missing}"
                )

    return errors


def _check_chart_keys() -> List[str]:
    """Check that chart span label keys exist in the result dicts from each derive fn.

    Runs each derive function against a minimal synthetic TSV and verifies that
    every key referenced in the chart label mappings (_CISC_SPANS, etc.) is
    actually present in the returned result dict.
    """
    from planars import (
        ciscategorial, subspanrepetition, noninterruption, stress, aspiration,
        nonpermutability, free_occurrence, biuniqueness, repair,
        segmental, suprasegmental, pausing, proform, play_language, idiom,
    )
    from planars.charts import (
        _CISC_SPANS, _NONINT_SPANS, _STRESS_SPANS, _ASPIRATION_SPANS,
        _SUBSPAN_CATS, _SUBSPAN_VARIANTS, _SIMPLE_SPANS, _NONPERM_SPANS,
    )
    from planars.io import load_filled_tsv

    errors = []

    def _check(label, derive_fn, span_keys, tsv_io, required_params):
        """Run derive_fn on a synthetic TSV and check that all span_keys are present."""
        try:
            data = load_filled_tsv(tsv_io, required_params, strict=False)
            result = derive_fn(_data=data, strict=False)
        except Exception as e:
            errors.append(f"[{label}] could not run derive function: {e}")
            return
        for key in span_keys:
            if key not in result:
                errors.append(f"[{label}] chart references key '{key}' not in result dict")

    simple_keys = [k for k, _ in _SIMPLE_SPANS]

    # ciscategorial (no module-level _REQUIRED_PARAMS — uses inline required_params)
    cisc_keys = [k for k, _ in _CISC_SPANS]
    _check("ciscategorial", ciscategorial.derive_v_ciscategorial_fractures, cisc_keys,
           _make_minimal_tsv(["V-combines", "N-combines", "A-combines"]),
           {"V-combines"})

    # noninterruption
    nonint_keys = [k for k, _ in _NONINT_SPANS]
    _check("noninterruption", noninterruption.derive_noninterruption_domains, nonint_keys,
           _make_minimal_tsv(["free", "multiple"]),
           noninterruption._REQUIRED_PARAMS)

    # stress
    stress_keys = [k for k, _ in _STRESS_SPANS]
    _check("stress", stress.derive_stress_domains, stress_keys,
           _make_minimal_tsv(["stressed", "obligatory", "independence"],
                              ["left-interaction", "right-interaction"]),
           stress._REQUIRED_PARAMS)

    # aspiration
    asp_keys = [k for k, _ in _ASPIRATION_SPANS]
    _check("aspiration", aspiration.derive_aspiration_domains, asp_keys,
           _make_minimal_tsv(["stressed", "obligatory", "independence"],
                              ["left-interaction", "right-interaction"]),
           aspiration._REQUIRED_PARAMS)

    # subspanrepetition
    subspan_keys = [
        f"{variant}_{cat}_span"
        for cat in _SUBSPAN_CATS
        for variant, _ in _SUBSPAN_VARIANTS
    ]
    _check("subspanrepetition", subspanrepetition.derive_subspanrepetition_spans, subspan_keys,
           _make_minimal_tsv(["widescope_left", "widescope_right", "fillable_botheither_conjunct"]),
           subspanrepetition._REQUIRED_PARAMS)

    # nonpermutability (strict+flexible × complete/partial — all strict spans)
    nonperm_keys = [k for k, _ in _NONPERM_SPANS]
    _check("nonpermutability", nonpermutability.derive_nonpermutability_domains, nonperm_keys,
           _make_minimal_tsv(list(nonpermutability._REQUIRED_PARAMS)),
           nonpermutability._REQUIRED_PARAMS)

    # simple 4-span modules (strict/loose × complete/partial)
    simple_cases = [
        ("free_occurrence",  free_occurrence,  free_occurrence.derive_free_occurrence_spans),
        ("biuniqueness",     biuniqueness,     biuniqueness.derive_biuniqueness_domains),
        ("repair",           repair,           repair.derive_repair_domains),
        ("segmental",        segmental,        segmental.derive_segmental_domains),
        ("suprasegmental",   suprasegmental,   suprasegmental.derive_suprasegmental_domains),
        ("pausing",          pausing,          pausing.derive_pausing_domains),
        ("proform",          proform,          proform.derive_proform_domains),
        ("play_language",    play_language,    play_language.derive_play_language_domains),
        ("idiom",            idiom,            idiom.derive_idiom_domains),
    ]
    for name, mod, derive_fn in simple_cases:
        _check(name, derive_fn, simple_keys,
               _make_minimal_tsv(list(mod._REQUIRED_PARAMS)),
               mod._REQUIRED_PARAMS)

    return errors


def _report_needs_review(codebook: dict, diag_classes: dict) -> int:
    """Print a summary of [NEEDS REVIEW] and [PLACEHOLDER] entries. Returns count."""
    flagged = []
    for analysis in codebook.get("analyses", []):
        name = analysis["name"]
        for field in ("description", "qualification_rule"):
            text = analysis.get(field, "")
            if "[NEEDS REVIEW]" in text or "[PLACEHOLDER]" in text:
                flagged.append(f"codebook.yaml [{name}]: {field}")
                break
        for param in analysis.get("parameters", []):
            for field in ("description",):
                text = param.get(field, "")
                if "[NEEDS REVIEW]" in text or "[PLACEHOLDER]" in text:
                    flagged.append(f"codebook.yaml [{name}/{param['name']}]: {field}")
                    break
    for cls in diag_classes.values():
        status = str(cls.get("status", ""))
        if "[NEEDS REVIEW]" in status or "[PLACEHOLDER]" in status:
            flagged.append(f"diagnostic_classes.yaml [{cls['name']}]: status")
    if flagged:
        print(f"\u26a0  {len(flagged)} entry(ies) marked [NEEDS REVIEW] or [PLACEHOLDER]:")
        for entry in flagged:
            print(f"    {entry}")
    return len(flagged)


def main() -> None:
    """Entry point for `python -m coding check-codebook`.

    Runs four consistency checks and exits with status 1 if any fail:
    1. Every _REQUIRED_PARAMS param in each analysis module is in codebook.yaml.
    2. Every param name in diagnostics.tsv files is in codebook.yaml.
    3. Every span key referenced in charts.py exists in the corresponding derive result.
    4. diagnostics.tsv class names and required parameters match diagnostic_classes.yaml.

    Also prints a summary of [NEEDS REVIEW] / [PLACEHOLDER] entries as a warning
    (does not cause a non-zero exit).
    """
    codebook = _load_codebook()
    diag_classes = _load_diagnostic_classes()
    all_errors: List[str] = []

    print("1. Checking _REQUIRED_PARAMS vs codebook.yaml ...")
    all_errors.extend(_check_required_params(codebook))

    print("2. Checking diagnostics.tsv vs codebook.yaml ...")
    all_errors.extend(_check_diagnostics(codebook))

    print("3. Checking chart span keys vs derive function result dicts ...")
    all_errors.extend(_check_chart_keys())

    print("4. Checking diagnostics.tsv vs diagnostic_classes.yaml ...")
    all_errors.extend(_check_diagnostics_vs_classes(diag_classes))

    print()
    _report_needs_review(codebook, diag_classes)
    print()
    if all_errors:
        print(f"FOUND {len(all_errors)} INCONSISTENCY(IES):")
        for e in all_errors:
            print(f"  \u2717 {e}")
        sys.exit(1)
    else:
        print("\u2713 All checks passed.")


if __name__ == "__main__":
    main()
