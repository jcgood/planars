# Span-placement permutation test: does the real arrangement of a group's
# spans give fewer laminar families than those same span lengths placed at
# random would?
#
# Copied on 2026-09-21 from scripts/analysis/span_placement_test_plot.r, the
# last thing still drawing a chart straight into results/ without a chart
# name or a manifest row. Like the fragmentation chart, it was written in R
# from the start -- there is no matplotlib original -- so the references the
# renderer check compares against are the three charts that script drew,
# frozen before the package could overwrite them.
#
# Changes from the copy, the same two the fragmentation port made: the
# display labels were a hardcoded lookup of the nine group ids and the two
# bundle colours were hardcoded hex, and both now come from the bundle's own
# `label` and `colour` columns.
#
# The script had three calls and only two settings between them, which is why
# `view` is one argument rather than ten. Its own comments explain why the
# ten numbers are not independent knobs: at the standalone chart's larger
# annotation and tighter headroom a right-extending label runs into the bars,
# so it is right-aligned there -- and right-alignment is not safe in the grid,
# where several groups have their observed count sitting at the panel's own
# axis minimum and a left-extending label gets clipped. Both were seen
# happening, not reasoned about. So the two sets travel together.

SPAN_PLACEMENT_VIEWS <- list(
  # The nine-panel grid. These numbers reproduce theme_bw(base_size = 11)'s
  # own automatic axis sizes and the strip size the chart already used.
  grid = list(ncol = 3, width = 11, height = 9, fill = NULL,
              y_top_pad = 0.38, annotation_size = 3.1, label_y_frac = 1.35,
              label_hjust = -0.05, x_left_pad = 0.05,
              axis_text_size = 8.8, axis_title_size = 11, strip_text_size = 9),
  # One group meant to stand alone rather than sit packed into a 3x3 grid:
  # the group's own colour, a bigger annotation, and an axis that hugs the
  # data instead of reserving headroom purely for the label.
  standalone = list(ncol = 1, width = 9, height = 5.5, fill = NULL,
                    y_top_pad = 0.06, annotation_size = 5, label_y_frac = 0.9,
                    label_hjust = 1.05, x_left_pad = 0.14,
                    axis_text_size = 13, axis_title_size = 14, strip_text_size = 15)
)

#' Read the span-placement test summary from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A data frame: `group`, `kind`, `label`, `colour`, `n_spans`,
#'   `n_positions`, `observed_families`, the null summary columns,
#'   `p_value_le_observed`, `n_truncated`, `n_permutations`, `seed`.
#' @export
read_planars_span_placement <- function(bundle) {
  path <- file.path(bundle$bundle_dir, "data", "span_placement_test.tsv")
  if (!file.exists(path)) {
    stop("This bundle has no span_placement_test.tsv. The permutation test is ",
         "slow, so the exporter only runs it when asked: re-export with ",
         "--span-placement-permutations 5000.", call. = FALSE)
  }
  utils::read.delim(path, stringsAsFactors = FALSE, colClasses = c(
    n_spans = "integer", n_positions = "integer", observed_families = "integer",
    null_p05 = "integer", null_p50 = "integer", null_p95 = "integer",
    n_truncated = "integer", n_permutations = "integer", seed = "integer"
  ), na.strings = character(), comment.char = "")
}

#' Read the span-placement null distributions from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A data frame: `group`, `kind`, `family_count`, `n` -- a tally, one
#'   row per distinct family count per group. Unlike the fragmentation null
#'   this is not expanded back to one row per draw: the chart draws the tally
#'   directly as bars and weights its own density curve by `n`.
#' @export
read_planars_span_placement_null <- function(bundle) {
  path <- file.path(bundle$bundle_dir, "data", "span_placement_null.tsv")
  if (!file.exists(path)) {
    stop("This bundle has no span_placement_null.tsv. The permutation test is ",
         "slow, so the exporter only runs it when asked: re-export with ",
         "--span-placement-permutations 5000.", call. = FALSE)
  }
  utils::read.delim(path, stringsAsFactors = FALSE, colClasses = c(
    family_count = "integer", n = "integer"
  ), na.strings = character(), comment.char = "")
}

