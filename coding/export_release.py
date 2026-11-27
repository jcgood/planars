"""``python -m coding export-release``: one language's annotation as a
dataset to publish (docs/zenodo-report-plan.md, item 5).

    python -m coding export-release --lang stan1293 --out DIR --licence {CC-BY-4.0,CC0-1.0} --release-version 0.0.1 [--position N] [--apply]

Dry run by default: says what the folder would hold and whatever stops a
release; ``--apply`` writes it. ``DIR`` must not exist yet (or be empty)
and must lie outside this repository and planars-data: the annotation is
unpublished until the release is, and this repository is public.

**What it holds,** read at one change-log position (``--position``; default
the files as they are, which must all match their log), laid out like the
project so the spans can be derived from it again with the code at the
version it names:

- ``coded_data/<L>/lang_setup/``: the planar file and the diagnostics file;
- ``coded_data/<L>/<class>/<construction>.tsv``: every class's annotation
  (every class ``schemas/diagnostic_classes.yaml`` lists that the language
  has), without the Comments column (``check_comments.COMMENTS``: notes
  between annotator and coordinator, not data);
- ``coded_data/<L>/changes.tsv``: the language's change log, cut at the
  position (what changed when, and by which command);
- ``schemas/``: the schema files at the schemas' position
  (``versions.rebuild``), and ``codebook.md`` rendered from them;
- ``derived/``: what the code computes from the above, never typed:
  ``spans.tsv`` (``planars.reports.language_spans``), ``completeness.tsv``,
  and ``analysis/<dataset>/`` for each laminar bundle drawn from this
  version's spans (``chapters.data``'s rule);
- ``release.json``: the stamp (code version, schemas' and language's
  positions and versions), and every file's sha256;
- ``README.md``: what each folder is, how to rebuild the spans, and how to
  check a report's numbers against the folder (``python -m chapters
  rebuild-check``, chapters/rebuild_check.py);
- ``CITATION.cff``: how to cite the dataset. Its authors are the
  language's ``dataset_authors`` in ``schemas/languages.yaml``, in that
  order (English: Adam, then Jeff; Araona: Adam; Jeff, 2026-11-26), with
  each one's ORCID and affiliation read from this repository's
  ``CITATION.cff`` at each export, never copied here, as are its keywords
  (with the language's name added); its licence is
  ``--licence`` (``LICENCES``), which a release must name, since each
  language's annotator chooses for their own dataset (English: CC0, Adam,
  2026-11-26; docs/zenodo-report-plan.md, "Decided"). Under CC0 the file
  asks for a citation rather than requiring one. Its ``version`` is the
  release's own number, ``--release-version`` (``RELEASE_VERSION``: three
  numbers, e.g. 0.0.1; the Zenodo record's version too), chosen by whoever
  releases it, since the language's version counts only edits to its planar
  and diagnostics files, not its answers (English stayed 0.0.0 through its
  first release; Jeff, 2026-11-27). The README and ``release.json`` give
  both.

Everything else in the language's folder (``records/``, ``decisions.tsv``,
the archive, state the tooling keeps) is left out; the dry run lists it,
so nothing is dropped unseen.

**It refuses,** listing every case, when no licence or release version is named, when the release can't be rebuilt from
what it names (``versions.stamp_problems``: uncommitted result code, a
source changed outside the tooling), when the release check fails
(``versions.release_problems``: a breaking change with annotation still
waiting on it; reads GitHub).

**Answers drafted with Claude** and not yet checked by the annotator
(``chapters.data.claude_drafts``: Source starts with ``schemas/planar.yaml``
claude_draft_source_prefix) are released as they are, marked: the README
and ``release.json`` say how many there are in each construction and how
to find them (Jeff, 2026-11-26: the data as it is, stated openly;
docs/zenodo-report-plan.md, "Decided").

The folder is written straight to ``DIR``, not through the local-file
door: it writes nothing in planars-data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

from chapters.data import DERIVED, RELEASE_RECORD   # named there: the rebuild check reads them too
from coding import file_door, source_log, versions
from coding.check_comments import COMMENTS
from planars.languages import get_display_name, get_entry
from planars.schema_values import CLAUDE_DRAFT_SOURCE_PREFIX, class_domain_types

ROOT = file_door.ROOT
LANG_SETUP = "lang_setup"
README = "README.md"
CODEBOOK = "codebook.md"
CITATION = "CITATION.cff"
# A release's own number (--release-version): three numbers, as 0.0.1.
RELEASE_VERSION = re.compile(r"^\d+\.\d+\.\d+$")

# The licences a dataset may carry (SPDX identifiers), and what each
# CITATION.cff says to its reader. One of them is chosen per release.
LICENCES = {
    "CC-BY-4.0": "If you use this dataset, please cite it as below (CC BY 4.0 requires attribution).",
    "CC0-1.0": ("This dataset is in the public domain (CC0 1.0); no citation is required, "
                "but if you use it, please cite it as below."),
}


class ReleaseRefused(Exception):
    """A release can't be made; the message lists every reason."""


