# Boundary-strength charts (chart 17 in docs/PLAN_planarsviz_library.md).
#
# A cross-language port (plan section 4.3), not a copy: the working charts
# are matplotlib, drawn by scripts/analysis/boundary_strength.py at commit
# 43a308f. The numbers come from the bundle (boundary_strength.tsv, written
# by calling that script's compute_boundary_strength(); the density curves in
# boundary_strength_density.tsv). Every matplotlib setting that affects
# appearance is mapped below, with its source line. Fonts differ (DejaVu Sans
# vs R's sans), so the result can't be pixel-identical.
#
# The matplotlib itself is gone: cutover step C3 removed the plotting from
# boundary_strength.py, leaving compute_boundary_strength(). Every line number
# and function name below refers to that script as it stood at 43a308f, which
# is where to read it.
#
# Bars (save_figure(), lines 126-156) -> plot_boundary_strength():
#   figsize 11 x 7 in, two panels sharing x, left edge above right (134);
#   bars width 0.7, #7876B1, "strength (summed)" (141-142); capped values as
#   "_" markers, s = 260 (about 16 pt wide), line 2 pt, black, drawn over the
#   bars, "capped (reference only, max 69)" (143-144) -- the 69 is typed in
#   there, so the no-tonosegmental chart also says 69 although its dotted line
#   is at 24; here it is the analysis's own family count; y labels "Left edge"
#   / "Right edge" 13 pt (145); tick labels 11 pt (146); no top or right
#   spine (147-148); dotted line at the family count, 0.7 pt, alpha 0.5
#   (149); legend upper left of the top panel, 10 pt, capped listed first
#   (151); x label "Position on the planar structure" 13 pt (152); a tick at
#   every position (153); tight_layout (154); white background.
# Distributions (save_distribution_figure(), lines 159-200) ->
# plot_boundary_strength_distributions():
#   figsize 11 x 5 in (178); left and right curves filled at alpha 0.5 in
#   #7876B1 and #BC3C29 with 1.5 pt outlines (179-182); a row of dots per
#   side at y = -0.005 and -0.012, area = strength / 2 pt^2, alpha 0.6, not
#   clipped (186-189); x from first position - 1 to last + 1 (191); a tick
#   at every position (192); axis labels 13 pt (193-194); no top or right
#   spine (195-196); legend upper right, 10 pt (197); tick labels at
#   matplotlib's default 10 pt; tight_layout (198); white background.
# matplotlib defaults reproduced (see R/tree_counts.R): 5% axis margins
# around the data (bars keep y = 0 as the bottom), and 1/2/2.5/5/10 tick
# steps with at most 9 intervals. Point sizes: 16 pt marker width and the dot
# areas are converted with the panel sizes these canvases give, so they are
# close, not exact.

planarsviz_analysis_dir <- function(bundle, subset = NULL) {
  if (is.null(subset)) return(file.path(bundle$bundle_dir, "data"))
  index <- jsonlite::read_json(file.path(bundle$bundle_dir, "data", "subsets.json"), simplifyVector = TRUE)
  hit <- index$path[index$subset_id == subset]
  if (!length(hit)) {
    stop("No subset `", subset, "` in this bundle. Available: ", paste(index$subset_id, collapse = ", "), call. = FALSE)
  }
  file.path(bundle$bundle_dir, "data", hit[[1]])
}

#' Read boundary strength from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param subset `NULL` for the full analysis, or a `subset_id` from `subsets.json`.
#' @return A list: `strength` (position, left_summed, left_capped,
#'   right_summed, right_capped), `density` (x, left, right), `n_families`.
#' @export
read_planars_boundary_strength <- function(bundle, subset = NULL) {
  dir <- planarsviz_analysis_dir(bundle, subset)
  path <- file.path(dir, "boundary_strength.tsv")
  if (!file.exists(path)) stop("No boundary_strength.tsv for this analysis; re-export the bundle.", call. = FALSE)
  list(
    strength = utils::read.delim(path),
    density = utils::read.delim(file.path(dir, "boundary_strength_density.tsv")),
    n_families = nrow(utils::read.delim(file.path(dir, "families.tsv")))
  )
}

