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
        "status_sheet_completeness",
        "manifest_class_registration",
        "manifest_dropdown_values",
        "pair_row_position_numbers",
        "drive_state_test_fixtures",
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
