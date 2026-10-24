# The `cross_language` bundle: every structure's own bundle set side by side
# (nyan1308 and the 21 CCDB structures). Written by
# scripts/analysis/export_cross_language.py, which reads the per-language
# bundles and re-runs no analysis; plan docs/PLAN_cross_language_charts.md.
# Charts, each tied to one of the three hypotheses:
#   - plot_cross_language_tree_likeness(): observed family count against two
#     nulls, as a ratio to the null median (Tree hypothesis).
#   - plot_cross_language_families_vs_size(): family count against span count
#     (Tree hypothesis; which structures are unusually fragmented).
#   - plot_cross_language_divide() and plot_cross_language_side_p(): where
#     conflicts fall relative to the morphosyntax/phonology divide, and which
#     side is more tree-like (divide hypothesis).
#   - plot_cross_language_edges(): boundary strength around the root.
#   - plot_cross_language_convergence(): the most convergent spans around the
#     root (Word hypothesis).
# Like the illustrations bundle, the charts have no topic subfolder
# (`planarsviz_folder` is ""), so they land in results/cross_language/.

#' Read the cross-language data bundle
#'
#' @param bundle_dir The `cross_language` bundle directory (containing
#'   `data/`), or the `data/` directory itself.
#' @return A list with `metadata`, `structures`, `family_count_tests`,
#'   `pooled_tests`, `conflict_divide`, `boundary_profile`,
#'   `convergent_spans`, `summary` and `bundle_dir`.
#' @export
read_planars_cross_language <- function(bundle_dir) {
  bundle_dir <- normalizePath(bundle_dir, mustWork = TRUE)
  data_dir <- if (basename(bundle_dir) == "data") bundle_dir else file.path(bundle_dir, "data")
  tables <- c(
    "structures", "family_count_tests", "pooled_tests", "conflict_divide",
    "boundary_profile", "convergent_spans", "summary"
  )
  required <- c("metadata.json", paste0(tables, ".tsv"))
  missing <- required[!file.exists(file.path(data_dir, required))]
  if (length(missing) > 0L) {
    stop("Cross-language bundle is missing: ", paste(missing, collapse = ", "), call. = FALSE)
  }
  ref <- lapply(stats::setNames(tables, tables), function(name) {
    utils::read.delim(file.path(data_dir, paste0(name, ".tsv")),
      stringsAsFactors = FALSE, na.strings = "", comment.char = "", encoding = "UTF-8"
    )
  })
  ref$metadata <- jsonlite::read_json(file.path(data_dir, "metadata.json"), simplifyVector = TRUE)
  ref$bundle_dir <- dirname(data_dir)
  class(ref) <- "planarsviz_cross_language"
  ref
}

# Display label per dataset: the structure's label, with " *" on any structure
# not from CCDB (only nyan1308), which every chart's caption explains.
planarsviz_cross_labels <- function(ref) {
  s <- ref$structures
  stats::setNames(ifelse(s$source == "ccdb", s$label, paste0(s$label, " *")), s$dataset)
}

planarsviz_cross_caption <- function(ref, extra = NULL) {
  paste(c(extra, "* not from CCDB (Chichewa)."), collapse = "\n")
}

planarsviz_cross_finish <- function(p, width, height) {
  attr(p, "planarsviz_size") <- c(width = width, height = height)
  attr(p, "planarsviz_units") <- "in"
  attr(p, "planarsviz_folder") <- ""
  p
}

planarsviz_cross_role_label <- c(
  all = "all tests pooled",
  syntax_side = "syntax side only",
  phonology_side = "phonology side only"
)

