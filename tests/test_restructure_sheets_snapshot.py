"""Snapshot tests for `python -m coding restructure-sheets`, run against the fake.

File 18 of 18 migrated to the Drive doorway (#271) -- the last one, deliberately:
the archive-then-rebuild command with no rollback, behind #248's original
stray-row/silent-revert incidents. Once a spreadsheet is archived and a new one
created there is no undo, so this file's migration got the fullest before/after
comparison of any in the effort.

Before migrating, the old code was driven from a stand-in Drive through
`gc`/`drive` shims patched into a private copy of the pre-migration file
(placed temporarily inside `coding/` so its own relative imports resolved, then
deleted -- never committed), across thirteen scenarios: a plain dry run and a
true no-op `--apply` over the real fixture data (nothing in the current
repository needs restructuring, so every class hits "no changes -- skipping",
confirmed rather than assumed); `--rename-map` carrying over a renamed position
(dry run and apply, across every class for one language including its pair-row
constructions); `--rename-element`; `--split-element` fanning one element into
two, cascading into the pair-row tab that references it
(`nonpermutability/general`); the same split with a synthetic self-pair row
injected into the fake beforehand (left untouched, flagged for manual review,
never fanned out); `--rename-class` both the pre-flight abort (old class still
active) and a real apply after the diagnostics files were updated first; a
missing construction tab hit on both the download step and the
`_copy_pair_tab_with_rename` step (deleting a coreference pair tab from the
fixture before a rename-map apply that restructures every class in that
language); `--lang` restricting to one language while two others are seeded;
and a class absent from the manifest. `_autocommit_data`, `generate_notebooks.
regenerate_notebooks`, `validate_coding.revalidate_sheets`, and `import_planar.
push_planars_to_sheets` were stubbed identically on both sides (file 15's
precedent -- what this harness diffs is restructure_sheets.py's own Drive
interaction, not theirs). stdout, the mutation log, `sheets_manifest.json`
writes, and every `coded_data/` TSV written all came back byte-identical
between the unmigrated and migrated code across all thirteen.

Two harness lessons confirmed again, both already named in
docs/data-layer-progress.md's decisions log for earlier files: `load_manifest`/
`upload_manifest` (coding/drive.py) call *that module's own* `_load_drive_config`
internally, so patching only the importing module's copy of the name is not
enough (file 5's, then file 15's, lesson); and `_autocommit_data` reads *that
module's own* `CODED_DATA` constant rather than any path threaded through it,
so it was stubbed rather than driven for real, the same way the notebook/
revalidate/push-planar calls were.

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_restructure_sheets_snapshot.py`
"""
from __future__ import annotations

import io
import os
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable, Dict, List

import pandas as pd
import pytest

from coding import drive as drive_module
from coding import drive_doorway
from coding import generate_notebooks as gn
from coding import import_planar as ip
from coding import restructure_journal as rj
from coding import restructure_sheets as rs
from coding import validate_coding as vc
from fake_drive import FakeDriveDoorway, MANIFEST_FILE_ID
from mutation_checks import assert_no_criterion_writes_onto_trailing_columns
from render_mutations import render

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "restructure_sheets"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANGS = ["arao1248", "stan1293", "synth0001"]

# The command reads each language's planar/diagnostics files from coded_data/,
# a separate repo that a bare worktree may not have.
pytestmark = pytest.mark.skipif(
    not (ROOT / "coded_data").exists(),
    reason="coded_data/ (planars-data) is not checked out",
)


