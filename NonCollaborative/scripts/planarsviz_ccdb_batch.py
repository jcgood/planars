"""Draw every CCDB structure's charts, and write one summary of how it went.

A loop over the one-language command (``scripts/planarsviz_language.py``,
plan ``docs/PLAN_ccdb_planarsviz.md`` step 4): for each structure the CCDB
import wrote (``planar_tables/ccdb_<Planar_ID>.json``), export its bundle with
all four permutation tests and render every chart. A structure that fails
does not stop the others. Each structure's full output goes to
``results/ccdb_batch/<Planar_ID>.log``; the summary goes to
``results/ccdb_batch/summary.md`` and says, per structure:

- whether the export and render worked, and which charts failed, with the
  renderer's reason;
- which kinds of chart it has none of, when other structures do (the
  renderer leaves a chart out when the bundle has nothing for it, e.g. no
  conflict groups -- normal, but worth knowing);
- anything worth a look before trusting a chart: very few families, a family
  with more spans than the 26 letters two charts name spans with, very long
  structures, characters in a title or label the PDF fonts can't draw, a
  placeholder root span, truncated permutation draws.

It holds no analysis or drawing code of its own. ``--summary-only`` rewrites
the summary from the logs and bundles already there, without running
anything.

Usage (from ``NonCollaborative/``, though it runs from anywhere):
    python scripts/planarsviz_ccdb_batch.py                    # dry run: list what would run
    python scripts/planarsviz_ccdb_batch.py --apply            # all 21, four at a time
    python scripts/planarsviz_ccdb_batch.py --apply --only chac1251_nominal,mart1259_verbal
    python scripts/planarsviz_ccdb_batch.py --summary-only
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

NC = Path(__file__).resolve().parents[1]
BATCH_DIR = NC / "results" / "ccdb_batch"

# What counts as worth a look. Each threshold is where a chart is known to
# start misbehaving (see CCDB_PLANARSVIZ_PROGRESS.md "Likely trouble"); the
# first run's two commonest notes -- boundary strengths under the overlay's
# every-50 gridlines, and test labels too long for the pooled canvas -- were
# fixed in the charts, so they are no longer reported.
FEW_FAMILIES = 2           # exemplary and conflict-group charts have little to show
SPAN_LETTER_LIMIT = 26     # ghost_trees.R / conflict_groups.R name spans a..z
LONG_STRUCTURE = 40        # positions; widest canvases and longest label rows


def pdf_can_draw(char: str) -> bool:
    """Whether R's default PDF device can draw this character. Its standard
    fonts use the Windows Latin-1 encoding; anything outside it (IPA such as
    ʔ or ɛ, a separate combining accent) comes out as a period."""
    try:
        char.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


def ccdb_datasets() -> list[str]:
    return sorted(p.stem[len("ccdb_"):] for p in (NC / "planar_tables").glob("ccdb_*.json"))


def run_one(dataset: str, extra: list[str]) -> tuple[str, int, float]:
    cmd = [sys.executable, "scripts/planarsviz_language.py", dataset, "--apply", *extra]
    log = BATCH_DIR / f"{dataset}.log"
    start = time.monotonic()
    with log.open("w", encoding="utf-8") as out:
        out.write("$ " + " ".join(cmd) + "\n")
        out.flush()
        code = subprocess.run(cmd, cwd=NC, stdout=out, stderr=subprocess.STDOUT).returncode
    elapsed = time.monotonic() - start
    with log.open("a", encoding="utf-8") as out:
        out.write(f"\n[batch] exit code {code} after {elapsed:.0f} s\n")
    print(f"{dataset}: exit {code} after {elapsed:.0f} s", flush=True)
    return dataset, code, elapsed


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def chart_kind(name: str) -> str:
    """A chart name with its numbers taken out, so tree 3 of one forest and
    tree 7 of another count as the same kind of chart."""
    name = re.sub(r"_tree_\d+$", "_tree_N", name)
    return re.sub(r"exemplary_trees_(slide_)?\d+", r"exemplary_trees_\1N", name)


def parse_log(log: Path) -> dict:
    text = log.read_text(encoding="utf-8") if log.exists() else ""
    result = {"ran": bool(text), "exit": None, "seconds": None, "export_ok": False,
              "render_line": None, "failed": {}}
    if m := re.search(r"\[batch\] exit code (-?\d+) after (\d+) s", text):
        result["exit"], result["seconds"] = int(m.group(1)), int(m.group(2))
    result["export_ok"] = "Export finished in" in text
    if m := re.search(r"^(\d+ files for \d+ of \d+ charts.*?);", text, re.M):
        result["render_line"] = m.group(1)
    for m in re.finditer(r"^FAILED (\S+): (.*)$", text, re.M):
        result["failed"][m.group(1)] = m.group(2)
    if not result["export_ok"] and text:
        # The last few lines are where a Python traceback ends.
        result["tail"] = "\n".join(text.rstrip().splitlines()[-6:])
    return result


def bundle_notes(dataset: str) -> tuple[dict, list[str]]:
    data = NC / "results" / "chart_data" / dataset / "data"
    meta_path = data / "metadata.json"
    if not meta_path.exists():
        return {}, ["no bundle"]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    notes = []
    n_fam = meta.get("n_maximal_families", 0)
    if n_fam <= FEW_FAMILIES:
        notes.append(f"only {n_fam} famil{'y' if n_fam == 1 else 'ies'}: exemplary and "
                     "conflict-group charts have little to show")
    largest = max((int(r["n_spans"]) for r in read_tsv(data / "families.tsv")), default=0)
    if largest > SPAN_LETTER_LIMIT:
        notes.append(f"largest family has {largest} spans, more than the {SPAN_LETTER_LIMIT} "
                     "letters ghost_trees/conflict_groups name spans with")
    if meta.get("n_positions", 0) > LONG_STRUCTURE:
        notes.append(f"{meta['n_positions']} positions: check label crowding")
    labels = [r["Test_Labels"] for r in read_tsv(data / "tests.tsv")]
    drawn = labels + [meta.get("language_name") or ""]
    undrawable = sorted({c for text in drawn for c in text if not pdf_can_draw(c)})
    if undrawable:
        notes.append("characters R's PDF fonts draw as a period: " + " ".join(undrawable))
    if meta.get("synthetic_root"):
        notes.append("no test covers the whole structure, so the placeholder root span puts "
                     "a capped mark with no bar at the first and/or last position of boundary_strength")
    for table in ("span_placement_test.tsv", "arbitrary_layers_test.tsv"):
        truncated = [r["group"] for r in read_tsv(data / table) if int(r.get("n_truncated") or 0)]
        if truncated:
            notes.append(f"{table}: truncated draws in {', '.join(truncated)}")
    if meta.get("root_position_source") != "--root-position":
        notes.append(f"root position from {meta.get('root_position_source')}, not CCDB's overlaps.tsv")
    return meta, notes


def rendered_kinds(dataset: str) -> set[str]:
    manifest = NC / "results" / f"{dataset}_planarsviz_manifest.tsv"
    return {chart_kind(r["chart"]) for r in read_tsv(manifest)}


def write_summary(datasets: list[str]) -> Path:
    rows = []
    for ds in datasets:
        log = parse_log(BATCH_DIR / f"{ds}.log")
        meta, notes = bundle_notes(ds)
        rows.append((ds, log, meta, notes, rendered_kinds(ds) | {chart_kind(c) for c in log["failed"]}))
    all_kinds = set().union(*(r[4] for r in rows)) if rows else set()

    lines = ["# CCDB batch: all structures through planarsviz", "",
             "Written by `scripts/planarsviz_ccdb_batch.py`; each structure's full output is "
             "in the `.log` beside this file.", "",
             "| Structure | Positions | Tests | Families | Export | Charts | Minutes |",
             "|---|---|---|---|---|---|---|"]
    for ds, log, meta, notes, _ in rows:
        if not log["ran"]:
            status, charts = "not run", ""
        else:
            status = "ok" if log["export_ok"] else "**failed**"
            charts = log["render_line"] or ""
            if log["failed"]:
                charts += f"; **{len(log['failed'])} failed**"
        minutes = f"{log['seconds'] / 60:.1f}" if log["seconds"] is not None else ""
        lines.append(f"| {ds} | {meta.get('n_positions', '')} | {meta.get('n_active_tests', '')} | "
                     f"{meta.get('n_maximal_families', '')} | {status} | {charts} | {minutes} |")

    failures = [(ds, log) for ds, log, *_ in rows if log["ran"] and (log["failed"] or not log["export_ok"])]
    lines += ["", "## What failed", ""]
    if not failures:
        lines.append("Nothing.")
    for ds, log in failures:
        if not log["export_ok"]:
            lines += [f"- **{ds}**: export failed:", "", "  ```", *("  " + l for l in log.get("tail", "").splitlines()), "  ```"]
        for chart, reason in log["failed"].items():
            lines.append(f"- **{ds}** `{chart}`: {reason}")

    # Grouped by chart, since one fix to a chart function fixes it everywhere.
    by_kind: dict[str, list[str]] = {}
    for ds, log, _, _, kinds in rows:
        if log["ran"] and log["export_ok"]:
            for kind in sorted(all_kinds - kinds):
                by_kind.setdefault(kind, []).append(ds)
    lines += ["", "## Charts a structure has none of (the bundle had nothing for them)", ""]
    lines += [f"- `{k}`: {', '.join(v)}" for k, v in sorted(by_kind.items())] or ["None."]

    lines += ["", "## Worth a look", ""]
    noted = [(ds, notes) for ds, _, _, notes, _ in rows if notes]
    lines += [f"- **{ds}**: " + "; ".join(notes) for ds, notes in noted] or ["Nothing."]

    path = BATCH_DIR / "summary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export and render every CCDB structure, then summarise.")
    parser.add_argument("--apply", action="store_true", help="Run. Without it, only list what would run.")
    parser.add_argument("--only", help="Comma-separated Planar_IDs instead of all of them.")
    parser.add_argument("--jobs", type=int, default=4, help="Structures run at once (default 4).")
    parser.add_argument("--permutations", type=int, help="Passed to planarsviz_language.py (its default is 5000).")
    parser.add_argument("--no-permutations", action="store_true", help="Passed to planarsviz_language.py.")
    parser.add_argument("--formats", help="Passed to the renderer, e.g. pdf,png (default pdf).")
    parser.add_argument("--summary-only", action="store_true",
                        help="Rewrite the summary from the existing logs and bundles; run nothing.")
    args = parser.parse_args()

    datasets = ccdb_datasets()
    if args.only:
        wanted = args.only.split(",")
        unknown = sorted(set(wanted) - set(datasets))
        if unknown:
            sys.exit(f"Not a CCDB structure: {', '.join(unknown)}. "
                     "scripts/analysis/import_ccdb.py writes one planar_tables/ccdb_<Planar_ID>.json each.")
        datasets = [d for d in datasets if d in wanted]
    extra = []
    if args.permutations is not None:
        extra += ["--permutations", str(args.permutations)]
    if args.no_permutations:
        extra.append("--no-permutations")
    if args.formats:
        extra += ["--formats", args.formats]

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    if args.summary_only:
        print(f"Summary: {write_summary(ccdb_datasets()).relative_to(NC)}")
        return
    if not args.apply:
        print(f"Would run, from {NC.name}/, {args.jobs} at a time:\n")
        for ds in datasets:
            print("  python scripts/planarsviz_language.py " + " ".join([ds, "--apply", *extra]))
        print(f"\n{len(datasets)} structures. Nothing was run. Add --apply to run them.")
        return

    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(lambda ds: run_one(ds, extra), datasets))
    print(f"\nAll {len(datasets)} done in {(time.monotonic() - start) / 60:.1f} min.")
    # The summary covers every structure, so a --only run's results sit
    # beside the earlier runs' rather than replacing them.
    print(f"Summary: {write_summary(ccdb_datasets()).relative_to(NC)}")


if __name__ == "__main__":
    main()