#' Tree-likeness across structures
#'
#' One row per structure: its observed number of maximal laminar families
#' divided by the median of the span-placement null (filled point; the bar is
#' that null's 5th-95th percentile, on the same scale), and by the median of
#' the weaker arbitrary-layers null (open point). Left of 1 means fewer
#' families, i.e. more tree-like, than chance gives. Rows are ordered by the
#' span-placement ratio. The caption gives the count below the median with its
#' sign-test p and Fisher's combined p, both caveated.
#'
#' @param ref A bundle from [read_planars_cross_language()].
#' @param role `"all"` (every test pooled), `"syntax_side"` or
#'   `"phonology_side"` -- which of each structure's test groups to compare.
#' @return A ggplot object with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`) and `planarsviz_folder` (`""`).
#' @export
plot_cross_language_tree_likeness <- function(ref, role = c("all", "syntax_side", "phonology_side")) {
  role <- match.arg(role)
  labels <- planarsviz_cross_labels(ref)
  d <- ref$family_count_tests[ref$family_count_tests$role == role, , drop = FALSE]
  sp <- d[d$null == "span_placement", , drop = FALSE]
  al <- d[d$null == "arbitrary_layers", , drop = FALSE]
  sp$label <- labels[sp$dataset]
  al$label <- labels[al$dataset]
  order <- sp$label[order(-sp$observed_ratio, sp$label)]
  sp$label <- factor(sp$label, levels = order)
  al$label <- factor(al$label, levels = order)
  sp$p_text <- sprintf("%.3f", sp$p_value_le_observed)
  al$p_text <- sprintf("%.3f", al$p_value_le_observed)

  pooled <- ref$pooled_tests[ref$pooled_tests$role == role, , drop = FALSE]
  describe <- function(null, name) {
    r <- pooled[pooled$null == null, , drop = FALSE]
    sprintf(
      "%s: %d of %d below the null median (%d above, %d on it); sign test p = %.2g; Fisher's combined p = %.2g.",
      name, r$n_below_median, r$n_structures, r$n_above_median, r$n_at_median, r$sign_test_p, r$fisher_p
    )
  }
  caption <- planarsviz_cross_caption(ref, c(
    describe("span_placement", "Span placement"),
    describe("arbitrary_layers", "Arbitrary layers"),
    paste(
      "The structures share test batteries, authors and in some cases language families,",
      "so neither figure is a test on independent cases."
    )
  ))

  lo <- min(c(sp$null_p05_ratio, sp$observed_ratio, al$observed_ratio))
  hi <- max(c(sp$null_p95_ratio, sp$observed_ratio, al$observed_ratio))
  p_x <- hi * 1.5
  p <- ggplot(sp, aes(y = label)) +
    geom_vline(xintercept = 1, colour = "grey45", linetype = "dashed") +
    geom_segment(aes(x = null_p05_ratio, xend = null_p95_ratio, yend = label),
      colour = "grey80", linewidth = 2.2, lineend = "round"
    ) +
    geom_point(data = al, aes(x = observed_ratio, shape = "Arbitrary layers"), size = 2.4, colour = "#D55E00") +
    geom_point(aes(x = observed_ratio, shape = "Span placement"), size = 2.6, colour = "#0072B2") +
    geom_text(aes(x = p_x, label = p_text), size = 3, hjust = 0) +
    geom_text(aes(x = p_x * 1.7, label = p_text), data = al, size = 3, hjust = 0, colour = "#D55E00") +
    annotate("text", x = p_x, y = length(order) + 0.9, label = "p placement", size = 3, hjust = 0) +
    annotate("text",
      x = p_x * 1.7, y = length(order) + 0.9, label = "p layers", size = 3, hjust = 0,
      colour = "#D55E00"
    ) +
    scale_x_log10(limits = c(lo / 1.1, p_x * 2.6), breaks = c(0.1, 0.2, 0.5, 1, 2, 5)) +
    scale_shape_manual(values = c("Span placement" = 16, "Arbitrary layers" = 1), name = NULL) +
    coord_cartesian(clip = "off") +
    labs(
      x = "Observed families ÷ null median (log scale; grey bar: span-placement null, 5th–95th percentile)",
      y = NULL,
      title = paste0("Are the structures more tree-like than chance? (", planarsviz_cross_role_label[[role]], ")"),
      subtitle = "Left of the dashed line: fewer laminar families than randomly placed spans give.",
      caption = caption
    ) +
    theme_bw() +
    theme(
      legend.position = "top", plot.caption = element_text(hjust = 0, size = 8),
      panel.grid.minor = element_blank()
    )
  planarsviz_cross_finish(p, 9, 8)
}

