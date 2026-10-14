"""Run a command's main() the way `python -m coding` does, for the Drive door.

The dispatcher tells the Drive door (coding/drive_door.py) which command is
running, so the door knows whether this invocation may write; a door with no
command running refuses every write. Tests call a command's main() directly,
so they say which command it is here instead. Arguments come from sys.argv,
as the command's own main() would read them.

The door checks writes against the language files the command itself reads:
the command module's CODED_DATA, which tests point at their own copy.
"""
from __future__ import annotations

from coding import drive_door


def run_command(module, command: str) -> None:
    """Parse sys.argv with ``module``'s parser and run it as ``command``."""
    args = module.build_parser().parse_args()
    previous = drive_door.CODED_DATA
    drive_door.CODED_DATA = getattr(module, "CODED_DATA", previous)
    try:
        with drive_door.running(command, args):
            module.main(args)
    finally:
        drive_door.CODED_DATA = previous
