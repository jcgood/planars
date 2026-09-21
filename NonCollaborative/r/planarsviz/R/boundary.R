# Boundary charts (charts 5, 17, 18 in docs/PLAN_planarsviz_library.md).
#
# Chart 5 is copied from scripts/nyan_boundary_skyline.r, lines 1-129, at
# commit 43a308f (see the previous commit for the unchanged copy). The only
# changes since:
#   - the test rows come from the bundle instead of reading the domain TSV;
#   - literals replaced with bundle data: position labels and the 1..22
#     position range (position_labels.tsv, metadata n_positions), the
#     domain-type panel order (domain_types.tsv facet_order; unknown types
#     get a panel instead of silently vanishing), and the language name in
#     the title (metadata language_name);
#   - the boundary-count table is returned as an attribute instead of being
#     written to results/ (library functions don't write files);
#   - the unused type_colors vector is dropped;
#   - library() calls and ggsave() removed (the package imports ggplot2 and
#     patchwork; the renderer saves files).

#' Boundary-frequency skyline
#'
#' Each active test contributes two observations: where its span starts and
#' where it ends. The top panel pools all tests; the lower panel splits starts
#' and ends by domain type. Reproduces `nyan1308_boundary_skyline.pdf` from
#' `scripts/nyan_boundary_skyline.r`.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A patchwork plot with attributes `planarsviz_size` (`c(width,
#'   height)`), `planarsviz_units` (`"in"`), `planarsviz_folder` (its
#'   `results/planarsviz` subfolder), `planarsviz_boundary_counts` (the
#'   per-position, per-boundary, per-type counts the working script wrote to
#'   `nyan1308_boundary_counts.tsv`), and `planarsviz_parts` (the two panels,
#'   for checking).
#' @export
plot_boundary_skyline <- function(bundle) {
  validate_planars_bundle(bundle)
  n_positions <- as.integer(bundle$metadata$n_positions)
  position_labels <- unname(planarsviz_position_labels(bundle$position_labels))
  style <- planarsviz_domain_types(bundle)
  facet_levels <- style$domain_type[order(style$facet_order)]

  domains <- bundle$tests
  domains$Left_Edge <- as.integer(domains$Left_Edge)
  domains$Right_Edge <- as.integer(domains$Right_Edge)

  boundary_data <- rbind(
    data.frame(
      Position = domains$Left_Edge,
      Boundary = "Start",
      Domain_Type = domains$Domain_Type
    ),
    data.frame(
      Position = domains$Right_Edge,
      Boundary = "End",
      Domain_Type = domains$Domain_Type
    )
  )

  boundary_data$Position <- factor(boundary_data$Position, levels = seq_len(n_positions))
  boundary_data$Boundary <- factor(boundary_data$Boundary, levels = c("Start", "End"))
  boundary_data$Domain_Type <- factor(
    boundary_data$Domain_Type,
    levels = facet_levels
  )

  counts <- as.data.frame(table(
    Position = boundary_data$Position,
    Boundary = boundary_data$Boundary,
    Domain_Type = boundary_data$Domain_Type
  ))
  names(counts)[names(counts) == "Freq"] <- "Count"
  counts <- counts[counts$Count > 0, ]

  boundary_colors <- c(Start = "#D55E00", End = "#0072B2")

  axis_theme <- theme(
    axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1),
    axis.title.y = element_text(margin = margin(r = 8)),
    panel.grid.minor = element_blank()
  )

  all_counts <- as.data.frame(table(
    Position = boundary_data$Position,
    Boundary = boundary_data$Boundary
  ))
  names(all_counts)[names(all_counts) == "Freq"] <- "Count"

  p_all <- ggplot(all_counts, aes(x = Position, y = Count, fill = Boundary)) +
    geom_col(position = "dodge", width = 0.82, color = "white", linewidth = 0.2) +
    scale_fill_manual(values = boundary_colors) +
    scale_x_discrete(labels = position_labels, drop = FALSE) +
    scale_y_continuous(expand = expansion(mult = c(0, 0.08)), breaks = scales::pretty_breaks(5)) +
    labs(
      title = "All active tests",
      x = "Planar position",
      y = "Number of tests",
      fill = "Boundary"
    ) +
    theme_bw(base_size = 11) +
    axis_theme +
    theme(legend.position = "top")

  p_by_type <- ggplot(counts, aes(x = Position, y = Count, fill = Boundary)) +
    geom_col(position = "dodge", width = 0.82, color = "white", linewidth = 0.2) +
    facet_grid(Boundary ~ Domain_Type, scales = "free_y") +
    scale_fill_manual(values = boundary_colors, drop = FALSE) +
    scale_x_discrete(labels = position_labels, drop = FALSE) +
    scale_y_continuous(expand = expansion(mult = c(0, 0.08)), breaks = scales::pretty_breaks(5)) +
    labs(
      x = "Planar position",
      y = "Number of tests",
      fill = "Boundary"
    ) +
    theme_bw(base_size = 11) +
    theme(
      strip.background = element_rect(fill = "grey92", color = "grey60"),
      panel.grid.minor = element_blank(),
      axis.text.x = element_blank(),
      axis.title.x = element_blank(),
      legend.position = "none"
    )

  p <- p_all / p_by_type +
    plot_layout(heights = c(1, 1.7)) +
    plot_annotation(
      title = paste0(planarsviz_dataset_title(bundle), ": distribution of span boundaries"),
      subtitle = paste0(
        nrow(domains), " active tests; each test contributes one start and one end boundary. ",
        "Bars show counts at each planar position."
      )
    )

  attr(p, "planarsviz_size") <- c(width = 16, height = 11)
  attr(p, "planarsviz_units") <- "in"
  attr(p, "planarsviz_folder") <- "boundaries"
  attr(p, "planarsviz_boundary_counts") <- counts
  attr(p, "planarsviz_parts") <- list(p_all = p_all, p_by_type = p_by_type)
  p
}

#' Dataset name for chart titles
#'
#' `"Language (dataset)"` when the bundle records a language name, otherwise
#' just the dataset id.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A single string.
#' @export
planarsviz_dataset_title <- function(bundle) {
  name <- bundle$metadata$language_name
  dataset <- bundle$metadata$dataset
  if (is.null(name) || !nzchar(name)) dataset else paste0(name, " (", dataset, ")")
}
