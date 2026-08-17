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
    assert env.autocommit_calls, "written TSVs must be committed to coded_data/"
