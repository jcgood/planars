#!/usr/bin/env Rscript
# Porting check for chart 18 (boundary-strength overlay, full and without
# tonosegmental), docs/PLAN_planarsviz_library.md section 7 steps 3-6.
#
# Default (nyan1308): evaluates scripts/analysis/boundary_strength_plot.r's
# function definition in memory with ggsave replaced by a function that
# keeps the plot (nothing is written), calls it for both variants on the
# committed TSVs, builds the same charts with
# plot_boundary_strength_overlay(), compares ggplot_build() data, renders at
# 13x7 in and pixel-compares with the frozen references.
# library-only (shifted test data): render only, beside the nyan1308 renders.
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_boundary_strength_overlay.R
#   Rscript scripts/planarsviz_checks/check_boundary_strength_overlay.R results/planarsviz/shifted_nyan shifted_nyan library-only

args <- commandArgs(trailingOnly = TRUE)
bundle_dir <- if (length(args) >= 1) args[[1]] else "results/planarsviz/nyan1308"
prefix <- if (length(args) >= 2) args[[2]] else "nyan1308"
library_only <- length(args) >= 3 && args[[3]] == "library-only"
python <- "/Users/jcgood/gitrepos/planars/.venv/bin/python"
source("scripts/planarsviz_checks/superseded.R")

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

plain <- function(df) {
  df <- as.data.frame(df)
  df <- df[vapply(df, is.atomic, logical(1))]
  df[] <- lapply(df, function(v) if (is.factor(v)) as.character(v) else as.vector(v))
  rownames(df) <- NULL
  df
}
build <- function(p) suppressMessages(suppressWarnings(ggplot2::ggplot_build(p)))
same_data <- function(po, pl, what) {
  bo <- build(po); bl <- build(pl)
  if (length(bo$data) != length(bl$data)) return(sprintf("%s: layer count", what))
  out <- character()
  for (k in seq_along(bo$data)) {
    a <- plain(bo$data[[k]]); b2 <- plain(bl$data[[k]])
    cols <- intersect(names(a), names(b2))
    if (!setequal(names(a), names(b2))) out <- c(out, sprintf("%s layer %d: columns differ", what, k))
    res <- all.equal(a[cols], b2[cols], check.attributes = FALSE)
    if (!isTRUE(res)) out <- c(out, sprintf("%s layer %d: %s", what, k, paste(head(res, 2), collapse = "; ")))
  }
  y_breaks <- function(b) b$layout$panel_params[[1]]$y$breaks
  if (!identical(y_breaks(bo), y_breaks(bl))) out <- c(out, sprintf("%s: y breaks", what))
  out
}
compare <- function(ref, new_png, out_png) {
  system2(python, c("scripts/planarsviz_compare.py", shQuote(ref), shQuote(new_png), shQuote(out_png)), stdout = TRUE)
}
cmp_dir <- file.path(dirname(bundle_dir), "comparisons", if (library_only) "shifted" else "")
dir.create(cmp_dir, recursive = TRUE, showWarnings = FALSE)
subset_ids <- vapply(jsonlite::read_json(file.path(bundle_dir, "data", "subsets.json")),
                     function(s) s$subset_id, character(1))

orig <- NULL
if (!library_only) {
  orig <- new.env()
  assign("ggsave", function(filename, plot, ...) assign("captured", plot, envir = orig), envir = orig)
  src <- readLines(superseded("scripts", "analysis", "boundary_strength_plot.r"))
  first_call <- grep("^plot_boundary_strength\\(", src)[[1]]
  suppressMessages(suppressWarnings(eval(parse(text = src[seq_len(first_call - 1)]), envir = orig)))
}

cases <- list(
  list(name = "boundary_strength_overlay", subset = NULL,
       tsv = "results/nyan1308_boundary_strength.tsv", colours = c(Left = "#0072B2", Right = "#E69F00")),
  list(name = "boundary_strength_overlay_no_tono", subset = "no_tono",
       tsv = "results/nyan1308_boundary_strength_no_tono.tsv", colours = c(Left = "#009E73", Right = "#CC79A7"))
)

all_ok <- TRUE
for (case in cases) {
  base <- paste0(prefix, "_", case$name)
  if (!is.null(case$subset) && !case$subset %in% subset_ids) {
    cat(base, ": skipped (bundle has no `", case$subset, "` subset)\n", sep = "")
    next
  }
  pl <- suppressMessages(suppressWarnings(plot_boundary_strength_overlay(bundle, subset = case$subset, colours = case$colours)))
  size <- attr(pl, "planarsviz_size")
  pdf_path <- file.path(bundle_dir, "plots", paste0(base, ".pdf"))
  dir.create(dirname(pdf_path), recursive = TRUE, showWarnings = FALSE)
  suppressMessages(suppressWarnings(ggplot2::ggsave(pdf_path, pl, device = "pdf", width = size[["width"]],
                                                    height = size[["height"]], units = "in")))
  stem <- file.path(tempdir(), base)
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(stem)))
  new_png <- paste0(stem, ".png")

  if (library_only) {
    nyan_pdf <- file.path("results", paste0("nyan1308_", case$name, ".pdf"))
    nyan_stem <- file.path(tempdir(), paste0("nyan_", case$name))
    system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(nyan_pdf), shQuote(nyan_stem)))
    cat(base, ": rendered; side by side with nyan1308: ",
        compare(paste0(nyan_stem, ".png"), new_png, file.path(cmp_dir, paste0(base, ".png"))), "\n", sep = "")
    next
  }

  suppressMessages(suppressWarnings(
    get("plot_boundary_strength", envir = orig)(case$tsv, paste0(case$name, ".pdf"), case$colours)))
  problems <- same_data(get("captured", envir = orig), pl, case$name)
  if (length(problems)) all_ok <- FALSE
  pix <- compare(file.path(dirname(bundle_dir), "reference", paste0(base, ".png")), new_png,
                 file.path(cmp_dir, paste0(base, ".png")))
  cat(base, ": ", if (length(problems)) paste("NUMBERS DIFFER:", paste(head(problems, 5), collapse = " | ")) else "numbers identical",
      "; canvas ", size[["width"]], "x", size[["height"]], " in; pixels: ", pix, "\n", sep = "")
}
if (!library_only) cat(if (all_ok) "ALL NUMBER CHECKS PASSED\n" else "SOME NUMBER CHECKS FAILED\n")
