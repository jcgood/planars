# Pooled constituency plots (charts 1-4 in docs/PLAN_planarsviz_library.md).
#
# Copied from scripts/domain_charts-cgpt.r, lines 14-202, at commit 43a308f
# (see the previous commit for the unchanged copy). The only changes since:
#   - literals replaced with bundle data: the domain-type factor levels,
#     group.colors, and the legend breaks now come from domain_types.tsv; the
#     root position (o) and position count (b) from metadata.json;
#   - the dotted root line is skipped when the bundle has no root position;
#   - plot_height() renamed pooled_plot_height() (a "plot_" name would be
#     exported by the NAMESPACE pattern);
#   - plot_pooled() added as the public entry point, reproducing the four
#     chart families that script builds.

# Ensures test rows become two edges (L/R) and layers are computed consistently
df.plot <- function(d, type_levels) {
  d <- d %>%
    mutate(
      Domain_Type = factor(
        Domain_Type,
        levels = type_levels
      )
    ) %>%
    arrange(desc(Size), Left_Edge) %>%
    group_by(Size, Left_Edge) %>% # group for layer IDs
    mutate(Layer = cur_group_id()) %>%
    ungroup() %>%
    arrange(Layer, Domain_Type, Left_Edge, Test_Labels) %>%
    mutate(Test_Labels = factor(Test_Labels, levels = unique(Test_Labels))) %>%
    pivot_longer(Left_Edge:Right_Edge, names_to = "Edge_Type", values_to = "Edge")

  # Provide Reverse_Layer universally so any subset will work with constituency.plot()
  max_layer <- max(d$Layer, na.rm = TRUE)
  d <- d %>% mutate(Reverse_Layer = max_layer + 1 - Layer)
  d
}

# Domain-focused version; remove desc() from group_by
df.domain.plot <- function(d, type_levels) {
  d <- d %>%
    mutate(
      Domain_Type = factor(
        Domain_Type,
        levels = type_levels
      )
    ) %>%
    group_by(Domain_Type, Size, Left_Edge) %>%
    mutate(Layer = cur_group_id()) %>%
    ungroup() %>%
    arrange(desc(Size), Left_Edge) %>%
    group_by(Size, Left_Edge) %>%
    mutate(Domain_Layer = cur_group_id()) %>%
    ungroup() %>%
    pivot_longer(Left_Edge:Right_Edge, names_to = "Edge_Type", values_to = "Edge")

  # Provide Reverse_Domain_Layer universally
  max_dlayer <- max(d$Domain_Layer, na.rm = TRUE)
  d <- d %>% mutate(Reverse_Domain_Layer = max_dlayer + 1 - Domain_Layer)
  d
}

# Shared finishing touches for both plot functions below. When the data covers only one
# Domain_Type (the per-class charts), a 5-item color legend is both misleading (it lists
# types that aren't in the chart) and a waste of vertical space on already-short charts —
# so swap it for a plain title instead. Multi-domain charts (the pooled ones) keep the legend.
#
# The legend's horizontal justification of 1.25 (past flush right) was tuned on
# nyan1308's five-type legend, which nearly fills the width, so the overshoot
# is small. ggplot scales that overshoot by the room left beside the legend,
# so a shorter legend (CCDB's three types) is pushed off the right edge; with
# fewer than five entries the legend sits flush right instead.
finish.constituency.plot <- function(p, c, n_legend_entries = 5L) {
  domain_types <- unique(na.omit(as.character(c$Domain_Type)))

  if (length(domain_types) == 1) {
    p +
      ggtitle(paste0(str_to_title(domain_types), " domains")) +
      # plot.title.position = "panel" (the theme_bw() default) already aligns the title to
      # the data panel rather than the full plot width, so hjust = 0.5 centers it over the
      # panel itself, not over the (variable-width) row-label column to its left.
      theme(legend.position = "none", plot.title = element_text(hjust = 0.5))
  } else {
    p +
      theme(
        legend.direction = "horizontal",
        legend.position = "top",
        legend.justification = c(if (n_legend_entries >= 5L) 1.25 else 1, 0)
      )
  }
}

