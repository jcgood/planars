"""``python -m laminar <command>``: the package's commands.

Each command is a module with a ``main(argv)``; the analysis modules'
own command lines are run as ``python -m laminar.<module>``.
"""

from __future__ import annotations

import importlib
import sys

# command -> (module, one line for the list)
COMMANDS = {
    "charts": ("laminar.charts", "Export a dataset's chart bundle and render its charts (or every CCDB structure's)."),
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: python -m laminar <command> [options]\n\nCommands:")
        for name, (_module, line) in COMMANDS.items():
            print(f"  {name:8s} {line}")
        print("\n`python -m laminar <command> --help` for a command's options.")
        sys.exit(0 if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help") else 2)
    module, _line = COMMANDS[sys.argv[1]]
    importlib.import_module(module).main(sys.argv[2:])


if __name__ == "__main__":
    main()