planarsviz_mpl_theme <- function() {
  theme_classic() +
    theme(
      axis.line = element_line(linewidth = 0.8 / .pt, colour = "black"),
      axis.ticks = element_line(linewidth = 0.8 / .pt, colour = "black"),
      axis.ticks.length = unit(3.5, "pt"),
      axis.text = element_text(colour = "black"),
      legend.text = element_text(size = 10),
      legend.background = element_rect(fill = "white", colour = "grey80", linewidth = 0.8 / .pt),
      legend.key = element_blank(),
      plot.background = element_rect(fill = "white", colour = NA)
    )
}

#' Boundary-strength bar chart
#'
#' For each position, how strongly it is a left (top panel) or right (bottom
#' panel) constituent edge: bars sum each span's family count over the spans
#' starting or ending there; black marks count the families with at least
#' one such span, which can't exceed the dotted line at the family count.
#' Reproduces `nyan1308_boundary_strength.pdf`; with `subset = "no_tono"`,
#' `nyan1308_boundary_strength_no_tono.pdf`.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param subset `NULL` for the full analysis, or a `subset_id` from `subsets.json`.
#' @param bar_colour Bar colour.
#' @return A patchwork plot with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`), and `planarsviz_folder` (its
#'   `results/planarsviz` subfolder).
#' @export
plot_boundary_strength <- function(bundle, subset = NULL, bar_colour = "#7876B1") {
  validate_planars_bundle(bundle)
  bs <- read_planars_boundary_strength(bundle, subset)
  strength <- bs$strength
  n_families <- bs$n_families
  positions <- strength$position
  capped_label <- paste0("capped (reference only, max ", n_families, ")")

  # x: bars' outer edges plus matplotlib's 5% margin.
  x_edges <- range(positions) + c(-0.35, 0.35)
  xlim <- x_edges + c(-1, 1) * 0.05 * diff(x_edges)
  # "_" marker, s = 260: about 16.1 pt wide; the panel is about 10.1 in wide.
  half_tick <- sqrt(260) / 2 / (10.1 * 72 / diff(xlim))

  panel <- function(side, ylabel, top_panel) {
    d <- data.frame(position = positions,
                    summed = strength[[paste0(side, "_summed")]],
                    capped = strength[[paste0(side, "_capped")]])
    ytop <- max(d$summed, d$capped, n_families) * 1.05
    p <- ggplot(d, aes(x = position)) +
      geom_col(aes(y = summed, fill = "strength (summed)"), width = 0.7) +
      geom_hline(yintercept = n_families, linetype = "dotted", linewidth = 0.7 / .pt, alpha = 0.5) +
      geom_segment(aes(x = position - half_tick, xend = position + half_tick,
                       y = capped, yend = capped, colour = capped_label), linewidth = 2 / .pt) +
      scale_fill_manual(values = stats::setNames(bar_colour, "strength (summed)"), name = NULL) +
      scale_colour_manual(values = stats::setNames("black", capped_label), name = NULL) +
      guides(colour = guide_legend(order = 1), fill = guide_legend(order = 2)) +
      scale_x_continuous(breaks = positions, limits = xlim, expand = c(0, 0)) +
      scale_y_continuous(limits = c(0, ytop), expand = c(0, 0), breaks = planarsviz_mpl_breaks(ytop)) +
      labs(x = if (top_panel) NULL else "Position on the planar structure", y = ylabel) +
      planarsviz_mpl_theme() +
      theme(axis.title = element_text(size = 13), axis.text = element_text(size = 11, colour = "black"))
    if (top_panel) {
      p + theme(axis.text.x = element_blank(),
                legend.position = "inside", legend.position.inside = c(0.005, 0.995),
                legend.justification = c(0, 1), legend.box = "vertical",
                legend.spacing.y = unit(0, "pt"), legend.margin = margin(3, 6, 3, 4))
    } else {
      p + theme(legend.position = "none")
    }
  }

  p <- (panel("left", "Left edge", TRUE) / panel("right", "Right edge", FALSE)) &
    theme(plot.background = element_rect(fill = "white", colour = NA))
  attr(p, "planarsviz_size") <- c(width = 11, height = 7)
  attr(p, "planarsviz_units") <- "in"
  attr(p, "planarsviz_folder") <- "boundaries"
  p
}

