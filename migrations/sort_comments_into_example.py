"""One-time migration: sort each class sheet's Comments cells into Example,
Comments, or nothing.

Motivation: Comments mixed three things (#318 item f, 2026-10-22): notes the
tooling wrote (`[split from PRON{P,T} …]`, `[new: pronoun-specific row …]`,
`[carried from split of …]`, 284 cells in English), Adam's example sentences
(about 70), and his questions and doubts (about 25), which nothing passed on.
The `Example` column was added before Source (schemas/planar.yaml), the
tooling stopped writing in Comments (restructure-sheets uses cell notes), and
check-comments now reports new comments daily. This sorts what is already
there, so its first report holds only Adam's own questions and notes:

- a tooling note is cleared (the archived sheets and the change log keep
  where each value came from);
- an example moves to Example (a cell holding an example and a doubt counts
  as an example, Jeff, 2026-10-22);
- a question or note stays.

Every comment must match exactly one entry below (an exact start of the
text); one that matches none or several stops the run before anything is
written. English and the synthetic test language (whose sheets hold copies
of the English comments) are sorted; Araona has none.
Run: 2026-10-22, after `update-sheets --apply` added the Example column.

Usage:
    python migrations/sort_comments_into_example.py           # dry run: every change listed
    python migrations/sort_comments_into_example.py --apply   # write them

Then:
    python -m coding import-sheets --apply --ignore-status
    python -m coding check-comments            # dry run: the first report
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gspread.utils import rowcol_to_a1  # noqa: E402

from coding import drive_door  # noqa: E402
from coding.drive import load_manifest  # noqa: E402
from coding.drive_doorway import get_doorway  # noqa: E402

LANGS = ("stan1293", "synth0001")
CLEAR, EXAMPLE, KEEP = "clear", "example", "keep"

TOOLING = (
    "[new: pronoun-specific row added alongside NP{S,A}, see issue #236]",
    "[split from PRON{P,T} — see archived sheet for prior judgment]",
    "[carried from split of 'PRON{P,T}']",
)
# Adam's questions, doubts and notes: stay in Comments.
QUESTIONS = (
    "I dont know what to do with this.",
    "I don't know what to do with this.",
    "Interesting case, so here just the inflection",
    'Arguably, "which" and "what" actually do N-combine',
    "I struggle with the test sentences here.",
    "In fact, in this case it appears to be obligatory",
    "This should not have been a possiblity to begin with",
    "Tell's me that my entry here is invalid.",
    "The answer to the final value isn't clear",
    "Interesting ... shouldn",
    "But interestingly, this part is just completely deleted.",
    "I couldn",
    "yes, but I wonder if it counts",
    "I'm not sure if this is true, a Qword",
    "The scope is limited in some way",
    "I can't get any scope differences",
    "This is actually unclear",
    "I don't understand, this one is a proform?",
    "because we can't tell if its fronted.",
    'If the test is "can it be shared independently',
    "Are we referring to flapping",
    "Flapping the first consonant of an incorporated noun",
    "This is sort of interesting",
    "actually this is very ambiguous",
)
# Example sentences and forms (some with a doubt attached): move to Example.
EXAMPLES = (
    # coreference
    "Mary, I really like her", "Who has John spoken to him", "I was dogsitting him",
    "I fact-checked it", "??I stone-cut it!!", "*then Sarah, John spoke to herself",
    "Whom has spoken to himself.", "*Then, Sarah, John saw herself",
    "Then, who has seen himself", "*Martin air-conditioned itself", "*Martin babysat himself",
    "I showed the baby to himself", "I showed her herself", "I showed her to herself",
    "To herself, I showed her",
    # free_occurrence
    "don't!",
    # metrical
    "diagnose vs. diagram", "enter vs. enrich", "exit vs. expel", "foresee vs. foreground",
    "interrogate vs. intervene", "misuse vs. misfire", "perform, permit vs. percolate",
    "program, protest vs. produce", "seperate vs. secede", "sublet, sublease vs. submerge",
    "supplicate vs. supply", "survey vs. survive", "syllabify vs. synthesize",
    "upset, uplift, uproot",
    # nonpermutability
    "Frankly, John probably didn", "John deliberately didn", "Adam didn't leave quickly",
    # phrasal_accent
    "cross-exAmine", "OVERdose (verb)", "OUTsource, OUTline",
    # proform: do_so_substitution
    "Also Martin ate sausage", "Is Martin reading the bible and John doing so too",
    "Can Martin read the bible and John do so too", "*John preached on the streeet",
    "Martin loudly criticized the pope", "Martin has criticized the sale",
    "Martin has not left wartburg castle", "Martin is hiding in Wartburg castle",
    "Martin is reading the bible and John is doing so too", "Martin air dropped supplies",
    "John gave a book to Mary", "John brought up the expert",
    # proform: vp_ellipsis
    "Also Martin drank beer", "sausage, Martin ate and Leo as well",
    "What did Martin eat, and Leo as well?", '"Is[3] Martin eating',
    "Martin could eat a lot of sausage", "John can play the piano",
    "Martin would clean up the abuses", "Leo sold indulgences",
    # segmental
    "Matt air dried his hair", "They de-escalalated", "I outacted him",
    # subspanrepetition
    "did martin borrow and read the book?", "could martin borrow the book",
    "martin carefully read the bible", "martin can read the bible and write",
    "martin would presumably eat stew", "martin might not eat stew", "martin has eaten stew",
    "under pay and cook", "*contradict and vene", "*downplay and size",
    "Martin explained and John wrote", "Martin gave Adam a bible", "John buys and Mary eats",
    "cleaned up the kitchen", "??Martin gave John an apple", "*also martin also tried",
    "did martin try to unify", "martin quickly wanted", "martin can try to eat",
    "martin would presumably try", "martin would not try", "martin has persuaded andreas",
    "martin had unfortunately persuaded", "martin was persuaded to",
    "martin is persuading andres", "*She set out to figure", "martin believed that then",
)
RULES = [(p, CLEAR) for p in TOOLING] + [(p, KEEP) for p in QUESTIONS] + \
        [(p, EXAMPLE) for p in EXAMPLES]


def classify(text: str) -> str:
    hits = {action for prefix, action in RULES if text.startswith(prefix)}
    if len(hits) != 1:
        raise ValueError(f"{'no entry' if not hits else 'several entries'} for {text!r}")
    return hits.pop()


def plan_tab(rows: List[List[str]]) -> Tuple[Dict[int, Tuple[str, str]], List[str]]:
    """{data row index: (new Example, new Comments)} for the rows that change,
    and the texts no entry places."""
    header = rows[0]
    c, e = header.index("Comments"), header.index("Example")
    changes, unplaced = {}, []
    for i, row in enumerate(rows[1:]):
        row = row + [""] * (len(header) - len(row))
        text, example = row[c].strip(), row[e].strip()
        if not text:
            continue
        try:
            action = classify(text)
        except ValueError as exc:
            unplaced.append(str(exc))
            continue
        if action == CLEAR:
            changes[i] = (example, "")
        elif action == EXAMPLE:
            changes[i] = ((f"{example}; {text}" if example else text), "")
    return changes, unplaced


def main() -> None:
    apply = "--apply" in sys.argv
    doorway = get_doorway()
    manifest = load_manifest(doorway)
    plans = []
    unplaced: List[str] = []
    for lang in LANGS:
        for class_name, info in sorted(manifest[lang].get("sheets", {}).items()):
            ss = doorway.open_spreadsheet(info["spreadsheet_id"])
            for construction in info["constructions"]:
                ws = ss.worksheet(construction)
                rows = ws.get_all_values()
                if not rows or "Comments" not in rows[0]:
                    continue
                if "Example" not in rows[0]:
                    raise SystemExit(f"{ss.title}/{ws.title} has no Example column: "
                                     f"run update-sheets --apply first")
                changes, missed = plan_tab(rows)
                unplaced += [f"{ss.title}/{ws.title}: {m}" for m in missed]
                if changes:
                    plans.append((ss, ws, rows, changes))
    for ss, ws, rows, changes in plans:
        moved = sum(1 for ex, _ in changes.values() if ex)
        print(f"{ss.title}/{ws.title}: {len(changes) - moved} tooling note(s) cleared, "
              f"{moved} moved to Example")
    if unplaced:
        print("\nNo entry places these, so nothing was written:")
        print("\n".join(f"  {u}" for u in unplaced))
        sys.exit(1)
    if not apply:
        print("\nDry run: pass --apply to write.")
        return
    for ss, ws, rows, changes in plans:
        header = rows[0]
        c, e = header.index("Comments") + 1, header.index("Example") + 1
        n = len(rows) - 1
        ex_col = [[(changes[i][0] if i in changes else (rows[i + 1] + [""] * len(header))[e - 1])]
                  for i in range(n)]
        co_col = [[(changes[i][1] if i in changes else (rows[i + 1] + [""] * len(header))[c - 1])]
                  for i in range(n)]
        with drive_door.replacing(ws, "Comments sorted: examples to Example, tooling notes "
                                      "cleared (Jeff, 2026-10-22, #318)"):
            ws.update(ex_col, f"{rowcol_to_a1(2, e)}:{rowcol_to_a1(n + 1, e)}")
            ws.update(co_col, f"{rowcol_to_a1(2, c)}:{rowcol_to_a1(n + 1, c)}")
        print(f"  written: {ss.title}/{ws.title}")


if __name__ == "__main__":
    with drive_door.running("migration sort_comments_into_example",
                            may_write="--apply" in sys.argv):
        main()
