# Boundary-strength overlay (chart 18 in docs/PLAN_planarsviz_library.md).
#
# Copied, at commit 43a308f, from scripts/analysis/boundary_strength_plot.r
# (see the previous commit for the unchanged copy); its function body is kept
# as it was. Changes since the copy:
#   - literals replaced with bundle data: the strength table
#     (boundary_strength.tsv of the full analysis or a subsets.json analysis,
#     instead of a TSV path), position labels (position_labels.tsv), and the
#     label text colours -- black, red for positions 5-19, #0072B5 for 17,
#     typed in there -- from a named highlight in highlights.tsv
#     (`highlight`, default "orthographic_word", which holds exactly those
#     ranges and colours for nyan1308);
#   - the two calls at the end of the script (all types: #0072B2/#E69F00;
#     without tonosegmental: #009E73/#CC79A7 from the no_tono TSV) become
#     `subset` and `colours` arguments; the defaults reproduce the first;
#   - library() and ggsave() removed; the script's canvas (13 x 7 in) is
#     returned as an attribute.
# The notes below are the script's own, unchanged.
#
# Notes on the non-obvious choices, all still apply to every variant:
#  - No title/subtitle on the chart itself -- kept out entirely rather than
#    risk a stale or wrong description drifting from the code again.
#  - Boxed "N\nName" tick labels, matching the tip-label convention used
#    throughout every ggtree chart in this project (geom_label(), not plain
#    axis text) -- default axis text turned off, these added as an explicit
#    geom_label() layer instead. Positioned by explicitly extending the y
#    AXIS RANGE itself (scale_y_continuous(limits=...)) rather than relying
#    on coord_cartesian(clip="off") alone: clip="off" only stops the
#    plotting device from clipping content outside the panel, but a label's
#    rendered height is fixed in points/font size, not data units, so a
#    small negative y-offset can still put the box's top edge back above
#    y=0, visibly bisected by the panel's own bottom border/axis line --
#    confirmed this actually happening, not just a theoretical risk. Giving
#    the coordinate space real negative headroom avoids that outright,
#    rather than trying to out-guess it with a bigger offset. The negative
#    region has no data and no visible negative tick labels (breaks are
#    listed explicitly, none below 0), so it just reads as blank space
#    reserved for the labels. Label fill stays white to keep the boxes
#    readable against the density colors above them; the label TEXT color
#    follows the highlight (see above). This label-text blue is independent
#    of whatever the bar/density colors happen to be for a given variant --
#    one marks a specific position, the other marks "Left edge"; kept
#    distinct on purpose.
#  - A semi-transparent weighted density curve underlaid behind the bars for
#    each side, via base R's density(x, weights=) -- R's own density() takes
#    weights natively. Each side's curve is rescaled so its own peak matches
#    that side's own tallest bar, purely so the shape reads at a comparable
#    height to the bars on the same panel -- not a second, separately-labeled
#    axis.

