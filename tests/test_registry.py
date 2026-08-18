"""Tests for `python -m coding registry` (Phase 5 unit C, issue #271).

The point of this command is that its output can never go stale -- it is
recomputed from live sources on every call, not hand-maintained. These tests
check that claim directly: every command in coding/__main__.py's _COMMANDS
table appears, and a couple of known commands' flag lists are checked
against a fresh, independent call to that module's own build_parser()
(not against a copy pinned in this file), so a hand-copied flag list
couldn't pass silently.
"""
from __future__ import annotations

import io
from contextlib import redirect_stdout

import pytest

from coding import registry
from coding.__main__ import _COMMANDS


def test_every_command_appears_in_the_registry():
    entries = registry.build_registry()
    seen = {e["cli_command"] for e in entries}
    assert seen == set(_COMMANDS)


def test_every_command_has_an_operations_yaml_record():
    # A gap here would mean build_registry() silently degraded to
    # "[no operations.yaml record]" for a real command -- registry itself
    # was exactly this gap until its own record was added.
    entries = registry.build_registry()
    missing = [e["cli_command"] for e in entries if e["operation"] is None]
    assert missing == []


@pytest.mark.parametrize("cli_command", [
    "import-planar",      # already used argparse before Phase 5 unit A
    "generate-sheets",    # largest file, plain argparse.Namespace throughout
    "restructure-sheets", # hand-rolled colon/comma parsers under argparse
    "check-codebook",     # no flags at all
])
def test_flags_match_a_fresh_call_to_the_module_s_own_build_parser(cli_command):
    import importlib
    mod = importlib.import_module(_COMMANDS[cli_command])
    expected = registry._flags_from_parser(mod.build_parser())

    entries = registry.build_registry()
    entry = next(e for e in entries if e["cli_command"] == cli_command)
    assert entry["flags"] == expected


def test_summary_output_lists_every_command():
    buf = io.StringIO()
    with redirect_stdout(buf):
        registry.main(registry.build_parser().parse_args([]))
    out = buf.getvalue()
    for cli_command in _COMMANDS:
        assert cli_command in out


def test_command_detail_shows_flags_and_operation_fields():
    buf = io.StringIO()
    with redirect_stdout(buf):
        registry.main(registry.build_parser().parse_args(["--command", "generate-sheets"]))
    out = buf.getvalue()
    assert "--apply" in out
    assert "--regen-construction" in out
    assert "Idempotent: False" in out
    assert "Apply gate: --apply" in out


def test_unknown_command_is_a_clear_error():
    with pytest.raises(SystemExit, match="Unknown command 'not-a-real-command'"):
        registry.main(registry.build_parser().parse_args(["--command", "not-a-real-command"]))


def test_unknown_flag_hard_errors():
    with pytest.raises(SystemExit):
        registry.build_parser().parse_args(["--bogus-flag"])


def test_a_second_call_in_the_same_process_reflects_a_changed_operations_yaml(tmp_path):
    """Idempotency (Phase 8 of the data layer redesign, issue #271) --
    every claim in this module and its own docstrings is "recomputed fresh
    every call, nothing cached." Found a real violation this way:
    `_load_operations()` cached the parsed file in a module-level global
    after its first read, so a second `build_registry()` call in the same
    process silently returned stale data -- harmless for the ordinary CLI
    invocation (a fresh process every time), but a real gap for anything
    importing this module and calling it more than once, which a test
    suite does constantly. Fixed by removing the cache; this test proves
    the fix by writing a real operations.yaml, calling build_registry()
    twice, changing the file in between, and confirming the second call
    picks up the change.
    """
    ops_path = tmp_path / "operations.yaml"
    ops_path.write_text(
        "- id: check_codebook\n  description: original description\n",
        encoding="utf-8",
    )
    original = registry.OPERATIONS_PATH
    registry.OPERATIONS_PATH = ops_path
    try:
        first = registry.build_registry()
        check_codebook = next(e for e in first if e["cli_command"] == "check-codebook")
        assert check_codebook["operation"]["description"] == "original description"

        ops_path.write_text(
            "- id: check_codebook\n  description: changed description\n",
            encoding="utf-8",
        )
        second = registry.build_registry()
        check_codebook = next(e for e in second if e["cli_command"] == "check-codebook")
        assert check_codebook["operation"]["description"] == "changed description"
    finally:
        registry.OPERATIONS_PATH = original
