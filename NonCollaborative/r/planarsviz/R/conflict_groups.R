# Conflict groups (chart 12 in docs/PLAN_planarsviz_library.md).
#
# Copied, at commit 43a308f, from results/laminar_conflict_groups.r (a
# generated script whose generator was never committed; see the previous
# commit for the unchanged copy). The per-tree block the script repeats 103
# times became planarsviz_conflict_tree(), and the per-panel block became a
# loop. Changes since the copy:
#   - literals replaced with bundle data: Newick strings (families.tsv),
#     which families each panel draws and in what order (conflict_groups.tsv
#     draw_rank; rule recovered in section 4.1), the groups' defining spans
#     and sizes, the family count in the titles;
#   - computed here with the values the script's numbers follow, instead of
#     pasted in: each panel's opacity 1 - 0.01^(1/trees drawn), rounded to 6
#     places; each branch's thickness sqrt(the span's family count across ALL
#     families), rounded to 4; groupOTU span order by left edge, larger span
#     first on ties;
#   - the final layout stacks the all-families panel over the group panels
#     side by side for any number of groups (the script's three-group
#     expression is the same thing);
#   - library() and ggsave() removed.

#' One conflict-groups tree
#'
#' @param newick Newick string.
#' @param group_spans Character vector of `"left-right"` spans in groupOTU order.
#' @param strengths Thickness for each span, same order.
#' @param alphaval Opacity of this tree.
#' @param colour Line colour.
#' @return A ggtree plot (no tip labels).
#' @export
planarsviz_conflict_tree <- function(newick, group_spans, strengths, alphaval, colour = "black") {
  planarsviz_require_trees()
  all_tree1 <- ape::read.tree(text = newick)
  spans <- lapply(strsplit(group_spans, "-", fixed = TRUE), as.numeric)
  names(spans) <- letters[seq_along(spans)]
  all_tree1_g <- ggtree::groupOTU(all_tree1, spans)
  all_sm1 <- c(0.5, strengths)
  all_tp1 <- ggtree::ggtree(all_tree1_g,
    aes(size=(all_sm1[group])),
    layout='slanted', ladderize=FALSE) +
    ggtree::layout_dendrogram() +
    theme(panel.background=element_blank(),
      plot.background=element_blank(),
      legend.position='none') +
    scale_size_identity()
  all_tp1$layers[[1]]$aes_params$alpha <- alphaval
  all_tp1$layers[[1]]$aes_params$colour <- colour
  all_tp1
}

#' Conflict groups
#'
#' Every maximal family stacked in one large panel, and below it one panel
#' per conflict group (families containing a defining span, and the rest),
#' each group capped at the exporter's `conflict_group_cap` trees.
#' Reproduces `nyan1308_conflict_groups.pdf`.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param other_label Title text for the group with no defining span.
#' @return A patchwork plot with attributes `planarsviz_size`,
#'   `planarsviz_units` and `planarsviz_parts` (one list of trees per panel,
#'   all-families first).
#' @export
plot_conflict_groups <- function(bundle, other_label = "neither") {
  validate_planars_bundle(bundle)
  planarsviz_require_trees()
  groups <- read_planars_conflict_groups(bundle)
  spans <- bundle$spans
  membership <- bundle$family_membership

  tree_for <- function(family_id, alphaval) {
    ids <- membership$span_id[membership$family_id == family_id]
    s <- spans[match(ids, spans$span_id), , drop = FALSE]
    s <- s[order(s$left, -s$size), , drop = FALSE]
    planarsviz_conflict_tree(
      newick = bundle$families$newick[bundle$families$family_id == family_id],
      group_spans = paste(s$left, s$right, sep = "-"),
      strengths = round(sqrt(s$family_frequency), 4),
      alphaval = alphaval)
  }
  make_panel <- function(family_ids, title) {
    alphaval <- round(1 - 0.01 ^ (1 / length(family_ids)), 6)
    trees <- lapply(family_ids, tree_for, alphaval = alphaval)
    panel_design <- do.call(c, rep(list(patchwork::area(t=1, l=1, b=5, r=1)), length(trees)))
    panel <- Reduce(`+`, trees) +
      plot_layout(design=panel_design)
    panel <- panel + plot_annotation(title=title)
    list(panel = panel, trees = trees)
  }

  n <- nrow(bundle$families)
  panel_all <- make_panel(bundle$families$family_id, paste0('All ', n, ' families'))
  group_panels <- lapply(unique(groups$group_id), function(g) {
    rows <- groups[groups$group_id == g, , drop = FALSE]
    drawn <- rows[!is.na(rows$draw_rank), , drop = FALSE]
    drawn <- drawn[order(drawn$draw_rank), , drop = FALSE]
    defining <- rows$defining_span_id[[1]]
    what <- if (is.na(defining) || defining == "") other_label else paste0('[', sub("-", "–", defining, fixed = TRUE), ']')
    make_panel(drawn$family_id, paste0('Group ', g, ': ', what, ' (', nrow(rows), ' families)'))
  })

  forest <- (panel_all$panel / Reduce(`|`, lapply(group_panels, `[[`, "panel"))) +
    plot_layout(heights=c(2, 1))
  attr(forest, "planarsviz_size") <- c(width = 24, height = 20)
  attr(forest, "planarsviz_units") <- "in"
  attr(forest, "planarsviz_parts") <- c(list(panel_all$trees), lapply(group_panels, `[[`, "trees"))
  forest
}
