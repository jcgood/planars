# Class-fragmentation permutation test (chart 19 in docs/PLAN_planarsviz_library.md).
#
# Unlike every other chart in this package, this one has no earlier original to
# reproduce line for line: it was written directly in R in 2026-09, as
# scripts/analysis/fragmentation_test_plot.r, and there has never been a
# matplotlib version. That script is the source this was copied from, and the
# chart it drew -- results/planarsviz/reference/nyan1308_fragmentation_test_plot.png
# -- is the reference the porting check compares against.
#
# Changes from the copy, both of them removing nyan1308 facts from the R:
#   - the display labels were a hardcoded lookup of the eight group ids; they
#     now come from the bundle's own `label` column.
#   - the colours were read from a `color` column the Python wrote from its own
#     palette; they now come from the bundle's `colour` column, spelled the way
#     every other bundle table spells it.
#
# The script had a second call, drawing just two of the bundles for someone
# presenting them on their own. That became the `groups` argument on
# 2026-09-21, when the script was archived: it was the last thing still
# writing a chart into results/ that the package also wrote, so whichever ran
# last won and nothing recorded which.
#
# The null distributions arrive as a tally (one row per distinct family count
# per group, with `n`) rather than one row per draw, which is the same
# information in 227 rows instead of 40,000. They are expanded back to one row
# per draw before drawing. That is deliberate rather than lazy: geom_violin
# does accept a `weight` aesthetic, but its density estimate weights and
# normalises differently enough that the result is not guaranteed identical to
# what the original drew, and this chart's whole check is that it is identical.
# 40,000 rows is nothing to hold in memory, so the expansion buys exactness for
# no real cost.

#' Read the fragmentation test summary from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A data frame: `group`, `kind`, `label`, `colour`, `n_tests`,
#'   `observed_families`, `null_mean`, `null_p05`, `null_p95`,
#'   `p_value_le_observed`, `n_permutations`, `seed`.
#' @export
read_planars_fragmentation <- function(bundle) {
  path <- file.path(bundle$bundle_dir, "data", "fragmentation_test.tsv")
  if (!file.exists(path)) {
    stop("This bundle has no fragmentation_test.tsv. The permutation test is ",
      "slow, so the exporter only runs it when asked: re-export with ",
      "--fragmentation-permutations 5000.",
      call. = FALSE
    )
  }
  utils::read.delim(path, stringsAsFactors = FALSE, colClasses = c(
    n_tests = "integer", observed_families = "integer",
    null_p05 = "integer", null_p95 = "integer",
    n_permutations = "integer", seed = "integer"
  ), na.strings = character(), comment.char = "")
}

#' Read the fragmentation null distributions from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param expand Return one row per draw (the default) rather than the stored
#'   tally of `group`, `kind`, `family_count`, `n`.
#' @return A data frame.
#' @export
read_planars_fragmentation_null <- function(bundle, expand = TRUE) {
  path <- file.path(bundle$bundle_dir, "data", "fragmentation_null.tsv")
  if (!file.exists(path)) {
    stop("This bundle has no fragmentation_null.tsv. The permutation test is ",
      "slow, so the exporter only runs it when asked: re-export with ",
      "--fragmentation-permutations 5000.",
      call. = FALSE
    )
  }
  tally <- utils::read.delim(path, stringsAsFactors = FALSE, colClasses = c(
    family_count = "integer", n = "integer"
  ), na.strings = character(), comment.char = "")
  if (!expand) {
    return(tally)
  }
  idx <- rep(seq_len(nrow(tally)), tally$n)
  data.frame(
    group = tally$group[idx],
    kind = tally$kind[idx],
    family_count = tally$family_count[idx],
    stringsAsFactors = FALSE
  )
}

