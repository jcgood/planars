"""Equivalent of nyan1308_forestspans_plot.pdf (make_forestspans_table.py),
restricted to non-tonosegmental domain types.

Reuses make_forestspans_table.py's make_r_plot_script() unmodified -- that
function only needs (rows, n_families, span_types), it doesn't care which
domain-type subset produced them -- and recomputes those three inputs here
via laminar_analysis.main(subset=[...]) instead of the unfiltered
compute_forest_spans(), which has no subset parameter.

Layer numbers are NOT carried over from the full-dataset forestspans chart:
excluding tonosegmental changes which spans exist at all (any span produced
only by tonosegmental tests disappears; one produced by tonosegmental
alongside other domain types survives with reduced convergence), so this is
a fresh analysis with its own span inventory, numbered the same way
(Size ascending, Left_Edge ascending, then inverted) as any other
independent laminar-family analysis in this project -- not a filtered view
of the original chart's own numbering.

Output: results/nyan1308_forestspans_plot_no_tono.r (+ .pdf)

Usage:
    python make_forestspans_table_no_tono.py
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(__file__)
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))  # make_forestspans_table.py lives in scripts/

import laminar_analysis as la
from make_forestspans_table import make_r_plot_script, run_r_script

RESULTS_DIR = os.path.join(SCRIPT_DIR, "..", "..", "results")
DOMAINS_DIR = os.path.join(SCRIPT_DIR, "..", "..", "domains")

NON_TONOSEGMENTAL = ["morphosyntactic", "phonological", "length", "intonational"]


def compute_forest_spans_subset(domain_file, subset):
    import tempfile

    result = la.main(
        domain_file=domain_file,
        domains_dir=DOMAINS_DIR,
        output_dir=tempfile.gettempdir(),  # this script doesn't want the R script main() writes
        subset=subset,
        show_trees=False,
    )
    spans = result["spans"]
    span_family_count = result["span_family_count"]
    n_families = result["n_families"]

    ordered = sorted(spans, key=lambda s: (s.size, s.left))
    n = len(ordered)
    reverse_layer = {(s.left, s.right): n + 1 - i for i, s in enumerate(ordered, start=1)}

    rows = [
        (reverse_layer[(s.left, s.right)], s.left, s.right, span_family_count.get(s, 0))
        for s in spans
    ]
    rows.sort(key=lambda r: (-r[3], r[0]))

    span_types = {(s.left, s.right): tuple(sorted(s.domain_types)) for s in spans}
    return rows, n_families, span_types


def main():
    domain_file = "domains_nyan1308.tsv"
    rows, n_families, span_types = compute_forest_spans_subset(domain_file, NON_TONOSEGMENTAL)
    print(f"{n_families} maximal laminar families (no tonosegmental); {len(rows)} distinct spans")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    r_script = make_r_plot_script(rows, n_families, span_types)
    # make_r_plot_script hardcodes the "nyan1308_forestspans_plot.pdf" output
    # filename inside the generated ggsave() call -- retarget it here rather
    # than touch that shared function, so this variant never overwrites the
    # original.
    r_script = r_script.replace(
        "nyan1308_forestspans_plot.pdf", "nyan1308_forestspans_plot_no_tono.pdf"
    )
    r_script_path = os.path.join(RESULTS_DIR, "nyan1308_forestspans_plot_no_tono.r")
    with open(r_script_path, "w") as f:
        f.write(r_script)
    print("Wrote %s" % r_script_path)

    if run_r_script(r_script_path):
        print("Wrote %s" % os.path.join(RESULTS_DIR, "nyan1308_forestspans_plot_no_tono.pdf"))


if __name__ == "__main__":
    main()
