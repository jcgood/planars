# Stacked laminar overlays (charts 7, 8, 9 in docs/PLAN_planarsviz_library.md).
#
# Copied, at commit 43a308f, from the R that
# laminar_analysis.generate_r_overlay_script() used to write
# (nyan1308_laminar_overlay.r, nyan1308_all_families_labeled.r) and the hand
# edits in nyan1308_all_families_labeled_wordhood.r. Both are gone from the
# working tree: that generator was removed in cutover step C3 and the scripts
# it wrote are archived in OlderFiles/planarsviz_superseded/results/.
# One function now covers all
# three charts; the choices that made them different scripts are options
# whose defaults reproduce the generator's defaults:
#   chart 7  plot_laminar_overlay(bundle)
#   chart 8  plot_laminar_overlay(bundle, groups = "all", alpha_divisor = 1,
#                                 thickness_exponent = 0.75)
#   chart 9  chart 8 + highlight = "orthographic_word"
# Changes since the copy:
#   - per-tree blocks via planarsviz_ghost_tree() (spacer without lineheight,
#     as this generator writes it);
#   - literals replaced with bundle data: trees, span groups and convergence
#     (data/overlay_groups/<id>.tsv), group colours and domain types
#     (overlay_groups.json), position labels, domain-type legend colours and
#     order (domain_types.tsv), highlight ranges and colours (highlights.tsv);
#   - alpha, thickness, and the darkness/thickness legend's swatch values are
#     computed here with the generator's formulas instead of being pasted in;
#   - the colour legend lists the domain types of the groups actually drawn
#     (the generator always listed its fixed five, which for nyan1308 are the
#     same five);
#   - fixed 2026-09-15 at Jeff's request: the darkness/thickness legend's
#     "More" thickness swatch follows the lines' exponent (the generator
#     always used a square root, so with exponent 0.75 the swatch was
#     thinner than the thickest line); legend_thickness_exponent = 0.5
#     reproduces the generator's legend;
#   - library() and ggsave() removed. Without `legend`, the white page
#     background the generator applied inside ggsave() is applied to the
#     returned plot; with `legend`, the plot is built exactly as the
#     generator's legend_version (the multi-group version has no white
#     background layer, as in the generator).

#' Read overlay groups from a bundle
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @return A list of groups, each with `meta` (a row of overlay_groups.json)
#'   and `trees` (newick, group_spans, group_convergence).
#' @export
read_planars_overlay_groups <- function(bundle) {
  path <- file.path(bundle$bundle_dir, "data", "overlay_groups.json")
  if (!file.exists(path)) stop("Bundle has no overlay_groups.json; re-export it.", call. = FALSE)
  index <- jsonlite::read_json(path, simplifyVector = FALSE)
  lapply(index, function(meta) {
    list(
      meta = meta,
      trees = utils::read.delim(
        file.path(
          bundle$bundle_dir, "data", "overlay_groups",
          paste0(meta$group_id, ".tsv")
        ),
        stringsAsFactors = FALSE, colClasses = "character"
      )
    )
  })
}