#' Plot the class-fragmentation permutation test
#'
#' One horizontal violin per group -- the family counts under permuted domain
#' type labels -- with that group's observed family count as a filled dot and
#' its p-value at the right. Domain types and bundles are two stacked panels
#' sharing one x axis, so the raw scale stays comparable rather than being
#' normalised away.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param groups Draw only these groups, by their `group` ids, instead of
#'   every group the test covers. When what is left is all one kind, the
#'   panel strip is dropped rather than drawn as a single pointless label.
#' @return A ggplot object with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`), `planarsviz_transparent` and
#'   `planarsviz_folder` (its `results/planarsviz` subfolder).
#' @export
plot_fragmentation_test <- function(bundle, groups = NULL) {
  validate_planars_bundle(bundle)
  summary_df <- read_planars_fragmentation(bundle)
  null_draws <- read_planars_fragmentation_null(bundle)

  if (!is.null(groups)) {
    unknown <- setdiff(groups, summary_df$group)
    if (length(unknown)) {
      stop("No group `", paste(unknown, collapse = "`, `"),
        "` in this bundle's fragmentation test. It covers: ",
        paste(summary_df$group, collapse = ", "), ".",
        call. = FALSE
      )
    }
    summary_df <- summary_df[summary_df$group %in% groups, , drop = FALSE]
    null_draws <- null_draws[null_draws$group %in% groups, , drop = FALSE]
  }

  # Bottom-to-top by n_tests ascending, classes before bundles. The factor's
  # global level order sets each facet's own row order under
  # facet_grid(scales = "free_y"), so building it once here is enough.
  summary_df <- summary_df[order(summary_df$kind == "bundle", summary_df$n_tests), ]
  group_levels <- summary_df$group
  kind_levels <- c("class", "bundle")
  multi_kind <- length(unique(summary_df$kind)) > 1
  summary_df$group <- factor(summary_df$group, levels = group_levels)
  summary_df$kind <- factor(summary_df$kind, levels = kind_levels)
  null_draws$group <- factor(null_draws$group, levels = group_levels)
  null_draws$kind <- factor(null_draws$kind, levels = kind_levels)

  colour_map <- stats::setNames(summary_df$colour, as.character(summary_df$group))
  label_map <- stats::setNames(summary_df$label, as.character(summary_df$group))

  # One fixed p-value x per panel, just past that panel's own widest data. A
  # single global position would either crowd the class panel or sit oddly far
  # from the bundle panel's much wider range. With one panel there is nothing
  # to stagger, so one x serves the whole chart.
  if (multi_kind) {
    null_max <- stats::aggregate(family_count ~ kind, data = null_draws, FUN = max)
    names(null_max) <- c("kind", "null_max")
    obs_max <- stats::aggregate(observed_families ~ kind, data = summary_df, FUN = max)
    names(obs_max) <- c("kind", "obs_max")
    panel_max <- merge(null_max, obs_max, by = "kind")
    panel_max$label_x <- pmax(panel_max$null_max, panel_max$obs_max) * 1.08
    summary_df <- merge(summary_df, panel_max[, c("kind", "label_x")], by = "kind")
  } else {
    summary_df$label_x <- max(
      max(null_draws$family_count),
      max(summary_df$observed_families)
    ) * 1.08
  }

  p <- ggplot() +
    geom_violin(
      data = null_draws, aes(x = family_count, y = group, fill = group),
      bw = 1, scale = "width", width = 0.75, alpha = 0.45, color = NA
    ) +
    geom_point(
      data = summary_df, aes(x = observed_families, y = group, fill = group),
      shape = 21, size = 4, color = "black", stroke = 0.9
    ) +
    geom_text(
      data = summary_df,
      aes(
        x = label_x, y = group,
        label = sprintf("p=%.3f", p_value_le_observed)
      ),
      hjust = 0, size = 3.6, color = "black"
    ) +
    scale_fill_manual(values = colour_map, guide = "none") +
    scale_y_discrete(labels = label_map) +
    scale_x_continuous(expand = expansion(mult = c(0.02, 0.16))) +
    coord_cartesian(clip = "off") +
    labs(
      x = "Number of maximal laminar families (violin: permuted null; dot: observed)",
      y = NULL
    ) +
    theme_bw(base_size = 12) +
    theme(
      strip.background = element_rect(fill = "grey90", color = NA),
      strip.text = element_text(face = "bold"),
      panel.grid.minor = element_blank(),
      plot.margin = margin(t = 10, r = 60, b = 10, l = 10)
    )

  if (multi_kind) {
    p <- p + facet_grid(kind ~ .,
      scales = "free_y", space = "free_y",
      labeller = as_labeller(c(class = "Domain type", bundle = "Bundle"))
    )
  }

  # Two canvases, because the script this came from hardcoded a ggsave() size
  # for each of its two calls and no formula connects them. A `groups` list
  # other than the pair of bundles may well want a size of its own; set the
  # attribute on the returned plot to change it.
  attr(p, "planarsviz_size") <- if (multi_kind) c(width = 10, height = 6.5) else c(width = 9, height = 3.2)
  attr(p, "planarsviz_units") <- "in"
  attr(p, "planarsviz_transparent") <- FALSE
  attr(p, "planarsviz_folder") <- "counts-and-chance"
  p
}
