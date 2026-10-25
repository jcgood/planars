"""Partial spans and their k-of-n weights (docs/laminar-analysis-plan.md
decision 3): planars.reports._span_rows and laminar/planars_language.py."""

import pandas as pd

from planars.reports import _CLASS_HANDLERS, _WEIGHTED_SPANS, _span_rows
from laminar.planars_language import _weights, select


def _cisc_result():
    # Keystone 5. Complete positions {4, 6}; partial ones add 2 (1 of 3) and
    # 3 (1 of 2); 7 (0 of 1) is in neither.
    return {
        "strict_complete_span": (4, 6), "loose_complete_span": (4, 6),
        "strict_partial_span": (3, 6), "loose_partial_span": (2, 6),
        "position_counts": {2: (1, 3), 3: (1, 2), 4: (2, 2), 6: (1, 1), 7: (0, 1)},
    }


def test_every_class_has_an_entry():
    assert set(_WEIGHTED_SPANS) == set(_CLASS_HANDLERS)


def test_partial_spans_carry_their_gained_positions():
    rows = {r["Span_Key"]: r for r in _span_rows("ciscategorial", "general", _cisc_result(), "synth0001")}
    assert rows["strict_complete_span"]["Position_Basis"] == "complete"
    assert rows["strict_complete_span"]["Gained_Positions"] == []
    assert rows["strict_partial_span"]["Position_Basis"] == "partial"
    assert rows["strict_partial_span"]["Gained_Positions"] == [(3, 1, 2)]
    assert rows["loose_partial_span"]["Gained_Positions"] == [(2, 1, 3), (3, 1, 2)]
    assert all(r["Construction"] == "general" for r in rows.values())


def test_metrical_weighs_its_wider_complete_span():
    result = {"minimal_partial_span": (4, 5), "minimal_complete_span": (3, 5),
              "maximal_partial_span": (4, 5), "maximal_complete_span": (4, 5),
              "minimal_position_counts": {3: (2, 3), 4: (1, 1)},
              "maximal_position_counts": {3: (2, 3), 4: (1, 1)}}
    rows = {r["Span_Key"]: r for r in _span_rows("metrical", "stress_domain", result, "synth0001")}
    assert rows["minimal_complete_span"]["Position_Basis"] == "partial"
    assert rows["minimal_complete_span"]["Gained_Positions"] == [(3, 2, 3)]
    assert rows["minimal_partial_span"]["Position_Basis"] == "complete"


def test_classes_without_the_distinction_have_no_basis():
    result = {"minimal_span": (5, 5), "maximal_span": (2, 7)}
    rows = _span_rows("free_occurrence", "general", result, "synth0001")
    assert {r["Position_Basis"] for r in rows} == {""}


def test_three_weights():
    assert _weights([]) == (1.0, 1.0, 1.0)
    # mean of 1/2 and 0/2 = 0.25; weakest 0; share 1/4
    assert _weights([(3, 1, 2), (2, 0, 2)]) == (0.25, 0.0, 0.25)
    # share lets a large class count for more: (1 + 9) / (2 + 10)
    assert _weights([(3, 1, 2), (2, 9, 10)])[2] == round(10 / 12, 4)


def _table():
    return pd.DataFrame([
        {"Class": "c", "Construction": "x", "Test_Labels": "c strict complete", "Left_Edge": 3, "Right_Edge": 6, "Position_Basis": "complete"},
        {"Class": "c", "Construction": "x", "Test_Labels": "c loose complete", "Left_Edge": 3, "Right_Edge": 6, "Position_Basis": "complete"},
        {"Class": "c", "Construction": "x", "Test_Labels": "c strict partial", "Left_Edge": 2, "Right_Edge": 6, "Position_Basis": "partial"},
        {"Class": "f", "Construction": "y", "Test_Labels": "f maximal", "Left_Edge": 2, "Right_Edge": 6, "Position_Basis": ""},
    ])


def test_selections():
    table = _table()
    assert len(select(table, "all")) == 4
    assert list(select(table, "complete")["Test_Labels"]) == ["c strict complete", "c loose complete", "f maximal"]
    assert list(select(table, "partial")["Test_Labels"]) == ["c strict partial", "f maximal"]
    distinct = select(table, "distinct")
    # Same span in the same construction counts once; across classes it does not.
    assert list(distinct["Test_Labels"]) == ["c strict complete", "c strict partial", "f maximal"]
    assert distinct.iloc[0]["Same_Span_As"] == "c loose complete"
