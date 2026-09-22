# Every individual maximal-family tree in a forest, one chart each.
#
# Absorbed into the package on 2026-09-21 from
# scripts/analysis/bundle_forest_trees.r, which wrote its 22 PDFs straight
# into results/ with no chart name and no manifest row -- the same defect the
# fragmentation chart had before chart 19's port. That script is archived in
# OlderFiles/planarsviz_superseded/scripts/ and the charts it drew are frozen
# in results/planarsviz/reference/laminar-families/, which is what the
# renderer check compares this function's output against.
#
# These are not the ghost forests (R/ghost_trees.R), which stack every tree of
# a forest into one see-through image, and not the exemplary trees
# (R/exemplary.R), which draw a curated seven of the pooled analysis's 69
# families. This draws every family of one named forest, separately.
#
# Only tree_number and newick are read. The group_spans/strengths columns in
# the same table carry the per-span thickness the stacked overlay encodes; a
# single clean tree does not use them, the same choice planarsviz_exemplary_
# tree() makes for an individual exemplar.

#' One maximal-family tree from a forest
#'
#' The tree of a single maximal laminar family belonging to one forest, drawn
#' solid with a boxed position label at each tip -- the same drawing the
#' exemplary charts use, keyed by forest and tree number rather than by
#' family id. Reproduces `nyan1308_<forest_id>_tree_<nn>.pdf`.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param forest_id A forest id from `data/forests.json` (e.g. `"syntaxlike"`).
#' @param tree_number Which tree of that forest, as numbered in
#'   `data/forests/<forest_id>.tsv` (1 = first).
#' @return A ggtree plot with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`) and `planarsviz_folder` (its
#'   `results/planarsviz` subfolder).
#' @export
plot_forest_tree <- function(bundle, forest_id, tree_number) {
  validate_planars_bundle(bundle)
  trees <- read_planars_forest(bundle, forest_id)$trees
  row <- which(as.integer(trees$tree_number) == as.integer(tree_number))
  if (length(row) != 1L) {
    stop("Forest `", forest_id, "` has no tree ", tree_number,
      " (it has ", nrow(trees), ").",
      call. = FALSE
    )
  }
  pos_label <- as.list(planarsviz_position_labels(bundle$position_labels))
  p <- planarsviz_labelled_tree(trees$newick[[row]], pos_label)
  attr(p, "planarsviz_size") <- c(width = 12, height = 8)
  attr(p, "planarsviz_units") <- "in"
  attr(p, "planarsviz_folder") <- "laminar-families"
  p
}
