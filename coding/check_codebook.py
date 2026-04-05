"""Check consistency between diagnostic_criteria.yaml, diagnostic_classes.yaml, analysis modules, and charts.py.

Checks:
  1. Every criterion in each module's _REQUIRED_CRITERIA is defined in diagnostic_criteria.yaml
  2. Criterion names in diagnostics_{lang_id}.tsv are defined in diagnostic_criteria.yaml
  3. Chart span label keys match the keys returned by each derive function
  4. diagnostics_{lang_id}.tsv class names and required criteria match diagnostic_classes.yaml
  5. Qualification rule drift: bidirectional module/YAML correspondence, hash sentinel, docstring mirror

Informational reports (not errors):
  6. keystone_active_default "[NEEDS REVIEW]" for active (lang, class) pairs with no override
  7. Schema stubs: classes in diagnostic_classes.yaml with no language coverage
  8. Coverage matrix: language × class grid (✓ = active, - = not collected)

Run:
    python -m coding check-codebook
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import io
import sys
from pathlib import Path
from typing import List

import pandas as pd

from .schemas import load_diagnostic_classes as _load_dc, load_diagnostic_criteria as _load_crit

ROOT = Path(__file__).resolve().parent.parent


def _load_codebook() -> dict:
    """Return diagnostic_criteria.yaml as a dict (via shared cached loader)."""
    return _load_crit()


def _load_diagnostic_classes() -> dict:
    """Return diagnostic_classes.yaml keyed by class name (via shared cached loader).

    Returns a dict keyed by class name:
        {class_name: {"required_criteria": [...], "specificity": str, ...}}
    """
    data = _load_dc()
    return {cls["name"]: cls for cls in data.get("classes", [])}


def _codebook_criteria(codebook: dict) -> dict[str, set[str]]:
    """Return {analysis_name: {criterion_name, ...}} from codebook."""
    return {
        a["name"]: {p["name"] for p in a.get("diagnostic_criteria", [])}
        for a in codebook.get("analyses", [])
    }


def _check_required_criteria(codebook: dict) -> List[str]:
    """Check that every required criterion in each module is defined in diagnostic_criteria.yaml."""
    import importlib

    cb = _codebook_criteria(codebook)
    # ciscategorial uses inline required_criteria rather than a module-level constant.
    # All other modules expose _REQUIRED_CRITERIA at module level.
    module_params: dict[str, set] = {
        "ciscategorial": {"V-combines", "N-combines", "A-combines"},
    }
    for name in [
        "subspanrepetition", "noninterruption", "metrical",
        "nonpermutability", "free_occurrence", "biuniqueness", "repair",
        "segmental", "tonal", "tonosegmental", "intonational",
        "pausing", "proform", "play_language", "idiom",
    ]:
        mod = importlib.import_module(f"planars.{name}")
        params = getattr(mod, "_REQUIRED_CRITERIA", None)
        if params is not None:
            module_params[name] = set(params)

    errors = []
    for name, mod_params in module_params.items():
        cb_params = cb.get(name, set())
        not_in_codebook = mod_params - cb_params
        if not_in_codebook:
            errors.append(
                f"[{name}] required criteria not in codebook: "
                f"{sorted(not_in_codebook)}"
            )
    return errors


def _check_diagnostics(codebook: dict) -> List[str]:
    """Check that criterion names in all diagnostics_{lang_id}.tsv files are in diagnostic_criteria.yaml."""
    cb = _codebook_criteria(codebook)
    diag_files = sorted((ROOT / "coded_data").glob("*/planar_input/diagnostics_*.tsv"))
    if not diag_files:
        return ["No diagnostics_*.tsv files found under coded_data/"]

    errors = []
    for diag_path in diag_files:
        lang = diag_path.parent.parent.name
        df = pd.read_csv(diag_path, sep="\t", dtype=str, keep_default_na=False)
        for _, row in df.iterrows():
            class_name = row.get("Class", "").strip()
            params_raw = row.get("Criteria", "").strip()
            if not params_raw:
                continue
            for spec in params_raw.split(","):
                spec = spec.strip()
                name = spec[: spec.index("{")] .strip() if "{" in spec else spec
                if name and name not in cb.get(class_name, set()):
                    errors.append(
                        f"[{lang}/{class_name}] diagnostics_{lang}.tsv criterion '{name}' "
                        f"not found in codebook"
                    )
    return errors


def _make_minimal_tsv(params: list[str], extra_params: list[str] = None) -> io.StringIO:
    """Build a minimal filled TSV with one keystone row and one data row.

    Used to run derive functions in isolation during consistency checks, without
    needing real annotation data. All data-row params are set to 'y' so every
    qualification condition evaluates to True and all span keys appear in the result.

    Args:
        params: required criterion column names (e.g. ["free", "multiple"]).
        extra_params: additional columns to include (e.g. extra interaction criteria).

    Returns:
        An io.StringIO object ready to pass to load_filled_tsv.
    """
    all_params = list(params) + (extra_params or [])
    cols = ["Element", "Position_Name", "Position_Number"] + all_params + ["Source", "Comments"]
    header = "\t".join(cols)
    keystone = "\t".join(["ROOT", "v:verbstem", "1"] + ["na"] * len(all_params) + ["", ""])
    data    = "\t".join(["x",    "v:test",    "2"] + ["y"]  * len(all_params) + ["", ""])
    return io.StringIO("\n".join([header, keystone, data]) + "\n")


def _check_diagnostics_vs_classes(diag_classes: dict) -> List[str]:
    """Check diagnostics_{lang_id}.tsv entries against diagnostic_classes.yaml.

    For each row in every diagnostics_{lang_id}.tsv:
      - The class name must appear in diagnostic_classes.yaml.
      - All required_criteria listed for that class must be present as criterion columns.
      - No criterion may appear that is outside the allowed set
        (required_criteria ∪ optional_criteria) for the class.
    """
    if not diag_classes:
        return ["diagnostic_classes.yaml not found — skipping class schema check"]

    diag_files = sorted((ROOT / "coded_data").glob("*/planar_input/diagnostics_*.tsv"))
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
                    f"[{lang}] diagnostics_{lang}.tsv class '{class_name}' not in "
                    f"diagnostic_classes.yaml"
                )
                continue

            # Check required criteria are present
            params_raw = row.get("Criteria", "").strip()
            present = set()
            for spec in params_raw.split(","):
                spec = spec.strip()
                name = spec[: spec.index("{")].strip() if "{" in spec else spec
                if name:
                    present.add(name)

            construction = row.get("Constructions", "").strip()

            required = diag_classes[class_name].get("required_criteria", [])
            missing = [p for p in required if p not in present]
            if missing:
                errors.append(
                    f"[{lang}/{class_name}/{construction}] missing required "
                    f"diagnostic criterion(ia) from diagnostic_classes.yaml: {missing}"
                )

            # Check no undeclared criteria are used (opt-in model)
            optional = diag_classes[class_name].get("optional_criteria", [])
            allowed = set(required) | set(optional)
            extra = sorted(present - allowed)
            if extra:
                errors.append(
                    f"[{lang}/{class_name}/{construction}] diagnostic criterion(ia) not in "
                    f"diagnostic_classes.yaml allowed set: {extra}"
                )

    return errors


def _check_chart_keys() -> List[str]:
    """Check that chart span label keys exist in the result dicts from each derive fn.

    Runs each derive function against a minimal synthetic TSV and verifies that
    every key referenced in the chart label mappings (_CISC_SPANS, etc.) is
    actually present in the returned result dict.
    """
    from planars import (
        ciscategorial, subspanrepetition, noninterruption,
        metrical, nonpermutability, free_occurrence, biuniqueness, repair,
        segmental, tonal, tonosegmental, intonational,
        pausing, proform, play_language, idiom,
    )
    from planars.charts import (
        _CISC_SPANS, _NONINT_SPANS, _METRICAL_BLOCKED_SPANS,
        _SUBSPAN_CATS, _SUBSPAN_VARIANTS, _SIMPLE_SPANS, _NONPERM_SPANS,
    )
    from planars.io import load_filled_tsv

    errors = []

    def _check(label, derive_fn, span_keys, tsv_io, required_criteria):
        """Run derive_fn on a synthetic TSV and check that all span_keys are present."""
        try:
            data = load_filled_tsv(tsv_io, required_criteria, strict=False)
            result = derive_fn(_data=data, strict=False)
        except Exception as e:
            errors.append(f"[{label}] could not run derive function: {e}")
            return
        for key in span_keys:
            if key not in result:
                errors.append(f"[{label}] chart references key '{key}' not in result dict")

    simple_keys = [k for k, _ in _SIMPLE_SPANS]

    # ciscategorial (no module-level _REQUIRED_CRITERIA — uses inline required_criteria)
    cisc_keys = [k for k, _ in _CISC_SPANS]
    _check("ciscategorial", ciscategorial.derive_v_ciscategorial_fractures, cisc_keys,
           _make_minimal_tsv(["V-combines", "N-combines", "A-combines"]),
           {"V-combines"})

    # noninterruption
    nonint_keys = [k for k, _ in _NONINT_SPANS]
    _check("noninterruption", noninterruption.derive_noninterruption_domains, nonint_keys,
           _make_minimal_tsv(["free", "multiple"]),
           noninterruption._REQUIRED_CRITERIA)

    # metrical (blocked-span: accented/obligatory/independence)
    metr_keys = [k for k, _ in _METRICAL_BLOCKED_SPANS]
    _check("metrical", metrical.derive_metrical_domains, metr_keys,
           _make_minimal_tsv(["accented", "obligatory", "independence"]),
           metrical._REQUIRED_CRITERIA)

    # subspanrepetition
    subspan_keys = [
        f"{variant}_{cat}_span"
        for cat in _SUBSPAN_CATS
        for variant, _ in _SUBSPAN_VARIANTS
    ]
    _check("subspanrepetition", subspanrepetition.derive_subspanrepetition_spans, subspan_keys,
           _make_minimal_tsv(["widescope_left", "widescope_right", "fillable_botheither_conjunct"]),
           subspanrepetition._REQUIRED_CRITERIA)

    # nonpermutability (strict+flexible × complete/partial — all strict spans)
    nonperm_keys = [k for k, _ in _NONPERM_SPANS]
    _check("nonpermutability", nonpermutability.derive_nonpermutability_domains, nonperm_keys,
           _make_minimal_tsv(list(nonpermutability._REQUIRED_CRITERIA)),
           nonpermutability._REQUIRED_CRITERIA)

    # simple 4-span modules (strict/loose × complete/partial)
    simple_cases = [
        ("free_occurrence",       free_occurrence.derive_free_occurrence_spans,  free_occurrence._REQUIRED_CRITERIA),
        ("biuniqueness",          biuniqueness.derive_biuniqueness_domains,      biuniqueness._REQUIRED_CRITERIA),
        ("repair",                repair.derive_repair_domains,                  repair._REQUIRED_CRITERIA),
        ("segmental",             segmental.derive_segmental_domains,        segmental._REQUIRED_CRITERIA),
        ("tonal",                 tonal.derive_tonal_domains,                tonal._REQUIRED_CRITERIA),
        ("tonosegmental",         tonosegmental.derive_tonosegmental_domains, tonosegmental._REQUIRED_CRITERIA),
        ("intonational",          intonational.derive_intonational_domains,   intonational._REQUIRED_CRITERIA),
        ("pausing",               pausing.derive_pausing_domains,             pausing._REQUIRED_CRITERIA),
        ("proform",               proform.derive_proform_domains,             proform._REQUIRED_CRITERIA),
        ("play_language",         play_language.derive_play_language_domains, play_language._REQUIRED_CRITERIA),
        ("idiom",                 idiom.derive_idiom_domains,                 idiom._REQUIRED_CRITERIA),
    ]
    for name, derive_fn, req_criteria in simple_cases:
        _check(name, derive_fn, simple_keys,
               _make_minimal_tsv(list(req_criteria)),
               req_criteria)

    return errors


def _discover_analysis_modules() -> set[str]:
    """Return set of module names in planars/ that expose a `derive` attribute.

    Scans planars/*.py (excluding __init__, __main__, and non-analysis files)
    and returns names of modules that define a `derive` callable at module level.
    This avoids hardcoding the module list and auto-discovers new modules.
    """
    planars_dir = ROOT / "planars"
    names: set[str] = set()
    skip = {"__init__", "__main__", "io", "spans", "reports", "charts",
            "cli", "html_report", "languages"}
    for path in sorted(planars_dir.glob("*.py")):
        name = path.stem
        if name in skip:
            continue
        try:
            mod = importlib.import_module(f"planars.{name}")
        except Exception:
            continue
        if hasattr(mod, "derive"):
            names.add(name)
    return names


def _check_qualification_rule_drift(diag_classes: dict) -> List[str]:
    """Check qualification rule bidirectional correspondence, hash sentinel, and docstring.

    Bidirectional correspondence (dynamic — no hardcoded module list):
      - YAML class with qualification_rule but no corresponding module: WARNING
        (expected during development; does not exit 1)
      - Python module with no YAML class: HARD ERROR (always a mistake; exits 1)

    Hash sentinel (hash lives in YAML as qualification_rule_hash):
      - qualification_rule_hash missing from YAML: WARNING (new class, not yet stamped)
      - Hash present but wrong: HARD ERROR (rule edited without review; exits 1)

    Docstring mirror:
      - Normalised qualification_rule text not found in normalised module source: WARNING

    Hash is SHA-256[:8] of the whitespace-normalised qualification_rule text.
    Run `python -m coding sync-qualification-hashes --apply` to stamp hashes after
    a module has been reviewed and updated.
    """
    errors = []
    analysis_modules = _discover_analysis_modules()
    yaml_classes_with_rule = {name for name, cls in diag_classes.items()
                               if cls.get("qualification_rule", "")}

    # Module with no YAML class → hard error
    for name in sorted(analysis_modules):
        if name not in diag_classes:
            errors.append(
                f"[{name}] planars/{name}.py has a `derive` attribute but no entry in "
                f"diagnostic_classes.yaml — add the class definition or remove the module"
            )

    # YAML class with rule but no module → warning only
    for name in sorted(yaml_classes_with_rule):
        if name not in analysis_modules:
            print(f"  \u26a0  [{name}] diagnostic_classes.yaml has a qualification_rule "
                  f"but planars/{name}.py has no `derive` attribute "
                  f"(expected during development)")

    # Hash sentinel and docstring mirror for classes that have both YAML and module
    for name in sorted(yaml_classes_with_rule & analysis_modules):
        cls = diag_classes[name]
        qr = cls["qualification_rule"]
        normalized_qr = " ".join(qr.split())
        expected_hash = hashlib.sha256(normalized_qr.encode()).hexdigest()[:8]

        yaml_hash = cls.get("qualification_rule_hash")
        if yaml_hash is None:
            print(f"  \u26a0  [{name}] qualification_rule_hash not set in "
                  f"diagnostic_classes.yaml (expected: {expected_hash!r}) — "
                  f"run: python -m coding sync-qualification-hashes --apply --class {name}")
        elif yaml_hash != expected_hash:
            errors.append(
                f"[{name}] qualification_rule_hash mismatch: YAML has {yaml_hash!r} but "
                f"qualification_rule hashes to {expected_hash!r} — "
                f"the rule was edited without a module review cycle; "
                f"run: python -m coding generate-rule-update-prompt {name}"
            )

        spec = importlib.util.find_spec(f"planars.{name}")
        if spec and spec.origin:
            try:
                source_normalized = " ".join(
                    Path(spec.origin).read_text(encoding="utf-8").split()
                )
                if normalized_qr not in source_normalized:
                    print(f"  \u26a0  [{name}] qualification_rule text not found in module "
                          f"source — update the 'Qualification rule' docstring section")
            except Exception:
                pass

    return errors


def _report_keystone_active_unresolved(
    diag_classes: dict,
    coverage: dict[str, list[str]],
    root: Path = ROOT,
) -> int:
    """Warn when an active (lang, class) pair has keystone_active_default: "[NEEDS REVIEW]"
    and no language-level keystone_active override.

    A "[NEEDS REVIEW]" default means the linguistic question is unresolved and the class
    will silently treat the keystone as inactive (False). This is usually fine during
    development, but coordinators should know which active classes are still unresolved
    so they can make an explicit decision when evidence arrives.

    Returns the count of unresolved pairs (informational, not an error).
    """
    import yaml as _yaml

    unresolved: list[tuple[str, str]] = []  # (lang_id, class_name)

    for class_name, lang_ids in sorted(coverage.items()):
        cls = diag_classes.get(class_name, {})
        default = cls.get("keystone_active_default", "")
        if not (isinstance(default, str) and "[NEEDS REVIEW]" in default):
            continue
        for lang_id in sorted(lang_ids):
            yaml_path = root / "coded_data" / lang_id / "planar_input" / f"diagnostics_{lang_id}.yaml"
            if not yaml_path.exists():
                unresolved.append((lang_id, class_name))
                continue
            lang_data = _yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            class_entry = (lang_data.get("classes") or {}).get(class_name, {})
            if "keystone_active" not in class_entry:
                unresolved.append((lang_id, class_name))

    if not unresolved:
        print("  All active classes have a resolved keystone_active.")
        return 0

    print(f"  {len(unresolved)} active (language, class) pair(s) with "
          f"keystone_active_default: \"[NEEDS REVIEW]\" and no language override:")
    for lang_id, class_name in unresolved:
        print(f"    [{lang_id}/{class_name}] add keystone_active: true/false to "
              f"diagnostics_{lang_id}.yaml when the linguistic question is resolved")
    return len(unresolved)


def _report_needs_review(codebook: dict, diag_classes: dict) -> int:
    """Print a summary of [NEEDS REVIEW] and [PLACEHOLDER] entries. Returns count."""
    flagged = []
    for analysis in codebook.get("analyses", []):
        name = analysis["name"]
        for field in ("description", "qualification_rule"):
            text = analysis.get(field, "")
            if "[NEEDS REVIEW]" in text or "[PLACEHOLDER]" in text:
                flagged.append(f"diagnostic_criteria.yaml [{name}]: {field}")
                break
        for param in analysis.get("diagnostic_criteria", []):
            for field in ("description",):
                text = param.get(field, "")
                if "[NEEDS REVIEW]" in text or "[PLACEHOLDER]" in text:
                    flagged.append(f"diagnostic_criteria.yaml [{name}/{param['name']}]: {field}")
                    break
    for cls in diag_classes.values():
        status = str(cls.get("status", ""))
        if "[NEEDS REVIEW]" in status or "[PLACEHOLDER]" in status:
            flagged.append(f"diagnostic_classes.yaml [{cls['name']}]: status")
        cr = str(cls.get("collection_required", ""))
        if "[NEEDS COORDINATOR INPUT]" in cr:
            flagged.append(
                f"diagnostic_classes.yaml [{cls['name']}]: collection_required — "
                f"coordinator decision needed (set to 'y' or 'n')"
            )
    if flagged:
        print(f"\u26a0  {len(flagged)} entry(ies) marked [NEEDS REVIEW], [PLACEHOLDER], or [NEEDS COORDINATOR INPUT]:")
        for entry in flagged:
            print(f"    {entry}")
    return len(flagged)


def _collect_coverage(root: Path = ROOT) -> dict[str, list[str]]:
    """Return {class_name: [lang_id, ...]} for all active classes across all diagnostics TSVs.

    Args:
        root: repository root to search under (default ROOT; tests pass tmp_path here).
    """
    coverage: dict[str, list[str]] = {}
    for diag_path in sorted((root / "coded_data").glob("*/planar_input/diagnostics_*.tsv")):
        lang = diag_path.parent.parent.name
        df = pd.read_csv(diag_path, sep="\t", dtype=str, keep_default_na=False)
        for _, row in df.iterrows():
            class_name = row.get("Class", "").strip()
            if class_name:
                coverage.setdefault(class_name, []).append(lang)
    return coverage


