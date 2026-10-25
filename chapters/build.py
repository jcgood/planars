"""``python -m chapters build``: write a chapter's generated fragments.

    python -m chapters build --lang stan1293 --out DIR [--version COMMIT] [--apply]
    python -m chapters build --intro --out DIR [--apply]

Phase 2 of docs/chapter-generation-plan.md. Dry run by default: says what
it would write; ``--apply`` writes. Only files whose text changed are
written, so a rebuild with nothing new touches nothing.

**A language chapter** (``--lang``), from chapters.data.chapter_data at the
data version asked for (default: coded_data/ as it is, which must have no
uncommitted changes for the language, so every chapter can be rebuilt
exactly from the commit it names):

- ``DIR/values.tex``: every named value (``\\pvset{name}{value}``);
- ``DIR/planarschapter.sty``: the macros the fragments use (``\\pv``);
- ``DIR/fragments/``: ``front_matter.tex`` (language, annotator, data
  version, how complete the annotation was), ``planar_table.tex``,
  ``diagnostics_table.tex``, ``class_<class>.tex`` for each class the
  language has (one sentence per span, then the class's span table), and
  ``spans_table.tex`` (every span of the language in one table, grouped
  by domain type in the schema's class order).

**The introduction** (``--intro``), from the schemas alone:
``DIR/fragments/terms.tex`` (schemas/terms.yaml) and ``class_<class>.tex``
for every class (what it tests, its criteria, its span rule), plus the
.sty.

Fragments are never edited by hand: each build overwrites them and
deletes a fragment it no longer makes (a class retired). The prose that
goes around them lives in other files (Phase 3). A language chapter holds
unpublished annotation, so its DIR may not be inside this public
repository (the manuscripts go in planars-data's ``.papers/``, decision 2).
The wording is in chapters/templates/ (chapters.tex says how they work).
"""

from __future__ import annotations

import argparse
import sys
from importlib.resources import files as _res_files
from pathlib import Path

import yaml

from chapters import tex
from chapters.data import CODED_DATA, REPO, ChapterData, ChapterDataError, chapter_data
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
                 "% Written by `python -m chapters build`; never edit it by hand.\n")


def language_files(chapter: ChapterData) -> dict:
    """{path relative to DIR: text} for a language chapter."""
    files = {f"fragments/{name}": text for name, text in language_fragments(chapter).items()}
    files["values.tex"] = tex.values_tex(chapter.values, VALUES_HEADER)
    files["planarschapter.sty"] = tex.STY
    return files


def intro_files() -> dict:
    files = {f"fragments/{name}": text for name, text in intro_fragments().items()}
    files["planarschapter.sty"] = tex.STY
    return files


# ── Writing ─────────────────────────────────────────────────────────────────

def write(out: Path, files: dict, apply: bool) -> list:
    """Write each file whose text differs and delete fragments no longer
    made; returns one line per change."""
    report = []
    for rel, text in sorted(files.items()):
        path = out / rel
        if path.exists() and path.read_text(encoding="utf-8") == text:
            continue
        report.append(f"{'wrote' if apply else 'would write'} {rel}")
        if apply:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    fragments = out / "fragments"
    if fragments.is_dir():
        for path in sorted(fragments.glob("*.tex")):
            if f"fragments/{path.name}" not in files:
                report.append(f"{'deleted' if apply else 'would delete'} fragments/{path.name} "
                              f"(no longer made)")
                if apply:
                    path.unlink()
    return report


def _check_out(out: Path) -> None:
    out = out.resolve()
    if out.is_relative_to(REPO) and not out.is_relative_to(CODED_DATA):
        sys.exit(f"{out} is inside the public planars repository, and a language chapter "
                 f"holds unpublished annotation. Write it under coded_data/.papers/ "
                 f"(or any folder outside this repository).")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m chapters build",
                                     description="Write a chapter's generated fragments.")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--lang", help="Glottocode of the language chapter to build.")
    which.add_argument("--intro", action="store_true", help="Build the introduction's fragments.")
    parser.add_argument("--out", type=Path, required=True, help="The chapter's folder.")
    parser.add_argument("--version", default=None,
                        help="planars-data commit to build from (default: coded_data/ as it is).")
    parser.add_argument("--apply", action="store_true", help="Write (default: dry run).")
    args = parser.parse_args(argv)
    try:
        if args.intro:
            files = intro_files()
        else:
            _check_out(args.out)
            chapter = chapter_data(args.lang, version=args.version)
            if chapter.version["uncommitted_changes"]:
                sys.exit(f"coded_data/{args.lang} has uncommitted changes, so the chapter could "
                         f"not be rebuilt from the commit it names. Commit them, or pass "
                         f"--version COMMIT.")
            files = language_files(chapter)
            print(f"{chapter.values[f'{args.lang}.language.display_name']}, planars-data "
                  f"{chapter.version['planars_data_commit'][:12]} ({chapter.version['date']})")
            for line in chapter.missing:
                print(f"  missing: {line}")
    except ChapterDataError as e:
        sys.exit(str(e))
    report = write(args.out, files, args.apply)
    print("\n".join(report) if report else "Nothing to change.")
    if report and not args.apply:
        print("Dry run: add --apply to write.")


if __name__ == "__main__":
    main()