#' Family count against span count
#'
#' One point per structure: its number of distinct spans against its number
#' of maximal laminar families (log scale), shaped by planar type. The grey
#' bar at each point is the arbitrary-layers null's 5th-95th percentile for
#' that structure. Points are coloured by where they fall against it, and
#' only structures outside it (plus the one not from CCDB) are labelled.
#'
#' @param ref A bundle from [read_planars_cross_language()].
#' @return A ggplot object with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`) and `planarsviz_folder` (`""`).
#' @export
plot_cross_language_families_vs_size <- function(ref) {
  labels <- planarsviz_cross_labels(ref)
  d <- ref$family_count_tests[ref$family_count_tests$null == "arbitrary_layers" &
    ref$family_count_tests$role == "all", , drop = FALSE]
  d$planar_type <- ref$structures$planar_type[match(d$dataset, ref$structures$dataset)]
  d$source <- ref$structures$source[match(d$dataset, ref$structures$dataset)]
  d$label <- labels[d$dataset]
  d$where <- ifelse(d$observed_families < d$null_p05, "Below the null's 5th percentile",
    ifelse(d$observed_families > d$null_p95, "Above its 95th", "Within it")
  )
  d$where <- factor(d$where, levels = c("Below the null's 5th percentile", "Within it", "Above its 95th"))
  shown <- d[d$where != "Within it" | d$source != "ccdb", , drop = FALSE]
  # Labelled structures with the same family count get their labels stacked,
  # one line apart on the log axis, rather than run into each other. The
  # rightmost keeps its place, so a raised label never crosses a point.
  shown <- shown[order(shown$observed_families, -shown$n_spans, shown$label), , drop = FALSE]
  shown$line <- stats::ave(seq_len(nrow(shown)), shown$observed_families, FUN = seq_along) - 1
  shown$label_y <- shown$observed_families * 1.13^shown$line
  p <- ggplot(d, aes(x = n_spans, y = observed_families)) +
    geom_segment(aes(xend = n_spans, y = null_p05, yend = null_p95),
      colour = "grey82", linewidth = 2, lineend = "round"
    ) +
    geom_point(aes(shape = planar_type, colour = where), size = 2.8) +
    geom_text(data = shown, aes(y = label_y, label = label), size = 2.8, hjust = 0, nudge_x = 0.5) +
    scale_y_log10() +
    scale_colour_manual(
      values = c(
        "Below the null's 5th percentile" = "#0072B2", "Within it" = "grey30",
        "Above its 95th" = "#D55E00"
      ),
      name = "Against the arbitrary-layers null", drop = FALSE
    ) +
    scale_shape_manual(values = c(verbal = 16, nominal = 17), name = "Planar type") +
    scale_x_continuous(expand = expansion(mult = c(0.05, 0.3))) +
    labs(
      x = "Distinct spans", y = "Maximal laminar families (log scale)",
      title = "Families against size",
      subtitle = "Grey bar: 5th–95th percentile of the arbitrary-layers null for that structure.",
      caption = planarsviz_cross_caption(ref)
    ) +
    theme_bw() +
    theme(plot.caption = element_text(hjust = 0, size = 8), legend.position = "right")
  planarsviz_cross_finish(p, 9, 6)
}

