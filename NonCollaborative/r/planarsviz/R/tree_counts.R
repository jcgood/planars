# Tree-count bar charts (chart 16 in docs/PLAN_planarsviz_library.md).
#
# A cross-language port (plan section 4.3), not a copy: the working charts
# are matplotlib, drawn by scripts/analysis/laminar_tree_counts.py at commit
# 43a308f. The counts come from the bundle (tree_counts.tsv, written by
# calling that script's collect_counts()/collect_bundle_counts()); every
# matplotlib setting that affects appearance is mapped below, with the
# source line it comes from. Fonts differ (matplotlib's DejaVu Sans vs R's
# default sans), so the result can't be pixel-identical.
#
# Horizontal "house style" (save_horizontal_bar_chart(), lines 169-213),
# used for by_class and bundles:
#   figsize 8 x 3.8 in (173); bars sorted by value, smallest at the bottom,
#   ties in input order (183, barh draws the first item lowest); bar height
#   0.45 (191); value label 6 pt right of the bar end, left-aligned,
#   vertically centred, 15 pt, black (193-203); x label 14 pt black (204);
#   x limits 0 .. 1.2 x max, no padding (205); y tick labels 14 pt, x tick
#   labels 13 pt, black (206-207); no spines (208-209); tick length 0 (210);
#   transparent figure and axes backgrounds, saved transparent (189-190,
#   212); no title; tight_layout (211).
# Vertical (save_all_figure(), lines 156-166; save_without_adjacent_figure(),
# 242-258):
#   figsize 7 x 5 / 8 x 5 in (158, 250); bar colour #444444 / #777777 and
#   #222222 (159, 251); width 0.55 / 0.6 (159, 251); value label 5 pt above
#   the bar, centred, 12 pt (add_value_labels(), 142-153); y label "Number of
#   maximal laminar families" (161, 253) and tick labels at matplotlib's
#   default 10 pt; title at the default 12 pt (162, 254) naming the language
#   (now from metadata, not "Chichewa (nyan1308)"); y limits 0 .. 1.18 x max
#   / 1.25 x max (163, 255); all four spines, default outward ticks 3.5 pt;
#   white background (default savefig); tight_layout (164, 256).
# Point offsets (5 pt, 6 pt) are converted to data units from the panel
# size those canvases give, so they are close, not exact.
# Two matplotlib defaults the charts rely on without naming them, also
# reproduced: the axis around categorical bars spans the bars plus a 5%
# margin (so a single bar fills most of its panel), and tick steps are the
# smallest of 1, 2, 2.5, 5, 10 (times a power of ten) giving at most 9
# intervals (AutoLocator/MaxNLocator), e.g. 2.5 for the bundles chart.
# Known remaining differences: R's default sans is narrower than DejaVu Sans
# at the same point size, and the hyphen in labels such as "Syntax-like"
# renders long, like a minus sign (a PDF encoding of WinAnsi.enc did not
# change it).

# matplotlib's AutoLocator ticks for an axis from `lower` to `limit`.
planarsviz_mpl_breaks <- function(limit, nbins = 9, lower = 0) {
  raw <- (limit - lower) / nbins
  scale <- 10 ^ floor(log10(raw))
  steps <- c(1, 2, 2.5, 5, 10) * scale
  step <- steps[steps >= raw - 1e-9][1]
  seq(ceiling(lower / step - 1e-9) * step, floor(limit / step + 1e-9) * step, by = step)
}

# matplotlib's padding around n categorical bars of the given width, as a
# ggplot discrete expansion measured from the outer category centres.
planarsviz_mpl_bar_expand <- function(n, width) {
  expansion(add = width / 2 + 0.05 * ((n - 1) + width))
}

#' Read tree counts from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A data frame: `condition`, `class`, `n_unique_spans`,
#'   `n_maximal_laminar_families`, `kind`, `label`, `colour`, in export order.
#' @export
read_planars_tree_counts <- function(bundle) {
  path <- file.path(bundle$bundle_dir, "data", "tree_counts.tsv")
  if (!file.exists(path)) stop("Bundle has no tree_counts.tsv; re-export it.", call. = FALSE)
  utils::read.delim(path, stringsAsFactors = FALSE, colClasses = c(
    n_unique_spans = "integer", n_maximal_laminar_families = "integer"
  ), na.strings = character(), comment.char = "")
}