#' Plot the span-placement permutation test
#'
#' One panel per group: that group's null distribution of family counts, from
#' re-placing its own spans' lengths at random, with its real observed count
#' as a dashed line and its p-value in the panel. Panels do not share an axis
#' -- an absolute family count is not comparable across groups with very
#' different span counts, and the comparable quantity is each panel's own
#' p-value.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param groups Draw only these groups, by their `group` ids, in the order
#'   given. Default: every group the test covers.
#' @param view `"grid"` for the multi-panel chart (a neutral fill, room above
#'   each panel's peak for its label), `"standalone"` for one group on its own
#'   (its own colour, a larger label, an axis that hugs the data).
#' @return A ggplot object with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`) and `planarsviz_folder` (its
#'   `results/planarsviz` subfolder).
#' @export
plot_span_placement_test <- function(bundle, groups = NULL, view = c("grid", "standalone")) {
  validate_planars_bundle(bundle)
  view <- match.arg(view)
  settings <- SPAN_PLACEMENT_VIEWS[[view]]

  summary_df <- read_planars_span_placement(bundle)
  tally <- read_planars_span_placement_null(bundle)
  if (is.null(groups)) groups <- summary_df$group
  unknown <- setdiff(groups, summary_df$group)
  if (length(unknown)) {
    stop("No group `", paste(unknown, collapse = "`, `"),
         "` in this bundle's span-placement test. It covers: ",
         paste(summary_df$group, collapse = ", "), ".", call. = FALSE)
  }
  if (view == "standalone" && length(groups) != 1L) {
    stop("The standalone view draws one group; ", length(groups), " were asked for.", call. = FALSE)
  }

  # The grid's neutral fill is the pooled row's colour -- one colour, because
  # a per-group palette across nine very different panels would just be
  # noise. Read before the table is narrowed, so asking for a few groups in
  # the grid view still finds it. Standing alone, a group wears its own
  # colour instead: the one it has in its ghost overlay and its
  # fragmentation violin.
  neutral <- summary_df$colour[summary_df$group == "all"]
  if (!length(neutral)) neutral <- "#0072B2"

  summary_df <- summary_df[match(groups, summary_df$group), , drop = FALSE]
  tally <- tally[tally$group %in% groups, , drop = FALSE]
  labels <- stats::setNames(summary_df$label, summary_df$group)
  fill_colour <- if (view == "standalone") summary_df$colour[[1]] else neutral[[1]]

  summary_df$group <- factor(summary_df$group, levels = groups, labels = labels[groups])
  tally$group <- factor(tally$group, levels = groups, labels = labels[groups])

  # Weighted density per group, rescaled to that group's own histogram peak,
  # computed once per group since each has its own support and bandwidth.
  density_df <- do.call(rbind, lapply(split(tally, tally$group), function(sub) {
    peak_height <- max(sub$n)
    bw <- max(1, diff(range(sub$family_count)) / 15)
    dens <- stats::density(sub$family_count, weights = sub$n / sum(sub$n), bw = bw,
                           from = min(sub$family_count) - 1, to = max(sub$family_count) + 1, n = 256)
    data.frame(group = sub$group[1], x = dens$x, y = dens$y * peak_height / max(dens$y))
  }))

  peak_by_group <- stats::aggregate(n ~ group, data = tally, FUN = max)
  names(peak_by_group) <- c("group", "peak_height")
  summary_df <- merge(summary_df, peak_by_group, by = "group")
  summary_df$annotation <- sprintf("obs = %d\np(<=obs) = %.3f",
                                   summary_df$observed_families, summary_df$p_value_le_observed)
  # label_y_frac is deliberately independent of y_top_pad. The two were once
  # coupled, which quietly moved the grid chart's labels when the padding
  # changed.
  summary_df$label_y <- summary_df$peak_height * settings$label_y_frac

  p <- ggplot() +
    geom_col(data = tally, aes(x = family_count, y = n),
             fill = fill_colour, alpha = 0.55, width = 1, color = NA) +
    geom_line(data = density_df, aes(x = x, y = y), color = fill_colour, linewidth = 0.8) +
    geom_vline(data = summary_df, aes(xintercept = observed_families),
               linetype = "dashed", color = "black", linewidth = 0.7) +
    geom_text(data = summary_df, aes(x = observed_families, y = label_y, label = annotation),
              hjust = settings$label_hjust, vjust = 1, size = settings$annotation_size,
              color = "black") +
    facet_wrap(~ group, scales = "free", ncol = settings$ncol) +
    scale_x_continuous(expand = expansion(mult = c(settings$x_left_pad, 0.05))) +
    scale_y_continuous(expand = expansion(mult = c(0, settings$y_top_pad))) +
    labs(
      x = "Number of maximal laminar families (that group's own spans, same lengths, random positions)",
      y = "Permutations producing that count"
    ) +
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
