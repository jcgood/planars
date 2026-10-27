"""Snapshot tests for `python -m coding validate-coding`, run against the fake.

File 13 of 18 migrated to the Drive doorway (#271). Its Drive footprint is the
smallest of any command migrated so far: no folder creation, no sharing, no
manifest uploads. `revalidate_sheets()` only downloads the manifest, opens each
language's class spreadsheets, and writes pink cell highlighting back — every
value it validates comes from the local TSVs `import-sheets` already wrote, not
from the Sheet content itself.

**How the pre-migration baseline was taken.** As for every file after the
first, a real-Drive dry run is not permitted before Phase 9, so the substitute
was to drive the *unmigrated* code (`from .drive import _get_clients,
_load_manifest_from_drive, _open_spreadsheet, _with_retry`) from a
`FakeDriveDoorway.from_fixtures()` through thin `gc.open_by_key` /
`_download_file_json` shims, guarding every unshimmed route to real Drive so it
raises rather than quietly working. Twelve scenarios were run through both the
unmigrated and migrated code against identically seeded fakes: all languages,
one `--lang`, `--verbose`, a `--lang` matching nothing in the manifest, a
language with a spreadsheet ID the fake has never seen (exercising the
`except Exception` around `open_spreadsheet`), a language whose local TSV has
an invalid cell value (exercising `highlight_cells`' `batch_update`), each of
the three fixture languages alone (`arao1248` standard-path only,
`synth0001` and `stan1293` exercising the pair-row path via
`coreference`/`nonpermutability`), and `main()` itself across the equivalent
argv combinations to check exit codes. stdout, exit codes, and the mutation
logs came back byte-identical in all twelve. The shim script is a scratch
throwaway per the plan's convention, not committed.

`highlight_cells`/`clear_highlights` (lines ~104-142) needed no edits at all —
they only call `ws.spreadsheet.batch_update(...)`, `ws.id`, `ws.row_count`,
`ws.col_count`, all handle methods that mirror gspread by design.

`CODED_DATA` is redirected into a private copy of the frozen language folders
(`fake_drive.FROZEN_CODED_DATA`) in every test, so a test can corrupt one TSV
cell to exercise the pink-highlight path without ever touching the real
annotation data, and so annotators' ongoing work can't change these snapshots.

Regenerate: PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_validate_coding_snapshot.py
"""
from __future__ import annotations

import io
import os
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import pytest

from coding import drive as drive_module
from coding import drive_doorway
from coding import validate_coding as vc
from command_runner import run_command
from planars.schema_values import STATUS_STATUS_COLUMN
from fake_drive import FROZEN_CODED_DATA, FakeDriveDoorway, MANIFEST_FILE_ID, point_coded_data_at
from render_mutations import render

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "validate_coding"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANGS = ["arao1248", "stan1293", "synth0001"]

# The command reads local TSVs from coded_data/, a separate repo that a bare
# worktree may not have.
pytestmark = pytest.mark.skipif(
    not (ROOT / "coded_data").exists(),
    reason="coded_data/ (planars-data) is not checked out",
)


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """A stand-in Drive seeded from the three fixture languages, and a private
    copy of coded_data/ so a test can corrupt a cell without touching real
    annotation data."""
    doorway = FakeDriveDoorway.from_fixtures()
    coded = tmp_path / "coded_data"
    for lang in LANGS:
        shutil.copytree(FROZEN_CODED_DATA / lang, coded / lang)

    point_coded_data_at(monkeypatch, coded)
    monkeypatch.setattr(drive_module, "_load_drive_config", FakeDriveDoorway.drive_config)
    drive_doorway.set_doorway(doorway)

    def run_main(argv: List[str]) -> Tuple[str, Optional[int]]:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        exit_code = None
        try:
            with redirect_stdout(buf):
                run_command(vc, "validate-coding")
        except SystemExit as exc:
            exit_code = exc.code
        return buf.getvalue(), exit_code

    try:
        yield doorway, coded, run_main
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


def set_cell(coded: Path, lang: str, class_name: str, construction: str,
            match_col: str, match_val: str, target_col: str, new_val: str) -> None:
    """Overwrite one cell of a local TSV, selected by another column's value."""
    path = coded / lang / class_name / f"{construction}.tsv"
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    idx = df.index[df[match_col] == match_val][0]
    df.loc[idx, target_col] = new_val
    df.to_csv(path, sep="\t", index=False)


