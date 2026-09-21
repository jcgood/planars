# Exemplary trees and slides (chart 10 in docs/PLAN_planarsviz_library.md).
#
# Copied, at commit 43a308f, from nyan1308_exemplary_trees.r, the R that
# laminar_analysis.generate_r_exemplary_trees_script() used to write. Both
# are gone from the working tree: that generator was removed in cutover step
# C3 and the script it wrote is archived in OlderFiles/planarsviz_superseded/
# results/. The three blocks it repeats per exemplar -- print tree, evidence
# panel, slide tree -- became functions.
# Changes since the copy:
#   - literals replaced with bundle data: the Newick string (families.tsv),
#     which families and in what order (selections.tsv `exemplary`, chosen
#     in Python by select_representative_families() + the sparsest family),
#     position labels, the test list (the member spans' `labels` in
#     spans.tsv, synthetic root excluded), root and position count;
#   - the evidence panel no longer source()s domain_charts-cgpt.r (which
#     also re-saved every pooled PDF as a side effect); it uses the same
#     df.plot()/constituency.plot() copied into R/pooled.R, filtering the
#     already-numbered all-tests data exactly as before, so layer numbers
#     stay global (section 5);
#   - canvas sizes computed with the generator's formulas: evidence height
#     max(7, tests x 0.7) cm rounded to 2 places, print page 51 + 25 cm wide,
#     slide tree 13.333 x 7.5 in;
#   - library(), source() and ggsave() removed.

