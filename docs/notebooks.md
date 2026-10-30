# Notebooks guide

planars uses Colab notebooks for browser-based access to results. No local installation is required to use them — collaborators and coordinators open shared Drive links and choose **Runtime → Run all**.

Notebooks are generated automatically by `python -m coding generate-notebooks --apply` (which runs in the daily refresh and at the end of `generate-sheets`, `sync-params --apply`, and `restructure-sheets --apply`) and uploaded directly to Google Drive. You do not manage notebook files manually.

A notebook finds a language's sheets by the labels the tooling puts on every sheet it makes (`planars/from_sheets.py`), so it works for anyone the sheets are shared with, and a new or replaced sheet needs no new notebook. The tests it shows come from the tabs it finds, so the notebook names no class either. (Until 2026-10-29 the notebooks read a list of sheet IDs, the manifest, from a file on Drive; it went stale more than once and was deleted.)

---

## Contributor notebook

**Filename:** `domains_{lang_id}.ipynb`
**Audience:** Collaborators (annotators) and coordinators
**Location:** Language Drive folder

One notebook per language. Shows how complete each construction is (with its review status), a text report per construction under **Results by test**, and a domain chart for that language. This is the primary way collaborators see the effect of their annotations.

### How to use

1. Open the shared notebook link from your Drive folder — it opens in Colab automatically
2. Choose **Runtime → Run all**
3. When prompted, sign in with your Google account and allow access
4. The completeness list, the text reports and the domain chart appear in that order

### How to read the domain chart

The chart shows horizontal segments — one per analysis type — laid out on a shared position axis anchored at the keystone (`v:verbstem`). Each segment represents a span: how far a particular domain extends to the left and right of the keystone.

The four span variants appear as distinct rows or colors within each analysis:
- **Strict complete** — the domain defined only by positions where every element is in the span, with no gaps
- **Strict partial** — the same, but a position counts if any element is in the span
- **Loose complete** / **Loose partial** — as above, but gaps are allowed (extends to the farthest in-span position on each side)

Longer segments mean broader domains. A strict span will always be contained within or equal to the corresponding loose span. See the [Analyses guide](analyses.md) for precise definitions of all span types.

### Text reports

Under **Results by test**, each construction that produces spans gets a text report listing:
- The keystone position
- Which positions are complete and partial
- The four span values in human-readable form (e.g., `positions 4–15 (vpref–tamesuf)`)

---

## Coordinator notebook

**Filename:** `all_languages.ipynb`
**Audience:** Project coordinators
**Location:** Top-level `ConstituencyTypology` Drive folder

A single notebook covering every language whose sheets you can open (found by their labels). Shows completeness, per-construction text reports and one domain chart per language. Useful for cross-linguistic comparison and project oversight.

### How to use

1. Open the shared notebook link from Google Drive
2. Choose **Runtime → Run all**
3. When prompted, sign in and allow access

The notebook loops over all languages automatically — no configuration needed.

---

## Report notebook

**Filename:** `report_{lang_id}.ipynb`
**Audience:** Non-technical collaborators, coordinators
**Location:** Language Drive folder

One notebook per language. Generates a self-contained HTML report for that language and uploads it to Drive as `report_{lang_id}.html` — updating the file in-place so the shared URL stays stable.

### How to use

1. Open the report notebook link from your Drive folder
2. Choose **Runtime → Run all**
3. When prompted, sign in with your Google account and allow access
4. The notebook prints the stable Drive URL for the HTML report at the end

The HTML report can then be shared directly — recipients do not need a Google account or Colab to view it. The report includes a completeness table (which constructions are annotated), a domain chart, and a timestamp showing when it was generated.

The report is also refreshed automatically by a nightly GitHub Actions workflow — see the [Coordinator guide](coordinator-guide.md#nightly-report-generation). Run the notebook manually when you want an on-demand update outside the nightly schedule.

---

## How notebooks are generated

Notebooks are built from templates in `notebooks/templates/`:

| Template | Generates |
|---|---|
| `domains_boilerplate.ipynb` | Per-language contributor notebooks |
| `all_languages_boilerplate.ipynb` | Coordinator notebook |
| `report_boilerplate.ipynb` | Per-language report notebooks |

To update the boilerplate (setup cell, chart cell, etc.), edit the template; `tests/test_notebook_templates.py` runs every cell after Setup against the saved test data, so run it before pushing. The daily refresh then publishes the change to every notebook, or publish it at once:

```bash
python -m coding generate-notebooks --apply
```

This uploads fresh notebooks to Drive for all languages, keeping each notebook's link. It also runs automatically in the daily refresh and at the end of `generate-sheets`, `sync-params --apply`, and `restructure-sheets --apply`, so run it by hand only to publish a template change before the next refresh.

The predecessor notebooks (`sync_colab.ipynb`, `span_results_colab.ipynb`) are archived in `notebooks/archive/` for reference.

There was also a validation notebook per language (`validation_{lang_id}.ipynb`), retired 2026-10-23. Problem cells are now listed in the **Needs fixing** column of each sheet's Status tab by the daily refresh, and highlighted pink ([Collaborator guide](collaborator-guide.md)).
