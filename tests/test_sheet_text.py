"""The Instructions sentences in planar.yaml's sheet_text (Phase 10 unit 11d):
every entry the code reads exists and fills, and a wording mistake fails
loudly instead of reaching an annotator's sheet half-filled."""
import pytest

from coding import schemas
from coding.locked_tabs import _instructions_rows
from coding.sheet_spec import proposal_instructions_rows


def test_every_class_instructions_tab_builds(tmp_path):
    for entry in schemas.load_diagnostic_classes()["classes"]:
        rows = _instructions_rows(entry, "stan1293", tmp_path / "planar.tsv")
        assert rows[0][0].endswith("ANNOTATION INSTRUCTIONS")


def test_proposal_instructions_fill():
    text = "\n".join(r[0] for r in proposal_instructions_rows("stan1293"))
    assert "planar_stan1293" in text and "{" not in text


def test_missing_entry_fails():
    with pytest.raises(ValueError, match="no class_sheet.nonexistent"):
        schemas.sheet_text("class_sheet", "nonexistent")


def test_unsupplied_name_fails(monkeypatch):
    fake = {"sheet_text": {"class_sheet": {"step": "STEP {number} — {typo}"}}}
    monkeypatch.setattr(schemas, "load_planar_schema", lambda: fake)
    with pytest.raises(ValueError, match="typo"):
        schemas.sheet_text("class_sheet", "step", number=1)
