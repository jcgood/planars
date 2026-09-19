#!/usr/bin/env Rscript
# Porting check for chart 12 (conflict groups),
# docs/PLAN_planarsviz_library.md section 7 steps 3-6.
#
# Default (nyan1308): evaluates results/laminar_conflict_groups.r in memory
# (ggsave disabled; file untouched), builds the chart with
# plot_conflict_groups(), compares every tree's ggplot_build() data panel by
# panel (all_tp*, ga_tp*, gb_tp*, gc_tp* against the library's parts in
# order), renders at 24x20 in and pixel-compares with the frozen reference.
# Panel titles were fixed on 2026-09-15 (the old chart's never showed). The
# exact pixel comparison uses panel_titles = FALSE, which reproduces the old
# chart; plots/ and comparisons/ get the library's default (titled) chart,
# and the report gives both pixel figures.
# library-only (shifted test data): render only, beside the nyan1308 render.
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_conflict_groups.R
#   Rscript scripts/planarsviz_checks/check_conflict_groups.R results/planarsviz/shifted_nyan shifted_nyan library-only

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
  out
}
compare <- function(ref, new_png, out_png) {
  system2(python, c("scripts/planarsviz_compare.py", shQuote(ref), shQuote(new_png), shQuote(out_png)), stdout = TRUE)
}
# Saves the PDF at pdf_path (at the chart's own canvas) and returns a 100 dpi PNG made in tempdir().
render <- function(p, pdf_path) {
  size <- attr(p, "planarsviz_size")
  dir.create(dirname(pdf_path), recursive = TRUE, showWarnings = FALSE)
  suppressMessages(suppressWarnings(ggplot2::ggsave(pdf_path, p, width = size[["width"]], height = size[["height"]], units = "in")))
  stem <- file.path(tempdir(), paste0(basename(dirname(pdf_path)), "_", sub("\\.pdf$", "", basename(pdf_path))))
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(stem)))
  paste0(stem, ".png")
}
cmp_dir <- file.path(dirname(bundle_dir), "comparisons", if (library_only) "shifted" else "")
dir.create(cmp_dir, recursive = TRUE, showWarnings = FALSE)

base <- paste0(prefix, "_conflict_groups")
pl <- suppressMessages(suppressWarnings(plot_conflict_groups(bundle)))
size <- attr(pl, "planarsviz_size")
new_png <- render(pl, file.path(bundle_dir, "plots", paste0(base, ".pdf")))

if (library_only) {
  nyan_pdf <- file.path(dirname(bundle_dir), "nyan1308", "plots", "nyan1308_conflict_groups.pdf")
  nyan_stem <- file.path(tempdir(), "nyan_conflict_groups")
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(nyan_pdf), shQuote(nyan_stem)))
  cat(base, ": rendered; side by side with nyan1308: ",
      compare(paste0(nyan_stem, ".png"), new_png, file.path(cmp_dir, paste0(base, ".png"))), "\n", sep = "")
} else {
  pl_old <- suppressMessages(suppressWarnings(plot_conflict_groups(bundle, panel_titles = FALSE)))
  old_png <- render(pl_old, file.path(tempdir(), "as_generated", paste0(base, ".pdf")))

  src <- readLines(file.path("results", "laminar_conflict_groups.r"))
  src <- src[!startsWith(src, "ggsave(")]
  orig <- new.env()
  suppressMessages(suppressWarnings(eval(parse(text = src), envir = orig)))
  parts <- attr(pl_old, "planarsviz_parts")
  prefixes <- c("all_tp", "ga_tp", "gb_tp", "gc_tp")
  problems <- character()
  if (length(parts) != length(prefixes)) problems <- sprintf("panel count %d vs %d", length(parts), length(prefixes))
  for (j in seq_along(prefixes)) {
    names_j <- grep(paste0("^", prefixes[[j]], "[0-9]+$"), ls(orig), value = TRUE)
    names_j <- names_j[order(as.integer(sub(prefixes[[j]], "", names_j)))]
    if (length(names_j) != length(parts[[j]])) {
      problems <- c(problems, sprintf("%s: %d trees vs %d", prefixes[[j]], length(names_j), length(parts[[j]])))
      next
    }
    for (i in seq_along(names_j)) problems <- c(problems, same_data(get(names_j[[i]], envir = orig), parts[[j]][[i]], names_j[[i]]))
  }
  ref <- file.path(dirname(bundle_dir), "reference", paste0(base, ".png"))
  pix_old <- compare(ref, old_png, file.path(tempdir(), paste0(base, "_as_generated_cmp.png")))
  pix <- compare(ref, new_png, file.path(cmp_dir, paste0(base, ".png")))
  cat(base, ": ", if (length(problems)) paste("NUMBERS DIFFER:", paste(head(problems, 5), collapse = " | ")) else "numbers identical",
      "; canvas ", size[["width"]], "x", size[["height"]], " in",
      "\n  as generated (panel_titles = FALSE): ", pix_old,
      "\n  library default (titles shown): ", pix, "\n", sep = "")
  cat(if (length(problems)) "SOME NUMBER CHECKS FAILED\n" else "ALL NUMBER CHECKS PASSED\n")
}