# ── Where it may write ──────────────────────────────────────────────────────

def out_problems(out: Path) -> list:
    """Why `out` can't take a release ([] if it can)."""
    out = out.resolve()
    problems = []
    for name, repo in [("this public repository", ROOT), ("planars-data", file_door.CODED_DATA)]:
        repo = repo.resolve()
        if out == repo or repo in out.parents:
            problems.append(f"{out} is inside {name}; choose a folder outside both repositories "
                            f"(the annotation is unpublished until the release is).")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        problems.append(f"{out} already exists and is not an empty folder.")
    return problems


# ── What goes in ────────────────────────────────────────────────────────────

def chosen_files(lang_id: str, lang_dir: Path) -> tuple[list, list]:
    """The language files a release holds (paths within `lang_dir`), and
    those it leaves out, from a folder holding the language's files at one
    position (module docstring)."""
    keep = {Path(LANG_SETUP) / f"planar_{lang_id}.tsv",
            Path(LANG_SETUP) / f"diagnostics_{lang_id}.yaml",
            Path(source_log.log_path(lang_id).name)}
    classes = set(class_domain_types())
    kept, left_out = [], []
    for path in sorted(p for p in lang_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(lang_dir)
        if rel in keep or (len(rel.parts) == 2 and rel.parts[0] in classes and rel.suffix == ".tsv"):
            kept.append(rel)
        else:
            left_out.append(rel)
    missing = sorted(str(k) for k in keep if k not in kept)
    if missing:
        raise ReleaseRefused(f"{get_display_name(lang_id)} has no {', '.join(missing)} at this position.")
    return kept, left_out


def without_comments(text: str) -> str:
    """An annotation TSV's text without its Comments column."""
    header = text.split("\n", 1)[0].split("\t")
    if COMMENTS not in header:
        return text
    i = header.index(COMMENTS)
    lines = text.split("\n")
    return "\n".join("\t".join(c for j, c in enumerate(line.split("\t")) if j != i) if line else line
                     for line in lines)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _codebook(schemas_dir: Path) -> str:
    """codebook.md rendered from the release's own schema files."""
    import yaml
    sys.path.insert(0, str(ROOT))
    try:
        import render_codebook
    finally:
        sys.path.remove(str(ROOT))
    load = lambda name: yaml.safe_load((schemas_dir / name).read_text(encoding="utf-8")) or {}
    return render_codebook.render(load("diagnostic_criteria.yaml"), load("diagnostic_classes.yaml"),
                                  load("terms.yaml"), load("planar.yaml"))


def drafts_section(drafts: list) -> str:
    """The README's account of the answers drafted with Claude (`drafts`:
    release.json's list), or "" when there are none."""
    if not drafts:
        return ""
    total = sum(d["answers"] for d in drafts)
    lines = "\n".join(f"- `{d['class']}/{d['construction']}.tsv`: {d['answers']}" for d in drafts)
    return f"""
## Answers drafted with Claude

{total} answers were drafted with Claude and have not yet been checked by
the annotator. They are released as they are. Each one's `Source` begins
"{CLAUDE_DRAFT_SOURCE_PREFIX}"; when the annotator checks an answer, the mark
is replaced by their own source in a later version.

{lines}
"""


def readme(lang_id: str, record: dict, counts: dict, datasets: list) -> str:
    stamp = record["stamp"]
    lang = stamp["languages"][lang_id]
    name = get_display_name(lang_id)
    analysis = ("\n".join(f"  - `{d}`" for d in datasets) if datasets
                else "  (none drawn from this version's spans)")
    drafts = drafts_section(record.get("claude_drafts", []))
    return f"""# {name}: planars annotation, change-log position {lang['position']} ({record['date']})

The annotation of {name} for the planars project: which positions of its
planar structure each constituency diagnostic picks out, as judged by its
annotator. Authors, licence and how to cite are in `CITATION.cff` and on
the Zenodo record.

- Release {record['release']}
- Language version {lang['version']}, its change log cut at line {lang['position']}
- Schemas version {stamp['schemas']['version']} (their log at line {stamp['schemas']['position']})
- Code: planars {stamp['code']['version']} (https://github.com/jcgood/planars, the release tagged `v{stamp['code']['version']}`)
- {counts['classes']} diagnostic classes, {counts['constructions']} constructions; {counts['percent']}% of cells answered

## What is here

- `coded_data/{lang_id}/lang_setup/`: the planar structure (`planar_{lang_id}.tsv`) and which
  diagnostics apply, with their constructions and criteria (`diagnostics_{lang_id}.yaml`).
- `coded_data/{lang_id}/<class>/<construction>.tsv`: the annotation, one file per construction.
  Criterion columns hold `y`, `n`, `na` or `?`; `Example` and `Source` are the annotator's.
  The annotator's notes to the coordinator (the Comments column) are left out.
- `coded_data/{lang_id}/changes.tsv`: every change to these files, when, and by which command.
- `schemas/`: the definitions the annotation is read with; `codebook.md` is them in prose.
- `derived/`: computed by the code from the files above, never typed:
  `spans.tsv` (each test's strict and loose, complete and partial spans),
  `completeness.tsv`, and the laminar analysis:
{analysis}
- `release.json`: the versions above and every file's sha256.
{drafts}
## Deriving the spans again

Install planars at the tagged version (its schemas are the ones in
`schemas/`) and, from this folder, read the annotation with it:

    pip install "git+https://github.com/jcgood/planars@v{stamp['code']['version']}"
    python -c "from planars.reports import language_spans; print(language_spans('{lang_id}', '.')[0].to_csv(sep='\\t', index=False))"

The result is `derived/spans.tsv`.

## Checking a report's numbers

A report built from this release prints every number from the language's
`values.tex`, which the report's own record holds. With planars installed
as above, this works each one out again from this folder (the analysis
from `derived/analysis/`) and lists any that differ:

    python -m chapters rebuild-check --release . --values <the report's {lang_id}/values.tex>
"""


def _cff_name(person: dict) -> str:
    return f"{person.get('given-names', '')} {person.get('family-names', '')}".strip()


def dataset_authors(lang_id: str, repo_cff: Path | None = None,
                    names: list | None = None) -> tuple[list, list]:
    """The dataset's authors, as CITATION.cff entries, and the software's
    (the repository file's). `names` (default: the language's
    dataset_authors in schemas/languages.yaml) picks and orders them from
    `repo_cff`; ReleaseRefused for a language with none or a name the file
    doesn't have."""
    import yaml
    from planars.languages import get_entry
    repo_cff = repo_cff or ROOT / CITATION
    software = (yaml.safe_load(repo_cff.read_text(encoding="utf-8")) or {}).get("authors") or []
    if not software:
        raise ReleaseRefused(f"{repo_cff} lists no authors, so the dataset's {CITATION} can't name any.")
    if names is None:
        names = ((get_entry(lang_id) or {}).get("meta") or {}).get("dataset_authors") or []
    if not names:
        raise ReleaseRefused(f"{get_display_name(lang_id)} has no dataset_authors in "
                             f"schemas/languages.yaml: list them there, in order.")
    by_name = {_cff_name(p): p for p in software}
    unknown = [n for n in names if n not in by_name]
    if unknown:
        raise ReleaseRefused(f"{', '.join(unknown)} (dataset_authors of {get_display_name(lang_id)}) "
                             f"not in {repo_cff.name}, which has {', '.join(by_name)}: add them there "
                             f"or write the name as it does.")
    return [by_name[n] for n in names], software


def citation(lang_id: str, record: dict, licence: str, repo_cff: Path | None = None,
             names: list | None = None) -> str:
    """The dataset's CITATION.cff text (authors: `dataset_authors`)."""
    import yaml
    authors, software = dataset_authors(lang_id, repo_cff, names)
    keywords = (yaml.safe_load((repo_cff or ROOT / CITATION).read_text(encoding="utf-8")) or {}
                ).get("keywords") or []
    stamp = record["stamp"]
    lang = stamp["languages"][lang_id]
    name = get_display_name(lang_id)
    cff = {
        "cff-version": "1.2.0",
        "message": LICENCES[licence],
        "type": "dataset",
        "title": f"{name}: planars constituency annotation",
        "authors": authors,
        "version": record["release"],
        "date-released": record["date"],
        "license": licence,
        "abstract": (f"The annotation of {name} for the planars project: which positions of its "
                     f"planar structure each constituency diagnostic picks out, with the schemas "
                     f"it is read with and the spans derived from it."),
        # The software's, read from the repository's file, and the language.
        "keywords": list(keywords) + [((get_entry(lang_id) or {}).get("glottolog") or {}).get("name")
                                      or lang_id],
        "references": [{
            "type": "software",
            "title": "planars",
            "version": stamp["code"]["version"],
            "url": "https://github.com/jcgood/planars",
            "authors": software,
        }],
    }
    return yaml.safe_dump(cff, sort_keys=False, allow_unicode=True)


def _table_text(df: pd.DataFrame) -> str:
    return df.to_csv(sep="\t", index=False)


def build(lang_id: str, position: int | None, out: Path, apply: bool,
          check_release: bool = True, licence: str | None = None,
          release_version: str | None = None) -> dict:
    """Make the release (or, without `apply`, say what it would hold).
    Returns a summary: files, left_out, missing, refusals. Raises
    ReleaseRefused listing every reason a release can't be made."""
    from chapters.data import ChapterDataError, chapter_data, claude_drafts

    refusals = out_problems(out)
    if licence is None:
        refusals.append(f"No licence named: give --licence ({' or '.join(LICENCES)}); the language's "
                        f"annotator chooses it (English: CC0-1.0; docs/zenodo-report-plan.md, \"Decided\").")
    elif licence not in LICENCES:
        raise ReleaseRefused(f"{licence} is not a licence a dataset may carry ({', '.join(LICENCES)}).")
    if release_version is None:
        refusals.append("No release version named: give --release-version (three numbers, e.g. "
                        "0.0.1 for a first release; higher than the language's last release).")
    elif not RELEASE_VERSION.match(release_version):
        raise ReleaseRefused(f"--release-version {release_version!r}: write it as three numbers, "
                             f"e.g. 0.0.1.")
    try:
        chapter = chapter_data(lang_id, position=position)
    except ChapterDataError as e:
        raise ReleaseRefused(str(e))
    record_stamp = chapter.version["stamp"]
    refusals += versions.stamp_problems(record_stamp)
    if check_release:
        try:
            refusals += [f"Release check: {p}" for p in versions.release_problems()]
        except RuntimeError as e:
            refusals.append(f"Release check not run: {e}")

    with tempfile.TemporaryDirectory(prefix="release_") as tmp:
        stage = Path(tmp) / "release"
        lang_dir = stage / "coded_data" / lang_id
        at = chapter.version["position"]
        try:
            source_log.files_at(lang_id, at, lang_dir)
            versions.rebuild({"schemas": record_stamp["schemas"], "languages": {}}, stage)
        except source_log.RebuildError as e:
            raise ReleaseRefused(f"{get_display_name(lang_id)} can't be rebuilt at line {at}: {e}")
        drafts = [{"class": r["Class"], "construction": r["Construction"], "answers": int(r["Rows"])}
                  for _i, r in claude_drafts(lang_dir).iterrows()]
        kept, left_out = chosen_files(lang_id, lang_dir)
        for rel in left_out:
            (lang_dir / rel).unlink()
        for folder in sorted((p for p in lang_dir.rglob("*") if p.is_dir()), reverse=True):
            if not any(folder.iterdir()):
                folder.rmdir()
        for rel in kept:
            path = lang_dir / rel
            if rel.parts[0] in class_domain_types():
                path.write_text(without_comments(path.read_text(encoding="utf-8")), encoding="utf-8")
        (stage / CODEBOOK).write_text(_codebook(stage / "schemas"), encoding="utf-8")
        derived = stage / DERIVED
        derived.mkdir()
        (derived / "spans.tsv").write_text(_table_text(chapter.tables["spans"]), encoding="utf-8")
        (derived / "completeness.tsv").write_text(_table_text(chapter.tables["completeness"]),
                                                  encoding="utf-8")
        for dataset, folder in sorted(chapter.bundles.items()):
            shutil.copytree(folder, derived / "analysis" / dataset)
        counts = {"classes": chapter.values[f"{lang_id}.diagnostics.classes"],
                  "constructions": chapter.values[f"{lang_id}.diagnostics.constructions"],
                  "percent": chapter.values[f"{lang_id}.annotation.percent"]}
        record = {"language": lang_id, "release": release_version or "(none named)",
                  "date": chapter.version["date"], "stamp": record_stamp,
                  "claude_drafts": drafts}
        (stage / README).write_text(readme(lang_id, record, counts, sorted(chapter.bundles)),
                                    encoding="utf-8")
        if licence is not None:
            (stage / CITATION).write_text(citation(lang_id, record, licence), encoding="utf-8")
        files = sorted(str(p.relative_to(stage)) for p in stage.rglob("*") if p.is_file())
        record["files"] = {f: _sha256(stage / f) for f in files}
        (stage / RELEASE_RECORD).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                                            encoding="utf-8")
        summary = {"files": files + [RELEASE_RECORD],
                   "left_out": [str(r) for r in left_out], "missing": chapter.missing,
                   "refusals": refusals, "position": at, "claude_drafts": drafts}
        if refusals:
            if apply:
                raise ReleaseRefused("\n".join(refusals))
            return summary
        if apply:
            out.mkdir(parents=True, exist_ok=True)
            shutil.copytree(stage, out, dirs_exist_ok=True)
        return summary


