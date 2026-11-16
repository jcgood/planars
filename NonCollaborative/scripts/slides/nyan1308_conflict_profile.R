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
# - Where conflict lies: at each juncture between two positions, the share
#   of the conflicting pairs that span it (a pair spans the junctures inside
#   its smallest common stretch; each pair counted once), against the same
#   share in 5000 random placements (mean and 90% band). A wall is a
#   position where the share changes beyond what chance's largest change
#   reaches in 95% of placements (dashed line); a position whose change is
#   beyond chance there alone (uncorrected p < 0.05) is shaded orange.
# The caption gives the quantal test (nyan1308_conflict_quantal.tsv).
#
# Run from the repository root (where .Rprofile sets up the pinned packages),
# after python -m laminar.resolution_profile:
#   Rscript NonCollaborative/scripts/slides/nyan1308_conflict_profile.R
# Writes NonCollaborative/results/nyan1308/slides/
#   nyan1308_conflict_profile.pdf / .png  (16 x 9 in; png 3840 x 2160)

results <- "NonCollaborative/results/nyan1308/counts-and-chance"
profile_path <- file.path(results, "nyan1308_resolution_profile.tsv")
junctures_path <- file.path(results, "nyan1308_conflict_junctures.tsv")
quantal_path <- file.path(results, "nyan1308_conflict_quantal.tsv")
labels_path <- "NonCollaborative/planar_tables/display_labels_nyan1308.tsv"
out_dir <- "NonCollaborative/results/nyan1308/slides"
out_stem <- "nyan1308_conflict_profile"
if (!file.exists(junctures_path)) {
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

jn <- utils::read.delim(junctures_path)
jn$x <- jn$left_position + 0.5
labels <- utils::read.delim(labels_path)
q <- utils::read.delim(quantal_path)
# Walls: positions whose change in share is beyond chance's 95th-percentile
# largest change (corrected for looking at every position). Steep: the
# change is beyond chance at that position alone (uncorrected p < 0.05).
walls <- jn[!is.na(jn$excess_change) & abs(jn$excess_change) > q$null_largest_hi, ]
steep <- jn[!is.na(jn$p_abs_excess_ge) & jn$p_abs_excess_ge < 0.05, ]

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

p_steps <- ggplot(jn, aes(x = x)) +
  geom_rect(data = steep, aes(xmin = position_passed - 0.5, xmax = position_passed + 0.5),
            ymin = -Inf, ymax = Inf, fill = "#E66101", alpha = 0.13, inherit.aes = FALSE) +
  geom_vline(data = walls, aes(xintercept = position_passed), colour = "#E66101",
             linewidth = 1, linetype = "dashed") +
  geom_ribbon(aes(ymin = null_share_lo, ymax = null_share_hi), fill = "grey80", alpha = 0.7) +
  geom_line(aes(y = null_share_mean), colour = "grey45", linewidth = 0.9) +
  geom_line(aes(y = share), colour = "black", linewidth = 1.2) +
  geom_point(aes(y = share), colour = "black", size = 3) +
  geom_text(data = walls, aes(x = position_passed, y = 1.04, label = paste("wall at", position_passed)),
            family = font, size = 5.5, colour = "#B04A00") +
  scale_x_continuous("Position", breaks = labels$position,
                     labels = paste(labels$position, labels$label),
                     limits = c(0.5, n + 0.5), expand = c(0, 0)) +
  scale_y_continuous("Share of conflicting pairs spanning the juncture",
                     limits = c(0, 1.07), breaks = seq(0, 1, 0.25)) +
  theme_minimal(base_size = 18, base_family = font) +
  theme(panel.grid.minor = element_blank(),
        panel.grid.major.x = element_blank(),
        axis.text.x = element_text(size = 12, angle = 90, hjust = 1, vjust = 0.5),
        plot.title = element_text(size = 22),
        plot.subtitle = element_text(size = 15, colour = "grey30")) +
  ggtitle("Where conflict lies",
          subtitle = "Grey: 5000 random placements (mean, 90%).\nOrange: steeper than chance at that position (uncorrected).")

caption <- paste(
  "Left: each tile is a stretch of positions; black outlines are the 26 domains the tests found; grey holds fewer than two domains.",
  if (any(d$significant)) {
    "Dots: more conflict than 5000 random placements of the same domain lengths, p < 0.05 (uncorrected)."
  } else {
    "No single stretch has more conflict than 5000 random placements of the same domain lengths at p < 0.05 (uncorrected)."
  },
  sprintf(paste0("Right: each point is a juncture between two positions; a conflicting pair spans the junctures inside the smallest stretch holding both (%d pairs, each counted once).\n",
                 "Largest change beyond chance: %+.2f at position %d; chance's largest is under %.2f in 95%% of placements (p = %.3f)%s."),
          q$n_conflicting_pairs, q$largest_excess_change, q$at_position, q$null_largest_hi, q$p_largest_ge,
          if (nrow(walls) == 0) ", so no single position is a wall once every position is looked at" else ""),
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
