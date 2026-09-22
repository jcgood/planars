"""Makes the planarsviz porting checks fail on their own.

`scripts/planarsviz_checks/` holds the checks that prove the `planarsviz` R
package draws what the hand-written scripts it replaced drew. Each one renders
a chart from the package and pixel-compares it against a frozen reference
image, printing a line like:

    nyan1308_boundary_strength (11x7 in): ... differing_pixels=5.7336%

Until now they only *printed* those numbers. `check_forests.R` reported
0.0000% and nothing anywhere said it had to. Someone had to run each check by
hand and read the output to notice a chart had drifted. This file closes that
gap: it runs every check and compares its whole output against a snapshot, so
a change fails the test suite instead of scrolling past in a terminal.

Comparing the *whole* output rather than just the percentages is deliberate.
It also catches a case that quietly started skipping, a canvas that changed
size, a comparison that lost its reference image, and a count that moved --
all of which are real regressions that a percentage-only check would miss.

Why snapshots rather than a table of expected percentages: the project
already does change detection this way (see `test_tree_traversal.py`), and
several of these numbers are not "pass/fail" values at all. Charts 16 and 17
are cross-language ports from matplotlib, where fonts differ and so a non-zero
figure is correct and expected; five further charts were changed on purpose in
September 2026 and their numbers record the size of that deliberate change.
None of those have a threshold to sit under. What they have is a value that
should not move without someone knowing.

To re-bless the numbers after a deliberate change:

    pytest tests/test_planarsviz_checks.py --update-snapshots

Then read the diff before committing it. A snapshot updated without being read
is worse than no snapshot, because it looks like evidence.

Running the whole file takes roughly six or seven minutes. Most of that is not
the drawing: each check installs the package into its own temporary library
first, so `R CMD INSTALL` runs once per check.

Skips cleanly, rather than failing, where the tools these checks need are
absent -- R, the project virtual environment, or poppler's `pdftoppm` and
`pdftocairo`. That keeps the suite passing on a machine set up only for the
Python side of the project.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

NC = Path(__file__).resolve().parent.parent
CHECKS = NC / "scripts" / "planarsviz_checks"
SNAPSHOTS = Path(__file__).parent / "snapshots" / "planarsviz_checks"
VENV_PYTHON = NC.parent / ".venv" / "bin" / "python"
BUNDLE = NC / "results" / "planarsviz" / "nyan1308"

# These need R, the pinned R packages, and poppler. They also compare against
# reference images rendered on a Mac, so they cannot run on a Linux CI runner
# even with all three installed -- the fonts differ and every glyph would
# register as a changed pixel. CI runs this directory as
# `pytest NonCollaborative/tests -m "not needs_r"`.
pytestmark = pytest.mark.needs_r

# Every check script that can be run on its own, with no arguments.
#
# Two files in that directory are deliberately absent from this list:
#
#   superseded.R / superseded.py  -- shared helpers naming where the archived
#       original scripts live, not checks.
#   check_transparency.py         -- a helper that reports how transparent one
#       PNG is, given its path. It has no standalone form: `check_tree_counts.R`
#       calls it, so its output is already covered by that check's snapshot.
#
# `check_renderer.py` is also missing here because it needs a full render to
# compare against; it has its own test at the bottom of this file.
R_CHECKS = [
    "check_boundary_strength.R",
    "check_boundary_strength_overlay.R",
    "check_conflict_groups.R",
    "check_exemplary.R",
    "check_forests.R",
    "check_forestspans.R",
    "check_fragmentation.R",
    "check_overlays.R",
    "check_pooled.R",
    "check_skyline.R",
    "check_spanchart.R",
    "check_summary_trees.R",
    "check_tree_counts.R",
]

PYTHON_CHECKS = [
    "verify_boundary_density.py",
    "verify_boundary_strength_export.py",
    "verify_forest_export.py",
    "verify_forestspans_export.py",
    "verify_overlay_export.py",
    "verify_selection_export.py",
    "verify_tree_counts_export.py",
]


def _missing_tools():
    """Name whatever these checks need and this machine hasn't got."""
    missing = []
    if shutil.which("Rscript") is None:
        missing.append("Rscript")
    if shutil.which("pdftoppm") is None:
        missing.append("pdftoppm (poppler)")
    if shutil.which("pdftocairo") is None:
        missing.append("pdftocairo (poppler)")
    if not VENV_PYTHON.exists():
        missing.append(f"the project virtual environment at {VENV_PYTHON}")
    if not BUNDLE.is_dir():
        missing.append(f"the nyan1308 data bundle at {BUNDLE}")
    return missing


