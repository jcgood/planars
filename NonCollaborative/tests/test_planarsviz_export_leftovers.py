"""A re-export must not keep permutation-test tables it was not asked for.

The renderer draws a permutation test's chart whenever that test's table is in
the bundle, so a table left over from an earlier export would be drawn as if it
belonged to the data just exported (found 2026-09-23, CCDB step 5).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from export_planarsviz_data import export_bundle  # noqa: E402

TABLES = [
    "fragmentation_test.tsv", "fragmentation_null.tsv",
    "boundary_strength_test.tsv",
    "span_placement_test.tsv", "span_placement_null.tsv",
    "arbitrary_layers_test.tsv", "arbitrary_layers_null.tsv",
]


def test_export_without_tests_removes_their_old_tables(tmp_path):
    data_dir = tmp_path / "chac1251_verbal" / "data"
    data_dir.mkdir(parents=True)
    for name in TABLES:
        (data_dir / name).write_text("left over from an earlier export\n")

    export_bundle(ROOT / "domains" / "domains_chac1251_verbal.tsv", tmp_path,
                  root_position_override=8, groupings="ccdb")

    assert [name for name in TABLES if (data_dir / name).exists()] == []
