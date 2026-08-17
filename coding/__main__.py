"""Command-line interface for the coding workflow tools.

Usage:
    python -m coding <command> [options]

Run `python -m coding registry` for the full, always-current list of
commands with a one-line description of each -- derived fresh from this
file's _COMMANDS table, every command's own argparse flags, and
data_dependency_schema/operations.yaml, rather than restated here where it
would inevitably drift (Phase 5 unit C, issue #271). Add `--command NAME`
to that for one command's full detail: flags, side effects, idempotency,
preconditions, and ordering relative to other commands. Use --help on any
individual command for just its flags, or see CLAUDE.md.
"""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

_COMMANDS = {
    "capture-drive-state":         "coding.capture_drive_state",
    "generate-sheets":             "coding.generate_sheets",
    "generate-notebooks":          "coding.generate_notebooks",
    "generate-reports":            "coding.generate_reports",
    "sync-params":                 "coding.sync_params",
    "sync-diagnostics-yaml":       "coding.sync_diagnostics_yaml",
    "sync-qualification-hashes":   "coding.sync_qualification_hashes",
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
    "apply-pending":               "coding.apply_pending",
    "prune-manifest":              "coding.prune_manifest",
    "check-notes":                 "coding.check_notes",
    "refresh-dropdowns":           "coding.refresh_dropdowns",
    "import-planar":               "coding.import_planar",
    "generate-status-sheet":       "coding.generate_status_sheet",
    "generate-biuniqueness-allomorphy-sheet": "coding.generate_biuniqueness_allomorphy_sheet",
    "registry":                    "coding.registry",
}


def _warn_pending() -> None:
    """Print a reminder if pending_changes.json has unreviewed destructive changes."""
    pending = _ROOT / "pending_changes.json"
    if pending.exists() and json.loads(pending.read_text(encoding="utf-8") or "[]"):
        print("WARNING: Pending destructive changes require coordinator approval.")
        print("         Run: python -m coding apply-pending\n")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    _warn_pending()

    cmd = sys.argv[1]
    if cmd not in _COMMANDS:
        print(f"Unknown command: {cmd!r}")
        print(f"Available commands: {', '.join(sorted(_COMMANDS))}")
        sys.exit(1)

    # Remove the subcommand so the module's own parser -- and, for
    # restructure_sheets.py/sync_params.py, their hand-rolled colon/comma
    # helpers that read sys.argv directly -- see only its own flags.
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    import importlib
    mod = importlib.import_module(_COMMANDS[cmd])
    args = mod.build_parser().parse_args()
    # Parsed once, here, rather than inside mod.main() -- this is the
    # dispatch chokepoint Phase 5 units D (precondition enforcement) and E
    # (provenance capture) hook into, keyed by `cmd` and `args`.
    op_id = cmd.replace("-", "_")
    from . import preconditions, provenance
    preconditions.enforce(op_id, args)
    # Logged before the command runs, not after -- a run that fails partway
    # through can still have written something to Drive, and "this run may
    # have changed something" is the signal provenance.py exists to capture.
    provenance.record(cmd, op_id, args)
    mod.main(args)


if __name__ == "__main__":
    main()
