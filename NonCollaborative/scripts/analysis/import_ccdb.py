"""Import planar structures and constituency tests from the CCDB.

The Constituency and Convergence Database (CCDB) holds planar structures and
constituency-test results for languages of the Americas, in a local clone at
``~/gitrepos/Constituency-Database`` (read-only here -- this script never
writes to, commits to, fetches, or pulls that clone). The goal of this
project's CCDB work, and the full plan this script is step 1 of, is recorded
in ``docs/PLAN_ccdb_planarsviz.md``: give every CCDB planar structure the
same laminar-family analysis and the same charts nyan1308 already gets.

This script is the one place that reads the CCDB clone. For each CCDB
``Planar_ID`` that has at least one constituency test (21 of the 24 planar
structures the clone lists -- three have planar tables but no tests, and are
only reported, never written), it writes three files this project's own
tools already read:

- ``domains/domains_<Planar_ID>.tsv`` -- that structure's rows from CCDB's
  ``domains.tsv``, every column, in CCDB's own row order, with one change:
  the ``Test_Labels`` column is rebuilt from ``Domain_ID`` rather than kept
  as CCDB wrote it, and CCDB's own value is kept alongside it in a new
  ``CCDB_Test_Labels`` column. CCDB's own short label (the one
  ``docs/PLAN_ccdb_planarsviz.md`` section 6.3 originally chose for chart
  labels) turns out to be missing -- CCDB's own "NA" -- for every test in 8
  of the 21 structures, and duplicated across genuinely distinct tests in 3
  more (see ``build_test_label()``'s docstring for exactly which). The
  pooled plots use this column as their row label, so it must be unique
  within a structure; ``Domain_ID`` always is, so the built label -- the
  Domain_ID with its ``<language_id>_<v/n/a>_`` prefix dropped and every
  ``_``/``.`` turned into a space -- is what gets written to
  ``Test_Labels``, and CCDB's own value moves to ``CCDB_Test_Labels`` so it
  is not lost. Decision recorded in ``docs/PLAN_ccdb_planarsviz.md``
  section 6.3, 2026-09-22.
- ``planar_tables/planar_<Planar_ID>.tsv`` -- that structure's rows from
  CCDB's ``planar.tsv``, unchanged.
- ``planar_tables/ccdb_<Planar_ID>.json`` -- a few facts a future exporter
  step needs and CCDB does not put in either TSV: the root position (from
  CCDB's ``input/overlaps.tsv``), the CCDB commit these files were read
  from, and a small headline count.

Two checks stop a structure's import (a clear error naming the structure and
row, not a traceback) rather than writing a file that says something CCDB's
own data doesn't actually support:

- Two rows in one structure sharing a *built* ``Test_Labels`` value. Not
  observed in the current clone -- the built label is unique across all 21
  structures -- but a real problem if it ever happens, since it would mean
  two distinct tests drew the same Domain_ID stem. CCDB's own label
  (``CCDB_Test_Labels``) is no longer checked for uniqueness, since it is
  known to fail that check for 11 structures for reasons that are CCDB data
  issues, not import bugs (see above); the dry run instead just reports,
  per structure, how many rows carry CCDB's "NA" and which CCDB labels are
  duplicated, as information worth raising with CCDB upstream, not a reason
  to stop.
- A ``Size`` that disagrees with ``Right_Edge - Left_Edge + 1``, or an edge
  outside ``1..n_positions``. Not observed in the current clone, but a real
  data problem if the clone ever produces one.

The planar table is checked separately: positions must run ``1..N`` with no
gaps. Also not observed in the current clone.

Dry run by default: prints, per structure, what it would write and whether
each file is new, unchanged, or would change, without touching disk.
``--apply`` writes. A structure that fails a check is reported and skipped
(no partial files for it); every other structure is still processed.

Usage:
    python scripts/analysis/import_ccdb.py                  # dry run, all 21
    python scripts/analysis/import_ccdb.py --apply
    python scripts/analysis/import_ccdb.py --planar-id chac1251_verbal --apply
    python scripts/analysis/import_ccdb.py --ccdb-dir /path/to/clone

Refuses to run (clear message, exit code 1, nothing written) if the clone
has uncommitted changes to ``domains.tsv``, ``planar.tsv`` or
``input/overlaps.tsv`` -- so the ``ccdb_commit`` recorded in each JSON file
always names the exact content that was read. Changes to other files in the
clone (it has a modified ``.DS_Store``) do not block this.

Re-running with no change to the CCDB clone produces byte-identical output.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[1]

DEFAULT_CCDB_DIR = Path.home() / "gitrepos" / "Constituency-Database"
DOMAINS_RELPATH = "domains.tsv"
PLANAR_RELPATH = "planar.tsv"
OVERLAPS_RELPATH = "input/overlaps.tsv"
DATA_RELPATHS = [DOMAINS_RELPATH, PLANAR_RELPATH, OVERLAPS_RELPATH]

DOMAINS_OUT_DIR = REPO_DIR / "domains"
PLANAR_OUT_DIR = REPO_DIR / "planar_tables"

# A Domain_ID's own language/structure stem: 8 characters, then a single
# letter for the structure type (v = verbal, n = nominal, a = adjective),
# then an underscore -- e.g. "arao1248_v_", "chac1251_n_". Checked against
# every row of the current clone's domains.tsv: matches all 464.
DOMAIN_ID_PREFIX_RE = re.compile(r"^[a-z0-9]{8}_[a-z]_")


def build_test_label(domain_id: str) -> str:
    """The chart label actually written to Test_Labels, built from Domain_ID
    rather than kept as CCDB's own short label.

    CCDB's own Test_Labels (kept alongside this, unchanged, as
    CCDB_Test_Labels) is missing -- CCDB's literal "NA" -- for every test in
    8 of the 21 structures with tests (chac1251_nominal, chac1251_verbal,
    dura0000_nominal, iyoj1235_verbal, kaya1330_verbal, kiow1266_verbal,
    mart1259_verbal, siks1238_verbal), and duplicated across genuinely
    distinct tests in 3 more: moco1246_verbal ("Non-permut. Rigid" for both
    the rigid and rigid/verb-conditioned-variability tests), sout2991_verbal
    (5 labels, each covering a maximal and a minimal or broad and narrow
    variant), and yucu1253_verbal ("Tone Diss. Max." for both the maximal
    and minimal tone-sandhi-dissimilation tests). The pooled plots key rows
    off this label, so it has to be unique within a structure; Domain_ID
    always is (found while writing this script, 2026-09-22; decision
    recorded in docs/PLAN_ccdb_planarsviz.md section 6.3).

    Built by dropping the leading "<8-char language id>_<v/n/a>_" and
    turning every "_" and "." into a space, then collapsing runs of spaces
    to one and stripping the ends. Every other character -- slashes,
    parentheses, non-ASCII (e.g. the IPA in "*ɛ j constraint", or curly
    quotes) -- is kept as CCDB wrote it. Example:
    "arao1248_v_ciscategorial.selection_maximal_broad" ->
    "ciscategorial selection maximal broad".
    """
    stem = DOMAIN_ID_PREFIX_RE.sub("", domain_id, count=1)
    stem = stem.replace("_", " ").replace(".", " ")
    return re.sub(r"\s+", " ", stem).strip()


def ccdb_label_diagnostics(ccdb_labels: pd.Series) -> tuple[int, dict[str, int]]:
    """(rows labelled CCDB's "NA", {duplicated CCDB label: count}) for one
    structure. Information only -- collected for the coordinator to raise
    with CCDB upstream, never a reason to stop this script."""
    na_count = int((ccdb_labels == "NA").sum())
    counts = ccdb_labels[ccdb_labels != "NA"].value_counts()
    duplicated = {label: int(count) for label, count in counts.items() if count > 1}
    return na_count, duplicated


def read_ccdb_tsv(path: Path) -> pd.DataFrame:
    """Read a CCDB TSV exactly as written: every value a string, and CCDB's
    own literal "NA" kept as the three-character string it is rather than
    becoming a missing value pandas would blank out on write."""
    return pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, na_filter=False)


def check_clone_clean(ccdb_dir: Path) -> None:
    """Refuse to run if the data files this script reads have uncommitted
    changes, so the recorded ccdb_commit always names what was actually
    read. Other uncommitted changes in the clone (e.g. its modified
    .DS_Store) do not block this."""
    result = subprocess.run(
        ["git", "-C", str(ccdb_dir), "status", "--porcelain", "--"] + DATA_RELPATHS,
        capture_output=True, text=True, check=True,
    )
    if result.stdout.strip():
        raise SystemExit(
            "Refusing to import: the CCDB clone has uncommitted changes to a "
            "file this script reads:\n" + result.stdout +
            "\nCommit or discard those changes in the clone, then re-run. "
            "This script never writes to the clone itself."
        )


def ccdb_commit(ccdb_dir: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(ccdb_dir), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def render_tsv(df: pd.DataFrame) -> bytes:
    """Deterministic TSV bytes for a slice of a CCDB table: every column,
    CCDB's own column order (df.columns, as read from the header), CCDB's
    own row order (the slice keeps the parent dataframe's row order), no
    reformatting of any value."""
    buffer = io.StringIO()
    df.to_csv(buffer, sep="\t", index=False, lineterminator="\n")
    return buffer.getvalue().encode("utf-8")


def render_json(metadata: dict) -> bytes:
    return (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")


class StructureError(ValueError):
    """A CCDB structure fails a data-integrity check; import for that
    structure alone stops, with a message naming the structure and the
    offending rows."""


def validate_planar_rows(planar_id: str, prows: pd.DataFrame) -> int:
    """Positions must run 1..N with no gaps or duplicates. Returns N."""
    positions = sorted(int(value) for value in prows["Position"])
    n = len(positions)
    if positions != list(range(1, n + 1)):
        raise StructureError(
            f"{planar_id}: planar_tables positions are not a gap-free 1..{n} "
            f"run: {positions}"
        )
    return n


def validate_domains_rows(
    planar_id: str, drows: pd.DataFrame, built_labels: pd.Series, n_positions: int
) -> None:
    """The built Test_Labels must be unique within the structure (CCDB's own
    label is no longer checked -- see build_test_label()'s docstring); Size
    must agree with Right_Edge - Left_Edge + 1; every edge must fall within
    1..n_positions."""
    duplicated = built_labels[built_labels.duplicated(keep=False)]
    if not duplicated.empty:
        offending = drows.loc[duplicated.index, ["Domain_ID"]].assign(built=duplicated)
        detail = "; ".join(
            f"{row.Domain_ID!r} built to {row.built!r}"
            for row in offending.itertuples()
        )
        raise StructureError(
            f"{planar_id}: {duplicated.nunique()} built Test_Labels value(s) "
            f"are shared by more than one row: {detail}"
        )

    left = drows["Left_Edge"].astype(int)
    right = drows["Right_Edge"].astype(int)
    size = drows["Size"].astype(int)
    bad_size = drows[size != (right - left + 1)]
    if not bad_size.empty:
        detail = "; ".join(
            f"{row.Domain_ID!r} Size={row.Size} but edges give "
            f"{int(row.Right_Edge) - int(row.Left_Edge) + 1}"
            for row in bad_size.itertuples()
        )
        raise StructureError(f"{planar_id}: Size disagrees with edges: {detail}")

    out_of_range = drows[(left < 1) | (right > n_positions)]
    if not out_of_range.empty:
        detail = "; ".join(
            f"{row.Domain_ID!r} spans {row.Left_Edge}-{row.Right_Edge}"
            for row in out_of_range.itertuples()
        )
        raise StructureError(
            f"{planar_id}: edge(s) fall outside 1..{n_positions}: {detail}"
        )


def root_position_for(
    language_id: str, planar_type: str, overlaps_df: pd.DataFrame
) -> int | None:
    """The root position from CCDB's overlaps.tsv: Overlap_Verbal for a
    verbal structure, Overlap_Nominal for a nominal one, null for anything
    else (e.g. adjective) or when the language has no overlaps row.
    Overlap_Verbal_Extended is never used (its meaning is unsettled -- see
    docs/PLAN_ccdb_planarsviz.md section 2)."""
    if planar_type == "verbal":
        column = "Overlap_Verbal"
    elif planar_type == "nominal":
        column = "Overlap_Nominal"
    else:
        return None
    matches = overlaps_df.loc[overlaps_df["Language_ID"] == language_id, column]
    if matches.empty:
        return None
    value = matches.iloc[0]
    return None if value == "NA" else int(value)


def build_structure(
    planar_id: str,
    domains_df: pd.DataFrame,
    planar_df: pd.DataFrame,
    overlaps_df: pd.DataFrame,
    commit: str,
) -> dict:
    """Validate one structure and render the bytes of its three output
    files. Raises StructureError if a check fails; writes nothing itself."""
    drows = domains_df[domains_df["Planar_ID"] == planar_id]
    prows = planar_df[planar_df["Planar_ID"] == planar_id]
    if prows.empty:
        raise StructureError(f"{planar_id}: has tests but no planar_tables rows.")

    n_positions = validate_planar_rows(planar_id, prows)

    built_labels = drows["Domain_ID"].apply(build_test_label)
    validate_domains_rows(planar_id, drows, built_labels, n_positions)
    na_count, duplicated_ccdb_labels = ccdb_label_diagnostics(drows["Test_Labels"])

    # Test_Labels becomes the built label; CCDB's own value moves to a new
    # CCDB_Test_Labels column placed right after it. Every other column, and
    # its position, is untouched.
    drows = drows.copy()
    ccdb_labels = drows["Test_Labels"]
    drows["Test_Labels"] = built_labels
    drows.insert(drows.columns.get_loc("Test_Labels") + 1, "CCDB_Test_Labels", ccdb_labels)

    planar_type = prows["Planar_Type"].iloc[0]
    language_id = prows["Language_ID"].iloc[0]
    language_name = prows["Language_Name"].iloc[0]
    root_position = root_position_for(language_id, planar_type, overlaps_df)

    metadata = {
        "planar_id": planar_id,
        "language_id": language_id,
        "language_name": language_name,
        "planar_type": planar_type,
        "n_positions": n_positions,
        "root_position": root_position,
        "ccdb_commit": commit,
        "ccdb_source_files": DATA_RELPATHS,
        "n_tests": len(drows),
    }
    return {
        "domains_bytes": render_tsv(drows),
        "planar_bytes": render_tsv(prows),
        "json_bytes": render_json(metadata),
        "n_positions": n_positions,
        "n_tests": len(drows),
        "root_position": root_position,
        "language_name": language_name,
        "planar_type": planar_type,
        "ccdb_na_count": na_count,
        "ccdb_duplicated_labels": duplicated_ccdb_labels,
    }


def file_status(path: Path, new_bytes: bytes) -> str:
    if not path.exists():
        return "new"
    return "unchanged" if path.read_bytes() == new_bytes else "changed"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--ccdb-dir", type=Path, default=DEFAULT_CCDB_DIR,
        help=f"Path to the local CCDB clone (default: {DEFAULT_CCDB_DIR})",
    )
    parser.add_argument(
        "--planar-id", nargs="+", default=None, metavar="PLANAR_ID",
        help="Limit to one or more Planar_ID values (default: every structure with tests)",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Write the files. Without this flag, only report what would happen.",
    )
    args = parser.parse_args()

    ccdb_dir = args.ccdb_dir
    if not ccdb_dir.is_dir():
        raise SystemExit(f"CCDB clone not found at {ccdb_dir}")

    check_clone_clean(ccdb_dir)
    commit = ccdb_commit(ccdb_dir)

    domains_df = read_ccdb_tsv(ccdb_dir / DOMAINS_RELPATH)
    planar_df = read_ccdb_tsv(ccdb_dir / PLANAR_RELPATH)
    overlaps_df = read_ccdb_tsv(ccdb_dir / OVERLAPS_RELPATH)

    tested_ids = sorted(domains_df["Planar_ID"].unique())
    all_planar_ids = sorted(planar_df["Planar_ID"].unique())
    untested_ids = sorted(set(all_planar_ids) - set(tested_ids))

    selected_ids = tested_ids
    if args.planar_id is not None:
        unknown = sorted(set(args.planar_id) - set(all_planar_ids))
        if unknown:
            raise SystemExit(f"Unknown Planar_ID(s), not in {PLANAR_RELPATH}: {unknown}")
        requested_untested = sorted(set(args.planar_id) & set(untested_ids))
        if requested_untested:
            raise SystemExit(
                f"Requested Planar_ID(s) have no constituency tests in CCDB, "
                f"nothing to import: {requested_untested}"
            )
        selected_ids = sorted(set(args.planar_id))

    print(f"CCDB clone: {ccdb_dir}")
    print(f"CCDB commit: {commit}")
    print(f"Structures with tests: {len(tested_ids)}; structures with no "
          f"tests (skipped): {len(untested_ids)} {untested_ids}")
    print(f"Mode: {'APPLY' if args.apply else 'dry run'}")
    print()

    header = (
        f"{'Planar_ID':22s} {'tests':>5s} {'positions':>9s} {'root':>5s} "
        f"{'domains':>10s} {'planar':>10s} {'json':>10s}"
    )
    print(header)
    print("-" * len(header))

    failures: list[str] = []
    written = 0
    for planar_id in selected_ids:
        try:
            structure = build_structure(planar_id, domains_df, planar_df, overlaps_df, commit)
        except StructureError as exc:
            print(f"{planar_id:22s}  ERROR: {exc}")
            failures.append(planar_id)
            continue

        domains_path = DOMAINS_OUT_DIR / f"domains_{planar_id}.tsv"
        planar_path = PLANAR_OUT_DIR / f"planar_{planar_id}.tsv"
        json_path = PLANAR_OUT_DIR / f"ccdb_{planar_id}.json"

        domains_status = file_status(domains_path, structure["domains_bytes"])
        planar_status = file_status(planar_path, structure["planar_bytes"])
        json_status = file_status(json_path, structure["json_bytes"])

        root = structure["root_position"]
        print(
            f"{planar_id:22s} {structure['n_tests']:5d} {structure['n_positions']:9d} "
            f"{'--' if root is None else root:>5} "
            f"{domains_status:>10s} {planar_status:>10s} {json_status:>10s}"
        )
        na_count = structure["ccdb_na_count"]
        duplicated = structure["ccdb_duplicated_labels"]
        if na_count or duplicated:
            bits = []
            if na_count:
                bits.append(f'CCDB label "NA": {na_count} row(s)')
            if duplicated:
                dup_desc = "; ".join(f"{label!r} x{count}" for label, count in duplicated.items())
                bits.append(f"CCDB label duplicated: {dup_desc}")
            print(f"    info: {'; '.join(bits)}")

        if args.apply:
            for path, data, status in (
                (domains_path, structure["domains_bytes"], domains_status),
                (planar_path, structure["planar_bytes"], planar_status),
                (json_path, structure["json_bytes"], json_status),
            ):
                if status != "unchanged":
                    path.write_bytes(data)
        written += 1

    print()
    print(f"{written} of {len(selected_ids)} requested structure(s) "
          f"{'written' if args.apply else 'would be written'}.")
    if failures:
        print(f"{len(failures)} structure(s) failed validation and were not "
              f"written: {failures}")
        sys.exit(1)


if __name__ == "__main__":
    main()
