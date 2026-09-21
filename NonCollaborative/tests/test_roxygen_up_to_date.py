"""Checks that the committed R package files match what roxygen2 would write.

The `r/planarsviz` package's `NAMESPACE` file and its `man/*.Rd` help pages
are not typed by hand. They are generated from the `#'` comments sitting
above each function in `r/planarsviz/R/*.R`. If someone edits one of those
comments -- adding a parameter, changing what a function returns, fixing a
typo in a description -- and forgets to re-run roxygen2 afterward, the
comment and the generated files quietly fall out of step. Nothing else
would notice: the package still loads and works, R CMD check would not
complain, and the mismatch would only surface much later as a wrong help
page or a stale export list.

This test closes that gap. It regenerates `NAMESPACE` and `man/` from the
current `R/` source into a scratch copy of the package and compares the
result to what is actually committed. If they differ, the comments in
`R/` have moved on without anyone re-running roxygen2.

`DESCRIPTION` is deliberately left out of the comparison: roxygen2 stamps
a `Config/roxygen2/version` line into it recording the roxygen2 version
that last ran, so this test would fail every time someone runs it with a
newer roxygen2 even when nothing in `R/` actually changed. That line is
not something the drift check needs to care about.

Both R calls below run from `NonCollaborative/`, and that is not incidental.
The `.Rprofile` there is what points R at the versions `renv.lock` pins,
roxygen2 among them. Run from anywhere else, R would fall back to whatever
is installed on the machine -- and on a machine that only ran
`renv::restore()`, roxygen2 would be missing, so this test would *skip*
rather than fail. A skip reads as a pass, which is the one outcome a drift
guard must never produce by accident.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

NC_ROOT = Path(__file__).parents[1]
PACKAGE_DIR = NC_ROOT / "r" / "planarsviz"

RSCRIPT = shutil.which("Rscript")


def _roxygen2_available():
    if RSCRIPT is None:
        return False
    result = subprocess.run(
        [RSCRIPT, "-e", 'quit(status = !requireNamespace("roxygen2", quietly=TRUE))'],
        capture_output=True,
        cwd=NC_ROOT,
    )
    return result.returncode == 0


pytestmark = [
    pytest.mark.needs_r,
    pytest.mark.skipif(
        not _roxygen2_available(),
        reason="Rscript and/or the roxygen2 R package are not installed on this machine.",
    ),
]


def test_namespace_and_man_match_roxygen2_output():
    with tempfile.TemporaryDirectory() as tmp:
        scratch_package = Path(tmp) / "planarsviz"
        shutil.copytree(PACKAGE_DIR, scratch_package)

        result = subprocess.run(
            [RSCRIPT, "-e", 'roxygen2::roxygenise("%s")' % scratch_package],
            capture_output=True,
            text=True,
            cwd=NC_ROOT,
        )
        assert result.returncode == 0, (
            "roxygen2::roxygenise() failed to run against a scratch copy of "
            "r/planarsviz. Its output was:\n" + result.stdout + result.stderr
        )

        committed_namespace = (PACKAGE_DIR / "NAMESPACE").read_text()
        regenerated_namespace = (scratch_package / "NAMESPACE").read_text()
        assert committed_namespace == regenerated_namespace, (
            "r/planarsviz/NAMESPACE does not match what roxygen2 generates from "
            "the #' comments in r/planarsviz/R/*.R right now. Someone edited a "
            "roxygen comment (an @export, @import, or similar tag) without "
            "re-running roxygen2 afterward. Fix: from NC, run\n"
            '    Rscript -e \'roxygen2::roxygenise("r/planarsviz")\'\n'
            "then commit the updated NAMESPACE."
        )

        committed_man_dir = PACKAGE_DIR / "man"
        regenerated_man_dir = scratch_package / "man"
        committed_files = {p.name for p in committed_man_dir.glob("*.Rd")}
        regenerated_files = {p.name for p in regenerated_man_dir.glob("*.Rd")}

        missing = sorted(regenerated_files - committed_files)
        extra = sorted(committed_files - regenerated_files)
        assert not missing and not extra, (
            "r/planarsviz/man/ does not contain the same set of help pages that "
            "roxygen2 generates from R/ right now.\n"
            + ("Help pages roxygen2 would add: %s\n" % ", ".join(missing) if missing else "")
            + ("Help pages committed but no longer generated: %s\n" % ", ".join(extra) if extra else "")
            + "Fix: from NC, run\n"
            '    Rscript -e \'roxygen2::roxygenise("r/planarsviz")\'\n'
            "then commit the result (including any man/ files it deletes or adds)."
        )

        differing = sorted(
            name for name in committed_files
            if (committed_man_dir / name).read_text() != (regenerated_man_dir / name).read_text()
        )
        assert not differing, (
            "The following r/planarsviz/man/ help pages are out of date with the "
            "#' comments in r/planarsviz/R/*.R: " + ", ".join(differing) + ". "
            "Someone edited a roxygen comment (an @param, @return, description, "
            "or similar tag) without re-running roxygen2 afterward. Fix: from NC, run\n"
            '    Rscript -e \'roxygen2::roxygenise("r/planarsviz")\'\n'
            "then commit the updated man/ files."
        )
