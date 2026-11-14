#!/usr/bin/env Rscript
# Slide figures: nyan1308's combined constituency forest (every family of
# every test, stacked: the package's all_families_labeled chart), plain, then
# annotated with a possible word domain from position 5 (Neg1) to 17 (FV),
# then with the orthographic word's extension from there to 19 (Enc) as a
# blue "shield" around it. A one-off for a talk, not one of the package's
# charts.
#
# Annotation, in each of the stacked family trees: an edge is coloured for a
# domain when both the node it leads to and that node's parent lie within
# the domain.
#   - 5-17 in dark red. Where a family has the 5-17 node, that is exactly
#     every line below it. 5-17 is in only 37 of the 69 families; in the
#     others no node joins 5 and 17 alone, and only their structure lying
#     wholly inside 5-17 is coloured.
#   - slide 3 adds 5-19 in blue, for edges not already red: the lines from
#     the 5-19 and 5-18 nodes down, i.e. what the orthographic word adds.
# Labels: slide 2, 5-16 dark red and FV (17) dark blue; slide 3, 5-17 dark
# red and 18-19 blue (FV red there, so blue means only the extension).
#
# The slides are for dissolves: all come from the same code on the package
# chart's own canvas (20 x 14 in), so they differ only in the annotation. The
# trees, their opacity and line thickness come from the package
# (plot_laminar_overlay with the renderer's all_families_labeled settings),
# so they always match the bundle.
#
# Run from the repository root (where .Rprofile sets up the pinned packages):
#   Rscript NonCollaborative/scripts/slides/nyan1308_all_families_word_5_17.R
# Writes NonCollaborative/results/nyan1308/slides/
#   nyan1308_all_families_word_5_17_slide_1_plain.pdf / .png
#   nyan1308_all_families_word_5_17_slide_2_annotated.pdf / .png
#   nyan1308_all_families_word_5_17_slide_3_shield.pdf / .png

bundle_dir <- "NonCollaborative/results/chart_data/nyan1308"
out_dir <- "NonCollaborative/results/nyan1308/slides"
out_stem <- "nyan1308_all_families_word_5_17_slide"
red <- "darkred"
blue <- "#1F4FA0"
dark_blue <- "darkblue"

# Each slide: its domains, innermost first (an edge takes the colour of the
# first domain it lies in), and its label colours by position.
slides <- list(
  list(name = "1_plain", domains = list(), labels = list()),
  list(name = "2_annotated",
       domains = list(list(range = c(5L, 17L), colour = red)),
       labels = list(list(positions = 5:16, colour = red), list(positions = 17L, colour = dark_blue))),
  list(name = "3_shield",
       domains = list(list(range = c(5L, 17L), colour = red), list(range = c(5L, 19L), colour = blue)),
       labels = list(list(positions = 5:17, colour = red), list(positions = 18:19, colour = blue)))
)
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
names_by_position <- planarsviz_position_labels(bundle$position_labels)
n_positions <- as.integer(bundle$metadata$n_positions)

# The renderer's settings for all_families_labeled (laminar/render_planarsviz.R,
# `all_group`).
overlay <- plot_laminar_overlay(bundle, groups = "all", alpha_divisor = 1, thickness_exponent = 0.75)
parts <- attr(overlay, "planarsviz_parts")
size <- attr(overlay, "planarsviz_size")

# A node's extent from its label: a tip is "7", an inner node "5-17".
extent_of <- function(label) {
  bounds <- lapply(strsplit(label, "-", fixed = TRUE), as.integer)
  cbind(left = vapply(bounds, `[`, integer(1), 1L),
        right = vapply(bounds, function(b) b[[length(b)]], integer(1)))
}
inside <- function(ext, range) ext[, "left"] >= range[[1]] & ext[, "right"] <= range[[2]]

recolour_edges <- function(p, domains) {
  d <- p$data
  ext <- extent_of(d$label)
  parent_ext <- ext[match(d$parent, d$node), , drop = FALSE]
  colour <- rep("black", nrow(d))
  for (dom in rev(domains)) {  # innermost last, so it wins
    hit <- inside(ext, dom$range) & inside(parent_ext, dom$range) & d$node != d$parent
    colour[hit] <- dom$colour
  }
  d$edge_colour <- colour
  p$data <- d
  # The tree layer is the one carrying the fixed colour; map it instead.
  for (i in seq_along(p$layers)) {
    if (!is.null(p$layers[[i]]$aes_params$colour) && !is.na(p$layers[[i]]$aes_params$colour)) {
      p$layers[[i]]$aes_params$colour <- NULL
      p$layers[[i]]$mapping$colour <- quote(edge_colour)
    }
  }
  p + scale_colour_identity()
}

label_colours <- function(labels) {
  colours <- stats::setNames(rep("black", n_positions), as.character(seq_len(n_positions)))
  for (l in labels) colours[as.character(l$positions)] <- l$colour
  colours
}

slide_forest <- function(slide) {
  plots <- if (length(slide$domains)) lapply(parts, recolour_edges, domains = slide$domains) else parts
  colours <- label_colours(slide$labels)
  n <- length(plots)
  # Same label geometry as the package's, drawn over its labels on the top tree.
  plots[[n]] <- plots[[n]] + ggtree::geom_tiplab(
    aes(label = paste(label, names_by_position[label], sep = "\n"), colour = colours[label]),
    geom = "label", size = 6, angle = 0, offset = -1, hjust = 0.5, vjust = 0.35,
    alpha = 1, lineheight = 1
  ) + scale_colour_identity()
  layout <- do.call(c, rep(list(patchwork::area(t = 1, l = 1, b = 5, r = 1)), n))
  (Reduce(`+`, plots) + patchwork::plot_layout(design = layout)) &
    theme(plot.background = element_rect(fill = "white", color = NA))
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
for (slide in slides) {
  out_name <- paste0(out_stem, "_", slide$name)
  pdf_path <- file.path(out_dir, paste0(out_name, ".pdf"))
  suppressMessages(ggsave(pdf_path, slide_forest(slide),
                          width = size[["width"]], height = size[["height"]], units = "in"))
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path),
                        shQuote(file.path(out_dir, out_name))))
  cat("Wrote", pdf_path, "and .png\n")
}