#' Where conflicts fall relative to the morphosyntax/phonology divide
#'
#' One row per structure: the share of its conflicting span pairs that fall
#' wholly across the divide (one span purely syntax side, the other purely
#' phonology side; filled point), against the share of all its span pairs
#' that do (open point: what the share would be if conflicts ignored the
#' divide). The divide hypothesis predicts filled to the right of open. The
#' p-value is from shuffling the spans' sides around the fixed conflict list.
#' Structures with no span purely on one side cannot be tested, and are
#' listed at the bottom without points.
#'
#' @param ref A bundle from [read_planars_cross_language()].
#' @return A ggplot object with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`) and `planarsviz_folder` (`""`).
#' @export
plot_cross_language_divide <- function(ref) {
  labels <- planarsviz_cross_labels(ref)
  d <- ref$conflict_divide
  d$label <- labels[d$dataset]
  testable <- !is.na(d$expected_share_between) & d$expected_share_between > 0
  d$diff <- ifelse(testable, d$share_between - d$expected_share_between, -Inf)
  order <- d$label[order(d$diff, d$label)]
  d$label <- factor(d$label, levels = order)
  d$right_text <- ifelse(testable,
    sprintf("%d / %d   p = %.3f", d$n_between, d$n_conflict_pairs, d$p_value_ge_observed),
    ifelse(d$n_spans_phonology_only == 0, "no phonology-only span", "no syntax-only span")
  )
  t <- d[testable, , drop = FALSE]
  sides <- ref$metadata$sides
  side_text <- sprintf(
    "Syntax side: %s (CCDB); %s (Chichewa).\nPhonology side: %s (CCDB); %s (Chichewa).",
    paste(sides$ccdb$syntax_side$domain_types, collapse = ", "),
    paste(sides$chichewa$syntax_side$domain_types, collapse = ", "),
    paste(sides$ccdb$phonology_side$domain_types, collapse = ", "),
    paste(sides$chichewa$phonology_side$domain_types, collapse = ", ")
  )
  p <- ggplot(d, aes(y = label)) +
    geom_segment(data = t, aes(x = expected_share_between, xend = share_between, yend = label), colour = "grey70") +
    geom_point(data = t, aes(x = expected_share_between, shape = "If conflicts ignored the divide"), size = 2.4) +
    geom_point(data = t, aes(x = share_between, shape = "Observed"), size = 2.6, colour = "#0072B2") +
    geom_text(aes(x = 1.04, label = right_text), size = 2.9, hjust = 0) +
    annotate("text", x = 1.04, y = length(order) + 1.3, label = "across / all conflicts", size = 3, hjust = 0) +
    scale_x_continuous(
      limits = c(0, 1.5), breaks = seq(0, 1, 0.25), labels = scales::label_percent(),
      expand = expansion(mult = c(0.02, 0))
    ) +
    scale_shape_manual(values = c("Observed" = 16, "If conflicts ignored the divide" = 1), name = NULL) +
    coord_cartesian(clip = "off") +
    labs(
      x = "Share of conflicting span pairs that fall wholly across the divide", y = NULL,
      title = "Do conflicts fall across the morphosyntax/phonology divide?",
      subtitle = "Hypothesis (ii) predicts the blue point to the right of the open one.",
      caption = planarsviz_cross_caption(ref, c(
        side_text,
        "A span on both sides shares a side with anything, so its conflicts count as within a side.",
        "p: how often shuffling the spans' sides gives a share across the divide at least this high."
      ))
    ) +
    theme_bw() +
    theme(
      legend.position = "top", plot.caption = element_text(hjust = 0, size = 8),
      panel.grid.minor = element_blank()
    )
  planarsviz_cross_finish(p, 9, 8)
}

