"""``python -m coding stage-zenodo``: a volume's three Zenodo records, ready
to upload (docs/zenodo-report-plan.md, "What gets published").

    python -m coding stage-zenodo --volume report --licence stan1293=CC0-1.0 \
        --release-version stan1293=0.0.1 --out DIR [--apply]

Dry run by default: says what it would stage and whatever stops it;
``--apply`` writes ``DIR`` (new or empty, outside this repository and
planars-data, as export-release's is). Nothing is sent to Zenodo: the
folders are uploaded by hand, or by whoever holds a Zenodo token, each as a
draft (private, editable, no DOI registered) that a person publishes.

**What it stages**, one folder per record, each with ``metadata.json``
(the record's fields in Zenodo's deposit form: type, title, creators with
ORCIDs and affiliations, description, licence, keywords, version, and its
links to the other records and to the work it builds on):

- ``1-software/``: ``planars-<version>.zip``, ``git archive`` of this
  repository's HEAD (what Zenodo's GitHub link would archive, so
  ``.gitattributes``' ``export-ignore`` leaves ``NonCollaborative/`` out).
  Title, authors, abstract, keywords and the works it builds on
  (``references``) are read from this repository's ``CITATION.cff``.
  Its ``README.md`` and ``CITATION.cff`` at HEAD also go beside the zip,
  and so do the dataset's: Zenodo shows them on the record page, so a
  reader sees what the zip holds before downloading it (a dataset is too
  many files for a record to hold loose, as Zenodo allows 100).
- ``2-dataset-<L>/`` for each language chapter in the volume: the
  release export-release writes (coding/export_release.py), at the
  chapter's pin in the volume, zipped as
  ``planars-<L>-dataset-<release version>.zip``, with ``--licence``'s licence (the
  annotator's choice, so it is always given, never a default) and
  ``--release-version``'s number (export-release's ``--release-version``;
  the record's version).
- ``3-report/``: ``<file_name>.pdf``, compiled from planars-data's committed
  copy of the volume's folder (refused on a LaTeX error, a value with no
  name or a claim that no longer holds), ``<file_name>-source.zip`` (those
  committed files: the LaTeX source and every ``values.tex``), and the
  record's metadata: volume.yaml's title, authors (ORCIDs and affiliations
  read from ``CITATION.cff``) and ``abstract``.
- ``README.md``: the order to upload them in, and which DOIs are not yet
  reserved.

**The DOIs.** Zenodo reserves a draft's DOI before it is published.
volume.yaml's ``records`` holds those reserved (chapters.build: ``report``,
``software`` and each language's Glottocode); each record's metadata links
to those given (the report ``documents`` the software and datasets, which
``isDocumentedBy`` it), and the report prints them under its title. So:
stage, make the drafts and reserve their DOIs, write them into
``records``, rebuild the volume, stage again, and upload these files.

**It refuses,** listing every case, when this repository has commits not
pushed (the software archive is HEAD, and must be a version others can
fetch; uncommitted code that produces results is refused by
export-release's stamp check); when the volume's folder in planars-data
has uncommitted changes; when a language chapter is not built, or was
built with other code than this checkout's (rebuild the volume); when the
volume has no ``abstract``, a language no licence or release version, or a person named as
author is not in ``CITATION.cff``; and whenever export-release refuses.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

from chapters import build as cb
from coding import export_release as er
from coding import file_door, state_files, versions
from planars.languages import get_display_name

ROOT = file_door.ROOT
METADATA = "metadata.json"
README = "README.md"
# Zenodo's identifiers for the licences a record may carry (SPDX -> Zenodo).
ZENODO_LICENCE = {"MIT": "mit", "CC0-1.0": "cc-zero", "CC-BY-4.0": "cc-by-4.0"}
# The report's own text (docs/zenodo-report-plan.md, "What gets published").
REPORT_LICENCE = "CC0-1.0"   # Jeff, 2026-11-27
_LANG_ARG = re.compile(r"^([a-z0-9]{4}\d{4})=(\S+)$")


class StagingRefused(Exception):
    """The records can't be staged; the message lists every reason."""


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise StagingRefused(f"git {' '.join(args)} failed in {repo}: {result.stderr.strip()}")
    return result.stdout


def repository_problems() -> list:
    """Why HEAD is not a version others can fetch, if it isn't. (What is
    not committed never reaches the archive, which is HEAD; uncommitted
    code that produces results is refused by the dataset's stamp check.)"""
    problems = []
    ahead = _git(ROOT, "rev-list", "--count", "@{u}..HEAD").strip()
    if ahead != "0":
        problems.append(f"This repository has {ahead} commit(s) not pushed: push them first.")
    return problems


