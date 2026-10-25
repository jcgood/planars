"""``python -m coding build-chapters``: build the volume's chapters.

    python -m coding build-chapters [--apply]                  # every part in volume.yaml
    python -m coding build-chapters --lang stan1293 [--version COMMIT] [--apply]
    python -m coding build-chapters [--lang stan1293] --update [--version COMMIT] [--apply]
    python -m coding build-chapters --intro [--apply]
    python -m coding build-chapters --check [--lang stan1293] [--apply]

Phases 2–5 of docs/chapter-generation-plan.md. Dry run by default:
says what it would write; ``--apply`` writes. Only files whose text
changed are written, so a rebuild with nothing new touches nothing. Every
write goes through the local-file door (``file_door.write_paper``), which
commits and pushes what the command wrote when it ends.

**Where:** planars-data's ``.papers/`` (``state_files.PAPERS_DIR``,
decision 2; a language chapter holds unpublished annotation, so it never
goes in this public repository):

- ``volume.yaml``: the volume's title, its venue (a file in
  ``chapters/venues/``) and its parts in order (``intro``, or a language's
  Glottocode). Hand-edited; the build makes a starting one if there is
  none, and checks every part is one it can build.
- ``main.tex`` (from volume.yaml), ``planarschapter.sty`` (``\\pv``,
  ``\\proseslot``) and ``planarsvenue.sty`` (the venue's example macros,
  chapters.tex): compile ``main.tex`` there.
- one folder per part: ``chapter.tex`` (the outline: sections in the order
  of ``chapters/templates/outline.yaml``, each with its prose slot and
  then its fragments), ``fragments/``, ``prose/``, and for a language
  ``values.tex`` (every named value, ``\\pvset{name}{value}``) and
  ``data.lock`` (its pin, below).

**Built and hand-written files never share a file.** Everything except
``volume.yaml`` and ``prose/`` is rebuilt every time; a fragment no longer
made (a class retired) is deleted. ``volume.yaml`` and each
``prose/<slot>.tex`` are stubs: made once, with the slot's instructions
(who writes it, what it should say) as comments, and never written over
(the door refuses). A prose file whose slot has left the outline is
listed, never deleted; a slot still holding its ``\\proseslot`` line is
counted as not yet written.

**A language chapter is pinned to a data version**, recorded in
``<L>/data.lock`` (the planars-data commit and its date, and the planars
commit the chapter was last built with). Its first build pins the version
asked for (``--version``; default coded_data/ as it is, which must have no
uncommitted changes for the language, so every chapter can be rebuilt
exactly from the commit it names); every later build reads the data at the
pin, so new annotation never reaches a chapter unannounced. ``--update``
moves the pin (to ``--version``, or coded_data/ as it is).

**Every build reports what it changes** in a chapter's values (spans one
line each, the analysis counted per dataset), by cause, one pin at a
time: first the code (schemas, span rules: values.tex as built against the
old data read with today's code), then, with ``--update``, the annotation
(the old data against the new, both with today's code). It then lists the
prose to reread: each slot whose section's fragments changed or cite a
changed value, and each line of prose that cites one (``\\pv`` or
``\\claim``).

**Checked claims.** Prose states a fact it argues from as
``\\claim{name}{text}``, text written as values.tex writes the value (a
span's range is ``9--20``). Every build lists each claim in any part's
prose, about a language it built, that the data no longer bear out (with
its file and line), and the PDF boxes it. A claim must sit on one line.

**A language chapter** (``--lang``) is built from chapters.data.chapter_data
at its pinned version. Its fragments:
``front_matter.tex`` (language, annotator, data version, how complete the
annotation was), ``planar_table.tex``, ``diagnostics_table.tex``,
``class_<class>.tex`` for each class the language has (one sentence per
span, then the class's span table), ``examples_<class>.tex`` (the examples
its annotation gives, through the venue's example macro for the
language's example style), and ``spans_table.tex`` (every span of
the language in one table, grouped by domain type in the schema's class
order). **The introduction** (``--intro``) comes from the schemas alone:
``terms.tex`` (schemas/terms.yaml) and ``class_<class>.tex`` for every
class (what it tests, its criteria, its span rule).

**The daily check** (``--check``, run by the daily refresh) writes nothing
in ``.papers/``. For each language chapter in volume.yaml that has been
built, it builds the chapter again at its pin and compares that with what
is written (the code's changes: values and fragments), and today's data
with the pin (the annotation's), and finds the ``\\claim``s that fail now
or would fail after a move. When any of that touches the chapter (see
``VALUE_GROUPS``: how complete the annotation is, on its own, does not),
``--apply`` files or rewrites that chapter's ``chapter-behind`` issue,
counts and file names only (the repository is public); when nothing does,
it closes it. The analysis is compared only for datasets with a bundle on
the machine running it, which on GitHub is none (bundles are never
committed) until the weekly analysis (laminar plan 4d) keeps them.

The wording is in chapters/templates/ (chapters.tex says how they work).
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from importlib.resources import files as _res_files

import yaml

from chapters import tex
from chapters.data import (ChapterData, ChapterDataError, chapter_data, commit_of, is_glossed,
                           split_examples)
from coding import file_door
from laminar.planars_language import parse_dataset
from planars.languages import get_display_name, get_entry
from planars.reports import span_constructions
from planars.schema_values import is_keystone


def _schema(name: str) -> dict:
    return yaml.safe_load(_res_files("schemas").joinpath(name).read_text(encoding="utf-8")) or {}


def _class_entries() -> dict:
    return {c["name"]: c for c in _schema("diagnostic_classes.yaml").get("classes", [])}


def _criteria_entries() -> dict:
    """{class: {"description": str, "criteria": {name: entry}}} from
    diagnostic_criteria.yaml."""
    out = {}
    for a in _schema("diagnostic_criteria.yaml").get("analyses", []):
        out[a["name"]] = {"description": a.get("description", ""),
                          "criteria": {c["name"]: c for c in a.get("diagnostic_criteria") or []}}
    return out


def _domain(entry: dict) -> str:
    return ", ".join(x for x in (entry["domain_type"], entry.get("domain_subtype")) if x)


# ── The introduction ────────────────────────────────────────────────────────

def intro_fragments() -> dict:
    """{file name: text} for the introduction's fragments."""
    out = {"terms.tex": tex.render("terms.tex.j2", terms=_schema("terms.yaml").get("terms", []))}
    criteria = _criteria_entries()
    for name, entry in _class_entries().items():
        own = criteria.get(name, {"description": "", "criteria": {}})
        names = list(entry.get("required_criteria") or []) + list(entry.get("optional_criteria") or [])
        unknown = [c for c in names if c not in own["criteria"]]
        if unknown:
            raise ChapterDataError(f"Class {name}: criteria {unknown} have no entry in "
                                   f"schemas/diagnostic_criteria.yaml.")
        out[f"class_{name}.tex"] = tex.render(
            "intro_class.tex.j2", display_name=entry["display_name"], domain=_domain(entry),
            applicability=entry.get("applicability", ""), description=own["description"],
            criteria=[{"name": c, "values": [str(v) for v in own["criteria"][c].get("values") or []],
                       "description": own["criteria"][c].get("description", "")} for c in names],
            span_rule=entry.get("span_rule", ""))
    return out