#' Which side is more tree-like, structure by structure
#'
#' One row per structure: the span-placement test's p-value for its
#' syntax-side tests and for its phonology-side tests, joined by a line. A low
#' p-value means that side's spans give fewer families than the same span
#' lengths placed at random. Rows are ordered by the syntax side's p-value.
#'
#' @param ref A bundle from [read_planars_cross_language()].
#' @return A ggplot object with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`) and `planarsviz_folder` (`""`).
#' @export
plot_cross_language_side_p <- function(ref) {
  labels <- planarsviz_cross_labels(ref)
  d <- ref$family_count_tests[ref$family_count_tests$null == "span_placement" &
    ref$family_count_tests$role != "all", , drop = FALSE]
  d$side <- factor(ifelse(d$role == "syntax_side", "Syntax side", "Phonology side"),
    levels = c("Syntax side", "Phonology side")
  )
  d$label <- labels[d$dataset]
  syn <- d[d$role == "syntax_side", , drop = FALSE]
  phon <- d[d$role == "phonology_side", , drop = FALSE]
  order <- syn$label[order(-syn$p_value_le_observed, syn$label)]
  d$label <- factor(d$label, levels = order)
  pairs <- data.frame(
    label = factor(syn$label, levels = order),
    syntax = syn$p_value_le_observed,
    phonology = phon$p_value_le_observed[match(syn$dataset, phon$dataset)]
  )
  n_lower <- sum(pairs$syntax < pairs$phonology)
  n_higher <- sum(pairs$syntax > pairs$phonology)
  p <- ggplot(d, aes(y = label)) +
    geom_vline(xintercept = 0.05, linetype = "dotted", colour = "grey40") +
    geom_segment(data = pairs, aes(x = syntax, xend = phonology, yend = label), colour = "grey70") +
    geom_point(aes(x = p_value_le_observed, colour = side), size = 2.4) +
    scale_colour_manual(values = c("Syntax side" = "#BC3C29", "Phonology side" = "#20845E"), name = NULL) +
    scale_x_continuous(limits = c(0, 1), breaks = c(0, 0.25, 0.5, 0.75, 1)) +
    labs(
      x = "Span-placement p-value (low: fewer families than the same spans placed at random)", y = NULL,
      title = "Which side is more tree-like?",
      subtitle = sprintf(
        "Syntax side lower in %d of %d structures, phonology side lower in %d.\nDotted line: p = 0.05.",
        n_lower, nrow(pairs), n_higher
      ),
      caption = planarsviz_cross_caption(ref, paste(
        "A side with few spans can hardly give fewer families than chance, so its p-value is near 1",
        "whatever its arrangement."
      ))
    ) +
    theme_bw() +
    theme(
      legend.position = "top", plot.caption = element_text(hjust = 0, size = 8),
      panel.grid.minor = element_blank()
    )
  planarsviz_cross_finish(p, 8, 7.5)
}

#' Boundary strength around the root
#'
#' A heatmap with one row per structure and positions numbered relative to
#' the root (0), left edges and right edges as two panels. Colour is summed
#' boundary strength scaled by that structure's own largest value, so rows are
#' comparable in shape rather than size. A dot marks a position whose jump in
#' strength is higher than chance (boundary-strength test, p < 0.05, not
#' corrected for the number of positions).
#'
#' @param ref A bundle from [read_planars_cross_language()].
#' @return A ggplot object with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`) and `planarsviz_folder` (`""`).
#' @export
plot_cross_language_edges <- function(ref) {
  labels <- planarsviz_cross_labels(ref)
  d <- ref$boundary_profile
  d$label <- factor(labels[d$dataset], levels = rev(sort(unique(labels))))
  d$side <- factor(ifelse(d$side == "left", "Left edges", "Right edges"), levels = c("Left edges", "Right edges"))
  sig <- d[d$jump_significant == "y", , drop = FALSE]
  p <- ggplot(d, aes(x = relative_position, y = label)) +
    geom_tile(aes(fill = scaled), colour = "white", linewidth = 0.2) +
    geom_point(data = sig, size = 0.9, colour = "#D55E00") +
    geom_vline(xintercept = c(-0.5, 0.5), colour = "grey30", linewidth = 0.3) +
    facet_wrap(~side, nrow = 1) +
    scale_fill_gradient(
      low = "#F4F4F4", high = "#08306B", limits = c(0, 1),
      name = "Boundary strength\n(share of the\nstructure's largest)",
      # Drawn as rectangles, not an image: when this chart went through the
      # Quartz PDF device, the image came out upside down in the PNG.
      guide = guide_colourbar(raster = FALSE)
    ) +
    scale_x_continuous(breaks = seq(-40, 40, 5)) +
    labs(
      x = "Position relative to the root (root = 0, between the vertical lines)", y = NULL,
      title = "Where do strong edges fall, relative to the root?",
      subtitle = "Orange dot: jump in strength higher than chance at that position (p < 0.05, uncorrected).",
      caption = planarsviz_cross_caption(ref)
    ) +
    theme_bw() +
    theme(
      panel.grid = element_blank(), plot.caption = element_text(hjust = 0, size = 8),
      strip.background = element_rect(fill = "grey92")
    )
  planarsviz_cross_finish(p, 13, 7)
}

