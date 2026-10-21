"""Every file write in coding/ goes through the local-file door, or is listed.

The local twin of tests/test_doorway_coverage.py (Phase 10 unit 6a; design
docs/ownership-design.md § 4.1). It reads every module under coding/ except
the door itself and finds each call that writes, moves or deletes a file
(write_text, to_csv to a path, open for writing, json/yaml dump to a file,
shutil copy/move/rmtree, unlink, rename, rmdir). Each one must be in
``NOT_THROUGH_THE_DOOR`` with the reason it is not the door's: a file outside
planars-data, or test data (since unit 6b the state files and the ID file go
through the door too). A new write anywhere else fails here, so it goes
through the door instead; a listed write that no longer exists fails too,
so the list can't go stale.

A site is (module, enclosing function, what is called), not a line number,
so an unrelated edit doesn't break this test.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
CODING = ROOT / "coding"

Site = Tuple[str, str, str]   # (module, enclosing function, call)

_METHODS = {"write_text", "write_bytes", "unlink", "rename", "replace", "rmdir", "touch"}
_SHUTIL = {"copy", "copy2", "copyfile", "copytree", "move", "rmtree"}
_OS = {"remove", "rename", "replace", "unlink", "rmdir"}

# The writes that are not planars-data's at all, and its test data.
_ROOT_MANIFEST = ("not in planars-data: sheets_manifest.json (and manifest_backup.json) "
                  "at the repo root, deleted in unit 11c")
NOT_THROUGH_THE_DOOR: Dict[Site, str] = {
    # Test data: capture-drive-state is its one writer (ownership-design § 4.4).
    ("capture_drive_state.py", "main", "shutil.copytree"): "test data under .test_fixtures/",
    ("capture_drive_state.py", "main", "shutil.rmtree"): "test data under .test_fixtures/",
    ("capture_drive_state.py", "main", "unlink"): "test data under .test_fixtures/",
    ("capture_drive_state.py", "main", "write_text"): "test data under .test_fixtures/",
    # Not planars-data at all.
    ("generate_sheets.py", "main", "write_text"): _ROOT_MANIFEST,
    ("generate_status_sheet.py", "main", "write_text"): _ROOT_MANIFEST,
    ("restructure_sheets.py", "main", "write_text"): _ROOT_MANIFEST,
    ("prune_manifest.py", "_archive_manifest", "write_text"):
        "not in planars-data: manifest_archives/ at the repo root (gitignored)",
    ("import_planar.py", "import_planar", "write_text"):
        "not in planars-data: PLANAR_CHANGES_PATH in /tmp, for the daily refresh's issue",
    ("daily_refresh.py", "import_planar", "unlink"): "not in planars-data: PLANAR_CHANGES_PATH",
    ("import_sheets.py", "main", "write_text"):
        "not in planars-data: diagnostics_drift.json at the repo root",
    ("daily_refresh.py", "import_sheets", "unlink"): "not in planars-data: diagnostics_drift.json",
    ("sync_diagnostics_yaml.py", "main", "write_text"):
        "not in planars-data: diagnostics_drift.json at the repo root",
    ("import_sheets.py", "_write_error_report", "write_text"):
        "not in planars-data: import_errors/ at the repo root",
    ("daily_refresh.py", "summary", "open"): "not in planars-data: the Actions run's summary page",
    ("glottolog.py", "_save_cache", "open"): "not in planars-data: glottolog_cache.json",
    ("glottolog.py", "_save_cache", "json.dump"): "not in planars-data: glottolog_cache.json",
    ("glottolog.py", "_update_languages_yaml", "open"):
        "not in planars-data: schemas/languages.yaml (schema hand edits: unit 17)",
    ("glottolog.py", "_update_languages_yaml", "yaml.dump"):
        "not in planars-data: schemas/languages.yaml (schema hand edits: unit 17)",
    ("sync_qualification_hashes.py", "_apply_hashes", "write_text"):
        "not in planars-data: schemas/diagnostic_classes_status.yaml",
    ("issues.py", "_run", "unlink"): "not in planars-data: a temporary issue-body file",
    ("issues.py", "main", "write_text"): "not in planars-data: CLAUDE.md's Labels table",
    ("validation_report.py", "main", "write_text"):
        "not in planars-data: the issue body file the workflow asked for (--out)",
}


def _call_name(node: ast.Call) -> str:
    """What a call writes with, or "" if it is not a write."""
    f = node.func
    if isinstance(f, ast.Name) and f.id == "open":
        mode = node.args[1] if len(node.args) > 1 else next(
            (k.value for k in node.keywords if k.arg == "mode"), None)
        if isinstance(mode, ast.Constant) and any(c in str(mode.value) for c in "wax"):
            return "open"
        return ""
    if not isinstance(f, ast.Attribute):
        return ""
    if f.attr == "open":      # path.open("w")
        mode = node.args[0] if node.args else next(
            (k.value for k in node.keywords if k.arg == "mode"), None)
        if isinstance(mode, ast.Constant) and any(c in str(mode.value) for c in "wax"):
            return "open"
        return ""
    base = f.value.id if isinstance(f.value, ast.Name) else ""
    if base == "shutil" and f.attr in _SHUTIL:
        return f"shutil.{f.attr}"
    if base == "os" and f.attr in _OS:
        return f"os.{f.attr}"
    if f.attr in ("dump",) and base in ("json", "yaml", "_yaml") and len(node.args) > 1:
        return f"{base}.dump"
    if f.attr == "to_csv" and (node.args or any(k.arg == "path_or_buf" for k in node.keywords)):
        return "to_csv"
    if f.attr in _METHODS:
        # str.replace takes two arguments, dataclasses.replace and a table's
        # rename keywords; a path's replace or rename takes exactly one, the
        # target.
        if f.attr in ("replace", "rename") and (len(node.args) != 1 or base == "dataclasses"):
            return ""
        return f.attr
    return ""


def _write_sites() -> Set[Site]:
    sites: Set[Site] = set()
    for path in sorted(CODING.glob("*.py")):
        if path.name == "file_door.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))

        def visit(node, func: str) -> None:
            for child in ast.iter_child_nodes(node):
                name = func
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    name = child.name
                if isinstance(child, ast.Call):
                    call = _call_name(child)
                    if call:
                        sites.add((path.name, func, call))
                visit(child, name)

        visit(tree, "<module>")
    return sites


def test_every_write_goes_through_the_door_or_is_listed():
    found = _write_sites()
    unlisted = sorted(found - set(NOT_THROUGH_THE_DOOR))
    assert not unlisted, (
        "These write files without going through the local-file door "
        "(coding/file_door.py). Write through the door, or, for a file outside "
        "planars-data, list it in NOT_THROUGH_THE_DOOR with the reason:\n  "
        + "\n  ".join(map(str, unlisted)))


def test_the_list_has_no_write_that_is_gone():
    stale = sorted(set(NOT_THROUGH_THE_DOOR) - _write_sites())
    assert not stale, ("NOT_THROUGH_THE_DOOR lists writes that no longer exist; "
                       "delete them:\n  " + "\n  ".join(map(str, stale)))