# ── A language chapter ──────────────────────────────────────────────────────

def _class_context(chapter: ChapterData, cls: str) -> list:
    L = chapter.lang_id
    spans = chapter.tables["spans"]
    producing = span_constructions(cls)
    diagnostics = chapter.tables["diagnostics"]
    constructions = []
    for construction in diagnostics[diagnostics["Class"] == cls]["Construction"]:
        rows = spans[(spans["Analysis"] == cls) & (spans["Construction"] == construction)] \
            if len(spans) else spans
        constructions.append({
            "name": construction,
            "feeder": producing is not None and construction not in producing,
            "spans": [{"phrase": row["Span_Key"].replace("_", " "),
                       "base": f"{L}.span.{cls}.{construction}.{row['Span_Key']}",
                       "single": int(row["Left_Edge"]) == int(row["Right_Edge"])}
                      for _i, row in rows.iterrows()],
        })
    return constructions


def _class_examples(chapter: ChapterData, cls: str) -> list:
    """[{name, rows: [{row, examples: [Tex]}]}] for the class's annotation
    rows with an Example, in table order, each example as its venue macro."""
    glossed = is_glossed(chapter.lang_id)
    examples = chapter.tables["examples"]
    out = {}
    for _i, r in examples[examples["Class"] == cls].iterrows():
        items, _paired = split_examples(r, glossed)
        out.setdefault(r["Construction"], []).append({"row": r["Row"], "examples": [
            tex.example(e["form"], e["gloss"], e["translation"], r["Source"], glossed)
            for e in items]})
    return [{"name": name, "rows": rows} for name, rows in out.items()]


def language_fragments(chapter: ChapterData) -> dict:
    """{file name: text} for a language chapter's fragments."""
    L = chapter.lang_id
    planar = chapter.tables["planar"]
    out = {
        "front_matter.tex": tex.render("front_matter.tex.j2", L=L),
        "planar_table.tex": tex.render("planar_table.tex.j2", L=L, positions=[
            {"number": r["Position"], "type": r["Position_Type"], "name": r["Position_Name"],
             "elements": r["Elements"].strip(), "keystone": is_keystone(r["Position_Name"])}
            for _i, r in planar.iterrows()]),
        "diagnostics_table.tex": tex.render("diagnostics_table.tex.j2", L=L, rows=[
            {"class_name": _class_entries()[r["Class"]]["display_name"],
             "construction": r["Construction"], "criteria": list(r["Criteria"].items())}
            for _i, r in chapter.tables["diagnostics"].iterrows()]),
    }
    entries = _class_entries()
    diagnostics = chapter.tables["diagnostics"]
    groups = {}  # domain -> rows of the language-wide span table
    for cls in dict.fromkeys(diagnostics["Class"]):
        constructions = _class_context(chapter, cls)
        out[f"class_{cls}.tex"] = tex.render("class_section.tex.j2", L=L,
                                             display_name=entries[cls]["display_name"],
                                             constructions=constructions)
        out[f"examples_{cls}.tex"] = tex.render("examples_section.tex.j2",
                                                display_name=entries[cls]["display_name"],
                                                constructions=_class_examples(chapter, cls))
        rows = groups.setdefault(_domain(entries[cls]), [])
        rows.extend({"class_name": entries[cls]["display_name"], "construction": c["name"], **s}
                    for c in constructions for s in c["spans"])
    out["spans_table.tex"] = tex.render("spans_table.tex.j2", L=L, groups=[
        {"domain": domain, "rows": rows} for domain, rows in groups.items() if rows])
    return out


