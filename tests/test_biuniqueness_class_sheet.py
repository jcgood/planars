"""End to end: the biuniqueness_deviations class sheet through generate-sheets,
on the offline Drive stand-in (issue #254).

Walks the three-tab chain the way Adam will: the sheet is created with
the elements tab filled from the planar and the two later tabs empty; once
that is answered and imported, morphemes is regenerated from it;
once morphemes is imported, morphs is regenerated from that. Then the
backward guarantees: an answered row is never silently dropped, and a row
added by hand survives.
"""
from __future__ import annotations

import pandas as pd
import pytest

from command_runner import run_command
from coding import biuniqueness_rows as br
from test_generate_sheets_snapshot import env  # noqa: F401  (pytest fixture)

LANG = "stan1293"
CLASS = br.CLASS_NAME
ELEMENTS = br.ELEMENTS

CRITERIA = {
    ELEMENTS: {"has_allomorphs": ["y", "n"], "members": ["<free_text>"],
                     "co_exponents": ["<position_names>"]},
    "morphemes": {"morpheme_class": ["<free_text>"], "forms_relation": ["alternate", "co-occur"]},
    "morphs": {"occurs_here": ["y", "n"],
               "conditioning_type": ["phonological", "morphosyntactic",
                                     "lexico-constructional", "prosodic"],
               "conditioning_features": ["<free_text>"],
               "conditioned_by": ["<position_names>"], "trigger_filled": ["y", "n"]},
}


def add_class(env):
    env.edit_yaml(LANG, lambda d: d["classes"].__setitem__(CLASS, {
        "constructions": list(CRITERIA),
        "construction_criteria": CRITERIA,
    }))


def tab_df(env, construction):
    values = env.tab(LANG, CLASS, construction).get_all_values()
    return pd.DataFrame(values[1:], columns=values[0])


def import_tab(env, construction, edit=None):
    """Stand in for import-sheets: the tab as it is, written to the local TSV."""
    df = tab_df(env, construction)
    if edit:
        df = edit(df)
    path = env.coded / LANG / CLASS / f"{construction}.tsv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep="\t", index=False)
    return df


def answer_elements(df):
    def put(element, pos, **vals):
        mask = (df["Element"] == element) & (df["Position_Name"] == pos)
        assert mask.any(), (element, pos)
        for k, v in vals.items():
            df.loc[mask, k] = v
    put("do", "v:frontedauxiliary", has_allomorphs="y", members="do, does")
    put("will", "v:modal1", has_allomorphs="y", members="'ll, won't")
    put("be", "v:progressive", has_allomorphs="n", co_exponents="v:verbinflection")
    return df


def regen(env, construction, *extra):
    return env.run(["generate-sheets", "--lang", LANG,
                    "--regen-construction", f"{CLASS}:{construction}", *extra])


@pytest.fixture
def created(env):
    # The frozen data already has English's live class sheet; start from none.
    env.remove_class(LANG, CLASS)
    add_class(env)
    out = env.run(["generate-sheets", "--apply"])
    assert "[SystemExit:" not in out, out
    return env, out


def test_creating_the_sheet_fills_elements_and_leaves_the_later_tabs_waiting(created):
    env, out = created
    ps = tab_df(env, ELEMENTS)
    assert list(ps.columns[:3]) == ["Element", "Position_Name", "Position_Number"]
    assert "KEYSTONE" not in set(ps["Element"])                  # out of scope
    assert (ps.loc[ps["Element"] == "AD-S", "has_allomorphs"] == "NA").all()
    assert tab_df(env, "morphemes").empty
    assert list(tab_df(env, "morphemes").columns[:3]) == br.MORPHEMES_STRUCT
    assert f"{ELEMENTS}.tsv not found" in out


def test_free_text_columns_get_no_dropdown_and_choice_columns_do(created):
    env, _ = created
    ws = env.tab(LANG, CLASS, ELEMENTS)
    header = ws.get_all_values()[0]
    assert ws._cell(1, header.index("has_allomorphs")).validation is not None
    assert ws._cell(1, header.index("members")).validation is None
    assert ws._cell(1, header.index("co_exponents")).validation is None


