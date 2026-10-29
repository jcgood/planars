"""Snapshot tests for `python -m coding import-sheets`, run against the fake.

File 15 of 18 migrated to the Drive doorway (#271) -- the command the daily
`data-refresh` GitHub Action runs to pull annotator work down from Sheets, and
the largest and most consequential file migrated so far (1,138 lines against
the last three files' combined total of well under that). Its Drive footprint:
`get_doorway()`, `doorway.open_spreadsheet(...)` per class spreadsheet (the
class sheets come from the ID file), and `doorway.get_file(...)` in
`_verify_sheet_ids` (abort-before-download guard, `--apply` only). Since unit
11c the command neither reads nor writes the manifest. Cell highlighting
(`_highlight_invalid_cells`, delegating to `validate_coding.highlight_cells`)
and the final `revalidate_sheets()` call are handle-level operations that
needed no edits -- both already went through the doorway before this file did
(files 13 and 12 respectively).

**How the pre-migration baseline was taken.** As for every file after the
first, a real-Drive dry run is not permitted before Phase 9. The substitute:
drive the *unmigrated* code (`from .drive import _check_coded_data_clean,
_get_clients, _load_manifest_from_drive, _open_spreadsheet,
_upload_planars_config, _load_drive_config, _save_drive_config, _with_retry`,
all module-level) from a `FakeDriveDoorway.from_fixtures()` through thin
`gc`/`drive` shims -- `gc` is never really used once `_open_spreadsheet` is
shimmed to route straight to the doorway, and `drive` only needs a
`.files().get(fileId=..., fields=...).execute()` shape for
`_verify_manifest_sheet_ids`. Twenty-two scenarios were run through both the
unmigrated and migrated code against identically seeded fakes: dry run over
all languages and with `--lang`; `--apply` with no prior local TSVs
(first-time download); a baseline "already matches" run and a genuine content
change on top of it (archive-then-write); `--overwrite-existing` forcing a
rewrite despite unchanged content; a purely-additive in-order planar change
(queues `update-sheets --apply`, confirmed via a stubbed
`sys.modules["coding.update_sheets"]` recording the auto-applied call rather
than really running it) versus a deletion and a reorder (each its own pending
entry); an unrecognised criterion in the diagnostics sheet (ambiguous YAML
drift); a missing construction tab (`WorksheetNotFound`, warn and continue); a
class with no Status tab versus `--ignore-status` versus one construction set
to `ready-for-review` alongside others left `in-progress`; an injected invalid
cell (confirmed via the mutation log, not just stdout, since blank cells are
*also* pink-highlighted on real fixture data and so don't move the highlight
*count* -- the confirming check was a `updateCells` mutation at the exact
row/column touched, with the pink `{1.0, 0.8, 0.8}` background); a missing
local row on an in-progress tab (collaborator-check, not pending); a bad
manifest spreadsheet ID reached under `--apply` (clean abort, pre-download)
versus the same ID on a language excluded by `--lang` under a dry run
(silently never reached, confirmed by the *absence* of a crash); the manifest
metadata sync firing only when the computed planar structure actually
differs; and `--lang` leaving other languages' local trees untouched. stdout,
exit codes, the mutation logs, the local `coded_data/` tree contents,
`pending_changes.json`, and `diagnostics_drift.json` all came back
byte-identical in every scenario once `datetime.now()` was frozen (the
archive filename embeds a timestamp computed once at the top of `main()`, so
two real invocations a second apart otherwise disagreed on nothing but that).
The shim script and its scenario driver are scratch throwaways per the plan's
convention, not committed.

**A genuine finding, not introduced by this migration, fixed separately:** a
dry run had *no* protection at all against a manifest entry pointing at an
inaccessible spreadsheet. `_verify_manifest_sheet_ids` -- the clean "ERROR:
Manifest contains inaccessible spreadsheet IDs" abort -- only runs `if apply:`.
A dry run instead reached `ss = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])`
inside the per-class loop with no `try`/`except` around it at all, so a bad ID
crashed the *entire* run -- every language, not just the one naming the bad
ID -- with an unhandled `SpreadsheetNotFound` traceback. Confirmed identical
between the unmigrated and migrated code (both raised the same exception at
the same point); recorded as Finding 13 in docs/data-layer-progress.md, and
fixed in a follow-up commit rather than in the migration itself, per the
migration's non-goal of no behaviour changes beyond the doorway swap. The
`open_spreadsheet` call is now wrapped in its own `try`/`except Exception`,
reported per class the same way a missing worksheet already is (`WARNING:
... skipping`, appended to `lang_warning_lines`, `total_warnings` incremented),
and the loop moves on to the next class rather than the next language --
so a bad ID only ever costs the preview of the one class that names it.

`_verify_manifest_sheet_ids`, `_read_sheet_as_df`, `_download_lang_setup_sheets`,
and `_read_status_tab` all took a `gc`/`drive`/`ss` parameter typed against
`gspread`; each now takes a `doorway`/handle instead, with the type annotation
dropped (the doorway has no `gspread.Client` equivalent to name). `gspread` is
no longer imported at all -- it was used only for those annotations and for
`except gspread.WorksheetNotFound`, now `except WorksheetNotFound` imported
from `drive_doorway` (the identical class, re-exported for exactly this).

`tests/test_import_sheets.py`'s `TestVerifyManifestSheetIds` mocked a raw
`drive` object shaped like `.files().get(fileId=..., fields=...).execute()`;
its six tests now pass a tiny local stub with a `get_file(self, file_id,
fields=None)` method instead, keeping the same behaviour under test (which IDs
abort, which don't) without depending on a shape `_verify_manifest_sheet_ids`
no longer receives.

`revalidate_sheets()` (called at the end of `main()` under `--apply`) reads
local TSVs from `coding.validate_coding.CODED_DATA`, a *separate* module-level
constant from this file's own `ROOT` -- both are redirected into the same
private tree in every test below, so the revalidation pass sees exactly what
`import-sheets` itself just wrote rather than the real repo's current
annotation state (which would make these snapshots drift for reasons having
nothing to do with this file).

Since Phase 10 unit 11b (2026-10-24) the command no longer downloads the
planar and diagnostics Sheets, so the planar-change, pending-changes,
auto-apply and YAML-drift scenarios above are gone; one test checks that
edits to those Sheets never reach the sources.

Regenerate: PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_import_sheets_snapshot.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd
import pytest

from coding import drive as drive_module
from coding import drive_doorway, drive_ids, file_door
from coding import import_sheets as is_
from command_runner import run_command
from fake_drive import FROZEN_CODED_DATA, FakeDriveDoorway, MANIFEST_FILE_ID, point_coded_data_at
from mutation_checks import assert_no_criterion_writes_onto_trailing_columns

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "import_sheets"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANGS = ["arao1248", "stan1293", "synth0001"]

# The archive filename and the change log embed the time the local-file door
# wrote -- frozen so two runs a second apart don't disagree on nothing else.
FROZEN = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FROZEN if tz is None else FROZEN.astimezone(tz)


# The command reads local TSVs and diagnostics YAMLs from coded_data/, a
# separate repo that a bare worktree may not have.
pytestmark = pytest.mark.skipif(
    not (ROOT / "coded_data").exists(),
    reason="coded_data/ (planars-data) is not checked out",
)


class Env:
    """One stand-in Drive, one private copy of coded_data/, one command."""

    def __init__(self, doorway: FakeDriveDoorway, coded: Path,
                 notified_collaborator: List[List[Dict]],
                 run: Callable[[List[str]], Tuple[str, Optional[int]]]) -> None:
        self.doorway = doorway
        self.config = FakeDriveDoorway.drive_config()
        self.coded = coded
        self.notified_collaborator = notified_collaborator
        self.run = run

    # -- the ID file ----------------------------------------------------
    def mutate_config(self, fn: Callable[[Dict], None]) -> None:
        fn(self.config)

    def sheet_id(self, lang: str, cls: str) -> str:
        return drive_ids.class_sheet_id(self.config, lang, cls)

    def tab(self, lang: str, cls: str, construction: str):
        return self.doorway.spreadsheet(self.sheet_id(lang, cls)).worksheet(construction)

    def planar_sheet(self, lang: str):
        return self.doorway.spreadsheet(self.config[lang]["planar_spreadsheet_id"]).sheet1

    def diagnostics_sheet(self, lang: str):
        return self.doorway.spreadsheet(self.config[lang]["diagnostics_spreadsheet_id"]).sheet1

    def set_status(self, lang: str, cls: str, construction: str, status: str) -> None:
        ws = self.doorway.spreadsheet(self.sheet_id(lang, cls)).worksheet("Status")
        for r, row in enumerate(ws.get_all_values()):
            if row and row[0] == construction:
                ws._cell(r, 1).value = status
                return
        raise AssertionError(f"{construction!r} not found in Status tab")

    def remove_status_tab(self, lang: str, cls: str) -> None:
        ss = self.doorway.spreadsheet(self.sheet_id(lang, cls))
        ss.del_worksheet(ss.worksheet("Status"))

    def delete_tab(self, lang: str, cls: str, construction: str) -> None:
        ss = self.doorway.spreadsheet(self.sheet_id(lang, cls))
        ss.del_worksheet(ss.worksheet(construction))

    def edit_sheet_rows(self, ws, fn) -> None:
        rows = fn(ws.get_all_values())
        ws.clear()
        ws.update(rows, "A1")

    # -- the local tree ---------------------------------------------------
    def output_tsv(self, lang: str, cls: str, construction: str) -> Path:
        return self.coded / lang / cls / f"{construction}.tsv"

    def archives(self, lang: str, cls: str) -> List[Path]:
        return sorted((self.coded / lang / "archive" / cls).glob("*.tsv")) \
            if (self.coded / lang / "archive" / cls).exists() else []


@pytest.fixture()
def env(monkeypatch, tmp_path):
    doorway = FakeDriveDoorway.from_fixtures()

    coded = tmp_path / "coded_data"
    for lang in LANGS:
        shutil.copytree(FROZEN_CODED_DATA / lang, coded / lang,
                        ignore=shutil.ignore_patterns(".git"))

    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir(parents=True)
    (schemas_dir / "languages.yaml").write_text("{}\n", encoding="utf-8")

    # revalidate_sheets() reads local TSVs from validate_coding's own
    # CODED_DATA constant, not this file's ROOT; the Drive door reads its
    # own too. Every module's is pointed at the private tree.
    point_coded_data_at(monkeypatch, coded)

    notified_collaborator: List[List[Dict]] = []

    monkeypatch.setattr(is_, "ROOT", tmp_path)
    monkeypatch.setattr(is_, "ERROR_DIR", tmp_path / "import_errors")
    # Archive names and change-log times are the local-file door's.
    monkeypatch.setattr(file_door, "datetime", _FrozenDatetime)
    monkeypatch.setattr(is_, "_notify_collaborator_check", notified_collaborator.append)
    # The ID file, one copy for the test, which a scenario may change.
    # The command's own import of _load_drive_config and coding.drive's
    # (used by revalidate_sheets) both read it.
    config_holder: List[Dict] = []
    monkeypatch.setattr(is_, "_load_drive_config", lambda: config_holder[0])
    monkeypatch.setattr(drive_module, "_load_drive_config", lambda: config_holder[0])
    drive_doorway.set_doorway(doorway)

    def run(argv: List[str]) -> Tuple[str, Optional[int]]:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        exit_code = None
        try:
            with redirect_stdout(buf):
                run_command(is_, "import-sheets")
        except SystemExit as exc:
            exit_code = exc.code
        return buf.getvalue(), exit_code

    try:
        e = Env(doorway, coded, notified_collaborator, run)
        config_holder.append(e.config)
        yield e
    finally:
        drive_doorway.reset_doorway()


def check_snapshot(name: str, actual: str) -> None:
    path = SNAPSHOT_DIR / name
    if UPDATING:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        pytest.skip(f"updated snapshot {path.relative_to(ROOT)}")
    assert path.exists(), (
        f"Snapshot missing: {path.relative_to(ROOT)}\n"
        f"Run: PLANARS_UPDATE_SNAPSHOTS=1 pytest {Path(__file__).relative_to(ROOT)}")
    assert actual == path.read_text(encoding="utf-8"), (
        f"Output differs from {path.name}. If intended, regenerate with "
        f"PLANARS_UPDATE_SNAPSHOTS=1 and review the diff.")


def add_planar_position(rows: List[List[str]]) -> List[List[str]]:
    """One more position, numbered after the current last -- in-order addition."""
    header = rows[0]
    pos_idx, name_idx = header.index("Position"), header.index("Position_Name")
    numbers = [int(r[pos_idx]) for r in rows[1:] if r[pos_idx].strip().isdigit()]
    new_row = list(rows[-1])
    new_row[pos_idx] = str(max(numbers) + 1)
    new_row[name_idx] = "x:newpos-test"
    return rows + [new_row[:len(header)]]


def drop_last_planar_position(rows: List[List[str]]) -> List[List[str]]:
    return rows[:-1]


def assert_finished(out: str, exit_code: Optional[int]) -> None:
    """The run finished cleanly. A coding error in the recorded annotation
    (real annotators' work, brought in by a refreeze) no longer stops it
    (#309): validate-coding reports those."""
    assert exit_code is None, out


# ---------------------------------------------------------------------------
# What the coordinator sees
# ---------------------------------------------------------------------------

def test_dry_run_transcript(env):
    """Nothing changed anywhere -- the ordinary daily "nothing to do" run."""
    out, exit_code = env.run(["import-sheets"])
    assert_finished(out, exit_code)
    check_snapshot("dry_run.txt", out)


def test_verify_aborts_transcript(env):
    """An ID-file entry pointing at a spreadsheet the fake has never seen."""
    drive_ids.set_class_sheet(env.config, "arao1248", "ciscategorial", "does_not_exist_xyz")
    out, exit_code = env.run(["import-sheets", "--apply"])
    assert exit_code == 1
    check_snapshot("verify_aborts.txt", out)


def test_apply_multiple_kinds_of_change_transcript(env):
    """A content change on one language's class sheet, and edits to two
    planar Sheets, which are read-only copies and never read back (11b)."""
    env.edit_sheet_rows(env.planar_sheet("arao1248"), add_planar_position)
    env.edit_sheet_rows(env.planar_sheet("stan1293"), drop_last_planar_position)
    env.tab("synth0001", "ciscategorial", "general")._cell(1, 3).value = "y"
    out, exit_code = env.run(["import-sheets", "--apply"])
    assert_finished(out, exit_code)
    check_snapshot("apply_multiple_changes.txt", out)


# ---------------------------------------------------------------------------
# --apply: first download, no-op, forced overwrite
# ---------------------------------------------------------------------------

def test_first_time_download_writes_every_construction(env):
    for cls_dir in (env.coded / "arao1248").iterdir():
        if cls_dir.is_dir() and cls_dir.name not in ("lang_setup", "archive"):
            shutil.rmtree(cls_dir)
    out, _ = env.run(["import-sheets", "--lang", "arao1248", "--apply"])
    assert "Would create" not in out  # this is --apply, not a dry run
    assert env.output_tsv("arao1248", "ciscategorial", "general").exists()
    assert env.output_tsv("arao1248", "subspanrepetition", "tso_clause_linkage").exists()


def test_a_noop_apply_writes_no_new_tsvs_or_archives(env):
    env.run(["import-sheets", "--lang", "arao1248", "--apply"])  # materialize
    before = env.output_tsv("arao1248", "ciscategorial", "general").read_text()
    n_archives_before = len(env.archives("arao1248", "ciscategorial"))

    out, exit_code = env.run(["import-sheets", "--lang", "arao1248", "--apply"])

    assert exit_code is None
    assert "No changes" in out
    assert env.output_tsv("arao1248", "ciscategorial", "general").read_text() == before
    assert len(env.archives("arao1248", "ciscategorial")) == n_archives_before


def test_overwrite_existing_rewrites_matching_cells_but_never_identical_bytes(env):
    # Materialize in today's form (the frozen copy may still have CRLF ends).
    env.run(["import-sheets", "--lang", "arao1248", "--apply", "--overwrite-existing"])
    tsv = env.output_tsv("arao1248", "ciscategorial", "general")
    n_archives_before = len(env.archives("arao1248", "ciscategorial"))

    # Identical bytes: the local-file door has nothing to write.
    env.run(["import-sheets", "--lang", "arao1248", "--apply", "--overwrite-existing"])
    assert len(env.archives("arao1248", "ciscategorial")) == n_archives_before

    # Same cells, different line ends: a plain import sees no change, the
    # flag rewrites it (and the door archives the old text).
    written = tsv.read_bytes()
    assert b"\r\n" not in written                 # LF, as every writer uses
    tsv.write_bytes(written.replace(b"\n", b"\r\n"))
    out, _ = env.run(["import-sheets", "--lang", "arao1248", "--apply"])
    assert "No changes → coded_data/arao1248/ciscategorial/general.tsv" in out
    env.run(["import-sheets", "--lang", "arao1248", "--apply", "--overwrite-existing"])
    assert tsv.read_bytes() == written
    assert len(env.archives("arao1248", "ciscategorial")) == n_archives_before + 1


def test_content_change_archives_before_overwriting(env):
    env.run(["import-sheets", "--lang", "arao1248", "--apply"])  # materialize
    before = env.output_tsv("arao1248", "ciscategorial", "general").read_text()
    # coded_data/ carries pre-existing archives from real history; look at the
    # one archive this run adds, by name rather than by modification time --
    # the frozen copy's files all share one timestamp, so "newest" is a tie.
    archives_before = set(env.archives("arao1248", "ciscategorial"))
    env.tab("arao1248", "ciscategorial", "general")._cell(1, 3).value = "y"

    out, _ = env.run(["import-sheets", "--lang", "arao1248", "--apply"])

    added = set(env.archives("arao1248", "ciscategorial")) - archives_before
    assert len(added) == 1
    assert added.pop().read_text() == before
    assert env.output_tsv("arao1248", "ciscategorial", "general").read_text() != before


# ---------------------------------------------------------------------------
# The planar and diagnostics Sheets are never read back (unit 11b)
# ---------------------------------------------------------------------------

def test_edits_to_the_planar_and_diagnostics_sheets_never_reach_the_sources(env):
    """Both Sheets are read-only copies; until 2026-10-24 this command
    downloaded them into planar_{lang}.tsv and diagnostics_{lang}.tsv."""
    setup = env.coded / "stan1293" / "lang_setup"
    archive = env.coded / "stan1293" / "archive" / "lang_setup"

    def snapshot():
        files = {p.name: p.read_bytes() for p in setup.iterdir() if p.is_file()}
        return files, sorted(p.name for p in archive.glob("*")) if archive.exists() else []

    before = snapshot()
    env.edit_sheet_rows(env.planar_sheet("stan1293"), drop_last_planar_position)
    env.edit_sheet_rows(env.diagnostics_sheet("stan1293"), lambda rows: rows[:-1])

    out, exit_code = env.run(["import-sheets", "--lang", "stan1293", "--apply"])

    assert_finished(out, exit_code)
    assert snapshot() == before
    assert "[planar]" not in out and "[diagnostics]" not in out


# ---------------------------------------------------------------------------
# A missing construction tab warns and continues
# ---------------------------------------------------------------------------

def test_a_missing_tab_warns_and_does_not_stop_the_rest_of_the_language(env):
    before = env.output_tsv("arao1248", "subspanrepetition", "tso_clause_linkage").read_text()
    env.delete_tab("arao1248", "subspanrepetition", "tso_clause_linkage")
    out, exit_code = env.run(["import-sheets", "--apply"])
    assert "[subspanrepetition/tso_clause_linkage] tab not found in sheet, skipping" in out
    # The sibling construction on the same spreadsheet is still imported.
    assert env.output_tsv("arao1248", "subspanrepetition", "auxiliary_construction").exists()
    # The missing tab's local TSV (pre-existing from real history) is left
    # alone entirely -- the run never reaches the point of writing it.
    assert env.output_tsv("arao1248", "subspanrepetition", "tso_clause_linkage").read_text() == before
    # Issue #283: a missing tab is one of the warnings serious enough to
    # make the command exit non-zero, even though (as above) it doesn't
    # stop the rest of the run from completing.
    assert exit_code == 1


# ---------------------------------------------------------------------------
# Status tab: absent, --ignore-status, and a mixed in-progress/ready tab
# ---------------------------------------------------------------------------

def test_no_status_tab_treats_every_construction_as_ready_for_review(env):
    env.remove_status_tab("arao1248", "ciscategorial")
    out, _ = env.run(["import-sheets", "--apply"])
    assert "(no Status tab found — importing all constructions)" in out
    # A ready-for-review construction is never labelled "[backup]".
    assert "[general] [backup]" not in out.split("noninterruption")[0]


def test_ignore_status_treats_every_tab_as_ready_for_review(env):
    out, _ = env.run(["import-sheets", "--lang", "arao1248", "--apply", "--ignore-status"])
    # The ways import marks a tab it treated as in-progress (revalidation's
    # summary line names in-progress tabs in general, so not the bare word).
    for mark in ("[backup]", "in-progress backup(s)", "in-progress sheet(s) have"):
        assert mark not in out, out


def test_mixed_status_only_treats_the_flipped_construction_as_ready(env):
    env.set_status("arao1248", "ciscategorial", "general", "ready-for-review")
    out, _ = env.run(["import-sheets", "--apply"])
    ciscategorial_section = out.split("noninterruption")[0]
    noninterruption_section = out.split("noninterruption")[1].split("subspanrepetition")[0]
    assert "in-progress" not in ciscategorial_section
    assert "status: 'in-progress' — importing for backup" in noninterruption_section


# ---------------------------------------------------------------------------
# Invalid cells get pink-highlighted
# ---------------------------------------------------------------------------

def test_an_invalid_cell_is_pink_highlighted(env):
    sid = env.sheet_id("arao1248", "ciscategorial")
    env.tab("arao1248", "ciscategorial", "general")._cell(1, 3).value = "maybe123"

    out, exit_code = env.run(["import-sheets", "--lang", "arao1248", "--apply", "--ignore-status"])

    hits = [
        m for m in env.doorway.mutations
        if m.get("op") == "batch_request" and m.get("request_type") == "updateCells"
        and m.get("spreadsheet") == sid
        and m["payload"]["range"].get("startRowIndex") == 1
        and m["payload"]["range"].get("startColumnIndex") == 3
    ]
    assert hits, "expected a pink-highlight write for the invalid cell"
    assert hits[0]["payload"]["rows"][0]["values"][0]["userEnteredFormat"]["backgroundColor"] \
        == {"red": 1.0, "green": 0.8, "blue": 0.8}
    # Since #309 an invalid value is not an import failure: it is printed,
    # graded by the tab's real Status (this tab is in-progress, so a warning),
    # and reported by validate-coding, never through import-error.
    assert exit_code is None
    assert "[WARNING] general row 2" in out and "unexpected value 'maybe123'" in out


# ---------------------------------------------------------------------------
# A missing local row on an in-progress tab: a collaborator-check issue
# ---------------------------------------------------------------------------

def test_a_missing_row_on_an_in_progress_tab_is_a_collaborator_check(env):
    env.run(["import-sheets", "--lang", "arao1248", "--apply"])  # materialize

    def drop_first_data_row(rows):
        return [rows[0]] + rows[2:]
    env.edit_sheet_rows(env.tab("arao1248", "ciscategorial", "general"), drop_first_data_row)

    out, _ = env.run(["import-sheets", "--lang", "arao1248", "--apply"])

    assert "ANOMALY: Missing rows" in out
    assert env.notified_collaborator
    assert env.notified_collaborator[0][0]["class_name"] == "ciscategorial"


# ---------------------------------------------------------------------------
# _verify_sheet_ids only ever runs under --apply
# ---------------------------------------------------------------------------

def test_verify_aborts_before_any_download_under_apply(env):
    drive_ids.set_class_sheet(env.config, "arao1248", "ciscategorial", "does_not_exist_xyz")
    out, exit_code = env.run(["import-sheets", "--apply"])
    assert exit_code == 1
    assert "ERROR: The ID file contains inaccessible spreadsheet IDs" in out
    assert "Language:" not in out  # aborted before the per-language loop started
    assert env.doorway.mutations == []


def test_verify_is_skipped_on_a_dry_run_that_never_reaches_the_bad_id(env):
    """A bad ID on a language the --lang filter excludes never gets checked at
    all on a dry run -- confirmed by the run completing normally rather than
    raising, since a reached bad ID has no guard on a dry run (see the module
    docstring's Finding). Not asserting "ERROR" not in out overall: arao1248's
    diagnostics_arao1248.yaml is genuinely missing three collection_required:
    "y" classes (Finding 19), which surfaces its own unrelated ERROR lines on
    every run for this language -- the thing this test actually checks is
    that stan1293's bad ID is never reached."""
    drive_ids.set_class_sheet(env.config, "stan1293", "ciscategorial", "does_not_exist_xyz")
    out, exit_code = env.run(["import-sheets", "--lang", "arao1248"])
    assert exit_code is None
    assert "does_not_exist_xyz" not in out
    assert "inaccessible spreadsheet" not in out


def test_a_bad_id_reached_on_a_dry_run_warns_and_previews_every_other_language(env):
    """Finding 13, fixed: a dry run used to have no guard at all -- reaching a
    bad manifest spreadsheet ID crashed the entire run with an unhandled
    exception, stopping every language, not just the one naming it. Now the
    bad ID is reported as a per-class ERROR line and the run continues,
    previewing every other class and every other language exactly as if the
    bad ID were never there. Since issue #283, a spreadsheet-open failure is
    also one of the warnings serious enough to make the command exit
    non-zero (dry run or not -- it's the same real problem either way, and
    the daily automation always runs --apply, never a dry run, so this
    matters operationally for the --apply case; asserted here on the dry
    run because that's what this test already exercises for the
    no-crash/keeps-previewing behavior above)."""
    drive_ids.set_class_sheet(env.config, "stan1293", "ciscategorial", "does_not_exist_xyz")
    out, exit_code = env.run(["import-sheets"])

    assert exit_code == 1
    # The failure itself, not just any warning: until 2026-10-17 this read
    # `"WARNING" in out` and passed on an unrelated daily notice.
    assert ("ERROR: [ciscategorial] could not open spreadsheet 'does_not_exist_xyz' "
            "for stan1293") in out
    # Every language still gets previewed -- the run did not stop at stan1293.
    assert "Language: arao1248" in out
    assert "Language: stan1293" in out
    assert "Language: synth0001" in out
    # stan1293's other classes (not just ciscategorial) are still reached.
    other_classes = [c for c in drive_ids.class_sheets(env.config, "stan1293")
                     if c != "ciscategorial"]
    assert other_classes, "expected stan1293 to have more than one class sheet"
    for cls in other_classes:
        assert f"\n  {cls}" in out


# ---------------------------------------------------------------------------
# The manifest is not this command's: it never writes it
# ---------------------------------------------------------------------------

def test_the_manifest_is_never_written(env):
    out, _ = env.run(["import-sheets", "--lang", "arao1248", "--apply"])
    assert "manifest" not in out
    assert not any(m["op"] == "update_file" and m["file_id"] == MANIFEST_FILE_ID
                  for m in env.doorway.mutations)


# ---------------------------------------------------------------------------
# --lang restricts the run to one language
# ---------------------------------------------------------------------------

def test_lang_filter_leaves_other_languages_local_trees_untouched(env):
    for lang in LANGS:
        env.tab(lang, "ciscategorial", "general")._cell(1, 3).value = "y"
    before = {
        lang: (env.coded / lang / "ciscategorial" / "general.tsv").read_text()
        if (env.coded / lang / "ciscategorial" / "general.tsv").exists() else None
        for lang in LANGS if lang != "arao1248"
    }

    env.run(["import-sheets", "--lang", "arao1248", "--apply"])

    for lang, content in before.items():
        current = env.coded / lang / "ciscategorial" / "general.tsv"
        assert (current.read_text() if current.exists() else None) == content


# ---------------------------------------------------------------------------
# Pair-row constructions (coreference, nonpermutability, phrasal_accent) go
# through the pair-row validator; standard constructions go through the
# element-row validator. Both live in stan1293's manifest entry.
# ---------------------------------------------------------------------------

def test_pair_row_and_standard_constructions_both_import_cleanly(env):
    out, exit_code = env.run(["import-sheets", "--lang", "stan1293", "--apply"])
    assert_finished(out, exit_code)
    assert env.output_tsv("stan1293", "ciscategorial", "general").exists()       # element rows
    assert env.output_tsv("stan1293", "coreference", "reflexive_coreference").exists()  # pair rows
    assert env.output_tsv("stan1293", "nonpermutability", "general").exists()     # pair rows


def test_pair_row_constructions_are_read_from_the_schema_not_hardcoded(env):
    """coreference's three constructions and nonpermutability/general are
    pair-row constructions (see the schema's row_type field); phrasal_accent's
    general construction is too, but its live tab is a documented exception --
    #275, still in the pre-pair-rows shape pending Adam's prescreening
    annotation, so it is not useful evidence here. This used to be a
    hardcoded class list in this file that missed phrasal_accent entirely
    (data_dependency_schema/facts.yaml's pair_row_construction_set); confirms
    a genuinely pair-shaped live tab round-trips through _validate_pair_tab
    with its Element_A/Position_A/Position_B columns intact."""
    env.run(["import-sheets", "--lang", "stan1293", "--apply"])
    header = pd.read_csv(
        env.output_tsv("stan1293", "coreference", "reflexive_coreference"), sep="\t", nrows=0,
    ).columns.tolist()
    assert header[:3] == ["Element_A", "Position_A", "Position_B"]
    assert "Element" not in header  # the element-row path's own column


# ---------------------------------------------------------------------------
# Defensive check: import-sheets never writes a criterion-shaped thing onto
# Source/Comments. It reads construction_params for validation only (fed into
# _validate_tab/_validate_pair_tab) and never writes a dropdown or a note --
# its only sheet write is highlight_cells, which paints backgrounds. Expected
# to always pass; kept as a guard against this file gaining such a write later.
# ---------------------------------------------------------------------------

def test_never_writes_a_criterion_shaped_thing_onto_trailing_columns(env):
    env.tab("arao1248", "ciscategorial", "general")._cell(1, 3).value = "maybe123"
    env.run(["import-sheets", "--lang", "arao1248", "--apply"])
    assert_no_criterion_writes_onto_trailing_columns(env.doorway)
