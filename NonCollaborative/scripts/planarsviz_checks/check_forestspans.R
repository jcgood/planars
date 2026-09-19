#!/usr/bin/env Rscript
# Porting check for chart 11 (ForestSpans plot and its no-tonosegmental
# version), docs/PLAN_planarsviz_library.md section 7 steps 3-6.
#
# Default (nyan1308): evaluates results/nyan1308_forestspans_plot.r and
# results/nyan1308_forestspans_plot_no_tono.r in memory (ggsave disabled;
# files untouched), builds the same charts with plot_forestspans(bundle) and
# plot_forestspans(bundle, subset = "no_tono"), compares ggplot_build() data
# and the y-axis order, renders at 34x24 cm and pixel-compares with the
# frozen references.
# library-only (shifted test data): render only, beside the nyan1308 renders.
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_forestspans.R
#   Rscript scripts/planarsviz_checks/check_forestspans.R results/planarsviz/shifted_nyan shifted_nyan library-only

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
  y_labels <- function(b) b$layout$panel_params[[1]]$y$get_labels()
  if (!identical(y_labels(bo), y_labels(bl))) out <- c(out, sprintf("%s: y order", what))
  fill_name <- function(b) b$plot$scales$get_scales("fill")$name
  if (!identical(fill_name(bo), fill_name(bl))) out <- c(out, sprintf("%s: legend title", what))
  out
}
compare <- function(ref, new_png, out_png) {
  system2(python, c("scripts/planarsviz_compare.py", shQuote(ref), shQuote(new_png), shQuote(out_png)), stdout = TRUE)
}
render <- function(p, base, dir = file.path(bundle_dir, "plots")) {
  size <- attr(p, "planarsviz_size")
  pdf_path <- file.path(dir, paste0(base, ".pdf"))
  dir.create(dirname(pdf_path), recursive = TRUE, showWarnings = FALSE)
  suppressMessages(suppressWarnings(ggplot2::ggsave(pdf_path, p, width = size[["width"]], height = size[["height"]],
                                                    units = attr(p, "planarsviz_units"))))
  stem <- file.path(tempdir(), base)
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(stem)))
  paste0(stem, ".png")
}
cmp_dir <- file.path(dirname(bundle_dir), "comparisons", if (library_only) "shifted" else "")
dir.create(cmp_dir, recursive = TRUE, showWarnings = FALSE)

subset_ids <- vapply(jsonlite::read_json(file.path(bundle_dir, "data", "subsets.json")),
                     function(s) s$subset_id, character(1))
cases <- list(
  list(name = "forestspans_plot", script = "nyan1308_forestspans_plot.r", subset = NULL),
  list(name = "forestspans_plot_no_tono", script = "nyan1308_forestspans_plot_no_tono.r", subset = "no_tono")
)

all_ok <- TRUE
for (case in cases) {
  base <- paste0(prefix, "_", case$name)
  if (!is.null(case$subset) && !case$subset %in% subset_ids) {
    cat(base, ": skipped (bundle has no `", case$subset, "` subset)\n", sep = "")
    next
  }
  pl <- suppressMessages(suppressWarnings(plot_forestspans(bundle, subset = case$subset)))
  new_png <- render(pl, base)
  # The legend moved into the panel's lower-left corner on 2026-09-16; the
  # exact comparison with the old script uses the original right-hand legend.
  # 2026-09-16 also: "Trees" set larger than "(n = N)" in the count header;
  # count_header_size = NULL restores the original label.
  pl_old <- suppressMessages(suppressWarnings(
    plot_forestspans(bundle, subset = case$subset, legend_position = "right", count_header_size = NULL)))
  old_png <- render(pl_old, paste0(base, "_legend_right"), file.path(tempdir(), "as_generated"))

  if (library_only) {
    nyan_pdf <- file.path(dirname(bundle_dir), "nyan1308", "plots", paste0("nyan1308_", case$name, ".pdf"))
    stem <- file.path(tempdir(), paste0("nyan_", case$name))
    system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(nyan_pdf), shQuote(stem)))
    cat(base, ": rendered; side by side with nyan1308: ",
        compare(paste0(stem, ".png"), new_png, file.path(cmp_dir, paste0(base, ".png"))), "\n", sep = "")
    next
  }

  src <- readLines(file.path("results", case$script))
  src <- src[!startsWith(src, "ggsave(")]
  orig <- new.env()
  suppressMessages(suppressWarnings(eval(parse(text = src), envir = orig)))
  problems <- same_data(get("p", envir = orig), pl_old, case$name)
  if (length(problems)) all_ok <- FALSE
  size <- attr(pl, "planarsviz_size")
  ref <- file.path(dirname(bundle_dir), "reference", paste0(base, ".png"))
  pix_old <- compare(ref, old_png, file.path(tempdir(), paste0(base, "_as_generated_cmp.png")))
  pix <- compare(ref, new_png, file.path(cmp_dir, paste0(base, ".png")))
  cat(base, ": ", if (length(problems)) paste("NUMBERS DIFFER:", paste(head(problems, 5), collapse = " | ")) else "numbers identical",
      "; canvas ", size[["width"]], "x", size[["height"]], " ", attr(pl, "planarsviz_units"),
      "\n  as generated (legend right, original header): ", pix_old,
      "\n  library default (inset legend, larger header): ", pix, "\n", sep = "")
}
if (!library_only) cat(if (all_ok) "ALL NUMBER CHECKS PASSED\n" else "SOME NUMBER CHECKS FAILED\n")
