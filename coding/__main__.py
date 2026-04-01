"""Command-line interface for the coding workflow tools.

Usage:
    python -m coding <command> [options]

Commands:
    generate-sheets          Create/update Google Sheets annotation forms
    generate-notebooks       Generate and upload contributor + coordinator notebooks
    generate-reports         Generate and upload PDF reports for all languages to Drive
    sync-params              Sync diagnostic criterion columns when diagnostics_{lang_id}.yaml changes
    sync-diagnostics-yaml    Sync diagnostics YAML → TSV (YAML is source of truth)
    update-sheets            Add missing rows/columns to existing sheets
    import-sheets            Download filled sheets to TSVs
    validate-coding          Re-validate annotation sheets and update cell highlighting
    restructure-sheets       Archive and regenerate sheets after structural changes (--rename-class, --rename-map, --rename-element)
    populate-sheets          Upload legacy TSV data to sheets (one-time utility)
    check-codebook           Check consistency between schema files and analysis modules
    integrity-check          Full project-wide integrity check (all languages, all schemas)
    setup-root-folder        Create ConstituencyTypology root Drive folder (run once)
    lookup-lang              Fetch and cache Glottolog metadata for a language ID
    apply-pending            Review and apply pending destructive changes
    prune-manifest           Archive retired class TSVs and remove stale manifest entries

Each command accepts the same flags as the original script. Use --help on any
command for details, or see CLAUDE.md.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

_COMMANDS = {
    "generate-sheets":    "coding.generate_sheets",
    "generate-notebooks": "coding.generate_notebooks",
    "generate-reports":   "coding.generate_reports",
    "sync-params":             "coding.sync_params",
    "sync-diagnostics-yaml":  "coding.sync_diagnostics_yaml",
    "update-sheets":      "coding.update_sheets",
    "import-sheets":      "coding.import_sheets",
    "validate-coding":    "coding.validate_coding",
    "restructure-sheets": "coding.restructure_sheets",
    "populate-sheets":    "coding.populate_sheets",
    "check-codebook":     "coding.check_codebook",
    "integrity-check":    "coding.integrity_check",
    "setup-root-folder":  "coding.setup_root_folder",
    "lookup-lang":        "coding.glottolog",
    "apply-pending":      "coding.apply_pending",
    "prune-manifest":     "coding.prune_manifest",
}


def _warn_pending() -> None:
    """Print a reminder if pending_changes.json has unreviewed destructive changes."""
    pending = _ROOT / "pending_changes.json"
    if pending.exists() and pending.stat().st_size > 2:
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

    # Remove the subcommand so the module's main() sees only its own flags
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    import importlib
    mod = importlib.import_module(_COMMANDS[cmd])
    mod.main()


if __name__ == "__main__":
    main()
