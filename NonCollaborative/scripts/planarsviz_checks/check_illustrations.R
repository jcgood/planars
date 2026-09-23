#!/usr/bin/env Rscript
# Porting check for the illustrations bundle's tree-shape and tree-count-growth
# charts (phase E, docs/PLANARSVIZ_LIBRARY_PROGRESS.md).
#
# tree_shapes_n2/n3/n4/n5: verified in memory once (evaluating the archived
# generate_supercatalan_rows.py + render_supercatalan_rows.r directly, with
# their pdfcrop step skipped) against plot_tree_shapes() at 0.0000% differing
# pixels for all four rows before the frozen references below were made --
# see docs/PLANARSVIZ_LIBRARY_PROGRESS.md's "Phase E" entry for that session.
# This check does not re-run the archived scripts (their loop reuses one `p`
# variable per row, so there is no per-row object left to compare against
# once the loop finishes, and cowplot's composite plots do not decompose via
# ggplot_build() the way an ordinary ggplot object does) -- it pixel-compares
# against those frozen references instead, the same shape as the two
# cross-language ports (check_boundary_strength.R, check_tree_counts.R) use
# for the same reason: the original isn't practical to introspect in-process.
# scripts/planarsviz_checks/verify_tree_shapes_export.py is what checks the
# data (tree_shapes.tsv, tree_count_growth.tsv) against catalan.py directly.
#
# One deliberate difference from the pre-port PDFs still committed at
# results/illustrations/supercatalan_trees_n*.pdf: those were run through
# pdfcrop afterward (trimmed to content plus a 5bp margin); this package
# never post-processes a chart's PDF after ggsave(), for any chart, so
# plot_tree_shapes() draws at its own fixed canvas instead. The size differs
# by a few percent; the tree drawings inside it are identical (confirmed
# against the *un-cropped* PDF render_supercatalan_rows.r itself produces,
# before generate_supercatalan_rows.py's pdfcrop step runs).
#
# tree_count_growth is a new chart (the old scripts only ever showed this as
# tree_counting_equations.tex's static table), so there is no original to
# port from -- this only pixel-compares against its own frozen reference, to
# catch future drift.
#
# random_tree_overlay is checked by check_renderer.py's blanket pass (same
# frozen-reference comparison) but not here: there is no fixed drawing to
# port against, since the whole point of a random sample is that a fresh one
# looks different from the last. scripts/planarsviz_checks/
# verify_random_trees_export.py is what checks the sample is well-formed and
# reproduces from its recorded seed.
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_illustrations.R

python <- "/Users/jcgood/gitrepos/planars/.venv/bin/python"

lib <- file.path(tempdir(), "planarsviz_lib")
dir.create(lib, showWarnings = FALSE)
status <- system2("R", c("CMD", "INSTALL", "--no-test-load", paste0("--library=", lib),
                         "r/planarsviz"), stdout = FALSE, stderr = FALSE)
if (status != 0) stop("R CMD INSTALL failed")
suppressPackageStartupMessages({
  library(planarsviz, lib.loc = lib)
  library(ggplot2)
})

ref <- read_planars_illustrations("results/planarsviz/illustrations")
bundle <- read_planars_bundle("results/planarsviz/nyan1308")

compare <- function(reference, new_png, out_png) {
  system2(python, c("scripts/planarsviz_compare.py", shQuote(reference), shQuote(new_png), shQuote(out_png)),
          stdout = TRUE)
}
reference_dir <- file.path("results", "planarsviz", "reference", "illustrations")
cmp_dir <- file.path("results", "planarsviz", "comparisons", "illustrations")
dir.create(cmp_dir, recursive = TRUE, showWarnings = FALSE)
out_dir <- file.path("results", "planarsviz", "illustrations", "plots")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

render_and_compare <- function(base, p) {
  size <- attr(p, "planarsviz_size")
  pdf_path <- file.path(out_dir, paste0(base, ".pdf"))
  suppressMessages(suppressWarnings(ggplot2::ggsave(pdf_path, p, device = "pdf", width = size[["width"]],
                                                    height = size[["height"]], units = attr(p, "planarsviz_units"))))
  stem <- file.path(tempdir(), base)
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(stem)))
  pix <- compare(file.path(reference_dir, paste0(base, ".png")), paste0(stem, ".png"),
                file.path(cmp_dir, paste0(base, ".png")))
  cat(base, " (", size[["width"]], "x", size[["height"]], " ", attr(p, "planarsviz_units"), "): ", pix, "\n", sep = "")
}

for (n in sort(unique(ref$tree_shapes$n))) {
  render_and_compare(paste0("illustrations_tree_shapes_n", n),
                     suppressMessages(suppressWarnings(plot_tree_shapes(ref, n))))
}
render_and_compare("illustrations_tree_count_growth",
                   suppressMessages(suppressWarnings(plot_tree_count_growth(ref, bundle))))

cat("(random_tree_overlay is not pixel-checked here -- see this script's header comment; ",
    "verify_random_trees_export.py checks its data.)\n", sep = "")