#' Boundary-strength distributions
#'
#' Left-edge and right-edge strength as two smoothed curves over position
#' (weighted density, computed by the exporter), with a row of dots per side
#' sized by each position's strength.
#' Reproduces `nyan1308_boundary_strength_distributions.pdf`.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param subset `NULL` for the full analysis, or a `subset_id` from `subsets.json`.
#' @param colours Named colours for `left` and `right`.
#' @return A ggplot object with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`), and `planarsviz_folder` (its
#'   `results/planarsviz` subfolder).
#' @export
plot_boundary_strength_distributions <- function(bundle, subset = NULL,
                                                 colours = c(left = "#7876B1", right = "#BC3C29")) {
  validate_planars_bundle(bundle)
  bs <- read_planars_boundary_strength(bundle, subset)
  strength <- bs$strength
  density <- bs$density
  labels <- c(left = "left-edge strength", right = "right-edge strength")

  curves <- rbind(
    data.frame(x = density$x, y = density$left, side = labels[["left"]]),
    data.frame(x = density$x, y = density$right, side = labels[["right"]])
  )
  curves <- curves[!is.na(curves$y), , drop = FALSE]
  curves$side <- factor(curves$side, levels = labels)
  rug <- rbind(
    data.frame(x = strength$position, y = -0.005, area = strength$left_summed / 2, side = labels[["left"]]),
    data.frame(x = strength$position, y = -0.012, area = strength$right_summed / 2, side = labels[["right"]])
  )
  rug$side <- factor(rug$side, levels = labels)
  # matplotlib draws nothing for a zero-area dot; ggplot would still draw a
  # speck (the point's outline), so leave zero-strength positions out.
  rug <- rug[rug$area > 0, , drop = FALSE]
  rug$size <- sqrt(rug$area) / .pt  # matplotlib s is area in pt^2; ggplot size is roughly diameter in mm

  ylow <- min(-0.012, curves$y)
  yhigh <- max(curves$y)
  ylim <- c(ylow, yhigh) + c(-1, 1) * 0.05 * (yhigh - ylow)
  xlim <- range(strength$position) + c(-1, 1)
  fill_values <- stats::setNames(unname(colours[c("left", "right")]), labels)

  p <- ggplot() +
    geom_area(data = curves, aes(x = x, y = y, fill = side), alpha = 0.5, position = "identity") +
    geom_line(data = curves, aes(x = x, y = y, colour = side), linewidth = 1.5 / .pt, show.legend = FALSE) +
    geom_point(data = rug, aes(x = x, y = y, colour = side, size = size), alpha = 0.6, show.legend = FALSE) +
    scale_fill_manual(values = fill_values, name = NULL) +
    scale_colour_manual(values = fill_values, guide = "none") +
    scale_size_identity() +
    scale_x_continuous(breaks = strength$position, limits = xlim, expand = c(0, 0)) +
    scale_y_continuous(limits = ylim, expand = c(0, 0),
                       breaks = planarsviz_mpl_breaks(ylim[[2]], lower = ylim[[1]]),
                       labels = scales::label_number(accuracy = 0.01)) +
    labs(x = "Position on the planar structure", y = "Inferred density (juncture strength)") +
    coord_cartesian(clip = "off") +
    planarsviz_mpl_theme() +
    theme(axis.title = element_text(size = 13), axis.text = element_text(size = 10, colour = "black"),
          legend.position = "inside", legend.position.inside = c(0.995, 0.995),
          legend.justification = c(1, 1), legend.margin = margin(3, 6, 3, 4))
  attr(p, "planarsviz_size") <- c(width = 11, height = 5)
  attr(p, "planarsviz_units") <- "in"
  attr(p, "planarsviz_folder") <- "boundaries"
  p
}
