#!/usr/bin/env Rscript
# Porting check for chart 6 (per-class laminar forests),
# docs/PLAN_planarsviz_library.md section 7 steps 3-6.
#
# Default (nyan1308): for every forest in the bundle, evaluates the generated
# script OlderFiles/planarsviz_superseded/results/nyan1308_<id>_laminar_forest.r in memory (ggsave disabled;
# file untouched) and builds the library forest; compares every tree's
# ggplot_build() data layer by layer; renders the library forest at the
# script's 20x14 in canvas and pixel-compares it with the frozen reference.
# library-only (shifted test data): render only, beside the nyan1308 render,
# under results/chart_checks/comparisons/shifted_nyan/shifted/.
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_forests.R
#   Rscript scripts/planarsviz_checks/check_forests.R results/chart_data/shifted_nyan shifted_nyan library-only

args <- commandArgs(trailingOnly = TRUE)
bundle_dir <- if (length(args) >= 1) args[[1]] else "results/chart_data/nyan1308"
prefix <- if (length(args) >= 2) args[[2]] else "nyan1308"
library_only <- length(args) >= 3 && args[[3]] == "library-only"
python <- "/Users/jcgood/gitrepos/planars/.venv/bin/python"
source("scripts/planarsviz_checks/superseded.R")

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
ids <- vapply(jsonlite::read_json(file.path(bundle_dir, "data", "forests.json")), function(f) f$forest_id, character(1))

plain <- function(df) {
  df <- as.data.frame(df)
  keep <- vapply(df, function(v) is.atomic(v), logical(1))
  df <- df[keep]
  df[] <- lapply(df, function(v) if (is.factor(v)) as.character(v) else as.vector(v))
  rownames(df) <- NULL
  df
}
compare <- function(ref, new_png, out_png) {
  system2(python, c("scripts/planarsviz_compare.py", shQuote(ref), shQuote(new_png), shQuote(out_png)), stdout = TRUE)
}
out_dir <- file.path(bundle_dir, "plots")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
cmp_dir <- file.path(dirname(dirname(bundle_dir)), "chart_checks", "comparisons", prefix, if (library_only) "shifted" else "")
dir.create(cmp_dir, recursive = TRUE, showWarnings = FALSE)

all_ok <- TRUE
for (id in ids) {
  pl <- suppressMessages(suppressWarnings(plot_laminar_forest(bundle, id)))
  problems <- character()
  if (!library_only) {
    src <- readLines(superseded("results", paste0("nyan1308_", id, "_laminar_forest.r")))
    src <- src[!startsWith(src, "ggsave(")]
    orig <- new.env()
    suppressMessages(suppressWarnings(eval(parse(text = src), envir = orig)))
    parts <- attr(pl, "planarsviz_parts")
    for (i in seq_along(parts)) {
      po <- get(sprintf("nyan1308_%s_treeplot%d", id, i), envir = orig)
      bo <- suppressMessages(suppressWarnings(ggplot2::ggplot_build(po)))
      bl <- suppressMessages(suppressWarnings(ggplot2::ggplot_build(parts[[i]])))
      if (length(bo$data) != length(bl$data)) {
        problems <- c(problems, sprintf("tree %d layer count", i)); next
      }
      for (k in seq_along(bo$data)) {
        a <- plain(bo$data[[k]]); b2 <- plain(bl$data[[k]])
        cols <- intersect(names(a), names(b2))
        res <- all.equal(a[cols], b2[cols], check.attributes = FALSE)
        if (!isTRUE(res)) problems <- c(problems, sprintf("tree %d layer %d: %s", i, k, paste(head(res, 2), collapse = "; ")))
      }
    }
    if (!exists(sprintf("nyan1308_%s_treeplot%d", id, length(parts) + 1), envir = orig) == FALSE) {
      problems <- c(problems, "script has more trees than the library")
    }
  }
  size <- attr(pl, "planarsviz_size")
  folder <- attr(pl, "planarsviz_folder")
  cmp_out <- file.path(cmp_dir, folder)
  dir.create(cmp_out, recursive = TRUE, showWarnings = FALSE)
  base <- paste0(prefix, "_", id, "_laminar_forest")
  pdf_path <- file.path(out_dir, paste0(base, ".pdf"))
  suppressMessages(suppressWarnings(ggplot2::ggsave(pdf_path, pl, width = size[["width"]], height = size[["height"]],
                                                    units = attr(pl, "planarsviz_units"))))
  png_stem <- file.path(tempdir(), base)
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(png_stem)))
  if (library_only) {
    nyan_pdf <- file.path("results", "nyan1308", folder, paste0("nyan1308_", id, "_laminar_forest.pdf"))
    if (file.exists(nyan_pdf)) {
      nyan_stem <- file.path(tempdir(), paste0("nyan_", id))
      system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(nyan_pdf), shQuote(nyan_stem)))
      cat(base, ": rendered; side by side with nyan1308: ",
          compare(paste0(nyan_stem, ".png"), paste0(png_stem, ".png"), file.path(cmp_out, paste0(base, ".png"))), "\n")
    } else {
      cat(base, ": rendered; no nyan1308 counterpart\n")
    }
    next
  }
  ref <- file.path(dirname(dirname(bundle_dir)), "chart_checks", "reference", prefix, folder, paste0(base, ".png"))
  if (length(problems)) all_ok <- FALSE
  cat(base, ": ", if (length(problems)) paste("NUMBERS DIFFER:", paste(problems, collapse = " | ")) else "numbers identical",
      "; pixels: ", compare(ref, paste0(png_stem, ".png"), file.path(cmp_out, paste0(base, ".png"))), "\n", sep = "")
}
if (!library_only) cat(if (all_ok) "ALL NUMBER CHECKS PASSED\n" else "SOME NUMBER CHECKS FAILED\n")