def sheet_id(doorway, lang: str, class_name: str) -> str:
    manifest = doorway.download_file_json(MANIFEST_FILE_ID)
    info = manifest[lang]["sheets"][class_name]
    return info.get("spreadsheet_id") or info.get("id")


def tab(doorway, lang: str, class_name: str, construction: str):
    return doorway.spreadsheet(sheet_id(doorway, lang, class_name)).worksheet(construction)


# ---------------------------------------------------------------------------
# Coordinator-facing transcripts
# ---------------------------------------------------------------------------

def test_stan1293_transcript(env):
    _, _, run_main = env
    out, _ = run_main(["validate-coding", "--lang", "stan1293"])
    check_snapshot("stan1293.txt", out)


def test_arao1248_transcript(env):
    _, _, run_main = env
    out, _ = run_main(["validate-coding", "--lang", "arao1248"])
    check_snapshot("arao1248.txt", out)


# ---------------------------------------------------------------------------
# --lang restricts to one language
# ---------------------------------------------------------------------------

def test_lang_filter_restricts_output(env):
    _, _, run_main = env
    out, _ = run_main(["validate-coding", "--lang", "arao1248"])
    assert "arao1248" in out
    assert "stan1293" not in out
    assert "synth0001" not in out


def test_no_lang_flag_runs_every_manifest_language(env):
    _, _, run_main = env
    out, _ = run_main(["validate-coding"])
    for lang_id in LANGS:
        assert lang_id in out


# ---------------------------------------------------------------------------
# Status / Instructions / Planar Structure tabs are skipped
# ---------------------------------------------------------------------------

def test_status_instructions_planar_ref_tabs_are_skipped(env):
    """These tabs exist on every fixture spreadsheet touched here (Status on
    all of them; stan1293/synth0001's nonpermutability and coreference also
    carry Planar Structure, and stan1293/phrasal_accent and
    synth0001/nonpermutability and coreference also carry Instructions) -- if
    any leaked through they would report a spurious "no local TSV" error,
    since none of them has a coded_data/ TSV of its own."""
    _, _, run_main = env
    out, _ = run_main(["validate-coding"])
    for tab_name in vc.system_tab_titles():
        assert f"/{tab_name}]" not in out


# ---------------------------------------------------------------------------
# A spreadsheet that cannot be opened is reported per-class, not fatal
# ---------------------------------------------------------------------------

def test_unopenable_spreadsheet_is_reported_and_does_not_crash_the_run(env, monkeypatch):
    import json

    doorway, _, run_main = env
    manifest = doorway.download_file_json(MANIFEST_FILE_ID)
    manifest["arao1248"]["sheets"]["noninterruption"]["spreadsheet_id"] = "nonexistent_ss_xyz"
    doorway.file(MANIFEST_FILE_ID).content = json.dumps(manifest).encode("utf-8")

    out, exit_code = run_main(["validate-coding", "--lang", "arao1248"])
    assert "[noninterruption] could not open spreadsheet:" in out
    # The other two classes for this language are still validated -- one bad
    # spreadsheet does not stop the run.
    assert "[ciscategorial/general]" in out
    assert "[subspanrepetition/auxiliary_construction]" in out
    assert "[subspanrepetition/tso_clause_linkage]" in out
    # No local TSV to compare against, but no crash either -- Python did not
    # propagate an unhandled exception up through run_main (which would have
    # shown up as something other than a clean SystemExit or None here).
    assert exit_code in (None, 1)


# ---------------------------------------------------------------------------
# Blank-cell issues are separated from blocking issues, in the summary and
# in the exit code
# ---------------------------------------------------------------------------

def test_blank_cells_alone_do_not_block(env):
    """arao1248 is entirely blank-annotated and has no shape mismatches, so
    blocking should be zero and main() should not call sys.exit at all --
    even though the transcript reports hundreds of blank cells."""
    _, _, run_main = env
    out, exit_code = run_main(["validate-coding", "--lang", "arao1248"])
    assert "blank cell(s)" in out
    assert "issue(s):" not in out
    assert exit_code is None
    assert "No errors." in out


def set_status(doorway, lang: str, class_name: str, construction: str, value: str) -> None:
    """Set one construction's Status on the fake's Status tab."""
    ws = doorway.spreadsheet(sheet_id(doorway, lang, class_name)).worksheet(vc.STATUS_TAB)
    rows = ws.get_all_values()
    col = rows[0].index(STATUS_STATUS_COLUMN)
    row = next(i for i, r in enumerate(rows) if r and r[0] == construction)
    ws._cell(row, col).value = value


