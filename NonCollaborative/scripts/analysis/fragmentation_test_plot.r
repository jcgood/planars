# Fragmentation permutation test, visualized: for each domain class and each
# bundle, a horizontal violin of its null distribution (family count under
# 5000 permutations of the Domain_Type labels, own test count held fixed --
# see class_fragmentation_test.py's module docstring for the full null-model
# writeup) with the group's OWN observed family count marked as a filled dot.
# Reads nyan1308_fragmentation_null_draws.tsv (long format: group, kind,
# family_count) and the two summary TSVs (class/bundle) for observed values,
# colors and p-values -- this script does not re-run the permutation itself.
#
# The story the chart exists to tell: tonosegmental's raw family count (9,
# the tallest bar in nyan1308_tree_count_by_class.pdf) looks like the most
# fragmented class on that chart alone, but its dot here sits well to the
# LEFT of its own null violin -- a random same-sized sample of tests
# typically produces far more families (17), not fewer. The dot-vs-violin
# relationship is the finding; the bar chart alone can't show it because it
# has no sense of "fragmented relative to what."
#
# Design notes:
#  - Classes and bundles share one x-axis (family count) on purpose, even
#    though bundles run to higher counts (more underlying tests) -- the
#    point is to see the raw scale honestly, not to normalize it away. Two
#    stacked panels via facet_grid(kind ~ ., scales="free_y", space="free_y")
#    keep the panels visually separate (5 rows vs. 3 rows, different height)
#    while keeping that one shared, comparable x-axis. When a filtered call
#    only has one kind left (e.g. two bundles), faceting is dropped entirely
#    rather than drawing a single, pointless strip label.
#  - Each group's violin AND its observed dot use that group's own house
#    color (from CLASS_COLORS / BUNDLES in the Python side, carried through
#    the `color` column in the summary TSVs) -- no new palette invented here.
#  - Rows within each panel ordered by n_tests ascending (bottom to top),
#    matching the "least to most" convention the project's other horizontal
#    bar charts use.
#  - p-value printed at a fixed x position to the right of the shared axis
#    range (not next to each violin's own right edge, which would stagger
#    unreadably given how different the panels' ranges are) -- same
#    plain-language framing as the module docstring: "p(<= observed)",
#    the same "small p = unusually laminar" convention span_placement_test.py
#    uses, so a small number always reads as more tree-like regardless of
#    which of the two permutation scripts produced it.
#  - No title -- kept out entirely per this project's established
#    convention (see the archived boundary_strength_plot.r's notes on why).
#
# Refactored into one function so a filtered subset (e.g. just the two
# bundles someone is presenting) is a second call with a different
# `groups`/output name, not a copy of the whole script -- same reasoning as
# span_placement_test_plot.r's plot_span_placement().
#
# Run from anywhere:
#   Rscript NonCollaborative/scripts/analysis/fragmentation_test_plot.r

library(ggplot2)

# Resolve results/ from this file's own location, not the working directory,
# so the command above works from the repo root, from NonCollaborative/, or
# from this directory.
script_dir <- local({
  file_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
  if (length(file_arg)) dirname(normalizePath(sub("^--file=", "", file_arg[[1]]))) else getwd()
})
output_dir <- normalizePath(file.path(script_dir, "..", "..", "results"), mustWork = TRUE)

class_summary <- read.delim(file.path(output_dir, "nyan1308_class_fragmentation_test.tsv"),
                             stringsAsFactors = FALSE, check.names = FALSE)
class_summary$kind <- "class"

bundle_summary <- read.delim(file.path(output_dir, "nyan1308_bundle_fragmentation_test.tsv"),
                              stringsAsFactors = FALSE, check.names = FALSE)
bundle_summary$kind <- "bundle"

all_summary <- rbind(class_summary, bundle_summary)

all_null_draws <- read.delim(file.path(output_dir, "nyan1308_fragmentation_null_draws.tsv"),
                              stringsAsFactors = FALSE, check.names = FALSE)

# Display labels: title-case for the five plain domain types; the bundles'
# own display strings (from BUNDLES in planars_groupings.py) hardcoded here
# since the summary TSV only carries the bare group id, not the display
# label -- matching how boundary_strength_plot.r hardcodes position_labels.
display_labels <- c(
  morphosyntactic = "Morphosyntactic",
  phonological = "Phonological",
  tonosegmental = "Tonosegmental",
  intonational = "Intonational",
  length = "Length",
  phonologylike = "Phonology-like",
  syntaxlike = "Syntax-like",
  syntaxlike_notono = "Syntax-like (no Tono)"
)

