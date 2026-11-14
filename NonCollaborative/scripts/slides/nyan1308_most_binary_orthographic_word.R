#!/usr/bin/env Rscript
# Slide figures: nyan1308's most binary tree, plain and then with the
# orthographic word (5-19) picked out -- the edges out to positions 5 and 19
# drawn thick, and the labels of positions 5 to 19 in dark red. A one-off for
# a talk, not one of the package's charts.
#
# The two are a pair for a dissolve between slides: both are drawn by the
# same code on the same canvas, differing only in the emphasis, so every line
# and label sits on the same pixel in each. (The package's own
# nyan1308_most_binary_tree is a different canvas, with a title, and will not
# line up with the highlighted one.)
#
# Both draw on the package's own chart (plot_frequency_tree; with
# emphasis = "orthographic_word" for the second) and only add the coloured
# labels on top, so the tree always matches the bundle. The word's extent
# comes from the bundle's highlights.tsv, not from this file.
#
# Run from the repository root (where .Rprofile sets up the pinned packages):
#   Rscript NonCollaborative/scripts/slides/nyan1308_most_binary_orthographic_word.R
# Writes NonCollaborative/results/nyan1308/slides/
#   nyan1308_most_binary_orthographic_word_slide_1_plain.pdf / .png
#   nyan1308_most_binary_orthographic_word_slide_2_highlighted.pdf / .png
# (16:9, 16 x 9 in, no title; png 1920 x 1080).

bundle_dir <- "NonCollaborative/results/chart_data/nyan1308"
out_dir <- "NonCollaborative/results/nyan1308/slides"
out_stem <- "nyan1308_most_binary_orthographic_word_slide"
highlight <- "orthographic_word"
label_colour <- "darkred"
if (!dir.exists(bundle_dir)) stop("Run this from the repository root.", call. = FALSE)

lib <- file.path(tempdir(), "planarsviz_lib")
dir.create(lib, showWarnings = FALSE)
status <- system2("R", c("CMD", "INSTALL", "--no-test-load", paste0("--library=", lib), "planarsviz"),
                  stdout = FALSE, stderr = FALSE)
if (status != 0) stop("R CMD INSTALL of planarsviz failed.", call. = FALSE)
suppressPackageStartupMessages({
  library(planarsviz, lib.loc = lib)
  library(ggplot2)
})

bundle <- read_planars_bundle(bundle_dir)
word <- planarsviz_highlight_range(bundle, highlight)
names_by_position <- planarsviz_position_labels(bundle$position_labels)

# One function for both, so the layers are identical apart from emphasis and
# the overlay labels' colour (black in the plain one, so even the layer stack
# matches).
slide_tree <- function(emphasised) {
  plot_frequency_tree(bundle, selection = "most_binary", weight = "none",
                      emphasis = if (emphasised) highlight else NULL, title = NULL) +
    ggtitle(NULL) +
    # Same label geometry as the package's tip labels, drawn over them for
    # the positions inside the word.
    ggtree::geom_tiplab(
      # Internal node labels ("5-6") aren't numbers; isTip filters them out.
      aes(subset = isTip & suppressWarnings(as.integer(label)) %in% seq(min(word), max(word)),
          label = paste(label, names_by_position[label], sep = "\n")),
      geom = "label", size = 5, angle = 0, offset = -1, hjust = 0.5, alpha = 1,
      lineheight = 1, colour = if (emphasised) label_colour else "black"
    )
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
for (version in list(list(name = "1_plain", emphasised = FALSE),
                     list(name = "2_highlighted", emphasised = TRUE))) {
  out_name <- paste0(out_stem, "_", version$name)
  pdf_path <- file.path(out_dir, paste0(out_name, ".pdf"))
  # 16:9 at the package chart's own 16in width: at the usual 13.333in slide
  # width the tip labels collide (PostSbj, Obj2 clipped). It scales on a slide.
  ggsave(pdf_path, slide_tree(version$emphasised), width = 16, height = 9, units = "in")
  system2("pdftoppm", c("-png", "-r", "120", "-singlefile", shQuote(pdf_path),
                        shQuote(file.path(out_dir, out_name))))
  cat("Wrote", pdf_path, "and .png\n")
}
