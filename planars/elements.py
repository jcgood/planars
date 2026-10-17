"""How a planar's Elements cell is read, for both planars/ and coding/.

Until 2026-10-16 the brace-aware split was written out in four files and the
bracket rule in five (found closing hidden-facts D2b/M0); a change to either
convention had to be made everywhere at once or the sheets and the analyses
would name elements differently.
"""
from __future__ import annotations

from typing import List


def split_elements(raw: str) -> List[str]:
    """Split a comma-separated Elements cell, ignoring commas inside braces,
    stripping each element and dropping empty ones.

    E.g. 'QWORDS, NP{S,A,P}' -> ['QWORDS', 'NP{S,A,P}']
    """
    parts: List[str] = []
    current: List[str] = []
    depth = 0
    for ch in raw or "":
        if ch == "{":
            depth += 1
            current.append(ch)
        elif ch == "}":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def wrap_element(element: str) -> str:
    """An element as every sheet shows it: stripped, and bracketed if it
    starts or ends with a hyphen (planar.yaml's Element convention; Sheets
    would otherwise read '-ing' as a formula)."""
    element = str(element).strip()
    return f"[{element}]" if (element.startswith("-") or element.endswith("-")) else element
