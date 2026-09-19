# Single summary trees: the frequency tree and the four trees (charts 14 and
# 13 in docs/PLAN_planarsviz_library.md).
#
# Copied, at commit 43a308f, from results/laminar_freqtree.r and
# results/laminar_four_trees.r (generated scripts whose generator was never
# committed; see the previous commit for the unchanged copies). The per-tree
# block both scripts repeat became planarsviz_summary_tree(). Changes since
# the copy:
#   - literals replaced with bundle data: the Newick string (families.tsv
#     `newick`), which family each tree shows (selections.tsv, rule recovered
#     in section 4.1), the groups and their defining spans
#     (conflict_groups.tsv), position labels, and the family counts in the
#     titles and legend names;
#   - the node table (freq, freq_scaled, edge_size) is counted from
#     family_membership.tsv over the tree's comparison set -- all families, or
#     the group's families -- with the scripts' rounding (6 places) and
#     edge_size = 4 x share, instead of being pasted in;
#   - library() and ggsave() removed; unused `n_families` dropped.

#' Read representative-family selections from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A data frame with `selection`, `rank`, `family_id`.
#' @export
read_planars_selections <- function(bundle) {
  path <- file.path(bundle$bundle_dir, "data", "selections.tsv")
  if (!file.exists(path)) stop("Bundle has no selections.tsv; re-export it.", call. = FALSE)
  out <- utils::read.delim(path, stringsAsFactors = FALSE, colClasses = "character")
  out$rank <- as.integer(out$rank)
  out
}

#' Read conflict groups from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A data frame with `group_id`, `defining_span_id` (empty for the
#'   group of all remaining families), `family_id`, `draw_rank` (`NA` = not
#'   drawn under the exporter's cap). Rows keep the exporter's group order.
#' @export
read_planars_conflict_groups <- function(bundle) {
  path <- file.path(bundle$bundle_dir, "data", "conflict_groups.tsv")
  if (!file.exists(path)) stop("Bundle has no conflict_groups.tsv; re-export it.", call. = FALSE)
  out <- utils::read.delim(path, stringsAsFactors = FALSE, colClasses = "character")
  if (!nrow(out)) stop("This bundle defines no conflict groups.", call. = FALSE)
  out$draw_rank <- suppressWarnings(as.integer(out$draw_rank))
  out
}

planarsviz_selected_family <- function(bundle, selection) {
  selections <- read_planars_selections(bundle)
  hit <- selections$family_id[selections$selection == selection & selections$rank == 1L]
  if (!length(hit)) {
    stop("No selection `", selection, "` in this bundle. Available: ",
         paste(unique(selections$selection), collapse = ", "), call. = FALSE)
  }
  hit[[1]]
}

