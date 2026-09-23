"""Checks that `planarsviz`'s R source matches what styler would write.

Phase D's tooling pass (2026-09-22) ran `styler::style_pkg()` once over the
whole package -- 19 of 21 files changed, all cosmetic (brace placement, call
wrapping), confirmed by re-rendering all 137 nyan1308 charts and getting the
same renderer-check numbers as before. Nothing since then re-styles the
source automatically, so a hand-edit that drifts from styler's formatting
would otherwise sit unnoticed until the next full re-style produces an
unrelated-looking diff.

This test runs styler in its `dry = "fail"` mode, which restyles nothing and
just reports whether restyling would change anything. If it would, someone
edited `R/` without running `styler::style_pkg("planarsviz")` afterward.

Both R calls below run from `NonCollaborative/`, for the same reason
`test_roxygen_up_to_date.py` does: `.Rprofile` there is what points R at
the versions `renv.lock` pins, styler among them. Run from anywhere else
and a machine that only ran `renv::restore()` would have no styler
installed at the project root, and this test would *skip* rather than
fail -- a skip reads as a pass, which is the one outcome a drift guard
must never produce by accident.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

NC_ROOT = Path(__file__).parents[1]
PACKAGE_DIR = NC_ROOT / "planarsviz"

RSCRIPT = shutil.which("Rscript")


def _styler_available():
    if RSCRIPT is None:
        return False
    result = subprocess.run(
        [RSCRIPT, "-e", 'quit(status = !requireNamespace("styler", quietly=TRUE))'],
        capture_output=True,
        cwd=NC_ROOT,
    )
    return result.returncode == 0


pytestmark = [
    pytest.mark.needs_r,
    pytest.mark.skipif(
        not _styler_available(),
        reason="Rscript and/or the styler R package are not installed on this machine.",
    ),
]


def test_planarsviz_r_source_is_styled():
    result = subprocess.run(
        [
            RSCRIPT, "-e",
            'styler::style_pkg("planarsviz", filetype = "R", dry = "fail")',
        ],
        capture_output=True,
        text=True,
        cwd=NC_ROOT,
    )
    assert result.returncode == 0, (
        "planarsviz/R/*.R does not match what styler::style_pkg() would write. "
        "Someone edited R/ without re-running styler afterward. Its output was:\n"
        + result.stdout + result.stderr
        + "\nFix: from NC, run\n"
        '    Rscript -e \'styler::style_pkg("planarsviz")\'\n'
        "review the diff, then commit it."
    )