def _cff(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def creators(people: list) -> list:
    """CITATION.cff authors as Zenodo creators."""
    out = []
    for p in people:
        entry = {"name": f"{p.get('family-names', '')}, {p.get('given-names', '')}".strip(", ")}
        if p.get("affiliation"):
            entry["affiliation"] = p["affiliation"]
        if p.get("orcid"):
            entry["orcid"] = str(p["orcid"]).rsplit("/", 1)[-1]
        out.append(entry)
    return out


def builds_on(repo_cff: dict) -> list:
    """The works the records build on, from CITATION.cff's ``references``
    (each with a ``doi`` or a ``url``), as Zenodo related identifiers."""
    out = []
    for ref in repo_cff.get("references") or []:
        kind = "publication" if ref.get("type") in ("book", "article", "report") else "dataset"
        if ref.get("doi"):
            out.append({"identifier": str(ref["doi"]), "relation": "references",
                        "scheme": "doi", "resource_type": kind})
        elif ref.get("url"):
            out.append({"identifier": str(ref["url"]), "relation": "references",
                        "scheme": "url", "resource_type": kind})
        else:
            raise StagingRefused(f"CITATION.cff: the reference {ref.get('title')!r} has no doi or url.")
    return out


def _link(doi: str | None, relation: str, kind: str) -> list:
    return [{"identifier": doi, "relation": relation, "scheme": "doi", "resource_type": kind}] if doi else []


def _paragraphs(*texts: str) -> str:
    return "".join(f"<p>{html.escape(' '.join(t.split()))}</p>" for t in texts if t)


def _metadata(fields: dict) -> str:
    return json.dumps({"metadata": fields}, indent=2, ensure_ascii=False) + "\n"


def parse_per_language(flag: str, values: list, example: str) -> dict:
    """``L=VALUE`` arguments (``--licence``, ``--release-version``) as {L: VALUE}."""
    out = {}
    for value in values or []:
        m = _LANG_ARG.match(value)
        if not m:
            raise StagingRefused(f"{flag} {value!r}: write it as <glottocode>=<value>, "
                                 f"e.g. {example}.")
        out[m.group(1)] = m.group(2)
    return out


def _compile(folder: Path) -> list:
    """Compile the volume in `folder`; the problems its log shows."""
    if shutil.which("latexmk") is None:
        return ["latexmk is not installed, so the report's PDF can't be made."]
    subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-quiet", "main.tex"],
                   cwd=folder, capture_output=True, text=True)
    log_path = folder / "main.log"
    if not (folder / "main.pdf").is_file() or not log_path.is_file():
        return ["The report did not compile (no main.pdf)."]
    text = log_path.read_text(encoding="utf-8", errors="replace")
    log = text.replace("\n", "")   # TeX breaks log lines at 79 characters
    problems = []
    if any(line.startswith("!") for line in text.splitlines()):
        problems.append("The report's LaTeX has errors: compile main.tex in its folder and read main.log.")
    for name in sorted(set(re.findall(r"No value named ([^\s]+)", log))):
        problems.append(f"The report cites {name}, which has no value.")
    for name in sorted(set(re.findall(r"Claim ([^\s]+) no longer holds", log))):
        problems.append(f"The report's claim on {name} no longer holds (build-chapters lists where).")
    return problems


