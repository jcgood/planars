"""Where the scripts the planarsviz library replaced now live.

The Python twin of superseded.R, for the checks written in Python. Same
reasoning: these checks prove the library draws what the old scripts drew, by
comparing against what those scripts contain. That makes the old scripts
evidence -- they are archived rather than deleted, and the checks stop working
if they go. See OlderFiles/planarsviz_superseded/README.md.

One place holds the path so that moving the archive again is one edit, not
fifteen. Every check imports this and calls superseded():

    from superseded import superseded
    text = superseded("results", "laminar_four_trees.r").read_text()

Paths are resolved from NonCollaborative/, so a check works from any working
directory.
"""

from pathlib import Path

NC = Path(__file__).resolve().parents[2]
SUPERSEDED_DIR = NC / "OlderFiles" / "planarsviz_superseded"


def superseded(*parts: str) -> Path:
    """Path to one archived script, checked for existence."""
    path = SUPERSEDED_DIR.joinpath(*parts)
    if not path.exists():
        raise FileNotFoundError(
            f"Superseded script not found: {path}\n"
            "These scripts are the evidence the porting checks compare against. "
            "If one is missing, restore it from git rather than skipping the check."
        )
    return path
