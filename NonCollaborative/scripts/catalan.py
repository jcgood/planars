"""
Counting, enumerating, and visualizing rooted ordered trees with n leaves,
where each internal node has >=2 children (n-ary ordered trees).

The count sequence is OEIS A001003 (little Schröder numbers):
  1, 1, 3, 11, 45, 197, 903, 4279, 20793, 103049, ...  (n = 1, 2, 3, ...)

See catalan_old.py for the original exploratory code. That code computed
OEIS A007052 ("order-consecutive partitions"), which is a different sequence
that counts only trees where every internal node has at least one direct leaf
child. The two sequences agree for n=1,2,3 (both give 1, 3) but diverge at
n=4 (A007052 gives 10; A001003 gives 11). The missed tree at n=4 is
[[1,2],[3,4]], whose root has no direct leaf children.

See ../REFERENCES.md § "Counting Constituency Trees" for references on the
little Schröder numbers, their relationship to n-ary trees, and the
distinction from A007052 (order-consecutive partitions).
"""

from functools import lru_cache
import math


# ── Counting ──────────────────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def _ordered_forests(n):
    """Number of ordered non-empty sequences of trees covering n leaves."""
    if n == 0:
        return 1
    return sum(all_trees_new(j) * _ordered_forests(n - j) for j in range(1, n + 1))


@lru_cache(maxsize=None)
def all_trees_new(n):
    """Count rooted ordered trees with n ordered leaves (each internal node has >=2 children).

    Matches OEIS A007052. See catalan_old.py::all_trees() for the buggy predecessor,
    which gave 10 for n=4 (correct: 11) because it used bare (i+1) where it needed
    all_trees_new(i+1), and because its range excluded splits where one side is a single leaf.
    """
    if n == 1:
        return 1
    return sum(all_trees_new(j) * _ordered_forests(n - j) for j in range(1, n))


# ── Enumeration ───────────────────────────────────────────────────────────────

def _build_forests(lo, hi):
    """All ordered sequences of >=1 trees covering positions lo..hi.
    Returns a list of forests; each forest is a list of trees."""
    if lo > hi:
        return [[]]
    result = []
    for split in range(lo, hi + 1):
        for first in _build_trees(lo, split):
            for rest in _build_forests(split + 1, hi):
                result.append([first] + rest)
    return result


def _build_trees(lo, hi):
    """All trees over positions lo..hi.
    A tree is either an int (leaf) or a list of child trees."""
    if lo == hi:
        return [lo]
    result = []
    for split in range(lo, hi):
        for first in _build_trees(lo, split):
            for rest in _build_forests(split + 1, hi):
                result.append([first] + rest)
    return result


def enumerate_trees(n):
    """Return all rooted ordered trees with leaves labeled 1..n.

    Each tree is an int (leaf) or a list of child trees (internal node).
    Example for n=3: [1, 2, 3], [[1, 2], 3], [1, [2, 3]]
    """
    return _build_trees(1, n)


# ── Rendering helpers ─────────────────────────────────────────────────────────

def _leftmost(tree):
    if isinstance(tree, int):
        return tree
    return _leftmost(tree[0])


def _rightmost(tree):
    if isinstance(tree, int):
        return tree
    return _rightmost(tree[-1])


def _span_label(tree):
    if isinstance(tree, int):
        return str(tree)
    return f"[{_leftmost(tree)}-{_rightmost(tree)}]"


# ── Top-down ASCII renderer ───────────────────────────────────────────────────

def _render_block(tree):
    """Render a tree as a rectangular block of text.

    Returns (lines, anchor) where lines is a list of equal-width strings and
    anchor is the x-position (0-indexed) of this node's label center.
    """
    label = _span_label(tree)

    if isinstance(tree, int):
        return [label], 0

    GAP = 2

    child_renders = [_render_block(c) for c in tree]
    child_lines_list = [lines for lines, _ in child_renders]
    child_centers   = [center for _, center in child_renders]
    child_widths    = [len(lines[0]) for lines in child_lines_list]

    child_starts = []
    x = 0
    for w in child_widths:
        child_starts.append(x)
        x += w + GAP

    child_anchors = [child_starts[i] + child_centers[i] for i in range(len(tree))]
    parent_anchor = (child_anchors[0] + child_anchors[-1]) // 2
    label_start   = parent_anchor - len(label) // 2

    if label_start < 0:
        shift = -label_start
        child_starts  = [s + shift for s in child_starts]
        child_anchors = [a + shift for a in child_anchors]
        parent_anchor += shift
        label_start = 0

    total_width = max(child_starts[-1] + child_widths[-1], label_start + len(label))

    label_row = (' ' * label_start + label).ljust(total_width)

    connector = [' '] * total_width
    for anchor in child_anchors:
        if   anchor < parent_anchor: connector[anchor] = '/'
        elif anchor > parent_anchor: connector[anchor] = '\\'
        else:                        connector[anchor] = '|'
    connector_row = ''.join(connector)

    max_height = max(len(lines) for lines in child_lines_list)
    content_rows = []
    for row_idx in range(max_height):
        row = [' '] * total_width
        for i, lines in enumerate(child_lines_list):
            start = child_starts[i]
            src   = lines[row_idx] if row_idx < len(lines) else ' ' * child_widths[i]
            for j, ch in enumerate(src):
                if start + j < total_width:
                    row[start + j] = ch
        content_rows.append(''.join(row))

    all_lines = [label_row, connector_row] + content_rows
    final_width = max(len(l) for l in all_lines)
    return [l.ljust(final_width) for l in all_lines], parent_anchor