def _report_schema_stubs(diag_classes: dict, coverage: dict[str, list[str]]) -> int:
    """Print schema stubs for classes in diagnostic_classes.yaml with no language coverage.

    A schema stub is the ready-to-paste diagnostics_{lang_id}.tsv row derived from the
    schema definition — the minimal instantiation before language-specific choices are made.
    Distinct from 'planar template', which refers to the planar structure.

    Returns the count of uncovered classes (informational, not an error).
    """
    uncovered = [name for name in diag_classes if name not in coverage]
    if not uncovered:
        print("  All schema classes have at least one language.")
        return 0

    print(f"  {len(uncovered)} class(es) with no language coverage.")
    print("  Paste into diagnostics_{{lang_id}}.tsv and adjust constructions/criteria as needed:\n")
    for name in uncovered:
        cls = diag_classes[name]
        specificity = cls.get("specificity", "general")
        required = cls.get("required_criteria", [])
        if specificity == "general":
            constructions = "general"
        else:
            known = cls.get("known_constructions", [])
            constructions = ", ".join(known) if known else "CONSTRUCTION_NAME"
        criteria = ", ".join(required) if required else "CRITERION"
        print(f"  {name}\t{{lang_id}}\t{constructions}\t{criteria}")
    return len(uncovered)


def _report_coverage_matrix(
    diag_classes: dict,
    coverage: dict[str, list[str]],
    lang_ids: list[str],
) -> None:
    """Print a language × class coverage matrix (✓ = active, - = not collected)."""
    if not lang_ids or not diag_classes:
        return

    col_w = max(len(l) for l in lang_ids) + 2
    row_w = max(len(name) for name in diag_classes) + 2

    header = " " * (row_w + 2) + "".join(l.ljust(col_w) for l in lang_ids)
    print(f"  {header}")
    for name in diag_classes:
        langs_with = set(coverage.get(name, []))
        cells = "".join(("✓" if l in langs_with else "-").ljust(col_w) for l in lang_ids)
        print(f"  {name.ljust(row_w)}  {cells}")


