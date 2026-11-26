"""What the chart fingerprint counts as the charts' code.

The weekly analysis reruns every dataset when the chart code changes
(laminar/contributor_charts.code_version()), so the code it counts must be
what the charts actually run: every module the exporter imports, and not a
standalone script the charts never touch (on 2026-11-15, editing three such
scripts reran all 16 English and Araona datasets, about four hours).
"""

from laminar.contributor_charts import chart_code_files
from laminar.datasets import REPO
from laminar.export_planarsviz_data import PERMUTATION_TESTS


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