def add_problems_column(doorway, lang: str, class_name: str) -> None:
    """Make sure the fake's Status tab has the column update-sheets adds
    (recordings made before 2026-10-17 lack it)."""
    ws = doorway.spreadsheet(sheet_id(doorway, lang, class_name)).worksheet(vc.STATUS_TAB)
    header = ws.get_all_values()[0]
    if vc.STATUS_PROBLEMS_COLUMN not in header:
        ws.update([[vc.STATUS_PROBLEMS_COLUMN]], vc.rowcol_to_a1(1, len(header) + 1))


def remove_problems_column(doorway, lang: str, class_name: str) -> None:
    """Make the fake's Status tab look like one made before the column existed."""
    ws = doorway.spreadsheet(sheet_id(doorway, lang, class_name)).worksheet(vc.STATUS_TAB)
    rows = ws.get_all_values()
    drop = rows[0].index(vc.STATUS_PROBLEMS_COLUMN)
    ws.clear()
    ws.update([r[:drop] + r[drop + 1:] for r in rows], "A1")


def status_cell(doorway, lang: str, class_name: str, construction: str, column: str) -> str:
    rows = doorway.spreadsheet(sheet_id(doorway, lang, class_name)).worksheet(
        vc.STATUS_TAB).get_all_values()
    col = rows[0].index(column)
    row = next(r for r in rows if r and r[0] == construction)
    return row[col] if col < len(row) else ""


def problems_cell(doorway, lang: str, class_name: str, construction: str) -> str:
    return status_cell(doorway, lang, class_name, construction, vc.STATUS_PROBLEMS_COLUMN)


def test_an_invalid_value_on_an_in_progress_tab_is_only_a_warning(env):
    """#309: the annotator is still working on the tab, so a bad value is
    pink and listed as a warning, not an error, and nothing is exited on."""
    doorway, coded, run_main = env
    set_cell(coded, "arao1248", "ciscategorial", "general",
            "Element", "ADVERBIALS", "V-combines", "maybe")

    out, exit_code = run_main(["validate-coding", "--lang", "arao1248"])
    assert exit_code is None
    assert "1 issue(s):" in out
    assert "[WARNING] general row" in out and "unexpected value 'maybe' in 'V-combines'" in out
    # The blank cells on the rest of the tab are still counted, but noted
    # separately from the issue rather than folded into it.
    assert "blank cell(s) — annotation in progress; use --verbose to list" in out


def test_an_invalid_value_on_a_ready_tab_is_an_error_listed_in_the_status_tab(env):
    """#309: on a tab marked ready-for-review the same value is an error (the
    sheet-validation workflow files an issue), and the Status tab's problems
    column names it for the annotator; fixing it blanks the cell again."""
    doorway, coded, run_main = env
    set_status(doorway, "arao1248", "ciscategorial", "general", vc.STATUS_READY)
    add_problems_column(doorway, "arao1248", "ciscategorial")
    set_cell(coded, "arao1248", "ciscategorial", "general",
            "Element", "ADVERBIALS", "V-combines", "maybe")

    out, exit_code = run_main(["validate-coding", "--lang", "arao1248"])
    assert exit_code == 1
    assert "[ERROR] general row" in out and "unexpected value 'maybe' in 'V-combines'" in out
    text = problems_cell(doorway, "arao1248", "ciscategorial", "general")
    assert text.startswith("row ") and "(ADVERBIALS), V-combines: 'maybe' — should be one of:" in text
    assert "\n" not in text

    set_cell(coded, "arao1248", "ciscategorial", "general",
            "Element", "ADVERBIALS", "V-combines", "y")
    out, exit_code = run_main(["validate-coding", "--lang", "arao1248"])
    assert exit_code is None
    assert problems_cell(doorway, "arao1248", "ciscategorial", "general") == ""


def test_a_status_tab_without_the_problems_column_is_reported_not_written(env):
    doorway, coded, run_main = env
    remove_problems_column(doorway, "arao1248", "ciscategorial")
    set_status(doorway, "arao1248", "ciscategorial", "general", vc.STATUS_READY)
    set_cell(coded, "arao1248", "ciscategorial", "general",
            "Element", "ADVERBIALS", "V-combines", "maybe")
    out, _ = run_main(["validate-coding", "--lang", "arao1248"])
    assert (f"[ciscategorial] its Status tab has no '{vc.STATUS_PROBLEMS_COLUMN}' column yet"
            in out)
    assert "update-sheets --apply adds it" in out


