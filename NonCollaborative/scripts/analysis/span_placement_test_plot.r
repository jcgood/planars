# Span-placement permutation test, broken down by domain class and bundle:
# one panel per group, each showing that group's own null distribution of
# family counts (from randomly re-placing its own spans' lengths -- see
# span_placement_test.py's module docstring) against its own real observed
# count.
#
# Reads nyan1308_span_placement_test.tsv (one row per group: n_spans,
# observed count, null summary stats, p-value) and
# nyan1308_span_placement_null_tally.tsv (group, family_count, n -- a
# tally, not raw draws). Does not re-run the permutation.
#
# Unlike fragmentation_test_plot.r, panels here do NOT share one x-axis.
# There the shared scale was the point (showing that a "big" class was only
# big because it had more tests). Here the absolute family count isn't
# comparable across groups of very different span counts to begin with (6
# families means something different for an 11-span group than a 20-span
# one) -- the comparable quantity is each group's own p-value, which is
# already a single number per panel. facet_wrap(scales="free") lets each
# group's own null distribution read clearly at its own natural scale on
# BOTH axes -- not just x: a 3-span group (intonational) has almost no
# distinct family-count values, so one bar can absorb a large share of all
# 5000 draws; sharing the y-axis with a 26-span group's much flatter,
# wider-spread distribution would squash every other panel toward zero
# height and, worse, silently misplace each panel's own p-value annotation
# (computed relative to that panel's own local peak, but rendered against
# the dominant panel's shared scale) -- confirmed happening, not just a
# theoretical risk, in the first free_x-only render.
#
# Design notes (shared with span_placement_test_plot.r's single-group
# ancestor): one house color per call (default #0072B2, the neutral shade
# used when many groups share one chart -- a per-group palette across nine
# very different panels would just be noise); observed marked as a black
# dashed line, p-value annotated in-panel, no title, self-locating path
# resolution (works from anywhere, not just scripts/analysis/ -- see the
# module comment in the single-group version and
# docs/PLANARSVIZ_LIBRARY_PROGRESS.md's note on why that convention exists).
# The two single-bundle files below pass `fill_color` explicitly, matching
# that bundle's own color from BUNDLES in planars_groupings.py -- the same
# color used for it everywhere else (its own laminar-forest ghost overlay,
# the fragmentation-test violin) rather than a new one invented here.
#
# Refactored into one function so a filtered subset (e.g. one bundle
# someone is presenting on its own) is a second call with a different
# `groups`/output name, not a copy of the whole script -- same reasoning as
# boundary_strength_plot.r's plot_boundary_strength() before it was ported.
#
# Run from anywhere:
#   Rscript NonCollaborative/scripts/analysis/span_placement_test_plot.r

library(ggplot2)

script_dir <- local({
  file_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
  if (length(file_arg)) dirname(normalizePath(sub("^--file=", "", file_arg[[1]]))) else getwd()
})
output_dir <- normalizePath(file.path(script_dir, "..", "..", "results", "counts-and-chance"), mustWork = TRUE)

all_summary <- read.delim(file.path(output_dir, "nyan1308_span_placement_test.tsv"),
                           stringsAsFactors = FALSE, check.names = FALSE)
all_tally <- read.delim(file.path(output_dir, "nyan1308_span_placement_null_tally.tsv"),
                         stringsAsFactors = FALSE, check.names = FALSE)

# Display labels: title-case for the five plain domain types, "All" for the
# pooled group, and the bundles' own display strings (from BUNDLES in
# planars_groupings.py) -- matching fragmentation_test_plot.r's convention.
display_labels <- c(
  all = "All (pooled)",
  morphosyntactic = "Morphosyntactic",
  phonological = "Phonological",
  tonosegmental = "Tonosegmental",
  intonational = "Intonational",
  length = "Length",
  phonologylike = "Phonology-like",
  syntaxlike = "Syntax-like",
  syntaxlike_notono = "Syntax-like (no Tono)"
)

