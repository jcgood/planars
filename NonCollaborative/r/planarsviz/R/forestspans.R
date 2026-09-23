# ForestSpans plot (chart 11 in docs/PLAN_planarsviz_library.md).
#
# Copied, at commit 43a308f, from nyan1308_forestspans_plot.r, the R that
# scripts/make_forestspans_table.py's make_r_plot_script() used to write.
# Both are gone from the working tree: that generator was removed in cutover
# step C3 and the script it wrote is archived in OlderFiles/planarsviz_superseded/results/.
# The no-tonosegmental file is the
# same code over a fresh analysis without tonosegmental, so it is the
# `subset` option here, not a second function. Changes since the copy:
#   - literals replaced with bundle data: the span table (spans.tsv of the
#     full analysis or of a subsets.json analysis: edges, family counts,
#     blend_colour computed in Python), tree count (families.tsv), root and
#     position count (metadata.json), legend colours and order
#     (domain_types.tsv);
#   - computed here with the generator's rules instead of pasted in: Layer =
#     size rank inverted (sort by size, then left edge; largest span = 1),
#     rows by family count descending then Layer; synthetic root dropped;
#   - library loading (pacman) and ggsave() removed; the dotted root line is
#     skipped when the bundle has no root position.

#' ForestSpans plot
#'
#' One row per span, ordered by how many maximal families contain it, drawn
#' like a pooled plot (boxed layer number at both edges) in a colour blended
#' from its domain types, with the family count in a column at the right.
#' Reproduces `nyan1308_forestspans_plot.pdf`; with `subset = "no_tono"`,
#' `nyan1308_forestspans_plot_no_tono.pdf`.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param subset `NULL` for the full analysis, or a `subset_id` from
#'   `subsets.json` (a fresh analysis of part of the data, e.g. `"no_tono"`);
#'   its layer numbers and counts are its own, not the full chart's.
#' @param legend_position `"inside"` puts the colour key in the lower-left
#'   corner of the panel, in a bordered white box; `"right"` puts it beside
#'   the panel, as the original script did. `"auto"` (default) chooses
#'   `"inside"` when that corner is empty -- no span in the bottom quarter of
#'   rows starts in the leftmost fifth of the axis, as in nyan1308 -- and
#'   `"right"` otherwise, so the key never covers a span.
#' @param legend_inside Position of the inset legend's lower-left corner, as
#'   a share of the panel.
#' @param count_header_size Text sizes (ggplot size units) of the count
#'   column's header: `c(trees, n)` for the "Trees" line and the "(n = N)"
#'   line beneath it. `NULL` draws the original single label (both lines at
#'   size 4).
#' @return A ggplot object with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"cm"`) and `planarsviz_folder` (its
#'   `results/planarsviz` subfolder).
#' @export
plot_forestspans <- function(bundle, subset = NULL,
                             legend_position = c("auto", "inside", "right"),
                             legend_inside = c(0.012, 0.02),
                             count_header_size = c(6, 4.5)) {
  legend_position <- match.arg(legend_position)
  validate_planars_bundle(bundle)
  analysis <- if (is.null(subset)) bundle else read_planars_subset(bundle, subset)
  spans <- analysis$spans
  if ("synthetic" %in% names(spans)) spans <- spans[!as.logical(spans$synthetic), , drop = FALSE]
  if (!"blend_colour" %in% names(spans)) stop("spans.tsv has no blend_colour; re-export the bundle.", call. = FALSE)
  n_families <- nrow(analysis$families)

  # Replicate make_forestspans_table.py's Layer and row order.
  n <- nrow(spans)
  layer <- integer(n)
  layer[order(spans$size, spans$left)] <- n + 1L - seq_len(n)
  row_order <- order(-spans$family_frequency, layer)

  forest_spans <- data.frame(
    Layer = as.numeric(layer[row_order]),
    Left = as.numeric(spans$left[row_order]),
    Right = as.numeric(spans$right[row_order]),
    Count = as.numeric(spans$family_frequency[row_order]),
    Color = spans$blend_colour[row_order],
    stringsAsFactors = FALSE
  ) %>%
    mutate(Layer = factor(Layer, levels = rev(unique(Layer))))

  long <- forest_spans %>%
    pivot_longer(c(Left, Right), names_to = "Edge_Type", values_to = "Edge")

  # Pure domain-type colors, for the reference legend only (see docstring) --
  # not the per-span composite colors, which live in forest_spans$Color above.
  style <- planarsviz_domain_types(bundle)
  style <- style[order(style$sort_order), , drop = FALSE]
  legend_colors <- data.frame(
    Domain_Type = style$domain_type, Color = style$colour,
    stringsAsFactors = FALSE
  )

  o <- bundle$metadata$root_position
  if (!is.null(o)) o <- as.numeric(o)
  b <- as.numeric(bundle$metadata$n_positions)
  count_x <- b + 1 # right edge of the (now right-justified) tree-count
  # column -- just a touch past the axis's own right end
  margin_unit <- 1 # one position-to-position gap -- the actual panel margins
  # (scale_x_continuous's expand below) are set to this same
  # unit on the left, so the blank space before position 1
  # reads as "one more position-width," not a guessed number.

  p <- ggplot(long, aes(x = Edge, y = Layer)) +
    {
      if (!is.null(o)) geom_vline(xintercept = o, linetype = "dotted")
    } +
    # show.legend = FALSE on both: without it, ggplot2 folds these two layers'
    # own key-glyph drawing functions (a colored line segment; a boxed "a", the
    # generic placeholder geom_label always draws in a legend) into the
    # invisible geom_point layer's "colour" legend below -- even though these
    # two use I(Color), not the real scale -- producing a garbled box-inside-a-
    # box glyph instead of a clean colored circle. Confirmed the actual cause
    # (not a font/rasterizer bug, an earlier guess) by rendering and zooming
    # into the legend after this change.
    geom_line(aes(color = I(Color)), linewidth = 2, show.legend = FALSE) +
    # Boxed layer number at both edges, matching constituency.plot().
    geom_label(
      aes(label = Layer, color = I(Color)),
      size = 3, label.padding = unit(0.2, "lines"), fill = "white", show.legend = FALSE
    ) +
    # Tree count: single fixed-x column, plain (unboxed) text, right-justified
    # (hjust = 1, count_x is the column's RIGHT edge) so digits line up on the
    # ones place rather than the ragged look of left-justified single- vs.
    # double-digit numbers.
    geom_text(
      data = forest_spans,
      aes(x = count_x, label = Count),
      hjust = 1, size = 6, color = "black", inherit.aes = TRUE
    ) +
    # Column header for the count, right-justified to sit above the column the
    # same way the numbers do. By default "Trees" is set larger than the
    # "(n = N)" line beneath it; count_header_size = NULL draws the original
    # single two-line label.
    {
      if (is.null(count_header_size)) {
        annotate(
          "text",
          x = count_x, y = Inf, vjust = -0.3, hjust = 1,
          label = paste0("Trees\n(n = ", n_families, ")"), fontface = "bold", size = 4
        )
      } else {
        trees_size <- count_header_size[[1]]
        n_size <- count_header_size[[2]]
        list(
          annotate(
            "text",
            x = count_x, y = Inf, vjust = -0.3, hjust = 1,
            label = paste0("(n = ", n_families, ")"), fontface = "bold", size = n_size
          ),
          # vjust is measured in this label's own height, so lift "Trees" by
          # the "(n = N)" line's height expressed in "Trees" heights.
          annotate(
            "text",
            x = count_x, y = Inf, vjust = -0.3 - 1.25 * n_size / trees_size, hjust = 1,
            label = "Trees", fontface = "bold", size = trees_size
          )
        )
      }
    } +
    # Invisible reference layer: exists only to put a real, correctly-labeled
    # legend on the plot for the pure domain-type colors (see docstring).
    # fill (not color) mapped, so the legend key renders as a solid filled
    # square, matching the filled-square swatch style used elsewhere in this
    # project rather than an outline-only square.
    geom_point(
      data = legend_colors,
      aes(x = if (is.null(o)) 1 else o, y = levels(forest_spans$Layer)[1], fill = Domain_Type),
      shape = 22, color = NA, alpha = 0, size = 3, inherit.aes = FALSE
    ) +
    scale_fill_manual(
      name = "Domain type\n(spans with multiple types\ngiven blended colors)",
      values = stats::setNames(legend_colors$Color, legend_colors$Domain_Type),
      breaks = style$domain_type[order(style$legend_order)]
    ) +
    guides(fill = guide_legend(override.aes = list(alpha = 1, size = 4, shape = 22))) +
    xlab("Positions on the verbal planar structure") +
    # No manual limits -- the panel's x-range is left to derive from the actual
    # data (1..b for the spans, count_x for the tree-count text), then margined
    # by a flat, principled rule: margin_unit on each side, i.e. exactly one
    # position-to-position gap.
    scale_x_continuous(
      breaks = seq(1, b, 1),
      expand = expansion(add = c(margin_unit, margin_unit))
    ) +
    coord_cartesian(clip = "off") +
    theme_bw() +
    theme(
      axis.title.y = element_blank(),
      axis.text.y = element_blank(),
      axis.ticks.y = element_blank(),
      text = element_text(size = 15),
      panel.grid.minor = element_blank(),
      plot.margin = margin(t = 60, r = 10, b = 10, l = 10),
      legend.position = "right",
      legend.key = element_blank(),
      legend.title = element_text(size = 10),
      legend.text = element_text(size = 10)
    )

  if (legend_position == "auto") {
    # The rows at the bottom are the spans in the fewest families. In nyan1308
    # they all start well right of position 1, leaving the corner empty; in a
    # CCDB structure one can start at position 1 and run under the key. The
    # x range is 0 to count_x + 1 (the one-position margins either side).
    bottom_rows <- tail(forest_spans, ceiling(nrow(forest_spans) / 4))
    corner_clear <- all(bottom_rows$Left > 0.2 * (count_x + margin_unit))
    legend_position <- if (corner_clear) "inside" else "right"
  }
  if (legend_position == "inside") {
    p <- p + theme(
      legend.position = "inside",
      legend.position.inside = legend_inside,
      legend.justification = c(0, 0),
      legend.background = element_rect(fill = "white", colour = "black", linewidth = 0.3),
      legend.margin = margin(6, 8, 6, 8),
      legend.key.height = unit(1.1, "lines")
    )
  }

  attr(p, "planarsviz_size") <- c(width = 34 * planarsviz_position_scale(bundle), height = 24)
  attr(p, "planarsviz_units") <- "cm"
  attr(p, "planarsviz_folder") <- "pooled"
  p
}