# ---------------------------------------------------------------------------
# --notify: the annotator hears about it (#309 step 3)
# ---------------------------------------------------------------------------

def _break_a_ready_tab(doorway, coded, value="maybe"):
    set_status(doorway, "arao1248", "ciscategorial", "general", vc.STATUS_READY)
    add_problems_column(doorway, "arao1248", "ciscategorial")
    set_cell(coded, "arao1248", "ciscategorial", "general",
            "Element", "ADVERBIALS", "V-combines", value)


def _with_github(monkeypatch, username):
    import coding.people
    monkeypatch.setattr(coding.people, "_load_people", lambda: {
        "Adam Tallman": {"email": "annotator@example.org", "github": username}})


def test_notify_mentions_an_annotator_with_github_once_per_new_problem(env, github, monkeypatch):
    doorway, coded, run_main = env
    _with_github(monkeypatch, "annotator-gh")
    _break_a_ready_tab(doorway, coded)
    # Marked, so only the bad value keeps the issue open.
    for t in ("auxiliary_construction", "tso_clause_linkage"):
        set_status(doorway, "arao1248", "subspanrepetition", t, vc.STATUS_READY)

    out, _ = run_main(["validate-coding", "--lang", "arao1248", "--notify"])
    [issue] = [i for i in github.issues if "needs-fixing" in i["labels"]]
    assert issue["title"] == "To do in the Araona [arao1248] sheets"
    assert "@annotator-gh" in issue["body"]
    assert "**ciscategorial**: 1 cell to fix" in issue["body"]
    assert "Status tab" in issue["body"]
    assert f"arao1248: filed #{issue['number']}" in out
    assert not doorway.list_comments(sheet_id(doorway, "arao1248", "ciscategorial"))

    # The same problem the next day: nobody is told again.
    out, _ = run_main(["validate-coding", "--lang", "arao1248", "--notify"])
    assert "nothing new to tell the annotator" in out
    assert not github.comments.get(issue["number"])

    # A different bad value is a new problem: a comment mentions them.
    set_cell(coded, "arao1248", "ciscategorial", "general",
            "Element", "ADVERBIALS", "V-combines", "perhaps")
    run_main(["validate-coding", "--lang", "arao1248", "--notify"])
    [comment] = github.comments[issue["number"]]
    assert comment.startswith("@annotator-gh something new on your sheets")

    # Fixed: the issue closes.
    set_cell(coded, "arao1248", "ciscategorial", "general",
            "Element", "ADVERBIALS", "V-combines", "y")
    out, _ = run_main(["validate-coding", "--lang", "arao1248", "--notify"])
    assert github.issue(issue["number"])["state"] == "CLOSED"
    assert f"arao1248: closed #{issue['number']}" in out


def test_a_finished_tab_is_marked_ready_and_the_annotator_told(env, github, monkeypatch):
    """arao1248's two subspanrepetition tabs have every cell answered and no
    errors but are still in-progress: the check marks them ready-for-review
    and the issue tells the annotator; the next day nothing is left."""
    doorway, coded, run_main = env
    _with_github(monkeypatch, "annotator-gh")
    add_problems_column(doorway, "arao1248", "subspanrepetition")
    tabs = ["auxiliary_construction", "tso_clause_linkage"]
    for t in tabs:
        set_status(doorway, "arao1248", "subspanrepetition", t, vc.STATUS_IN_PROGRESS)

    out, _ = run_main(["validate-coding", "--lang", "arao1248", "--notify"])
    assert (f"every cell answered with no errors, so marked {vc.STATUS_READY}: "
            f"{', '.join(tabs)}") in out
    ss = doorway.spreadsheet(sheet_id(doorway, "arao1248", "subspanrepetition"))
    statuses = vc.tab_statuses(ss)
    for t in tabs:
        assert statuses[t] == vc.STATUS_READY
        assert problems_cell(doorway, "arao1248", "subspanrepetition", t) == ""
        assert (status_cell(doorway, "arao1248", "subspanrepetition", t,
                            vc.STATUS_MARKED_BY_COLUMN)
                == vc.marked_by_text(vc.MARKED_BY_CHECK))
    [issue] = [i for i in github.issues if "needs-fixing" in i["labels"]]
    assert f"{', '.join(tabs)} finished, so marked {vc.STATUS_READY}" in issue["body"]

    run_main(["validate-coding", "--lang", "arao1248", "--notify"])
    assert github.issue(issue["number"])["state"] == "CLOSED"