#' One summary tree weighted by family frequency
#'
#' Draws one family's tree; each branch's opacity and thickness show the
#' share of the comparison families that contain that span.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param family_id The family to draw.
#' @param member_ids Family ids the frequencies are counted over.
#' @param title Plot title.
#' @param alpha_name Name of the opacity scale.
#' @param legend Keep the opacity legend (`FALSE` hides it).
#' @param weight What a branch's opacity and thickness show: `"families"` (the
#'   share of `member_ids` containing the span), `"tests"` (the span's
#'   convergence as a share of the drawn tree's best-tested span), or
#'   `"none"` (every branch drawn solid — for illustrating shape alone).
#' @param branch_size Thickness of a fully supported branch; thinner branches
#'   scale down from it. With `weight = "none"` every branch is fully
#'   supported, so this is simply the line width of the whole tree.
#' @return A ggtree plot.
#' @export
planarsviz_summary_tree <- function(bundle, family_id, member_ids, title, alpha_name,
                                    legend = TRUE, weight = c("families", "tests", "none"),
                                    branch_size = 4) {
  planarsviz_require_trees()
  weight <- match.arg(weight)
  `%<+%` <- ggtree::`%<+%`
  posLabel <- as.list(planarsviz_position_labels(bundle$position_labels))
  newick <- bundle$families$newick[bundle$families$family_id == family_id]
  if (length(newick) != 1L) stop("No family `", family_id, "` with a Newick string in this bundle.", call. = FALSE)
  n_members <- length(member_ids)
  membership <- bundle$family_membership
  counts <- table(membership$span_id[membership$family_id %in% member_ids])
  family_spans <- membership$span_id[membership$family_id == family_id]
  tips <- as.character(seq_len(as.integer(bundle$metadata$n_positions)))
  if (weight == "families") {
    span_value <- as.numeric(counts[family_spans])
    n_members <- n_members
  } else if (weight == "tests") {
    span_value <- as.numeric(bundle$spans$convergence[match(family_spans, bundle$spans$span_id)])
    n_members <- max(span_value)
  } else {
    span_value <- rep(1, length(family_spans))
    n_members <- 1
  }
  freq <- c(span_value, rep(n_members, length(tips)))

  freq_tree <- ape::read.tree(text = newick)

  node_freq <- data.frame(
    label      = c(family_spans, tips),
    freq       = freq,
    freq_scaled= round(freq / n_members, 6),
    edge_size  = round(branch_size * freq / n_members, 6)
  )

  p <- ggtree::ggtree(freq_tree, layout='slanted', ladderize=FALSE) %<+%
    node_freq +
    ggtree::layout_dendrogram() +
    aes(alpha=freq_scaled, size=edge_size) +
    scale_size_identity() +
    # With one weight for every branch the scale would otherwise map them all
    # to the middle of its range, drawing a solid tree in grey.
    scale_alpha_continuous(range=c(0.05, 1.0), name=alpha_name,
      limits=if (weight == "none") c(0, 1) else NULL) +
    ggtree::geom_tiplab(geom='label', size=5, angle=0,
      offset=-1, hjust=0.5, alpha=1, label.size=0,
      aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
    theme(panel.background=element_blank(),
      plot.background=element_blank()) +
    ggtitle(title)
  if (!isTRUE(legend)) p <- p + theme(legend.position='none')
  p
}

#' Frequency tree
#'
#' The most consensus-like family (by default), with each branch weighted by
#' the share of all maximal families containing it. Reproduces
#' `nyan1308_freqtree.pdf`.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param selection A selection from `selections.tsv`.
#' @param title Plot title; the default names the number of families.
#' @param weight What branch opacity and thickness show: `"families"`
#'   (default), `"tests"`, or `"none"`. See [planarsviz_summary_tree()].
#' @param branch_size Thickness of a fully supported branch. Defaults to 4,
#'   the weighted charts' heaviest line; with `weight = "none"`, where every
#'   branch would be drawn at that weight, it defaults to 1.5.
#' @return A ggtree plot with attributes `planarsviz_size` and `planarsviz_units`.
#' @export
plot_frequency_tree <- function(bundle, selection = "consensus_all", title = NULL,
                                weight = c("families", "tests", "none"),
                                branch_size = NULL) {
  validate_planars_bundle(bundle)
  weight <- match.arg(weight)
  if (is.null(branch_size)) branch_size <- if (weight == "none") 1.5 else 4
  n <- nrow(bundle$families)
  if (is.null(title)) title <- paste0(n, ' maximal families — edge weight = family count')
  alpha_name <- switch(weight,
    families = paste0('Proportion of ', n, ' families'),
    tests = 'Share of the best-tested span',
    none = NULL)
  p <- planarsviz_summary_tree(
    bundle, planarsviz_selected_family(bundle, selection), bundle$families$family_id,
    title = title, alpha_name = alpha_name, legend = weight != "none", weight = weight,
    branch_size = branch_size)
  attr(p, "planarsviz_size") <- c(width = 16, height = 10)
  attr(p, "planarsviz_units") <- "in"
  p
}

#' Four trees: the most consensus-like family overall and per conflict group
#'
#' One panel for all families and one per conflict group, each showing the
#' group's most consensus-like family weighted by frequency within the group.
#' Reproduces `nyan1308_four_trees.pdf` (for three groups).
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param other_label Title text for the group with no defining span.
#' @return A patchwork plot with attributes `planarsviz_size`,
#'   `planarsviz_units` and `planarsviz_parts` (the panels, all-families first).
#' @export
plot_four_trees <- function(bundle, other_label = "neither") {
  validate_planars_bundle(bundle)
  groups <- read_planars_conflict_groups(bundle)
  n <- nrow(bundle$families)
  p_all <- planarsviz_summary_tree(
    bundle, planarsviz_selected_family(bundle, "consensus_all"), bundle$families$family_id,
    title = paste0('All ', n, ' families (representative)'),
    alpha_name = paste0('Prop. of ', n, ' families'), legend = FALSE)
  panels <- lapply(unique(groups$group_id), function(g) {
    rows <- groups[groups$group_id == g, , drop = FALSE]
    defining <- rows$defining_span_id[[1]]
    what <- if (is.na(defining) || defining == "") other_label else paste0('[', defining, ']')
    planarsviz_summary_tree(
      bundle, planarsviz_selected_family(bundle, paste0("consensus_", g)), rows$family_id,
      title = paste0('Group ', g, ': ', what, ' (', nrow(rows), ' families)'),
      alpha_name = paste0('Prop. of ', nrow(rows), ' families'), legend = FALSE)
  })
  parts <- c(list(p_all), panels)

  # The source script's 2x2 layout, kept exactly for three groups; any other
  # number of groups is laid out two panels per row.
  forest <- if (length(panels) == 3L) {
    (parts[[1]] | parts[[2]]) / (parts[[3]] | parts[[4]]) +
      plot_layout(guides='collect')
  } else {
    patchwork::wrap_plots(parts, ncol = 2) + plot_layout(guides='collect')
  }
  attr(forest, "planarsviz_size") <- c(width = 24, height = 16)
  attr(forest, "planarsviz_units") <- "in"
  attr(forest, "planarsviz_parts") <- parts
  forest
}
