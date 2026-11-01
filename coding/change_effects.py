"""What a change to a source did: how many answered cells it broke and whose
spans it moved. Measured, never declared (Phase 10 unit 17;
docs/change-log-design.md § 4.3).

``measure(before)`` compares two copies of the project. *After* is the
project as it stands. *Before* is the same with each file in ``before``
put back as it was (``{path: text}``, ``None`` for a file that did not
exist): the sources a hand edit changed (``log-change``), or every language
file a command changed (the local-file door, when the command ends). Each
copy holds the code, ``schemas/`` and every language's folder (archive and
records left out), in a temporary folder; the real files are never touched.
For a schema edit, ``log-change`` also takes the *before* copy's
``planars/`` from the last commit (``code_from``), so a span rule logged
with its module change, before they are committed, shows the spans the
two move together (Jeff, 2026-10-31: a change that moves results is
breaking).
This module is run in each copy (``python -m coding.change_effects``, from
the copy), so every cache and schema read comes from that copy, and prints
what it finds as JSON:

- for each language, class and criterion column, how many answered cells
  are valid (the tab's criteria from the diagnostics file and schema, each
  cell checked by ``validate_coding.local_tab_issues``, the checks
  validate-coding runs);
- for each language and class, a hash of each span-producing tab's spans,
  as ``generate_snapshots.py`` writes them (the title left out, so a
  renamed construction with the same spans has not moved).

**Answers broken** is, per language, the sum over class and column of the
valid answered cells lost (before minus after, when positive): an answer
that is now invalid, or whose column is no longer a criterion. A language
whose diagnostics file no longer reads has no valid answer, so all of them
count. Counting by
column rather than by cell means a construction renamed with its answers
breaks nothing. **Spans moved** names each language and class whose span
hashes differ. ``Effects`` holds both and writes the change-log cells.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional

ROOT = Path(__file__).resolve().parent.parent
# What each copy of the project holds besides the language folders: the
# code the measurement imports and the definition files it reads.
CODE = ("planars", "coding", "schemas", "chapters", "laminar", "generate_snapshots.py")
# Inside a language folder, what the measurement never reads.
LEFT_OUT = ("archive", "records")
UNKNOWN = "unknown"


@dataclass
class Effects:
    """A change's effects. ``broken``: answers broken per language;
    ``moved``: per language, the classes whose spans moved. ``failure``:
    why they could not be measured (then nothing else is known)."""
    broken: Dict[str, int] = field(default_factory=dict)
    moved: Dict[str, List[str]] = field(default_factory=dict)
    failure: str = ""

    @classmethod
    def unknown(cls, why: str) -> "Effects":
        return cls(failure=" ".join(why.split())[:200] or "no reason given")

    @property
    def answers(self) -> Optional[int]:
        return None if self.failure else sum(self.broken.values())

    def answers_cell(self) -> str:
        """``0``; ``15 (stan1293 12; synth0001 3)``; or ``unknown (why)``."""
        if self.failure:
            return f"{UNKNOWN} ({self.failure})"
        total = self.answers
        if not total:
            return "0"
        parts = "; ".join(f"{lang} {n}" for lang, n in sorted(self.broken.items()) if n)
        return f"{total} ({parts})"

    def spans_cell(self) -> str:
        """``stan1293: metrical, proform; synth0001: metrical``, or empty."""
        if self.failure:
            return f"{UNKNOWN} ({self.failure})"
        return "; ".join(f"{lang}: {', '.join(classes)}"
                         for lang, classes in sorted(self.moved.items()) if classes)

    @property
    def breaking(self) -> bool:
        """Breaking (§ 6.1): answers broken, spans moved, or not known."""
        return bool(self.failure or self.answers or self.spans_cell())


def answers_broken(cell: str) -> Optional[int]:
    """The number in an ``answers broken`` cell: None for unknown or empty."""
    head = (cell or "").split(" ", 1)[0]
    return int(head) if head.isdigit() else None


# ---------------------------------------------------------------------------
# Comparing two copies
# ---------------------------------------------------------------------------

def measure(before: Mapping[Path, Optional[str]], coded_data: Optional[Path] = None,
            code_from: Optional[str] = None) -> Effects:
    """The effects of the project going from ``before`` to how it stands.
    With ``code_from`` (a git revision of this repository, e.g. ``HEAD``),
    the *before* copy's analysis code (``planars/``) is taken from it: a
    span rule's schema edit and its module change measured as one change."""
    from . import file_door
    coded = coded_data or file_door.CODED_DATA
    with tempfile.TemporaryDirectory(prefix="planars-effects-") as tmp:
        old_tree = _copy(Path(tmp) / "before", coded, before)
        if code_from:
            _code_at(old_tree, code_from)
        old = _snapshot(old_tree)
        new = _snapshot(_copy(Path(tmp) / "after", coded, {}))
    return compare(old, new)


