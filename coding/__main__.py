"""Command-line interface for the coding workflow tools.

Usage:
    python -m coding <command> [options]

Run `python -m coding registry` for the full, always-current list of
commands with a one-line description of each -- derived fresh from this
file's _COMMANDS table, every command's own argparse flags, and
data_dependency_schema/operations.yaml, rather than restated here where it
would inevitably drift (Phase 5 unit C, issue #271). Add `--command NAME`
to that for one command's full detail: flags, side effects, idempotency,
preconditions and modes. Use --help on any
individual command for just its flags, or see CLAUDE.md.

How a command is run. Every command module exposes
``build_parser() -> argparse.ArgumentParser`` and
``main(args: argparse.Namespace | None = None)``; ``main()`` parses
``sys.argv`` itself only when called with no ``args``, so a test can still set
``sys.argv`` and call ``mod.main()``. ``dispatch(cmd, argv)`` (also called by
daily_refresh.py once per step) builds the parser, parses once, calls
``preconditions.enforce(op_id, args)``, then runs ``mod.main(args)`` inside
``drive_door.running(cmd, args)``. That is the one place both doors learn which
command is running (so each can say whether this invocation may write); when
the command ends, however it ends, the Drive door logs what it wrote
(provenance.py) and the local-file door commits and pushes every file it wrote
in planars-data, state files included (file_door.py).

Two commands keep hand-written colon/comma flag readers that still look at
``sys.argv`` for their values: restructure_sheets.py and sync_params.py (their
``build_parser()`` exists for ``--help`` and for catching unknown flags).
check_codebook.py and setup_root_folder.py take no flags, so their parsers are
empty.
"""
import sys

_COMMANDS = {
    "capture-drive-state":         "coding.capture_drive_state",
    "generate-sheets":             "coding.generate_sheets",
    "generate-notebooks":          "coding.generate_notebooks",
    "generate-reports":            "coding.generate_reports",
    "laminar-charts":              "coding.laminar_charts",
    # The chapters package's one writer, run here so its writes go through
    # the local-file door (docs/chapter-generation-plan.md, Phase 3).
    "build-chapters":              "chapters.build",
    "sync-params":                 "coding.sync_params",
    "sync-diagnostics-yaml":       "coding.sync_diagnostics_yaml",
    "sync-span-rule-hashes":       "coding.sync_span_rule_hashes",
    "update-sheets":               "coding.update_sheets",
    "import-sheets":               "coding.import_sheets",
    "validate-coding":             "coding.validate_coding",
    "validation-report":           "coding.validation_report",
    "restructure-sheets":          "coding.restructure_sheets",
    "check-codebook":              "coding.check_codebook",
    "generate-rule-update-prompt": "coding.generate_rule_update_prompt",
    "integrity-check":             "coding.integrity_check",
    "setup-root-folder":           "coding.setup_root_folder",
    "lookup-lang":                 "coding.glottolog",
    "prune-manifest":              "coding.prune_manifest",
    "rename-construction":         "coding.rename_construction",
    "check-notes":                 "coding.check_notes",
    "check-comments":              "coding.check_comments",
    "refresh-dropdowns":           "coding.refresh_dropdowns",
    "sync-planar":                 "coding.sync_planar",
    "generate-status-sheet":       "coding.generate_status_sheet",
    "proposal-sheets":             "coding.proposal_sheets",
    "accept-proposal":             "coding.accept_proposal",
    "registry":                    "coding.registry",
    "issue":                       "coding.issues",
    "daily-refresh":               "coding.daily_refresh",
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in _COMMANDS:
        print(f"Unknown command: {cmd!r}")
        print(f"Available commands: {', '.join(sorted(_COMMANDS))}")
        sys.exit(1)

    dispatch(cmd, sys.argv[2:])


def dispatch(cmd: str, argv: list) -> None:
    """Run one command with its own flags, the one way every command runs:
    from the command line (main above) and from daily-refresh, which calls
    this once per step."""
    # The module's own parser -- and, for restructure_sheets.py/sync_params.py,
    # their hand-rolled colon/comma helpers that read sys.argv directly --
    # see only its own flags.
    saved, sys.argv = sys.argv, [sys.argv[0] if sys.argv else "coding"] + list(argv)
    try:
        import importlib
        mod = importlib.import_module(_COMMANDS[cmd])
        args = mod.build_parser().parse_args()
        # Parsed once, here, rather than inside mod.main() -- this is the
        # dispatch chokepoint precondition enforcement and the Drive door hook
        # into, keyed by `cmd` and `args`.
        op_id = cmd.replace("-", "_")
        from . import preconditions
        preconditions.enforce(op_id, args)
        # Both doors learn which command is running here, so they know
        # whether this invocation may write (docs/drive-door-design.md § 2.2).
        # When it ends, however it ends, the Drive door logs what it wrote
        # (coding/provenance.py) and the local-file door commits and pushes
        # every file it wrote in planars-data (coding/file_door.py).
        from . import drive_door
        with drive_door.running(cmd, args):
            mod.main(args)
    finally:
        sys.argv = saved


if __name__ == "__main__":
    main()