def _normalise(text, extra_paths=()):
    """Strip the parts of a check's output that change from run to run.

    R makes a fresh temporary directory each session, so paths like
    /var/folders/58/.../T//RtmpNIFRXz/nyan1308_tree_count_by_class_transp.png
    differ on every run while naming the same file. The directory is replaced
    and the filename kept, since the filename is the part that carries meaning.
    """
    for path in extra_paths:
        text = text.replace(str(path), "<output-dir>")
    # R's per-session temporary directory, wherever it sits.
    text = re.sub(r"\S*/Rtmp[A-Za-z0-9]+/+", "<tmp>/", text)
    # Any other absolute path into a system temporary directory.
    text = re.sub(r"(/private)?/(var/folders|tmp)/\S*/", "<tmp>/", text)
    # check_tree_counts.R prints results/planarsviz/reference/<file>.png
    # verbatim (via check_transparency.py) for its "reference:" transparency
    # line -- the one place a check's output names a reference image's own
    # location rather than just a chart name and a percentage. Since commit A
    # of the results/ reorg (2026-09-20), that location includes a topic
    # subfolder (e.g. reference/counts-and-chance/); since the per-language
    # folder layer (2026-09-22) it includes a dataset subfolder ahead of that
    # (e.g. reference/nyan1308/counts-and-chance/). Both are where the file
    # happens to live, not something this snapshot is meant to track, so both
    # are stripped here the same way the R tmp directory above is.
    text = re.sub(
        r"(reference/)[^/\s]+/(?:laminar-families|pooled|boundaries|counts-and-chance)/",
        r"\1", text,
    )
    return text


def _run(command, cwd=NC):
    """Run one check from NonCollaborative/ and return its combined output.

    The checks record paths relative to NonCollaborative/ and are documented
    as running from there, so the working directory is not incidental.
    """
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=900,
        env={**os.environ, "R_KEEP_PKG_SOURCE": "no"},
    )
    return completed


def _compare(name, output, request, extra_paths=()):
    """Compare a check's output against its snapshot, or write one."""
    snapshot = SNAPSHOTS / f"{name}.txt"
    actual = _normalise(output, extra_paths)

    if request.config.getoption("--update-snapshots", default=False):
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text(actual)
        pytest.skip(f"Snapshot updated: {snapshot.name}")

    if not snapshot.exists():
        pytest.fail(
            f"No snapshot for {name}. This check's output has never been "
            f"recorded. Run:\n"
            f"    pytest tests/test_planarsviz_checks.py --update-snapshots\n"
            f"then read the new file before committing it."
        )

    expected = snapshot.read_text()
    if actual == expected:
        return

    actual_lines = actual.splitlines()
    expected_lines = expected.splitlines()
    first = next(
        (i for i, (a, e) in enumerate(zip(actual_lines, expected_lines)) if a != e),
        min(len(actual_lines), len(expected_lines)),
    )
    pytest.fail(
        f"{name} no longer reports what it did.\n"
        f"  Recorded {len(expected_lines)} lines, got {len(actual_lines)}.\n"
        f"  First difference at line {first + 1}:\n"
        f"    recorded: "
        f"{expected_lines[first] if first < len(expected_lines) else '<nothing>'}\n"
        f"    now:      "
        f"{actual_lines[first] if first < len(actual_lines) else '<nothing>'}\n"
        f"\n"
        f"If a chart changed on purpose, look at the comparison image under "
        f"results/planarsviz/comparisons/ first, then re-record with "
        f"--update-snapshots."
    )