def _code_at(tree: Path, revision: str) -> None:
    """Replace the copy's ``planars/`` with this repository's at ``revision``."""
    import tarfile
    done = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", revision,
                           "planars"], capture_output=True)
    if done.returncode != 0:
        raise RuntimeError(f"could not read planars/ at {revision}: "
                           f"{done.stderr.decode(errors='replace').strip()}")
    shutil.rmtree(tree / "planars")
    with tarfile.open(fileobj=io.BytesIO(done.stdout)) as archive:
        archive.extractall(tree, filter="data")


def compare(old: Dict, new: Dict) -> Effects:
    """The effects between two snapshots (``_measure_here``'s JSON)."""
    broken: Dict[str, int] = {}
    for lang in sorted(set(old["valid"]) | set(new["valid"])):
        a, b = old["valid"].get(lang, {}), new["valid"].get(lang, {})
        lost = sum(max(0, n - b.get(key, 0)) for key, n in a.items())
        if lost:
            broken[lang] = lost
    moved: Dict[str, List[str]] = {}
    for lang in sorted(set(old["spans"]) | set(new["spans"])):
        a, b = old["spans"].get(lang, {}), new["spans"].get(lang, {})
        classes = sorted(c for c in set(a) | set(b) if sorted(a.get(c, [])) != sorted(b.get(c, [])))
        if classes:
            moved[lang] = classes
    return Effects(broken, moved)


def _copy(dest: Path, coded: Path, before: Mapping[Path, Optional[str]]) -> Path:
    """A copy of the project at ``dest``, with ``before``'s files put back."""
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for name in CODE:
        src = ROOT / name
        if src.is_dir():
            shutil.copytree(src, dest / name, ignore=ignore)
        elif src.exists():
            shutil.copy2(src, dest / name)
    data = dest / "coded_data"
    data.mkdir(parents=True)
    if coded.is_dir():
        for lang in sorted(p for p in coded.iterdir() if p.is_dir() and not p.name.startswith(".")):
            shutil.copytree(lang, data / lang.name, ignore=shutil.ignore_patterns(*LEFT_OUT))
        for f in coded.iterdir():
            if f.is_file() and f.suffix == ".yaml":   # people.yaml
                shutil.copy2(f, data / f.name)
    for path, text in before.items():
        path = Path(path).resolve()
        if path.is_relative_to(coded.resolve()):
            target = data / path.relative_to(coded.resolve())
        elif path.is_relative_to(ROOT):
            target = dest / path.relative_to(ROOT)
        else:
            raise ValueError(f"{path} is neither in the project nor in planars-data")
        if text is None:
            target.unlink(missing_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="") as f:
                f.write(text)
    return dest