def main() -> None:
    """Entry point for `python -m coding check-codebook`.

    Runs five consistency checks (exit 1 if any fail) then three informational reports:
    1. Every _REQUIRED_CRITERIA criterion in each analysis module is in diagnostic_criteria.yaml.
    2. Every criterion name in diagnostics_{lang_id}.tsv files is in diagnostic_criteria.yaml.
    3. Every span key referenced in charts.py exists in the corresponding derive result.
    4. diagnostics_{lang_id}.tsv class names and required criteria match diagnostic_classes.yaml.
    5. Qualification rule drift: bidirectional module/YAML correspondence, hash sentinel,
       docstring mirror.
    6. keystone_active_default "[NEEDS REVIEW]" for active classes with no language override.
    7. Schema stubs: classes with no language coverage (ready-to-paste TSV rows).
    8. Coverage matrix: language × class grid.
    """
    codebook = _load_codebook()
    diag_classes = _load_diagnostic_classes()
    all_errors: List[str] = []

    print("1. Checking _REQUIRED_CRITERIA vs diagnostic_criteria.yaml ...")
    all_errors.extend(_check_required_criteria(codebook))

    print("2. Checking diagnostics_{lang_id}.tsv vs diagnostic_criteria.yaml ...")
    all_errors.extend(_check_diagnostics(codebook))

    print("3. Checking chart span keys vs derive function result dicts ...")
    all_errors.extend(_check_chart_keys())

    print("4. Checking diagnostics_{lang_id}.tsv criteria vs diagnostic_classes.yaml ...")
    all_errors.extend(_check_diagnostics_vs_classes(diag_classes))

    print("5. Checking qualification rule drift (hash sentinel + docstring) ...")
    all_errors.extend(_check_qualification_rule_drift(diag_classes))

    coverage = _collect_coverage()
    lang_ids = sorted({l for langs in coverage.values() for l in langs})

    print()
    _report_needs_review(codebook, diag_classes)

    print()
    print("6. keystone_active_default [NEEDS REVIEW] for active classes:")
    _report_keystone_active_unresolved(diag_classes, coverage)

    print()
    print("6b. Open policy questions — classes with unresolved keystone_active_default (no active instances yet):")
    pending_defaults = sorted(
        name for name, cls in diag_classes.items()
        if "[NEEDS REVIEW]" in str(cls.get("keystone_active_default", ""))
        and name not in coverage
    )
    if pending_defaults:
        print(f"  {len(pending_defaults)} class(es) — not yet blocking, but resolve when a language adopts the class:")
        for name in pending_defaults:
            print(f"    [{name}] add keystone_active: true/false to diagnostics_{{lang_id}}.yaml at onboarding")
    else:
        print("  All classes with [NEEDS REVIEW] keystone_active_default already have active instances (see section 6).")

    print()
    print("7. Schema stubs (classes with no language coverage):")
    _report_schema_stubs(diag_classes, coverage)

    print()
    print("8. Coverage matrix:")
    _report_coverage_matrix(diag_classes, coverage, lang_ids)

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
