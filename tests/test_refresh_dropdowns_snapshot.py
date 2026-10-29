"""Snapshot tests for `python -m coding refresh-dropdowns`, run against the fake.

First file migrated to the Drive doorway (plan Phase 0b/1, file 1 of 11). These
snapshots lock the command's behaviour — stdout for both modes, and the full
mutation log for `--apply` — so that later migrations, or any change to the
doorway, must either preserve that behaviour or show exactly what they altered.

**How the pre-migration baseline was taken.** The plan's per-file procedure
asks for a real-Drive dry run before migrating. That is not permitted before
Phase 9, so the substitute was to drive the *unmigrated* code from this same
seeded fake through thin gspread-client and Drive-service shims, and diff its
output against the migrated code's. Both modes matched exactly, with one
intended difference recorded in docs/data-layer-progress.md: opening a
spreadsheet now retries, because `open_spreadsheet` always retries.

**The recorded sheets carry no dropdowns** (capture-drive-state doesn't
record them), so `--apply` here sets every criterion column's dropdown and
the Status column's; the tests at the end seed a wrong one and check it is
put right (#322).

**Regenerating.** These snapshots read each language's setup files from the
frozen copy (`fake_drive.FROZEN_CODED_DATA`), never the live `coded_data/`,
so they change only when the code does or when the saved test data is
refrozen with `python -m coding capture-drive-state --apply`. Either way,
regenerate and review the diff, same workflow as tests/snapshots/:

    PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_refresh_dropdowns_snapshot.py
    git diff tests/snapshots/coordinator/
"""
from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from coding import drive, drive_doorway, refresh_dropdowns
from command_runner import run_command
from fake_drive import (FIXTURE_DIR, FakeDriveDoorway, MANIFEST_FILE_ID,
                        use_frozen_coded_data)
from mutation_checks import assert_no_criterion_writes_onto_trailing_columns
from render_mutations import render

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "refresh_dropdowns"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

# The command reads each language's diagnostics YAML and planar TSV from
# coded_data/, which is a separate repo that a bare worktree may not have.
pytestmark = pytest.mark.skipif(
    not (ROOT / "coded_data").exists(),
    reason="coded_data/ (planars-data) is not checked out",
)


@pytest.fixture()
def fake(monkeypatch, tmp_path):
    """A fake doorway seeded from the recorded capture, wired into the command."""
    doorway = FakeDriveDoorway.from_fixtures()
    use_frozen_coded_data(monkeypatch, tmp_path)
    monkeypatch.setattr(drive, "_load_drive_config", FakeDriveDoorway.drive_config)
    drive_doorway.set_doorway(doorway)
    try:
        yield doorway
    finally:
        drive_doorway.reset_doorway()


def _sheet_id(fake, lang: str, class_name: str) -> str:
    """The Drive ID of one language's class spreadsheet, from the ID file."""
    from coding import drive_ids
    return drive_ids.class_sheet_id(FakeDriveDoorway.drive_config(), lang, class_name)


def run(argv, monkeypatch) -> str:
    monkeypatch.setattr("sys.argv", argv)
    buf = io.StringIO()
    with redirect_stdout(buf):
        run_command(refresh_dropdowns, "refresh-dropdowns")
    return buf.getvalue()


def check_snapshot(name: str, actual: str) -> None:
    path = SNAPSHOT_DIR / name
    if UPDATING:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        pytest.skip(f"updated snapshot {path.relative_to(ROOT)}")
    assert path.exists(), (
        f"Snapshot missing: {path.relative_to(ROOT)}\n"
        f"Run: PLANARS_UPDATE_SNAPSHOTS=1 pytest {Path(__file__).relative_to(ROOT)}"
    )
    assert actual == path.read_text(encoding="utf-8"), (
        f"Output differs from {path.name}. If intended, regenerate with "
        f"PLANARS_UPDATE_SNAPSHOTS=1 and review the diff."
    )


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------

def test_dry_run_output(fake, monkeypatch):
    check_snapshot("dry_run.txt", run(["refresh-dropdowns"], monkeypatch))


def test_dry_run_touches_nothing(fake, monkeypatch):
    """Dry run is the safety property this command's users rely on."""
    run(["refresh-dropdowns"], monkeypatch)
    assert fake.mutations == []


def test_lang_filter_restricts_output(fake, monkeypatch):
    out = run(["refresh-dropdowns", "--lang", "arao1248"], monkeypatch)
    assert "[arao1248]" in out
    assert "[stan1293]" not in out and "[synth0001]" not in out


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def test_apply_output(fake, monkeypatch):
    check_snapshot("apply.txt", run(["refresh-dropdowns", "--apply"], monkeypatch))


