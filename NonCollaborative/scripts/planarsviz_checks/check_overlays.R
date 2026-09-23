#!/usr/bin/env Rscript
# Porting check for charts 7-9 (stacked laminar overlays),
# docs/PLAN_planarsviz_library.md section 7 steps 3-6.
#
# Default (nyan1308): evaluates each generated/hand-edited script in memory
# (ggsave disabled; files untouched) and builds the same chart with
# plot_laminar_overlay(); compares every tree's ggplot_build() data and the
# legend plot's data; renders the chart and its legend version at 20x14 in
# and pixel-compares both with the frozen references.
#   chart 7: OlderFiles/planarsviz_superseded/results/nyan1308_laminar_overlay.r      -> plot_laminar_overlay(bundle)
#   chart 8: OlderFiles/planarsviz_superseded/results/nyan1308_all_families_labeled.r -> groups = "all", divisor 1, exponent 0.75
#   chart 9: OlderFiles/planarsviz_superseded/results/nyan1308_all_families_labeled_wordhood.r -> chart 8 + highlight
# The legend's thickness swatch was fixed on 2026-09-15 (it now follows the
# lines' exponent). The exact comparison with the old scripts uses
# legend_thickness_exponent = 0.5, which reproduces their legend; the files
# written to plots/ and comparisons/ are the library's default (fixed)
# charts, and the report gives both pixel figures.
# library-only (shifted test data): render only, beside the nyan1308 renders,
# under results/chart_checks/comparisons/shifted_nyan/shifted/.
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_overlays.R
#   Rscript scripts/planarsviz_checks/check_overlays.R results/chart_data/shifted_nyan shifted_nyan library-only

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
    res <- all.equal(a[cols], b2[cols], check.attributes = FALSE)
    if (!isTRUE(res)) out <- c(out, sprintf("%s layer %d: %s", what, k, paste(head(res, 2), collapse = "; ")))
  }
  out
}
compare <- function(ref, new_png, out_png) {
  system2(python, c("scripts/planarsviz_compare.py", shQuote(ref), shQuote(new_png), shQuote(out_png)), stdout = TRUE)
}
# Saves the PDF at pdf_path and returns a 100 dpi PNG made in tempdir().
render <- function(p, pdf_path) {
  dir.create(dirname(pdf_path), recursive = TRUE, showWarnings = FALSE)
  suppressMessages(suppressWarnings(ggplot2::ggsave(pdf_path, p, width = 20, height = 14, units = "in")))
  stem <- file.path(tempdir(), paste0(basename(dirname(pdf_path)), "_", sub("\\.pdf$", "", basename(pdf_path))))
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(stem)))
  paste0(stem, ".png")
}
cmp_dir <- file.path(dirname(dirname(bundle_dir)), "chart_checks", "comparisons", prefix, if (library_only) "shifted" else "")
dir.create(cmp_dir, recursive = TRUE, showWarnings = FALSE)
plots_dir <- file.path(bundle_dir, "plots")

cases <- list(
  list(name = "laminar_overlay", script = "nyan1308_laminar_overlay.r", args = list()),
  list(name = "all_families_labeled", script = "nyan1308_all_families_labeled.r",
       args = list(groups = "all", alpha_divisor = 1, thickness_exponent = 0.75)),
  list(name = "all_families_labeled_wordhood", script = "nyan1308_all_families_labeled_wordhood.r",
       args = list(groups = "all", alpha_divisor = 1, thickness_exponent = 0.75, highlight = "orthographic_word"))
)

all_ok <- TRUE
for (case in cases) {
  if (library_only && !is.null(case$args$highlight) &&
      !nrow(utils::read.delim(file.path(bundle_dir, "data", "highlights.tsv")))) {
    cat(prefix, "_", case$name, ": skipped (no highlights in this bundle)\n", sep = "")
    next
  }
  make <- function(...) suppressMessages(suppressWarnings(do.call(plot_laminar_overlay, c(list(bundle), case$args, list(...)))))
  pl <- make()
  pl_legend <- make(legend = TRUE)
  base <- paste0(prefix, "_", case$name)
  folder <- attr(pl, "planarsviz_folder")
  cmp_out <- file.path(cmp_dir, folder)
  dir.create(cmp_out, recursive = TRUE, showWarnings = FALSE)
  new_png <- render(pl, file.path(plots_dir, paste0(base, ".pdf")))
  new_legend_png <- render(pl_legend, file.path(plots_dir, paste0(base, "_legend.pdf")))

  if (library_only) {
    for (suffix in c("", "_legend")) {
      nyan_pdf <- file.path("results", "nyan1308", folder, paste0("nyan1308_", case$name, suffix, ".pdf"))
      stem <- file.path(tempdir(), paste0("nyan_", case$name, suffix))
      system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(nyan_pdf), shQuote(stem)))
      cat(base, suffix, ": rendered; side by side with nyan1308: ",
          compare(paste0(stem, ".png"), if (suffix == "") new_png else new_legend_png,
                  file.path(cmp_out, paste0(base, suffix, ".png"))), "\n", sep = "")
    }
    next
  }

  # The old scripts' legend, for the exact comparison.
  pl_legend_old <- make(legend = TRUE, legend_thickness_exponent = 0.5)
  old_legend_png <- render(pl_legend_old, file.path(tempdir(), "as_generated", paste0(base, "_legend.pdf")))

  src <- readLines(superseded("results", case$script))
  src <- src[!startsWith(src, "ggsave(")]
  orig <- new.env()
  suppressMessages(suppressWarnings(eval(parse(text = src), envir = orig)))
  problems <- character()
  parts <- attr(pl, "planarsviz_parts")
  # generated names are <group>treeplot<i>; order them as the script stacks them
  forest_src <- src[grep("^forest <- \\(", src):length(src)]
  stack_order <- trimws(sub("\\+$", "", grep("treeplot[0-9]+ \\+$", forest_src, value = TRUE)))
  if (length(stack_order) != length(parts)) {
    problems <- c(problems, sprintf("tree count %d vs %d", length(stack_order), length(parts)))
  } else {
    for (i in seq_along(parts)) problems <- c(problems, same_data(get(stack_order[[i]], envir = orig), parts[[i]], stack_order[[i]]))
  }
  problems <- c(problems, same_data(get("legend_plot", envir = orig), attr(pl_legend_old, "planarsviz_legend_plot"), "legend"))
  if (length(problems)) all_ok <- FALSE
  ref_dir <- file.path(dirname(dirname(bundle_dir)), "chart_checks", "reference", prefix, folder)
  pix <- compare(file.path(ref_dir, paste0(base, ".png")), new_png, file.path(cmp_out, paste0(base, ".png")))
  pix_old <- compare(file.path(ref_dir, paste0(base, "_legend.png")), old_legend_png,
                     file.path(tempdir(), paste0(base, "_legend_as_generated_cmp.png")))
  pix_fixed <- compare(file.path(ref_dir, paste0(base, "_legend.png")), new_legend_png,
                       file.path(cmp_out, paste0(base, "_legend.png")))
  cat(base, ": ", if (length(problems)) paste("NUMBERS DIFFER:", paste(head(problems, 5), collapse = " | ")) else "numbers identical",
      "\n  chart pixels: ", pix,
      "\n  legend as generated (swatch exponent 0.5): ", pix_old,
      "\n  legend, library default (swatch follows exponent): ", pix_fixed, "\n", sep = "")
}
if (!library_only) cat(if (all_ok) "ALL NUMBER CHECKS PASSED\n" else "SOME NUMBER CHECKS FAILED\n")