def test_the_chain_elements_to_morphemes_to_morphs(created):
    env, _ = created
    import_tab(env, ELEMENTS, answer_elements)

    out = regen(env, "morphemes")
    assert "[SystemExit:" not in out, out
    morphemes = tab_df(env, "morphemes")
    assert {"do", "will", "be + v:verbinflection"} <= set(morphemes["Morpheme"])
    co = morphemes[morphemes["Morpheme"] == "be + v:verbinflection"].iloc[0]
    assert co["forms_relation"] == "co-occur"

    import_tab(env, "morphemes")
    out = regen(env, "morphs")
    assert "[SystemExit:" not in out, out
    morphs = tab_df(env, "morphs")
    will = morphs[morphs["Morpheme"] == "will"]
    assert set(zip(will["Position_Name"], will["Form"])) == {
        (p, f) for p in ("v:frontedauxiliary", "v:modal1") for f in ("will", "'ll", "won't")}
    assert set(morphs["Origin"]) <= set(br.GENERATED_ORIGINS)


def _through_morphs(env):
    import_tab(env, ELEMENTS, answer_elements)
    regen(env, "morphemes")
    import_tab(env, "morphemes")
    regen(env, "morphs")


def _set_cell(env, construction, match, col, value):
    ws = env.tab(LANG, CLASS, construction)
    values = ws.get_all_values()
    header = values[0]
    for i, row in enumerate(values[1:], start=2):
        rec = dict(zip(header, row))
        if all(rec[k] == v for k, v in match.items()):
            ws.update_cell(i, header.index(col) + 1, value)
            return
    raise AssertionError(f"no row matching {match}")


def test_regenerating_keeps_every_answer(created):
    env, _ = created
    _through_morphs(env)
    _set_cell(env, "morphs", {"Morpheme": "do", "Form": "does"}, "occurs_here", "y")
    out = regen(env, "morphs")
    assert "[SystemExit:" not in out, out
    morphs = tab_df(env, "morphs")
    assert morphs.loc[(morphs["Morpheme"] == "do") & (morphs["Form"] == "does"),
                      "occurs_here"].tolist() == ["y"]


def test_an_answered_row_whose_source_disappears_stops_the_regeneration(created):
    env, _ = created
    _through_morphs(env)
    _set_cell(env, "morphs", {"Morpheme": "do", "Form": "does"}, "occurs_here", "y")
    before = env.tab(LANG, CLASS, "morphs").get_all_values()

    # do drops out of morphemes (Adam changed the elements tab and it was re-imported).
    import_tab(env, "morphemes", lambda df: df[df["Morpheme"] != "do"])
    out = regen(env, "morphs")
    assert "ABORTED" in out
    assert "Morpheme 'do', Position_Name 'v:frontedauxiliary', Form 'does'" in out
    assert "occurs_here: 'y'" in out
    assert "--confirm-drop" in out
    assert env.tab(LANG, CLASS, "morphs").get_all_values() == before   # nothing written

    out = regen(env, "morphs", "--confirm-drop")
    assert "[SystemExit:" not in out, out
    assert "do" not in set(tab_df(env, "morphs")["Morpheme"])


def test_a_row_added_by_hand_survives_regeneration(created):
    env, _ = created
    _through_morphs(env)
    ws = env.tab(LANG, CLASS, "morphs")
    header = ws.get_all_values()[0]
    hand = {"Morpheme": "will", "Position_Name": "v:modal1", "Form": "wo", "occurs_here": "y"}
    ws.append_rows([[hand.get(c, "") for c in header]])

    out = regen(env, "morphs")
    assert "[SystemExit:" not in out, out
    morphs = tab_df(env, "morphs")
    row = morphs[morphs["Form"] == "wo"]
    assert row["Origin"].tolist() == ["hand-added"]
    assert row["occurs_here"].tolist() == ["y"]


