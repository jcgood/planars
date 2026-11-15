#!/usr/bin/env Rscript
# Slide figure: conflict density across every stretch of nyan1308's planar
# structure, and the conflict each position brings in, from
# laminar/resolution_profile.py (plan decision 11). A one-off for a talk, not
# one of the package's charts (planned: docs/laminar-analysis-progress.md,
# "Domain support and resolution"). Companion to nyan1308_resolution_profile.R.
#
# Two panels:
# - Conflict density against chance: each tile is one stretch [left, right]
#   (left edge down the side, right edge along the bottom), coloured by the
#   share of pairs of domains within it that conflict, less the average over
#   5000 random placements of the same domain lengths. Orange is more
#   conflict than chance, green less; a dot marks p < 0.05 for more
#   (uncorrected; nested stretches share domains, so a map, not tests). Grey:
#   fewer than two domains, no density.
# - Conflict each position brings in: for every one-position step that adds
#   a position, the marginal conflict (of the pairs the step adds, the share
#   that conflict) less chance's for the same step, averaged by the position
#   added; the bar runs from the lowest to the highest step. Separately for
#   a stretch growing rightward (position added at its right edge) and
#   leftward. Positions whose steps add no pair are left out.
# The caption gives the quantal test (nyan1308_conflict_quantal.tsv).
#
# Run from the repository root (where .Rprofile sets up the pinned packages),
# after python -m laminar.resolution_profile:
#   Rscript NonCollaborative/scripts/slides/nyan1308_conflict_profile.R
# Writes NonCollaborative/results/nyan1308/slides/
#   nyan1308_conflict_profile.pdf / .png  (16 x 9 in; png 3840 x 2160)

results <- "NonCollaborative/results/nyan1308/counts-and-chance"
profile_path <- file.path(results, "nyan1308_resolution_profile.tsv")
positions_path <- file.path(results, "nyan1308_resolution_positions.tsv")
quantal_path <- file.path(results, "nyan1308_conflict_quantal.tsv")
labels_path <- "NonCollaborative/planar_tables/display_labels_nyan1308.tsv"
out_dir <- "NonCollaborative/results/nyan1308/slides"
out_stem <- "nyan1308_conflict_profile"
if (!file.exists(quantal_path)) {
  stop("Run this from the repository root, after python -m laminar.resolution_profile.", call. = FALSE)
}

suppressPackageStartupMessages({
  library(ggplot2)
  library(patchwork)
})

d <- utils::read.delim(profile_path)
d$is_domain <- d$is_domain == "True"
d$excess <- d$conflict_density - d$null_conflict_density_mean
d$significant <- !is.na(d$p_conflict_density_ge) & d$p_conflict_density_ge < 0.05
domains <- d[d$is_domain, ]

pos <- utils::read.delim(positions_path)
pos <- pos[pos$n_steps_scored > 0, ]
pos$side <- factor(ifelse(pos$side == "right", "growing rightward", "growing leftward"),
                   levels = c("growing rightward", "growing leftward"))
labels <- utils::read.delim(labels_path)
q <- utils::read.delim(quantal_path)

n <- max(d$right)
font <- "Gill Sans"
grid_theme <- theme_minimal(base_size = 18, base_family = font) +
  theme(panel.grid = element_blank(),
        plot.title = element_text(size = 22),
        legend.position = "bottom",
        legend.key.width = grid::unit(2.2, "cm"),
        legend.title = element_text(size = 15, vjust = 0.85))

limit <- max(abs(d$excess), na.rm = TRUE)
p_grid <- ggplot(d, aes(x = right, y = left)) +
  geom_tile(aes(fill = excess), colour = "white", linewidth = 0.6) +
  geom_tile(data = domains, width = 1, height = 1, fill = NA, colour = "black", linewidth = 0.9) +
  geom_point(data = d[d$significant, ], size = 1.6, colour = "black") +
  scale_fill_gradient2("Conflict density less chance", low = "#1B7837", mid = "#F2F2F2", high = "#E66101",
                       midpoint = 0, limits = c(-limit, limit), na.value = "#BDBDBD") +
  scale_x_continuous("Right edge", breaks = 2:n, expand = c(0, 0)) +
  scale_y_reverse("Left edge", breaks = 1:(n - 1), expand = c(0, 0)) +
  coord_equal(clip = "off") +
  grid_theme +
  ggtitle("Conflict density against chance")

side_colours <- c("growing rightward" = "#E66101", "growing leftward" = "#5E3C99")
dodge <- position_dodge(width = 0.6)
p_steps <- ggplot(pos, aes(x = added, y = mean_excess_marginal, colour = side)) +
  annotate("rect", xmin = -Inf, xmax = Inf, ymin = 0, ymax = Inf, fill = "#E66101", alpha = 0.06) +
  annotate("rect", xmin = -Inf, xmax = Inf, ymin = -Inf, ymax = 0, fill = "#1B7837", alpha = 0.06) +
  geom_hline(yintercept = 0, colour = "grey40") +
  geom_linerange(aes(ymin = min_excess_marginal, ymax = max_excess_marginal),
                 position = dodge, linewidth = 1.1, alpha = 0.6) +
  geom_point(position = dodge, size = 4) +
  scale_colour_manual(NULL, values = side_colours) +
  scale_x_continuous("Position added", breaks = labels$position,
                     labels = paste(labels$position, labels$label),
                     limits = c(0.5, n + 0.5), expand = c(0, 0)) +
  scale_y_continuous("Conflict it brings in, less chance", limits = c(-0.7, 0.85)) +
  annotate("text", x = 0.8, y = 0.82, label = "more conflict than chance", hjust = 0,
           family = font, size = 5, colour = "#B04A00") +
  annotate("text", x = 0.8, y = -0.67, label = "less conflict than chance: new domains nest", hjust = 0,
           family = font, size = 5, colour = "#1B7837") +
  theme_minimal(base_size = 18, base_family = font) +
  theme(panel.grid.minor = element_blank(),
        panel.grid.major.x = element_blank(),
        axis.text.x = element_text(size = 12, angle = 90, hjust = 1, vjust = 0.5),
        plot.title = element_text(size = 22),
        legend.position = "bottom") +
  ggtitle("Conflict each position brings in")

caption <- paste(
  "Left: each tile is a stretch of positions; black outlines are the 26 domains the tests found; grey holds fewer than two domains.",
  if (any(d$significant)) {
    "Dots: more conflict than 5000 random placements of the same domain lengths, p < 0.05 (uncorrected)."
  } else {
    "No single stretch has more conflict than 5000 random placements of the same domain lengths at p < 0.05 (uncorrected)."
  },
  sprintf("Right: points are means over the steps that add the position; bars run from lowest to highest. Quantal test: conflict changes in jumps more than chance (Gini %.2f against %.2f, p = %.3f).",
          q$gini_observed, q$null_gini_mean, q$p_gini_ge),
  sep = "\n")
p <- p_grid + p_steps + plot_layout(widths = c(1, 1.15)) +
  plot_annotation(caption = caption,
                  theme = theme(plot.caption = element_text(family = font, size = 14, hjust = 0)))

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
pdf_path <- file.path(out_dir, paste0(out_stem, ".pdf"))
suppressMessages(ggsave(pdf_path, p, width = 16, height = 9, units = "in",
                        device = function(filename, ...) grDevices::quartz(file = filename, type = "pdf", ...)))
system2("pdftocairo", c("-png", "-r", "240", "-singlefile", shQuote(pdf_path),
                        shQuote(file.path(out_dir, out_stem))))
cat("Wrote", pdf_path, "and the .png\n")
