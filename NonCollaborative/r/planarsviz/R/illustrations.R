# The `illustrations` bundle: pure tree-shape combinatorics with no language
# behind it (question 1, docs/PLANARSVIZ_LIBRARY_PROGRESS.md, phase E,
# 2026-09-22). Three charts:
#   - plot_tree_shapes(ref, n): one row of every (or a sample of) the n-ary
#     tree shapes with n leaves. Copied from
#     scripts/exploratory/render_supercatalan_rows.r's per-row drawing
#     (that script + generate_supercatalan_rows.py wrote the same PDFs by
#     hand; both are archived in OlderFiles/planarsviz_superseded/ once this
#     port matched them at 0.0000%). Every constant below (INCHES_PER_LEAF,
#     WIDTH_PAD_IN, TREE_HEIGHT_IN, TREE_GAP_IN, PANEL_EXPAND) and their
#     reasoning are that script's own, unchanged -- see its header comment
#     for why a fixed tree height and a leaf-count-plus-pad width, not just
#     leaf count, are what they are.
#   - plot_tree_count_growth(ref, bundle = NULL): Catalan and little
#     Schröder counts (tree_count_growth.tsv) against leaf count, on a log
#     scale. A new chart -- the old scripts only ever showed this as
#     tree_counting_equations.tex's static table. `bundle`, when given,
#     draws a dotted reference line at that language's own
#     n_maximal_families, which is the whole point named in question 1: "the
#     growth of the tree space against the 69 families."
#   - plot_random_tree_overlay(ref, bundle): the same "stack N ghost trees on
#     one patchwork cell" mechanism plot_laminar_overlay() uses, but with no
#     span/strength colouring -- every edge is the same fixed alpha, since
#     there is no target span to highlight in a purely combinatorial sample.
#     Ported from scripts/analysis/random_tree_overlay.py's
#     make_r_script(), which used to write this same drawing as 2200 lines
#     of generated R (one hand-templated block per sampled tree) rather than
#     a function operating on data -- the last generated-R-file holdout this
#     package hadn't absorbed. `bundle` supplies the real position labels
#     (its positions are real; only the tree shapes are illustrative
#     samples, not this language's actual data).

planarsviz_require_cowplot <- function() {
  if (!requireNamespace("cowplot", quietly = TRUE)) {
    stop("Package `cowplot` is required for plot_tree_shapes().", call. = FALSE)
  }
}

#' Read the illustrations data bundle
#'
#' @param bundle_dir The `illustrations` bundle directory (containing
#'   `data/`), or the `data/` directory itself.
#' @return A list with `metadata`, `tree_shapes`, `tree_count_growth`,
#'   `random_trees`, and `bundle_dir`.
#' @export
read_planars_illustrations <- function(bundle_dir) {
  bundle_dir <- normalizePath(bundle_dir, mustWork = TRUE)
  data_dir <- if (basename(bundle_dir) == "data") bundle_dir else file.path(bundle_dir, "data")
  required <- c("metadata.json", "tree_shapes.tsv", "tree_count_growth.tsv", "random_trees.tsv")
  missing <- required[!file.exists(file.path(data_dir, required))]
  if (length(missing) > 0L) {
    stop("Illustrations bundle is missing: ", paste(missing, collapse = ", "), call. = FALSE)
  }
  ref <- list(
    metadata = jsonlite::read_json(file.path(data_dir, "metadata.json"), simplifyVector = TRUE),
    tree_shapes = utils::read.delim(file.path(data_dir, "tree_shapes.tsv"), stringsAsFactors = FALSE),
    tree_count_growth = utils::read.delim(file.path(data_dir, "tree_count_growth.tsv"), stringsAsFactors = FALSE),
    random_trees = utils::read.delim(file.path(data_dir, "random_trees.tsv"), stringsAsFactors = FALSE),
    bundle_dir = dirname(data_dir)
  )
  class(ref) <- "planarsviz_illustrations"
  ref
}

