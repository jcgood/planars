"""``python -m coding build-chapters``: build the volume's chapters.

    python -m coding build-chapters [--apply]                  # every part in volume.yaml
    python -m coding build-chapters --lang stan1293 [--version COMMIT] [--apply]
    python -m coding build-chapters --intro [--apply]

Phases 2 and 3 of docs/chapter-generation-plan.md. Dry run by default:
says what it would write; ``--apply`` writes. Only files whose text
changed are written, so a rebuild with nothing new touches nothing. Every
write goes through the local-file door (``file_door.write_paper``), which
commits and pushes what the command wrote when it ends.

**Where:** planars-data's ``.papers/`` (``state_files.PAPERS_DIR``,
decision 2; a language chapter holds unpublished annotation, so it never
goes in this public repository):

- ``volume.yaml``: the volume's title and its parts in order (``intro``,
  or a language's Glottocode). Hand-edited; the build makes a starting one
  if there is none, and checks every part is one it can build.
- ``main.tex`` (from volume.yaml) and ``planarschapter.sty`` (``\\pv``,
  ``\\proseslot``): compile ``main.tex`` there.
- one folder per part: ``chapter.tex`` (the outline: sections in the order
  of ``chapters/templates/outline.yaml``, each with its prose slot and
  then its fragments), ``fragments/``, ``prose/``, and for a language
  ``values.tex`` (every named value, ``\\pvset{name}{value}``).

**Built and hand-written files never share a file.** Everything except
``volume.yaml`` and ``prose/`` is rebuilt every time; a fragment no longer
made (a class retired) is deleted. ``volume.yaml`` and each
``prose/<slot>.tex`` are stubs: made once, with the slot's instructions
(who writes it, what it should say) as comments, and never written over
(the door refuses). A prose file whose slot has left the outline is
listed, never deleted; a slot still holding its ``\\proseslot`` line is
counted as not yet written.

**A language chapter** (``--lang``) is built from chapters.data.chapter_data
at the data version asked for (default: coded_data/ as it is, which must
have no uncommitted changes for the language, so every chapter can be
rebuilt exactly from the commit it names). Its fragments:
``front_matter.tex`` (language, annotator, data version, how complete the
annotation was), ``planar_table.tex``, ``diagnostics_table.tex``,
``class_<class>.tex`` for each class the language has (one sentence per
span, then the class's span table), and ``spans_table.tex`` (every span of
the language in one table, grouped by domain type in the schema's class
order). **The introduction** (``--intro``) comes from the schemas alone:
``terms.tex`` (schemas/terms.yaml) and ``class_<class>.tex`` for every
class (what it tests, its criteria, its span rule).

The wording is in chapters/templates/ (chapters.tex says how they work).
"""

from __future__ import annotations

import argparse
import sys
from importlib.resources import files as _res_files

import yaml

from chapters import tex
from chapters.data import ChapterData, ChapterDataError, chapter_data
from coding import file_door
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
_SECTION_KEYS = {"heading", "slot", "who", "says", "fragments", "classes"}


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
    one subsection per class."""
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
            by_domain = {}
            for cls, display_name, domain_type in classes:
                by_domain.setdefault(domain_type, []).append((cls, display_name))
            for domain_type, members in by_domain.items():
                items.append({"command": "section", "heading": None, "domain": domain_type,
                              "slot": None, "fragments": []})
                items += [{"command": "subsection", "heading": display_name, "domain": None,
                           "in_domain": domain_type, "slot": f"class_{cls}",
                           "fragments": [f"class_{cls}"], "who": section["who"],
                           "says": section["says"]} for cls, display_name in members]
        else:
            items.append({"command": "section" if section.get("heading") else None,
                          "heading": section.get("heading"), "domain": None, "in_domain": None,
                          "slot": section.get("slot"), "fragments": list(section.get("fragments") or []),
                          "who": section.get("who"), "says": section.get("says")})
    return items


# ── A part: its built files and its stubs ───────────────────────────────────

def part_files(part: str, version: str | None = None) -> tuple[dict, dict, list]:
    """({path in .papers: text} built, {path: text} stubs, lines to print)
    for one part of the volume."""
    entries = _class_entries()
    if part == INTRO:
        fragments, L, built, said = intro_fragments(), None, {}, []
        classes = [(name, e["display_name"], e["domain_type"]) for name, e in entries.items()]
    else:
        chapter = chapter_data(part, version=version)
        if chapter.version["uncommitted_changes"]:
            raise ChapterDataError(
                f"coded_data/{part} has uncommitted changes, so the chapter could not be "
                f"rebuilt from the commit it names. Commit them, or pass --version COMMIT.")
        fragments, L = language_fragments(chapter), part
        built = {f"{part}/values.tex": tex.values_tex(chapter.values, VALUES_HEADER)}
        classes = [(c, entries[c]["display_name"], entries[c]["domain_type"])
                   for c in dict.fromkeys(chapter.tables["diagnostics"]["Class"])]
        said = [f"{get_display_name(part)}, planars-data "
                f"{chapter.version['planars_data_commit'][:12]} ({chapter.version['date']})"]
        said += [f"  missing: {line}" for line in chapter.missing]
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
    return built, stubs, said


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
        raise ChapterDataError(".papers/volume.yaml needs a `title` and a list of `parts`.")
    unknown = [p for p in parts if p != INTRO and get_entry(str(p)) is None]
    if unknown:
        raise ChapterDataError(
            f".papers/volume.yaml: parts {unknown} are neither `{INTRO}` nor a language in "
            f"schemas/languages.yaml (a part is `{INTRO}` or a Glottocode).")
    repeated = sorted({p for p in parts if parts.count(p) > 1})
    if repeated:
        raise ChapterDataError(f".papers/volume.yaml lists {repeated} more than once.")
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
                        help="With --lang: the planars-data commit to build from "
                             "(default: coded_data/ as it is).")
    parser.add_argument("--apply", action="store_true", help="Write (default: dry run).")
    return parser


def main(args: argparse.Namespace | None = None) -> None:
    args = args if args is not None else build_parser().parse_args()
    if args.version and not args.lang:
        sys.exit("--version names the planars-data commit of one language's chapter; "
                 "give --lang too.")
    try:
        volume, volume_stub = read_volume(args.lang)
        parts = [args.lang] if args.lang else [INTRO] if args.intro else list(volume["parts"])
        built = {STY_FILE: tex.STY, MAIN: tex.render(
            "main.tex.j2", title=volume["title"], parts=volume["parts"],
            languages=[p for p in volume["parts"] if p != INTRO])}
        stubs = {VOLUME: volume_stub} if volume_stub else {}
        for part in parts:
            part_built, part_stubs, said = part_files(part, args.version)
            built.update(part_built)
            stubs.update(part_stubs)
            for line in said:
                print(line)
    except ChapterDataError as e:
        sys.exit(str(e))
    report = write(built, stubs, parts, args.apply)
    print("\n".join(report) if report else "Nothing to change.")
    print("\n".join(slot_report(stubs, parts)))
    missing = [p for p in parts if p not in volume["parts"]]
    if missing:
        print(f"Not in .papers/volume.yaml, so main.tex leaves it out: {', '.join(missing)}. "
              f"Add it to `parts` there to include it.")
    if report and not args.apply:
        print("Dry run: add --apply to write.")


if __name__ == "__main__":
    main()