VALUES_HEADER = ("% values.tex: every value the chapter can cite, as \\pvset{name}{value}.\n"
                 "% Written by `python -m coding build-chapters`; never edit it by hand.\n")


# ── The outline ─────────────────────────────────────────────────────────────

INTRO = "intro"
VOLUME = "volume.yaml"
MAIN = "main.tex"
STY_FILE = "planarschapter.sty"
# What a prose stub holds until someone writes in it.
SLOT_MARK = "\\proseslot{"
_SECTION_KEYS = {"heading", "slot", "who", "says", "fragments", "classes", "class_fragments"}


def _outline(kind: str) -> list:
    outline = yaml.safe_load((tex.TEMPLATES / "outline.yaml").read_text(encoding="utf-8"))
    if kind not in outline:
        raise ChapterDataError(f"chapters/templates/outline.yaml has no {kind!r} outline.")
    return outline[kind]


def outline_items(kind: str, classes: list) -> list:
    """The chapter's sections from outline.yaml, flattened: one item per
    heading or headless block. ``classes`` is [(class, display name,
    domain type)] in the schema's class order; a ``classes: true`` section
    becomes one section per domain type (in order of first appearance) and
    one subsection per class, holding the fragments its `class_fragments`
    name for that class."""
    items = []
    for section in _outline(kind):
        unknown = set(section) - _SECTION_KEYS
        if unknown:
            raise ChapterDataError(f"outline.yaml ({kind}): unknown keys {sorted(unknown)}; "
                                   f"a section takes {sorted(_SECTION_KEYS)}.")
        if (section.get("slot") or section.get("classes")) and not (section.get("who") and section.get("says")):
            raise ChapterDataError(f"outline.yaml ({kind}): a section with a prose slot needs "
                                   f"`who` and `says` (its stub's instructions): {section}")
        if section.get("classes"):
            if not section.get("class_fragments"):
                raise ChapterDataError(f"outline.yaml ({kind}): a `classes` section needs "
                                       f"`class_fragments` (e.g. [class]): {section}")
            by_domain = {}
            for cls, display_name, domain_type in classes:
                by_domain.setdefault(domain_type, []).append((cls, display_name))
            for domain_type, members in by_domain.items():
                items.append({"command": "section", "heading": None, "domain": domain_type,
                              "slot": None, "fragments": []})
                items += [{"command": "subsection", "heading": display_name, "domain": None,
                           "in_domain": domain_type, "slot": f"class_{cls}",
                           "fragments": [f"{f}_{cls}" for f in section["class_fragments"]],
                           "who": section["who"],
                           "says": section["says"]} for cls, display_name in members]
        else:
            items.append({"command": "section" if section.get("heading") else None,
                          "heading": section.get("heading"), "domain": None, "in_domain": None,
                          "slot": section.get("slot"), "fragments": list(section.get("fragments") or []),
                          "who": section.get("who"), "says": section.get("says")})
    return items


# ── The pin: the data version a chapter is built from ───────────────────────

LOCK = "data.lock"
LOCK_HEADER = ("# data.lock: the planars-data version this chapter is built from, and the\n"
               "# planars code (schemas, span rules) it was last built with. Written by\n"
               "# `python -m coding build-chapters`; move it with --update, never by hand.\n")


def read_lock(lang: str) -> dict | None:
    text = file_door.read_paper(file_door.paper_built(f"{lang}/{LOCK}"))
    if text is None:
        return None
    lock = yaml.safe_load(text) or {}
    if not all(isinstance(lock.get(k), str) for k in ("planars_data", "date", "planars")):
        raise ChapterDataError(f".papers/{lang}/{LOCK} needs `planars_data`, `date` and `planars`. "
                               f"It is written only by build-chapters: restore it from git.")
    return lock


def lock_text(chapter: ChapterData) -> str:
    return LOCK_HEADER + yaml.safe_dump({"planars_data": chapter.version["planars_data_commit"],
                                         "date": chapter.version["date"],
                                         "planars": chapter.version["planars_commit"]},
                                        sort_keys=False)