#' One row of tree shapes
#'
#' @param ref An illustrations bundle from [read_planars_illustrations()].
#' @param n Leaf count -- one of `tree_shapes.tsv`'s `n` values.
#' @return A plot with attributes `planarsviz_size` (varies with `n` and the
#'   number of shapes in that row), `planarsviz_units` (`"in"`) and
#'   `planarsviz_folder` (`""` -- this bundle has one topic, itself, so there
#'   is no second-level folder to name).
#' @export
plot_tree_shapes <- function(ref, n) {
  planarsviz_require_trees()
  planarsviz_require_cowplot()
  trees <- ref$tree_shapes[ref$tree_shapes$n == n, , drop = FALSE]
  trees <- trees[order(trees$shape_number), , drop = FALSE]
  if (!nrow(trees)) stop("No tree shapes for n = ", n, " in this bundle.", call. = FALSE)

  inches_per_leaf <- 0.22
  width_pad_in <- 0.35
  tree_height_in <- 0.9
  tree_gap_in <- 0.3
  panel_expand <- 0.04

  n_trees <- nrow(trees)
  panel_w_in <- n * inches_per_leaf + width_pad_in
  total_width_in <- panel_w_in * n_trees + (n_trees - 1) * tree_gap_in

  make_one <- function(newick) {
    tr <- ape::read.tree(text = newick)
    ggtree::ggtree(tr, layout = "slanted", ladderize = FALSE) +
      ggtree::layout_dendrogram() +
      scale_x_reverse(expand = expansion(mult = panel_expand)) +
      scale_y_continuous(expand = expansion(mult = panel_expand)) +
      theme_void() +
      theme(plot.margin = margin(0, 0, 0, 0))
  }

  p <- cowplot::ggdraw()
  x_cursor <- 0
  for (i in seq_len(n_trees)) {
    p <- p + cowplot::draw_plot(make_one(trees$newick[[i]]),
      x = x_cursor / total_width_in, y = 0,
      width = panel_w_in / total_width_in, height = 1
    )
    x_cursor <- x_cursor + panel_w_in + tree_gap_in
  }
  attr(p, "planarsviz_size") <- c(width = total_width_in, height = tree_height_in)
  attr(p, "planarsviz_units") <- "in"
  attr(p, "planarsviz_folder") <- ""
  p
}

#' Tree-shape count growth
#'
#' Catalan numbers (binary trees) and little Schröder numbers / OEIS A001003
#' (n-ary trees) against leaf count, on a log scale -- how fast the space of
#' possible tree shapes grows.
#'
#' @param ref An illustrations bundle from [read_planars_illustrations()].
#' @param bundle A language bundle from [read_planars_bundle()], or `NULL`
#'   (default) to omit the reference line. When given, draws a dotted line
#'   at that language's own `n_maximal_families`, since the point of this
#'   chart is to show the observed family count against how large the tree
#'   space it was drawn from actually is.
#' @return A plot with attributes `planarsviz_size`, `planarsviz_units`
#'   (`"in"`) and `planarsviz_folder` (`""`).
#' @export
plot_tree_count_growth <- function(ref, bundle = NULL) {
  d <- ref$tree_count_growth
  long <- rbind(
    data.frame(n = d$n, count = d$catalan, series = "Catalan (binary branching)"),
    data.frame(n = d$n, count = d$little_schroder, series = "Little Schröder (n-ary branching)")
  )
  p <- ggplot(long, aes(x = n, y = count, colour = series)) +
    geom_line() +
    geom_point(size = 1.5) +
    scale_y_log10(labels = scales::label_comma()) +
    scale_x_continuous(breaks = d$n) +
    scale_colour_manual(values = c(
      "Catalan (binary branching)" = "#0072B2",
      "Little Schröder (n-ary branching)" = "#D55E00"
    )) +
    labs(
      x = "Number of leaves", y = "Number of distinct tree shapes (log scale)",
      colour = NULL
    ) +
    theme_bw() +
    theme(
      legend.position = "inside", legend.position.inside = c(0.02, 0.98),
      legend.justification = c(0, 1)
    )
  if (!is.null(bundle)) {
    n_families <- as.integer(bundle$metadata$n_maximal_families)
    language <- bundle$metadata$language_name
    ref_label <- if (is.null(language) || !nzchar(language)) {
      sprintf("%d observed families", n_families)
    } else {
      sprintf("%d observed families (%s)", n_families, language)
    }
    p <- p +
      geom_hline(yintercept = n_families, linetype = "dotted") +
      annotate("text",
        x = min(d$n), y = n_families, label = ref_label,
        hjust = 0, vjust = -0.6, size = 3.2
      )
  }
  attr(p, "planarsviz_size") <- c(width = 7, height = 5)
  attr(p, "planarsviz_units") <- "in"
  attr(p, "planarsviz_folder") <- ""
  p
}

