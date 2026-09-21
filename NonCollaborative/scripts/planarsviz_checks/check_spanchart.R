#!/usr/bin/env Rscript
# Porting check for chart 15 (span-frequency chart),
# docs/PLAN_planarsviz_library.md section 7 steps 3-6.
#
# Default (nyan1308): builds the chart from the working script
# (results/laminar_spanchart.r, evaluated in memory with ggsave disabled; the
# file is not modified) and from the library; compares ggplot_build() data,
# title, x labels and alpha-legend name; renders the library chart at the
# working canvas and pixel-compares it with the frozen reference.
# library-only (shifted test data): render only, beside the nyan1308 render.
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_spanchart.R
#   Rscript scripts/planarsviz_checks/check_spanchart.R results/planarsviz/shifted_nyan shifted_nyan library-only

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
suppressPackageStartupMessages(library(planarsviz, lib.loc = lib))
bundle <- read_planars_bundle(bundle_dir)
pl <- plot_span_chart(bundle)
# The axis shows every position from 2026-09-19; positions = "drawn" is the
# original, which the comparisons against the old script use.
pl_old <- plot_span_chart(bundle, positions = "drawn")
problems <- character()

plain <- function(df) {
  df <- as.data.frame(df)
  df[] <- lapply(df, function(v) if (is.factor(v)) as.character(v) else as.vector(v))
  rownames(df) <- NULL
  df
}

if (!library_only) {
  src <- readLines(superseded("results", "laminar_spanchart.r"))
  src <- append(src, "ggsave <- function(...) invisible(NULL)", after = grep("^library\\(ggplot2\\)", src))
  orig <- new.env()
  suppressMessages(suppressWarnings(eval(parse(text = src), envir = orig)))
  po <- get("p_spanchart", envir = orig)
  bo <- ggplot2::ggplot_build(po)
  bl <- ggplot2::ggplot_build(pl_old)
  if (length(bo$data) != length(bl$data)) problems <- c(problems, "layer count differs")
  for (k in seq_along(bo$data)) {
    a <- plain(bo$data[[k]]); b2 <- plain(bl$data[[k]])
    cols <- intersect(names(a), names(b2))
    res <- all.equal(a[cols], b2[cols], check.attributes = FALSE, tolerance = 1e-6)
    if (!isTRUE(res)) problems <- c(problems, sprintf("layer %d: %s", k, paste(res, collapse = "; ")))
  }
  if (!identical(po$labels$title, pl_old$labels$title)) problems <- c(problems, "title differs")
  xo <- bo$layout$panel_params[[1]]$x$get_labels(); xl <- bl$layout$panel_params[[1]]$x$get_labels()
  if (!identical(as.character(xo), as.character(xl))) problems <- c(problems, "x labels differ")
  if (!identical(po$scales$get_scales("alpha")$name, pl_old$scales$get_scales("alpha")$name)) {
    problems <- c(problems, "alpha legend name differs")
  }
}

size <- attr(pl, "planarsviz_size")
base <- paste0(prefix, "_spanchart")
out_dir <- file.path(bundle_dir, "plots")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
pdf_path <- file.path(out_dir, paste0(base, ".pdf"))
ggplot2::ggsave(pdf_path, pl, width = size[["width"]], height = size[["height"]],
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
  nyan_pdf <- file.path("results", "nyan1308_spanchart.pdf")
  nyan_stem <- file.path(tempdir(), "nyan_spanchart")
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(nyan_pdf), shQuote(nyan_stem)))
  cat(base, ": rendered; side by side with nyan1308: ",
      compare(paste0(nyan_stem, ".png"), paste0(png_stem, ".png"), file.path(cmp_out, paste0(base, ".png"))), "\n")
} else {
  ref <- file.path(dirname(bundle_dir), "reference", folder, paste0(base, ".png"))
  cat(base, ": ", if (length(problems)) paste("NUMBERS DIFFER:", paste(problems, collapse = " | ")) else "numbers identical",
      "; pixels: ", compare(ref, paste0(png_stem, ".png"), file.path(cmp_out, paste0(base, ".png"))), "\n", sep = "")
}