def pinned_version(lang: str, lock: dict | None, version: str | None, update: bool) -> str | None:
    """The planars-data version to build `lang` from: its pin, unless there is
    none yet or the pin is being moved (None: coded_data/ as it is)."""
    if update or lock is None:
        return version
    if version and commit_of(version) != lock["planars_data"]:
        raise ChapterDataError(
            f"The {get_display_name(lang)} chapter is pinned to planars-data "
            f"{lock['planars_data'][:12]} ({lock['date']}) by .papers/{lang}/{LOCK}. To move it, "
            f"add --update: the dry run reports what the move changes.")
    return lock["planars_data"]


# ── What changed, and the claims prose makes ────────────────────────────────

# \pv{name} and \claim{name}{text} in prose; a claim's text may hold escaped
# characters (\{) and one level of braces, and sits on one line.
_CITE = re.compile(r"\\(pv|claim)\{([^}]*)\}(?:\{((?:\\.|[^{}\\]|\{[^{}]*\})*)\})?")
_COMMENT = re.compile(r"(?<!\\)%.*")
_SPAN = re.compile(r"^(?P<L>[^.]+)\.span\.(?P<cls>[^.]+)\.(?P<con>[^.]+)\.(?P<key>[^.]+)\.(?P<field>[^.]+)$")
_ANALYSIS = re.compile(r"^[^.]+\.analysis\.[^.]+\.[^.]+")


def citations(parts: list) -> list:
    """Every \\pv and \\claim in the prose of `parts` (comments skipped):
    [(path in .papers, line number, "pv" or "claim", name, claimed text or None)]."""
    out = []
    for part in parts:
        for path in file_door.paper_files(f"{part}/prose", "*.tex"):
            text = path.read_text(encoding="utf-8")
            for number, line in enumerate(text.splitlines(), 1):
                for m in _CITE.finditer(_COMMENT.sub("", line)):
                    out.append((f"{part}/prose/{path.name}", number, m.group(1), m.group(2),
                                m.group(3) if m.group(1) == "claim" else None))
    return out


def value_changes(old: dict, new: dict, lang: str) -> tuple[list, set]:
    """Plain-words lines for what differs between two {name: values.tex text},
    and the names that differ. The data version's own values are left out
    (they change with every move); a span is one line; the analysis is
    counted per dataset."""
    skip = f"{lang}.data."
    changed = {k for k in set(old) | set(new) if not k.startswith(skip) and old.get(k) != new.get(k)}
    lines, spans, analysis = [], {}, {}
    for k in sorted(changed):
        span, grouped = _SPAN.match(k), _ANALYSIS.match(k)
        if span:
            spans.setdefault(k.rsplit(".", 1)[0], span)
        elif grouped:
            analysis[grouped.group()] = analysis.get(grouped.group(), 0) + 1
        elif k not in old:
            lines.append(f"  new value {k}: {new[k]}")
        elif k not in new:
            lines.append(f"  value gone {k} (was {old[k]})")
        else:
            lines.append(f"  {k}: {old[k]} -> {new[k]}")
    for base, m in spans.items():
        what = (f"  {m['cls']} {m['con']}, {m['key'].replace('_', ' ')}")
        was, now = old.get(f"{base}.range"), new.get(f"{base}.range")
        lines.append(f"{what}: new, {now}" if was is None else f"{what}: gone (was {was})"
                     if now is None else f"{what}: {was} -> {now}")
    lines += [f"  {base}: {n} values changed" for base, n in analysis.items()]
    return lines, changed


def change_report(lang: str, lock: dict | None, old: dict | None, middle: dict | None,
                  new: ChapterData) -> tuple[list, set]:
    """What a build changes in `lang`'s chapter, by cause: the code (schemas,
    span rules) and the annotation, one at a time. `old` is values.tex as it
    is, `middle` the values at the old data version with today's code (only
    when the data version moves). Returns lines and every changed name."""
    if old is None:
        return [], set()
    now = {k: tex.value_text(v) for k, v in new.values.items()}
    was, now_commit = (lock or {}).get("planars", ""), new.version["planars_commit"]
    code = ("since the last build" if not lock else f"planars {now_commit[:12]}" if was == now_commit
            else f"planars {was[:12]} -> {now_commit[:12]}")
    data = (f"planars-data {lock['planars_data'][:12]} ({lock['date']}) -> "
            f"{new.version['planars_data_commit'][:12]} ({new.version['date']})" if lock else "")
    steps = ([("the code", code, old, middle), ("the annotation", data, middle, now)]
             if middle is not None else [("the code" if lock else "the build", code, old, now)])
    lines, changed = [], set()
    for cause, between, before, after in steps:
        said, names = value_changes(before, after, lang)
        changed |= names
        lines.append(f"Changes from {cause} ({between}): " + ("none" if not said else f"{len(names)} values"))
        lines += said
    return lines, changed


