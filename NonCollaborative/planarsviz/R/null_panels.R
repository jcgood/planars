# The shared drawing behind the two "null distribution per group" charts:
# span placement (R/span_placement.R) and arbitrary layers
# (R/arbitrary_layers.R).
#
# Both show the same thing in the same way -- one panel per group, that
# group's null distribution of family counts as bars with a density curve
# over them, its real observed count as a dashed line, and its p-value in the
# panel -- and differ only in which tables they read and what the x axis
# says. The drawing was hoisted here on 2026-09-22, when the arbitrary-layers
# test was integrated, rather than copied a second time; the span-placement
# chart has frozen reference images, so this hoist is checked against them
# pixel for pixel exactly as the port that created it was.
#
# Panels deliberately share no axis. An absolute family count is not
# comparable across groups with very different span counts -- 6 families means
# something different for an 11-span group than a 20-span one -- and the
# comparable quantity is each group's own p-value, which is already one number
# per panel. facet_wrap(scales = "free") also matters on the y axis, not just
# the x: a 3-span group has almost no distinct family-count values, so one bar
# absorbs a large share of the draws, and sharing y with a 26-span group's much
# flatter distribution would squash every other panel toward zero height and
# silently misplace each panel's own p-value annotation. That was seen
# happening, not reasoned about.

# The two presentations. Their numbers are not independent knobs, which is why
# they travel together as one `view` rather than as ten arguments: at the
# standalone chart's larger annotation and tighter headroom a right-extending
# label runs into the bars, so it is right-aligned there -- and right-alignment
# is not safe in the grid, where several groups have their observed count at
# the panel's own axis minimum and a left-extending label gets clipped. Both
# were seen happening.
null_panel_views <- list(
  # The multi-panel grid. These numbers reproduce theme_bw(base_size = 11)'s
  # own automatic axis sizes and the strip size the chart already used.
  grid = list(
    ncol = 3, width = 11, height = 9,
    y_top_pad = 0.38, annotation_size = 3.1, label_y_frac = 1.35,
    label_hjust = -0.05, x_left_pad = 0.05,
    axis_text_size = 8.8, axis_title_size = 11, strip_text_size = 9
  ),
  # One group meant to stand alone rather than sit packed into a grid: the
  # group's own colour, a bigger annotation, and an axis that hugs the data
  # instead of reserving headroom purely for the label.
  standalone = list(
    ncol = 1, width = 9, height = 5.5,
    y_top_pad = 0.06, annotation_size = 5, label_y_frac = 0.9,
    label_hjust = 1.05, x_left_pad = 0.14,
    axis_text_size = 13, axis_title_size = 14, strip_text_size = 15
  )
)

# Resolve `groups` against a summary table and narrow both tables to it,
# keeping the order asked for. Shared so the two charts refuse an unknown
# group the same way and name the same alternatives.
planarsviz_null_select <- function(summary_df, tally, groups, view, what) {
  if (is.null(groups)) groups <- summary_df$group
  unknown <- setdiff(groups, summary_df$group)
  if (length(unknown)) {
    stop("No group `", paste(unknown, collapse = "`, `"),
      "` in this bundle's ", what, ". It covers: ",
      paste(summary_df$group, collapse = ", "), ".",
      call. = FALSE
    )
  }
  if (view == "standalone" && length(groups) != 1L) {
    stop("The standalone view draws one group; ", length(groups), " were asked for.", call. = FALSE)
  }
  list(
    groups = groups,
    summary_df = summary_df[match(groups, summary_df$group), , drop = FALSE],
    tally = tally[tally$group %in% groups, , drop = FALSE]
  )
}

# Draw the panels. `neutral` is the grid's single fill; standalone uses the
# group's own colour instead.
planarsviz_null_panels <- function(summary_df, tally, groups, view, x_lab, neutral) {
  settings <- null_panel_views[[view]]
  labels <- stats::setNames(summary_df$label, summary_df$group)
  fill_colour <- if (view == "standalone") summary_df$colour[[1]] else neutral

  summary_df$group <- factor(summary_df$group, levels = groups, labels = labels[groups])
  tally$group <- factor(tally$group, levels = groups, labels = labels[groups])

  # Weighted density per group, rescaled to that group's own histogram peak,
  # computed once per group since each has its own support and bandwidth.
  density_df <- do.call(rbind, lapply(split(tally, tally$group), function(sub) {
    peak_height <- max(sub$n)
    bw <- max(1, diff(range(sub$family_count)) / 15)
    dens <- stats::density(sub$family_count,
      weights = sub$n / sum(sub$n), bw = bw,
      from = min(sub$family_count) - 1, to = max(sub$family_count) + 1, n = 256
    )
    data.frame(group = sub$group[1], x = dens$x, y = dens$y * peak_height / max(dens$y))
  }))

  peak_by_group <- stats::aggregate(n ~ group, data = tally, FUN = max)
  names(peak_by_group) <- c("group", "peak_height")
  summary_df <- merge(summary_df, peak_by_group, by = "group")
  summary_df$annotation <- sprintf(
    "obs = %d\np(<=obs) = %.3f",
    summary_df$observed_families, summary_df$p_value_le_observed
  )
  # label_y_frac is deliberately independent of y_top_pad. The two were once
  # coupled, which quietly moved the grid chart's labels when the padding
  # changed.
  summary_df$label_y <- summary_df$peak_height * settings$label_y_frac

  p <- ggplot() +
    geom_col(
      data = tally, aes(x = family_count, y = n),
      fill = fill_colour, alpha = 0.55, width = 1, color = NA
    ) +
    geom_line(data = density_df, aes(x = x, y = y), color = fill_colour, linewidth = 0.8) +
    geom_vline(
      data = summary_df, aes(xintercept = observed_families),
      linetype = "dashed", color = "black", linewidth = 0.7
    ) +
    geom_text(
      data = summary_df, aes(x = observed_families, y = label_y, label = annotation),
      hjust = settings$label_hjust, vjust = 1, size = settings$annotation_size,
      color = "black"
    ) +
    facet_wrap(~group, scales = "free", ncol = settings$ncol) +
    scale_x_continuous(expand = expansion(mult = c(settings$x_left_pad, 0.05))) +
    scale_y_continuous(expand = expansion(mult = c(0, settings$y_top_pad))) +
    labs(x = x_lab, y = "Permutations producing that count") +
    theme_bw(base_size = 11) +
    theme(
      strip.background = element_rect(fill = "grey90", color = NA),
      strip.text = element_text(face = "bold", size = settings$strip_text_size),
      axis.text = element_text(size = settings$axis_text_size),
      axis.title = element_text(size = settings$axis_title_size),
      panel.grid.minor = element_blank(),
      plot.margin = margin(t = 10, r = 12, b = 10, l = 10)
    )

  attr(p, "planarsviz_size") <- c(width = settings$width, height = settings$height)
  attr(p, "planarsviz_units") <- "in"
  attr(p, "planarsviz_folder") <- "counts-and-chance"
  p
}
