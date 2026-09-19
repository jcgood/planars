# Span-frequency chart (chart 15 in docs/PLAN_planarsviz_library.md).
#
# Copied from results/laminar_spanchart.r, lines 1-35, at commit 43a308f (see
# the previous commit for the unchanged copy). That script is generated and
# its generator was never committed; its pasted-in data frame is rebuilt here
# from the bundle using rules recovered from its values (all reproduce it
# exactly for nyan1308 -- see docs/PLANARSVIZ_LIBRARY_PROGRESS.md):
#   - rows: every span except the full root, in spans.tsv span_chart_rank
#     order (computed by the exporter);
#   - freq = family count; freq_scaled = round(freq / n_families, 6);
#   - lw = round(0.5 + 5 * freq_scaled, 4);
#   - color = alt_colour of the span's domain type with the lowest
#     colour_priority (domain_types.tsv);
#   - label = "[left-right] freq/n_families".
# Other literals replaced: position labels and 1..22 breaks, and the family
# count in the title and legend name. library() and ggsave() removed.

#' Span-frequency chart
#'
#' Each observed span except the full root drawn as a horizontal segment over
#' its positions, ordered by how many maximal families contain it (fewest at
#' the bottom), with line width and opacity scaled by that share and colour
#' by domain type. Reproduces `nyan1308_spanchart.pdf`.
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A ggplot object with attributes `planarsviz_size` (`c(width,
#'   height)`) and `planarsviz_units` (`"in"`).
#' @param positions `"all"` (default) shows every position in the planar
#'   structure; `"drawn"` shows only the stretch the charted spans cover,
#'   as the original script did — for nyan1308 that silently dropped
#'   position 1, which only the excluded full root reaches.
#' @export
plot_span_chart <- function(bundle, positions = c("all", "drawn")) {
  validate_planars_bundle(bundle)
  positions <- match.arg(positions)
  n_families <- as.integer(bundle$metadata$n_maximal_families)
  n_positions <- as.integer(bundle$metadata$n_positions)
  pos_labels_vec <- unname(planarsviz_position_labels(bundle$position_labels))
  style <- planarsviz_domain_types(bundle)
  for (col in c("alt_colour", "colour_priority")) {
    if (!col %in% names(style)) stop("domain_types.tsv is missing ", col, "; re-export the bundle.", call. = FALSE)
  }
  if (!"span_chart_rank" %in% names(bundle$spans)) {
    stop("spans.tsv is missing span_chart_rank; re-export the bundle.", call. = FALSE)
  }

  spans <- bundle$spans[!is.na(bundle$spans$span_chart_rank), , drop = FALSE]
  spans <- spans[order(as.integer(spans$span_chart_rank)), , drop = FALSE]
  priority <- stats::setNames(style$colour_priority, style$domain_type)
  alt <- stats::setNames(style$alt_colour, style$domain_type)
  span_types <- strsplit(spans$domain_types, "|", fixed = TRUE)
  color <- vapply(span_types, function(types) {
    types <- types[types %in% names(priority)]
    alt[[types[which.min(priority[types])]]]
  }, character(1))
  freq_scaled <- round(spans$family_frequency / n_families, 6)

  span_data <- data.frame(
    left        = as.numeric(spans$left),
    right       = as.numeric(spans$right),
    freq        = as.numeric(spans$family_frequency),
    freq_scaled = freq_scaled,
    domain      = gsub("|", "/", spans$domain_types, fixed = TRUE),
    color       = unname(color),
    lw          = round(0.5 + 5 * freq_scaled, 4),
    label       = paste0("[", spans$left, "-", spans$right, "] ", spans$family_frequency, "/", n_families),
    y_rank      = as.numeric(seq_len(nrow(spans)))
  )

  p_spanchart <- ggplot(span_data) +
    geom_segment(aes(x=left, xend=right, y=y_rank, yend=y_rank,
      color=color, alpha=freq_scaled, linewidth=lw)) +
    geom_text(aes(x=(left+right)/2, y=y_rank+0.45, label=label),
      size=2.8, hjust=0.5) +
    scale_color_identity(guide='none') +
    scale_alpha_continuous(range=c(0.15, 1.0),
      name=paste0('Proportion of ', n_families, ' families')) +
    scale_linewidth_identity() +
    scale_x_continuous(breaks=seq_len(n_positions),
      labels=pos_labels_vec, name='Position',
      # Without limits the axis runs only as far as the drawn spans reach,
      # so a position no span touches loses its tick label.
      limits=if (positions == "all") c(1, n_positions) else NULL,
      expand=expansion(add=0.5)) +
    scale_y_continuous(name='', breaks=NULL) +
    theme_minimal() +
    theme(panel.grid.major.y=element_blank(),
      axis.text.x=element_text(angle=90, vjust=0.5, hjust=1)) +
    ggtitle(paste0(n_families, ' maximal families: span frequencies'))

  attr(p_spanchart, "planarsviz_size") <- c(width = 14, height = 8)
  attr(p_spanchart, "planarsviz_units") <- "in"
  p_spanchart
}
