# Arbitrary-layers permutation test: is a group's family count remarkable for
# that many spans of arbitrary size at arbitrary positions?
#
# Integrated 2026-09-22 from scripts/analysis/scratch_25layers_covering.py,
# which answered the pooled version of this question as scratch work. Unlike
# every other chart in this package there was never an R original to port --
# the scratch printed numbers and drew nothing -- so this chart has no frozen
# reference and the renderer check reports it as having none. What it does
# have is arbitrary_layers_test.py's own committed TSVs, which the bundle must
# reproduce.
#
# The drawing is R/null_panels.R's, shared with the span-placement chart:
# same panels, same annotation, different tables and a different x axis. The
# two tests are deliberately different nulls -- see
# scripts/analysis/arbitrary_layers_test.py's module docstring for how the
# project's three permutation tests relate -- but they answer in the same
# currency, a family count against a null distribution, so they are read more
# easily side by side than in two different chart forms.

#' Read the arbitrary-layers test summary from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A data frame: `group`, `kind`, `label`, `colour`, `n_spans`,
#'   `n_positions`, `includes_root`, `observed_families`, the null summary
#'   columns, `p_value_le_observed`, `n_truncated`, `n_permutations`, `seed`.
#' @export
read_planars_arbitrary_layers <- function(bundle) {
  path <- file.path(bundle$bundle_dir, "data", "arbitrary_layers_test.tsv")
  if (!file.exists(path)) {
    stop("This bundle has no arbitrary_layers_test.tsv. The permutation test is ",
      "slow, so the exporter only runs it when asked: re-export with ",
      "--arbitrary-layers-permutations 5000.",
      call. = FALSE
    )
  }
  utils::read.delim(path, stringsAsFactors = FALSE, colClasses = c(
    n_spans = "integer", n_positions = "integer", observed_families = "integer",
    null_p05 = "integer", null_p50 = "integer", null_p95 = "integer",
    n_truncated = "integer", n_permutations = "integer", seed = "integer"
  ), na.strings = character(), comment.char = "")
}

#' Read the arbitrary-layers null distributions from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A data frame: `group`, `kind`, `family_count`, `n` -- a tally, one
#'   row per distinct family count per group, the same shape as the
#'   span-placement null.
#' @export
read_planars_arbitrary_layers_null <- function(bundle) {
  path <- file.path(bundle$bundle_dir, "data", "arbitrary_layers_null.tsv")
  if (!file.exists(path)) {
    stop("This bundle has no arbitrary_layers_null.tsv. The permutation test is ",
      "slow, so the exporter only runs it when asked: re-export with ",
      "--arbitrary-layers-permutations 5000.",
      call. = FALSE
    )
  }
  utils::read.delim(path, stringsAsFactors = FALSE, colClasses = c(
    family_count = "integer", n = "integer"
  ), na.strings = character(), comment.char = "")
}

#' Plot the arbitrary-layers permutation test
#'
#' One panel per group: how many maximal laminar families that many spans
#' would produce if their sizes and positions were arbitrary, with the group's
#' real count as a dashed line and its p-value in the panel. The weakest of
#' the project's three nulls -- it knows only how many spans a group has, not
#' how big they are -- and so the baseline a raw family count is implicitly
#' read against.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param groups Draw only these groups, by their `group` ids, in the order
#'   given. Default: every group the test covers.
#' @param view `"grid"` for the multi-panel chart, `"standalone"` for one
#'   group on its own in its own colour. Same two presentations as
#'   [plot_span_placement_test()].
#' @return A ggplot object with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`) and `planarsviz_folder` (its
#'   `results/planarsviz` subfolder).
#' @export
plot_arbitrary_layers_test <- function(bundle, groups = NULL, view = c("grid", "standalone")) {
  validate_planars_bundle(bundle)
  view <- match.arg(view)
  summary_df <- read_planars_arbitrary_layers(bundle)
  tally <- read_planars_arbitrary_layers_null(bundle)

  neutral <- summary_df$colour[summary_df$group == "all"]
  if (!length(neutral)) neutral <- "#0072B2"

  picked <- planarsviz_null_select(summary_df, tally, groups, view, "arbitrary-layers test")
  planarsviz_null_panels(
    picked$summary_df, picked$tally, picked$groups, view,
    x_lab = "Number of maximal laminar families (that many spans, arbitrary sizes and positions)",
    neutral = neutral[[1]]
  )
}