def test_marked_by_records_the_annotator_and_clears_when_set_back(env):
    """A ready tab the tooling didn't mark was marked by hand; a tab set back
    to in-progress loses its Marked by, so a later hand mark reads right."""
    doorway, coded, run_main = env
    set_status(doorway, "arao1248", "ciscategorial", "general", vc.STATUS_READY)
    run_main(["validate-coding", "--lang", "arao1248"])
    assert (status_cell(doorway, "arao1248", "ciscategorial", "general",
                        vc.STATUS_MARKED_BY_COLUMN)
            == vc.marked_by_text(vc.MARKED_BY_ANNOTATOR))
    set_status(doorway, "arao1248", "ciscategorial", "general", vc.STATUS_IN_PROGRESS)
    run_main(["validate-coding", "--lang", "arao1248"])
    assert status_cell(doorway, "arao1248", "ciscategorial", "general",
                       vc.STATUS_MARKED_BY_COLUMN) == ""


def test_a_tab_with_a_blank_cell_is_not_marked(env):
    doorway, coded, run_main = env
    add_problems_column(doorway, "arao1248", "subspanrepetition")
    set_status(doorway, "arao1248", "subspanrepetition", "tso_clause_linkage",
               vc.STATUS_IN_PROGRESS)
    path = coded / "arao1248" / "subspanrepetition" / "tso_clause_linkage.tsv"
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    row = df[df["Position_Name"] != vc._KEYSTONE_NAME].iloc[0]
    criterion = next(c for c in df.columns if c not in vc.ELEMENT_ROW_COLUMNS
                     and c not in vc.TRAILING_COLUMNS)
    set_cell(coded, "arao1248", "subspanrepetition", "tso_clause_linkage",
             "Element", row["Element"], criterion, "")
    run_main(["validate-coding", "--lang", "arao1248"])
    ss = doorway.spreadsheet(sheet_id(doorway, "arao1248", "subspanrepetition"))
    assert vc.tab_statuses(ss).get("tso_clause_linkage") != vc.STATUS_READY


def test_notify_comments_on_the_sheet_for_an_annotator_without_github(env, github):
    doorway, coded, run_main = env
    _break_a_ready_tab(doorway, coded)

    run_main(["validate-coding", "--lang", "arao1248", "--notify"])
    sid = sheet_id(doorway, "arao1248", "ciscategorial")
    [comment] = doorway.list_comments(sid)
    assert comment["content"] == ("+annotator@example.org 1 cell needs fixing: see the "
                                  "Status tab, column 'Needs fixing'.")
    [issue] = [i for i in github.issues if "needs-fixing" in i["labels"]]
    assert "no GitHub username in people.yaml" in issue["body"]

    run_main(["validate-coding", "--lang", "arao1248", "--notify"])
    assert len(doorway.list_comments(sid)) == 1


def test_notify_leaves_a_language_alone_when_a_sheet_could_not_be_checked(env, github):
    import json
    doorway, coded, run_main = env
    _break_a_ready_tab(doorway, coded)
    manifest = doorway.download_file_json(MANIFEST_FILE_ID)
    manifest["arao1248"]["sheets"]["noninterruption"]["spreadsheet_id"] = "nonexistent_ss_xyz"
    doorway.file(MANIFEST_FILE_ID).content = json.dumps(manifest).encode("utf-8")

    out, _ = run_main(["validate-coding", "--lang", "arao1248", "--notify"])
    assert "arao1248: not every sheet could be checked" in out
    assert not [i for i in github.issues if "needs-fixing" in i["labels"]]


def test_without_notify_nobody_is_told(env, github):
    doorway, coded, run_main = env
    _break_a_ready_tab(doorway, coded)
    run_main(["validate-coding", "--lang", "arao1248"])
    assert not [i for i in github.issues if "needs-fixing" in i["labels"]]
    assert not doorway.list_comments(sheet_id(doorway, "arao1248", "ciscategorial"))


def test_needs_fixing_is_the_one_rule():
    invalid = vc._invalid("t row 2 'x'", 2, "x", "c", "q", "should be one of: n, y",
                          (1, 3), "unexpected value 'q' in 'c'")
    blank = vc._blank("t row 2 'x'", "c", (1, 3))
    assert vc.needs_fixing(invalid, vc.STATUS_READY)
    assert not vc.needs_fixing(invalid, vc.STATUS_IN_PROGRESS)
    assert not vc.needs_fixing(blank, vc.STATUS_READY)
    graded = vc.grade([invalid, blank], vc.STATUS_READY)
    assert [i.level for i in graded] == ["error", "warning"]
    assert vc.problems_text(graded) == "row 2 (x), c: 'q' — should be one of: n, y"


