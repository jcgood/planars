"""Validation tests for data_dependency_schema/ (facts.yaml + preconditions.yaml).

Deliberately does not import anything from planars/coding -- these registries
are meant to be readable and checkable on their own, so this test just loads
the plain YAML/JSON files directly off disk. See
data_dependency_schema/SCHEMA.md for the field-by-field spec.
"""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

SCHEMA_DIR = Path(__file__).parent.parent / "data_dependency_schema"
FACT_SCHEMA_PATH = SCHEMA_DIR / "fact_record.schema.json"
FACTS_PATH = SCHEMA_DIR / "facts.yaml"
PRECONDITION_SCHEMA_PATH = SCHEMA_DIR / "precondition_record.schema.json"
PRECONDITIONS_PATH = SCHEMA_DIR / "preconditions.yaml"
OPERATION_SCHEMA_PATH = SCHEMA_DIR / "operation_record.schema.json"
OPERATIONS_PATH = SCHEMA_DIR / "operations.yaml"


def _load_json(path: Path):
    return json.loads(path.read_text())


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


# ---------------------------------------------------------------------------
# facts.yaml vs fact_record.schema.json
# ---------------------------------------------------------------------------

def test_facts_validate_against_schema():
    schema = _load_json(FACT_SCHEMA_PATH)
    records = _load_yaml(FACTS_PATH)
    jsonschema.validate(instance=records, schema=schema)


def test_facts_have_expected_ids():
    records = _load_yaml(FACTS_PATH)
    ids = {record["id"] for record in records}
    assert ids == {
        "planar_sheet_structure",
        "diagnostics_scope",
        "languages_metadata",
        "qualification_rule_semantics",
        "dependent_construction_element_scope",
        "sheet_change_notification_state",
        "collaborator_notes_surfaced_state",
        "status_sheet_completeness",
        "manifest_class_registration",
        "manifest_dropdown_values",
        "construction_criterion_columns",
        "pair_row_position_numbers",
        "drive_state_test_fixtures",
        "pair_row_construction_set",
    }


def test_every_fact_authoritative_entity_is_among_its_own_locations():
    # The JSON Schema itself can't express this cross-field constraint (see
    # SCHEMA.md's "Known limitations" note) -- checked here instead, as a
    # belt-and-suspenders sanity check on the real registry.
    records = _load_yaml(FACTS_PATH)
    for record in records:
        location_entities = {loc["entity"] for loc in record["locations"]}
        assert record["authoritative"] in location_entities, record["id"]


def test_planar_sheet_structure_fact_is_bidirectional():
    records = _load_yaml(FACTS_PATH)
    record = next(r for r in records if r["id"] == "planar_sheet_structure")
    assert record["cascade"]["direction"] == "bidirectional"
    assert record["drift_risk"]["possible"] is True
    assert record["drift_risk"]["caught_by"]


def test_missing_required_field_fails_fact_validation():
    schema = _load_json(FACT_SCHEMA_PATH)
    invalid = [
        {
            "id": "broken_fact",
            "description": "missing locations/authoritative/cascade/drift_risk",
        }
    ]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid, schema=schema)


def test_drift_risk_possible_without_caught_by_fails_fact_validation():
    schema = _load_json(FACT_SCHEMA_PATH)
    invalid = [
        {
            "id": "broken_fact",
            "description": "drift_risk.possible is true but caught_by is missing",
            "locations": [{"entity": "planar_sheet", "detail": "somewhere"}],
            "authoritative": "planar_sheet",
            "cascade": {"direction": "manual", "mechanism": "a human notices"},
            "drift_risk": {"possible": True, "note": "no mitigation exists"},
        }
    ]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid, schema=schema)


def test_unknown_entity_fails_fact_validation():
    schema = _load_json(FACT_SCHEMA_PATH)
    invalid = [
        {
            "id": "broken_fact",
            "description": "uses an entity not in the vocabulary",
            "locations": [{"entity": "some_made_up_entity", "detail": "somewhere"}],
            "authoritative": "some_made_up_entity",
            "cascade": {"direction": "automatic", "mechanism": "a script"},
            "drift_risk": {"possible": False, "note": "n/a"},
        }
    ]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid, schema=schema)


# ---------------------------------------------------------------------------
# preconditions.yaml vs precondition_record.schema.json
# ---------------------------------------------------------------------------

def test_preconditions_validate_against_schema():
    schema = _load_json(PRECONDITION_SCHEMA_PATH)
    records = _load_yaml(PRECONDITIONS_PATH)
    jsonschema.validate(instance=records, schema=schema)


def test_preconditions_have_expected_ids():
    records = _load_yaml(PRECONDITIONS_PATH)
    ids = {record["id"] for record in records}
    assert ids == {
        "coded_data_clean_tree",
        "coded_data_git_identity_configured",
        "check_notes_documents_scope_authorized",
    }


def test_missing_required_field_fails_precondition_validation():
    schema = _load_json(PRECONDITION_SCHEMA_PATH)
    invalid = [
        {
            "id": "broken_precondition",
            "description": "missing required_by/enforced_by/failure_symptom",
        }
    ]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid, schema=schema)