#' Stacked laminar overlay
#'
#' Every maximal family of one or more groups drawn as a faint tree and
#' stacked in one panel: darkness shows how many trees share a branch, line
#' thickness shows convergence (how many tests produced the span).
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param groups Group ids from `overlay_groups.json`. `NULL` (default) = every
#'   domain-type group, coloured; `"all"` = every family of the full dataset.
#' @param alpha_divisor Divides the opacity formula `1 - 0.01^(1/n_trees)`.
#' @param thickness_exponent Line thickness is `max(convergence, 1)` to this power.
#' @param legend Add the inset legend: a domain-type colour key when more than
#'   one group is drawn, otherwise a darkness/thickness key.
#' @param highlight A `highlight_id` from `highlights.tsv` to colour position
#'   labels by (e.g. `"orthographic_word"`), or `NULL`.
#' @param legend_thickness_exponent Exponent for the darkness/thickness
#'   legend's "More" thickness swatch; defaults to `thickness_exponent` so the
#'   swatch matches the lines. `0.5` reproduces the old generated legend.
#' @return A patchwork plot with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`), `planarsviz_folder` (its
#'   `results/planarsviz` subfolder), `planarsviz_parts` (tree plots in
#'   stacking order) and, with `legend = TRUE`, `planarsviz_legend_plot`.
#' @export
plot_laminar_overlay <- function(bundle, groups = NULL, alpha_divisor = 2,
                                 thickness_exponent = 0.5, legend = FALSE,
                                 highlight = NULL,
                                 legend_thickness_exponent = thickness_exponent) {
  validate_planars_bundle(bundle)
  planarsviz_require_trees()
  all_groups <- read_planars_overlay_groups(bundle)
  ids <- vapply(all_groups, function(g) g$meta$group_id, character(1))
  if (is.null(groups)) groups <- setdiff(ids, "all")
  missing <- setdiff(groups, ids)
  if (length(missing)) {
    stop("Overlay group(s) not in this bundle: ", paste(missing, collapse = ", "),
      ". Available: ", paste(ids, collapse = ", "),
      call. = FALSE
    )
  }
  chosen <- all_groups[match(groups, ids)]
  chosen <- Filter(function(g) nrow(g$trees) > 0, chosen)
  n_total <- sum(vapply(chosen, function(g) nrow(g$trees), integer(1)))
  alphaval <- round((1 - 0.01^(1 / n_total)) / alpha_divisor, 6)
  labels <- planarsviz_position_labels(bundle$position_labels)
  pos_label <- as.list(labels)

  plots <- list()
  for (g in chosen) {
    for (i in seq_len(nrow(g$trees))) {
      convergence <- as.integer(strsplit(g$trees$group_convergence[[i]], ";", fixed = TRUE)[[1]])
      plots[[length(plots) + 1]] <- planarsviz_ghost_tree(
        newick = g$trees$newick[[i]],
        group_spans = strsplit(g$trees$group_spans[[i]], ";", fixed = TRUE)[[1]],
        strengths = round(pmax(convergence, 1)^thickness_exponent, 4),
        alphaval = alphaval,
        colour = g$meta$colour,
        spacer_lineheight = NULL
      )
    }
  }
  n <- length(plots)

  if (is.null(highlight)) {
    plots[[n]] <- plots[[n]] + ggtree::geom_tiplab(
      geom = "label", size = 6, angle = 0,
      offset = -1, hjust = 0.5, vjust = 0.35, alpha = 1, label.size = 0,
      aes(label = paste(label, pos_label[label], sep = "\n")), lineheight = 1
    )
  } else {
    word_color <- planarsviz_highlight_colours(bundle, highlight)
    plots[[n]] <- plots[[n]] + ggtree::geom_tiplab(
      geom = "label", size = 6, angle = 0,
      offset = -1, hjust = 0.5, vjust = 0.35, alpha = 1, label.size = 0,
      aes(label = paste(label, pos_label[label], sep = "\n"), colour = word_color[label]),
      lineheight = 1
    ) +
      scale_colour_identity()
  }

  treelayout <- do.call(c, rep(list(patchwork::area(t = 1, l = 1, b = 5, r = 1)), n))
  forest <- Reduce(`+`, plots) + plot_layout(design = treelayout)
  bg_theme <- theme(plot.background = element_rect(fill = "white", color = NA))

  legend_plot <- NULL
  if (!isTRUE(legend)) {
    result <- forest & bg_theme
  } else if (length(chosen) > 1) {
    types <- unique(unlist(lapply(chosen, function(g) g$meta$domain_types)))
    style <- planarsviz_domain_types(bundle)
    style <- style[style$domain_type %in% types, , drop = FALSE]
    style <- style[order(style$sort_order), , drop = FALSE]
    legend_data <- data.frame(
      Domain_Type = factor(style$domain_type,
        levels = style$domain_type
      ),
      x = 1, y = 1
    )
    legend_plot <- ggplot(legend_data, aes(x = x, y = y, color = Domain_Type)) +
      geom_point(size = 3, alpha = 0) +
      scale_color_manual(
        values = stats::setNames(style$colour, style$domain_type),
        name = "Domain type"
      ) +
      guides(color = guide_legend(override.aes = list(alpha = 1))) +
      theme_void() +
      theme(
        legend.position = "inside", legend.position.inside = c(0.02, 0.98),
        legend.justification = c("left", "top"), legend.direction = "vertical",
        legend.background = element_rect(fill = "white", color = "black", linewidth = 0.5),
        legend.text = element_text(size = 26), legend.title = element_text(size = 28, face = "bold"),
        legend.key.height = unit(2.2, "lines"), legend.key.width = unit(1.2, "lines"),
        legend.spacing.y = unit(0.45, "in"), legend.margin = margin(18, 20, 18, 20),
        plot.margin = margin(8, 8, 8, 8)
      )
    result <- forest + patchwork::inset_element(
      legend_plot,
      left = 0.002, bottom = 0.55, right = 0.40, top = 0.97,
      align_to = "panel", on_top = TRUE
    )
  } else {
    # Swatch values with the generator's formulas, except that the thickness
    # swatches use legend_thickness_exponent (default: the lines' own
    # exponent; the generator always used 0.5).
    max_conv <- max(1L, unlist(lapply(chosen, function(g) {
      as.integer(unlist(strsplit(g$trees$group_convergence, ";", fixed = TRUE)))
    })))
    dark_hi <- round(1 - (1 - alphaval)^n_total, 6)
    dark_lo <- 0.4
    thick_hi <- round(max_conv^legend_thickness_exponent, 4)
    thick_lo <- round(1^legend_thickness_exponent, 4)
    legend_header_data <- data.frame(
      y = c(7, 3.65),
      label = c(
        "Darkness: Trees sharing span",
        "Thickness: Tests supporting span"
      )
    )
    legend_swatch_data <- data.frame(
      y = c(6.0, 5.15, 2.65, 1.8),
      alpha_val = c(dark_hi, dark_lo, 1, 1),
      lw = c(3, 3, thick_hi, thick_lo),
      label = c("More", "Fewer", "More", "Fewer")
    )
    # A swatch's rounded ends stick out by half its line width. Up to the
    # legend's 6 pt left margin that is harmless (every swatch the generator
    # drew fits, so those keep their exact position); a thicker swatch --
    # e.g. the thickness swatch at exponent 0.75 -- is pulled in by the
    # excess so it stays inside the box and clear of its label. The legend
    # panel is about 0.26 x 19.8 in wide for x from 0 to 4.9.
    pt_per_unit <- 0.26 * 19.8 * 72 / 4.9
    inset <- pmax(0, legend_swatch_data$lw * .pt * 0.75 / 2 - 6) / pt_per_unit
    legend_swatch_data$x0 <- inset
    legend_swatch_data$x1 <- 0.9 - inset
    legend_plot <- ggplot() +
      geom_text(
        data = legend_header_data, aes(x = 0, y = y, label = label),
        hjust = 0, size = 7
      ) +
      geom_segment(
        data = legend_swatch_data,
        aes(x = x0, xend = x1, y = y, yend = y, alpha = alpha_val, linewidth = lw),
        color = "black", lineend = "round"
      ) +
      geom_text(
        data = legend_swatch_data, aes(x = 1.05, y = y, label = label),
        hjust = 0, size = 5.8
      ) +
      scale_alpha_identity() +
      scale_linewidth_identity() +
      xlim(0, 4.9) +
      ylim(1.3, 7.5) +
      theme_void() +
      theme(
        plot.background = element_rect(fill = "white", color = "black", linewidth = 1.2),
        plot.margin = margin(6, 8, 6, 6)
      )
    result <- (forest & bg_theme) + patchwork::inset_element(legend_plot,
      left = 0.01, bottom = 0.67, right = 0.27, top = 0.97,
      align_to = "panel", on_top = TRUE
    )
  }

  attr(result, "planarsviz_size") <- c(width = 20, height = 14)
  attr(result, "planarsviz_units") <- "in"
  attr(result, "planarsviz_folder") <- "laminar-families"
  attr(result, "planarsviz_parts") <- plots
  if (!is.null(legend_plot)) attr(result, "planarsviz_legend_plot") <- legend_plot
  result
}

