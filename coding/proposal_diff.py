"""The three-way comparison behind a proposal sheet (Phase 10 unit 11a;
docs/ownership-design.md § 3.4).

A proposal tab is compared row by row, in order (the way ``diff`` compares
lines), across three versions of the same grid:

- the **base**, what the tab was last filled with;
- the **sheet**, the tab as the annotator left it;
- the **source**, what the planar or diagnostics file renders to today.

The annotator's proposal is how the sheet differs from the base; the
coordinator's own edits since are how the source differs from it. Rows are
matched in order rather than by position number, since a proposal that adds
a position renumbers every position after it.

``three_way`` sorts each stretch of rows into one of four cases: unchanged;
changed only in the source (taken into the sheet, so a refill never undoes a
coordinator's edit and never loses a proposal); changed only in the sheet
(the proposal); changed in both, the same way (taken) or differently (a
**conflict**: the sheet keeps the annotator's version, the base the old one,
and the review shows all three). ``describe`` puts a change in plain words.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import List, Optional, Sequence, Tuple

Grid = List[List[str]]
Row = Tuple[str, ...]


def normal(grid: Sequence[Sequence[str]]) -> List[Row]:
    """``grid`` as compared: cells stripped, trailing blanks and trailing
    blank rows dropped (Sheets returns a grid with neither)."""
    rows = [[str(v).strip() for v in r] for r in grid]
    rows = [r[:max((i + 1 for i, v in enumerate(r) if v), default=0)] for r in rows]
    while rows and not rows[-1]:
        rows.pop()
    return [tuple(r) for r in rows]


@dataclass(frozen=True)
class Hunk:
    """One stretch of rows: ``base[lo:hi]`` became ``rows``."""
    lo: int
    hi: int
    rows: Tuple[Row, ...]


@dataclass(frozen=True)
class Conflict:
    """A stretch both sides changed differently. ``ours`` (the sheet's) and
    ``theirs`` (the source's) are against the old base; in the new base the
    stretch still holds the old rows, from row ``at``."""
    ours: Hunk
    theirs: Hunk
    at: int

    @property
    def span(self) -> Tuple[int, int]:
        """Where the stretch sits in the new base."""
        return self.at, self.at + (self.ours.hi - self.ours.lo)


@dataclass
class Merge:
    sheet: List[Row]                 # the sheet, with the source's own changes taken in
    base: List[Row]                  # the base, with the same changes taken in
    proposal: List[Hunk] = field(default_factory=list)   # against the new base
    conflicts: List[Conflict] = field(default_factory=list)
    source_changes: int = 0          # stretches taken in from the source

    @property
    def refreshed(self) -> bool:
        return self.source_changes > 0


def hunks(base: Sequence[Row], other: Sequence[Row]) -> List[Hunk]:
    """Where ``other`` differs from ``base``, in base coordinates."""
    sm = SequenceMatcher(None, list(base), list(other), autojunk=False)
    return [Hunk(i1, i2, tuple(other[j1:j2]))
            for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]


def _version(base: Sequence[Row], own: List[Hunk], lo: int, hi: int) -> Tuple[Row, ...]:
    """base[lo:hi] with ``own``'s hunks (all inside it) applied."""
    out: List[Row] = []
    at = lo
    for h in own:
        out.extend(base[at:h.lo])
        out.extend(h.rows)
        at = h.hi
    out.extend(base[at:hi])
    return tuple(out)


def three_way(base: Sequence[Row], sheet: Sequence[Row], source: Sequence[Row]) -> Merge:
    """Merge the source's changes into the sheet, keeping the annotator's."""
    a, b = hunks(base, sheet), hunks(base, source)
    tagged = sorted([(h.lo, h.hi, 0, h) for h in a] + [(h.lo, h.hi, 1, h) for h in b],
                    key=lambda t: (t[0], t[1], t[2]))
    # Changes that overlap or touch form one stretch, as in diff3 and git:
    # two edits to neighbouring rows are read together, not merged blind.
    groups: List[Tuple[int, int, List[Hunk], List[Hunk]]] = []
    for lo, hi, who, h in tagged:
        if groups and lo <= groups[-1][1]:
            g_lo, g_hi, ga, gb = groups[-1]
            groups[-1] = (g_lo, max(g_hi, hi), ga, gb)
        else:
            groups.append((lo, hi, [], []))
        (groups[-1][2] if who == 0 else groups[-1][3]).append(h)

    new_sheet: List[Row] = []
    new_base: List[Row] = []
    merge = Merge([], [])
    at = 0
    for lo, hi, ga, gb in groups:
        new_sheet.extend(base[at:lo])
        new_base.extend(base[at:lo])
        ours, theirs = _version(base, ga, lo, hi), _version(base, gb, lo, hi)
        old = tuple(base[lo:hi])
        if not gb:                              # the annotator's alone
            new_sheet.extend(ours)
            new_base.extend(old)
        elif not ga or ours == theirs:          # the source's alone, or the same change
            new_sheet.extend(theirs)
            new_base.extend(theirs)
            merge.source_changes += 1
        else:                                   # both, differently
            merge.conflicts.append(Conflict(Hunk(lo, hi, ours), Hunk(lo, hi, theirs),
                                            len(new_base)))
            new_sheet.extend(ours)
            new_base.extend(old)
        at = hi
    new_sheet.extend(base[at:])
    new_base.extend(base[at:])
    merge.sheet, merge.base = new_sheet, new_base
    merge.proposal = hunks(new_base, new_sheet)
    return merge


@dataclass
class Comparison:
    """A proposal tab compared (``compare``)."""
    sheet: List[Row]                 # what the tab should now hold (reasons kept)
    base: List[Row]                  # what to save as its base
    changes: List[Hunk]              # the proposal, against ``base``: reason-only rows
                                     # and the conflicts' stretches left out
    conflicts: List[Conflict]
    refreshed: bool                  # the source's changes were taken in
    old_base: List[Row]              # the base compared against, reasons set aside


def compare(base: Sequence[Sequence[str]], sheet: Sequence[Sequence[str]],
            source: Sequence[Sequence[str]], note_column: str) -> Comparison:
    """Compare one proposal tab. The rows are compared with the annotator's
    reasons (``note_column``) set aside, so a change the coordinator has
    made in the source too counts as agreed, not as a conflict; the reasons
    then go back on the rows they were written on."""
    base_rows, sheet_full, source_rows = normal(base), normal(sheet), normal(source)
    header = list(base_rows[0]) if base_rows else (list(sheet_full[0]) if sheet_full else [])

    def bare(rows):     # the header row is compared whole: it names the column
        return rows[:1] + [without(r, header, note_column) for r in rows[1:]]

    sheet_bare, old_base = bare(sheet_full), bare(base_rows)
    merge = three_way(old_base, sheet_bare, bare(source_rows))
    merged = _with_reasons(merge.sheet, sheet_bare, sheet_full, header, note_column)
    spans = [c.span for c in merge.conflicts]
    changes = [h for h in hunks(merge.base, merged)
               if not note_only(header, merge.base, h, note_column)
               and not any(h.lo <= end and start <= h.hi for start, end in spans)]
    return Comparison(merged, merge.base, changes, merge.conflicts, merge.refreshed, old_base)


def apply(base: Sequence[Row], edits: Sequence[Tuple[int, int, Sequence[Row]]]) -> List[Row]:
    """``base`` with each edit ``(lo, hi, rows)`` replacing base[lo:hi].
    The edits must not overlap."""
    out: List[Row] = []
    at = 0
    for lo, hi, rows in sorted(edits, key=lambda e: (e[0], e[1])):
        if lo < at:
            raise ValueError(f"edits overlap at row {lo + 1}")
        out.extend(base[at:lo])
        out.extend(tuple(r) for r in rows)
        at = hi
    out.extend(base[at:])
    return out


def _with_reasons(merged: Sequence[Row], sheet_bare: Sequence[Row], sheet_full: Sequence[Row],
                  header: Sequence[str], note_column: str) -> List[Row]:
    """``merged`` with each row's reason copied back from the sheet row it
    came from (matched in order)."""
    if note_column not in header:
        return list(merged)
    at = header.index(note_column)
    out = [list(r) for r in merged]
    sm = SequenceMatcher(None, list(sheet_bare), list(merged), autojunk=False)
    for block in sm.get_matching_blocks():
        for k in range(block.size):
            full = sheet_full[block.a + k]
            reason = full[at] if at < len(full) else ""
            if reason:
                row = out[block.b + k]
                row.extend([""] * (at + 1 - len(row)))
                row[at] = reason
    return [tuple(r) for r in out]


# ---------------------------------------------------------------------------
# In plain words
# ---------------------------------------------------------------------------

def label(header: Sequence[str], row: Sequence[str]) -> str:
    """How a person names a row: its position, or its class."""
    rec = dict(zip(header, row))
    if rec.get("Position"):
        return f"position {rec['Position']} `{rec.get('Position_Name', '')}`"
    if rec.get("Class"):
        return f"class `{rec['Class']}`"
    return "a row"


def without(row: Sequence[str], header: Sequence[str], column: Optional[str]) -> Row:
    """``row`` with ``column``'s cell blanked, trailing blanks dropped."""
    if column not in header:
        return tuple(row)
    i = header.index(column)
    cells = [("" if j == i else v) for j, v in enumerate(row)]
    while cells and not cells[-1]:
        cells.pop()
    return tuple(cells)


def note_only(header: Sequence[str], base: Sequence[Row], hunk: Hunk,
              note_column: Optional[str]) -> bool:
    """Whether the hunk only writes reasons: the same rows, differing only in
    the note column. Not a proposal: nothing would change in the source."""
    old = base[hunk.lo:hunk.hi]
    return len(old) == len(hunk.rows) and all(
        without(o, header, note_column) == without(n, header, note_column)
        for o, n in zip(old, hunk.rows))


def describe(header: Sequence[str], base: Sequence[Row], hunk: Hunk,
             note_column: Optional[str] = None) -> List[str]:
    """One line per row the hunk changes, adds or removes. ``note_column``
    is the annotator's reason (What changed?), quoted at the end of each line
    and left out of the cells compared."""
    note = header.index(note_column) if note_column in header else None

    def cells(row: Sequence[str]) -> List[Tuple[str, str]]:
        return [(header[i] if i < len(header) else f"column {i + 1}", v)
                for i, v in enumerate(row) if i != note]

    def why(row: Sequence[str]) -> str:
        text = row[note] if note is not None and note < len(row) else ""
        return f" — *{text}*" if text else ""

    old, new = list(base[hunk.lo:hunk.hi]), list(hunk.rows)
    lines = []
    if hunk.lo == 0 and old:
        if not new or new[0] != old[0]:
            lines.append("the header row changed: "
                         + (" | ".join(new[0]) if new else "(removed)"))
        old, new = old[1:], new[1:]
        hunk = Hunk(1, hunk.hi, tuple(new))
    for o, n in zip(old, new):
        before, after = dict(cells(o)), dict(cells(n))
        diffs = [f"{c} {before.get(c, '')!r} → {after.get(c, '')!r}"
                 for c in dict.fromkeys(list(before) + list(after))
                 if before.get(c, "") != after.get(c, "")]
        lines.append(f"{label(header, o)}: " + ("; ".join(diffs) or "reason added") + why(n))
    after_row = base[hunk.lo - 1] if hunk.lo > 0 else None
    where = f"after {label(header, after_row)}" if after_row and hunk.lo > 1 else "at the top"
    for n in new[len(old):]:
        shown = ", ".join(f"{c} {v!r}" for c, v in cells(n) if v)
        lines.append(f"row added {where}: {shown}{why(n)}")
    for o in old[len(new):]:
        lines.append(f"{label(header, o)} removed")
    return lines
