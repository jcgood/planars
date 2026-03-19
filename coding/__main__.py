"""Command-line interface for the coding workflow tools.

Usage:
    python -m coding <command> [options]

Commands:
    generate-sheets      Create/update Google Sheets annotation forms
    generate-notebooks   Generate and upload contributor + coordinator notebooks
    sync-params          Sync parameter columns when diagnostics.tsv changes
    update-sheets        Add missing rows/columns to existing sheets
    import-sheets        Download filled sheets to TSVs
    restructure-sheets   Archive and regenerate sheets after structural changes
    populate-sheets      Upload legacy TSV data to sheets (one-time utility)
    check-codebook       Check consistency between codebook.yaml and analysis modules
    setup-root-folder    Create ConstituencyTypology root Drive folder (run once)

Each command accepts the same flags as the original script. Use --help on any
command for details, or see CLAUDE.md.
"""
import sys


_COMMANDS = {
    "generate-sheets":    "coding.generate_sheets",
    "generate-notebooks": "coding.generate_notebooks",
    "sync-params":        "coding.sync_params",
    "update-sheets":      "coding.update_sheets",
    "import-sheets":      "coding.import_sheets",
    "restructure-sheets": "coding.restructure_sheets",
    "populate-sheets":    "coding.populate_sheets",
    "check-codebook":     "coding.check_codebook",
    "setup-root-folder":  "coding.setup_root_folder",
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

    # Remove the subcommand so the module's main() sees only its own flags
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    import importlib
    mod = importlib.import_module(_COMMANDS[cmd])
    mod.main()


if __name__ == "__main__":
    main()