def test_the_daily_import_brings_the_keyed_tabs_down_intact(created, monkeypatch):
    """The point of putting this class in the ordinary pipeline: import-sheets
    backs its tabs up like any other, free text exactly as typed."""
    import io
    import sys
    from contextlib import redirect_stdout
    from types import SimpleNamespace

    from coding import drive as drive_module
    from coding import import_sheets as is_
    from fake_drive import FakeDriveDoorway

    env, _ = created
    _through_morphs(env)
    _set_cell(env, "morphs", {"Morpheme": "will", "Position_Name": "v:modal1", "Form": "won't"},
              "conditioning_features", "Polarity=NEG")
    _set_cell(env, "morphs", {"Morpheme": "will", "Position_Name": "v:modal1", "Form": "won't"},
              "occurs_here", "Y")

    tmp = env.tmp_root
    for name in ("coding.sync_params", "coding.update_sheets", "coding.restructure_sheets"):
        monkeypatch.setitem(sys.modules, name, SimpleNamespace(main=lambda: None))
    monkeypatch.setattr(is_, "ROOT", tmp)
    monkeypatch.setattr(is_, "ERROR_DIR", tmp / "import_errors")
    monkeypatch.setattr(is_, "PENDING_PATH", tmp / "pending_changes.json")
    monkeypatch.setattr(is_, "DRIFT_PATH", tmp / "diagnostics_drift.json")
    monkeypatch.setattr(is_, "_notify_pending_changes", lambda *a: None)
    monkeypatch.setattr(is_, "_notify_collaborator_check", lambda *a: None)
    monkeypatch.setattr(is_, "_load_drive_config", FakeDriveDoorway.drive_config)
    monkeypatch.setattr(is_, "_save_drive_config", lambda cfg: None)
    monkeypatch.setattr(drive_module, "_load_drive_config", FakeDriveDoorway.drive_config)
    monkeypatch.setattr(sys, "argv", ["import-sheets", "--lang", LANG, "--apply",
                                      "--overwrite-existing"])
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            run_command(is_, "import-sheets")
    except SystemExit as exc:
        assert not exc.code or "biuniqueness" not in buf.getvalue(), buf.getvalue()

    out = buf.getvalue()
    assert f"{CLASS}/morphs.tsv" in out, out
    morphs = pd.read_csv(env.coded / LANG / CLASS / "morphs.tsv", sep="\t", dtype=str,
                         keep_default_na=False)
    wont = morphs[(morphs["Morpheme"] == "will") & (morphs["Form"] == "won't")
                  & (morphs["Position_Name"] == "v:modal1")].iloc[0]
    assert wont["conditioning_features"] == "Polarity=NEG"    # free text as typed
    assert wont["occurs_here"] == "y"                          # choice normalised
    assert "keyed rows" not in out                             # no wrong-shape report


def test_update_sheets_adds_only_in_scope_elements_and_leaves_keyed_tabs_alone(
        created, monkeypatch):
    import io
    import sys
    from contextlib import redirect_stdout

    from coding import update_sheets as us
    from fake_drive import FakeDriveDoorway

    env, _ = created
    # A new element enters the planar at v:modal1 in scope, and another out of scope.
    planar_path = env.coded / LANG / "lang_setup" / f"planar_{LANG}.tsv"
    planar = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
    i = planar.index[planar["Position_Name"] == "v:modal1"][0]
    planar.loc[i, "Elements"] += ", dare, NP{O}"
    planar.to_csv(planar_path, sep="\t", index=False)

    monkeypatch.setattr(us, "_load_drive_config", FakeDriveDoorway.drive_config)
    monkeypatch.setattr(sys, "argv", ["update-sheets", "--apply"])
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            run_command(us, "update-sheets")
        except SystemExit:
            pass
    out = buf.getvalue()
    assert "[morphemes] up to date (keyed-row tab" in out, out
    assert "[morphs] up to date (keyed-row tab" in out, out

    ps = tab_df(env, ELEMENTS)
    modal = ps[ps["Position_Name"] == "v:modal1"]
    assert "dare" in set(modal["Element"])
    assert "NP{O}" not in set(modal["Element"])         # out of scope


