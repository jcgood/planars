#!/usr/bin/env Rscript
# Porting check for charts 1-4 (pooled plots), docs/PLAN_planarsviz_library.md
# section 7 steps 3-4.
#
# Builds every pooled plot two ways -- from the working script
# (scripts/domain_charts-cgpt.r, evaluated in memory with its file writes
# disabled; the script file itself is not modified) and from the planarsviz
# library -- then:
#   1. compares ggplot_build() layer data, axis labels, title and canvas size;
#   2. renders the library plot at the working script's canvas size to
#      results/planarsviz/<dataset>/plots/, and pixel-compares it with the
#      frozen reference PNG (when checking nyan1308).
#
# Run from NonCollaborative/:
#   Rscript scripts/planarsviz_checks/check_pooled.R [BUNDLE_DIR] [DOMAIN_TSV] [OUT_NAME_PREFIX]
# Defaults: results/planarsviz/nyan1308, domains/domains_nyan1308.tsv, nyan1308

args <- commandArgs(trailingOnly = TRUE)
bundle_dir <- if (length(args) >= 1) args[[1]] else "results/planarsviz/nyan1308"
domain_tsv <- if (length(args) >= 2) args[[2]] else "domains/domains_nyan1308.tsv"
prefix <- if (length(args) >= 3) args[[3]] else "nyan1308"
python <- "/Users/jcgood/gitrepos/planars/.venv/bin/python"

# ---- install the library into a private temp library ----
lib <- file.path(tempdir(), "planarsviz_lib")
dir.create(lib, showWarnings = FALSE)
status <- system2("R", c("CMD", "INSTALL", "--no-test-load", paste0("--library=", lib),
                         "r/planarsviz"), stdout = FALSE, stderr = FALSE)
if (status != 0) stop("R CMD INSTALL failed")
suppressPackageStartupMessages(library(planarsviz, lib.loc = lib))
bundle <- read_planars_bundle(bundle_dir)

# ---- build the working script's plots in memory ----
src <- readLines("scripts/domain_charts-cgpt.r")
data_line <- grep("^domains <- read_tsv\\(here", src)
src[data_line] <- sprintf('domains <- read_tsv("%s", show_col_types = FALSE)', domain_tsv)
root_line <- grep("^o <- 10", src)
src[root_line] <- sprintf("o <- %s", if (is.null(bundle$metadata$root_position)) "NULL" else bundle$metadata$root_position)
n_line <- grep("^b <- 22", src)
src[n_line] <- sprintf("b <- %s", bundle$metadata$n_positions)
load_line <- grep("^pacman::p_load", src)
src <- append(src, "ggsave <- function(...) invisible(NULL); print <- function(...) invisible(NULL)",
              after = load_line)
orig <- new.env()
suppressMessages(suppressWarnings(eval(parse(text = src), envir = orig)))

types <- c("length", "morphosyntactic", "phonological", "tonosegmental", "intonational")
types <- intersect(types, unique(trimws(bundle$tests$Domain_Type)))
cases <- list(
  list(name = "pooled_plot", orig = "pooled_plot", data = "tests_plot", width = 26,
       lib = function() plot_pooled(bundle)),
  list(name = "pooled_domainplot", orig = "pooled_domainplot", data = "tests_domainsplot", width = 26,
       lib = function() plot_pooled(bundle, group_by_domain = TRUE))
)
for (t in types) {
  local({
    tt <- t
    cases[[length(cases) + 1]] <<- list(
      name = paste0("pooled_plot_", tt), orig = paste0("pooled_plot_", tt),
      data = paste0("tests_plot_", tt), width = 25,
      lib = function() plot_pooled(bundle, domain_types = tt, layers = "local"))
    cases[[length(cases) + 1]] <<- list(
      name = paste0("pooled_plot_", tt, "_global_layers"), orig = paste0("pooled_plot_", tt, "_global"),
      data = paste0("tests_plot_", tt, "_global"), width = 25,
      lib = function() plot_pooled(bundle, domain_types = tt, layers = "global"))
  })
}

plain <- function(df) {
  df <- as.data.frame(df)
  df[] <- lapply(df, function(v) if (is.factor(v)) as.character(v) else as.vector(v))
  rownames(df) <- NULL
  df
}

out_dir <- file.path(bundle_dir, "plots")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
cmp_dir <- file.path(dirname(bundle_dir), "comparisons")
dir.create(cmp_dir, recursive = TRUE, showWarnings = FALSE)

all_ok <- TRUE
for (case in cases) {
  po <- get(case$orig, envir = orig)
  pl <- case$lib()
  bo <- ggplot2::ggplot_build(po)
  bl <- ggplot2::ggplot_build(pl)
  problems <- character()
  if (length(bo$data) != length(bl$data)) {
    problems <- c(problems, sprintf("layer count %d vs %d", length(bo$data), length(bl$data)))
  } else {
    for (k in seq_along(bo$data)) {
      a <- plain(bo$data[[k]]); b2 <- plain(bl$data[[k]])
      cols <- intersect(names(a), names(b2))
      res <- all.equal(a[cols], b2[cols], check.attributes = FALSE)
      if (!isTRUE(res)) problems <- c(problems, sprintf("layer %d: %s", k, paste(res, collapse = "; ")))
    }
  }
  ya <- bo$layout$panel_params[[1]]$y$get_labels()
  yb <- bl$layout$panel_params[[1]]$y$get_labels()
  if (!identical(as.character(ya), as.character(yb))) problems <- c(problems, "y-axis labels differ")
  if (!identical(po$labels$title, pl$labels$title)) problems <- c(problems, "title differs")
  h_orig <- get("plot_height", envir = orig)(get(case$data, envir = orig))
  size <- attr(pl, "planarsviz_size")
  if (!isTRUE(all.equal(unname(size), c(case$width, h_orig)))) {
    problems <- c(problems, sprintf("size %s vs %s", paste(size, collapse = "x"), paste(c(case$width, h_orig), collapse = "x")))
  }

  base <- paste0(prefix, "_", case$name)
  pdf_path <- file.path(out_dir, paste0(base, ".pdf"))
  ggplot2::ggsave(pdf_path, pl, device = "pdf", width = size[["width"]], height = size[["height"]], units = "cm")
  png_stem <- file.path(tempdir(), base)
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(png_stem)))
  ref <- file.path(dirname(bundle_dir), "reference", paste0(base, ".png"))
  pixel <- "no reference for this dataset"
  if (file.exists(ref)) {
    pixel <- system2(python, c("scripts/planarsviz_compare.py", shQuote(ref), shQuote(paste0(png_stem, ".png")),
                               shQuote(file.path(cmp_dir, paste0(base, ".png")))), stdout = TRUE)
  }
  status_txt <- if (length(problems)) paste("NUMBERS DIFFER:", paste(problems, collapse = " | ")) else "numbers identical"
  if (length(problems)) all_ok <- FALSE
  cat(sprintf("%s: %s; pixels: %s\n", base, status_txt, pixel))
}
cat(if (all_ok) "ALL NUMBER CHECKS PASSED\n" else "SOME NUMBER CHECKS FAILED\n")