def test_a_long_list_of_problems_is_cut_short():
    issues = [vc.dataclasses.replace(
        vc._invalid("w", n, "x", "c", "q", "should be 'na'", (n, 1), "m"), level="error")
        for n in range(2, 40)]
    lines = vc.problems_text(issues).split("\n")
    assert len(lines) == vc._MAX_PROBLEM_LINES + 1
    assert lines[-1] == "…and 18 more (the pink cells on the tab)"


# ---------------------------------------------------------------------------
# Pink highlighting: written for an invalid cell, cleared once it is fixed
# ---------------------------------------------------------------------------

def test_invalid_cell_gets_pink_highlight(env):
    doorway, coded, run_main = env
    set_cell(coded, "stan1293", "ciscategorial", "general",
            "Element", "and", "V-combines", "maybe")

    run_main(["validate-coding", "--lang", "stan1293"])

    ws = tab(doorway, "stan1293", "ciscategorial", "general")
    # "and" is the second data row (row_num=3) -> 0-based sheet row 2;
    # V-combines is the fourth column (0-based index 3).
    assert ws._cell(2, 3).background == vc._PINK

    updates = [m for m in doorway.mutations
              if m.get("op") == "batch_request" and m["request_type"] == "updateCells"]
    assert updates, "highlight_cells should have fired an updateCells request"


def test_fixing_the_value_clears_its_highlight(env):
    doorway, coded, run_main = env
    set_cell(coded, "stan1293", "ciscategorial", "general",
            "Element", "and", "V-combines", "maybe")
    run_main(["validate-coding", "--lang", "stan1293"])
    ws = tab(doorway, "stan1293", "ciscategorial", "general")
    assert ws._cell(2, 3).background == vc._PINK

    set_cell(coded, "stan1293", "ciscategorial", "general",
            "Element", "and", "V-combines", "y")
    run_main(["validate-coding", "--lang", "stan1293"])
    assert ws._cell(2, 3).background == vc._WHITE


def test_apply_mutation_digest(env):
    """The rendered mutation log for one tab's revalidation -- the artifact a
    human actually reviews, tab titles and column headers resolved rather than
    raw sheetIds and 0-based indices (docs/data-layer-progress.md § "Weight the
    automated evidence, not the human review"). Scoped to a single construction
    (rather than a whole-language run through main()) so the digest stays
    something a person can actually read start to finish, not 1000+ lines of
    blank-cell noise from every other tab in the language."""
    doorway, coded, run_main = env
    set_cell(coded, "stan1293", "ciscategorial", "general",
            "Element", "and", "V-combines", "maybe")

    ws = tab(doorway, "stan1293", "ciscategorial", "general")
    param_map = vc._load_param_map("stan1293")
    info = param_map["ciscategorial"]["general"]
    vc.revalidate_sheet(ws, "stan1293", "ciscategorial", "general",
                        info["params"], info["values"])

    check_snapshot("invalid_cell_digest.txt", render(doorway.mutations))


# ---------------------------------------------------------------------------
# Pair-row constructions go through the pair path; standard constructions
# through the element path -- distinguishable in the transcript
# ---------------------------------------------------------------------------

def test_pair_row_construction_uses_the_pair_path(env):
    """coreference/reflexive_coreference is row_type: pair_rows. Its issue labels
    read "Element_A -> pos Position_B", which only validate_pair_rows
    produces -- validate_annotation_rows labels a row by its own Element."""
    doorway, coded, run_main = env
    set_cell(coded, "stan1293", "coreference", "reflexive_coreference",
            "Element_A", "NP{S,A,P}", "reflexive_allowed", "maybe")

    out, _ = run_main(["validate-coding", "--lang", "stan1293"])
    assert "coreference/reflexive_coreference" in out
    assert "→ pos" in out
    assert "unexpected value 'maybe' in 'reflexive_allowed'" in out


def test_standard_construction_uses_the_element_path(env):
    """ciscategorial/general is row_type: element (the default). Its issue
    labels read "row N 'element name'", with no pair-row arrow."""
    doorway, coded, run_main = env
    set_cell(coded, "stan1293", "ciscategorial", "general",
            "Element", "and", "V-combines", "maybe")

    out, _ = run_main(["validate-coding", "--lang", "stan1293"])
    assert "ciscategorial/general" in out
    assert "row 3 'and'" in out
    assert "→ pos" not in out
