# Boundary-strength permutation test: is the per-position strength
# (`plot_boundary_strength()`'s numbers), and its jump from the previous
# position, higher than a same-length-profile random arrangement of spans
# would produce? Written directly in the package from the start -- like
# `plot_fragmentation_test()` (see fragmentation.R), this has no earlier
# script or chart to port or freeze a reference against. The numbers come
# from the bundle (boundary_strength_test.tsv, written by calling
# boundary_strength_test.py's run_test() through the exporter's
# --boundary-strength-test-permutations flag).

#' Read the boundary-strength permutation test from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A data frame: `group`, `kind`, `label`, `colour`, `side`,
#'   `statistic` (`"level"` or `"jump"`), `position`, `observed`,
#'   `null_mean`, `null_p05`, `null_p95`, `p_value_ge_observed`,
#'   `n_permutations`, `seed`.
#' @export
read_planars_boundary_strength_test <- function(bundle) {
  path <- file.path(bundle$bundle_dir, "data", "boundary_strength_test.tsv")
  if (!file.exists(path)) {
    stop("This bundle has no boundary_strength_test.tsv. The permutation test is ",
      "slow, so the exporter only runs it when asked: re-export with ",
      "--boundary-strength-test-permutations 5000.",
      call. = FALSE
    )
  }
  utils::read.delim(path, stringsAsFactors = FALSE, colClasses = c(
    position = "integer", observed = "numeric", null_mean = "numeric",
    null_p05 = "numeric", null_p95 = "numeric", p_value_ge_observed = "numeric",
    n_permutations = "integer", seed = "integer"
  ), na.strings = character(), comment.char = "")
}

#' Plot the boundary-strength permutation test for one group
#'
#' For each position, the observed value (line + point) against the null's
#' 5th-95th percentile band (ribbon) and mean (dashed line), for the left
#' edge (top panel) and right edge (bottom panel). Points where
#' `p_value_ge_observed` is below `alpha` are filled; others are open, so a
#' real boundary candidate -- a run of filled points, ideally with a visible
#' rise at that position -- is visually distinct from noise.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param group Which group's test to plot -- `"all"` (pooled, the default),
#'   a domain type, or a bundle name from `planars_groupings.BUNDLES`.
#' @param statistic `"jump"` (the default -- strength\\[p\\] - strength\\[p-1\\],
#'   the direct test of a quantal discontinuity) or `"level"` (the summed
#'   strength itself).
#' @param alpha Significance threshold for filled vs. open points (default 0.05).
#' @param line_colour Observed-curve colour.
#' @return A patchwork plot with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`), and `planarsviz_folder` (its
#'   `results/planarsviz` subfolder).
#' @export
plot_boundary_strength_test <- function(bundle, group = "all", statistic = "jump",
                                        alpha = 0.05, line_colour = "#7876B1") {
  validate_planars_bundle(bundle)
  statistic <- match.arg(statistic, c("jump", "level"))
  test <- read_planars_boundary_strength_test(bundle)
  available <- unique(test$group)
  if (!group %in% available) {
    stop("No group '", group, "' in this bundle's boundary_strength_test.tsv. Available: ",
      paste(available, collapse = ", "),
      call. = FALSE
    )
  }
  test <- test[test$group == group & test$statistic == statistic, , drop = FALSE]
  test$significant <- test$p_value_ge_observed < alpha
  label <- test$label[[1]]
  statistic_title <- if (statistic == "jump") "Jump from previous position" else "Strength"

  panel <- function(side_value, ylabel, top_panel) {
    d <- test[test$side == side_value, , drop = FALSE]
    yrange <- range(d$observed, d$null_p05, d$null_p95)
    pad <- diff(yrange) * 0.08
    if (pad == 0) pad <- 1
    p <- ggplot(d, aes(x = position)) +
      geom_ribbon(aes(ymin = null_p05, ymax = null_p95),
        fill = "grey60", alpha = 0.3
      ) +
      geom_line(aes(y = null_mean),
        colour = "grey40", linetype = "dashed",
        linewidth = 0.7 / .pt
      ) +
      geom_line(aes(y = observed), colour = line_colour, linewidth = 1 / .pt) +
      geom_point(aes(y = observed, fill = significant),
        shape = 21, size = 2.4,
        colour = line_colour, stroke = 0.8
      ) +
      scale_fill_manual(
        values = c(`TRUE` = line_colour, `FALSE` = "white"),
        labels = c(`TRUE` = paste0("p < ", alpha), `FALSE` = paste0("p ≥ ", alpha)),
        name = NULL
      ) +
      scale_x_continuous(breaks = d$position) +
      scale_y_continuous(limits = yrange + c(-pad, pad)) +
      labs(x = if (top_panel) NULL else "Position on the planar structure", y = ylabel) +
      planarsviz_mpl_theme() +
      theme(axis.title = element_text(size = 13), axis.text = element_text(size = 11, colour = "black"))
    if (top_panel) {
      p + theme(
        axis.text.x = element_blank(),
        legend.position = "inside", legend.position.inside = c(0.005, 0.995),
        legend.justification = c(0, 1), legend.margin = margin(3, 6, 3, 4)
      )
    } else {
      p + theme(legend.position = "none")
    }
  }

  p <- (panel("left", "Left edge", TRUE) / panel("right", "Right edge", FALSE)) &
    plot_annotation(
      title = paste0(statistic_title, " vs. a same-length-profile random null — ", label),
      theme = theme(plot.title = element_text(size = 12))
    ) &
    theme(plot.background = element_rect(fill = "white", colour = NA))
  attr(p, "planarsviz_size") <- c(width = 11, height = 7)
  attr(p, "planarsviz_units") <- "in"
  attr(p, "planarsviz_folder") <- "boundaries"
  p
}
