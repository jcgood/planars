#!/usr/bin/env Rscript
# Porting check for chart 10 (exemplary trees and slides),
# docs/PLAN_planarsviz_library.md section 7 steps 3-6.
#
# Default (nyan1308): evaluates OlderFiles/planarsviz_superseded/results/nyan1308_exemplary_trees.r in memory,
# including the domain_charts-cgpt.r it source()s, with ggsave replaced by a
# do-nothing function so no committed PDF is rewritten. For every exemplar
# compares the print tree, evidence panel and slide tree's ggplot_build()
# data with the library's, then renders the print page, slide tree and slide
# evidence at the script's sizes and pixel-compares with the references.
# library-only (shifted test data): render only, beside the nyan1308 renders,
# under results/planarsviz/comparisons/shifted_nyan/shifted/.
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_exemplary.R
#   Rscript scripts/planarsviz_checks/check_exemplary.R results/planarsviz/shifted_nyan shifted_nyan library-only

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
  y_labels <- function(b) b$layout$panel_params[[1]]$y$get_labels()
  if (!identical(y_labels(bo), y_labels(bl))) out <- c(out, sprintf("%s: y labels", what))
  out
}
compare <- function(ref, new_png, out_png) {
  system2(python, c("scripts/planarsviz_compare.py", shQuote(ref), shQuote(new_png), shQuote(out_png)), stdout = TRUE)
}
render <- function(p, base) {
  size <- attr(p, "planarsviz_size")
  pdf_path <- file.path(bundle_dir, "plots", paste0(base, ".pdf"))
  dir.create(dirname(pdf_path), recursive = TRUE, showWarnings = FALSE)
  suppressMessages(suppressWarnings(ggplot2::ggsave(pdf_path, p, device = "pdf", width = size[["width"]],
    height = size[["height"]], units = attr(p, "planarsviz_units"), limitsize = FALSE)))
  stem <- file.path(tempdir(), base)
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(stem)))
  paste0(stem, ".png")
}
cmp_dir <- file.path(dirname(bundle_dir), "comparisons", prefix, if (library_only) "shifted" else "")
dir.create(cmp_dir, recursive = TRUE, showWarnings = FALSE)

selections <- read_planars_selections(bundle)
n_exemplars <- sum(selections$selection == "exemplary")

orig <- NULL
if (!library_only) {
  orig <- new.env()
  assign("ggsave", function(...) invisible(NULL), envir = orig)
  src <- readLines(superseded("results", "nyan1308_exemplary_trees.r"))
  pooled_line <- grep("^source\\(here::here", src)
  pooled_src <- readLines(superseded("scripts", "domain_charts-cgpt.r"))
  # Name the domains file outright instead of letting the archived script's
  # here() look it up. here() used to land on the planars repo root, which is
  # what that script's own comment says it relies on; since renv arrived it
  # lands on NonCollaborative/ instead, because rprojroot counts an renv
  # project as a project root, so the lookup built a doubled path and the
  # script died before drawing anything. check_pooled.R already substitutes
  # this same line of this same script for its own reasons -- this is that
  # substitution, not a new idea. The file read is identical either way.
  data_line <- grep("^domains <- read_tsv\\(here", pooled_src)
  pooled_src[data_line] <- sprintf(
    'domains <- read_tsv("%s", show_col_types = FALSE)',
    "domains/domains_nyan1308.tsv"
  )
  suppressMessages(suppressWarnings({
    eval(parse(text = src[seq_len(pooled_line - 1)]), envir = orig)
    eval(parse(text = pooled_src), envir = orig)
    eval(parse(text = src[(pooled_line + 1):length(src)]), envir = orig)
  }))
}

all_ok <- TRUE
for (i in seq_len(n_exemplars)) {
  views <- list(
    page = suppressMessages(suppressWarnings(plot_exemplary_tree(bundle, i, "page"))),
    slide_tree = suppressMessages(suppressWarnings(plot_exemplary_tree(bundle, i, "slide_tree"))),
    slide_evidence = suppressMessages(suppressWarnings(plot_exemplary_tree(bundle, i, "slide_evidence")))
  )
  bases <- c(page = sprintf("%s_exemplary_trees_%d", prefix, i),
             slide_tree = sprintf("%s_exemplary_trees_slide_%d_tree", prefix, i),
             slide_evidence = sprintf("%s_exemplary_trees_slide_%d_evidence", prefix, i))
  folder <- attr(views$page, "planarsviz_folder")
  cmp_out <- file.path(cmp_dir, folder)
  dir.create(cmp_out, recursive = TRUE, showWarnings = FALSE)
  pngs <- vapply(names(views), function(v) render(views[[v]], bases[[v]]), character(1))

  if (library_only) {
    for (v in names(views)) {
      nyan_base <- sub(prefix, "nyan1308", bases[[v]], fixed = TRUE)
      nyan_pdf <- file.path("results", "nyan1308", folder, paste0(nyan_base, ".pdf"))
      if (!file.exists(nyan_pdf)) { cat(bases[[v]], ": rendered (no nyan1308 counterpart)\n"); next }
      stem <- file.path(tempdir(), paste0("nyan_", nyan_base))
      system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(nyan_pdf), shQuote(stem)))
      cat(bases[[v]], ": rendered; side by side with nyan1308: ",
          compare(paste0(stem, ".png"), pngs[[v]], file.path(cmp_out, paste0(bases[[v]], ".png"))), "\n", sep = "")
    }
    next
  }

  parts <- attr(views$page, "planarsviz_parts")
  problems <- c(
    same_data(get(sprintf("ex_tp%d", i), envir = orig), parts$tree, sprintf("ex_tp%d", i)),
    same_data(get(sprintf("ex_plot%d", i), envir = orig), parts$evidence, sprintf("ex_plot%d", i)),
    same_data(get(sprintf("ex_slide_tp%d", i), envir = orig), views$slide_tree, sprintf("ex_slide_tp%d", i))
  )
  if (length(problems)) all_ok <- FALSE
  pix <- vapply(names(views), function(v) compare(
    file.path(dirname(bundle_dir), "reference", prefix, folder, paste0(bases[[v]], ".png")), pngs[[v]],
    file.path(cmp_out, paste0(bases[[v]], ".png"))), character(1))
  cat(sprintf("exemplar %d: %s\n", i,
              if (length(problems)) paste("NUMBERS DIFFER:", paste(head(problems, 5), collapse = " | ")) else "numbers identical"))
  for (v in names(views)) {
    size <- attr(views[[v]], "planarsviz_size")
    cat(sprintf("  %s (%s x %s %s): %s\n", v, size[["width"]], size[["height"]], attr(views[[v]], "planarsviz_units"), pix[[v]]))
  }
}
if (!library_only) cat(if (all_ok) "ALL NUMBER CHECKS PASSED\n" else "SOME NUMBER CHECKS FAILED\n")