def render_tree(tree):
    """Return a top-down ASCII constituency tree (root at top, leaves at bottom)."""
    lines, _ = _render_block(tree)
    return '\n'.join(l.rstrip() for l in lines)


# ── LaTeX forest export ───────────────────────────────────────────────────────

def to_forest(tree):
    """Return a forest-package expression for the tree.

    Paste inside a forest environment:
        \\begin{forest}
          <result>
        \\end{forest}
    """
    if isinstance(tree, int):
        return f"[{tree}]"
    label    = _span_label(tree)
    children = " ".join(to_forest(c) for c in tree)
    return f"[{label} {children}]"


def forest_document(tree):
    """Return a compilable standalone LaTeX document containing the tree."""
    return (
        "\\documentclass{standalone}\n"
        "\\usepackage{forest}\n"
        "\\begin{document}\n"
        "\\begin{forest}\n"
        f"  {to_forest(tree)}\n"
        "\\end{forest}\n"
        "\\end{document}"
    )


# ── Comparison with old buggy all_trees() ─────────────────────────────────────

def _has_all_internal_children(tree):
    """True if this node is internal and every child is also internal (no leaf children)."""
    if isinstance(tree, int):
        return False
    return all(not isinstance(c, int) for c in tree)


def _is_potentially_missed(tree):
    """True if tree contains any node with all-internal children.

    The old all_trees() recurrence only built trees where at least one child
    at each level is a direct leaf; it could not produce trees with this structure.
    """
    if isinstance(tree, int):
        return False
    if _has_all_internal_children(tree):
        return True
    return any(_is_potentially_missed(c) for c in tree)


def show_missing(n):
    """Print all n-leaf trees as ASCII, flagging those the old all_trees() missed."""
    trees     = enumerate_trees(n)
    old_count = all_trees_old(n)
    new_count = all_trees_new(n)
    print(f"n={n}: all_trees_new={new_count}, all_trees (buggy)={old_count}, "
          f"missed={new_count - old_count}")
    print()
    for i, tree in enumerate(trees, 1):
        missed = _is_potentially_missed(tree)
        marker = "  <-- MISSED BY OLD all_trees()" if missed else ""
        print(f"── Tree {i}/{new_count}{marker}")
        print(render_tree(tree))
        print()


# ── Legacy: old buggy counter (kept for reference / comparison) ───────────────

def all_trees_old(n):
    """BUGGY. Original all_trees() from catalan_old.py, kept for comparison.

    Gives wrong results for n>=4 (e.g., 10 instead of 11 for n=4).
    Two bugs: (1) uses bare (i+1) instead of all_trees_new(i+1);
    (2) range(1, n-1) excludes splits where one side is a single leaf.
    """
    if n < 2:
        return 0
    elif n == 2:
        return 1
    else:
        internalSum = 1
        for i in range(1, n - 1):
            internalSum += (i + 1) * all_trees_old(n - i)
        return internalSum


# ── Legacy: binary-only tree generator (from StackOverflow, kept for reference) ─

def _gen_trees_binary(a, b):
    """Generate all binary trees by combining left and right subtrees."""
    return [[l, r] for l in _gen_all_trees_binary(a) for r in _gen_all_trees_binary(b)]


def _gen_all_trees_binary(items):
    """Generate all binary trees over items (binary branching only, not n-ary).

    Counts match Catalan numbers, not A007052.
    Source: https://stackoverflow.com/questions/31874784
    """
    if len(items) == 1:
        return [items[0]]
    return [t for i in range(len(items) - 1, 0, -1)
            for t in _gen_trees_binary(items[:i], items[i:])]


# ── Legacy: closed-form formula attempt (unverified, from OEIS via Copilot) ──

def OCPSplus(n):
    """Attempt at a closed-form formula for A007052 from the OEIS paper.

    NOTE: Does not give correct results — misapplies the formula.
    Kept for reference only.
    """
    total_sum = 0
    for p in range(1, n + 1):
        inner_sum = 0
        for k in range(p):
            term = ((-1) ** (p - 1 - k)
                    * math.comb(p - 1, k)
                    * math.comb(n + 2 * k - 1, 2 * k))
            inner_sum += term
        total_sum += inner_sum
    return total_sum


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Count comparison table
    a007052 = [1, 1, 3, 11, 45, 197, 903, 4279, 20793, 103049]
    print("n   all_trees_new   all_trees_old   A007052   correct?")
    print("-" * 54)
    for n in range(1, 11):
        new = all_trees_new(n)
        old = all_trees_old(n)
        ref = a007052[n - 1]
        ok  = "✓" if new == ref else "✗"
        print(f"{n:2d}  {new:13d}   {old:13d}   {ref:7d}   {ok}")

    print()

    # Show all 11 trees for n=4 with the missing one flagged
    show_missing(4)

    # LaTeX example for the missing tree [[1,2],[3,4]]
    missing = [[1, 2], [3, 4]]
    print("── LaTeX forest output for the missed tree [[1,2],[3,4]]:")
    print(forest_document(missing))