def _renv_out_of_sync():
    """Say whether the installed R packages have drifted from renv.lock.

    Worth its own check because of how the drift shows up otherwise. When the
    project is out of sync, renv prints a one-line notice at the start of
    every R session -- and these tests compare a check's whole output,
    stderr included, so that line lands at the top of all fourteen R checks
    at once. Fourteen reports of "no longer reports what it did", each
    pointing at a chart, for a reason that has nothing to do with any chart.

    It is also not a failure to paper over. The packages are pinned because
    ggplot2 4.x draws differently from 3.x; if what is installed no longer
    matches the lockfile, the pixel comparisons below are not evidence of
    anything yet.
    """
    if shutil.which("Rscript") is None or not (NC / "renv.lock").exists():
        return None
    result = subprocess.run(
        ["Rscript", "-e", "quit(status = !isTRUE(renv::status()$synchronized))"],
        cwd=NC,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return None
    return (result.stdout + result.stderr).strip()


@pytest.fixture(scope="module")
def tools():
    missing = _missing_tools()
    if missing:
        pytest.skip("not set up to draw charts here: " + ", ".join(missing))

    drift = _renv_out_of_sync()
    if drift:
        pytest.fail(
            "The R packages installed here no longer match NonCollaborative/"
            "renv.lock, so these checks would compare charts drawn by the "
            "wrong versions -- and renv's own notice about it would land in "
            "every R check's output and fail them all for the wrong reason.\n"
            "Fix: from NonCollaborative/, run\n"
            "    Rscript -e 'renv::restore()'      # use the pinned versions\n"
            "or, if the change was deliberate,\n"
            "    Rscript -e 'renv::snapshot()'     # pin what is installed\n"
            "renv reported:\n" + drift
        )


@pytest.mark.parametrize("script", R_CHECKS)
def test_r_check_reports_what_it_did(script, tools, request):
    completed = _run(["Rscript", str(CHECKS / script)])
    assert completed.returncode == 0, (
        f"{script} exited {completed.returncode}.\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    _compare(script, completed.stdout + completed.stderr, request)


@pytest.mark.parametrize("script", PYTHON_CHECKS)
def test_python_check_reports_what_it_did(script, tools, request):
    completed = _run([str(VENV_PYTHON), str(CHECKS / script)])
    assert completed.returncode == 0, (
        f"{script} exited {completed.returncode}.\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    _compare(script, completed.stdout + completed.stderr, request)


def test_renderer_check_reports_what_it_did(tools, tmp_path, request):
    """The renderer check, which needs a full render to compare against.

    This is the one check that cannot run on its own: it reads the manifest a
    render wrote and pairs each PNG with its reference. So the render happens
    first, into a temporary directory rather than into results/, which keeps
    the test from touching committed output.
    """
    output = tmp_path / "render"
    render = _run(
        [
            "Rscript",
            str(NC / "scripts" / "render_planarsviz.R"),
            "--bundle",
            str(BUNDLE.relative_to(NC)),
            "--output",
            str(output),
            "--formats",
            "pdf,png",
        ]
    )
    assert render.returncode == 0, (
        f"render_planarsviz.R exited {render.returncode}.\n"
        f"stdout:\n{render.stdout}\nstderr:\n{render.stderr}"
    )

    completed = _run([str(VENV_PYTHON), str(CHECKS / "check_renderer.py"), str(output)])
    assert completed.returncode == 0, (
        f"check_renderer.py exited {completed.returncode}.\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    _compare(
        "check_renderer.py",
        completed.stdout + completed.stderr,
        request,
        extra_paths=(output, tmp_path),
    )
