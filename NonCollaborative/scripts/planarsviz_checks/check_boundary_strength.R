#!/usr/bin/env Rscript
# Porting check for chart 17 (boundary-strength bars, no-tonosegmental bars,
# distributions), a cross-language port: docs/PLAN_planarsviz_library.md
# section 4.3 step 4.
#
# Renders plot_boundary_strength() (full and subset = "no_tono") and
# plot_boundary_strength_distributions() at the matplotlib canvas sizes and
# pixel-compares them with the frozen references. Fonts differ between
# matplotlib and ggplot, so 0% is not expected: judge the comparison images
# by bar heights, marker positions, curve shapes, ticks, labels and margins.
# The no-tono legend deliberately says its own family count (24), not the
# reference's typed-in 69.
# library-only (shifted test data): render only, beside the nyan1308 renders,
# under results/chart_checks/comparisons/shifted_nyan/shifted/.
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_boundary_strength.R
#   Rscript scripts/planarsviz_checks/check_boundary_strength.R results/chart_data/shifted_nyan shifted_nyan library-only

args <- commandArgs(trailingOnly = TRUE)
bundle_dir <- if (length(args) >= 1) args[[1]] else "results/chart_data/nyan1308"
prefix <- if (length(args) >= 2) args[[2]] else "nyan1308"
library_only <- length(args) >= 3 && args[[3]] == "library-only"
python <- "/Users/jcgood/gitrepos/planars/.venv/bin/python"

lib <- file.path(tempdir(), "planarsviz_lib")
dir.create(lib, showWarnings = FALSE)
status <- system2("R", c("CMD", "INSTALL", "--no-test-load", paste0("--library=", lib),
                         "planarsviz"), stdout = FALSE, stderr = FALSE)
if (status != 0) stop("R CMD INSTALL failed")
suppressPackageStartupMessages({
  library(planarsviz, lib.loc = lib)
  library(ggplot2)
})
bundle <- read_planars_bundle(bundle_dir)

compare <- function(ref, new_png, out_png) {
  system2(python, c("scripts/planarsviz_compare.py", shQuote(ref), shQuote(new_png), shQuote(out_png)), stdout = TRUE)
}
cmp_dir <- file.path(dirname(dirname(bundle_dir)), "chart_checks", "comparisons", prefix, if (library_only) "shifted" else "")
dir.create(cmp_dir, recursive = TRUE, showWarnings = FALSE)
subset_ids <- vapply(jsonlite::read_json(file.path(bundle_dir, "data", "subsets.json")),
                     function(s) s$subset_id, character(1))

cases <- list(
  list(name = "boundary_strength", make = function() plot_boundary_strength(bundle), subset = NULL),
  list(name = "boundary_strength_no_tono", make = function() plot_boundary_strength(bundle, subset = "no_tono"), subset = "no_tono"),
  list(name = "boundary_strength_distributions", make = function() plot_boundary_strength_distributions(bundle), subset = NULL)
)

for (case in cases) {
  base <- paste0(prefix, "_", case$name)
  if (!is.null(case$subset) && !case$subset %in% subset_ids) {
    cat(base, ": skipped (bundle has no `", case$subset, "` subset)\n", sep = "")
    next
  }
  p <- suppressMessages(suppressWarnings(case$make()))
  size <- attr(p, "planarsviz_size")
  folder <- attr(p, "planarsviz_folder")
  cmp_out <- file.path(cmp_dir, folder)
  dir.create(cmp_out, recursive = TRUE, showWarnings = FALSE)
  pdf_path <- file.path(bundle_dir, "plots", paste0(base, ".pdf"))
  dir.create(dirname(pdf_path), recursive = TRUE, showWarnings = FALSE)
  suppressMessages(suppressWarnings(ggplot2::ggsave(pdf_path, p, width = size[["width"]], height = size[["height"]], units = "in")))
  stem <- file.path(tempdir(), base)
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(stem)))

  ref_base <- paste0("nyan1308_", case$name)
  ref_png <- if (library_only) {
    nyan_stem <- file.path(tempdir(), paste0("nyan_", case$name))
    system2("pdftoppm", c("-png", "-r", "100", "-singlefile",
                          shQuote(file.path("results", "nyan1308", folder, paste0(ref_base, ".pdf"))),
                          shQuote(nyan_stem)))
    paste0(nyan_stem, ".png")
  } else {
    file.path(dirname(dirname(bundle_dir)), "chart_checks", "reference", prefix, folder, paste0(ref_base, ".png"))
  }
  cat(base, " (", size[["width"]], "x", size[["height"]], " in): ",
      compare(ref_png, paste0(stem, ".png"), file.path(cmp_out, paste0(base, ".png"))), "\n", sep = "")
}