planarsviz_house_bar_chart <- function(labels, values, colours, xlabel = "Number of trees") {
  # Ascending, ties in input order; the first level is drawn lowest.
  ord <- order(values, seq_along(values))
  d <- data.frame(label = factor(labels[ord], levels = labels[ord]),
                  value = values[ord], colour = colours[ord], stringsAsFactors = FALSE)
  xmax <- max(values) * 1.2
  # 6 pt offset as a share of the x range; the 8 in canvas leaves a panel of
  # roughly 6 in (432 pt) after the y labels.
  nudge <- xmax * 6 / 432
  ggplot(d, aes(x = value, y = label)) +
    geom_col(aes(fill = I(colour)), width = 0.45) +
    geom_text(aes(x = value + nudge, label = value), hjust = 0, vjust = 0.5,
              size = 15 / .pt, colour = "black") +
    scale_x_continuous(limits = c(0, xmax), expand = c(0, 0),
                       breaks = planarsviz_mpl_breaks(xmax)) +
    scale_y_discrete(expand = planarsviz_mpl_bar_expand(nrow(d), 0.45)) +
    labs(x = xlabel, y = NULL) +
    theme_minimal() +
    theme(
      panel.grid = element_blank(),
      axis.ticks = element_blank(),
      axis.ticks.length = unit(0, "pt"),
      axis.title.x = element_text(size = 14, colour = "black"),
      axis.text.y = element_text(size = 14, colour = "black"),
      axis.text.x = element_text(size = 13, colour = "black"),
      plot.background = element_blank(),
      panel.background = element_blank()
    )
}

planarsviz_vertical_bar_chart <- function(labels, values, colours, width, ylim_factor, title) {
  d <- data.frame(label = factor(labels, levels = labels), value = values,
                  colour = colours, stringsAsFactors = FALSE)
  ymax <- max(values) * ylim_factor
  # 5 pt offset as a share of the y range; a 5 in canvas leaves a panel of
  # roughly 4.2 in (302 pt) after the title and x labels.
  nudge <- ymax * 5 / 302
  ggplot(d, aes(x = label, y = value)) +
    geom_col(aes(fill = I(colour)), width = width) +
    geom_text(aes(y = value + nudge, label = value), vjust = 0, size = 12 / .pt) +
    scale_y_continuous(limits = c(0, ymax), expand = c(0, 0),
                       breaks = planarsviz_mpl_breaks(ymax)) +
    scale_x_discrete(expand = planarsviz_mpl_bar_expand(nrow(d), width)) +
    labs(x = NULL, y = "Number of maximal laminar families", title = title) +
    theme_bw() +
    theme(
      panel.grid = element_blank(),
      panel.border = element_rect(colour = "black", fill = NA, linewidth = 0.8 * 0.35),
      axis.ticks = element_line(colour = "black", linewidth = 0.8 * 0.35),
      axis.ticks.length = unit(3.5, "pt"),
      axis.text = element_text(size = 10, colour = "black"),
      axis.title.y = element_text(size = 10),
      plot.title = element_text(size = 12, hjust = 0.5),
      plot.background = element_rect(fill = "white", colour = NA)
    )
}

#' Tree-count bar charts
#'
#' How many maximal laminar families (trees) the data allows, as bar charts.
#' Reproduces `nyan1308_tree_count_by_class.pdf`, `_bundles.pdf` (transparent
#' horizontal "house style"), `_all.pdf` and `_without_adjacent.pdf`.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param chart `"by_class"` (one bar per domain type), `"bundles"` (one per
#'   class bundle), `"all"` (all tests), or `"without_adjacent"` (all tests
#'   vs. without size-2 spans).
#' @return A ggplot object with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`) and `planarsviz_transparent`.
#' @export
plot_tree_counts <- function(bundle, chart = c("by_class", "bundles", "all", "without_adjacent")) {
  validate_planars_bundle(bundle)
  chart <- match.arg(chart)
  counts <- read_planars_tree_counts(bundle)
  all_rows <- counts[counts$kind == "all", , drop = FALSE]
  value_of <- function(condition) all_rows$n_maximal_laminar_families[all_rows$condition == condition]
  title_stem <- planarsviz_dataset_title(bundle)

  if (chart %in% c("by_class", "bundles")) {
    kind <- if (chart == "by_class") "class" else "bundle"
    rows <- counts[counts$kind == kind & counts$condition == "all_tests", , drop = FALSE]
    if (!nrow(rows)) stop("This bundle has no ", chart, " counts.", call. = FALSE)
    p <- planarsviz_house_bar_chart(rows$label, rows$n_maximal_laminar_families, rows$colour)
    size <- c(width = 8, height = 3.8)
    transparent <- TRUE
  } else if (chart == "all") {
    p <- planarsviz_vertical_bar_chart("All tests", value_of("all_tests"), "#444444",
                                       width = 0.55, ylim_factor = 1.18,
                                       title = paste0(title_stem, ": all tests"))
    size <- c(width = 7, height = 5)
    transparent <- FALSE
  } else {
    p <- planarsviz_vertical_bar_chart(c("All tests", "Without size-2 spans"),
                                       c(value_of("all_tests"), value_of("without_adjacent_spans")),
                                       c("#777777", "#222222"), width = 0.6, ylim_factor = 1.25,
                                       title = paste0(title_stem, ": effect of removing adjacent spans"))
    size <- c(width = 8, height = 5)
    transparent <- FALSE
  }
  attr(p, "planarsviz_size") <- size
  attr(p, "planarsviz_units") <- "in"
  attr(p, "planarsviz_transparent") <- transparent
  p
}
