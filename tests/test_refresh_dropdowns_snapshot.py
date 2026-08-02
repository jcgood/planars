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

**The `apply.txt` snapshot records a real bug, deliberately.** This command
narrows the dropdown for every class that declares per-construction criteria
(`segmental.flapping`, `phrasal_accent.general`), because it keeps only the
first construction's criterion values per class. See
docs/data-layer-progress.md § "Findings awaiting triage". Do not quietly
correct the snapshot — when the bug is fixed, its diff is the evidence.

**Regenerating.** These snapshots depend on `diagnostics_{lang}.yaml` in
`coded_data/`, which is a setup file that changes rarely — but when it does,
this test is *supposed* to fail. Regenerate and review the diff, same workflow
as tests/snapshots/:

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
from fake_drive import FakeDriveDoorway, MANIFEST_FILE_ID
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
def fake(monkeypatch):
    """A fake doorway seeded from the recorded capture, wired into the command."""
    doorway = FakeDriveDoorway.from_fixtures()
    monkeypatch.setattr(drive, "_load_drive_config", FakeDriveDoorway.drive_config)
    monkeypatch.setattr(refresh_dropdowns, "_load_drive_config",
                        FakeDriveDoorway.drive_config)
    drive_doorway.set_doorway(doorway)
    try:
        yield doorway
    finally:
        drive_doorway.reset_doorway()


def _sheet_id(fake, lang: str, class_name: str) -> str:
    """The Drive ID of one language's class spreadsheet, from the manifest."""
    manifest = fake.download_file_json(MANIFEST_FILE_ID)
    return manifest[lang]["sheets"][class_name]["spreadsheet_id"]


def run(argv, monkeypatch) -> str:
    monkeypatch.setattr("sys.argv", argv)
    buf = io.StringIO()
    with redirect_stdout(buf):
        refresh_dropdowns.main()
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
    assert request_types <= {"setDataValidation", "updateSheetProperties", "repeatCell"}


def test_apply_leaves_annotation_content_byte_identical(fake, monkeypatch):
    """Every captured tab still reads back exactly as recorded, after --apply."""
    index = json.loads(
        (ROOT / "tests" / "fixtures" / "drive_state" / "index.json").read_text())
    before = {}
    for entry in index["spreadsheets"]:
        data = json.loads((ROOT / entry["path"]).read_text(encoding="utf-8"))
        for tab in data["worksheets"]:
            before[(data["spreadsheet_id"], tab["title"])] = tab["values"]

    run(["refresh-dropdowns", "--apply"], monkeypatch)

    for (ss_id, title), values in before.items():
        assert fake.spreadsheet(ss_id).worksheet(title).get_all_values() == values


def test_apply_updates_the_manifest_in_place(fake, monkeypatch):
    """Manifest write goes through the doorway but keeps this file's own semantics.

    Notably: it updates in place with no create-if-missing fallback and no key
    reordering, unlike drive._upload_planars_config. Preserved deliberately —
    collapsing the four manifest writers is a later change.
    """
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    updates = fake.mutations_of("update_file")
    assert [u["file_id"] for u in updates] == [MANIFEST_FILE_ID]
    assert fake.mutations_of("create_file") == []

    manifest = fake.download_file_json(MANIFEST_FILE_ID)
    stored = (manifest["synth0001"]["sheets"]["coreference"]
              ["construction_params"]["reflexivization"]["param_values"])
    assert stored == {"reflexive_allowed": ["y", "n", "untestable"]}


# ---------------------------------------------------------------------------
# Issue #272 — the two bugs these snapshots caught, now fixed
# ---------------------------------------------------------------------------

def test_per_construction_criteria_are_not_collapsed_to_the_first(fake, monkeypatch):
    """#272 bug 1. A class's constructions can declare different criteria.

    segmental has aspiration_prominence and flapping; phrasal_accent has
    prescreening and general. Resolving every construction against the first
    one's values narrowed flapping's dropdowns from [y, n, both, na] to [y, n]
    and joint_accent's from [always, sometimes, never] to [y, n].

    Those manifests were already correct, so with the bug fixed there is
    nothing to change on those tabs at all — they must not be touched.
    """
    from coding.refresh_dropdowns import _fresh_param_values

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
    touched = {(m["spreadsheet"], m["payload"]["range"]["sheetId"])
               for m in fake.mutations
               if m["op"] == "batch_request" and m["request_type"] == "setDataValidation"}
    for lang in ("stan1293", "synth0001"):
        for class_name, tab in (("segmental", "flapping"),
                                ("phrasal_accent", "general")):
            ss = fake.spreadsheet(_sheet_id(fake, lang, class_name))
            assert (ss.id, ss.worksheet(tab).id) not in touched


def test_dropdowns_are_never_written_onto_source_or_comments(fake, monkeypatch):
    """#272 bug 2. Source and Comments are free text an annotator writes prose in.

    The command used to take the *number* of dropdown columns from the manifest
    and their *start* from the header; when those disagreed it ran off the end
    of the criteria. Column identity now comes from the sheet's own header.
    """
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    for m in fake.mutations:
        if m["op"] != "batch_request" or m["request_type"] != "setDataValidation":
            continue
        rng = m["payload"]["range"]
        ws = fake.spreadsheet(m["spreadsheet"])._worksheet_by_sheet_id(rng["sheetId"])
        header = ws.row_values(1)
        for col in range(rng["startColumnIndex"], rng["endColumnIndex"]):
            assert header[col] not in ("Source", "Comments"), (
                f"dropdown written onto {header[col]!r} of {ws.title}")


def test_an_unrecognised_criterion_column_is_skipped_not_guessed(fake, monkeypatch):
    """Belt and braces: never invent an allowed-value set for an unknown column.

    If the header's criterion block contains something the diagnostics YAML
    doesn't know about, the safe move is to write nothing to that tab and say
    so — a guessed [y, n] is how bug 2 did its damage.
    """
    from coding.refresh_dropdowns import _resolve_criterion_columns

    col_start, per_col, error = _resolve_criterion_columns(
        ["Element", "Position_Name", "Position_Number", "mystery", "Source", "Comments"],
        fresh={"accented": ["y", "n"]}, class_criteria={"accented": ["y", "n"]})
    assert col_start is None and per_col == []
    assert "mystery" in error and "not a criterion" in error


def test_criterion_columns_stop_at_the_trailing_columns(fake, monkeypatch):
    """The header, not the manifest, decides how many dropdown columns there are."""
    from coding.refresh_dropdowns import _resolve_criterion_columns

    col_start, per_col, error = _resolve_criterion_columns(
        ["Element", "Position_Name", "Position_Number", "referential", "Source", "Comments"],
        fresh={"referential": ["y", "n"]},
        class_criteria={"reflexive_allowed": ["y", "n", "untestable"]})
    assert error is None
    assert col_start == 3 and per_col == [["y", "n"]]


def test_apply_is_idempotent(fake, monkeypatch):
    """A second run finds nothing to do — nothing is rewritten, no manifest upload."""
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    fake.clear_mutations()
    out = run(["refresh-dropdowns", "--apply"], monkeypatch)
    assert fake.mutations == []
    assert "Manifest updated on Drive" not in out


def test_dry_run_after_apply_reports_everything_up_to_date(fake, monkeypatch):
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    out = run(["refresh-dropdowns"], monkeypatch)
    assert "All dropdowns are up to date." in out
