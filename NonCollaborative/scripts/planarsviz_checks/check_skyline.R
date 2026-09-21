#!/usr/bin/env Rscript
# Porting check for chart 5 (boundary skyline), docs/PLAN_planarsviz_library.md
# section 7 steps 3-6.
#
# Default (nyan1308): builds the skyline from the working script
# (scripts/nyan_boundary_skyline.r, evaluated in memory with its input path
# pointed at DOMAIN_TSV and its file writes sent to a temp dir; the script
# file itself is not modified) and from the library, then compares both
# panels' ggplot_build() data, the title/subtitle, and the boundary-count
# table; renders the library chart at the working script's canvas and
# pixel-compares it with the frozen reference.
#
# library-only (shifted test data): render only, side by side with the
# nyan1308 library render.
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_skyline.R
#   Rscript scripts/planarsviz_checks/check_skyline.R results/planarsviz/shifted_nyan tests/fixtures/domains_shifted_nyan.tsv shifted_nyan library-only

args <- commandArgs(trailingOnly = TRUE)
bundle_dir <- if (length(args) >= 1) args[[1]] else "results/planarsviz/nyan1308"
domain_tsv <- if (length(args) >= 2) args[[2]] else "domains/domains_nyan1308.tsv"
prefix <- if (length(args) >= 3) args[[3]] else "nyan1308"
library_only <- length(args) >= 4 && args[[4]] == "library-only"
python <- "/Users/jcgood/gitrepos/planars/.venv/bin/python"
source("scripts/planarsviz_checks/superseded.R")

lib <- file.path(tempdir(), "planarsviz_lib")
dir.create(lib, showWarnings = FALSE)
status <- system2("R", c("CMD", "INSTALL", "--no-test-load", paste0("--library=", lib),
                         "r/planarsviz"), stdout = FALSE, stderr = FALSE)
if (status != 0) stop("R CMD INSTALL failed")
suppressPackageStartupMessages(library(planarsviz, lib.loc = lib))
bundle <- read_planars_bundle(bundle_dir)

pl <- plot_boundary_skyline(bundle)
problems <- character()

plain <- function(df) {
  df <- as.data.frame(df)
  df[] <- lapply(df, function(v) if (is.factor(v)) as.character(v) else as.vector(v))
  rownames(df) <- NULL
  df
}

if (!library_only) {
  tmp_out <- file.path(tempdir(), "skyline_orig_out")
  dir.create(tmp_out, showWarnings = FALSE)
  src <- readLines(superseded("scripts", "nyan_boundary_skyline.r"))
  src[grep("^input_file <- ", src)] <- sprintf('input_file <- "%s"', normalizePath(domain_tsv))
  src[grep("^output_dir <- ", src)] <- sprintf('output_dir <- "%s"', tmp_out)
  src <- append(src, "ggsave <- function(...) invisible(NULL)", after = grep("^library\\(patchwork\\)", src))
  orig <- new.env()
  suppressMessages(suppressWarnings(eval(parse(text = src), envir = orig)))

  parts <- attr(pl, "planarsviz_parts")
  for (nm in c("p_all", "p_by_type")) {
    bo <- ggplot2::ggplot_build(get(nm, envir = orig))
    bl <- ggplot2::ggplot_build(parts[[nm]])
    for (k in seq_along(bo$data)) {
      a <- plain(bo$data[[k]]); b2 <- plain(bl$data[[k]])
      res <- all.equal(a[intersect(names(a), names(b2))], b2[intersect(names(a), names(b2))],
                       check.attributes = FALSE)
      if (!isTRUE(res)) problems <- c(problems, sprintf("%s layer %d: %s", nm, k, paste(res, collapse = "; ")))
    }
    if (!identical(bo$layout$layout$Domain_Type, bl$layout$layout$Domain_Type)) {
      problems <- c(problems, sprintf("%s facet panels differ", nm))
    }
    xo <- bo$layout$panel_params[[1]]$x$get_labels(); xl <- bl$layout$panel_params[[1]]$x$get_labels()
    if (!identical(as.character(xo), as.character(xl))) problems <- c(problems, sprintf("%s x labels differ", nm))
  }
  po <- get("p", envir = orig)
  if (!identical(po$patches$annotation$title, pl$patches$annotation$title)) problems <- c(problems, "title differs")
  if (!identical(po$patches$annotation$subtitle, pl$patches$annotation$subtitle)) problems <- c(problems, "subtitle differs")
  counts_orig <- read.delim(file.path(tmp_out, "nyan1308_boundary_counts.tsv"), stringsAsFactors = FALSE)
  counts_lib <- plain(attr(pl, "planarsviz_boundary_counts"))
  counts_lib$Position <- as.integer(counts_lib$Position)
  if (!isTRUE(all.equal(counts_orig, counts_lib, check.attributes = FALSE))) problems <- c(problems, "boundary counts differ")
}

size <- attr(pl, "planarsviz_size")
base <- paste0(prefix, "_boundary_skyline")
out_dir <- file.path(bundle_dir, "plots")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
pdf_path <- file.path(out_dir, paste0(base, ".pdf"))
ggplot2::ggsave(pdf_path, pl, device = "pdf", width = size[["width"]], height = size[["height"]],
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
  nyan_pdf <- file.path("results", "nyan1308_boundary_skyline.pdf")
  nyan_stem <- file.path(tempdir(), "nyan_skyline")
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(nyan_pdf), shQuote(nyan_stem)))
  cat(base, ": rendered; side by side with nyan1308: ",
      compare(paste0(nyan_stem, ".png"), paste0(png_stem, ".png"), file.path(cmp_out, paste0(base, ".png"))), "\n")
} else {
  ref <- file.path(dirname(bundle_dir), "reference", folder, paste0(base, ".png"))
  pixel <- compare(ref, paste0(png_stem, ".png"), file.path(cmp_out, paste0(base, ".png")))
  cat(base, ": ", if (length(problems)) paste("NUMBERS DIFFER:", paste(problems, collapse = " | ")) else "numbers identical",
      "; pixels: ", pixel, "\n", sep = "")
}
