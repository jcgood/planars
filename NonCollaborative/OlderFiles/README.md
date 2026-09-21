# OlderFiles/

Archived versions of scripts and data kept for historical reference. Do not use for new work.

**Do not run anything in here.** R started in `NonCollaborative/` refuses to, and says so — `.Rprofile` has the guard and the reason. The short version: the scripts in `planarsviz_superseded/` still work, and running one directly writes its old output over a chart the `planarsviz` package produced, under the same filename. The porting checks run them safely because they evaluate the script's text in memory with `ggsave` disabled; a direct run has no such protection. The deliberate escape is `PLANARS_RUN_ARCHIVED=1 Rscript <file>`.

## Contents

- `ConstituencyConvergenceDBScripts/` — Complete older processing pipeline for the Constituency and Convergence Database (CCDB). See its own `README.md` for database documentation.
- `MakeDomains/` — Earlier iterations of domain generation logic, generated plots, and output tables.
- `planar_tables/` — Archived planar structure files (timestamped CSV snapshots; canonical file is `../planar_tables/planar_stan1293.tsv`).
- `planars/` — Early per-language domain TSVs.
- `scripts/` — Deprecated copies of scripts now maintained in `../scripts/`.
- `planarsviz_superseded/` — The R scripts that drew the nyan1308 charts before the `planarsviz` package took over. **The exception to "do not use" below: do not delete these.** The porting checks in `../scripts/planarsviz_checks/` run them to prove the package draws the same charts, so they are evidence rather than dead weight, and several can no longer be regenerated. See that directory's own `README.md`.