constituency.plot <- function(c, b, o, group.colors, legend_breaks) {
  p <- ggplot(c, aes(
    x = Edge,
    # Largest domain on top: ascending Size puts the highest value (largest
    # domain) at the last factor level, which ggplot draws at the top.
    y = reorder(Test_Labels, Size * 100 + as.numeric(Layer)),
    label = Reverse_Layer
  )) +
    {
      if (!is.null(o)) geom_vline(xintercept = o, linetype = "dotted")
    } +
    geom_line(aes(color = Domain_Type), linewidth = 2) +
    labs(color = "Domain Type:") +
    geom_label(
      aes(color = Domain_Type),
      size = 3, label.padding = unit(0.2, "lines"),
      show.legend = FALSE
    ) +
    xlab("Positions on the verbal planar structure") +
    scale_x_continuous(breaks = seq(1, b, 1), limits = c(1, b)) +

    # Custom legend order (only shown for multi-domain charts; see finish.constituency.plot())
    scale_color_manual(
      values = group.colors,
      breaks = legend_breaks
    ) +
    theme_bw() +
    theme(
      axis.title.y = element_blank(),
      text = element_text(size = 15),
      panel.grid.minor = element_blank()
    )

  finish.constituency.plot(p, c, length(legend_breaks))
}


constituency.domain.plot <- function(c, b, o, group.colors, legend_breaks) {
  p <- ggplot(c, aes(
    x = Edge,
    y = reorder(Test_Labels, Layer),
    label = Reverse_Domain_Layer
  )) +
    {
      if (!is.null(o)) geom_vline(xintercept = o, linetype = "dotted")
    } +
    geom_line(aes(color = Domain_Type), linewidth = 2) +
    labs(color = "Domain Type:") +
    geom_label(
      aes(color = Domain_Type),
      size = 3, label.padding = unit(0.2, "lines"),
      show.legend = FALSE
    ) +
    xlab("Positions on the verbal planar structure") +
    scale_x_continuous(breaks = seq(1, b, 1), limits = c(1, b)) +

    # Custom legend order (only shown for multi-domain charts; see finish.constituency.plot())
    scale_color_manual(
      values = group.colors,
      breaks = legend_breaks
    ) +
    theme_bw() +
    theme(
      axis.title.y = element_blank(),
      text = element_text(size = 15),
      panel.grid.minor = element_blank()
    )

  finish.constituency.plot(p, c, length(legend_breaks))
}

# Chart height scales with how many tests it contains, with a floor so small
# classes (e.g. length, n=7 tests) don't render unreadably short.
pooled_plot_height <- function(d) max(7, n_distinct(d$Test_Labels) * 0.7)

