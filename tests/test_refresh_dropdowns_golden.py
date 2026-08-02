"""Golden tests for `python -m coding refresh-dropdowns`, run against the fake.

First file migrated to the Drive seam (plan Phase 0b/1, file 1 of 11). These
goldens lock the command's behaviour — stdout for both modes, and the full
mutation log for `--apply` — so that later migrations, or any change to the
seam, must either preserve that behaviour or show exactly what they altered.

**How the pre-migration baseline was taken.** The plan's per-file procedure
asks for a real-Drive dry run before migrating. That is not permitted before
Phase 9, so the substitute was to drive the *unmigrated* code from this same
seeded fake through thin gspread-client and Drive-service shims, and diff its
output against the migrated code's. Both modes matched exactly, with one
intended difference recorded in docs/data-layer-progress.md: opening a
spreadsheet now retries, because `open_spreadsheet` always retries.

**Regenerating.** These goldens depend on `diagnostics_{lang}.yaml` in
`coded_data/`, which is a setup file that changes rarely — but when it does,
this test is *supposed* to fail. Regenerate and review the diff, same workflow
as tests/snapshots/:

    PLANARS_UPDATE_GOLDENS=1 pytest tests/test_refresh_dropdowns_golden.py
    git diff tests/goldens/
"""
from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from coding import drive, drive_backend, refresh_dropdowns
from fake_drive import FakeDriveBackend, MANIFEST_FILE_ID

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = ROOT / "tests" / "goldens" / "refresh_dropdowns"
UPDATING = os.environ.get("PLANARS_UPDATE_GOLDENS") == "1"

# The command reads each language's diagnostics YAML and planar TSV from
# coded_data/, which is a separate repo that a bare worktree may not have.
pytestmark = pytest.mark.skipif(
    not (ROOT / "coded_data").exists(),
    reason="coded_data/ (planars-data) is not checked out",
)


@pytest.fixture()
def fake(monkeypatch):
    """A fake backend seeded from the recorded capture, wired into the command."""
    backend = FakeDriveBackend.from_fixtures()
    monkeypatch.setattr(drive, "_load_drive_config", FakeDriveBackend.drive_config)
    monkeypatch.setattr(refresh_dropdowns, "_load_drive_config",
                        FakeDriveBackend.drive_config)
    drive_backend.set_backend(backend)
    try:
        yield backend
    finally:
        drive_backend.reset_backend()


def run(argv, monkeypatch) -> str:
    monkeypatch.setattr("sys.argv", argv)
    buf = io.StringIO()
    with redirect_stdout(buf):
        refresh_dropdowns.main()
    return buf.getvalue()


def check_golden(name: str, actual: str) -> None:
    path = GOLDEN_DIR / name
    if UPDATING:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        pytest.skip(f"updated golden {path.relative_to(ROOT)}")
    assert path.exists(), (
        f"Golden missing: {path.relative_to(ROOT)}\n"
        f"Run: PLANARS_UPDATE_GOLDENS=1 pytest {Path(__file__).relative_to(ROOT)}"
    )
    assert actual == path.read_text(encoding="utf-8"), (
        f"Output differs from {path.name}. If intended, regenerate with "
        f"PLANARS_UPDATE_GOLDENS=1 and review the diff."
    )


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------

def test_dry_run_output(fake, monkeypatch):
    check_golden("dry_run.txt", run(["refresh-dropdowns"], monkeypatch))


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
    check_golden("apply.txt", run(["refresh-dropdowns", "--apply"], monkeypatch))


def test_apply_mutation_log(fake, monkeypatch):
    """The full write log, reviewed by a human before it became a golden.

    Write paths have no pre-migration baseline to diff against, so this review
    is the only barrier between a migration bug and its enshrinement as correct
    behaviour (plan Phase 0b/1, step 5).
    """
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    check_golden("apply_mutations.json",
                 json.dumps(fake.mutations, indent=2) + "\n")


def test_apply_never_writes_a_cell_value(fake, monkeypatch):
    """The command's whole promise: dropdowns change, annotation data does not.

    Adam's annotations are irreplaceable and annotation is in progress. A
    regression that made this command write values would be exactly the kind of
    silent data loss the data layer work exists to prevent, so it is asserted
    structurally rather than left to golden inspection.
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
    """Manifest write goes through the seam but keeps this file's own semantics.

    Notably: it updates in place with no create-if-missing fallback and no key
    reordering, unlike drive._upload_planars_config. Preserved deliberately —
    collapsing the four manifest writers is a later change.
    """
    run(["refresh-dropdowns", "--apply"], monkeypatch)
    updates = fake.mutations_of("update_file")
    assert [u["file_id"] for u in updates] == [MANIFEST_FILE_ID]
    assert fake.mutations_of("create_file") == []

    manifest = fake.download_file_json(MANIFEST_FILE_ID)
    stored = (manifest["stan1293"]["sheets"]["segmental"]
              ["construction_params"]["flapping"]["param_values"])
    assert stored["flapping_left"] == ["y", "n"]


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