#' Outer extent of a named position highlight
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param highlight_id A `highlight_id` from `highlights.tsv`.
#' @return `c(left, right)`: the first and last position the highlight's
#'   ranges cover together (nyan1308's orthographic word: 5 and 19).
#' @export
planarsviz_highlight_range <- function(bundle, highlight_id) {
  path <- file.path(bundle$bundle_dir, "data", "highlights.tsv")
  rows <- if (file.exists(path)) utils::read.delim(path, stringsAsFactors = FALSE) else data.frame()
  rows <- rows[rows$highlight_id == highlight_id, , drop = FALSE]
  if (!nrow(rows)) stop("No highlight `", highlight_id, "` in this bundle.", call. = FALSE)
  c(min(as.integer(rows$left)), max(as.integer(rows$right)))
}

#' Label colours for a named position highlight
#'
#' @param bundle A bundle from [read_planars_bundle()].
#' @param highlight_id A `highlight_id` from `highlights.tsv`.
#' @param default Colour for positions outside every range.
#' @return A character vector of colours named by position number, for
#'   positions 1..n_positions. Rows are applied in `layer` order, so later
#'   layers win where ranges overlap.
#' @export
planarsviz_highlight_colours <- function(bundle, highlight_id, default = "black") {
  path <- file.path(bundle$bundle_dir, "data", "highlights.tsv")
  rows <- if (file.exists(path)) utils::read.delim(path, stringsAsFactors = FALSE) else data.frame()
  rows <- rows[rows$highlight_id == highlight_id, , drop = FALSE]
  if (!nrow(rows)) stop("No highlight `", highlight_id, "` in this bundle.", call. = FALSE)
  n_positions <- as.integer(bundle$metadata$n_positions)
  word_color <- stats::setNames(rep(default, n_positions), as.character(seq_len(n_positions)))
  rows <- rows[order(rows$layer), , drop = FALSE]
  for (i in seq_len(nrow(rows))) {
    word_color[as.character(rows$left[[i]]:rows$right[[i]])] <- rows$colour[[i]]
  }
  word_color
}