#' Pooled constituency plot
#'
#' One horizontal line per test across the planar positions, coloured by
#' domain type, with tests that pick out the same span grouped into one
#' numbered layer. Reproduces the four chart families built by
#' `scripts/domain_charts-cgpt.r`:
#'
#' * `plot_pooled(bundle)` — all tests (`nyan1308_pooled_plot.pdf`).
#' * `plot_pooled(bundle, group_by_domain = TRUE)` — rows grouped by domain
#'   type first (`nyan1308_pooled_domainplot.pdf`).
#' * `plot_pooled(bundle, domain_types = "length", layers = "local")` — one
#'   domain type, layers renumbered from 1 for that type alone
#'   (`nyan1308_pooled_plot_length.pdf`).
#' * `plot_pooled(bundle, domain_types = "length", layers = "global")` — one
#'   domain type, keeping the layer numbers it has in the all-tests plot
#'   (`nyan1308_pooled_plot_length_global_layers.pdf`). This is a filtered
#'   *view*: the numbers deliberately refer to the all-tests plot.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param domain_types `NULL` for all tests, or domain types to keep.
#' @param layers `"global"` or `"local"` numbering when `domain_types` is set.
#' @param group_by_domain Group rows by domain type first (all tests only).
#' @return A ggplot object, with attributes `planarsviz_size` (the working
#'   script's canvas as `c(width, height)` in centimetres) and
#'   `planarsviz_folder` (its `results/planarsviz` subfolder).
#' @export
plot_pooled <- function(bundle, domain_types = NULL, layers = c("global", "local"),
                        group_by_domain = FALSE) {
  validate_planars_bundle(bundle)
  layers <- match.arg(layers)
  if (isTRUE(group_by_domain) && !is.null(domain_types)) {
    stop("`group_by_domain` is only available for all tests.", call. = FALSE)
  }

  setup <- planarsviz_pooled_setup(bundle)
  type_levels <- setup$type_levels
  group.colors <- setup$group.colors
  legend_breaks <- setup$legend_breaks
  b <- setup$b
  o <- setup$o
  tests <- setup$tests

  if (isTRUE(group_by_domain)) {
    d <- df.domain.plot(tests, type_levels)
    p <- constituency.domain.plot(d, b, o, group.colors, legend_breaks)
    width <- 26
  } else if (is.null(domain_types)) {
    d <- df.plot(tests, type_levels)
    p <- constituency.plot(d, b, o, group.colors, legend_breaks)
    width <- 26
  } else {
    unknown <- setdiff(domain_types, unique(tests$Domain_Type))
    if (length(unknown)) {
      stop("Domain type(s) not in this bundle: ", paste(unknown, collapse = ", "), call. = FALSE)
    }
    d <- if (layers == "local") {
      df.plot(filter(tests, Domain_Type %in% domain_types), type_levels)
    } else {
      filter(df.plot(tests, type_levels), Domain_Type %in% domain_types)
    }
    p <- constituency.plot(d, b, o, group.colors, legend_breaks)
    width <- 25
  }
  attr(p, "planarsviz_size") <- c(width = width * planarsviz_position_scale(bundle), height = pooled_plot_height(d))
  attr(p, "planarsviz_units") <- "cm"
  attr(p, "planarsviz_folder") <- "pooled"
  p
}

# What every pooled-style chart reads from the bundle: domain-type levels,
# colours and legend order, position count (b), root position (o), and the
# tests with trimmed labels. Shared by plot_pooled() and the exemplary
# evidence panels so they can't drift apart.
planarsviz_pooled_setup <- function(bundle) {
  style <- planarsviz_domain_types(bundle)
  o <- bundle$metadata$root_position
  if (!is.null(o)) o <- as.integer(o)
  tests <- bundle$tests
  tests$Test_Labels <- trimws(tests$Test_Labels)
  tests$Domain_Type <- trimws(tests$Domain_Type)
  list(
    type_levels = style$domain_type[order(style$sort_order)],
    group.colors = stats::setNames(style$colour, style$domain_type),
    legend_breaks = style$domain_type[order(style$legend_order)],
    b = as.integer(bundle$metadata$n_positions),
    o = o,
    tests = tests
  )
}

#' Domain-type style table from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A data frame with `domain_type`, `colour`, `sort_order`,
#'   `legend_order`.
#' @export
planarsviz_domain_types <- function(bundle) {
  path <- file.path(bundle$bundle_dir, "data", "domain_types.tsv")
  if (!file.exists(path)) {
    stop("Bundle has no domain_types.tsv; re-export it with export_planarsviz_data.py.", call. = FALSE)
  }
  style <- utils::read.delim(path, stringsAsFactors = FALSE, comment.char = "")
  required <- c("domain_type", "colour", "sort_order", "legend_order")
  missing <- setdiff(required, names(style))
  if (length(missing)) {
    stop("domain_types.tsv is missing: ", paste(missing, collapse = ", "), call. = FALSE)
  }
  style
}