plot_span_placement <- function(groups, output_name, ncol, width, height, fill_color = "#0072B2",
                                 y_top_pad = 0.38, annotation_size = 3.1, label_y_frac = 1.35,
                                 label_hjust = -0.05, x_left_pad = 0.05,
                                 axis_text_size = 8.8, axis_title_size = 11, strip_text_size = 9) {
  # Defaults (8.8, 11, 9) reproduce theme_bw(base_size=11)'s own automatic
  # axis text/title sizes and the strip text size this chart already used,
  # so the 9-group chart's pixel output is unaffected unless these are
  # passed explicitly -- same reasoning as every other parameter here.
  summary_df <- all_summary[all_summary$group %in% groups, , drop = FALSE]
  tally <- all_tally[all_tally$group %in% groups, , drop = FALSE]

  group_levels <- groups[groups %in% summary_df$group]
  summary_df$group <- factor(summary_df$group, levels = group_levels, labels = display_labels[group_levels])
  tally$group <- factor(tally$group, levels = group_levels, labels = display_labels[group_levels])

  # Weighted density per group, rescaled to that group's own histogram peak --
  # same underlay convention as the single-group version, computed once per
  # group since each has its own support/bandwidth needs.
  density_list <- lapply(split(tally, tally$group), function(sub) {
    peak_height <- max(sub$n)
    bw <- max(1, diff(range(sub$family_count)) / 15)
    dens <- density(sub$family_count, weights = sub$n / sum(sub$n), bw = bw,
                     from = min(sub$family_count) - 1, to = max(sub$family_count) + 1, n = 256)
    data.frame(group = sub$group[1], x = dens$x, y = dens$y * peak_height / max(dens$y))
  })
  density_df <- do.call(rbind, density_list)

  peak_by_group <- aggregate(n ~ group, data = tally, FUN = max)
  names(peak_by_group) <- c("group", "peak_height")
  summary_df <- merge(summary_df, peak_by_group, by = "group")
  summary_df$annotation <- sprintf("obs = %d\np(<=obs) = %.3f", summary_df$observed_families, summary_df$p_value_le_observed)
  # label_y_frac is independent of y_top_pad -- the two used to be coupled
  # (label position derived from the padding), which quietly changed the
  # 9-group chart's own label position when y_top_pad was parameterized,
  # breaking its pixel-identical-to-committed guarantee. Default 1.35
  # reproduces that original, unparameterized behavior exactly. The two
  # single-bundle calls pass a smaller fraction so the label sits within
  # the tightened axis instead of requiring headroom above the peak --
  # verified by rendering, not just computed, that this stays clear of the
  # bars (the label's x position is `observed`, away from each panel's own
  # peak x, where the local bar height is well under this fraction).
  summary_df$label_y <- summary_df$peak_height * label_y_frac

  p <- ggplot() +
    geom_col(data = tally, aes(x = family_count, y = n),
             fill = fill_color, alpha = 0.55, width = 1, color = NA) +
    geom_line(data = density_df, aes(x = x, y = y), color = fill_color, linewidth = 0.8) +
    geom_vline(data = summary_df, aes(xintercept = observed_families),
               linetype = "dashed", color = "black", linewidth = 0.7) +
    # label_hjust default (-0.05) extends the label rightward from the
    # dashed line, same as the original 9-group chart -- there, observed
    # sits well inside comfortable headroom above the peak, no overlap.
    # The two single-bundle calls below pass 1.05 (right-aligned, ending
    # just left of the line) instead: at their larger annotation_size and
    # tighter y_top_pad, a right-extending label ran into the bars
    # climbing toward the peak, and bars to observed's LEFT are shorter
    # (further down the null's left tail), leaving clear room there.
    # Left-aligned is NOT safe as a blanket default -- several groups in
    # the 9-panel chart have observed sitting right at their own panel's
    # axis minimum (e.g. morphosyntactic, syntax-like), so a left-extending
    # label there runs off the panel edge and gets clipped; confirmed
    # happening, not just a theoretical risk, before this was made
    # per-call rather than global.
    geom_text(data = summary_df, aes(x = observed_families, y = label_y, label = annotation),
              hjust = label_hjust, vjust = 1, size = annotation_size, color = "black") +
    facet_wrap(~ group, scales = "free", ncol = ncol) +
    scale_x_continuous(expand = expansion(mult = c(x_left_pad, 0.05))) +
    scale_y_continuous(expand = expansion(mult = c(0, y_top_pad))) +
    labs(
      x = "Number of maximal laminar families (that group's own spans, same lengths, random positions)",
      y = "Permutations producing that count"
    ) +
    theme_bw(base_size = 11) +
    theme(
      strip.background = element_rect(fill = "grey90", color = NA),
      strip.text = element_text(face = "bold", size = strip_text_size),
      axis.text = element_text(size = axis_text_size),
      axis.title = element_text(size = axis_title_size),
      panel.grid.minor = element_blank(),
      plot.margin = margin(t = 10, r = 12, b = 10, l = 10)
    )

  ggsave(file.path(output_dir, output_name), p, device = "pdf", width = width, height = height, units = "in")
}

# All nine groups.
plot_span_placement(
  groups = c("all", "morphosyntactic", "phonological", "tonosegmental", "intonational",
             "length", "phonologylike", "syntaxlike", "syntaxlike_notono"),
  output_name = "nyan1308_span_placement_test_by_group_plot.pdf",
  ncol = 3, width = 11, height = 9
)

# Syntax-like and phonology-like on their own, one file each -- order
# flipped from the first (combined) version of this pair: syntax-like
# first, phonology-like second. Colors match each bundle's own
# laminar-forest ghost overlay (BUNDLES in planars_groupings.py), not the
# neutral #0072B2 used above where nine groups share one chart. Tight top
# padding (6%, vs. the 9-group chart's 38%) so the axis hugs the data
# instead of reserving headroom purely for the label, and a larger
# annotation size (5, vs. 3.1) -- both per request, for a chart meant to
# stand alone rather than sit packed into a 3x3 grid.
plot_span_placement(
  groups = "syntaxlike",
  output_name = "nyan1308_span_placement_test_syntaxlike_plot.pdf",
  ncol = 1, width = 9, height = 5.5, fill_color = "#BC3C29",
  y_top_pad = 0.06, annotation_size = 5, label_y_frac = 0.9,
  label_hjust = 1.05, x_left_pad = 0.14,
  axis_text_size = 13, axis_title_size = 14, strip_text_size = 15
)
plot_span_placement(
  groups = "phonologylike",
  output_name = "nyan1308_span_placement_test_phonologylike_plot.pdf",
  ncol = 1, width = 9, height = 5.5, fill_color = "#0072B5",
  label_hjust = 1.05, x_left_pad = 0.14,
  y_top_pad = 0.06, annotation_size = 5, label_y_frac = 0.9,
  axis_text_size = 13, axis_title_size = 14, strip_text_size = 15
)