def _snapshot(tree: Path) -> Dict:
    """Run the measurement inside ``tree`` and read what it prints."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONSAFEPATH", "PYTHONPATH")}
    env["PYTHONPATH"] = str(tree)
    done = subprocess.run([sys.executable, "-m", "coding.change_effects"], cwd=tree, env=env,
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"measuring in a copy of the project failed: "
                           f"{(done.stderr or done.stdout).strip()[-1500:]}")
    return json.loads(done.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------------------
# Inside one copy
# ---------------------------------------------------------------------------

def _answered(rows: List[List[str]], column: str) -> List[int]:
    """The row numbers (sheet numbering, header = 1) with ``column`` filled."""
    if not rows or column not in rows[0]:
        return []
    i = rows[0].index(column)
    return [n for n, r in enumerate(rows[1:], start=2) if i < len(r) and str(r[i]).strip()]


def _valid_counts(coded: Path) -> Dict[str, Dict[str, int]]:
    """Per language, ``class/column`` → valid answered cells."""
    from planars.layout import ARCHIVE_FOLDER, RECORDS_FOLDER, SETUP_FOLDER
    from . import validate_coding as vc
    from .restructure_sheets import _get_keyed_row_constructions, _get_pair_row_constructions
    pair_rows, keyed_rows = _get_pair_row_constructions(), _get_keyed_row_constructions()
    out: Dict[str, Dict[str, int]] = {}
    for lang_dir in sorted(p for p in coded.iterdir() if p.is_dir() and not p.name.startswith(".")):
        lang = lang_dir.name
        counts: Dict[str, int] = {}
        out[lang] = counts
        try:
            param_map = vc._load_param_map(lang)
        except Exception as exc:  # a file that no longer reads leaves no answer valid
            print(f"{lang}: the diagnostics file could not be read: {exc}", file=sys.stderr)
            continue
        for class_dir in sorted(p for p in lang_dir.iterdir() if p.is_dir()):
            if class_dir.name in (SETUP_FOLDER, ARCHIVE_FOLDER, RECORDS_FOLDER):
                continue
            for tsv in sorted(class_dir.glob("*.tsv")):
                info = param_map.get(class_dir.name, {}).get(tsv.stem)
                if not info:
                    continue    # not a tab the diagnostics file has: no criteria
                with open(tsv, encoding="utf-8", newline="") as f:
                    rows = list(csv.reader(f, delimiter="\t"))
                issues = vc.local_tab_issues(lang, class_dir.name, tsv.stem, info,
                                             pair_rows, keyed_rows, rows=[list(r) for r in rows])
                header = rows[0] if rows else []
                bad = {(i.cell[0] + 1, header[i.cell[1]]) for i in issues
                       if i.cell is not None and i.kind == vc.INVALID and i.cell[1] < len(header)}
                for column in info.get("params", []):
                    good = [n for n in _answered(rows, column) if (n, column) not in bad]
                    if good:
                        key = f"{class_dir.name}/{column}"
                        counts[key] = counts.get(key, 0) + len(good)
    return out


def _span_hashes() -> Dict[str, Dict[str, List[str]]]:
    """Per language and class, a hash of each span-producing tab's spans."""
    import generate_snapshots as gs
    out: Dict[str, Dict[str, List[str]]] = {}
    for tsv, derive, fmt in gs.TASKS:
        try:
            body = fmt(derive(tsv, strict=False))
        except Exception as exc:   # a tab whose spans can't be derived differs from one whose can
            body = f"could not derive: {type(exc).__name__}: {exc}"
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
        out.setdefault(tsv.parent.parent.name, {}).setdefault(tsv.parent.name, []).append(digest)
    return out


def _measure_here() -> Dict:
    from . import validate_coding as vc
    with _quiet():
        return {"valid": _valid_counts(vc.CODED_DATA), "spans": _span_hashes()}


class _quiet:
    """Send what the checks print to stderr, so stdout holds only the JSON."""
    def __enter__(self):
        self._out, sys.stdout = sys.stdout, sys.stderr

    def __exit__(self, *exc):
        sys.stdout = self._out


if __name__ == "__main__":
    print(json.dumps(_measure_here()))
