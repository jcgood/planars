# Combined left/right boundary-strength overlay(s) for Chichewa (nyan1308),
# read from nyan1308_boundary_strength*.tsv (written by boundary_strength.py,
# including its --subset variants). Same dodged-bar convention as
# nyan_boundary_skyline.r's p_all panel, but for boundary strength (summed --
# weighted by how many of the source dataset's maximal laminar families each
# contributing span appears in), not raw test counts. The capped/ceilinged
# reference values in that TSV are deliberately not used here -- summed is
# the analytical object, see boundary_strength.py's own docstring.
#
# Refactored into one function + one call per variant (currently: all domain
# types pooled, and the same thing with tonosegmental excluded) so a future
# domain-type breakdown is a new call with a new TSV/color pair, not a
# rewrite -- matching boundary_strength.py's own --subset design.
#
# Notes on the non-obvious choices, all still apply to every variant below:
#  - Colors: each variant gets its own colorblind-safe pair (see call sites),
#    deliberately ordinary choices rather than anything unusual.
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
#    follows the same orthographic-word convention as
#    nyan1308_all_families_labeled_wordhood.r: black by default, red for
#    positions 5-19 (the orthographic word), blue (#0072B5, not green --
#    stays distinguishable from red under red-green colorblindness) for
#    position 17 specifically (FV, the final vowel). This label-text blue is
#    independent of whatever the bar/density colors happen to be for a given
#    variant -- one marks a specific position, the other marks "Left edge";
#    kept distinct on purpose.
#  - A semi-transparent weighted density curve underlaid behind the bars for
#    each side, via base R's density(x, weights=) -- no need for
#    Python/scipy here, R's own density() takes weights natively. Each
#    side's curve is rescaled so its own peak matches that side's own
#    tallest bar, purely so the shape reads at a comparable height to the
#    bars on the same panel -- not a second, separately-labeled axis.

library(ggplot2)

output_dir <- "../../results"

position_labels <- c(
  "QM", "PreSbj", "Sbj", "PostSbj", "Neg1", "SM", "Neg2", "TAM",
  "OM", "Root", "Ext", "STAT", "CAUS", "APPL", "REC", "PASS",
  "FV", "2P", "Enc", "Obj1", "Obj2", "PostObj"
)

plot_boundary_strength <- function(input_file, output_name, boundary_colors) {
  strength <- read.delim(input_file, stringsAsFactors = FALSE, check.names = FALSE)
  n_positions <- nrow(strength)

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
    d <- density(x, weights = w / sum(w), bw = 1, from = 0.5, to = n_positions + 0.5, n = 512)
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
  y_lower <- label_y - 0.05 * max_strength  # extra buffer below the label row itself

  label_colors <- setNames(rep("black", n_positions), as.character(seq_len(n_positions)))
  label_colors[as.character(5:19)] <- "red"
  label_colors["17"] <- "#0072B5"
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

  ggsave(file.path(output_dir, output_name), p, device = "pdf", width = 13, height = 7, units = "in")
}

# All domain types pooled: blue (#0072B2) / orange (#E69F00), Okabe-Ito.
plot_boundary_strength(
  "../../results/nyan1308_boundary_strength.tsv",
  "nyan1308_boundary_strength_overlay.pdf",
  c(Left = "#0072B2", Right = "#E69F00")
)

# Tonosegmental excluded: bluish green (#009E73) / reddish purple (#CC79A7),
# the other standard Okabe-Ito pair -- visually distinct from the pooled
# chart's blue/orange so the two are never mistaken for each other, while
# staying equally colorblind-safe.
plot_boundary_strength(
  "../../results/nyan1308_boundary_strength_no_tono.tsv",
  "nyan1308_boundary_strength_overlay_no_tono.pdf",
  c(Left = "#009E73", Right = "#CC79A7")
)
