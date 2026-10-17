"""Nothing kept that no starting point reaches.

Phase 10 unit 19 (issue #271). `python -m planars` was broken from March to
October with nothing using it, and snapshots of retired classes sat in
tests/snapshots/ for weeks: code nobody runs still gets read, maintained and
trusted. This test fails when a file in coding/ or planars/ can be reached
from none of the project's starting points:

- the `python -m coding` dispatcher and every command module it names
  (read from `coding.__main__._COMMANDS`, so a new command counts at once);
- every Python script at the repo root (generate_snapshots.py, the
  pre-commit hooks, render_codebook.py, ...), which the workflows,
  .pre-commit-config.yaml, the Makefile and the docs run;
- the code cells of the Colab notebook templates (notebooks/templates/),
  which generate-notebooks turns into every language's notebooks;
- NonCollaborative/scripts/, Jeff's own analysis code, which imports the
  library and is run by hand.

The workflows and the Makefile need no entry of their own: everything they
run is `python -m coding ...` or a root script. The reports' list of
analyses (`planars.reports._CLASS_HANDLERS`) imports each analysis module
directly, so it is followed like any other import.

Reached means imported, directly or through other files, anywhere in a
file — including inside a function. Being imported only by tests does not
count: a file only tests use is a file nothing uses. Imports that loop over
every file in planars/ (check-codebook, validate_diagnostics) are not
followed, since they would make everything look reached.

A file that is unreachable on purpose goes in KEPT with the reason. Keep that
list short: each entry is a hidden fact someone must re-check.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Dict, Iterator, Set

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ("coding", "planars")

# file (repo-relative) -> why nothing reaches it and it stays anyway.
KEPT: Dict[str, str] = {}


def _module_files() -> Dict[str, Path]:
    """Every importable module in the checked packages, by dotted name."""
    mods = {}
    for pkg in PACKAGES:
        for path in sorted((ROOT / pkg).rglob("*.py")):
            rel = path.relative_to(ROOT).with_suffix("")
            parts = list(rel.parts)
            if parts[-1] == "__init__":
                parts = parts[:-1]
            mods[".".join(parts)] = path
    return mods


def _imported_names(tree: ast.AST, current: str, is_package: bool) -> Iterator[str]:
    """Dotted names a parsed file imports, each candidate a module or package.

    `from a.b import c` yields both `a.b` and `a.b.c`: c may be a submodule.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = current.split(".")
                if not is_package:
                    base = base[:-1]
                base = base[: len(base) - (node.level - 1)]
                prefix = ".".join(base + ([node.module] if node.module else []))
            else:
                prefix = node.module or ""
            yield prefix
            for alias in node.names:
                yield f"{prefix}.{alias.name}"


def _with_parents(name: str) -> Iterator[str]:
    """Importing a.b.c runs a/__init__ and a/b/__init__ too."""
    parts = name.split(".")
    for i in range(1, len(parts) + 1):
        yield ".".join(parts[:i])


def _notebook_code(path: Path) -> str:
    """A notebook's code cells, minus the shell and magic lines."""
    nb = json.loads(path.read_text(encoding="utf-8"))
    lines = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        src = "".join(src) if isinstance(src, list) else src
        lines += [ln for ln in src.splitlines() if not ln.lstrip().startswith(("!", "%"))]
    return "\n".join(lines)


def _starting_trees() -> Iterator[ast.AST]:
    """Parsed code of every starting point outside the packages."""
    for path in sorted(ROOT.glob("*.py")):
        yield ast.parse(path.read_text(encoding="utf-8"))
    for path in sorted((ROOT / "notebooks" / "templates").glob("*.ipynb")):
        yield ast.parse(_notebook_code(path))
    for path in sorted((ROOT / "NonCollaborative" / "scripts").rglob("*.py")):
        try:
            yield ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue  # superseded scratch kept behind a run guard


def reached_modules() -> Set[str]:
    """Every module in coding/ and planars/ some starting point reaches."""
    from coding.__main__ import _COMMANDS

    mods = _module_files()
    todo = ["coding.__main__", *_COMMANDS.values()]
    for tree in _starting_trees():
        todo += list(_imported_names(tree, "", False))

    reached: Set[str] = set()
    while todo:
        name = todo.pop()
        for candidate in _with_parents(name):
            if candidate not in mods or candidate in reached:
                continue
            reached.add(candidate)
            path = mods[candidate]
            tree = ast.parse(path.read_text(encoding="utf-8"))
            todo += list(_imported_names(tree, candidate, path.name == "__init__.py"))
    return reached


def unreached_files() -> Dict[str, Path]:
    reached = reached_modules()
    return {
        str(path.relative_to(ROOT)): path
        for name, path in _module_files().items()
        if name not in reached
    }


def test_every_library_and_tooling_file_is_reached_from_a_starting_point():
    unreached = sorted(set(unreached_files()) - set(KEPT))
    assert not unreached, (
        "These files are run by no command, root script, notebook template or "
        "NonCollaborative script — only (at most) by tests:\n  "
        + "\n  ".join(unreached)
        + "\nDelete them (and their tests), or, if one must stay, add it to KEPT "
        "in tests/test_no_leftovers.py with the reason."
    )


def test_kept_files_still_exist_and_are_still_unreached():
    unreached = set(unreached_files())
    stale = sorted(f for f in KEPT if f not in unreached)
    assert not stale, (
        "These KEPT entries are now reached or gone; remove them from KEPT: "
        + ", ".join(stale)
    )
