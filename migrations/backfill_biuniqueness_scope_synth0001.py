#!/usr/bin/env python3
"""One-time migration: backfill the Biuniqueness_Scope column into
coded_data/synth0001/lang_setup/planar_synth0001.tsv.

Motivation: issue #254 Part 2b. Part 2a added the Biuniqueness_Scope structural
column (schemas/planar.yaml) and coding.make_forms.classify_biuniqueness_scope();
this script computes it per element (token-aligned with Elements, same tokenization
as Element_Types) and writes it into synth0001's planar TSV so Stage 1 Sheet
generation (Part 2c) has flags to read. synth0001-only by design — stan1293 stays
untouched until the mechanism is validated end-to-end on the synthetic language
(see #254's Part 2 sequencing decision).
Run: 2026-07-30, after commit 4e815c7.

Usage:
    python migrations/backfill_biuniqueness_scope_synth0001.py           # dry run
    python migrations/backfill_biuniqueness_scope_synth0001.py --apply   # write the file

Post-run checks:
    python -m coding integrity-check
    python -m pytest
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from coding.validate_planar import _tokenize_elements, validate_planar_df
from coding.make_forms import classify_biuniqueness_scope

TARGET = ROOT / "coded_data" / "synth0001" / "lang_setup" / "planar_synth0001.tsv"

DRY_RUN = "--apply" not in sys.argv


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"Not found: {TARGET}")

    df = pd.read_csv(TARGET, sep="\t", dtype=str, keep_default_na=False)

    if "Biuniqueness_Scope" in df.columns and df["Biuniqueness_Scope"].str.strip().any():
        raise SystemExit(
            "Biuniqueness_Scope already has content in this file — "
            "this migration is meant to run once against an unbackfilled file."
        )

    computed = []
    for _, row in df.iterrows():
        tokens = _tokenize_elements(str(row["Elements"]).strip())
        scopes = [classify_biuniqueness_scope(t) for t in tokens]
        if "unknown" in scopes:
            bad = [t for t, s in zip(tokens, scopes) if s == "unknown"]
            raise SystemExit(
                f"row '{row['Position_Name']}': unregistered ALL CAPS label(s) {bad} — "
                f"register in schemas/planar.yaml before backfilling"
            )
        computed.append(", ".join(scopes))

    print(f"Computed Biuniqueness_Scope for {len(computed)} row(s):")
    for pos_name, elements, scope in zip(df["Position_Name"], df["Elements"], computed):
        print(f"  {pos_name:24s} {elements!r:60s} -> {scope}")

    if DRY_RUN:
        print("\nDry run: no file written. Re-run with --apply to write.")
        return

    df["Biuniqueness_Scope"] = computed

    issues = validate_planar_df(df)
    errors = [i for i in issues if i.level == "error"]
    if errors:
        for e in errors:
            print(f"  [ERROR] {e.location}: {e.message}")
        raise SystemExit("validate_planar_df found error(s) after backfill — aborting write.")

    df.to_csv(TARGET, sep="\t", index=False)
    print(f"\nWrote Biuniqueness_Scope into {TARGET}")


if __name__ == "__main__":
    main()