def test_apply_mutation_log(fake, monkeypatch):
    """The full write log, reviewed by a human before it became a snapshot.

    Write paths have no pre-migration baseline to diff against, so this review
    is the only barrier between a migration bug and its enshrinement as correct
    behaviour (plan Phase 0b/1, step 5).
    """
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    check_snapshot("apply_mutations.json",
                 json.dumps(fake.mutations, indent=2) + "\n")


def test_apply_mutation_digest(fake, monkeypatch):
    """The same log, rendered for a human: tab titles and column headers resolved.

    This is the artifact to review, not the raw JSON — raw IDs and 0-based
    column indices hid one of the two bugs in #272 through a first reading.
    """
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    check_snapshot("apply_digest.txt", render(fake.mutations))


def test_apply_never_writes_a_cell_value(fake, monkeypatch):
    """The command's whole promise: dropdowns change, annotation data does not.

    Adam's annotations are irreplaceable and annotation is in progress. A
    regression that made this command write values would be exactly the kind of
    silent data loss the data layer work exists to prevent, so it is asserted
    structurally rather than left to snapshot inspection.
    """
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    value_writes = [m for m in fake.mutations
                    if m["op"] in {"update", "update_cell", "append_rows",
                                   "insert_cols", "clear", "values_batch_update"}]
    assert value_writes == []
    request_types = {m["request_type"] for m in fake.mutations
                     if m["op"] == "batch_request"}
    # createDeveloperMetadata: the Drive door labelling each tab it wrote,
    # which annotators never see and which touches no cell.
    assert request_types <= {"setDataValidation", "updateSheetProperties", "repeatCell",
                             "createDeveloperMetadata"}


def test_apply_leaves_annotation_content_byte_identical(fake, monkeypatch):
    """Every captured tab still reads back exactly as recorded, after --apply."""
    index = json.loads((FIXTURE_DIR / "index.json").read_text())
    before = {}
    for entry in index["spreadsheets"]:
        data = json.loads((FIXTURE_DIR / entry["path"]).read_text(encoding="utf-8"))
        for tab in data["worksheets"]:
            before[(data["spreadsheet_id"], tab["title"])] = tab["values"]

    run(["refresh-dropdowns", "--apply"], monkeypatch)

    for (ss_id, title), values in before.items():
        assert fake.spreadsheet(ss_id).worksheet(title).get_all_values() == values


def test_apply_never_writes_the_manifest(fake, monkeypatch):
    """Dropdowns only. Until 2026-10-23 this command also kept a copy of each
    criterion's values in the manifest, which went stale on its own."""
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    assert fake.mutations_of("update_file") == []
    assert fake.mutations_of("create_file") == []


# ---------------------------------------------------------------------------
# Issue #272 — the two bugs these snapshots caught, now fixed
# ---------------------------------------------------------------------------

def test_per_construction_criteria_are_not_collapsed_to_the_first(fake, monkeypatch):
    """#272 bug 1. A class's constructions can declare different criteria.

    segmental has aspiration_prominence and flapping; phrasal_accent has
    prescreening and general. Resolving every construction against the first
    one's values narrowed flapping's dropdowns from [y, n, both, na] to [y, n]
    and joint_accent's from [always, sometimes, never] to [y, n].

    Each tab now gets its own construction's values.
    """
    from coding.update_sheets import _fresh_param_values

    flapping = _fresh_param_values(
        "segmental", "flapping",
        {"flapping_left": ["y", "n", "both", "na"],
         "flapping_internal": ["y", "n", "both", "na"],
         "flapping_right": ["y", "n", "both", "na"]}, {})
    assert flapping["flapping_left"] == ["y", "n", "both", "na"]

    accent = _fresh_param_values(
        "phrasal_accent", "general",
        {"joint_accent": ["always", "sometimes", "never"]}, {})
    assert accent == {"joint_accent": ["always", "sometimes", "never"]}

    run(["refresh-dropdowns", "--apply"], monkeypatch)
    for lang in ("stan1293", "synth0001"):
        ws = fake.spreadsheet(_sheet_id(fake, lang, "segmental")).worksheet("flapping")
        assert _offered(ws, "flapping_left") == ("y", "n", "both", "na")


def test_dropdowns_are_never_written_onto_source_or_comments(fake, monkeypatch):
    """#272 bug 2. Source and Comments are free text an annotator writes prose in.

    The command used to take the *number* of dropdown columns from the manifest
    and their *start* from the header; when those disagreed it ran off the end
    of the criteria. Column identity now comes from the sheet's own header.

    The check itself is shared with update-sheets, which made the same mistake
    with criterion notes — see tests/mutation_checks.py.
    """
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    assert_no_criterion_writes_onto_trailing_columns(fake)