def near_changes(lang: str, changed: set, fragments: dict, items: list, parts: list) -> list:
    """The prose next to a change: each slot whose section's fragments
    changed or cite a changed value, and each line of prose anywhere that
    cites a changed value. Nothing for a chapter never built before."""
    if file_door.read_paper(file_door.paper_built(f"{lang}/values.tex")) is None:
        return []
    lines = []
    for item in items:
        texts = [fragments.get(f"{f}.tex", "") for f in item["fragments"]]
        cited = {m.group(2) for text in texts for m in _CITE.finditer(text)}
        rewritten = any(file_door.read_paper(file_door.paper_built(f"{lang}/fragments/{f}.tex")) != text
                        for f, text in zip(item["fragments"], texts))
        if item["slot"] and (cited & changed or rewritten):
            lines.append(f"  .papers/{lang}/prose/{item['slot']}.tex sits next to a change")
    lines += [f"  .papers/{rel}:{number} cites {name}, which changed"
              for rel, number, _kind, name, _said in citations(parts) if name in changed]
    return (["Prose to reread:"] + lines) if lines else []


def broken_claims(values: dict, langs: list, parts: list) -> list:
    """Every \\claim, in the prose of `parts`, about a language in `langs`
    that the data no longer bear out (or that names no value), with its file
    and line."""
    now = {k: tex.value_text(v) for k, v in values.items()}
    lines = []
    for rel, number, kind, name, said in citations(parts):
        if kind != "claim" or name.split(".", 1)[0] not in langs:
            continue
        if name not in now:
            lines.append(f"  .papers/{rel}:{number}: \\claim{{{name}}} names no value")
        elif said != now[name]:
            lines.append(f"  .papers/{rel}:{number}: \\claim{{{name}}} says {said}, the data now say {now[name]}")
    return (["Claims that no longer hold:"] + lines) if lines else []


# ── A part: its built files and its stubs ───────────────────────────────────

def part_files(part: str, version: str | None = None, update: bool = False,
               parts: list | None = None) -> tuple[dict, dict, list, dict]:
    """({path in .papers: text} built, {path: text} stubs, lines to print,
    {name: value} the part's values) for one part of the volume. A language
    is built from its pin (``pinned_version``); `update` moves the pin to
    `version`. `parts` are the parts whose prose the report looks through."""
    entries = _class_entries()
    changed, report = set(), []
    if part == INTRO:
        fragments, L, built, said, values = intro_fragments(), None, {}, [], {}
        classes = [(name, e["display_name"], e["domain_type"]) for name, e in entries.items()]
    else:
        lock = read_lock(part)
        chapter = chapter_data(part, version=pinned_version(part, lock, version, update))
        if chapter.version["uncommitted_changes"]:
            raise ChapterDataError(
                f"coded_data/{part} has uncommitted changes, so the chapter could not be "
                f"rebuilt from the commit it names. Commit them, or pass --version COMMIT.")
        fragments, L, values = language_fragments(chapter), part, chapter.values
        built = {f"{part}/values.tex": tex.values_tex(chapter.values, VALUES_HEADER),
                 f"{part}/{LOCK}": lock_text(chapter)}
        classes = [(c, entries[c]["display_name"], entries[c]["domain_type"])
                   for c in dict.fromkeys(chapter.tables["diagnostics"]["Class"])]
        said = [f"{get_display_name(part)}, planars-data "
                f"{chapter.version['planars_data_commit'][:12]} ({chapter.version['date']})"
                + (" (its pin)" if lock and not update else "")]
        said += [f"  missing: {line}" for line in chapter.missing]
        old_text = file_door.read_paper(file_door.paper_built(f"{part}/values.tex"))
        middle = None
        if lock and old_text is not None and lock["planars_data"] != chapter.version["planars_data_commit"]:
            middle = {k: tex.value_text(v)
                      for k, v in chapter_data(part, version=lock["planars_data"]).values.items()}
        report, changed = change_report(part, lock, tex.read_values_tex(old_text) if old_text else None,
                                        middle, chapter)
    items = outline_items(INTRO if part == INTRO else "language", classes)
    placed = {f for item in items for f in item["fragments"]}
    made = {name.removesuffix(".tex") for name in fragments}
    if placed != made:
        raise ChapterDataError(
            f"{part}: outline.yaml and the build disagree. Fragments made but placed nowhere: "
            f"{sorted(made - placed) or 'none'}; placed but not made: {sorted(placed - made) or 'none'}.")
    built.update({f"{part}/fragments/{name}": text for name, text in fragments.items()})
    built[f"{part}/chapter.tex"] = tex.render("chapter.tex.j2", part=part, L=L, items=items)
    chapter_name = get_display_name(part) if L else None
    stubs = {f"{part}/prose/{item['slot']}.tex": tex.render(
                 "prose_stub.tex.j2", L=L, chapter=chapter_name, slot=item["slot"],
                 heading=item["heading"], in_domain=item.get("in_domain"),
                 who=item["who"], says=item["says"])
             for item in items if item["slot"]}
    if L:
        said += report + near_changes(part, changed, fragments, items, parts or [part])
    return built, stubs, said, values


# ── The volume ──────────────────────────────────────────────────────────────

