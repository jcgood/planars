from pathlib import Path

def _find_repo_root():
    for p in [Path().resolve(), *Path().resolve().parents]:
        if (p / "planars").is_dir() and (p / "coded_data").is_dir():
            return p
    raise RuntimeError(
        "Could not find the planars repo root. "
        "Make sure you launched Jupyter from the repo directory."
    )

REPO_ROOT = _find_repo_root()

from planars import ciscategorial as _cisc
from planars import subspanrepetition as _subspan
from planars import noninterruption as _nonint

def show_results(folder, derive_fn, fmt_fn, pattern="*_filled.tsv"):
    tsv_files = sorted((REPO_ROOT / "coded_data").glob(f"*/{folder}/{pattern}"))
    if not tsv_files:
        print(f"  No filled TSVs found in {folder}/")
        return
    for tsv in tsv_files:
        lang_id = tsv.parent.parent.name
        print(f"{'─' * 60}")
        print(f"  {folder}  [{lang_id}]  —  {tsv.stem.replace('_filled', '')}")
        print(f"{'─' * 60}")
        result = derive_fn(tsv, strict=False)
        print(fmt_fn(result))
        print()

from planars.charts import collect_all_spans, domain_chart, charts_by_language

print(f"Ready. Repo root: {REPO_ROOT}")
