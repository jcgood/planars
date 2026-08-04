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

`CODED_DATA` is redirected into a private copy of the real `coded_data/` tree
in every test, so a test can corrupt one TSV cell to exercise the pink-highlight
path without ever touching the real annotation data.

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
from fake_drive import FakeDriveDoorway, MANIFEST_FILE_ID
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
        shutil.copytree(ROOT / "coded_data" / lang, coded / lang)

    monkeypatch.setattr(vc, "CODED_DATA", coded)
    monkeypatch.setattr(drive_module, "_load_drive_config", FakeDriveDoorway.drive_config)
    drive_doorway.set_doorway(doorway)

    def run_main(argv: List[str]) -> Tuple[str, Optional[int]]:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        exit_code = None
        try:
            with redirect_stdout(buf):
                vc.main()
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
    for tab_name in (vc._STATUS_TAB, vc._INSTRUCTIONS_TAB, vc._PLANAR_REF_TAB):
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
    assert "All data coding issues cleared." in out


def test_an_invalid_value_blocks_and_is_reported_separately_from_blanks(env):
    doorway, coded, run_main = env
    set_cell(coded, "arao1248", "ciscategorial", "general",
            "Element", "ADVERBIALS", "V-combines", "maybe")

    out, exit_code = run_main(["validate-coding", "--lang", "arao1248"])
    assert exit_code == 1
    assert "1 issue(s):" in out
    assert "unexpected value 'maybe' in 'V-combines'" in out
    # The blank cells on the rest of the tab are still counted, but noted
    # separately from the blocking issue rather than folded into it.
    assert "blank cell(s) — annotation in progress; use --verbose to list" in out
    assert "Cell highlighting updated in Google Sheets." in out


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
    """coreference/reflexivization is row_type: pair_rows. Its issue labels
    read "Element_A -> pos Position_B", which only validate_pair_rows
    produces -- validate_annotation_rows labels a row by its own Element."""
    doorway, coded, run_main = env
    set_cell(coded, "stan1293", "coreference", "reflexivization",
            "Element_A", "NP{S,A,P}", "reflexive_allowed", "maybe")

    out, _ = run_main(["validate-coding", "--lang", "stan1293"])
    assert "coreference/reflexivization" in out
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
