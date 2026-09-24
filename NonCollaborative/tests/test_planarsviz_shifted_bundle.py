"""The shifted nyan1308 bundle must have exactly nyan1308's structure, moved.

docs/PLAN_planarsviz_library.md section 10.2. Build and export it first:
    python tests/fixtures/make_shifted_nyan.py
    python scripts/analysis/export_planarsviz_data.py \
        --domain-file tests/fixtures/domains_shifted_nyan.tsv \
        --planar-file tests/fixtures/planar_shifted_nyan.tsv \
        --labels-file tests/fixtures/display_labels_shifted_nyan.tsv \
        --highlights-file tests/fixtures/highlights_shifted_nyan.tsv \
        --conflict-groups-file tests/fixtures/conflict_groups_shifted_nyan.tsv \
        --language-name "Shifted test data" \
        --output-dir results/chart_data
"""

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
NYAN = ROOT / "results" / "chart_data" / "nyan1308" / "data"
SHIFTED = ROOT / "results" / "chart_data" / "shifted_nyan" / "data"
SHIFT = 2

pytestmark = pytest.mark.skipif(not SHIFTED.exists(), reason="shifted bundle not exported")


def rows(data_dir, name):
    with (data_dir / name).open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def meta(data_dir):
    return json.loads((data_dir / "metadata.json").read_text())


def shift_id(span_id):
    left, right = map(int, span_id.split("-"))
    return f"{left + SHIFT}-{right + SHIFT}"


def test_counts_unchanged():
    a, b = meta(NYAN), meta(SHIFTED)
    for key in ("n_active_tests", "n_unique_spans", "n_conflict_pairs",
                "n_maximal_families", "n_universal_spans"):
        assert a[key] == b[key], key
    assert b["enumeration_truncated"] is False


def test_moved_facts():
    b = meta(SHIFTED)
    assert b["n_positions"] == 22 + SHIFT
    assert b["root_position"] == 10 + SHIFT
    labels = {int(r["position"]): r["label"] for r in rows(SHIFTED, "position_labels.tsv")}
    assert labels[1] == "New1" and labels[12] == "xRoot"
    types = {r["domain_type"]: r for r in rows(SHIFTED, "domain_types.tsv")}
    assert types["tonal"]["known"] == "False"
    assert types["tonal"]["colour"] == "#7F7F7F"


SYNTHETIC_ROOT = f"1-{22 + SHIFT}"


def test_synthetic_root_listed_and_flagged():
    # The shifted data starts at position 3, so the full [1-24] root is not
    # observed; the analysis adds it to every family, and the span table must
    # list it (flagged) so memberships don't name an unknown span.
    b = meta(SHIFTED)
    assert b["synthetic_root"] is True
    assert meta(NYAN)["synthetic_root"] is False
    spans = {r["span_id"]: r for r in rows(SHIFTED, "spans.tsv")}
    assert spans[SYNTHETIC_ROOT]["synthetic"] == "True"
    assert sum(r["synthetic"] == "True" for r in spans.values()) == 1


def test_spans_are_nyan_spans_shifted():
    a = {shift_id(r["span_id"]): r for r in rows(NYAN, "spans.tsv")}
    b = {r["span_id"]: r for r in rows(SHIFTED, "spans.tsv") if r["synthetic"] != "True"}
    assert set(a) == set(b)
    for key in a:
        assert a[key]["convergence"] == b[key]["convergence"]
        assert a[key]["family_frequency"] == b[key]["family_frequency"]


def test_families_identical_in_same_order():
    # Same families in the same family_NNN order, ignoring the synthetic root
    # that only the shifted data needs.
    def by_family(data_dir, shift):
        out = {}
        for r in rows(data_dir, "family_membership.tsv"):
            span = shift_id(r["span_id"]) if shift else r["span_id"]
            if span != SYNTHETIC_ROOT or shift:
                out.setdefault(r["family_id"], set()).add(span)
        return out
    assert by_family(NYAN, True) == by_family(SHIFTED, False)


def test_selections_pick_the_same_families():
    # Section 10.2: the recovered selection rules pick the same family numbers.
    assert rows(NYAN, "selections.tsv") == rows(SHIFTED, "selections.tsv")
    a = rows(NYAN, "conflict_groups.tsv")
    b = rows(SHIFTED, "conflict_groups.tsv")
    for row in a:
        if row["defining_span_id"]:
            row["defining_span_id"] = shift_id(row["defining_span_id"])
    assert a == b


def test_tree_counts_unchanged():
    # Per-type and all-tests counts are nyan1308's, with tonosegmental named
    # tonal. Bundle rows are left out: bundles are defined by type names, so
    # the rename changes them (see the chart 6 progress entry).
    def counts(data_dir, rename):
        return {(r["condition"], rename.get(r["class"], r["class"])):
                (r["n_unique_spans"], r["n_maximal_laminar_families"])
                for r in rows(data_dir, "tree_counts.tsv") if r["kind"] != "bundle"}
    assert counts(NYAN, {"tonosegmental": "tonal"}) == counts(SHIFTED, {})


def test_boundary_strength_shifted():
    # Same strengths two positions later, and nothing at the two added
    # positions. The shifted families all contain the placeholder root
    # [1-24], but no test puts an edge there, so it counts toward neither
    # summed nor capped strength (capped counted it until 2026-09-23).
    a = rows(NYAN, "boundary_strength.tsv")
    b = rows(SHIFTED, "boundary_strength.tsv")
    assert len(b) == len(a) + SHIFT
    for row in b[:SHIFT]:
        assert (row["left_summed"], row["left_capped"], row["right_summed"], row["right_capped"]) == \
               ("0", "0", "0", "0")
    for ra, rb in zip(a, b[SHIFT:]):
        assert int(rb["position"]) == int(ra["position"]) + SHIFT
        assert {k: v for k, v in ra.items() if k != "position"} == {k: v for k, v in rb.items() if k != "position"}


def test_conflicts_are_nyan_conflicts_shifted():
    a = {frozenset((shift_id(r["span_id_a"]), shift_id(r["span_id_b"]))) for r in rows(NYAN, "conflict_pairs.tsv")}
    b = {frozenset((r["span_id_a"], r["span_id_b"])) for r in rows(SHIFTED, "conflict_pairs.tsv")}
    assert a == b
