"""A re-export must not keep permutation-test tables it was not asked for.

The renderer draws a permutation test's chart whenever that test's table is in
the bundle, so a table left over from an earlier export would be drawn as if it
belonged to the data just exported (found 2026-09-23, CCDB step 5).
"""

import pytest

from laminar.datasets import NC as ROOT   # NonCollaborative/, where the CCDB domains files stay
from laminar.export_planarsviz_data import PERMUTATION_TESTS, export_bundle

# A release archive leaves NonCollaborative/ out (.gitattributes).
pytestmark = pytest.mark.skipif(not ROOT.is_dir(), reason="NonCollaborative/ is not in this copy")

TABLES = [name for test in PERMUTATION_TESTS for name in test.tables]


def test_export_without_tests_removes_their_old_tables(tmp_path):
    data_dir = tmp_path / "chac1251_verbal" / "data"
    data_dir.mkdir(parents=True)
    for name in TABLES:
        (data_dir / name).write_text("left over from an earlier export\n")

    export_bundle(ROOT / "domains" / "domains_chac1251_verbal.tsv", tmp_path,
                  root_position_override=8, groupings="ccdb")

    assert [name for name in TABLES if (data_dir / name).exists()] == []


def test_resolution_test_without_a_region_says_so(tmp_path):
    """A dataset with no word highlight runs no resolution test, writes no
    table for it, and its metadata says why (a region is a linguistic call,
    so there is no default)."""
    import json
    bundle = export_bundle(ROOT / "domains" / "domains_chac1251_verbal.tsv", tmp_path,
                           root_position_override=8, groupings="ccdb",
                           permutations={"resolution_test": 5})
    data_dir = bundle / "data"
    metadata = json.loads((data_dir / "metadata.json").read_text())
    assert metadata["resolution_test_region"] is None
    assert "orthographic_word" in metadata["resolution_test_skipped"]
    assert not (data_dir / "resolution_test.tsv").exists()


def test_an_unknown_test_name_is_refused(tmp_path):
    with pytest.raises(ValueError, match="No such permutation test"):
        export_bundle(ROOT / "domains" / "domains_chac1251_verbal.tsv", tmp_path,
                      root_position_override=8, groupings="ccdb",
                      permutations={"fragmentaton": 5})