def build(vol: str, licences: dict, out: Path, apply: bool,
          release_versions: dict | None = None) -> dict:
    """Stage the volume's records (or, without `apply`, say what it would).
    Returns {records: [folder names], refusals, notes}; raises
    StagingRefused when `apply` meets any refusal."""
    refusals = er.out_problems(out)
    release_versions = release_versions or {}
    volume, _stub = cb.read_volume(vol)
    if _stub is not None:
        raise StagingRefused(f"There is no volume {vol!r} in .papers/.")
    langs = cb.language_parts(volume["parts"])
    records = volume.get("records") or {}
    repo_cff_path = ROOT / er.CITATION
    repo_cff = _cff(repo_cff_path)
    code = versions.code_version()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    refusals += repository_problems()
    if _git(state_files.CODED_DATA, "status", "--porcelain", "--", f".papers/{vol}").strip():
        refusals.append(f"planars-data has uncommitted changes under .papers/{vol}/: commit them "
                        f"(the report is made from the committed files).")
    if not volume.get("abstract"):
        refusals.append(f".papers/{vol}/{cb.VOLUME} has no `abstract` (the record's description).")
    file_name = volume.get("file_name")
    if not file_name:
        refusals.append(f".papers/{vol}/{cb.VOLUME} has no `file_name` (what the PDF is called, "
                        f"with a date in it, e.g. constituency-typology-report-2026-11).")
    file_name = file_name or vol
    for flag, given in (("--licence", licences), ("--release-version", release_versions)):
        for L in sorted(set(given) - set(langs)):
            refusals.append(f"{flag} names {L}, which is not a language chapter of volume {vol}.")
    locks = {}
    for L in langs:
        if L not in licences:
            refusals.append(f"No licence for {get_display_name(L)}'s dataset: give --licence "
                            f"{L}=<{' or '.join(er.LICENCES)}> (the annotator's choice).")
        lock = cb.read_lock(vol, L)
        if lock is None:
            refusals.append(f"The {get_display_name(L)} chapter of volume {vol} is not built yet.")
        elif lock["code"] != code:
            refusals.append(f"The {get_display_name(L)} chapter of volume {vol} was built with code "
                            f"{lock['code']}, and this checkout is {code}: run `python -m coding "
                            f"build-chapters --volume {vol} --apply`, commit, and stage again.")
        locks[L] = lock
    by_name = {er._cff_name(p): p for p in repo_cff.get("authors") or []}
    unknown = [a for a in volume.get("authors", []) if a not in by_name]
    if unknown:
        refusals.append(f"{', '.join(unknown)} (the volume's authors) not in CITATION.cff, which has "
                        f"{', '.join(by_name)}: add them there or write the name as it does.")
    references = builds_on(repo_cff)
    keywords = list(repo_cff.get("keywords") or [])
    report_doi, software_doi = records.get(cb.RECORD_REPORT), records.get(cb.RECORD_SOFTWARE)
    unreserved = [what for what, doi in
                  [("the report", report_doi), ("the software", software_doi)]
                  + [(f"the {get_display_name(L)} dataset", records.get(L)) for L in langs] if not doi]

    with tempfile.TemporaryDirectory(prefix="zenodo_") as tmp:
        stage = Path(tmp) / "stage"
        stage.mkdir()
        names = []
        # 1. The software.
        folder = stage / "1-software"
        folder.mkdir()
        _git(ROOT, "archive", "--format=zip", f"--prefix=planars-{code}/",
             f"--output={folder / f'planars-{code}.zip'}", "HEAD")
        for name in (README, er.CITATION):   # shown on the record page
            (folder / name).write_text(_git(ROOT, "show", f"HEAD:{name}"), encoding="utf-8")
        (folder / METADATA).write_text(_metadata({
            "upload_type": "software", "title": repo_cff.get("title", "planars"), "version": code,
            "creators": creators(repo_cff.get("authors") or []),
            "description": _paragraphs(repo_cff.get("abstract", "")),
            "license": ZENODO_LICENCE[repo_cff.get("license", "MIT")], "keywords": keywords,
            "publication_date": today, "access_right": "open",
            "related_identifiers": _link(report_doi, "isDocumentedBy", "publication") + references,
        }), encoding="utf-8")
        names.append(folder.name)
        # 2. Each language's dataset.
        for L in langs:
            if L not in licences or locks.get(L) is None:
                continue
            folder = stage / f"2-dataset-{L}"
            folder.mkdir()
            release = Path(tmp) / f"release-{L}"
            try:
                # Into the temporary folder, dry run or not: --apply decides only DIR.
                summary = er.build(L, locks[L]["position"], release, apply=True,
                                   licence=licences[L],
                                   release_version=release_versions.get(L))
            except er.ReleaseRefused as e:
                refusals.append(f"{get_display_name(L)}'s dataset: {e}")
                continue
            dataset_cff = _cff(release / er.CITATION)
            lang_version = json.loads((release / er.RELEASE_RECORD).read_text(encoding="utf-8")
                                      )["stamp"]["languages"][L]["version"]
            shutil.make_archive(str(folder / f"planars-{L}-dataset-{dataset_cff['version']}"),
                                "zip", root_dir=release)
            for name in (er.README, er.CITATION):   # shown on the record page
                shutil.copy2(release / name, folder / name)
            drafts = sum(d["answers"] for d in summary["claude_drafts"])
            (folder / METADATA).write_text(_metadata({
                "upload_type": "dataset", "title": dataset_cff["title"],
                "version": dataset_cff["version"],
                "creators": creators(dataset_cff["authors"]),
                "description": _paragraphs(
                    dataset_cff["abstract"],
                    f"Release {dataset_cff['version']}: the language's annotation at "
                    f"change-log line {summary['position']} (its version "
                    f"{lang_version}, which counts edits to the "
                    f"planar and diagnostics files), with planars {code}; README.md says how to "
                    f"derive the spans "
                    f"again and check a report's numbers against these files.",
                    f"{drafts} answers drafted with Claude and not yet checked by the annotator "
                    f"are released as they are, marked in their Source column and listed in "
                    f"README.md." if drafts else ""),
                "license": ZENODO_LICENCE[licences[L]], "keywords": dataset_cff["keywords"],
                "publication_date": today, "access_right": "open",
                "related_identifiers": (_link(report_doi, "isDocumentedBy", "publication")
                                        + _link(software_doi, "references", "software")
                                        + references),
            }), encoding="utf-8")
            names.append(folder.name)
        # 3. The report.
        folder = stage / "3-report"
        folder.mkdir()
        source = Path(tmp) / vol
        for rel in _git(state_files.CODED_DATA, "ls-files", "--", f".papers/{vol}").splitlines():
            target = source / Path(rel).relative_to(f".papers/{vol}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(state_files.CODED_DATA / rel, target)
        shutil.make_archive(str(folder / f"{file_name}-source"), "zip", root_dir=source)
        compiled = _compile(source)
        refusals += compiled
        if not compiled:
            shutil.copy2(source / "main.pdf", folder / f"{file_name}.pdf")
        (folder / METADATA).write_text(_metadata({
            "upload_type": "publication", "publication_type": "report", "title": volume["title"],
            "creators": creators([by_name[a] for a in volume.get("authors", []) if a in by_name]),
            "description": _paragraphs(volume.get("abstract", ""),
                                       volume.get("author_note", "")),
            "license": ZENODO_LICENCE[REPORT_LICENCE], "keywords": keywords,
            "publication_date": today, "access_right": "open",
            "related_identifiers": (_link(software_doi, "documents", "software")
                                    + [x for L in langs
                                       for x in _link(records.get(L), "documents", "dataset")]
                                    + references),
        }), encoding="utf-8")
        names.append(folder.name)
        (stage / README).write_text(staging_readme(vol, names, unreserved), encoding="utf-8")
        result = {"records": names, "refusals": refusals, "unreserved": unreserved}
        if refusals:
            if apply:
                raise StagingRefused("\n".join(refusals))
            return result
        if apply:
            out.mkdir(parents=True, exist_ok=True)
            shutil.copytree(stage, out, dirs_exist_ok=True)
        return result


def staging_readme(vol: str, names: list, unreserved: list) -> str:
    lines = [f"# Zenodo records for volume {vol}", "",
             "Written by `python -m coding stage-zenodo` (coding/stage_zenodo.py). Each folder is",
             "one record: upload its files to a new Zenodo upload and enter metadata.json's",
             "fields (or send them through Zenodo's deposit API). An upload stays a private",
             "draft, with no DOI registered, until someone presses Publish.", "",
             "Order: the software, then each dataset, then the report, since the report",
             "prints the others' DOIs.", ""]
    lines += [f"- `{n}/`" for n in names]
    lines.append("")
    if unreserved:
        lines += ["**DOIs not yet reserved:** " + "; ".join(unreserved) + ". Make the drafts, press",
                  "\"Reserve DOI\" on each, write the DOIs into the volume's `records` in",
                  f".papers/{vol}/volume.yaml, run `python -m coding build-chapters --volume {vol} "
                  f"--apply`,", "commit, and stage again: the report then prints them and each "
                  "record's", "metadata links to the others. Upload the files from that second "
                  "staging.", ""]
    else:
        lines += ["Every DOI is reserved and printed in the report. After publishing, download",
                  "the dataset and run `python -m chapters rebuild-check` on it (the dataset's",
                  "README.md says how).", ""]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m coding stage-zenodo",
        description="Stage a volume's Zenodo records (software, each language's dataset, the "
                    "report) as folders to upload, each with its metadata. Sends nothing.")
    p.add_argument("--volume", required=True, metavar="NAME", help="the volume in .papers/")
    p.add_argument("--licence", action="append", metavar="LANG=LICENCE",
                   help=f"a language's dataset licence ({' or '.join(er.LICENCES)}); one per language")
    p.add_argument("--release-version", action="append", metavar="LANG=X.Y.Z",
                   help="a language's dataset release number, e.g. stan1293=0.0.1; one per language")
    p.add_argument("--out", required=True, metavar="DIR",
                   help="the folder to write (new or empty, outside both repositories)")
    p.add_argument("--apply", action="store_true", help="write the folder")
    return p


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    try:
        result = build(args.volume,
                       parse_per_language("--licence", args.licence, "stan1293=CC0-1.0"),
                       Path(args.out), args.apply,
                       parse_per_language("--release-version", args.release_version,
                                          "stan1293=0.0.1"))
    except (StagingRefused, cb.ChapterDataError) as e:
        sys.exit("NOT STAGED:\n  " + str(e).replace("\n", "\n  "))
    print(f"Volume {args.volume}: {', '.join(result['records'])}"
          + (f" written to {args.out}." if args.apply else "."))
    if result["unreserved"]:
        print("DOIs not yet reserved: " + "; ".join(result["unreserved"])
              + " (the staged README says what to do).")
    if result["refusals"]:
        print(f"NOT STAGED YET ({len(result['refusals'])}):")
        for r in result["refusals"]:
            print(f"  {r}")
        sys.exit(1)
    if not args.apply:
        print("Run again with --apply to write it.")


if __name__ == "__main__":
    main()
