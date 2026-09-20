# Renders the rows described in supercatalan_trees.json (written by
# generate_supercatalan_rows.py) to one raw, uncropped PDF per row in
# results/ -- generate_supercatalan_rows.py crops each one afterward with
# pdfcrop.
#
# Each tree is drawn with ggtree's `layout_dendrogram()`: a node's height
# is 1 + its tallest child's height, counted up from the leaves, so a
# small subtree always gets a small clean tent regardless of how deep it
# sits in the whole tree -- that's what keeps a cherry buried inside a big
# tree from looking disjointed. But every tree here represents the SAME
# thing -- one full span over n leaves -- so, as with the laminar trees,
# every root has to sit at the same height, the way every root does in
# the archived laminar_freqtree.r; a tree that happens to need fewer levels to
# reach its leaves should look like a wide, sparse triangle, not a short
# one. So every tree's drawing box gets the exact same fixed height
# (TREE_HEIGHT_IN), for every tree in every row -- not scaled by that
# tree's own height. ggtree/ggplot then auto-fits each tree's own natural
# 0..height range to fill that fixed box, which stretches a shallow tree's
# few levels to reach all the way to the same top line as a deep tree's
# many, while a linear stretch like that can't disturb the relative
# proportions (and hence shape) already correct within one tree.
suppressMessages({
  library(ape)
  library(ggplot2)
  library(ggtree)
  library(cowplot)
  library(jsonlite)
})

INCHES_PER_LEAF <- 0.22 # marginal width added per additional leaf
WIDTH_PAD_IN    <- 0.35 # fixed width every tree gets regardless of leaf count
TREE_HEIGHT_IN  <- 0.9  # every tree's root-to-leaf height, fixed and shared
TREE_GAP_IN     <- 0.3  # horizontal gap between separate trees in a row

# A tree's width is WIDTH_PAD_IN + n_leaves * INCHES_PER_LEAF, not just
# n_leaves * INCHES_PER_LEAF. Height is fixed (see above), so with no pad a
# 2-leaf tree would be a tall, narrow spike (n=2 alone gives only
# 2*0.22=0.44in against a 0.9in height) while an 11-leaf one is
# comfortably wide -- both correct by the same rule, but the small-n ones
# read as oddly skinny next to it. The fixed pad only meaningfully widens
# the few-leaf cases (0.35in on top of 0.44in roughly doubles it) and
# barely changes already-wide ones (0.35in on top of 11*0.22=2.42in), so
# it doesn't undo the leaf-count scaling that matters for bigger rows --
# it just stops leaf count alone from being the entire width for small n.

# generate_supercatalan_rows.py always launches this script with the
# working directory set to its own folder (scripts/exploratory/), so
# these can just be relative paths.
data <- fromJSON("supercatalan_trees.json", simplifyDataFrame = FALSE)
out_dir <- file.path("..", "..", "results")


# A truly zero expansion here (expand = c(0, 0)) puts the data's exact
# extremes -- the root apex, the leaf tips -- right on the panel's
# clipping boundary. A line has real width, and two strokes meeting at a
# sharp point (the apex, where both diagonals converge) miter into a
# little spike that sticks out past that exact point; with zero room, the
# panel boundary slices that spike off flat instead of leaving a clean
# point, and the same happens to the leaf ends at the left/right edges.
# A small proportional pad avoids that while barely changing the layout
# (it scales with each tree's own data range, so it stays proportionally
# tiny in every panel regardless of that tree's absolute size).
PANEL_EXPAND <- 0.04

make_plot <- function(newick) {
  tr <- read.tree(text = newick)
  ggtree(tr, layout = "slanted", ladderize = FALSE) +
    layout_dendrogram() +
    scale_x_reverse(expand = expansion(mult = PANEL_EXPAND)) +
    scale_y_continuous(expand = expansion(mult = PANEL_EXPAND)) +
    theme_void() +
    theme(plot.margin = margin(0, 0, 0, 0))
}

for (row in data$rows) {
  trees <- row$trees
  n_leaves <- sapply(trees, function(t) t$n_leaves)

  panel_widths_in <- n_leaves * INCHES_PER_LEAF + WIDTH_PAD_IN
  total_width_in  <- sum(panel_widths_in) + (length(trees) - 1) * TREE_GAP_IN
  total_height_in <- TREE_HEIGHT_IN

  p <- ggdraw()
  x_cursor <- 0
  for (i in seq_along(trees)) {
    panel_w_in <- panel_widths_in[i]
    p <- p + draw_plot(make_plot(trees[[i]]$newick),
                        x = x_cursor / total_width_in,
                        y = 0,
                        width = panel_w_in / total_width_in,
                        height = 1)
    x_cursor <- x_cursor + panel_w_in + TREE_GAP_IN
  }

  out_path <- file.path(out_dir, paste0(row$name, "_raw.pdf"))
  ggsave(out_path, p, width = total_width_in, height = total_height_in)
  cat("rendered", out_path, "\n")
}