def read_volume(lang: str | None = None) -> tuple[dict, str | None]:
    """volume.yaml's title and parts, and the starting volume.yaml's text
    when there is none yet (None otherwise). Every part must be one the
    build knows: ``intro`` or a language in schemas/languages.yaml."""
    current = file_door.read_paper(file_door.paper_stub(VOLUME))
    stub = None
    if current is None:
        stub = tex.render("volume.yaml.j2", parts=[INTRO] + ([lang] if lang else []))
        current = stub
    volume = yaml.safe_load(current) or {}
    parts = volume.get("parts")
    if not isinstance(volume.get("title"), str) or not isinstance(parts, list) or not parts:
        raise ChapterDataError(".papers/volume.yaml needs a `title`, a `venue` and a list of `parts`.")
    unknown = [p for p in parts if p != INTRO and get_entry(str(p)) is None]
    if unknown:
        raise ChapterDataError(
            f".papers/volume.yaml: parts {unknown} are neither `{INTRO}` nor a language in "
            f"schemas/languages.yaml (a part is `{INTRO}` or a Glottocode).")
    repeated = sorted({p for p in parts if parts.count(p) > 1})
    if repeated:
        raise ChapterDataError(f".papers/volume.yaml lists {repeated} more than once.")
    if volume.get("venue") not in tex.venues():
        raise ChapterDataError(f".papers/volume.yaml: `venue` is {volume.get('venue')!r}; it must "
                               f"name a file in chapters/venues/ ({', '.join(tex.venues())}).")
    return volume, stub


# ── Writing ─────────────────────────────────────────────────────────────────

def write(built: dict, stubs: dict, parts: list, apply: bool) -> list:
    """Write each built file whose text differs, each stub that does not
    exist yet, and delete fragments no longer made; one line per change."""
    did = "wrote" if apply else "would write"
    report = []
    for rel, text in sorted(built.items()):
        target = file_door.paper_built(rel)
        if file_door.read_paper(target) == text:
            continue
        report.append(f"{did} {rel}")
        if apply:
            file_door.write_paper(target, text)
    for rel, text in sorted(stubs.items()):
        target = file_door.paper_stub(rel)
        if target.path.exists():
            continue
        report.append(f"{'made' if apply else 'would make'} the starting {rel}")
        if apply:
            file_door.write_paper(target, text)
    for part in parts:
        for path in file_door.paper_files(f"{part}/fragments", "*.tex"):
            rel = f"{part}/fragments/{path.name}"
            if rel not in built:
                report.append(f"{'deleted' if apply else 'would delete'} {rel} (no longer made)")
                if apply:
                    file_door.remove_paper(file_door.paper_built(rel))
    return report


def slot_report(stubs: dict, parts: list) -> list:
    """How many prose slots are still unwritten, and every prose file whose
    slot has left the outline (listed, never deleted)."""
    slots = {rel for rel in stubs if "/prose/" in rel}
    unwritten = sum(1 for rel in slots
                    if SLOT_MARK in (file_door.read_paper(file_door.paper_stub(rel)) or SLOT_MARK))
    lines = [f"Prose: {len(slots) - unwritten} of {len(slots)} slots written."]
    for part in parts:
        for path in file_door.paper_files(f"{part}/prose", "*.tex"):
            rel = f"{part}/prose/{path.name}"
            if rel not in slots:
                lines.append(f"  .papers/{rel}: its section is no longer in the outline, so the "
                             f"chapter leaves it out. Move its text into a slot that is, then "
                             f"delete it.")
    return lines


# ── The daily check (Phase 5) ───────────────────────────────────────────────

CHECK_LABEL = "chapter-behind"

# Whether a change in each group of values (chapters.data's docstring) puts
# a chapter behind on its own. The data version changes with every move;
# how complete the annotation is changes with every session, and is shown
# only in the front matter, so on its own it files nothing. A group not
# listed here fails the check (a new group must be placed by hand).
VALUE_GROUPS = {"language": True, "data": False, "planar": True, "diagnostics": True,
                "annotation": False, "spans": True, "span": True, "analysis": True}


def check_title(lang: str) -> str:
    return f"Chapter behind its data — {get_display_name(lang)}"


def _group(name: str) -> str:
    group = name.split(".")[1] if name.count(".") else ""
    if group not in VALUE_GROUPS:
        raise ChapterDataError(f"Value {name}: group {group!r} is not in chapters/build.py "
                               f"VALUE_GROUPS; say there whether a change in it puts a chapter behind.")
    return group


def _comparable(values: dict, lang: str, chapters: list) -> dict:
    """`values` without the analysis of datasets that some of `chapters` has
    no bundle for here (none is committed: on GitHub there is none at all),
    so an analysis absent from this machine never reads as one that changed."""
    drawn = set.intersection(*(set(c.bundles) for c in chapters))
    keep = tuple(f"{lang}.analysis.{g}.{s}." for _l, g, s in map(parse_dataset, drawn))
    return {k: v for k, v in values.items() if _group(k) != "analysis" or k.startswith(keep)}


