"""Cells that refer to planar positions: reading them and renumbering them.

Some criteria take positions as their answer: co_exponents and conditioned_by
(biuniqueness_deviations, ``<position_names>``) and dependent-on-left/right
(free_occurrence, ``<position_number>``). Annotators write a position by its
number (``31``) or its name (``v:verbinflection``), several separated by
commas; numbers are what they see in the planar and are quicker to type
(Jeff, 2026-10-22).

A number only means something against the planar it was typed with, so two
things live here, used by everything that reads or rewrites such a cell:

- ``as_names``: the positions a cell names, numbers turned into names with the
  current planar. What the tooling builds from a cell (a morpheme label, a
  span) uses names, which no renumbering changes.
- ``renumber``: a cell rewritten from one numbering to another, matched by
  position name. import-planar runs it on every class sheet when the planar's
  numbers shift, so a typed ``31`` becomes ``32`` when a position is inserted
  before it. A number whose position is gone is left as typed and reported.

A number is a run of digits standing alone: the ``1`` in ``v:neg1`` is part
of a name, never a number.
"""
from __future__ import annotations

import re
from typing import List, Mapping, Tuple

_NUMBER = re.compile(r"(?<![\w:])(\d+)(?![\w:])")


def split_positions(cell) -> List[str]:
    """The comma-separated items of a cell, stripped; blank for an empty cell."""
    return [p.strip() for p in str(cell or "").split(",") if p.strip()]


def as_names(cell, number_to_name: Mapping[int, str]) -> Tuple[List[str], List[str]]:
    """(position names, items that are no position) for a cell's items, in
    order. An item is a position if it is a name in ``number_to_name`` or a
    number it holds; a number is given as its name."""
    known = set(number_to_name.values())
    names: List[str] = []
    unknown: List[str] = []
    for item in split_positions(cell):
        if item in known:
            names.append(item)
        elif item.isdigit() and int(item) in number_to_name:
            names.append(number_to_name[int(item)])
        else:
            unknown.append(item)
    return names, unknown


def renumber(cell, old_number_to_name: Mapping[int, str],
             new_name_to_number: Mapping[str, int]) -> Tuple[str, List[int]]:
    """``cell`` with each number rewritten from the old numbering to the new,
    matched by position name, and the numbers that could not be (their
    position is not in the new planar, or was never in the old one). Those,
    names and anything else are left exactly as typed."""
    unresolved: List[int] = []

    def swap(m: "re.Match") -> str:
        n = int(m.group(1))
        name = old_number_to_name.get(n)
        if name is None or name not in new_name_to_number:
            unresolved.append(n)
            return m.group(1)
        return str(new_name_to_number[name])

    return _NUMBER.sub(swap, str(cell or "")), unresolved
