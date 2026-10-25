"""Connecting a planars language to the laminar analysis: dataset names,
the planars groupings' styles, and the R packages charts check for
(laminar/planars_language.py, planars_groupings.py, export_planarsviz_data.py,
charts.py)."""

import pytest

from laminar.charts import DEV_ONLY_R_PACKAGES, r_packages
from laminar.export_planarsviz_data import DOMAIN_TYPE_STYLE, grouping_style
from laminar.laminar_analysis import OVERLAY_GROUPS
from laminar.planars_groupings import GROUPINGS, planars_domain_type
from laminar.planars_language import parse_dataset, planar_file
from planars.schema_values import class_domain_types

needs_english = pytest.mark.skipif(not planar_file("stan1293").exists(),
                                   reason="coded_data/ (planars-data) is not cloned")


@needs_english
def test_dataset_names():
    assert parse_dataset("stan1293_types_all") == ("stan1293", "types", "all")
    assert parse_dataset("stan1293_classes_distinct") == ("stan1293", "classes", "distinct")
    # A CCDB structure can start with a planars language's code.
    assert parse_dataset("arao1248_verbal") is None
    assert parse_dataset("stan1293_type_all") is None
    assert parse_dataset("nyan1308") is None


def test_other_datasets_keep_their_style():
    for groupings in ("chichewa", "ccdb"):
        style = grouping_style(groupings)
        assert style.rows is DOMAIN_TYPE_STYLE
        assert style.overlay is OVERLAY_GROUPS


def test_planars_styles_cover_every_type_and_class():
    types = class_domain_types()
    by_type = {r["domain_type"] for r in GROUPINGS["planars_types"]["styles"]}
    assert by_type == {planars_domain_type(t, s) for t, s in types.values()}
    by_class = {r["domain_type"] for r in GROUPINGS["planars_classes"]["styles"]}
    assert by_class == set(types)
    for groupings in ("planars_types", "planars_classes"):
        style = grouping_style(groupings)
        ids = [short for _types, _colour, short in style.overlay]
        bundle_names = {b[0] for b in GROUPINGS[groupings]["bundles"]}
        assert len(ids) == len(set(ids)) and not set(ids) & bundle_names  # forest ids are file names
        assert all("short" not in row for row in style.rows)


def test_r_packages_read_from_description():
    packages = r_packages()
    assert "ggplot2" in packages and "ggtree" in packages
    assert not set(packages) & DEV_ONLY_R_PACKAGES
