#!/usr/bin/env Rscript
# Porting check for chart 19 (class-fragmentation permutation test).
#
# This one is unlike the other twelve, and the difference is worth knowing
# before reading its output. Every other chart was ported from a working
# script that still exists, so its check runs that script in memory and
# compares layer by layer. This chart never had such an original: it was
# written directly in R in 2026-09 as scripts/analysis/fragmentation_test_plot.r,
# with no matplotlib version anywhere in this project's history. So the
# reference is the chart that script drew --
# results/planarsviz/reference/nyan1308_fragmentation_test_plot.png, frozen
# before the package could overwrite it -- and this check compares pixels
# against that.
#
# It also checks the numbers, which is the half that catches a real problem:
# the bundle's summary table must equal what class_fragmentation_test.py
# committed to results/, and the null tally must expand back to exactly the
# draws in results/counts-and-chance/nyan1308_fragmentation_null_draws.tsv. That is what proves
# the tally lost nothing.
#
# library-only (shifted test data): render only, beside the nyan1308 render.
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_fragmentation.R
#   Rscript scripts/planarsviz_checks/check_fragmentation.R results/planarsviz/shifted_nyan shifted_nyan library-only

args <- commandArgs(trailingOnly = TRUE)
bundle_dir <- if (length(args) >= 1) args[[1]] else "results/planarsviz/nyan1308"
prefix <- if (length(args) >= 2) args[[2]] else "nyan1308"
library_only <- length(args) >= 3 && args[[3]] == "library-only"
python <- "/Users/jcgood/gitrepos/planars/.venv/bin/python"

lib <- file.path(tempdir(), "planarsviz_lib")
dir.create(lib, showWarnings = FALSE)
status <- system2("R", c("CMD", "INSTALL", "--no-test-load", paste0("--library=", lib),
                         "r/planarsviz"), stdout = FALSE, stderr = FALSE)
if (status != 0) stop("R CMD INSTALL failed")
suppressPackageStartupMessages(library(planarsviz, lib.loc = lib))

if (!file.exists(file.path(bundle_dir, "data", "fragmentation_test.tsv"))) {
  stop("This bundle has no fragmentation tables. Re-export it with\n",
       "  python scripts/analysis/export_planarsviz_data.py --domain-file ... ",
       "--fragmentation-permutations 5000", call. = FALSE)
}

bundle <- read_planars_bundle(bundle_dir)
pl <- plot_fragmentation_test(bundle)
problems <- character()

if (!library_only) {
  # The committed TSVs the standalone script wrote, which the bundle must
  # reproduce exactly -- the same relationship boundary_strength and
  # tree_counts already have with their own committed files.
  summary_lib <- read_planars_fragmentation(bundle)
  class_orig <- utils::read.delim("results/counts-and-chance/nyan1308_class_fragmentation_test.tsv",
                                  stringsAsFactors = FALSE)
  bundle_orig <- utils::read.delim("results/counts-and-chance/nyan1308_bundle_fragmentation_test.tsv",
                                   stringsAsFactors = FALSE)
  orig <- rbind(class_orig, bundle_orig)

  shared <- c("group", "n_tests", "observed_families", "null_mean",
              "null_p05", "null_p95", "p_value_le_observed", "n_permutations", "seed")
  a <- orig[order(orig$group), shared]
  b <- summary_lib[order(summary_lib$group), shared]
  rownames(a) <- NULL
  rownames(b) <- NULL
  if (!isTRUE(all.equal(a, b, check.attributes = FALSE))) {
    problems <- c(problems, "summary table differs from the committed TSVs")
  }

  # The tally must expand back to exactly the committed draws. Compare as
  # sorted counts per group: the tally drops draw order and nothing else.
  draws_orig <- utils::read.delim("results/counts-and-chance/nyan1308_fragmentation_null_draws.tsv",
                                  stringsAsFactors = FALSE)
  draws_lib <- read_planars_fragmentation_null(bundle)
  for (g in sort(unique(draws_orig$group))) {
    o <- sort(draws_orig$family_count[draws_orig$group == g])
    l <- sort(draws_lib$family_count[draws_lib$group == g])
    if (!identical(as.integer(o), as.integer(l))) {
      problems <- c(problems, paste0("null draws differ for ", g))
    }
  }
  # And the kind column must agree with the summary's, or the two panels
  # would be built from different groupings.
  kind_lib <- stats::setNames(summary_lib$kind, summary_lib$group)
  kind_draw <- unique(draws_lib[, c("group", "kind")])
  if (!all(kind_draw$kind == kind_lib[kind_draw$group])) {
    problems <- c(problems, "null tally's kind disagrees with the summary's")
  }
  cat("groups checked: ", nrow(summary_lib),
      "; draws per group: ", length(unique(draws_lib$group)), " x ",
      nrow(draws_lib) / length(unique(draws_lib$group)), "\n", sep = "")
}

size <- attr(pl, "planarsviz_size")
base <- paste0(prefix, "_fragmentation_test_plot")
out_dir <- file.path(bundle_dir, "plots")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
pdf_path <- file.path(out_dir, paste0(base, ".pdf"))
ggplot2::ggsave(pdf_path, pl, device = "pdf", width = size[["width"]], height = size[["height"]],
                units = attr(pl, "planarsviz_units"))
png_stem <- file.path(tempdir(), base)
system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(png_stem)))
compare <- function(ref, new_png, out_png) {
  system2(python, c("scripts/planarsviz_compare.py", shQuote(ref), shQuote(new_png), shQuote(out_png)), stdout = TRUE)
}
cmp_dir <- file.path(dirname(bundle_dir), "comparisons", if (library_only) "shifted" else "")
folder <- attr(pl, "planarsviz_folder")
cmp_out <- file.path(cmp_dir, folder)
dir.create(cmp_out, recursive = TRUE, showWarnings = FALSE)

if (library_only) {
  nyan_pdf <- file.path("results", "nyan1308_fragmentation_test_plot.pdf")
  nyan_stem <- file.path(tempdir(), "nyan_fragmentation")
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(nyan_pdf), shQuote(nyan_stem)))
  cat(base, ": rendered; side by side with nyan1308: ",
      compare(paste0(nyan_stem, ".png"), paste0(png_stem, ".png"), file.path(cmp_out, paste0(base, ".png"))), "\n")
} else {
  ref <- file.path(dirname(bundle_dir), "reference", folder, paste0(base, ".png"))
  pixel <- compare(ref, paste0(png_stem, ".png"), file.path(cmp_out, paste0(base, ".png")))
  cat(base, ": ", if (length(problems)) paste("NUMBERS DIFFER:", paste(problems, collapse = " | ")) else "numbers identical",
      "; pixels: ", pixel, "\n", sep = "")
}
