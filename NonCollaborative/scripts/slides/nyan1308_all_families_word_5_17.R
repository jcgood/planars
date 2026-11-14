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
#   - 5-17 in blue. Where a family has the 5-17 node, that is exactly
#     every line below it. 5-17 is in only 37 of the 69 families; in the
#     others no node joins 5 and 17 alone, and only their structure lying
#     wholly inside 5-17 is coloured.
#   - slide 3 adds 5-19 in dark red, a "shield" around the blue, for edges
#     not already blue: the lines from the 5-19 and 5-18 nodes down, i.e.
#     what the orthographic word adds.
# Labels: 5-17 blue on slides 2 and 3; 18-19 dark red on slide 3.
# Legend, top left: "Linguist's word" (blue) on slide 2, plus "Orthographic
# word" (dark red) below it on slide 3, in a box sized for both on each.
# The colour is settled per line before drawing (the innermost domain is
# assigned last and replaces the outer one), so the colours never blend.
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
# Chosen to stay apart under simulated protan-, deutan- and tritanopia
# (Machado et al. 2009) and to read on white: the blue is Okabe-Ito's; the
# dark red is a little lighter than R's "darkred" so protanopes can still
# tell it from the black lines.
inner <- "#0072B2"
shield <- "#A50F15"

# ’ is the typographic apostrophe (escaped so the file stays plain ASCII).
linguists_word <- list(range = c(5L, 17L), colour = inner, legend = "Linguist’s word")
orthographic_word <- list(range = c(5L, 19L), colour = shield, legend = "Orthographic word")

# Each slide: its domains, innermost first (an edge takes the colour of the
# first domain it lies in; the legend lists them in this order), and its
# label colours by position.
slides <- list(
  list(name = "1_plain", domains = list(), labels = list()),
  list(name = "2_annotated",
       domains = list(linguists_word),
       labels = list(list(positions = 5:17, colour = inner))),
  list(name = "3_shield",
       domains = list(linguists_word, orthographic_word),
       labels = list(list(positions = 5:17, colour = inner), list(positions = 18:19, colour = shield)))
)
# Legend rows the box is sized for, on every slide, so a row added on a later
# slide doesn't move the ones before it in a dissolve.
legend_rows <- max(vapply(slides, function(s) length(s$domains), integer(1)))
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
  forest <- (Reduce(`+`, plots) + patchwork::plot_layout(design = layout)) &
    theme(plot.background = element_rect(fill = "white", color = NA))
  if (!length(slide$domains)) return(forest)
  # Top left, in the empty corner beside the tree, where the package puts
  # its own legends.
  forest + patchwork::inset_element(legend_box(slide$domains),
                                    left = 0.01, bottom = 0.97 - 0.07 * legend_rows,
                                    right = 0.25, top = 0.97, align_to = "full", on_top = TRUE)
}

legend_box <- function(domains) {
  rows <- data.frame(
    y = -seq_along(domains),
    colour = vapply(domains, `[[`, character(1), "colour"),
    text = vapply(domains, `[[`, character(1), "legend")
  )
  ggplot(rows) +
    geom_segment(aes(x = 0, xend = 0.6, y = y, yend = y, colour = colour),
                 linewidth = 3, lineend = "round") +
    geom_text(aes(x = 0.8, y = y, label = text, colour = colour), hjust = 0, size = 9) +
    scale_colour_identity() +
    coord_cartesian(xlim = c(-0.2, 3.6), ylim = c(-legend_rows - 0.5, -0.5), expand = FALSE) +
    theme_void() +
    # Boxed like the package's own legends (plot_laminar_overlay).
    theme(plot.background = element_rect(fill = "white", colour = "black", linewidth = 1.2),
          plot.margin = margin(10, 12, 10, 12))
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
for (slide in slides) {
  out_name <- paste0(out_stem, "_", slide$name)
  pdf_path <- file.path(out_dir, paste0(out_name, ".pdf"))
  # Quartz, not the default pdf device, which can't draw the typographic
  # apostrophe and swaps in a straight one. (Cairo needs XQuartz on a Mac;
  # laminar/render_planarsviz.R makes the same choice for IPA labels.)
  suppressMessages(ggsave(pdf_path, slide_forest(slide),
                          width = size[["width"]], height = size[["height"]], units = "in",
                          device = function(filename, ...) grDevices::quartz(file = filename, type = "pdf", ...)))
  system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path),
                        shQuote(file.path(out_dir, out_name))))
  cat("Wrote", pdf_path, "and .png\n")
}
