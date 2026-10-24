# Notebooks guide

planars uses Colab notebooks for browser-based access to results. No local installation is required to use them — collaborators and coordinators open shared Drive links and choose **Runtime → Run all**.

Notebooks are generated automatically by `python -m coding generate-notebooks` (which runs as part of `generate-sheets`, `sync-params --apply`, and `restructure-sheets --apply`) and uploaded directly to Google Drive. You do not manage notebook files manually.

---

## Contributor notebook

**Filename:** `domains_{lang_id}.ipynb`
**Audience:** Collaborators (annotators) and coordinators
**Location:** Language Drive folder

One notebook per language. Shows a domain chart for that language and per-construction text reports for each analysis class. This is the primary way collaborators see the effect of their annotations.

### How to use

1. Open the shared notebook link from your Drive folder — it opens in Colab automatically
2. Choose **Runtime → Run all**
3. When prompted, sign in with your Google account and allow access
4. The domain chart and text reports appear at the bottom of the notebook

### How to read the domain chart

The chart shows horizontal segments — one per analysis type — laid out on a shared position axis anchored at the keystone (`v:verbstem`). Each segment represents a span: how far a particular domain extends to the left and right of the keystone.

The four span variants appear as distinct rows or colors within each analysis:
- **Strict complete** — the domain defined only by positions where every element is in the span, with no gaps
- **Strict partial** — the same, but a position counts if any element is in the span
- **Loose complete** / **Loose partial** — as above, but gaps are allowed (extends to the farthest in-span position on each side)

Longer segments mean broader domains. A strict span will always be contained within or equal to the corresponding loose span. See the [Analyses guide](analyses.md) for precise definitions of all span types.

### Text reports

Below the chart, each analysis class produces a text report listing:
- The keystone position
- Which positions are complete and partial
- The four span values in human-readable form (e.g., `positions 4–15 (vpref–tamesuf)`)

---

## Coordinator notebook

**Filename:** `all_languages.ipynb`
**Audience:** Project coordinators
**Location:** Top-level `ConstituencyTypology` Drive folder

A single notebook covering all languages in the manifest. Shows per-construction text reports and one domain chart per language. Useful for cross-linguistic comparison and project oversight.

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

To update the boilerplate (setup cell, chart cell, etc.), edit the template and re-run:

```bash
python -m coding generate-notebooks
```

This uploads fresh notebooks to Drive for all languages. It also runs automatically at the end of `generate-sheets`, `sync-params --apply`, and `restructure-sheets --apply`. See the [Coordinator guide](coordinator-guide.md#regenerating-notebooks) for when to run this manually.

The predecessor notebooks (`sync_colab.ipynb`, `span_results_colab.ipynb`) are archived in `notebooks/archive/` for reference.

There was also a validation notebook per language (`validation_{lang_id}.ipynb`), retired 2026-10-23. Problem cells are now listed in the **Needs fixing** column of each sheet's Status tab by the daily refresh, and highlighted pink ([Collaborator guide](collaborator-guide.md)).