# ── Command line ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m coding export-release",
        description="Write one language's annotation, at one change-log position, as a "
                    "dataset to publish (with its schemas, codebook and derived spans); "
                    "refuses while anything stops a release.")
    p.add_argument("--lang", required=True, metavar="LANG_ID", help="the language to release")
    p.add_argument("--out", required=True, metavar="DIR",
                   help="the folder to write (new or empty, outside both repositories)")
    p.add_argument("--position", type=int, metavar="N",
                   help="the language's change-log position (default: the files as they are)")
    p.add_argument("--licence", choices=sorted(LICENCES),
                   help="the dataset's licence, written into its CITATION.cff (required to release)")
    p.add_argument("--release-version", metavar="X.Y.Z",
                   help="the release's own number, e.g. 0.0.1 (required to release)")
    p.add_argument("--apply", action="store_true", help="write the folder")
    return p


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    name = get_display_name(args.lang)
    try:
        summary = build(args.lang, args.position, Path(args.out), args.apply,
                        licence=args.licence, release_version=args.release_version)
    except ReleaseRefused as e:
        sys.exit(f"NO RELEASE of {name}:\n  " + str(e).replace("\n", "\n  "))
    print(f"{name} at change-log line {summary['position']}: {len(summary['files'])} file(s)"
          f"{' written to ' + args.out if args.apply else ''}.")
    if summary["left_out"]:
        print(f"Left out of the language's folder ({len(summary['left_out'])}): "
              + ", ".join(summary["left_out"][:12])
              + (" …" if len(summary["left_out"]) > 12 else ""))
    for m in summary["missing"]:
        print(f"Note: {m}")
    if summary["claude_drafts"]:
        total = sum(d["answers"] for d in summary["claude_drafts"])
        print(f"Released marked, as drafted with Claude: {total} answer(s) in "
              f"{len(summary['claude_drafts'])} construction(s) (listed in the README).")
    if summary["refusals"]:
        print(f"NO RELEASE YET ({len(summary['refusals'])}):")
        for r in summary["refusals"]:
            print(f"  {r}")
        sys.exit(1)
    if not args.apply:
        print("Run again with --apply to write it.")
