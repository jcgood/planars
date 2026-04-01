#!/usr/bin/env python3
"""Validation for diagnostics_{lang_id}.tsv files.

Called by generate-sheets and validate-coding to flag issues before sheets
are created or revalidated.

Checks:
  1. Structural     — required columns present; Language matches lang_id
  2. Brace syntax   — criterion specs like stressed{y/n/both} are well-formed
  3. Criterion names — base criterion names are defined in diagnostic_criteria.yaml
  4. Class names    — class corresponds to a planars/ analysis module
  5. Constructions  — 'general' must be alone; no duplicates within a class
  6. Glottocode     — lang_id matches Glottocode format; advisory if not cached
  7. Schema conform — every criterion is in the allowed set for its class
                      (required_criteria ∪ optional_criteria in
                      diagnostic_classes.yaml)
  8. Required classes — every class with collection_required: true in
                      diagnostic_classes.yaml must be present (no-op while
                      values are '[NEEDS COORDINATOR INPUT]')
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Dict, List, Set

from .validate import ValidationIssue
from .glottolog import is_valid_format as _is_valid_glottocode, cached_entry as _cached_glottocode
from .schemas import load_diagnostic_classes, load_diagnostic_criteria

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REQUIRED_COLS = {"Class", "Language", "Constructions", "Criteria"}


def _known_analysis_classes() -> Set[str]:
    """Return the set of valid class names by inspecting planars/ modules."""
    classes = set()
    planars_dir = ROOT / "planars"
    for path in planars_dir.glob("*.py"):
        if path.stem.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"planars.{path.stem}")
            if hasattr(mod, "derive"):
                classes.add(path.stem)
        except Exception:
            pass
    return classes


def _diagnostic_class_allowed_criteria() -> Dict[str, Set[str]]:
    """Return {class_name: set_of_allowed_param_names} from diagnostic_classes.yaml.

    Allowed = required_criteria ∪ optional_criteria.
    Returns an empty dict if the schema file is missing.
    """
    data = load_diagnostic_classes()
    result: Dict[str, Set[str]] = {}
    for cls in data.get("classes", []):
        name = cls.get("name", "")
        if not name:
            continue
        allowed: Set[str] = set(cls.get("required_criteria", []))
        allowed.update(cls.get("optional_criteria", []))
        result[name] = allowed
    return result


def _required_collection_classes() -> Set[str]:
    """Return class names where collection_required: true in diagnostic_classes.yaml.

    Classes with collection_required: false or '[NEEDS COORDINATOR INPUT]' are excluded.
    Returns an empty set if the schema file is missing or no classes are marked true.
    """
    data = load_diagnostic_classes()
    return {
        cls["name"]
        for cls in data.get("classes", [])
        if cls.get("name") and cls.get("collection_required") is True
    }


def _codebook_criterion_names() -> Set[str]:
    """Return all criterion names defined in diagnostic_criteria.yaml."""
    cb = load_diagnostic_criteria()
    names: Set[str] = set()
    for analysis in cb.get("analyses", []):
        for param in analysis.get("diagnostic_criteria", []):
            name = param.get("name", "").strip()
            if name:
                names.add(name)
    return names


def _parse_criterion_specs(value: str) -> List[tuple]:
    """Parse a comma-separated criterion specs string into (name, values, raw_spec) tuples.

    Does not raise — returns what it can and lets the caller emit ValidationIssues.
    """
    results = []
    for spec in [s.strip() for s in value.split(",") if s.strip()]:
        if "{" in spec:
            close = spec.find("}")
            open_ = spec.find("{")
            name = spec[:open_].strip()
            if close == -1:
                results.append((name, None, spec))  # None signals malformed
            else:
                values_str = spec[open_ + 1:close]
                values = [v.strip() for v in values_str.split("/") if v.strip()]
                results.append((name, values if values else None, spec))
        else:
            results.append((spec, ["y", "n"], spec))
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_diagnostics_yaml(data: dict, lang_id: str) -> List[ValidationIssue]:
    """Validate a diagnostics_{lang_id}.yaml dict for a given language.

    Parameters
    ----------
    data    : parsed YAML dict (top-level keys: language, classes)
    lang_id : expected language ID (from the planar filename)
    """
    issues: List[ValidationIssue] = []
    filename = f"diagnostics_{lang_id}.yaml"

    # ------------------------------------------------------------------
    # 1. Top-level structure
    # ------------------------------------------------------------------
    if not isinstance(data, dict):
        issues.append(ValidationIssue("error", filename, "YAML root must be a mapping"))
        return issues

    yaml_lang = str(data.get("language", "")).strip()
    if yaml_lang != lang_id:
        issues.append(ValidationIssue(
            "error", filename,
            f"'language' value '{yaml_lang}' does not match expected lang_id '{lang_id}'"
        ))

    classes = data.get("classes")
    if not isinstance(classes, dict) or not classes:
        issues.append(ValidationIssue("error", filename, "Missing or empty 'classes' mapping"))
        return issues

    known_criteria   = _codebook_criterion_names()
    known_classes    = _known_analysis_classes()
    allowed_by_class = _diagnostic_class_allowed_criteria()
    required_classes = _required_collection_classes()

    for class_name, class_data in classes.items():
        location = f"{filename} [{class_name}]"

        if not isinstance(class_data, dict):
            issues.append(ValidationIssue("error", location, "Class entry must be a mapping"))
            continue

        # ------------------------------------------------------------------
        # 2. constructions
        # ------------------------------------------------------------------
        constructions = class_data.get("constructions")
        if not isinstance(constructions, list) or not constructions:
            issues.append(ValidationIssue(
                "error", location, "'constructions' must be a non-empty list"
            ))
            constructions = []

        if "general" in constructions and len(constructions) > 1:
            issues.append(ValidationIssue(
                "error", location,
                f"'general' must be the only construction when used, but found: {constructions}"
            ))

        seen: Dict[str, int] = {}
        for j, name in enumerate(constructions):
            if name in seen:
                issues.append(ValidationIssue(
                    "error", location, f"Duplicate construction name '{name}'"
                ))
            else:
                seen[name] = j

        # ------------------------------------------------------------------
        # 3. criteria
        # ------------------------------------------------------------------
        criteria = class_data.get("criteria")
        if not isinstance(criteria, dict) or not criteria:
            issues.append(ValidationIssue(
                "error", location, "'criteria' must be a non-empty mapping"
            ))
            criteria = {}

        for crit_name, crit_values in criteria.items():
            if not isinstance(crit_values, list) or not crit_values:
                issues.append(ValidationIssue(
                    "error", location,
                    f"Criterion '{crit_name}' must have a non-empty list of allowed values"
                ))
            # Criterion names vs. codebook
            if known_criteria and crit_name not in known_criteria:
                issues.append(ValidationIssue(
                    "warning", location,
                    f"Diagnostic criterion '{crit_name}' is not defined in diagnostic_criteria.yaml"
                ))

        # ------------------------------------------------------------------
        # 4. Class names vs. analysis modules
        # ------------------------------------------------------------------
        if known_classes and class_name not in known_classes:
            issues.append(ValidationIssue(
                "warning", location,
                f"Class '{class_name}' has no corresponding planars/ analysis module "
                f"(known: {sorted(known_classes)})"
            ))

        # ------------------------------------------------------------------
        # 5. Schema conformance
        # ------------------------------------------------------------------
        if allowed_by_class and class_name in allowed_by_class:
            allowed = allowed_by_class[class_name]
            for crit_name in criteria:
                if crit_name not in allowed:
                    issues.append(ValidationIssue(
                        "warning", location,
                        f"Diagnostic criterion '{crit_name}' is not in the allowed set for "
                        f"class '{class_name}' in diagnostic_classes.yaml "
                        f"(allowed: {sorted(allowed)})"
                    ))

    # ------------------------------------------------------------------
    # 6. Glottocode format + cache advisory
    # ------------------------------------------------------------------
    if not _is_valid_glottocode(lang_id):
        issues.append(ValidationIssue(
            "warning", filename,
            f"Language ID '{lang_id}' does not match Glottocode format "
            f"(expected 4 lowercase letters + 4 digits, e.g. 'arao1248')"
        ))
    elif _cached_glottocode(lang_id) is None:
        issues.append(ValidationIssue(
            "warning", filename,
            f"Language ID '{lang_id}' has not been verified against Glottolog. "
            f"Run: python -m coding lookup-lang {lang_id}"
        ))

    # ------------------------------------------------------------------
    # 7. Required classes must be present
    # ------------------------------------------------------------------
    if required_classes:
        present = set(classes.keys())
        for cls in sorted(required_classes):
            if cls not in present:
                issues.append(ValidationIssue(
                    "error", filename,
                    f"Required class '{cls}' (collection_required: true) is missing"
                ))

    return issues


def validate_diagnostics_df(df, lang_id: str) -> List[ValidationIssue]:
    """Validate a diagnostics_{lang_id}.tsv DataFrame for a given language.

    Parameters
    ----------
    df      : DataFrame read from diagnostics_{lang_id}.tsv
    lang_id : expected language ID (from the planar filename)
    """
    issues: List[ValidationIssue] = []

    # ------------------------------------------------------------------
    # 1. Structural
    # ------------------------------------------------------------------
    missing_cols = _REQUIRED_COLS - set(df.columns)
    if missing_cols:
        issues.append(ValidationIssue(
            "error", f"diagnostics_{lang_id}.tsv",
            f"Missing required columns: {sorted(missing_cols)}"
        ))
        return issues  # can't proceed without structure

    for i, row in df.iterrows():
        lang = str(row.get("Language", "")).strip()
        if lang != lang_id:
            issues.append(ValidationIssue(
                "error", f"row {i + 2}",
                f"Language value '{lang}' does not match expected lang_id '{lang_id}'"
            ))

    # ------------------------------------------------------------------
    # 2. Brace syntax + 3. Param names vs. codebook
    # ------------------------------------------------------------------
    known_criteria = _codebook_criterion_names()

    for i, row in df.iterrows():
        class_name = str(row.get("Class", "")).strip()
        params_raw = str(row.get("Criteria", "")).strip()
        location   = f"row {i + 2} [{class_name}]"

        for name, values, raw_spec in _parse_criterion_specs(params_raw):
            # Brace syntax
            if values is None:
                if "}" not in raw_spec:
                    issues.append(ValidationIssue(
                        "error", location,
                        f"Malformed param spec '{raw_spec}' — missing closing brace"
                    ))
                else:
                    issues.append(ValidationIssue(
                        "error", location,
                        f"Param spec '{raw_spec}' has empty value list"
                    ))
            # Param names vs. codebook (only if codebook loaded successfully)
            if known_criteria and name and name not in known_criteria:
                issues.append(ValidationIssue(
                    "warning", location,
                    f"Diagnostic criterion '{name}' is not defined in diagnostic_criteria.yaml"
                ))

    # ------------------------------------------------------------------
    # 4. Class names vs. analysis modules
    # ------------------------------------------------------------------
    known_classes = _known_analysis_classes()

    for i, row in df.iterrows():
        class_name = str(row.get("Class", "")).strip()
        if not class_name:
            issues.append(ValidationIssue(
                "error", f"row {i + 2}",
                "Empty Class value"
            ))
        elif known_classes and class_name not in known_classes:
            issues.append(ValidationIssue(
                "warning", f"row {i + 2}",
                f"Class '{class_name}' has no corresponding planars/ analysis module "
                f"(known: {sorted(known_classes)})"
            ))

    # ------------------------------------------------------------------
    # 5. Construction naming
    # ------------------------------------------------------------------
    for i, row in df.iterrows():
        class_name     = str(row.get("Class", "")).strip()
        constructions  = [c.strip() for c in str(row.get("Constructions", "")).split(",") if c.strip()]
        location       = f"row {i + 2} [{class_name}]"

        if not constructions:
            issues.append(ValidationIssue(
                "error", location,
                "No constructions listed"
            ))
            continue

        if "general" in constructions and len(constructions) > 1:
            issues.append(ValidationIssue(
                "error", location,
                f"'general' must be the only construction when used, "
                f"but found: {constructions}"
            ))

        seen: Dict[str, int] = {}
        for j, name in enumerate(constructions):
            if name in seen:
                issues.append(ValidationIssue(
                    "error", location,
                    f"Duplicate construction name '{name}'"
                ))
            else:
                seen[name] = j

    # ------------------------------------------------------------------
    # 6. Glottocode format + cache advisory
    # ------------------------------------------------------------------
    if not _is_valid_glottocode(lang_id):
        issues.append(ValidationIssue(
            "warning", f"diagnostics_{lang_id}.tsv",
            f"Language ID '{lang_id}' does not match Glottocode format "
            f"(expected 4 lowercase letters + 4 digits, e.g. 'arao1248')"
        ))
    elif _cached_glottocode(lang_id) is None:
        issues.append(ValidationIssue(
            "warning", f"diagnostics_{lang_id}.tsv",
            f"Language ID '{lang_id}' has not been verified against Glottolog. "
            f"Run: python -m coding lookup-lang {lang_id}"
        ))

    # ------------------------------------------------------------------
    # 7. Schema conformance — params must be in the allowed set for class
    # ------------------------------------------------------------------
    allowed_by_class = _diagnostic_class_allowed_criteria()

    if allowed_by_class:
        for i, row in df.iterrows():
            class_name = str(row.get("Class", "")).strip()
            params_raw = str(row.get("Criteria", "")).strip()
            location   = f"row {i + 2} [{class_name}]"

            if not class_name or class_name not in allowed_by_class:
                continue  # unknown class already flagged in check 4

            allowed = allowed_by_class[class_name]
            for name, _values, _raw in _parse_criterion_specs(params_raw):
                if name and name not in allowed:
                    issues.append(ValidationIssue(
                        "warning", location,
                        f"Diagnostic criterion '{name}' is not in the allowed set for class "
                        f"'{class_name}' in diagnostic_classes.yaml "
                        f"(allowed: {sorted(allowed)})"
                    ))

    # ------------------------------------------------------------------
    # 8. Required classes must be present
    # ------------------------------------------------------------------
    required_classes = _required_collection_classes()
    if required_classes:
        present_classes = {str(row.get("Class", "")).strip() for _, row in df.iterrows()}
        for cls in sorted(required_classes):
            if cls not in present_classes:
                issues.append(ValidationIssue(
                    "error", f"diagnostics_{lang_id}.tsv",
                    f"Required class '{cls}' (collection_required: true in "
                    f"diagnostic_classes.yaml) is missing"
                ))

    return issues
