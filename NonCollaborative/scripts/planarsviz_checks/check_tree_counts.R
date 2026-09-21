#!/usr/bin/env Rscript
# Porting check for chart 16 (tree-count bar charts), a cross-language port:
# docs/PLAN_planarsviz_library.md section 4.3 step 4.
#
# Renders plot_tree_counts() for all four charts at the matplotlib canvas
# sizes and pixel-compares them with the frozen references. Fonts differ
# between matplotlib and ggplot, so 0% is not expected: judge the comparison
# images by bar lengths, order, colours, label positions and margins. For the
# two transparent charts, also renders with `pdftocairo -png -transp` and
# reports how much of the image is fully transparent, for the port and for
# the frozen matplotlib reference (results/planarsviz/reference/
# <name>_transp.png -- kept because the matplotlib that drew it was removed
# in cutover step C3).
# library-only (shifted test data): render only, beside the nyan1308 renders.
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_tree_counts.R
#   Rscript scripts/planarsviz_checks/check_tree_counts.R results/planarsviz/shifted_nyan shifted_nyan library-only

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
suppressPackageStartupMessages({
  library(planarsviz, lib.loc = lib)
  library(ggplot2)
})
bundle <- read_planars_bundle(bundle_dir)

compare <- function(ref, new_png, out_png) {
  system2(python, c("scripts/planarsviz_compare.py", shQuote(ref), shQuote(new_png), shQuote(out_png)), stdout = TRUE)
}
transparency <- function(pdf_path, stem) {
  system2("pdftocairo", c("-png", "-transp", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(stem)))
  transparency_of(paste0(stem, ".png"))
}
transparency_of <- function(png_path) {
  system2(python, c("scripts/planarsviz_checks/check_transparency.py", shQuote(png_path)), stdout = TRUE)
}
cmp_dir <- file.path(dirname(bundle_dir), "comparisons", if (library_only) "shifted" else "")
dir.create(cmp_dir, recursive = TRUE, showWarnings = FALSE)

for (chart in c("by_class", "bundles", "all", "without_adjacent")) {
  base <- paste0(prefix, "_tree_count_", chart)
  p <- plot_tree_counts(bundle, chart)
  size <- attr(p, "planarsviz_size")
  folder <- attr(p, "planarsviz_folder")
  cmp_out <- file.path(cmp_dir, folder)
  dir.create(cmp_out, recursive = TRUE, showWarnings = FALSE)
  pdf_path <- file.path(bundle_dir, "plots", paste0(base, ".pdf"))
  dir.create(dirname(pdf_path), recursive = TRUE, showWarnings = FALSE)
  suppressMessages(ggplot2::ggsave(pdf_path, p, width = size[["width"]], height = size[["height"]], units = "in"))
  stem <- file.path(tempdir(), base)
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(stem)))

  ref_base <- paste0("nyan1308_tree_count_", chart)
  ref_png <- if (library_only) {
    nyan_stem <- file.path(tempdir(), paste0("nyan_", chart))
    system2("pdftoppm", c("-png", "-r", "100", "-singlefile",
                          shQuote(file.path("results", paste0(ref_base, ".pdf"))),
                          shQuote(nyan_stem)))
    paste0(nyan_stem, ".png")
  } else {
    file.path(dirname(bundle_dir), "reference", folder, paste0(ref_base, ".png"))
  }
  cat(base, " (", size[["width"]], "x", size[["height"]], " in): ",
      compare(ref_png, paste0(stem, ".png"), file.path(cmp_out, paste0(base, ".png"))), "\n", sep = "")

  if (isTRUE(attr(p, "planarsviz_transparent"))) {
    cat("  port:      ", transparency(pdf_path, paste0(stem, "_transp")), "\n")
    if (!library_only) {
      # The frozen matplotlib render, kept with the other frozen references.
      # Not results/<name>.pdf: since cutover step C1 that file is the
      # library's own output, so reading it compared the port with itself.
      cat("  reference: ", transparency_of(
        file.path(dirname(bundle_dir), "reference", folder, paste0(ref_base, "_transp.png"))), "\n")
    }
  }
}
