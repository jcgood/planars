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
# `view` is one argument rather than ten. Those two settings, and the drawing
# itself, moved to R/null_panels.R on 2026-09-22 when the arbitrary-layers
# test arrived wanting the same chart from different tables.

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
  summary_df <- read_planars_span_placement(bundle)
  tally <- read_planars_span_placement_null(bundle)

  # The grid's neutral fill is the pooled row's colour -- one colour, because
  # a per-group palette across nine very different panels would just be
  # noise. Read before the table is narrowed, so asking for a few groups in
  # the grid view still finds it.
  neutral <- summary_df$colour[summary_df$group == "all"]
  if (!length(neutral)) neutral <- "#0072B2"

  picked <- planarsviz_null_select(summary_df, tally, groups, view, "span-placement test")
  planarsviz_null_panels(
    picked$summary_df, picked$tally, picked$groups, view,
    x_lab = "Number of maximal laminar families (that group's own spans, same lengths, random positions)",
    neutral = neutral[[1]]
  )
}
