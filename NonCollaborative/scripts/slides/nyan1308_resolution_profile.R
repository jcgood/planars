#!/usr/bin/env Rscript
# Slide figure: resolution and crossing for every stretch of nyan1308's
# planar structure, real domain or not, from laminar/resolution_profile.py.
# A one-off for a talk, not one of the package's charts (the package chart is
# planned: docs/laminar-analysis-progress.md, "Domain support and resolution").
#
# Each tile is one stretch [left, right]: left edge down the side (1 at the
# top), right edge along the bottom. Two panels on the same grid:
# - Resolution against chance: the stretch's resolution (domains strictly
#   inside it over the most it could hold, averaged over the 69 trees) less
#   the average over 5000 random placements of the same domain lengths. Blue
#   is more resolved than chance, red flatter; a dot marks p < 0.05 either
#   way (uncorrected, and nested stretches share domains, so a map, not
#   tests). Stretches of two positions have no resolution and are grey.
# - Crossing: how many domains cut through the stretch, averaged over the
#   trees; white is none.
# The 26 real domains are outlined in black, 5-17 and 5-19 in dark red.
#
# Run from the repository root (where .Rprofile sets up the pinned packages),
# after python -m laminar.resolution_profile:
#   Rscript NonCollaborative/scripts/slides/nyan1308_resolution_profile.R
# Writes NonCollaborative/results/nyan1308/slides/
#   nyan1308_resolution_profile.pdf / .png  (16 x 9 in; png 3840 x 2160)

profile_path <- "NonCollaborative/results/nyan1308/counts-and-chance/nyan1308_resolution_profile.tsv"
out_dir <- "NonCollaborative/results/nyan1308/slides"
out_stem <- "nyan1308_resolution_profile"
if (!file.exists(profile_path)) {
  stop("Run this from the repository root, after python -m laminar.resolution_profile.", call. = FALSE)
}

suppressPackageStartupMessages({
  library(ggplot2)
  library(patchwork)
})

d <- utils::read.delim(profile_path)
d$is_domain <- d$is_domain == "True"
d$excess <- d$resolution - d$null_resolution_mean
d$significant <- !is.na(d$p_resolution_le) & (d$p_resolution_le < 0.05 | d$p_resolution_ge < 0.05)
domains <- d[d$is_domain, ]
labelled <- d[(d$left == 5 & d$right %in% c(17, 19)), ]

n <- max(d$right)
grid_theme <- theme_minimal(base_size = 18, base_family = "Gill Sans") +
  theme(panel.grid = element_blank(),
        plot.title = element_text(size = 22),
        legend.position = "bottom",
        legend.key.width = grid::unit(2.2, "cm"),
        legend.title = element_text(size = 15, vjust = 0.85))

base <- function(fill_var) {
  ggplot(d, aes(x = right, y = left)) +
    geom_tile(aes(fill = .data[[fill_var]]), colour = "white", linewidth = 0.6) +
    geom_tile(data = domains, width = 1, height = 1, fill = NA, colour = "black", linewidth = 0.9) +
    geom_tile(data = labelled, width = 1, height = 1, fill = NA, colour = "#A50F15", linewidth = 1.8) +
    scale_x_continuous("Right edge", breaks = 2:n, expand = c(0, 0)) +
    scale_y_reverse("Left edge", breaks = 1:(n - 1), expand = c(0, 0)) +
    coord_equal(clip = "off") +
    grid_theme
}

limit <- max(abs(d$excess), na.rm = TRUE)
p_res <- base("excess") +
  geom_point(data = d[d$significant, ], size = 1.6, colour = "black") +
  scale_fill_gradient2("Resolution less chance", low = "#B2182B", mid = "#F2F2F2", high = "#2166AC",
                       midpoint = 0, limits = c(-limit, limit), na.value = "#BDBDBD") +
  ggtitle("Resolution against chance")

p_cross <- base("crossing") +
  scale_fill_gradient("Domains crossing", low = "#FFFFFF", high = "#3F007D") +
  ggtitle("Domains crossing the stretch")

p <- p_res + p_cross +
  plot_annotation(caption = paste("Each tile is a stretch of positions; black outlines are the 26 domains the tests found,",
                                  "dark red 5–17 and 5–19 (row 5, columns 17 and 19).",
                                  "Dots: p < 0.05 against 5000 random placements (uncorrected).",
                                  sep = "\n"),
                  theme = theme(plot.caption = element_text(family = "Gill Sans", size = 14, hjust = 0)))

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
pdf_path <- file.path(out_dir, paste0(out_stem, ".pdf"))
suppressMessages(ggsave(pdf_path, p, width = 16, height = 9, units = "in",
                        device = function(filename, ...) grDevices::quartz(file = filename, type = "pdf", ...)))
system2("pdftocairo", c("-png", "-r", "240", "-singlefile", shQuote(pdf_path),
                        shQuote(file.path(out_dir, out_stem))))
cat("Wrote", pdf_path, "and the .png\n")
