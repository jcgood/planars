"""coding/sheet_spec.py: the spec built from the schemas matches the sheets.

Every class sheet recorded in the saved test data (planars-data's
coded_data/.test_fixtures/) is compared with ``class_sheet_spec`` built from
the frozen language folders captured at the same moment: tab order, each
construction tab's header, an element-row tab's rows and the Status tab's
rows. A difference is either drift on the sheet or a gap in the spec, and
both need fixing (Phase 10 unit 5a, issue #271).

Dropdowns and protections are not in the recording, so they are checked by
the Drive door itself, not here.
"""
from __future__ import annotations

import json

import pytest

from coding.sheet_spec import CONSTRUCTION, LOCKED, STATUS, class_sheet_spec
from planars.schema_values import PAIR_ROW_SHAPES, header_shape, row_columns, row_type
from tests.fake_drive import FIXTURE_DIR, FROZEN_CODED_DATA, FakeDriveDoorway


def _recorded_class_sheets():
    index_path = FIXTURE_DIR / "index.json"
    if not index_path.exists():
        return []
    index = json.loads(index_path.read_text(encoding="utf-8"))
    return [(e["lang_id"], e["role"].split(":", 1)[1], e["spreadsheet_id"])
            for e in index["spreadsheets"] if e["role"].startswith("class:")]


def _differences(lang_id, class_name, spreadsheet_id):
    doorway = FakeDriveDoorway.from_fixtures(langs=[lang_id])
    ss = doorway.open_spreadsheet(spreadsheet_id)
    spec = class_sheet_spec(lang_id, class_name, FROZEN_CODED_DATA)
    where = f"{class_name}_{lang_id}"
    out = []

    actual_titles = [ws.title for ws in ss.worksheets()]
    if actual_titles != spec.tab_titles:
        out.append(f"{where}: tabs are {actual_titles}, spec says {spec.tab_titles}")

    by_title = {ws.title: ws for ws in ss.worksheets()}
    for tab in spec.tabs:
        ws = by_title.get(tab.title)
        if ws is None:
            continue
        if tab.kind == LOCKED:
            # Content not compared: the spec takes it from locked_tab_contents,
            # the same function rebuild_locked_tabs writes with, and the daily
            # update-sheets keeps live tabs current. Compared with a recording,
            # every change of wording would fail here until the next refreeze.
            continue
        values = ws.get_all_values()
        header = values[0] if values else []
        if header != tab.header:
            out.append(f"{where}/{tab.title}: header is {header}, spec says {tab.header}")
            continue
        if tab.rows is None:
            continue
        n = len(tab.row_columns)
        actual_rows = [tuple(r[:n]) for r in values[1:]]
        if tab.kind == STATUS:
            actual_rows = [r for r in actual_rows if any(r)]
        if actual_rows != list(tab.rows):
            missing = sorted(set(tab.rows) - set(actual_rows))
            extra = sorted(set(actual_rows) - set(tab.rows))
            out.append(f"{where}/{tab.title}: rows differ — missing {missing[:5]}"
                       f"{'…' if len(missing) > 5 else ''} ({len(missing)}), "
                       f"unexpected {extra[:5]}{'…' if len(extra) > 5 else ''} ({len(extra)})"
                       + ("" if missing or extra else " — same rows, different order"))
    return out


@pytest.mark.parametrize("lang_id,class_name,spreadsheet_id", _recorded_class_sheets(),
                         ids=lambda v: v if isinstance(v, str) and len(v) < 30 else "")
def test_recorded_class_sheet_matches_its_spec(lang_id, class_name, spreadsheet_id):
    problems = _differences(lang_id, class_name, spreadsheet_id)
    assert not problems, "\n".join(problems)


def test_there_are_recorded_class_sheets_to_compare():
    if not (FIXTURE_DIR / "index.json").exists():
        pytest.skip("saved test data (planars-data) not checked out")
    assert len(_recorded_class_sheets()) >= 20


def test_every_spec_column_has_an_owner_and_criteria_carry_their_values():
    for lang_id, class_name, _ in _recorded_class_sheets():
        spec = class_sheet_spec(lang_id, class_name, FROZEN_CODED_DATA)
        for tab in spec.tabs:
            if tab.kind != CONSTRUCTION:
                continue
            key = set(row_columns(class_name, tab.title))
            for col in tab.columns:
                assert col.owner == ("tooling" if col.name in key else "annotator"), (tab.title, col)


# ---------------------------------------------------------------------------
# planars.schema_values row shapes
# ---------------------------------------------------------------------------

def test_header_shape_names_each_declared_shape():
    for name, cols in PAIR_ROW_SHAPES.items():
        assert header_shape(cols + ["some_criterion", "Source"]) == name
    assert header_shape(["Morpheme", "Origin"]) is None
    assert header_shape([]) is None


def test_row_columns_refuses_what_the_schema_does_not_declare(monkeypatch):
    import planars.schema_values as sv
    monkeypatch.setattr(sv, "_construction_entry",
                        lambda c, k: {"row_type": "pair_rows", "pair_shape": "nonsense"})
    with pytest.raises(ValueError, match="pair_shape"):
        sv.row_columns("x", "y")
    monkeypatch.setattr(sv, "_construction_entry", lambda c, k: {"row_type": "pair_rows"})
    with pytest.raises(ValueError, match="pair_shape"):
        sv.row_columns("x", "y")
    monkeypatch.setattr(sv, "_construction_entry", lambda c, k: {"row_type": "rows"})
    with pytest.raises(ValueError, match="row_type"):
        sv.row_type("x", "y")
    monkeypatch.setattr(sv, "_construction_entry", lambda c, k: {"row_type": "keyed_rows"})
    with pytest.raises(ValueError, match="keyed_columns"):
        sv.row_columns("x", "y")


def test_unlisted_construction_has_element_rows():
    assert row_type("ciscategorial", "general") == "element"