def test_restructure_carries_keyed_answers_across_an_element_rename(created, monkeypatch):
    import io
    import sys
    from contextlib import redirect_stdout

    from coding import drive as drive_module
    from coding import generate_notebooks as gn
    from coding import import_planar as ip
    from coding import restructure_journal as rj
    from coding import restructure_sheets as rs
    from coding import validate_coding as vc
    from fake_drive import FakeDriveDoorway

    env, _ = created
    _through_morphs(env)
    _set_cell(env, "morphs", {"Morpheme": "do", "Form": "does"}, "occurs_here", "y")
    # restructure carries answers from the live Sheet; _through_morphs only
    # put the elements-tab answers in the local TSV.
    _set_cell(env, ELEMENTS, {"Element": "do", "Position_Name": "v:frontedauxiliary"},
              "has_allomorphs", "y")

    planar_path = env.coded / LANG / "lang_setup" / f"planar_{LANG}.tsv"
    planar = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
    i = planar.index[planar["Position_Name"] == "v:frontedauxiliary"][0]
    planar.loc[i, "Elements"] = planar.loc[i, "Elements"].replace("do,", "doo,")
    planar.to_csv(planar_path, sep="\t", index=False)

    tmp = env.tmp_root
    monkeypatch.setattr(rs, "MANIFEST_PATH", tmp / "sheets_manifest.json")
    monkeypatch.setattr(rj, "JOURNAL_PATH", tmp / "restructure_journal.json")
    monkeypatch.setattr(rs, "_load_drive_config", FakeDriveDoorway.drive_config)
    monkeypatch.setattr(drive_module, "_load_drive_config", FakeDriveDoorway.drive_config)
    monkeypatch.setattr(rs, "_save_drive_config", lambda cfg: None)
    monkeypatch.setattr(rs, "_autocommit_data", lambda paths, message: None)
    monkeypatch.setattr(gn, "regenerate_notebooks", lambda: None)
    monkeypatch.setattr(vc, "revalidate_sheets", lambda lang_ids=None: 0)
    monkeypatch.setattr(ip, "push_planars_to_sheets", lambda lang_ids=None, apply=False: [])
    monkeypatch.setattr(rs, "ensure_notification_issue", lambda lang_id, manifest: (999, False))
    monkeypatch.setattr(rs, "post_notification_comment", lambda *a, **kw: None)
    monkeypatch.setattr(sys, "argv", ["restructure-sheets", "--lang", LANG,
                                      "--rename-element", "do:doo", "--apply"])
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            run_command(rs, "restructure-sheets")
        except SystemExit as exc:
            assert not exc.code, buf.getvalue()
    out = buf.getvalue()
    assert "(keyed tab) copied" in out, out

    morphs = tab_df(env, "morphs")
    doo = morphs[(morphs["Morpheme"] == "doo") & (morphs["Form"] == "does")]
    assert doo["occurs_here"].tolist() == ["y"]               # answer carried, name renamed
    assert "do" not in set(morphs["Morpheme"])
    ps = tab_df(env, ELEMENTS)
    assert ps.loc[ps["Element"] == "doo", "has_allomorphs"].tolist() == ["y"]


def test_the_instructions_tab_walks_through_the_three_steps(created):
    env, _ = created
    text = "\n".join(r[0] for r in env.tab(LANG, CLASS, "Instructions").get_all_values() if r)
    assert f"STEP 1 — {ELEMENTS}" in text and "STEP 3 — morphs" in text
    assert "This tab is generated after morphemes is imported." in text
    assert text.count("ready-for-review") >= 2       # elements and morphemes
    assert "Contracted forms count" in text          # sheet_instructions (decision A)