def _counts(names: set) -> dict:
    """How many spans, analysis datasets and other values (those that put a
    chapter behind) `names` holds."""
    spans = {m.group("cls", "con", "key") for m in map(_SPAN.match, names) if m}
    analysis = {m.group() for m in map(_ANALYSIS.match, names) if m}
    other = {n for n in names if VALUE_GROUPS[_group(n)] and _group(n) not in ("span", "analysis")}
    return {"spans": len(spans), "analysis": len(analysis), "other": len(other)}


def check_chapter(lang: str, parts: list) -> dict | None:
    """What has moved on under `lang`'s chapter since it was built: its
    pinned build against values.tex and the fragments as written (the
    code), and today's data against the pin (the annotation). None if the
    chapter has not been built. Writes nothing."""
    lock = read_lock(lang)
    old_text = file_door.read_paper(file_door.paper_built(f"{lang}/values.tex"))
    if lock is None or old_text is None:
        return None
    pinned = chapter_data(lang, version=lock["planars_data"])
    current = chapter_data(lang)
    text = lambda chapter: {k: tex.value_text(v) for k, v in chapter.values.items()}
    old = _comparable(tex.read_values_tex(old_text), lang, [pinned])
    at_pin = text(pinned)
    _lines, code = value_changes(old, _comparable(at_pin, lang, [pinned]), lang)
    _lines, data = value_changes(_comparable(at_pin, lang, [pinned, current]),
                                 _comparable(text(current), lang, [pinned, current]), lang)
    fragments = language_fragments(pinned)
    written = {p.name for p in file_door.paper_files(f"{lang}/fragments", "*.tex")}
    files = sorted(name for name in set(fragments) | written
                   if file_door.read_paper(file_door.paper_built(f"{lang}/fragments/{name}"))
                   != fragments.get(name))
    entries = _class_entries()
    items = outline_items("language", [(c, entries[c]["display_name"], entries[c]["domain_type"])
                                       for c in dict.fromkeys(current.tables["diagnostics"]["Class"])])
    claims_now = broken_claims(pinned.values, [lang], parts)[1:]
    claims_moved = [c for c in broken_claims(current.values, [lang], parts)[1:] if c not in claims_now]
    # The file (and line) only: the rest of the line names the value.
    reread = list(dict.fromkeys(re.match(r"\s*(\S+?)(?::? |$)", line).group(1) for line in
                                near_changes(lang, code | data, language_fragments(current), items, parts)[1:]))
    return {"lock": lock, "current": current.version, "code": _counts(code),
            "data": _counts(data), "files": files, "claims_now": len(claims_now),
            "claims_moved": len(claims_moved), "reread": reread,
            "behind": bool(files or claims_now or claims_moved
                           or any(VALUE_GROUPS[_group(n)] for n in code | data))}


def _said(counts: dict) -> str:
    said = [f"{n} {what}{'' if n == 1 else 's'}" for n, what in
            ((counts["spans"], "span"), (counts["other"], "other value"),
             (counts["analysis"], "analysis dataset"))
            if n]
    return ", ".join(said) if said else "nothing"


def check_body(lang: str, found: dict, today: str) -> str:
    """The issue for a chapter behind its data. Counts and file names only:
    the repository is public, and spans and claims come from unpublished
    annotation."""
    lock, current = found["lock"], found["current"]
    lines = [f"## The {get_display_name(lang)} chapter is behind — {today}", "",
             f"The chapter in planars-data's `.papers/{lang}/` is built from planars-data "
             f"`{lock['planars_data'][:12]}` ({lock['date']}). Today's daily refresh built it "
             f"again without moving that version and found:", "",
             f"- **Changed in the annotation** since then (to `{current['planars_data_commit'][:12]}`, "
             f"{current['date']}): {_said(found['data'])}.",
             f"- **Changed by the code** (schemas, span rules, wording) at the same version: "
             + (_said(found["code"]) if any(found["code"].values()) or not found["files"]
                else "no values")
             + (f"; {len(found['files'])} generated file(s) would be rewritten" if found["files"] else "")
             + "."]
    if found["claims_now"]:
        lines.append(f"- **{found['claims_now']} `\\claim`(s) in the prose already fail** at the "
                     f"chapter's own version.")
    if found["claims_moved"]:
        lines.append(f"- **{found['claims_moved']} `\\claim`(s) would fail** once the chapter moves "
                     f"to today's data.")
    if found["reread"]:
        lines += ["", "Prose next to a change, to reread:", ""] + [f"- `{p}`" for p in found["reread"]]
    lines += ["", "## What to do", "",
              "In Claude Code in the planars repository, run the dry run, which lists each change:", "",
              f"```bash\npython -m coding build-chapters --lang {lang} --update\n```", "",
              "then the same with `--apply` to move the chapter to today's data, and reread the prose "
              "it lists. To bring in only the code's changes and keep the data version, run "
              f"`python -m coding build-chapters --lang {lang} --apply` instead. To keep the chapter "
              "where it is for now, leave this issue open: the daily refresh rewrites it in place, "
              "notifying nobody. It closes by itself when the chapter matches its data again."]
    return "\n".join(lines) + "\n"