#' Random-sample tree overlay
#'
#' Many uniformly-random n-ary tree shapes over a language's real positions,
#' stacked as faint ("ghost") trees onto one panel -- illustrating how vast
#' the tree space is next to the handful of laminar families actually
#' observed. Every edge is drawn at the same fixed opacity: unlike
#' [plot_laminar_overlay()], there is no target span to highlight in a
#' purely combinatorial sample.
#'
#' @param ref An illustrations bundle from [read_planars_illustrations()],
#'   whose `random_trees.tsv` leaf count must equal `bundle`'s
#'   `n_positions`.
#' @param bundle A language bundle from [read_planars_bundle()], for its
#'   real position labels.
#' @param alpha Per-tree edge opacity. Default `0.02`, tuned (like
#'   [plot_laminar_overlay()]'s own defaults) so edges shared by many of the
#'   sampled trees read as darker without any one tree's edges standing out.
#' @return A patchwork plot with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`) and `planarsviz_folder` (`""`).
#' @export
plot_random_tree_overlay <- function(ref, bundle, alpha = 0.02) {
  planarsviz_require_trees()
  n_leaves <- as.integer(ref$metadata$random_trees$n_leaves)
  n_positions <- as.integer(bundle$metadata$n_positions)
  if (n_leaves != n_positions) {
    stop(
      "This illustrations bundle's random trees have ", n_leaves, " leaves, but ",
      "`bundle` has ", n_positions, " positions -- they must match.",
      call. = FALSE
    )
  }
  trees <- ref$random_trees[order(ref$random_trees$tree_number), , drop = FALSE]
  pos_label <- as.list(planarsviz_position_labels(bundle$position_labels))
  n <- nrow(trees)

  make_one <- function(newick) {
    tr <- ape::read.tree(text = newick)
    p <- ggtree::ggtree(tr, layout = "slanted", ladderize = FALSE) +
      ggtree::layout_dendrogram() +
      theme(
        panel.background = element_blank(), plot.background = element_blank(),
        legend.position = "none"
      )
    p$layers[[1]]$aes_params$alpha <- alpha
    p$layers[[1]]$aes_params$colour <- "black"
    p
  }

  plots <- lapply(trees$newick, make_one)
  plots[[n]] <- plots[[n]] +
    ggtree::geom_tiplab(
      geom = "label", size = 5, angle = 0,
      offset = -1, hjust = 0.5, vjust = 1.25, alpha = 1, label.size = 0,
      aes(label = paste(label, pos_label[label], sep = "\n")), lineheight = 1
    ) +
    theme(plot.margin = margin(t = 5, r = 5, b = 25, l = 5, unit = "pt"))

  design <- do.call(c, rep(list(patchwork::area(t = 1, l = 1, b = 1, r = 1)), n))
  p <- Reduce(`+`, plots) + plot_layout(design = design)
  attr(p, "planarsviz_size") <- c(width = 16, height = 10)
  attr(p, "planarsviz_units") <- "in"
  attr(p, "planarsviz_folder") <- ""
  p
}