def test_an_unrecognised_criterion_column_is_skipped_not_guessed(fake, monkeypatch):
    """Belt and braces: never invent an allowed-value set for an unknown column.

    If the header's criterion block contains something the diagnostics YAML
    doesn't know about, the safe move is to write nothing to that tab and say
    so — a guessed [y, n] is how bug 2 did its damage.
    """
    from coding.update_sheets import _resolve_criterion_columns

    col_start, per_col, error = _resolve_criterion_columns(
        ["Element", "Position_Name", "Position_Number", "mystery", "Source", "Comments"],
        fresh={"accented": ["y", "n"]}, class_criteria={"accented": ["y", "n"]})
    assert col_start is None and per_col == []
    assert "mystery" in error and "not a criterion" in error


def test_criterion_columns_stop_at_the_trailing_columns(fake, monkeypatch):
    """The header, not the manifest, decides how many dropdown columns there are."""
    from coding.update_sheets import _resolve_criterion_columns

    col_start, per_col, error = _resolve_criterion_columns(
        ["Element", "Position_Name", "Position_Number", "referential", "Source", "Comments"],
        fresh={"referential": ["y", "n"]},
        class_criteria={"reflexive_allowed": ["y", "n", "untestable"]})
    assert error is None
    assert col_start == 3 and per_col == [["y", "n"]]


def test_apply_is_idempotent(fake, monkeypatch):
    """A second run finds nothing to do — nothing is rewritten."""
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    fake.clear_mutations()
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    assert fake.mutations == []


def test_dry_run_after_apply_reports_everything_up_to_date(fake, monkeypatch):
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    out = run(["refresh-dropdowns"], monkeypatch)
    assert "All dropdowns match the codebook." in out


# ---------------------------------------------------------------------------
# #322 — the sheet's real dropdowns, not the manifest's record of them
# ---------------------------------------------------------------------------

def _offered(ws, column: str):
    """The values column ``column``'s dropdown offers on row 2, None for none."""
    rule = ws._cells.get((1, ws.row_values(1).index(column)))
    rule = rule.validation if rule is not None else None
    return None if rule is None else tuple(
        v["userEnteredValue"] for v in rule["condition"]["values"])


def _seed(ws, column: str, values) -> None:
    """Give every data row of ``column`` a dropdown offering ``values``."""
    c = ws.row_values(1).index(column)
    for r in range(1, len(ws.get_all_values())):
        ws._cell(r, c).validation = {
            "condition": {"type": "ONE_OF_LIST",
                          "values": [{"userEnteredValue": v} for v in values]},
            "showCustomUi": True, "strict": False}


def test_an_old_narrow_dropdown_is_widened_and_a_wrong_one_removed(fake, monkeypatch):
    """What Adam met on the English sheets: the y/n list removed from the
    codebook 2026-10-12 was still on the sheets, so both, na and unclear
    weren't offered and a typed position number showed as invalid; and a
    dropdown sat on Comments. The manifest's copy of the values was right
    all along, so the old comparison saw nothing to do."""
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    ss = fake.spreadsheet(_sheet_id(fake, "stan1293", "free_occurrence"))
    ws = ss.worksheet("general")
    _seed(ws, "left-edge-of-free-form", ["y", "n"])
    _seed(ws, "dependent-on-left", ["y", "n"])
    _seed(ws, "Comments", ["y", "n", "both"])

    out = run(["refresh-dropdowns", "--lang", "stan1293"], monkeypatch)
    assert "general 'left-edge-of-free-form': y, n → y, n, na" in out
    assert "general 'dependent-on-left': y, n → no dropdown" in out
    assert "general 'Comments': both, n, y → no dropdown" not in out  # one list, as offered
    assert "general 'Comments': y, n, both → no dropdown" in out

    run(["refresh-dropdowns", "--apply", "--lang", "stan1293"], monkeypatch)
    assert _offered(ws, "left-edge-of-free-form") == ("y", "n", "na")
    assert _offered(ws, "dependent-on-left") is None
    assert _offered(ws, "Comments") is None
    assert "dropdowns match" in run(["refresh-dropdowns", "--lang", "stan1293"], monkeypatch)


def test_the_status_column_gets_its_strict_dropdown(fake, monkeypatch):
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    ws = fake.spreadsheet(_sheet_id(fake, "stan1293", "metrical")).worksheet("Status")
    rule = ws._cells[(1, ws.row_values(1).index("Status"))].validation
    assert rule["strict"] is True
    assert _offered(ws, "Needs fixing") is None