#' Boundary-strength overlay
#'
#' Left- and right-edge boundary strength per position as dodged bars over
#' rescaled weighted density curves, with boxed position labels coloured by
#' a position highlight. Reproduces `nyan1308_boundary_strength_overlay.pdf`;
#' with `subset = "no_tono", colours = c(Left = "#009E73", Right = "#CC79A7")`,
#' `nyan1308_boundary_strength_overlay_no_tono.pdf`.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param subset `NULL` for the full analysis, or a `subset_id` from `subsets.json`.
#' @param colours Named fill colours for `Left` and `Right`.
#' @param highlight A `highlight_id` from `highlights.tsv` for the label text
#'   colours, or `NULL` for all black.
#' @return A ggplot object with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`), and `planarsviz_folder` (its
#'   `results/planarsviz` subfolder).
#' @export
plot_boundary_strength_overlay <- function(bundle, subset = NULL,
                                           colours = c(Left = "#0072B2", Right = "#E69F00"),
                                           highlight = "orthographic_word") {
  validate_planars_bundle(bundle)
  strength <- read_planars_boundary_strength(bundle, subset)$strength
  boundary_colors <- colours
  n_positions <- nrow(strength)
  position_labels <- unname(planarsviz_position_labels(bundle$position_labels)[as.character(seq_len(n_positions))])

  # ---- bars ----
  long <- rbind(
    data.frame(Position = strength$position, Boundary = "Left", Strength = strength$left_summed),
    data.frame(Position = strength$position, Boundary = "Right", Strength = strength$right_summed)
  )
  long$Boundary <- factor(long$Boundary, levels = c("Left", "Right"))
  max_strength <- max(long$Strength)

  # ---- weighted density underlay, one per side ----
  # density() needs non-negative weights summing to 1; a side with all-zero
  # weight (shouldn't happen here, but guarded) would break that, so this
  # assumes at least one non-zero weight per side, matching the real data.
  weighted_density <- function(x, w, side_label, peak_target) {
    d <- stats::density(x, weights = w / sum(w), bw = 1, from = 0.5, to = n_positions + 0.5, n = 512)
    scale_factor <- peak_target / max(d$y)
    data.frame(Position = d$x, Density = d$y * scale_factor, Boundary = side_label)
  }
  density_df <- rbind(
    weighted_density(strength$position, strength$left_summed, "Left", max(strength$left_summed)),
    weighted_density(strength$position, strength$right_summed, "Right", max(strength$right_summed))
  )
  density_df$Boundary <- factor(density_df$Boundary, levels = c("Left", "Right"))

  # ---- boxed position labels, drawn manually (see notes above) ----
  y_upper <- max_strength * 1.08
  label_y <- -0.09 * max_strength
  y_lower <- label_y - 0.05 * max_strength # extra buffer below the label row itself

  label_colors <- if (is.null(highlight)) {
    stats::setNames(rep("black", n_positions), as.character(seq_len(n_positions)))
  } else {
    planarsviz_highlight_colours(bundle, highlight)
  }
  label_df <- data.frame(
    Position = seq_len(n_positions),
    Label = paste(seq_len(n_positions), position_labels[seq_len(n_positions)], sep = "\n"),
    Colour = label_colors[as.character(seq_len(n_positions))]
  )

  p <- ggplot() +
    geom_area(
      data = density_df, aes(x = Position, y = Density, fill = Boundary),
      alpha = 0.25, color = NA, position = "identity"
    ) +
    geom_col(
      data = long, aes(x = Position, y = Strength, fill = Boundary),
      position = position_dodge(width = 0.82), width = 0.78, color = "white", linewidth = 0.2
    ) +
    geom_label(
      data = label_df, aes(x = Position, y = label_y, label = Label, colour = Colour),
      size = 3.6, label.padding = unit(0.18, "lines"), lineheight = 0.9, fill = "white"
    ) +
    scale_fill_manual(values = boundary_colors) +
    scale_colour_identity() +
    scale_x_continuous(breaks = seq_len(n_positions), expand = expansion(add = 0.6)) +
    scale_y_continuous(
      limits = c(y_lower, y_upper), expand = c(0, 0),
      breaks = seq(0, ceiling(y_upper / 50) * 50, by = 50)
    ) +
    labs(
      x = NULL,
      y = "Boundary strength (summed)",
      fill = "Edge"
    ) +
    coord_cartesian(clip = "off") +
    theme_bw(base_size = 12) +
    theme(
      axis.text.x = element_blank(),
      axis.ticks.x = element_blank(),
      axis.title.y = element_text(margin = margin(r = 8)),
      panel.grid.minor = element_blank(),
      plot.margin = margin(t = 10, r = 10, b = 15, l = 10),
      legend.position = "top"
    )

  attr(p, "planarsviz_size") <- c(width = 13, height = 7)
  attr(p, "planarsviz_units") <- "in"
  attr(p, "planarsviz_folder") <- "boundaries"
  p
}
