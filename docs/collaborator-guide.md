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
- **Comments column**: Use this for anything you want to flag — uncertainty, alternative analyses, references to examples. It is passed through unchanged and is never used in computation.

### Viewing your results

Once your coordinator has imported your filled sheet, results appear in your contributor Colab notebook. Open the notebook link from the same Drive folder as your sheet and choose **Runtime → Run all**. Sign in with your Google account when prompted.

The notebook shows a domain chart and a text report for each analysis class. See the [Notebooks guide](notebooks.md) for a walkthrough of how to read the chart and what the different span types mean.

---

## Advanced: running the validation notebook yourself

You do not have to wait for your coordinator to tell you about errors. The validation notebook for your language checks the same rules that `import-sheets` applies: it highlights any invalid cells pink directly in the Google Sheet and prints a summary of issues.

1. Open the validation notebook link from your Drive folder (named `validation_{lang_id}.ipynb`)
2. Choose **Runtime → Run all**
3. Sign in with your Google account when prompted
4. Invalid cells are highlighted pink in the sheet; the issue summary appears at the bottom of the notebook

You can run this notebook as many times as you like while fixing errors — it clears previous pink highlights and re-checks from scratch each time.

See the [Notebooks guide](notebooks.md#validation-notebook) for more detail on how to read the validation output.

### What to do when a cell turns pink

Pink means the value is not in the allowed list for that criterion. Common causes:
- A typo (e.g. `Y` instead of `y`)
- A value that is valid in another column but not this one (e.g. `both` in a column that only accepts `y/n`)
- A cell that was accidentally cleared

Fix the cell using the dropdown, then re-run the validation notebook to confirm the pink is gone.

### Using the Comments column

The Comments column is free text and is never validated. Use it freely:
- Flag uncertainty (`"unclear — see example 3.12"`)
- Note alternative analyses
- Ask a question for the coordinator
- Record the source example you based your annotation on

Comments are preserved through `import-sheets` and are available in the filled TSV.