#' The most convergent spans around the root
#'
#' For each structure, its spans picked out by the most tests (up to three
#' convergence levels, ties kept, and only spans picked out by at least
#' `min_tests` tests), drawn as segments on a root-relative axis, thicker the
#' more tests pick them out. The grey band is the structure's full extent.
#' The Word hypothesis predicts a recurring small span around the root.
#'
#' @param ref A bundle from [read_planars_cross_language()].
#' @param min_tests Leave out spans picked out by fewer tests than this.
#'   Default 2: a span one test picks out has converged with nothing.
#' @return A ggplot object with attributes `planarsviz_size`,
#'   `planarsviz_units` (`"in"`) and `planarsviz_folder` (`""`).
#' @export
plot_cross_language_convergence <- function(ref, min_tests = 2L) {
  labels <- planarsviz_cross_labels(ref)
  s <- ref$structures
  s$label <- labels[s$dataset]
  d <- ref$convergent_spans[ref$convergent_spans$convergence >= min_tests, , drop = FALSE]
  d$label <- labels[d$dataset]
  d <- d[order(d$dataset, d$convergence_rank, d$size, d$left), , drop = FALSE]
  d$slot <- stats::ave(seq_len(nrow(d)), d$dataset, FUN = seq_along)
  none <- s[!s$dataset %in% d$dataset, , drop = FALSE]
  none$slot <- 1
  extent <- data.frame(
    label = s$label, xmin = 1 - s$root_position - 0.5, xmax = s$n_positions - s$root_position + 0.5
  )
  n_slots <- stats::aggregate(slot ~ label, data = rbind(d[, c("label", "slot")], none[, c("label", "slot")]), max)
  extent$ymax <- n_slots$slot[match(extent$label, n_slots$label)] + 0.5
  p <- ggplot(d) +
    geom_rect(
      data = extent, aes(xmin = xmin, xmax = xmax, ymin = 0.5, ymax = ymax),
      fill = "grey93", inherit.aes = FALSE
    ) +
    geom_vline(xintercept = 0, colour = "grey40", linetype = "dashed") +
    geom_segment(aes(
      x = relative_left - 0.4, xend = relative_right + 0.4, y = slot, yend = slot,
      linewidth = convergence
    ), colour = "#08306B", lineend = "butt") +
    geom_text(aes(x = relative_right + 0.7, y = slot, label = convergence), size = 2.3, hjust = 0) +
    geom_text(
      data = none, aes(x = 0, y = slot, label = paste("no span picked out by", min_tests, "or more tests")),
      size = 2.5, colour = "grey40", hjust = 0.5
    ) +
    facet_grid(label ~ ., scales = "free_y", space = "free_y", switch = "y") +
    scale_linewidth_continuous(range = c(0.8, 3.5), name = "Tests picking\nout the span") +
    scale_y_continuous(breaks = NULL) +
    scale_x_continuous(breaks = seq(-40, 40, 5)) +
    labs(
      x = "Position relative to the root (root = 0)", y = NULL,
      title = "Is there a recurring small, highly convergent span around the root?",
      subtitle = paste0(
        "Each structure's most convergent spans (top three levels, at least ", min_tests,
        " tests);\nthe number is how many tests pick the span out. Grey: the whole structure."
      ),
      caption = planarsviz_cross_caption(ref)
    ) +
    theme_bw() +
    theme(
      strip.text.y.left = element_text(angle = 0, hjust = 1, size = 8),
      strip.background = element_blank(), strip.placement = "outside",
      panel.border = element_rect(colour = "grey75", fill = NA, linewidth = 0.3),
      panel.spacing.y = unit(1, "pt"), panel.grid.minor = element_blank(),
      plot.caption = element_text(hjust = 0, size = 8)
    )
  planarsviz_cross_finish(p, 11, 13)
}
