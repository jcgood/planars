# Stacked see-through trees ("ghost forests"): the shared building block for
# charts 6-9 and 12 in docs/PLAN_planarsviz_library.md.
#
# Copied from nyan1308_inton_laminar_forest.r, lines 1-37, at commit 43a308f
# -- the R that laminar_analysis.generate_r_script() used to write. Both are
# gone from the working tree: that generator was removed in cutover step C3
# and the script it wrote is archived in OlderFiles/planarsviz_superseded/
# results/. The only changes since:
#   - the per-tree block (lines 10-25) became planarsviz_ghost_tree(), called
#     once per tree instead of pasted N times with numbered variables. Each
#     call has its own environment, so aes(size = (strengthMap[group])) sees
#     that tree's own thickness values (a single shared variable would give
#     every tree the last tree's values);
#   - literals replaced with bundle data: the Newick string, groupOTU span
#     list and thickness values (data/forests/<id>.tsv), alpha, colour and
#     tree count (data/forests.json), position labels (position_labels.tsv);
#   - the visible label (lines 27-29) is added to the last tree, as before;
#   - library() calls and ggsave() removed; the white page background the
#     generator applied inside ggsave() is applied to the returned plot.

planarsviz_require_trees <- function() {
  for (pkg in c("ape", "ggtree")) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      stop("Package `", pkg, "` is required for tree charts.", call. = FALSE)
    }
  }
}

#' One see-through tree
#'
#' @param newick Newick string (tips are position numbers, internal nodes
#'   `left-right`).
#' @param group_spans Character vector of `"left-right"` spans, in the order
#'   the generator passed them to `groupOTU()`.
#' @param strengths Numeric thickness for each span, same order.
#' @param alphaval Opacity of this tree.
#' @param colour Line colour.
#' @param spacer_lineheight `lineheight` of the invisible tip-label spacer, or
#'   `NULL` to leave it unset. The forest generator (generate_r_script) sets
#'   1; the overlay generator (generate_r_overlay_script) leaves it unset.
#' @return A ggtree plot with an invisible tip-label spacer.
#' @export
planarsviz_ghost_tree <- function(newick, group_spans, strengths, alphaval, colour,
                                  spacer_lineheight = 1) {
  planarsviz_require_trees()
  tree1 <- ape::read.tree(text = newick)
  spans <- lapply(strsplit(group_spans, "-", fixed = TRUE), as.numeric)
  names(spans) <- letters[seq_along(spans)]
  tree1grouped <- ggtree::groupOTU(tree1, spans)
  strengthMap1 <- c(0.5, strengths)
  spacer_args <- list(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA)
  if (!is.null(spacer_lineheight)) spacer_args$lineheight <- spacer_lineheight
  treeplot1 <- ggtree::ggtree(tree1grouped,
    aes(size=(strengthMap1[group])),
    layout="slanted", ladderize=FALSE,
    alpha=alphaval, color=colour) +
    ggtree::layout_dendrogram() +
    do.call(ggtree::geom_tiplab, spacer_args) +
    theme(panel.background=element_blank(),
      plot.background=element_blank(),
      legend.position="none",
      plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
    scale_size_identity()
  treeplot1
}

#' Read one per-class forest from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param forest_id A forest id from `data/forests.json` (e.g. `"inton"`).
#' @return A list with `meta` (one row of forests.json) and `trees` (a data
#'   frame with `newick`, `group_spans`, `strengths`).
#' @export
read_planars_forest <- function(bundle, forest_id) {
  index_path <- file.path(bundle$bundle_dir, "data", "forests.json")
  if (!file.exists(index_path)) stop("Bundle has no forests.json; re-export it.", call. = FALSE)
  index <- jsonlite::read_json(index_path, simplifyVector = FALSE)
  meta <- Filter(function(f) identical(f$forest_id, forest_id), index)
  if (!length(meta)) {
    ids <- vapply(index, function(f) f$forest_id, character(1))
    stop("No forest `", forest_id, "` in this bundle. Available: ", paste(ids, collapse = ", "), call. = FALSE)
  }
  trees <- utils::read.delim(file.path(bundle$bundle_dir, "data", "forests", paste0(forest_id, ".tsv")),
                             stringsAsFactors = FALSE, colClasses = "character")
  list(meta = meta[[1]], trees = trees)
}

#' Per-class laminar forest
#'
#' All maximal families of one domain-type class (or bundle of classes), each
#' drawn as a faint tree and stacked, so structure shared by many families
#' reads darker. Reproduces `nyan1308_<id>_laminar_forest.pdf`.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param forest_id A forest id from `data/forests.json`.
#' @return A patchwork plot with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`), and `planarsviz_parts` (the tree plots).
#' @export
plot_laminar_forest <- function(bundle, forest_id) {
  validate_planars_bundle(bundle)
  planarsviz_require_trees()
  forest_data <- read_planars_forest(bundle, forest_id)
  meta <- forest_data$meta
  trees <- forest_data$trees
  alphaval <- meta$alpha / 2
  labels <- planarsviz_position_labels(bundle$position_labels)
  posLabel <- as.list(labels)

  plots <- lapply(seq_len(nrow(trees)), function(i) {
    planarsviz_ghost_tree(
      newick = trees$newick[[i]],
      group_spans = strsplit(trees$group_spans[[i]], ";", fixed = TRUE)[[1]],
      strengths = as.numeric(strsplit(trees$strengths[[i]], ";", fixed = TRUE)[[1]]),
      alphaval = alphaval,
      colour = meta$colour
    )
  })
  n <- length(plots)
  plots[[n]] <- plots[[n]] + ggtree::geom_tiplab(geom="label", size=6, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1)

  treelayout <- do.call(c, rep(list(patchwork::area(t=1, l=1, b=5, r=1)), n))
  forest <- Reduce(`+`, plots) + plot_layout(design=treelayout)
  forest <- forest & theme(plot.background=element_rect(fill='white', color=NA))

  attr(forest, "planarsviz_size") <- c(width = 20, height = 14)
  attr(forest, "planarsviz_units") <- "in"
  attr(forest, "planarsviz_parts") <- plots
  forest
}
