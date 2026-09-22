"""Checks that `r/planarsviz` has no outstanding lintr findings.

Phase D's tooling pass (2026-09-22) ran `lintr::lint_package()` once, read
every finding, and resolved each one: a real fix (a handful of camelCase
variable names renamed to match the package's snake_case convention, three
overlong lines wrapped) or a documented exception in `r/planarsviz/.lintr`
for a linter whose default does not fit something this package does on
purpose (ggplot2 brought in with `import()` rather than per-function
`importFrom`, `%>%` as the project's chosen pipe, dot-separated names kept
in `pooled.R` because that file is a deliberately near-verbatim copy of the
script it was ported from). See `.lintr`'s own comments for the reasoning
behind each exception, and the "per-language folder layer" progress-doc
entry after it for how this was verified.

This test is what keeps that clean state from quietly rotting: a new lint
finding means either a real style slip or a case `.lintr` does not yet know
to excuse, and either way it wants a look before it piles up the way phase
D's own opening pass had to work through 939 at once.

Both R calls below run from `NonCollaborative/`, for the same reason
`test_roxygen_up_to_date.py` does: `.Rprofile` there is what points R at
the versions `renv.lock` pins, lintr among them. Run from anywhere else and
a machine that only ran `renv::restore()` would have no lintr installed at
the project root, and this test would *skip* rather than fail -- a skip
reads as a pass, which is the one outcome a drift guard must never produce
by accident.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

NC_ROOT = Path(__file__).parents[1]
PACKAGE_DIR = NC_ROOT / "r" / "planarsviz"

RSCRIPT = shutil.which("Rscript")


def _lintr_available():
    if RSCRIPT is None:
        return False
    result = subprocess.run(
        [RSCRIPT, "-e", 'quit(status = !requireNamespace("lintr", quietly=TRUE))'],
        capture_output=True,
        cwd=NC_ROOT,
    )
    return result.returncode == 0


pytestmark = [
    pytest.mark.needs_r,
    pytest.mark.skipif(
        not _lintr_available(),
        reason="Rscript and/or the lintr R package are not installed on this machine.",
    ),
]


def test_planarsviz_package_has_no_lints():
    result = subprocess.run(
        [
            RSCRIPT, "-e",
            'lints <- lintr::lint_package("r/planarsviz"); '
            'cat("LINT_COUNT:", length(lints), "\\n", sep = ""); '
            "print(lints)",
        ],
        capture_output=True,
        text=True,
        cwd=NC_ROOT,
    )
    assert result.returncode == 0, (
        "lintr::lint_package() failed to run against r/planarsviz. Its output was:\n"
        + result.stdout + result.stderr
    )
    # A prefixed marker, not just "the first line", because renv itself can print
    # its own startup noise (an out-of-sync warning, a large-dependency-scan
    # notice) ahead of this on stdout -- seen for real the first time this test
    # ran against a freshly-recorded renv.lock entry, before anything had made
    # renv's implicit scanner notice lintr/styler were actually in use.
    count_lines = [line for line in result.stdout.splitlines() if line.startswith("LINT_COUNT:")]
    assert count_lines, "Expected a LINT_COUNT: line in lintr's output but found none:\n" + result.stdout
    count = count_lines[0].removeprefix("LINT_COUNT:")
    assert count == "0", (
        f"r/planarsviz has {count} lintr finding(s) that r/planarsviz/.lintr "
        "does not already excuse:\n\n" + result.stdout + "\n"
        "Fix the finding, or if it is a false positive from something the package "
        "does on purpose, add a documented exception to r/planarsviz/.lintr the "
        "way the existing ones are written -- with the reasoning, not just the "
        "linter name."
    )
