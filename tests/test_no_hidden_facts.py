"""Detectors for hidden facts — values or commands typed where they should be read.

Phase 10 unit 7 (issue #271). The hidden-facts inventory went stale because
it was a hand search; these checks take their lists from the schemas and the
real command parsers, so they keep working as both grow, with nothing to
maintain by hand.

1. Literal detector: no string in coding/, planars/, generate_snapshots.py or
   the notebook templates' code may equal a value schemas/planar.yaml owns —
   the keystone's name, the Status tab's values, the locked tabs' titles.
   Read them from planars/schema_values.py or coding/locked_tabs.py instead. Deliberately narrow to start (2026-10-12):
   many schema values are ordinary words ("general", "free", "y"), and a noisy
   check breeds exceptions, which become a new hidden list. Widen it only
   where a hit has proven real.
2. Command-string detector: every `python -m coding <command> --flag ...`
   written anywhere a person or Claude will read it (code, docs, workflows,
   schemas, NextPrompt) names a real command, and every --flag in it is one
   that command's own parser accepts. Catches the drift where sync_params
   told readers to run `import-sheets --force` for months.

3. Row-shape detector: no list, set or tuple literal may restate two or more
   columns the schemas declare together (a tab's row columns, the trailing
   columns, the Status tab's columns). See test_no_row_shape_is_restated_in_code.

None of them can see behaviour facts (who keeps what current); the doorway
work in Phase 10 handles those.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Iterator, List, Tuple

from planars import schema_values

ROOT = Path(__file__).resolve().parent.parent

OWNED_VALUES = {
    schema_values.KEYSTONE_NAME: "planars.schema_values.KEYSTONE_NAME (or is_keystone)",
    schema_values.STATUS_IN_PROGRESS: "planars.schema_values.STATUS_IN_PROGRESS",
    schema_values.STATUS_READY: "planars.schema_values.STATUS_READY",
}
# The locked tabs' titles (schemas/planar.yaml locked_tabs, Phase 10 unit 2).
from coding.locked_tabs import locked_tab_titles  # noqa: E402
OWNED_VALUES.update({t: "coding.locked_tabs.locked_tab_titles() / system_tab_titles()"
                     for t in locked_tab_titles()})


def _python_sources() -> Iterator[Tuple[str, str]]:
    for base in ("coding", "planars"):
        for path in sorted((ROOT / base).glob("*.py")):
            yield str(path.relative_to(ROOT)), path.read_text(encoding="utf-8")
    yield "generate_snapshots.py", (ROOT / "generate_snapshots.py").read_text(encoding="utf-8")
    for nb in sorted((ROOT / "notebooks" / "templates").glob("*.ipynb")):
        cells = json.loads(nb.read_text(encoding="utf-8")).get("cells", [])
        for i, cell in enumerate(cells):
            if cell.get("cell_type") != "code":
                continue
            src = "".join(cell.get("source", []))
            # Notebook-only syntax (!pip, %magic) isn't Python; drop those lines.
            src = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith(("!", "%")))
            yield f"{nb.relative_to(ROOT)} cell {i}", src


def _docstring_ids(tree: ast.AST) -> set:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
    return ids


def test_no_schema_owned_value_is_typed_into_code():
    hits: List[str] = []
    for where, src in _python_sources():
        if where == "planars/schema_values.py":
            continue
        tree = ast.parse(src)
        skip = _docstring_ids(tree)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in skip and node.value in OWNED_VALUES):
                hits.append(f"{where}:{node.lineno}: {node.value!r} → use "
                            f"{OWNED_VALUES[node.value]}")
    assert not hits, (
        "These strings repeat a value schemas/planar.yaml owns. Read it instead "
        "(the schema is the one place it may change):\n  " + "\n  ".join(hits))


def _declared_column_groups() -> List[Tuple[str, frozenset]]:
    """Each group of columns the schemas declare together, with where to read it."""
    from coding.schemas import load_diagnostic_classes
    groups = [
        ("planars.schema_values.ELEMENT_ROW_COLUMNS (or row_columns)",
         frozenset(schema_values.ELEMENT_ROW_COLUMNS)),
        ("planars.schema_values.TRAILING_COLUMNS", frozenset(schema_values.TRAILING_COLUMNS)),
        ("planars.schema_values.STATUS_COLUMNS", frozenset(schema_values.STATUS_COLUMNS)),
    ]
    groups += [(f"planars.schema_values.PAIR_ROW_SHAPES[{name!r}] (or row_columns/row_key)",
                frozenset(cols)) for name, cols in schema_values.PAIR_ROW_SHAPES.items()]
    for cls in load_diagnostic_classes().get("classes", []):
        for con in cls.get("constructions") or []:
            if isinstance(con, dict) and con.get("keyed_columns"):
                groups.append((f"planars.schema_values.row_columns({cls['name']!r}, "
                               f"{con['name']!r}) / row_key", frozenset(con["keyed_columns"])))
    return groups


def test_no_row_shape_is_restated_in_code():
    """3. Row-shape detector: a list, set or tuple literal holding two or more
    columns of one declared shape (element rows, a pair shape, a keyed tab's
    columns, the trailing columns, the Status tab's columns) is a copy of that
    shape (hidden-facts D3, D4). Reading one column by name
    (row["Position_B"]) is not, and is not flagged."""
    groups = _declared_column_groups()
    hits: List[str] = []
    for where, src in _python_sources():
        if where == "planars/schema_values.py":
            continue
        for node in ast.walk(ast.parse(src)):
            if not isinstance(node, (ast.List, ast.Set, ast.Tuple)):
                continue
            strings = {e.value for e in node.elts
                       if isinstance(e, ast.Constant) and isinstance(e.value, str)}
            for read_from, cols in groups:
                if len(strings & cols) >= 2:
                    hits.append(f"{where}:{node.lineno}: {sorted(strings & cols)} → use {read_from}")
                    break
    assert not hits, (
        "These literals restate columns the schemas declare together. Read them "
        "instead:\n  " + "\n  ".join(hits))


_COMMAND_STRING = re.compile(r"python -m coding ([a-z][a-z0-9-]*)((?:[ \t]+[^\s`'\"|;)]+)*)")


def _text_sources() -> Iterator[Tuple[str, str]]:
    patterns = ["coding/*.py", "planars/*.py", "*.md", "docs/*.md", ".github/workflows/*.yml",
                ".github/scripts/*", "schemas/*.yaml", "data_dependency_schema/*.yaml",
                "migrations/*.py"]
    seen = set()
    for pattern in patterns:
        for path in sorted(ROOT.glob(pattern)):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            yield str(path.relative_to(ROOT)), path.read_text(encoding="utf-8")


def _known_flags(module_name: str) -> set:
    import importlib
    parser = importlib.import_module(module_name).build_parser()
    return {opt for action in parser._actions for opt in action.option_strings}


def test_every_written_command_and_flag_exists():
    from coding.__main__ import _COMMANDS
    flags_by_command = {cmd: _known_flags(mod) for cmd, mod in _COMMANDS.items()}
    problems: List[str] = []
    for where, text in _text_sources():
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in _COMMAND_STRING.finditer(line):
                command, rest = m.group(1), m.group(2)
                if command not in flags_by_command:
                    problems.append(f"{where}:{lineno}: no command {command!r}")
                    continue
                for token in rest.split():
                    flag = token.split("=", 1)[0].rstrip(".,:")
                    if (flag.startswith("--") and flag not in flags_by_command[command]
                            and re.fullmatch(r"--[a-z][a-z0-9-]*", flag)):
                        problems.append(f"{where}:{lineno}: {command} has no flag {flag}")
    assert not problems, (
        "These written commands would fail if someone ran them — fix the text "
        "(or the command):\n  " + "\n  ".join(problems))