def check(langs: list | None, apply: bool, today: str) -> None:
    """Check every language chapter in volume.yaml (or `langs`), filing,
    rewriting or closing each one's chapter-behind issue with `apply`."""
    from coding import issues
    volume, stub = read_volume()
    if stub is not None:
        print("No chapters yet (.papers/volume.yaml does not exist); nothing to check.")
        chapters = []
    else:
        chapters = [p for p in volume["parts"] if p != INTRO and (langs is None or p in langs)]
    parts = list(volume["parts"]) if stub is None else []
    behind = set()
    for lang in chapters:
        found = check_chapter(lang, parts)
        if found is None:
            print(f"{get_display_name(lang)}: not built yet.")
            continue
        print(f"{get_display_name(lang)}: annotation {_said(found['data'])}; code {_said(found['code'])}, "
              f"{len(found['files'])} file(s); claims failing {found['claims_now']}, "
              f"failing after a move {found['claims_moved']}.")
        if not found["behind"]:
            continue
        behind.add(lang)
        if apply:
            number, created = issues.file_issue(CHECK_LABEL, check_title(lang),
                                                check_body(lang, found, today),
                                                replace=True, match_title=True)
            print(f"  {'Filed' if created else 'Rewrote'} issue #{number} ({CHECK_LABEL}).")
    if not apply:
        if behind:
            print("Dry run: add --apply to file the issues.")
        return
    titles = {check_title(lang) for lang in behind}
    checked = {check_title(lang) for lang in chapters}
    for issue in issues.list_open(CHECK_LABEL):
        if issue["title"] in titles or (langs is not None and issue["title"] not in checked):
            continue
        issues.close(issue["number"], f"The chapter matches its data again (or is no longer in "
                                      f"the volume) on {today} — closing.")
        print(f"  Closed issue #{issue['number']} ({CHECK_LABEL}).")


# ── The command ─────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m coding build-chapters",
        description="Build the volume's chapters in planars-data's .papers/: the outline, "
                    "the generated fragments and values, and a stub for each prose slot.")
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--lang", help="Build only this language's chapter (Glottocode).")
    which.add_argument("--intro", action="store_true", help="Build only the introduction.")
    parser.add_argument("--version", default=None,
                        help="With --lang: the planars-data commit to build from: a chapter "
                             "not built yet, or with --update (default: coded_data/ as it is).")
    parser.add_argument("--update", action="store_true",
                        help="Move each language chapter's pin to --version (default: coded_data/ "
                             "as it is) and report what that changes.")
    parser.add_argument("--check", action="store_true",
                        help="Write nothing in .papers/: compare each language chapter (or "
                             "--lang's) with today's data and code, and with --apply file, rewrite "
                             "or close its chapter-behind issue (the daily refresh).")
    parser.add_argument("--apply", action="store_true", help="Write (default: dry run).")
    return parser


def main(args: argparse.Namespace | None = None) -> None:
    args = args if args is not None else build_parser().parse_args()
    if args.version and not args.lang:
        sys.exit("--version names the planars-data commit of one language's chapter; "
                 "give --lang too.")
    if args.check:
        if args.intro or args.update or args.version:
            sys.exit("--check compares each chapter at its pin with today's data; it takes "
                     "only --lang and --apply.")
        try:
            check([args.lang] if args.lang else None, args.apply,
                  datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        except ChapterDataError as e:
            sys.exit(str(e))
        return
    try:
        volume, volume_stub = read_volume(args.lang)
        parts = [args.lang] if args.lang else [INTRO] if args.intro else list(volume["parts"])
        built = {STY_FILE: tex.STY, tex.VENUE_STY: tex.venue_sty(volume["venue"]), MAIN: tex.render(
            "main.tex.j2", title=volume["title"], parts=volume["parts"],
            languages=[p for p in volume["parts"] if p != INTRO])}
        stubs = {VOLUME: volume_stub} if volume_stub else {}
        prose_parts = list(dict.fromkeys(list(volume["parts"]) + parts))
        values = {}
        for part in parts:
            part_built, part_stubs, said, part_values = part_files(part, args.version, args.update,
                                                                   prose_parts)
            built.update(part_built)
            stubs.update(part_stubs)
            values.update(part_values)
            for line in said:
                print(line)
    except ChapterDataError as e:
        sys.exit(str(e))
    report = write(built, stubs, parts, args.apply)
    print("\n".join(report) if report else "Nothing to change.")
    print("\n".join(slot_report(stubs, parts)))
    for line in broken_claims(values, [p for p in parts if p != INTRO], prose_parts):
        print(line)
    missing = [p for p in parts if p not in volume["parts"]]
    if missing:
        print(f"Not in .papers/volume.yaml, so main.tex leaves it out: {', '.join(missing)}. "
              f"Add it to `parts` there to include it.")
    if report and not args.apply:
        print("Dry run: add --apply to write.")


if __name__ == "__main__":
    main()
