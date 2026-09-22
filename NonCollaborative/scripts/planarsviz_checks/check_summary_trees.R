#!/usr/bin/env Rscript
# Porting check for charts 14 (frequency tree) and 13 (four trees),
# docs/PLAN_planarsviz_library.md section 7 steps 3-6.
#
# Default (nyan1308): evaluates results/laminar_freqtree.r and
# results/laminar_four_trees.r in memory (ggsave disabled; files untouched),
# builds the same charts with plot_frequency_tree() / plot_four_trees(),
# compares every panel's ggplot_build() data, title and opacity-scale name,
# renders at the scripts' canvas sizes and pixel-compares with the frozen
# references.
# library-only (shifted test data): render only, beside the nyan1308 renders,
# under results/planarsviz/comparisons/shifted_nyan/shifted/.
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_summary_trees.R
#   Rscript scripts/planarsviz_checks/check_summary_trees.R results/planarsviz/shifted_nyan shifted_nyan library-only

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
  if (!identical(bo$plot$labels$title, bl$plot$labels$title)) {
    out <- c(out, sprintf("%s: title '%s' vs '%s'", what, bo$plot$labels$title, bl$plot$labels$title))
  }
  alpha_name <- function(b) b$plot$scales$get_scales("alpha")$name
  if (!identical(alpha_name(bo), alpha_name(bl))) out <- c(out, sprintf("%s: alpha scale name", what))
  out
}
compare <- function(ref, new_png, out_png) {
  system2(python, c("scripts/planarsviz_compare.py", shQuote(ref), shQuote(new_png), shQuote(out_png)), stdout = TRUE)
}
render <- function(p, base, width, height) {
  pdf_path <- file.path(bundle_dir, "plots", paste0(base, ".pdf"))
  dir.create(dirname(pdf_path), recursive = TRUE, showWarnings = FALSE)
  suppressMessages(suppressWarnings(ggplot2::ggsave(pdf_path, p, width = width, height = height, units = "in")))
  stem <- file.path(tempdir(), base)
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(stem)))
  paste0(stem, ".png")
}
cmp_dir <- file.path(dirname(bundle_dir), "comparisons", prefix, if (library_only) "shifted" else "")
dir.create(cmp_dir, recursive = TRUE, showWarnings = FALSE)

cases <- list(
  list(name = "freqtree", script = "laminar_freqtree.r", make = function() plot_frequency_tree(bundle),
       objects = "p_freqtree"),
  list(name = "four_trees", script = "laminar_four_trees.r", make = function() plot_four_trees(bundle),
       objects = c("p_all", "p_A", "p_B", "p_C"))
)

all_ok <- TRUE
for (case in cases) {
  pl <- suppressMessages(suppressWarnings(case$make()))
  size <- attr(pl, "planarsviz_size")
  folder <- attr(pl, "planarsviz_folder")
  cmp_out <- file.path(cmp_dir, folder)
  dir.create(cmp_out, recursive = TRUE, showWarnings = FALSE)
  base <- paste0(prefix, "_", case$name)
  new_png <- render(pl, base, size[["width"]], size[["height"]])

  if (library_only) {
    nyan_pdf <- file.path("results", "nyan1308", folder, paste0("nyan1308_", case$name, ".pdf"))
    stem <- file.path(tempdir(), paste0("nyan_", case$name))
    system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(nyan_pdf), shQuote(stem)))
    cat(base, ": rendered; side by side with nyan1308: ",
        compare(paste0(stem, ".png"), new_png, file.path(cmp_out, paste0(base, ".png"))), "\n", sep = "")
    next
  }

  src <- readLines(superseded("results", case$script))
  src <- src[!startsWith(src, "ggsave(")]
  orig <- new.env()
  suppressMessages(suppressWarnings(eval(parse(text = src), envir = orig)))
  parts <- if (length(case$objects) == 1) list(pl) else attr(pl, "planarsviz_parts")
  problems <- character()
  for (i in seq_along(case$objects)) {
    problems <- c(problems, same_data(get(case$objects[[i]], envir = orig), parts[[i]], case$objects[[i]]))
  }
  if (length(problems)) all_ok <- FALSE
  pix <- compare(file.path(dirname(bundle_dir), "reference", prefix, folder, paste0(base, ".png")), new_png,
                 file.path(cmp_out, paste0(base, ".png")))
  cat(base, ": ", if (length(problems)) paste("NUMBERS DIFFER:", paste(head(problems, 5), collapse = " | ")) else "numbers identical",
      "; canvas ", size[["width"]], "x", size[["height"]], " in; pixels: ", pix, "\n", sep = "")
}
if (!library_only) cat(if (all_ok) "ALL NUMBER CHECKS PASSED\n" else "SOME NUMBER CHECKS FAILED\n")
