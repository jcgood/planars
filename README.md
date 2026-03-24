# planars

A Python toolkit for deriving morphosyntactic constituency spans from annotated planar structures, designed for cross-linguistic typological research.

Planar structures are ordered sequences of positions representing the morphosyntactic template of a language's verbal domain. Each position is filled by one or more elements (forms or form-types). Researchers annotate elements with diagnostic parameters, and this toolkit derives **spans** — ranges of positions identified as domains by various constituency tests.

This toolkit builds on the theoretical framework developed in:

> Tallman, Adam J. R., Sandra Auderset, and Hiroto Uchihara (eds.). 2024. *Constituency and convergence in the Americas*. Topics in Phonological Diversity 1. Berlin: Language Science Press. doi:[10.5281/zenodo.10559861](https://doi.org/10.5281/zenodo.10559861)

---

## Requirements

- Python 3.9+
- [pandas](https://pandas.pydata.org/)
- [gspread](https://docs.gspread.org/) + google-auth + google-api-python-client (Google Sheets workflow only)

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

---

## Documentation

| Guide | For whom | What you will find |
|---|---|---|
| [Collaborator guide](docs/collaborator-guide.md) | Annotators filling in Google Sheets | Opening your sheet, filling in values, viewing results in Colab, fixing validation errors |
| [Coordinator guide](docs/coordinator-guide.md) | Project coordinators managing data and sheets | Repository setup, daily git workflow, adding languages, all `coding/` commands |
| [Analyses](docs/analyses.md) | Researchers and library contributors | Span types, all 15 analysis modules, parameter reference, `[AUTO-DERIVED]` status notes |
| [Notebooks](docs/notebooks.md) | All users | Contributor, coordinator, and validation Colab notebooks — what they contain and how to use them |
| [Data management](docs/data-management.md) | Coordinators and developers | Two-repo architecture, planar input format, `diagnostics_{lang_id}.tsv` format, `coded_data/` layout |
| [Testing](docs/testing.md) | Developers | Regression snapshot tests, synthetic test language (`synth0001`) |
| [References](docs/references.md) | All users | Full bibliography in ULSS and BibTeX; how to cite the toolkit and individual language analyses |

For diagnostic criterion definitions and qualification rules, see `schemas/diagnostic_criteria.yaml` and `schemas/diagnostic_classes.yaml`. For analytical term definitions, see `schemas/terms.yaml`.

---

## How to cite

**Citing the planars toolkit:**

> Good, Jeff & Adam J. R. Tallman. 2026. *planars*: A Python toolkit for deriving morphosyntactic constituency spans from annotated planar structures (version 0.1.0a11). GitHub repository. https://github.com/jcgood/planars

A `CITATION.cff` file is included in the repository root for citation manager import. A Zenodo DOI will be added when the repository is formally archived at release.

**Citing the underlying theoretical framework:**

> Tallman, Adam J. R., Sandra Auderset & Hiroto Uchihara (eds.). 2024. *Constituency and convergence in the Americas* (Topics in Phonological Diversity 1). Berlin: Language Science Press. doi:10.5281/zenodo.10559861

**Citing specific language analyses:**

When reporting results for a specific language, please also cite the relevant chapter from Tallman, Auderset & Uchihara (2024). BibTeX entries and ULSS-formatted citations for all chapters that have informed this codebase are collected in [docs/references.md](docs/references.md).