# One family's tree, drawn solid with a boxed "N\nName" label at every tip.
#
# Hoisted out of planarsviz_exemplary_tree() on 2026-09-21, when the
# individual forest trees were absorbed into the package (R/forest_trees.R).
# Both draw the same tree; they differ only in where the Newick string comes
# from -- a family_id in the pooled analysis, a tree_number in a forest -- so
# the drawing itself lives here once instead of in two copies. The two
# branches below are the code as it stood before that move, unchanged, since
# the absorbed charts have to match frozen reference images pixel for pixel.
planarsviz_labelled_tree <- function(newick, posLabel, slide = FALSE) {
  planarsviz_require_trees()
  ex_tree1 <- ape::read.tree(text = newick)
  if (!isTRUE(slide)) {
    ex_tp1 <- ggtree::ggtree(ex_tree1, layout="slanted", ladderize=FALSE) +
      ggtree::layout_dendrogram() +
      ggtree::geom_tiplab(geom="label", size=5, angle=0,
        offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
        aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
      theme(panel.background=element_blank(),
        plot.background=element_blank(), legend.position="none",
        plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
  } else {
    ex_tp1 <- ggtree::ggtree(ex_tree1, layout="slanted", ladderize=FALSE) +
      ggtree::layout_dendrogram() +
      ggtree::geom_tiplab(geom="label", size=4.6, angle=0,
        offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
        label.padding=unit(0.12, "lines"),
        aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
      theme(panel.background=element_blank(),
        plot.background=element_blank(), legend.position="none",
        plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
  }
  ex_tp1
}

#' Tree panel for an exemplary family
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param family_id The family to draw.
#' @param slide `FALSE` for the print page's tree (label size 5), `TRUE` for
#'   the 16:9 slide tree (label size 4.6, tighter label padding).
#' @return A ggtree plot.
#' @export
planarsviz_exemplary_tree <- function(bundle, family_id, slide = FALSE) {
  posLabel <- as.list(planarsviz_position_labels(bundle$position_labels))
  newick <- bundle$families$newick[bundle$families$family_id == family_id]
  if (length(newick) != 1L) stop("No family `", family_id, "` with a Newick string in this bundle.", call. = FALSE)
  planarsviz_labelled_tree(newick, posLabel, slide = slide)
}

#' Evidence panel for a family: the tests that produced its spans
#'
#' A pooled plot of just those tests, keeping the layer numbers they have in
#' the all-tests pooled plot.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param family_id The family.
#' @return A ggplot object with attribute `planarsviz_n_tests`.
#' @export
planarsviz_family_evidence <- function(bundle, family_id) {
  membership <- bundle$family_membership
  s <- bundle$spans[match(membership$span_id[membership$family_id == family_id], bundle$spans$span_id), , drop = FALSE]
  if ("synthetic" %in% names(s)) s <- s[!as.logical(s$synthetic), , drop = FALSE]
  test_labels <- sort(unique(unlist(strsplit(s$labels, "|", fixed = TRUE))))

  setup <- planarsviz_pooled_setup(bundle)
  tests_plot <- df.plot(setup$tests, setup$type_levels)
  ex_plot1_data <- filter(tests_plot, Test_Labels %in% test_labels)
  ex_plot1 <- constituency.plot(ex_plot1_data, setup$b, setup$o, setup$group.colors, setup$legend_breaks)
  attr(ex_plot1, "planarsviz_n_tests") <- length(test_labels)
  ex_plot1
}

#' Exemplary tree charts
#'
#' One chart per selected family, in three views: the print page (tree
#' beside the pooled plot of the tests behind it), and a pair of 16:9 slides
#' (tree alone, evidence alone). Reproduces `nyan1308_exemplary_trees_<n>.pdf`,
#' `_slide_<n>_tree.pdf` and `_slide_<n>_evidence.pdf`.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param rank Which selected family (1 = first).
#' @param view `"page"`, `"slide_tree"` or `"slide_evidence"`.
#' @param selection A selection from `selections.tsv`.
#' @return A plot with attributes `planarsviz_size`, `planarsviz_units` and
#'   `planarsviz_folder` (its `results/planarsviz` subfolder); the page also
#'   has `planarsviz_parts` (tree, evidence).
#' @export
plot_exemplary_tree <- function(bundle, rank = 1L, view = c("page", "slide_tree", "slide_evidence"),
                                selection = "exemplary") {
  validate_planars_bundle(bundle)
  view <- match.arg(view)
  selections <- read_planars_selections(bundle)
  rows <- selections[selections$selection == selection, , drop = FALSE]
  family_id <- rows$family_id[rows$rank == as.integer(rank)]
  if (length(family_id) != 1L) {
    stop("No rank ", rank, " in selection `", selection, "` (it has ", nrow(rows), ").", call. = FALSE)
  }

  if (view == "slide_tree") {
    p <- planarsviz_exemplary_tree(bundle, family_id, slide = TRUE)
    attr(p, "planarsviz_size") <- c(width = 13.333, height = 7.5)
    attr(p, "planarsviz_units") <- "in"
    attr(p, "planarsviz_folder") <- "laminar-families"
    return(p)
  }
  ex_plot1 <- planarsviz_family_evidence(bundle, family_id)
  tree_width_cm <- 51.0
  pooled_width_cm <- 25.0
  pooled_height_cm <- round(max(7.0, attr(ex_plot1, "planarsviz_n_tests") * 0.7), 2)
  if (view == "slide_evidence") {
    attr(ex_plot1, "planarsviz_size") <- c(width = pooled_width_cm, height = pooled_height_cm)
    attr(ex_plot1, "planarsviz_units") <- "cm"
    attr(ex_plot1, "planarsviz_folder") <- "laminar-families"
    return(ex_plot1)
  }
  ex_tp1 <- planarsviz_exemplary_tree(bundle, family_id)
  ex_page1 <- (ex_tp1 | ex_plot1) +
    plot_layout(widths=c(tree_width_cm, pooled_width_cm))
  attr(ex_page1, "planarsviz_size") <- c(width = round(tree_width_cm + pooled_width_cm, 1), height = pooled_height_cm)
  attr(ex_page1, "planarsviz_units") <- "cm"
  attr(ex_page1, "planarsviz_folder") <- "laminar-families"
  attr(ex_page1, "planarsviz_parts") <- list(tree = ex_tp1, evidence = ex_plot1)
  ex_page1
}