def test_precondition_gap_field_is_optional():
    # Most records won't have an open gap -- schema must not require it.
    schema = _load_json(PRECONDITION_SCHEMA_PATH)
    valid = [
        {
            "id": "fully_closed_precondition",
            "description": "a precondition with no known open gap",
            "required_by": ["some_module.py (some-command --apply)"],
            "enforced_by": "some_module._check_something()",
            "failure_symptom": "something bad happens",
        }
    ]
    jsonschema.validate(instance=valid, schema=schema)  # no error


# ---------------------------------------------------------------------------
# operations.yaml vs operation_record.schema.json (Phase 4, issue #271)
# ---------------------------------------------------------------------------

def test_operations_validate_against_schema():
    schema = _load_json(OPERATION_SCHEMA_PATH)
    records = _load_yaml(OPERATIONS_PATH)
    jsonschema.validate(instance=records, schema=schema)


def test_every_coding_command_has_an_operation_record():
    # The mechanical half of Phase 4's "done when": a new coding/__main__.py
    # command cannot be added without declaring itself here. Derives the
    # expected id set from _COMMANDS itself rather than a hardcoded list, so
    # this test fails the moment a command is added or removed without a
    # matching operations.yaml entry -- unlike test_operations_have_expected_ids
    # below, which pins the set as of this writing and would need editing on
    # a legitimate addition too, this one never does.
    from coding.__main__ import _COMMANDS

    records = _load_yaml(OPERATIONS_PATH)
    record_ids = {r["id"] for r in records}
    expected_ids = {cli_name.replace("-", "_") for cli_name in _COMMANDS}
    assert record_ids == expected_ids


def test_operations_have_expected_ids():
    records = _load_yaml(OPERATIONS_PATH)
    ids = {record["id"] for record in records}
    assert ids == {
        "capture_drive_state",
        "generate_sheets",
        "generate_notebooks",
        "generate_reports",
        "sync_params",
        "sync_diagnostics_yaml",
        "sync_qualification_hashes",
        "update_sheets",
        "import_sheets",
        "validate_coding",
        "validation_report",
        "restructure_sheets",
        "check_codebook",
        "generate_rule_update_prompt",
        "integrity_check",
        "setup_root_folder",
        "lookup_lang",
        "apply_pending",
        "prune_manifest",
        "check_notes",
        "refresh_dropdowns",
        "import_planar",
        "generate_status_sheet",
        "generate_biuniqueness_allomorphy_sheet",
    }


def test_operation_cli_command_matches_its_id():
    # id is cli_command with hyphens -> underscores; catches a copy-paste
    # mismatch between the two fields within one record.
    records = _load_yaml(OPERATIONS_PATH)
    for record in records:
        assert record["id"] == record["cli_command"].replace("-", "_"), record["id"]


def test_every_operation_fact_reference_exists_in_facts_yaml():
    # Not expressible in JSON Schema (drafts can't reference another file's
    # dynamic enum) -- checked here instead, same belt-and-suspenders
    # approach as the authoritative-in-locations check above.
    fact_ids = {r["id"] for r in _load_yaml(FACTS_PATH)}
    records = _load_yaml(OPERATIONS_PATH)
    for record in records:
        for touched in record["facts_touched"]:
            assert touched["fact"] in fact_ids, (record["id"], touched["fact"])


def test_every_operation_precondition_reference_exists_in_preconditions_yaml():
    precondition_ids = {r["id"] for r in _load_yaml(PRECONDITIONS_PATH)}
    records = _load_yaml(OPERATIONS_PATH)
    for record in records:
        for precondition in record["preconditions"]:
            assert precondition in precondition_ids, (record["id"], precondition)


def test_every_idempotent_claim_has_a_note():
    # The schema already requires idempotency_note on every record; this
    # test is the explicit statement of why that field is required, not
    # merely optional colour -- a bare "idempotent: true" with no reasoning
    # is exactly the unreviewable claim Phase 4's coordinator-review
    # requirement exists to catch.
    records = _load_yaml(OPERATIONS_PATH)
    for record in records:
        assert record["idempotency_note"].strip(), record["id"]


def test_missing_required_field_fails_operation_validation():
    schema = _load_json(OPERATION_SCHEMA_PATH)
    invalid = [
        {
            "id": "broken_operation",
            "cli_command": "broken-operation",
            "description": "missing side_effects/idempotent/etc.",
        }
    ]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid, schema=schema)


def test_operation_missing_idempotency_note_fails_validation():
    schema = _load_json(OPERATION_SCHEMA_PATH)
    invalid = [
        {
            "id": "broken_operation",
            "cli_command": "broken-operation",
            "description": "idempotent is set but no note explains why",
            "side_effects": ["something"],
            "idempotent": True,
            "apply_gate": "--apply",
            "preconditions": [],
            "facts_touched": [],
            "cascades_triggered": [],
            "ordering_constraints": [],
        }
    ]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid, schema=schema)


def test_operation_unknown_fact_role_fails_validation():
    schema = _load_json(OPERATION_SCHEMA_PATH)
    invalid = [
        {
            "id": "broken_operation",
            "cli_command": "broken-operation",
            "description": "facts_touched role is not one of reads/writes/both",
            "side_effects": ["something"],
            "idempotent": True,
            "idempotency_note": "n/a",
            "apply_gate": None,
            "preconditions": [],
            "facts_touched": [{"fact": "planar_sheet_structure", "role": "deletes"}],
            "cascades_triggered": [],
            "ordering_constraints": [],
        }
    ]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid, schema=schema)
