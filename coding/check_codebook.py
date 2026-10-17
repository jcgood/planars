"""Check consistency between diagnostic_criteria.yaml, diagnostic_classes.yaml, analysis modules, and charts.py.

Checks:
  1. Every class's required_criteria, and every criterion a module's _REQUIRED_CRITERIA
     names, is defined in diagnostic_criteria.yaml
  2. Criterion names in diagnostics_{lang_id}.tsv are defined in diagnostic_criteria.yaml
  3. Chart span label keys match the keys returned by each derive function
  4. diagnostics_{lang_id}.tsv class names and required criteria match diagnostic_classes.yaml
  5. Qualification rule drift: bidirectional module/YAML correspondence, hash sentinel, docstring mirror
  6. Per-language criterion value sets vs global schema (hard error: lang declares unknown value;
     warning: schema allows a value the language YAML doesn't declare — may mean the YAML was not
     updated after a new value was added to the schema)

Informational reports (not errors):
  7. keystone_active_default "[NEEDS REVIEW]" for active (lang, class) pairs with no override
  8. Schema stubs: classes in diagnostic_classes.yaml with no language coverage
  9. Coverage matrix: language × class grid (✓ = active, - = not collected)

Run:
    python -m coding check-codebook
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import io
import sys
from pathlib import Path
from typing import List

import pandas as pd

from .schemas import load_diagnostic_classes as _load_dc, load_diagnostic_criteria as _load_crit
from planars.schema_values import (ELEMENT_ROW_COLUMNS, KEYSTONE_NAME, SLOT, TRAILING_COLUMNS,
                                   required_criteria, row_key_of)

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"


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


def _check_placeholders_declared(codebook: dict) -> List[str]:
    """Every criterion value written <like_this> in diagnostic_criteria.yaml is
    declared under value_placeholders (the code implements only those)."""
    from .schemas import placeholder_kind
    errors = []
    for analysis in codebook.get("analyses", []):
        for crit in analysis.get("diagnostic_criteria", []) or []:
            for v in crit.get("values") or []:
                try:
                    placeholder_kind(v)
                except ValueError as e:
                    errors.append(f"[{analysis['name']}/{crit['name']}] {e}")
    return errors


def _check_required_criteria(codebook: dict) -> List[str]:
    """Check that every class's required criteria (diagnostic_classes.yaml),
    and every criterion an analysis module says it reads (its
    _REQUIRED_CRITERIA), are defined in diagnostic_criteria.yaml.

    Most modules read _REQUIRED_CRITERIA from the schema; biuniqueness_deviations
    lists the columns of its morphs/morphemes tabs its rules read, since the
    class-level field is empty for it."""
    import importlib

    cb = _codebook_criteria(codebook)
    module_params: dict[str, set] = {}
    for cls in _load_dc().get("classes", []):
        name = cls["name"]
        params = set(cls.get("required_criteria") or [])
        try:
            mod = importlib.import_module(f"planars.{name}")
        except ModuleNotFoundError:
            mod = None  # a class with no module yet (phrasal_accent)
        params |= set(getattr(mod, "_REQUIRED_CRITERIA", None) or [])
        module_params[name] = params

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
    diag_files = sorted(CODED_DATA.glob("*/lang_setup/diagnostics_*.tsv"))
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
    cols = ELEMENT_ROW_COLUMNS + all_params + TRAILING_COLUMNS
    header = "\t".join(cols)
    keystone = "\t".join(["ROOT", KEYSTONE_NAME, "1"] + ["na"] * len(all_params) + [""] * len(TRAILING_COLUMNS))
    data    = "\t".join(["x",    "v:test",    "2"] + ["y"]  * len(all_params) + [""] * len(TRAILING_COLUMNS))
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

    diag_files = sorted(CODED_DATA.glob("*/lang_setup/diagnostics_*.tsv"))
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
        metrical, nonpermutability, free_occurrence, biuniqueness_deviations, repair,
        segmental, tonal, tonosegmental, intonational,
        pausing, proform, play_language, idiom,
    )
    from planars.reports import _BIUNIQ_VARIANTS
    from planars.charts import (
        _CISC_SPANS, _NONINT_SPANS, _METRICAL_BLOCKED_SPANS,
        _SUBSPAN_CATS, _SUBSPAN_VARIANTS, _SIMPLE_SPANS, _NONPERM_SPANS, _FREEOC_SPANS,
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

    # ciscategorial (no module-level _REQUIRED_CRITERIA; its loader insists only
    # on V-combines, the column its rule reads by name)
    cisc_keys = [k for k, _ in _CISC_SPANS]
    _check("ciscategorial", ciscategorial.derive_v_ciscategorial_fractures, cisc_keys,
           _make_minimal_tsv(sorted(required_criteria("ciscategorial"))),
           {"V-combines"})

    # noninterruption
    nonint_keys = [k for k, _ in _NONINT_SPANS]
    _check("noninterruption", noninterruption.derive_noninterruption_domains, nonint_keys,
           _make_minimal_tsv(sorted(noninterruption._REQUIRED_CRITERIA)),
           noninterruption._REQUIRED_CRITERIA)

    # metrical (blocked-span: accented/obligatory/independence)
    metr_keys = [k for k, _ in _METRICAL_BLOCKED_SPANS]
    _check("metrical", metrical.derive_metrical_domains, metr_keys,
           _make_minimal_tsv(sorted(metrical._REQUIRED_CRITERIA)),
           metrical._REQUIRED_CRITERIA)

    # subspanrepetition
    subspan_keys = [
        f"{variant}_{cat}_span"
        for cat in _SUBSPAN_CATS
        for variant, _ in _SUBSPAN_VARIANTS
    ]
    _check("subspanrepetition", subspanrepetition.derive_subspanrepetition_spans, subspan_keys,
           _make_minimal_tsv(sorted(subspanrepetition._REQUIRED_CRITERIA)),
           subspanrepetition._REQUIRED_CRITERIA)

    # nonpermutability: pair-row model; synthetic _data 6-tuple instead of element TSV.
    nonperm_keys = [k for k, _ in _NONPERM_SPANS]
    _nonperm_pair_df = __import__("pandas").DataFrame(
        [{"Element_A": "a", "Element_B": "b", "scopal": "y"}]
    )
    _nonperm_data = (
        _nonperm_pair_df,
        5,                          # keystone_pos
        {4: "v:left1", 5: KEYSTONE_NAME, 6: "v:right1"},  # pos_to_name
        {4: SLOT, 6: SLOT},         # pos_type
        {4: ["a"], 6: ["b"]},       # pos_to_elements
        {"a": {4}, "b": {6}},       # elem_to_positions
    )
    try:
        _nonperm_result = nonpermutability.derive_nonpermutability_domains(
            _data=_nonperm_data, strict=False
        )
        for key in nonperm_keys:
            if key not in _nonperm_result:
                errors.append(f"[nonpermutability] chart references key '{key}' not in result dict")
    except Exception as e:
        errors.append(f"[nonpermutability] could not run derive function: {e}")

    # free_occurrence: 2-span model (minimal/maximal); keystone_df carries free value.
    _freeoc_keys = [k for k, _ in _FREEOC_SPANS]
    _freeoc_pd = __import__("pandas")
    _freeoc_data_df = _freeoc_pd.DataFrame([
        {"Position_Number": 4, "Element": "elem-L",
         "free": "y", "left-edge-of-free-form": "na", "right-edge-of-free-form": "na",
         "dependent-on-left": "na", "dependent-on-right": "na"},
        {"Position_Number": 6, "Element": "elem-R",
         "free": "n", "left-edge-of-free-form": "na", "right-edge-of-free-form": "y",
         "dependent-on-left": "na", "dependent-on-right": "na"},
    ])
    _freeoc_keystone_df = _freeoc_pd.DataFrame([
        {"Position_Number": 5, "Element": KEYSTONE_NAME,
         "free": "y", "left-edge-of-free-form": "na", "right-edge-of-free-form": "na",
         "dependent-on-left": "na", "dependent-on-right": "na"},
    ])
    _freeoc_data = (
        _freeoc_data_df,
        5,                                        # keystone_pos
        {4: "v:left1", 5: KEYSTONE_NAME, 6: "v:right1"},  # pos_to_name
        list(free_occurrence._REQUIRED_CRITERIA),  # criterion_cols
        _freeoc_keystone_df,
    )
    try:
        _freeoc_result = free_occurrence.derive_free_occurrence_spans(
            _data=_freeoc_data, strict=False
        )
        for key in _freeoc_keys:
            if key not in _freeoc_result:
                errors.append(f"[free_occurrence] chart references key '{key}' not in result dict")
    except Exception as e:
        errors.append(f"[free_occurrence] could not run derive function: {e}")

    # biuniqueness_deviations: one domain per deviating morpheme, each carrying
    # the span keys terms.yaml's label map names. Synthetic _data: does, at a
    # fronted-auxiliary slot, conditioned by the subject.
    _bd_pd = __import__("pandas")
    _bd_data = (
        _bd_pd.DataFrame([{"Morpheme": "do", "forms_relation": "alternate"}]),
        _bd_pd.DataFrame([
            {"Morpheme": "do", "Position_Name": "v:aux", "Form": "do", "occurs_here": "y",
             "conditioning_type": "morphosyntactic", "conditioning_features": "elsewhere",
             "conditioned_by": "", "trigger_filled": ""},
            {"Morpheme": "do", "Position_Name": "v:aux", "Form": "does", "occurs_here": "y",
             "conditioning_type": "morphosyntactic", "conditioning_features": "person=3",
             "conditioned_by": "v:subj", "trigger_filled": "y"},
        ]),
        5,                                                    # keystone_pos
        {3: "v:aux", 4: "v:subj", 5: KEYSTONE_NAME},          # pos_to_name
    )
    try:
        _bd_result = biuniqueness_deviations.derive_biuniqueness_deviations_domains(
            _data=_bd_data, strict=True)
        if not _bd_result["domains"]:
            errors.append("[biuniqueness_deviations] synthetic case produced no domain")
        for d in _bd_result["domains"]:
            for key, _ in _BIUNIQ_VARIANTS:
                if key not in d:
                    errors.append(f"[biuniqueness_deviations] chart references key '{key}' "
                                  f"not in a domain dict")
    except Exception as e:
        errors.append(f"[biuniqueness_deviations] could not run derive function: {e}")

    # simple 4-span modules (strict/loose × complete/partial)
    simple_cases = [
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
                  f"diagnostic_classes_status.yaml (expected: {expected_hash!r}) — "
                  f"run: python -m coding sync-qualification-hashes --apply --class {name}")
        elif yaml_hash != expected_hash:
            errors.append(
                f"[{name}] qualification_rule_hash mismatch: diagnostic_classes_status.yaml has {yaml_hash!r} but "
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


def _check_lang_yaml_criterion_values(codebook: dict) -> List[str]:
    """Check per-language diagnostics YAMLs against global criterion value sets.

    Hard errors (added to all_errors, cause exit 1):
      Language YAML declares a value not present in the global schema — the annotator
      dropdown would accept it but the schema doesn't recognise it.

    Warnings (printed, not exit 1):
      Global schema allows a value that the language YAML doesn't declare — the YAML
      may not have been updated after the schema gained a new value.
    """
    import yaml as _yaml

    schema_values: dict[str, dict[str, frozenset]] = {}
    for analysis in codebook.get("analyses", []):
        crit_map = {}
        for crit in analysis.get("diagnostic_criteria", []):
            vals = crit.get("values", [])
            if vals:
                crit_map[crit["name"]] = frozenset(str(v) for v in vals)
        if crit_map:
            schema_values[analysis["name"]] = crit_map

    errors = []
    for yaml_path in sorted(CODED_DATA.glob("*/lang_setup/diagnostics_*.yaml")):
        lang = yaml_path.parent.parent.name
        data = _yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        for class_name, class_entry in (data.get("classes") or {}).items():
            if not isinstance(class_entry, dict):
                continue
            for crit_name, lang_vals in (class_entry.get("criteria") or {}).items():
                if not isinstance(lang_vals, list):
                    continue
                schema_set = (schema_values.get(class_name) or {}).get(crit_name)
                if schema_set is None:
                    continue  # not in schema — caught by other checks
                lang_set = frozenset(str(v) for v in lang_vals)
                lang_extra = lang_set - schema_set
                if lang_extra:
                    errors.append(
                        f"[{lang}/{class_name}] '{crit_name}' declares value(s) not in "
                        f"diagnostic_criteria.yaml: {sorted(lang_extra)}"
                    )
                schema_extra = schema_set - lang_set
                if schema_extra:
                    print(
                        f"  ⚠  [{lang}/{class_name}] '{crit_name}': schema allows "
                        f"{sorted(schema_extra)} but diagnostics_{lang}.yaml only declares "
                        f"{sorted(lang_set)} — update the YAML if annotators may use "
                        f"these values"
                    )
    return errors


def _check_diagnostics_yaml_exists(root: Path = ROOT) -> List[str]:
    """Every language with a diagnostics_{lang_id}.tsv must have a matching
    diagnostics_{lang_id}.yaml.

    diagnostics_{lang_id}.yaml is the coordinator-facing source of truth;
    diagnostics_{lang_id}.tsv is a derived artifact regenerated from it by
    sync-diagnostics-yaml (data_dependency_schema's diagnostics_scope fact).
    A TSV with no backing YAML has no source of truth behind it -- it could
    be legitimately hand-derived once and never touched again, or it could
    be silently stale, and there is no way to tell the difference. Hard
    error, not a warning: this is a total loss of provenance, not drift in
    an otherwise-intact relationship.
    """
    errors = []
    for tsv_path in sorted((root / "coded_data").glob("*/lang_setup/diagnostics_*.tsv")):
        lang = tsv_path.parent.parent.name
        yaml_path = tsv_path.with_suffix(".yaml")
        if not yaml_path.exists():
            errors.append(
                f"[{lang}] diagnostics_{lang}.tsv exists but diagnostics_{lang}.yaml "
                f"does not — the TSV is a derived artifact with no source of truth "
                f"backing it. Regenerate the YAML (or, if this TSV predates the "
                f"YAML-first workflow, write one by hand and run "
                f"sync-diagnostics-yaml --from-tsv to reconcile)."
            )
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
            yaml_path = root / "coded_data" / lang_id / "lang_setup" / f"diagnostics_{lang_id}.yaml"
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
            flagged.append(f"diagnostic_classes_status.yaml [{cls['name']}]: status")
        cr = str(cls.get("collection_required", ""))
        if "[NEEDS COORDINATOR INPUT]" in cr:
            flagged.append(
                f"diagnostic_classes_status.yaml [{cls['name']}]: collection_required — "
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
    for diag_path in sorted((root / "coded_data").glob("*/lang_setup/diagnostics_*.tsv")):
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


def _check_feeder_constructions(diag_classes: dict) -> List[str]:
    """Every construction another one is built from must say `produces_spans: false`.

    planars.reports.span_constructions() reads that field to decide which tabs
    are analysed for spans; a feeder left unmarked would be passed to the
    class's derive function and crash it (a feeder tab has a different shape —
    the 2026-10-12 data refresh failed exactly this way). Checks the schema
    against itself, so it cannot drift from the code.
    """
    errors = []
    for name, cls in sorted(diag_classes.items()):
        cons = [c for c in (cls.get("constructions") or []) if isinstance(c, dict)]
        by_name = {c.get("name"): c for c in cons}
        for c in cons:
            source = c.get("depends_on")
            if source and by_name.get(source, {}).get("produces_spans") is not False:
                errors.append(
                    f"[{name}] construction '{source}' feeds '{c['name']}' (depends_on) but "
                    f"does not say produces_spans: false in schemas/diagnostic_classes.yaml")
    return errors


def _check_row_shapes(diag_classes: dict) -> List[str]:
    """Every construction declares its row shape fully: a known row_type, a
    pair_shape planar.yaml defines for pair rows, keyed_columns and a key for
    keyed rows. Uses planars.schema_values' own rules, the ones every command
    runs from, so a gap is reported here before a command trips over it."""
    errors = []
    for name, cls in sorted(diag_classes.items()):
        for con in cls.get("constructions") or []:
            if not isinstance(con, dict):
                continue
            try:
                row_key_of(con, f"{name}/{con.get('name')}")
            except ValueError as exc:
                errors.append(f"[{name}] {exc}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding check-codebook` (no flags)."""
    return argparse.ArgumentParser(
        description="Check consistency between schema files and analysis modules."
    )


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for `python -m coding check-codebook`.

    Runs eight consistency checks (exit 1 if any fail) then three informational reports:
    1. Every _REQUIRED_CRITERIA criterion in each analysis module is in diagnostic_criteria.yaml.
    2. Every criterion name in diagnostics_{lang_id}.tsv files is in diagnostic_criteria.yaml.
    3. Every span key referenced in charts.py exists in the corresponding derive result.
    4. diagnostics_{lang_id}.tsv class names and required criteria match diagnostic_classes.yaml.
    5. Qualification rule drift: bidirectional module/YAML correspondence, hash sentinel,
       docstring mirror.
    6. Per-language criterion value sets vs global schema (hard error: unknown value declared;
       warning: schema has values not declared in language YAML).
    7. Every diagnostics_{lang_id}.tsv has a matching diagnostics_{lang_id}.yaml (the source
       of truth it's derived from) — hard error if the YAML is missing entirely.
    7b. Every construction another one depends_on says produces_spans: false.
    7c. Every construction declares its row shape (row_type, pair_shape, keyed_columns/key).
    8. keystone_active_default "[NEEDS REVIEW]" for active classes with no language override.
    9. Schema stubs: classes with no language coverage (ready-to-paste TSV rows).
    10. Coverage matrix: language × class grid.
    """
    if args is None:
        args = build_parser().parse_args()
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

    print("6. Checking per-language criterion value sets vs global schema ...")
    all_errors.extend(_check_lang_yaml_criterion_values(codebook))

    print("7. Checking every diagnostics_{lang_id}.tsv has a matching .yaml ...")
    all_errors.extend(_check_diagnostics_yaml_exists())

    print("7b. Checking feeder constructions are marked produces_spans: false ...")
    all_errors.extend(_check_feeder_constructions(diag_classes))

    print("7c. Checking every construction declares its row shape ...")
    all_errors.extend(_check_row_shapes(diag_classes))

    print("7d. Checking every <placeholder> value is declared ...")
    all_errors.extend(_check_placeholders_declared(codebook))

    coverage = _collect_coverage()
    lang_ids = sorted({l for langs in coverage.values() for l in langs})

    print()
    _report_needs_review(codebook, diag_classes)

    print()
    print("8. keystone_active_default [NEEDS REVIEW] for active classes:")
    _report_keystone_active_unresolved(diag_classes, coverage)

    print()
    print("8b. Open policy questions — classes with unresolved keystone_active_default (no active instances yet):")
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
        print("  All classes with [NEEDS REVIEW] keystone_active_default already have active instances (see section 7).")

    print()
    print("9. Schema stubs (classes with no language coverage):")
    _report_schema_stubs(diag_classes, coverage)

    print()
    print("10. Coverage matrix:")
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