plot_fragmentation_test <- function(groups, output_name, width, height) {
  summary_df <- all_summary[all_summary$group %in% groups, , drop = FALSE]
  null_draws <- all_null_draws[all_null_draws$group %in% groups, , drop = FALSE]

  # Order rows bottom-to-top by n_tests ascending, within each kind block --
  # the factor's global level order determines each facet's own row order
  # under facet_grid(scales="free_y"), so building it once here is enough.
  summary_df <- summary_df[order(summary_df$kind == "bundle", summary_df$n_tests), ]
  group_levels <- summary_df$group
  summary_df$group <- factor(summary_df$group, levels = group_levels)
  summary_df$kind <- factor(summary_df$kind, levels = c("class", "bundle"))

  null_draws$group <- factor(null_draws$group, levels = group_levels)
  null_draws$kind <- factor(null_draws$kind, levels = c("class", "bundle"))

  color_map <- setNames(summary_df$color, as.character(summary_df$group))
  multi_kind <- length(unique(summary_df$kind)) > 1

  # p-value label position: one fixed x per panel (or one x overall when
  # there's only one panel), just past the widest data (null draws or
  # observed dot, whichever is larger) -- a single global position across
  # panels of very different ranges would either crowd the smaller one or
  # sit oddly far from the larger one.
  group_col <- if (multi_kind) "kind" else NULL
  if (multi_kind) {
    null_max_by <- aggregate(family_count ~ kind, data = null_draws, FUN = max)
    names(null_max_by) <- c("kind", "null_max")
    obs_max_by <- aggregate(observed_families ~ kind, data = summary_df, FUN = max)
    names(obs_max_by) <- c("kind", "obs_max")
    panel_max <- merge(null_max_by, obs_max_by, by = "kind")
    panel_max$label_x <- pmax(panel_max$null_max, panel_max$obs_max) * 1.08
    summary_df <- merge(summary_df, panel_max[, c("kind", "label_x")], by = "kind")
  } else {
    label_x <- max(max(null_draws$family_count), max(summary_df$observed_families)) * 1.08
    summary_df$label_x <- label_x
  }

  p <- ggplot() +
    geom_violin(
      data = null_draws, aes(x = family_count, y = group, fill = group),
      bw = 1, scale = "width", width = 0.75, alpha = 0.45, color = NA
    ) +
    geom_point(
      data = summary_df, aes(x = observed_families, y = group, fill = group),
      shape = 21, size = 4, color = "black", stroke = 0.9
    ) +
    geom_text(
      data = summary_df,
      aes(x = label_x, y = group, label = sprintf("p=%.3f", p_value_le_observed)),
      hjust = 0, size = 3.6, color = "black"
    ) +
    scale_fill_manual(values = color_map, guide = "none") +
    scale_y_discrete(labels = display_labels) +
    scale_x_continuous(expand = expansion(mult = c(0.02, 0.16))) +
    coord_cartesian(clip = "off") +
    labs(
      x = "Number of maximal laminar families (violin: permuted null; dot: observed)",
      y = NULL
    ) +
    theme_bw(base_size = 12) +
    theme(
      strip.background = element_rect(fill = "grey90", color = NA),
      strip.text = element_text(face = "bold"),
      panel.grid.minor = element_blank(),
      plot.margin = margin(t = 10, r = 60, b = 10, l = 10)
    )

  if (multi_kind) {
    p <- p + facet_grid(kind ~ ., scales = "free_y", space = "free_y",
                         labeller = as_labeller(c(class = "Domain type", bundle = "Bundle")))
  }

  ggsave(file.path(output_dir, output_name), p, device = "pdf", width = width, height = height, units = "in")
}

# All five domain types and all three bundles.
plot_fragmentation_test(
  groups = c("morphosyntactic", "phonological", "tonosegmental", "intonational", "length",
             "phonologylike", "syntaxlike", "syntaxlike_notono"),
  output_name = "nyan1308_fragmentation_test_plot.pdf",
  width = 10, height = 6.5
)

# Just the two bundles someone is presenting on their own.
plot_fragmentation_test(
  groups = c("phonologylike", "syntaxlike"),
  output_name = "nyan1308_fragmentation_test_syntax_phon_plot.pdf",
  width = 9, height = 3.2
)
