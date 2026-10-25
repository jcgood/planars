"""``python -m chapters <command>``: the package's read-only commands.

Each command is a module with a ``main(argv)``. Building the chapters
writes into planars-data, so it is ``python -m coding build-chapters``
(chapters/build.py), which runs it through the local-file door.
"""

from __future__ import annotations

import importlib
import sys

# command -> (module, one line for the list)
COMMANDS = {
    "values": ("chapters.show_values", "Print every value a language's chapter can cite, and what is missing."),
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: python -m chapters <command> [options]\n\nCommands:")
        for name, (_module, line) in COMMANDS.items():
            print(f"  {name:8s} {line}")
        print("\n`python -m chapters <command> --help` for a command's options.")
        sys.exit(0 if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help") else 2)
    module, _line = COMMANDS[sys.argv[1]]
    importlib.import_module(module).main(sys.argv[2:])


if __name__ == "__main__":
    main()
