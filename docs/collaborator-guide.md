# Collaborator guide

This guide is for annotators filling in Google Sheets as part of the planars project. No programming experience or command-line access is required for the core annotation workflow.

If you want to understand more about how the results are computed or how to validate your own work independently, see the [Advanced](#advanced-running-the-validation-notebook-yourself) section at the bottom.

---

## Quick start

### What you will be doing

You have been given a link to a Google Sheets annotation form for one or more languages and analysis classes. Each sheet has one tab per construction. Your job is to fill in the criterion cells — typically `y` (yes) or `n` (no) — for each element in the planar structure.

The cells you fill in describe grammatical properties of the elements: whether they can be separated by pauses, whether they permute, whether they are freely occurring, and so on. The project coordinator will have explained what each diagnostic criterion means for your language. You can also consult the Comments column in each tab if your coordinator has left notes, or add your own.

### Opening your sheet

Your coordinator will share a Google Sheets link with you. Open it in a browser — it works like any Google Sheet. You do not need to install anything.

### Filling in values

Each criterion column has a dropdown validation list. Click a cell and use the dropdown, or type the value directly. Most criteria accept `y` or `n`; some accept additional values such as `both` or `?`. The allowed values are listed in the dropdown — entering anything else will trigger a validation warning (the cell will turn pink).

A few rules:
- **Keystone row** (`v:verbstem`): Pre-filled with `NA`. Do not change these cells.
- **Blank cells**: Leave blank if you have not yet annotated this element. Blanks appear as warnings when the coordinator imports the data and are excluded from span computations.
- **`?`**: Use `?` (not a blank) when you have consulted the source and genuinely cannot determine the value. A `?` is a positive annotation of uncertainty — it tells the coordinator "I looked and could not decide", which is different from "I have not looked yet". Both are flagged on import, but they mean different things for the record.
- **Example column**: the forms or sentences that show your answer (`*Martin babysat himself`, `diagnose vs. diagram`). For most languages it is followed by **Gloss** and **Translation** (details below).
- **Source column**: page or section references that justify your answer (`§4.3`, `p. 217`).
- **Comments column**: anything you want the coordinator to see — a question, a doubt about a value, something the columns can't express. New comments are passed to the coordinator each day. (Details below.)

### When a construction is finished

Every sheet has a **Status** tab (the last tab), with one row per construction. When you have finished a construction, set its **Status** to `ready-for-review`.

A day later, look at that row's **Needs fixing** column. It lists every value on that tab that isn't allowed, one per line, for example:

> row 125 (KEYSTONE), independence: 'n' — should be 'na'

Correct each one on the construction's tab (the cell is also pink there). The line disappears within a day of the fix, and the column is blank when nothing needs fixing. You do not need to change the Status back while you fix things.

While a construction is still `in-progress`, nothing is listed there: wrong values are only highlighted pink.

Your language's read-only status page (`status_{lang_id}`, in the "Annotation Status" folder shared with you) shows how much of each construction is filled in. It is rebuilt once a day, and its second line says when, so edits you made after that time aren't counted yet.

### Suggesting changes to the planar structure or the diagnostics

The `planar_{lang_id}` and `diagnostics_{lang_id}` sheets in your language's folder are read-only: they show the current planar structure and diagnostics. To change either, use the sheet called "*your language* planars and diagnostics" (for English, "English [stan1293] planars and diagnostics"). It is for editing, and has four tabs:

- **Instructions**: what the sheet is for and how to use it.
- **Last review**: the outcome of the last time the coordinator reviewed your changes.
- **Planar** and **Diagnostics**: copies of the planar structure (the positions and their elements) and the diagnostics (which classes, constructions and criteria apply), with a **What changed?** column at the end.

To suggest a change, edit the Planar or Diagnostics tab as you would like it to be: change a cell, add a row, or delete one. Then say why in that row's **What changed?** cell. A deleted row takes its cell with it, so give the reason for a deletion on the row just above it. For a new position, add its row where it belongs and renumber the positions after it. Give the reason on the new row; the renumbered rows don't need one.

Nothing else changes while you edit: your annotation sheets stay as they are. Within a day a GitHub issue titled "Changes suggested — " and the sheet's name lists each change you made and your reasons. The coordinator then accepts or declines each one. Then:

- The accepted changes go into the planar structure and diagnostics. The tabs are filled again from the new versions, so your edits disappear from them. A declined change goes back to how it was.
- **Last review** lists what was accepted, what was not and why, and the issue closes.
- If an accepted change affects your annotation sheets (a new position or a new class, say), the coordinator updates those sheets.

If the coordinator edits the planar or diagnostics while your changes are waiting, their change is copied into the tabs without touching yours. If you both changed the same row in different ways, the issue says so, and the coordinator decides which version to keep.

### Viewing your results

Once your coordinator has imported your filled sheet, results appear in your contributor Colab notebook. Open the notebook link from the same Drive folder as your sheet and choose **Runtime → Run all**. Sign in with your Google account when prompted.

The notebook shows a domain chart and a text report for each analysis class. See the [Notebooks guide](notebooks.md) for a walkthrough of how to read the chart and what the different span types mean.

---

## Fixing values

### What to do when a cell turns pink

Pink means the value is not in the allowed list for that criterion. Common causes:
- A typo (e.g. `Y` instead of `y`)
- A value that is valid in another column but not this one (e.g. `both` in a column that only accepts `y/n`)
- A cell that was accidentally cleared

Fix the cell using the dropdown. The pink goes within a day.

### Using the Example, Gloss, Translation, Source and Comments columns

All are free text and are never checked.

**Example** — The forms or sentences that show your answer, marked `*`, `?` or `??` as usual. Separate several with `;`. If you are judging your own language, this is your evidence.

**Gloss** and **Translation** — On every language's sheets except English's (whose examples need neither). Give each example its gloss, word for word, and its free translation, in the same order as in Example and separated with `;` in the same way (an invented example):

| Example | Gloss | Translation |
|---|---|---|
| `ema=ja kweti; *kweti ema=ja` | `1SG=ERG go.PST; go.PST 1SG=ERG` | `I went; I went` |

The chapters written from the annotation print these as glossed examples. A cell whose number of entries doesn't match Example's is printed without its gloss and translation.

**Source** — Page or section references for a published description (`§4.3`, `p. 217`, `Table 6.2`), so anyone can check a decision later without re-reading the whole grammar.

**Comments** — Only for things the coordinator should see:
- a question
- a doubt about a value (`unclear — see example 3.12`)
- something the columns can't express, or a test that doesn't fit

Each day, new and changed comments are collected into one GitHub issue for the coordinator, who replies there. Put examples in Example rather than here, so your questions stand out.

A small triangle in a cell's corner is a note from the tooling (for instance, the earlier answer of an element that was split in two). Hover over it to read it.
