"""What the chart fingerprint counts as the charts' code.

The weekly analysis reruns every dataset when the chart code changes
(laminar/contributor_charts.code_version()), so the code it counts must be
what the charts actually run: every module the exporter imports, and not a
standalone script the charts never touch (on 2026-11-15, editing three such
scripts reran all 16 English and Araona datasets, about four hours).
"""

import subprocess

import pytest

from laminar import contributor_charts as cc
from laminar.contributor_charts import chart_code_files
from laminar.datasets import REPO
from laminar.export_planarsviz_data import PERMUTATION_TESTS

needs_git = pytest.mark.skipif(not (REPO / ".git").exists(), reason="no git history in this copy")


def test_counts_every_module_the_permutation_tests_run():
    files = set(chart_code_files())
    for test in PERMUTATION_TESTS:
        module = test.export.__module__
        assert module.replace(".", "/") + ".py" in files
    # The analysis modules behind the tests, reached only through imports.
    for name in ("domain_support", "resolution_test", "resolution_profile",
                 "span_placement_test", "laminar_analysis"):
        assert f"laminar/{name}.py" in files
    assert {"laminar/render_planarsviz.R", "planarsviz"} <= files


def test_leaves_out_modules_the_charts_never_import():
    files = set(chart_code_files())
    for name in ("catalan", "import_ccdb", "export_cross_language", "refinement_counts"):
        assert f"laminar/{name}.py" not in files


def test_every_file_counted_exists():
    for path in chart_code_files():
        assert (REPO / path).exists(), path


def _git(*args, stdin=None):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True,
                          input=stdin, check=True).stdout.splitlines()


@needs_git
def test_without_git_the_code_s_record_is_the_one_git_gives():
    """The software record on Zenodo has no git history, so code_version()
    works git's record out from the files; it must be git's, line for line
    (here, for the files as they are on disk: git hash-object)."""
    paths = chart_code_files()
    committed = {line.split("\t", 1)[1]: line.split(" ", 1)[0]
                 for line in _git("ls-tree", "-r", "HEAD", "--", *paths)}
    worked_out = [line for line in cc._tree_lines_from_files(paths)
                  if line.split("\t", 1)[1] in committed]   # untracked files are not in a release
    names = [line.split("\t", 1)[1] for line in worked_out]
    assert names == [n for n in committed if n in set(names)] and set(names) == set(committed)
    blobs = _git("hash-object", "--stdin-paths", stdin="\n".join(names) + "\n")
    for line, name, blob in zip(worked_out, names, blobs):
        assert line == f"{committed[name]} blob {blob}\t{name}"