class Env:
    """One stand-in Drive, one private copy of the language setup files."""

    def __init__(self, doorway: FakeDriveDoorway, coded: Path,
                 saved_configs: List[dict], autocommit_calls: List[tuple],
                 notebook_calls: List[bool], revalidate_calls: List[dict],
                 push_planar_calls: List[dict],
                 run: Callable[[List[str]], str]) -> None:
        self.doorway = doorway
        self.coded = coded
        self.saved_configs = saved_configs
        self.autocommit_calls = autocommit_calls
        self.notebook_calls = notebook_calls
        self.revalidate_calls = revalidate_calls
        self.push_planar_calls = push_planar_calls
        self.run = run

    # -- the manifest ---------------------------------------------------
    def manifest(self) -> Dict:
        return self.doorway.download_file_json(MANIFEST_FILE_ID)

    def sheet_id(self, lang: str, class_name: str) -> str:
        return self.manifest()[lang]["sheets"][class_name]["spreadsheet_id"]

    def spreadsheet(self, lang: str, class_name: str):
        return self.doorway.spreadsheet(self.sheet_id(lang, class_name))

    def tab(self, lang: str, class_name: str, construction: str):
        return self.spreadsheet(lang, class_name).worksheet(construction)

    # -- the local planar / diagnostics files ----------------------------
    def planar_path(self, lang: str) -> Path:
        return self.coded / lang / "lang_setup" / f"planar_{lang}.tsv"

    def diagnostics_tsv_path(self, lang: str) -> Path:
        return self.coded / lang / "lang_setup" / f"diagnostics_{lang}.tsv"

    def diagnostics_yaml_path(self, lang: str) -> Path:
        return self.coded / lang / "lang_setup" / f"diagnostics_{lang}.yaml"

    def _edit_planar(self, lang: str, fn) -> None:
        path = self.planar_path(lang)
        df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
        fn(df)
        df.to_csv(path, sep="\t", index=False)

    def rename_position(self, lang: str, old: str, new: str) -> None:
        self._edit_planar(lang, lambda df: df.__setitem__(
            "Position_Name", df["Position_Name"].replace(old, new)))

    def _edit_elements(self, lang: str, old: str, replacement: List[str]) -> None:
        def fn(df):
            for i, cell in df["Elements"].items():
                tokens = [t.strip() for t in cell.split(",")]
                if old in tokens:
                    idx = tokens.index(old)
                    tokens[idx:idx + 1] = replacement
                    df.at[i, "Elements"] = ", ".join(tokens)
        self._edit_planar(lang, fn)

    def rename_element(self, lang: str, old: str, new: str) -> None:
        self._edit_elements(lang, old, [new])

    def split_element(self, lang: str, old: str, news: List[str]) -> None:
        self._edit_elements(lang, old, news)

    def rename_class_in_diagnostics(self, lang: str, old: str, new: str) -> None:
        tsv_path = self.diagnostics_tsv_path(lang)
        tsv_path.write_text(
            tsv_path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
        yaml_path = self.diagnostics_yaml_path(lang)
        yaml_path.write_text(
            yaml_path.read_text(encoding="utf-8").replace(f"{old}:", f"{new}:"),
            encoding="utf-8")

    def inject_pair_row(self, lang: str, class_name: str, construction: str,
                        a: str, b: str, criterion_col: str, value: str) -> None:
        """Append a synthetic Element_A/Element_B row directly on the fake tab."""
        ws = self.tab(lang, class_name, construction)
        vals = ws.get_all_values()
        header = vals[0]
        row = [""] * len(header)
        row[header.index("Element_A")] = a
        row[header.index("Element_B")] = b
        row[header.index(criterion_col)] = value
        ws.update([row], f"A{len(vals) + 1}")

    def delete_tab(self, lang: str, class_name: str, construction: str) -> None:
        ss = self.spreadsheet(lang, class_name)
        ss.del_worksheet(ss.worksheet(construction))

    def remove_class_from_manifest(self, lang: str, class_name: str) -> None:
        manifest = self.manifest()
        del manifest[lang]["sheets"][class_name]
        self.doorway.update_file(
            MANIFEST_FILE_ID,
            content=__import__("json").dumps(manifest).encode("utf-8"))

    # -- reading the stand-in Drive back ----------------------------------
    def all_tab_values(self) -> Dict:
        return {
            (ss_id, ws.title): ws.get_all_values()
            for ss_id, ss in self.doorway._spreadsheets.items()
            for ws in ss.worksheets()
        }


@pytest.fixture()
def env(monkeypatch, tmp_path):
    doorway = FakeDriveDoorway.from_fixtures()

    coded = tmp_path / "coded_data"
    for lang in LANGS:
        shutil.copytree(ROOT / "coded_data" / lang / "lang_setup",
                        coded / lang / "lang_setup")

    saved_configs: List[dict] = []
    autocommit_calls: List[tuple] = []
    notebook_calls: List[bool] = []
    revalidate_calls: List[dict] = []
    push_planar_calls: List[dict] = []

    monkeypatch.setattr(rs, "CODED_DATA", coded)
    monkeypatch.setattr(rs, "MANIFEST_PATH", tmp_path / "sheets_manifest.json")
    # restructure_journal's JOURNAL_PATH default is resolved fresh per call
    # (never bound into a default parameter -- see that module's docstring),
    # so patching the module attribute here reaches every call
    # restructure_sheets.py makes without needing rs's own copy patched too.
    monkeypatch.setattr(rj, "JOURNAL_PATH", tmp_path / "restructure_journal.json")
    monkeypatch.setattr(rs, "_load_drive_config", FakeDriveDoorway.drive_config)
    monkeypatch.setattr(drive_module, "_load_drive_config",
                        FakeDriveDoorway.drive_config)
    monkeypatch.setattr(rs, "_save_drive_config", saved_configs.append)
    monkeypatch.setattr(rs, "_autocommit_data",
                        lambda paths, message: autocommit_calls.append(
                            (sorted(str(p.relative_to(coded)) for p in paths), message)))
    monkeypatch.setattr(gn, "regenerate_notebooks",
                        lambda: notebook_calls.append(True))
    monkeypatch.setattr(vc, "revalidate_sheets",
                        lambda lang_ids=None: revalidate_calls.append(
                            {"lang_ids": lang_ids}))
    monkeypatch.setattr(ip, "push_planars_to_sheets",
                        lambda lang_ids=None, apply=False: push_planar_calls.append(
                            {"lang_ids": lang_ids, "apply": apply}) or [])
    # notify.* is imported by name at module load time in restructure_sheets.py,
    # so patching coding.notify doesn't reach the already-bound names -- patch
    # this module's own copies directly (mirrors the harness used to take the
    # pre-migration baseline).
    monkeypatch.setattr(rs, "ensure_notification_issue",
                        lambda lang_id, manifest: (999, False))
    monkeypatch.setattr(rs, "post_notification_comment", lambda *a, **kw: None)
    drive_doorway.set_doorway(doorway)

    def run(argv: List[str]) -> str:
        monkeypatch.setattr(sys, "argv", ["restructure-sheets"] + argv)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                rs.main()
        except SystemExit as exc:
            if exc.code:
                buf.write(f"[SystemExit: {exc.code}]\n")
        return buf.getvalue()

    try:
        yield Env(doorway, coded, saved_configs, autocommit_calls,
                  notebook_calls, revalidate_calls, push_planar_calls, run)
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


# ---------------------------------------------------------------------------
# What the coordinator sees
# ---------------------------------------------------------------------------

def test_dry_run_baseline_transcript(env):
    """Real fixture data as committed. Nothing here needs restructuring today."""
    check_snapshot("dry_run_baseline.txt", env.run([]))


def test_apply_baseline_is_a_true_no_op(env):
    """Every class hits "no changes -- skipping"; nothing is archived or created."""
    out = env.run(["--apply"])
    check_snapshot("apply_baseline.txt", out)
    assert "Archived" not in out
    assert "New sheet" not in out
    assert env.doorway.mutations_of("create_spreadsheet") == []


def test_dry_run_rename_map_transcript(env):
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    check_snapshot(
        "rename_map_dry.txt",
        env.run(["--lang", "stan1293", "--rename-map", "v:npsubj1:v:npsubj1new"]))


def test_apply_rename_map_transcript(env):
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    check_snapshot(
        "rename_map_apply.txt",
        env.run(["--apply", "--lang", "stan1293",
                "--rename-map", "v:npsubj1:v:npsubj1new"]))


def test_apply_rename_map_digest(env):
    """The rendered write log -- the artifact reviewed, not the raw JSON.

    Archive-then-rebuild is the highest-stakes write this whole migration
    touched, so this is the fullest human-review digest of the effort.
    """
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    env.run(["--apply", "--lang", "stan1293",
             "--rename-map", "v:npsubj1:v:npsubj1new"])
    check_snapshot("rename_map_apply_digest.txt", render(env.doorway.mutations))


def test_apply_rename_element_transcript(env):
    env.rename_element("stan1293", "her", "HER")
    check_snapshot(
        "rename_element_apply.txt",
        env.run(["--apply", "--lang", "stan1293", "--rename-element", "her:HER"]))


def test_apply_split_element_transcript(env):
    """Cascades into nonpermutability/general, the pair-row tab referencing 'her'."""
    env.split_element("stan1293", "her", ["HERACC", "HERDAT"])
    check_snapshot(
        "split_element_apply.txt",
        env.run(["--apply", "--lang", "stan1293",
                "--split-element", "her:HERACC,HERDAT"]))


def test_apply_split_element_digest(env):
    env.split_element("stan1293", "her", ["HERACC", "HERDAT"])
    env.run(["--apply", "--lang", "stan1293", "--split-element", "her:HERACC,HERDAT"])
    check_snapshot("split_element_apply_digest.txt", render(env.doorway.mutations))


def test_apply_split_element_self_pair_transcript(env):
    """A row where BOTH sides are the retired element is flagged, not fanned out."""
    env.split_element("stan1293", "her", ["HERACC", "HERDAT"])
    env.inject_pair_row("stan1293", "nonpermutability", "general",
                        "her", "her", "scopal", "y")
    check_snapshot(
        "split_element_self_pair.txt",
        env.run(["--apply", "--lang", "stan1293",
                "--split-element", "her:HERACC,HERDAT"]))


def test_rename_class_preflight_abort_transcript(env):
    """proform is still active in diagnostics -- must abort before any write."""
    check_snapshot(
        "rename_class_preflight_abort.txt",
        env.run(["--apply", "--lang", "stan1293",
                "--rename-class", "proform:proform_renamed"]))


def test_rename_class_apply_transcript(env):
    env.rename_class_in_diagnostics("stan1293", "proform", "proform_renamed")
    check_snapshot(
        "rename_class_apply.txt",
        env.run(["--apply", "--lang", "stan1293",
                "--rename-class", "proform:proform_renamed"]))


def test_missing_tab_hit_on_download_and_pair_copy(env):
    """Deleting a coreference pair tab before a restructuring apply hits
    WorksheetNotFound twice: once downloading annotations, once re-copying."""
    env.delete_tab("stan1293", "coreference", "np_reference")
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    out = env.run(["--apply", "--lang", "stan1293",
                  "--rename-map", "v:npsubj1:v:npsubj1new"])
    check_snapshot("missing_tab.txt", out)
    assert out.count("[np_reference] tab not found") == 1


def test_lang_filter_leaves_other_languages_untouched(env):
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    before = {
        lang: env.manifest()[lang]["sheets"]
        for lang in ("arao1248", "synth0001")
    }
    env.run(["--apply", "--lang", "stan1293",
            "--rename-map", "v:npsubj1:v:npsubj1new"])
    after = {
        lang: env.manifest()[lang]["sheets"]
        for lang in ("arao1248", "synth0001")
    }
    assert before == after


def test_a_class_absent_from_the_manifest_is_named_and_skipped(env):
    env.remove_class_from_manifest("stan1293", "proform")
    out = env.run(["--apply", "--lang", "stan1293"])
    assert "proform: not in manifest, skipping" in out


# ---------------------------------------------------------------------------
# The dry run writes nothing
# ---------------------------------------------------------------------------

def test_the_dry_run_changes_nothing_anywhere(env):
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    before = env.all_tab_values()

    env.run(["--lang", "stan1293", "--rename-map", "v:npsubj1:v:npsubj1new"])

    assert env.doorway.mutations == []
    assert env.all_tab_values() == before


def test_the_dry_run_saves_no_config_and_calls_no_downstream_command(env):
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    env.run(["--lang", "stan1293", "--rename-map", "v:npsubj1:v:npsubj1new"])
    assert env.saved_configs == []
    assert env.notebook_calls == []
    assert env.revalidate_calls == []
    assert env.push_planar_calls == []
    assert env.autocommit_calls == []


def test_rename_class_dry_run_does_not_write_even_after_preflight_passes(env):
    env.rename_class_in_diagnostics("stan1293", "proform", "proform_renamed")
    env.run(["--lang", "stan1293", "--rename-class", "proform:proform_renamed"])
    assert env.doorway.mutations == []


# ---------------------------------------------------------------------------
# Finding 17: --apply must refuse to run against a dirty coded_data/ tree,
# same as import-sheets/update-sheets/sync-params/generate-sheets
# --regen-dependents -- this file reads planar_{lang_id}.tsv and
# diagnostics_{lang_id}.tsv from coded_data/ as its source of truth for the
# new sheet structure just like those commands do, and is the single most
# destructive command in the project (archive-then-recreate, no rollback).
# coded_data_clean_tree is enforced centrally at the python -m coding
# dispatch chokepoint now, not inside rs.main() itself -- see
# coding/preconditions.py and tests/test_preconditions.py, which cover this
# command's gating directly against the real operations.yaml record.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# The pre-flight check for --rename-class aborts before any Drive write
# ---------------------------------------------------------------------------

def test_rename_class_preflight_abort_writes_nothing(env):
    before = env.all_tab_values()
    env.run(["--apply", "--lang", "stan1293",
            "--rename-class", "proform:proform_renamed"])
    assert env.doorway.mutations == []
    assert env.all_tab_values() == before


# ---------------------------------------------------------------------------
# --split-element: the self-pair is left untouched, not guessed at
# ---------------------------------------------------------------------------

def test_self_pair_row_survives_a_split_untouched(env):
    env.split_element("stan1293", "her", ["HERACC", "HERDAT"])
    env.inject_pair_row("stan1293", "nonpermutability", "general",
                        "her", "her", "scopal", "y")
    out = env.run(["--apply", "--lang", "stan1293",
                  "--split-element", "her:HERACC,HERDAT"])

    assert "NEEDS MANUAL REVIEW" in out
    header = env.tab("stan1293", "nonpermutability", "general").get_all_values()[0]
    rows = env.tab("stan1293", "nonpermutability", "general").get_all_values()[1:]
    a_idx, b_idx = header.index("Element_A"), header.index("Element_B")
    self_pairs = [r for r in rows if r[a_idx] == "her" and r[b_idx] == "her"]
    assert len(self_pairs) == 1, (
        "the self-pair row must survive exactly once -- not dropped, not "
        "duplicated, not fanned out into HERACC/HERDAT combinations")
    fanned = [r for r in rows if r[a_idx] in ("HERACC", "HERDAT")
             and r[b_idx] in ("HERACC", "HERDAT")]
    assert not fanned, "a self-pair must never be guessed at as a same-side pair"


# ---------------------------------------------------------------------------
# Findings check -- the recurring "manifest is authoritative for a tab's
# columns" mistake (#272, Finding 10). restructure_sheets reads
# construction_params from the manifest to build new tabs.
#
# arao1248 has no pair-row classes at all (only ciscategorial, noninterruption,
# subspanrepetition), so these two scoped checks avoid Finding 16 below and
# genuinely confirm _write_tab_with_carryover derives its column positions
# fresh from param_names/rows, never a stale manifest offset.
# ---------------------------------------------------------------------------

def test_nothing_criterion_shaped_is_written_onto_source_or_comments_on_rename(env):
    env.rename_element("arao1248", "sha", "SHA")
    env.run(["--apply", "--lang", "arao1248", "--rename-element", "sha:SHA"])
    assert_no_criterion_writes_onto_trailing_columns(env.doorway)


def test_nothing_criterion_shaped_is_written_onto_trailing_columns_on_split(env):
    env.split_element("arao1248", "sha", ["SHA1", "SHA2"])
    env.run(["--apply", "--lang", "arao1248", "--split-element", "sha:SHA1,SHA2"])
    assert_no_criterion_writes_onto_trailing_columns(env.doorway)


def test_nothing_criterion_shaped_is_written_onto_trailing_columns_on_rename_class(env):
    env.rename_class_in_diagnostics("stan1293", "proform", "proform_renamed")
    env.run(["--apply", "--lang", "stan1293",
            "--rename-class", "proform:proform_renamed"])
    assert_no_criterion_writes_onto_trailing_columns(env.doorway)


# ---------------------------------------------------------------------------
# Finding 16 (docs/data-layer-progress.md), fixed in a follow-up commit right
# after the migration landed, with this test's before/after as the evidence:
# `_copy_pair_tab_with_rename` used to hardcode col_start=4 when re-populating
# a copied pair tab. That was correct for coreference's four-structural-column
# shape (Element_A, Position_A, Position_B, Direction, THEN the criterion) but
# wrong for nonpermutability's and phrasal_accent's "general" construction,
# whose pair shape is only two columns wide (Element_A, Element_B, THEN the
# criterion at column 2) -- so the dropdown landed on Comments (column 4)
# instead of the criterion column, and the criterion column itself got no
# dropdown at all. Confirmed pre-existing (identical on both sides of this
# migration's own before/after comparison) before being fixed, per the
# deferral rule.
# ---------------------------------------------------------------------------

def test_finding_16_pair_tab_dropdown_lands_on_the_criterion_column_not_comments(env):
    env.split_element("stan1293", "her", ["HERACC", "HERDAT"])
    env.run(["--apply", "--lang", "stan1293", "--split-element", "her:HERACC,HERDAT"])

    ss_id = env.sheet_id("stan1293", "nonpermutability")
    ws = env.tab("stan1293", "nonpermutability", "general")
    header = ws.row_values(1)
    assert header == ["Element_A", "Element_B", "scopal", "Source", "Comments"]
    writes = [
        m for m in env.doorway.mutations
        if m.get("op") == "batch_request" and m["request_type"] == "setDataValidation"
        and m.get("spreadsheet") == ss_id
        and m["payload"]["range"]["sheetId"] == ws.id
    ]
    assert writes, "expected a dropdown write on this tab"
    col = writes[0]["payload"]["range"]["startColumnIndex"]
    assert header[col] == "scopal", (
        "the dropdown must land on the criterion column, not Comments "
        "(Finding 16) -- got column {!r}".format(header[col]))
    values = [v["userEnteredValue"]
             for v in writes[0]["payload"]["rule"]["condition"]["values"]]
    assert values == ["y", "n", "both"], "scopal's allowed values, not a guess"


# ---------------------------------------------------------------------------
# Archiving: the old sheet is renamed, moved, and locked; the new one is
# shared with the annotator
# ---------------------------------------------------------------------------

def test_archived_sheet_is_renamed_moved_and_stripped_of_anyone_access(env):
    old_id = env.sheet_id("stan1293", "proform")
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    env.run(["--apply", "--lang", "stan1293",
            "--rename-map", "v:npsubj1:v:npsubj1new"])

    updates = [m for m in env.doorway.mutations_of("update_file") if m["file_id"] == old_id]
    assert any(m["name"] == "proform_stan1293_v2" for m in updates)
    moves = [m for m in env.doorway.mutations_of("move_file") if m["file_id"] == old_id]
    assert moves, "the old sheet must be moved into _archived/"
    perms = env.doorway.list_permissions(old_id)
    assert not any(p["type"] == "anyone" for p in perms), (
        "an archived sheet must not still be world-editable")


def test_new_sheet_is_shared_with_the_annotator_when_one_is_on_file(env):
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    env.run(["--apply", "--lang", "stan1293",
            "--rename-map", "v:npsubj1:v:npsubj1new"])
    new_id = env.sheet_id("stan1293", "proform")
    creates = [m for m in env.doorway.mutations_of("create_permission")
              if m["file_id"] == new_id]
    # Whether stan1293 has an annotator_email on file is a schemas/languages.yaml
    # fact, not this test's business -- assert consistency instead of a fixed
    # count: a "writer" share happens iff the manifest's annotator lookup finds one.
    from coding.generate_sheets import _annotator_email
    email = _annotator_email("stan1293")
    if email:
        assert any(m["role"] == "writer" and m["email"] == email for m in creates)
    else:
        assert not creates


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------

def test_a_second_identical_apply_after_a_real_restructure_archives_nothing_further(env):
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    env.run(["--apply", "--lang", "stan1293",
            "--rename-map", "v:npsubj1:v:npsubj1new"])
    env.doorway.clear_mutations()

    out = env.run(["--apply", "--lang", "stan1293",
                  "--rename-map", "v:npsubj1:v:npsubj1new"])

    assert env.doorway.mutations_of("create_spreadsheet") == []
    assert "(no changes — skipping)" in out


# ---------------------------------------------------------------------------
# The manifest
# ---------------------------------------------------------------------------

def test_manifest_upload_fires_and_local_copy_is_written(env):
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    env.run(["--apply", "--lang", "stan1293",
            "--rename-map", "v:npsubj1:v:npsubj1new"])
    assert [m["file_id"] for m in env.doorway.mutations_of("update_file")
           if m["file_id"] == MANIFEST_FILE_ID]
    assert env.saved_configs
    assert rs.MANIFEST_PATH.exists()


def test_manifest_is_never_touched_by_a_dry_run(env):
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    env.run(["--lang", "stan1293", "--rename-map", "v:npsubj1:v:npsubj1new"])
    assert not any(m["file_id"] == MANIFEST_FILE_ID
                  for m in env.doorway.mutations_of("update_file"))


# ---------------------------------------------------------------------------
# Downstream commands only fire on a real, changed apply
# ---------------------------------------------------------------------------

def test_downstream_commands_fire_after_a_real_apply(env):
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    env.run(["--apply", "--lang", "stan1293",
            "--rename-map", "v:npsubj1:v:npsubj1new"])
    assert env.notebook_calls == [True]
    assert env.revalidate_calls == [{"lang_ids": ["stan1293"]}]
    assert env.push_planar_calls == [{"lang_ids": ["stan1293"], "apply": True}]


# ---------------------------------------------------------------------------
# Interrupted-run recovery (Phase 7 of the data layer redesign, issue #271)
#
# Rather than actually killing the process mid-run (Phase 8's job, with real
# fault injection), these drive the fake doorway directly to the exact Drive
# state an interrupted run would leave, write the matching journal entry by
# hand, and confirm --resume/--rollback/a plain run each do what
# restructure_journal.py's module docstring promises.
# ---------------------------------------------------------------------------

def _archive_ciscategorial(env) -> tuple:
    """Replicate restructure_sheets.py's own archive step (Step 3) by hand,
    for stan1293/ciscategorial, and return (spreadsheet_id, folder_id) --
    the exact detail OLD_SHEET_ARCHIVED's checkpoint stores.
    """
    lang_id, class_name = "stan1293", "ciscategorial"
    manifest = env.manifest()
    sheet_info = manifest[lang_id]["sheets"][class_name]
    folder_id = manifest[lang_id]["folder_url"].rstrip("/").rsplit("/", 1)[-1]
    ss_id = sheet_info["spreadsheet_id"]
    archive_id = env.doorway.get_or_create_folder("_archived", parent_id=folder_id)
    env.doorway.update_file(ss_id, name=f"{class_name}_{lang_id}_v{sheet_info['version']}")
    env.doorway.move_file(ss_id, archive_id)
    rs._lock_archived_sheet(env.doorway, ss_id, lang_id)
    return ss_id, folder_id


def test_plain_run_refuses_to_start_while_a_unit_is_mid_flight(env):
    ss_id, folder_id = _archive_ciscategorial(env)
    rj.record_checkpoint("stan1293", "ciscategorial", rj.OLD_SHEET_ARCHIVED,
                          archived_spreadsheet_id=ss_id, folder_id=folder_id)
    out = env.run(["--apply"])
    assert "[SystemExit:" in out
    assert "stan1293" in out and "ciscategorial" in out
    assert "--resume" in out and "--rollback" in out
    # Nothing else ran -- no other class got touched while this one is stuck.
    assert env.doorway.mutations_of("create_spreadsheet") == []


def test_resume_or_rollback_require_apply(env):
    out = env.run(["--resume"])
    assert "[SystemExit:" in out
    assert "--apply" in out
    out = env.run(["--rollback"])
    assert "[SystemExit:" in out
    assert "--apply" in out


def test_rollback_restores_the_archived_sheet_and_stops(env):
    ss_id, folder_id = _archive_ciscategorial(env)
    rj.record_checkpoint("stan1293", "ciscategorial", rj.OLD_SHEET_ARCHIVED,
                          archived_spreadsheet_id=ss_id, folder_id=folder_id)
    before_manifest = env.manifest()
    out = env.run(["--rollback", "--apply"])

    assert "rolled back" in out
    assert rj.load_journal() == {}
    # Sheet moved back out of _archived/ and renamed back.
    ss = env.doorway.spreadsheet(ss_id)
    assert ss.title == "ciscategorial_stan1293"
    move_calls = [m for m in env.doorway.mutations_of("move_file") if m["file_id"] == ss_id]
    assert move_calls[-1]["to_parent"] == folder_id
    # Nothing else happened: no replacement created, manifest untouched,
    # none of the end-of-run cascade fired.
    assert env.doorway.mutations_of("create_spreadsheet") == []
    assert env.manifest() == before_manifest
    assert env.notebook_calls == []
    assert "DRY RUN" not in out and "Manifest updated on Drive" not in out


def test_rollback_preserves_a_pre_existing_co_annotator_permission(env):
    """_rollback_unit's docstring flagged this as an unverified assumption
    (Phase 7): locking a sheet only ever adds ONE 'user'-type permission
    (the primary annotator's), so rollback deletes every 'user'-type grant
    and re-adds just that one. If the sheet already carried a second
    person's grant before archiving even started (a co-annotator, say),
    rollback must not silently drop it -- Phase 8's job is to check this
    for real rather than leave it as a documented risk.
    """
    lang_id, class_name = "stan1293", "ciscategorial"
    ss_id = env.manifest()[lang_id]["sheets"][class_name]["spreadsheet_id"]
    env.doorway.create_permission(
        ss_id, type="user", role="writer", email="co-annotator@example.test")

    _archive_ciscategorial(env)
    rj.record_checkpoint(lang_id, class_name, rj.OLD_SHEET_ARCHIVED,
                          archived_spreadsheet_id=ss_id, folder_id=None)
    env.run(["--rollback", "--apply"])

    emails = {p.get("emailAddress") for p in env.doorway.list_permissions(ss_id)}
    assert "co-annotator@example.test" in emails


def test_rollback_refuses_when_any_unit_is_past_recreate(env):
    ss_id, folder_id = _archive_ciscategorial(env)
    rj.record_checkpoint("stan1293", "ciscategorial", rj.OLD_SHEET_ARCHIVED,
                          archived_spreadsheet_id=ss_id, folder_id=folder_id)
    rj.record_checkpoint("stan1293", "noninterruption", rj.NEW_SHEET_CREATED,
                          spreadsheet_id="fake_new_id", url="https://example.test/fake",
                          constructions=["general"], construction_params={}, version=3)
    out = env.run(["--rollback", "--apply"])
    assert "[SystemExit:" in out
    assert "--resume instead" in out
    # Refuses outright -- neither unit touched, not even the safe one.
    assert len(rj.load_journal()) == 2
    ss = env.doorway.spreadsheet(ss_id)
    assert ss.title != "ciscategorial_stan1293"  # still archived


def test_resume_finishes_a_new_sheet_created_unit_then_continues(env):
    """--lang restricts the main loop to a different language (arao1248) so
    stan1293/ciscategorial's own resumed pointer is the only thing that can
    change it -- isolating "did resume's bookkeeping stick" from "did the
    main loop separately decide this class needs restructuring anyway",
    which is a real but different question a synthetic, not-fully-populated
    stand-in new sheet would otherwise confound.
    """
    lang_id, class_name = "stan1293", "ciscategorial"
    manifest = env.manifest()
    folder_id = manifest[lang_id]["folder_url"].rstrip("/").rsplit("/", 1)[-1]
    new_ss = env.doorway.create_spreadsheet(f"{class_name}_{lang_id}")
    env.doorway.move_file(new_ss.id, folder_id)
    rj.record_checkpoint(
        lang_id, class_name, rj.NEW_SHEET_CREATED,
        spreadsheet_id=new_ss.id, url=new_ss.url,
        constructions=["general"],
        construction_params=manifest[lang_id]["sheets"][class_name]["construction_params"],
        version=99,
    )
    out = env.run(["--resume", "--apply", "--lang", "arao1248"])

    assert "resumed" in out
    assert rj.load_journal() == {}
    updated = env.manifest()[lang_id]["sheets"][class_name]
    assert updated["spreadsheet_id"] == new_ss.id
    assert updated["version"] == 99
    # Exactly the one spreadsheet this test created itself -- the resume
    # pass didn't also recreate it, and the --lang-filtered main loop never
    # touched stan1293 at all.
    assert len(env.doorway.mutations_of("create_spreadsheet")) == 1
    # The resumed class's manifest fix rides the same end-of-run Drive
    # upload every normal run already does -- confirm it actually fired.
    assert env.saved_configs
    assert "Manifest updated on Drive." in out
    assert env.autocommit_calls, "written TSVs must be committed to coded_data/"


# ---------------------------------------------------------------------------
# Interrupted-run recovery for --rename-class (Phase 7 unit 2, issue #271)
#
# --rename-class's own archive sequence (_rename_class_for_language) shares
# the same two checkpoints and the same journal as the main loop above, keyed
# by the OLD class name with new_class_name carried in the detail. These
# mirror the main-loop recovery tests, checking the rename-specific parts:
# both names appear in reports, an archived-only unit restores under its OLD
# name, and a resumed replacement's manifest key swap (old removed, new
# added) and local TSV directory rename both land.
# ---------------------------------------------------------------------------

def _archive_for_rename(env, lang_id="stan1293", old_class="ciscategorial") -> tuple:
    """Replicate _rename_class_for_language's own archive step by hand."""
    manifest = env.manifest()
    sheet_info = manifest[lang_id]["sheets"][old_class]
    folder_id = manifest[lang_id]["folder_url"].rstrip("/").rsplit("/", 1)[-1]
    ss_id = sheet_info["spreadsheet_id"]
    archive_id = env.doorway.get_or_create_folder("_archived", parent_id=folder_id)
    env.doorway.update_file(ss_id, name=f"{old_class}_{lang_id}_v{sheet_info['version']}")
    env.doorway.move_file(ss_id, archive_id)
    rs._lock_archived_sheet(env.doorway, ss_id, lang_id)
    return ss_id, folder_id


def test_rename_class_stuck_unit_also_blocks_a_plain_run(env):
    ss_id, folder_id = _archive_for_rename(env)
    rj.record_checkpoint("stan1293", "ciscategorial", rj.OLD_SHEET_ARCHIVED,
                          archived_spreadsheet_id=ss_id, folder_id=folder_id,
                          new_class_name="ciscategorial_renamed")
    out = env.run(["--apply"])
    assert "[SystemExit:" in out
    # Both sides of the rename are named, not just the (old) journal key.
    assert "ciscategorial -> ciscategorial_renamed" in out
    assert env.doorway.mutations_of("create_spreadsheet") == []


def test_rename_class_rollback_restores_the_old_name_and_stops(env):
    ss_id, folder_id = _archive_for_rename(env)
    rj.record_checkpoint("stan1293", "ciscategorial", rj.OLD_SHEET_ARCHIVED,
                          archived_spreadsheet_id=ss_id, folder_id=folder_id,
                          new_class_name="ciscategorial_renamed")
    before_manifest = env.manifest()
    out = env.run(["--rollback", "--apply"])

    assert "rolled back" in out
    assert rj.load_journal() == {}
    ss = env.doorway.spreadsheet(ss_id)
    assert ss.title == "ciscategorial_stan1293"  # back under the OLD name
    assert env.doorway.mutations_of("create_spreadsheet") == []
    assert env.manifest() == before_manifest  # never touched -- rename never wrote it


def test_rename_class_resume_finishes_manifest_swap_and_local_dir_rename(env):
    lang_id, old_class, new_class = "stan1293", "ciscategorial", "ciscategorial_renamed"
    manifest = env.manifest()
    folder_id = manifest[lang_id]["folder_url"].rstrip("/").rsplit("/", 1)[-1]

    old_dir = env.coded / lang_id / old_class
    old_dir.mkdir(parents=True)
    (old_dir / "general.tsv").write_text("Element\tPosition_Name\n", encoding="utf-8")

    new_ss = env.doorway.create_spreadsheet(f"{new_class}_{lang_id}")
    env.doorway.move_file(new_ss.id, folder_id)
    rj.record_checkpoint(
        lang_id, old_class, rj.NEW_SHEET_CREATED,
        spreadsheet_id=new_ss.id, url=new_ss.url,
        constructions=["general"],
        construction_params=manifest[lang_id]["sheets"][old_class]["construction_params"],
        version=99, new_class_name=new_class,
    )
    out = env.run(["--resume", "--apply", "--lang", "arao1248"])

    assert "resumed" in out
    assert rj.load_journal() == {}
    updated_manifest = env.manifest()
    assert old_class not in updated_manifest[lang_id]["sheets"]
    new_entry = updated_manifest[lang_id]["sheets"][new_class]
    assert new_entry["spreadsheet_id"] == new_ss.id
    assert new_entry["version"] == 99
    assert not old_dir.exists()
    assert (env.coded / lang_id / new_class / "general.tsv").exists()


def test_rename_class_rollback_refuses_when_past_recreate(env):
    ss_id, folder_id = _archive_for_rename(env)
    rj.record_checkpoint("stan1293", "ciscategorial", rj.NEW_SHEET_CREATED,
                          spreadsheet_id="fake_new_id", url="https://example.test/fake",
                          constructions=["general"], construction_params={}, version=3,
                          new_class_name="ciscategorial_renamed")
    out = env.run(["--rollback", "--apply"])
    assert "[SystemExit:" in out
    assert "ciscategorial -> ciscategorial_renamed" in out
    assert "--resume instead" in out
    assert len(rj.load_journal()) == 1


# ---------------------------------------------------------------------------
# Fault injection (Phase 8 of the data layer redesign, issue #271) — proving
# the recovery above survives an actual crash mid-sequence, not just a
# hand-set journal entry the way every test above sets its scenario up.
# `env.doorway.fail_after(op, count)` raises on the Nth call to a doorway
# method, after that call's in-memory effect already landed (mirroring a
# Drive write that succeeded server-side right before the process died) --
# see fake_drive.py's own docstring on the hook for the full reasoning.
# ---------------------------------------------------------------------------

def test_real_crash_between_archive_and_create_then_resume_recovers(env):
    """A network failure right after archiving succeeds, before the
    replacement sheet is created -- the actual #248 shape, injected for
    real via the fake doorway rather than hand-seeded the way every test
    above this one sets its starting state up.
    """
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")
    env.doorway.fail_after("create_spreadsheet", 1)
    with pytest.raises(RuntimeError, match="simulated crash"):
        env.run(["--apply", "--lang", "stan1293",
                 "--rename-map", "v:npsubj1:v:npsubj1new"])

    journal = rj.load_journal()
    assert len(journal) == 1
    entry = next(iter(journal.values()))
    assert entry["checkpoint"] == rj.OLD_SHEET_ARCHIVED
    stuck_lang, stuck_class = entry["lang_id"], entry["class_name"]

    # A plain re-run refuses to touch anything else while it's stuck.
    env.doorway.clear_faults()
    out = env.run(["--apply", "--lang", "stan1293",
                   "--rename-map", "v:npsubj1:v:npsubj1new"])
    assert "[SystemExit:" in out
    assert stuck_class in out

    # --resume rolls the interrupted class back (nothing of value existed
    # past the archive) and the SAME run redoes it for real -- not a
    # hand-driven finish, the ordinary per-class loop running to completion.
    out = env.run(["--resume", "--apply", "--lang", "stan1293",
                   "--rename-map", "v:npsubj1:v:npsubj1new"])
    assert rj.load_journal() == {}
    assert f"Archived to _archived/{stuck_class}_{stuck_lang}" in out
    assert "New sheet (v" in out
    live_id = env.manifest()[stuck_lang]["sheets"][stuck_class]["spreadsheet_id"]
    assert env.doorway.spreadsheet(live_id).title == f"{stuck_class}_{stuck_lang}"


def test_real_crash_before_final_manifest_upload_then_resume_recovers(env, monkeypatch):
    """A network failure after the replacement sheet is fully created and
    populated, but before the run's closing Drive manifest upload -- the
    class exists live but is invisible to every other command until that
    upload lands.

    Injected by making the real upload_manifest call raise once, not via
    fail_after on a doorway op: _upload_manifest_with (coding/drive.py)
    catches a failed doorway.update_file itself and falls back to creating
    a fresh manifest file, so a doorway-level fault here self-heals inside
    upload_manifest rather than propagating as a crash. A genuine "the
    whole run dies here" failure needs to be simulated one level up, at the
    call restructure_sheets.py itself makes.
    """
    env.rename_position("stan1293", "v:npsubj1", "v:npsubj1new")

    real_upload_manifest = rs.upload_manifest
    calls = {"n": 0}

    def _flaky_upload_manifest(*a, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated crash during manifest upload")
        return real_upload_manifest(*a, **kw)

    monkeypatch.setattr(rs, "upload_manifest", _flaky_upload_manifest)
    with pytest.raises(RuntimeError, match="simulated crash"):
        env.run(["--apply", "--lang", "stan1293",
                 "--rename-map", "v:npsubj1:v:npsubj1new"])

    journal = rj.load_journal()
    assert journal  # at least one class reached NEW_SHEET_CREATED before the crash
    assert all(e["checkpoint"] == rj.NEW_SHEET_CREATED for e in journal.values())
    stuck = [(e["lang_id"], e["class_name"]) for e in journal.values()]

    monkeypatch.setattr(rs, "upload_manifest", real_upload_manifest)
    out = env.run(["--resume", "--apply", "--lang", "stan1293",
                   "--rename-map", "v:npsubj1:v:npsubj1new"])
    assert rj.load_journal() == {}
    assert "Manifest updated on Drive." in out
    for lang_id, class_name in stuck:
        assert class_name in env.manifest()[lang_id]["sheets"]
