# Every individual maximal-family tree in a bundle's forest, one file each --
# not the ghost overlay (all trees stacked semi-transparently into one
# image, e.g. nyan1308_phonologylike_laminar_forest.pdf) and not a curated
# subset (the "exemplary" charts pick 7 representative families out of 69
# for the pooled analysis; this draws every one, for a named forest).
#
# Reads directly from the exported bundle
# (results/planarsviz/nyan1308/data/forests/<name>.tsv, written by
# export_planarsviz_data.py -- one row per family: tree_number, newick,
# group_spans, strengths) rather than recomputing anything, matching this
# project's "Python computes, R only draws from the bundle" rule. Only
# tree_number and newick are used here; group_spans/strengths exist for the
# combined overlay's per-span thickness aesthetic, which a single clean tree
# doesn't need -- matching plot_exemplary_tree()'s own choice not to encode
# thickness on an individual exemplar tree either.
#
# Tree-drawing incantation (layout, boxed "N\nName" tip labels, margins) is
# the same one planarsviz_exemplary_tree() (r/planarsviz/R/exemplary.R) uses
# for the pooled analysis's individual exemplar trees -- copied rather than
# called, since that function is keyed by the pooled bundle's family_id
# (bundle$families$newick), and a forest's own trees are a separate table
# with no family_id of their own (just tree_number, matching e.g. the
# n_maximal_laminar_families count in nyan1308_tree_counts.tsv: 6 for
# phonologylike, 16 for syntaxlike). Not worth changing the package's own
# family_id-keyed function to accommodate this one-off ad hoc request.
#
# This is a one-off script, not a numbered planarsviz chart -- generating
# a file per individual tree (up to dozens per forest) doesn't fit the
# package's "one named chart per --plots entry" convention the way the
# other visualizations here do.
#
# Run from anywhere:
#   Rscript NonCollaborative/scripts/analysis/bundle_forest_trees.r

library(ggplot2)
library(ape)
library(ggtree)

script_dir <- local({
  file_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
  if (length(file_arg)) dirname(normalizePath(sub("^--file=", "", file_arg[[1]]))) else getwd()
})
results_dir <- normalizePath(file.path(script_dir, "..", "..", "results"), mustWork = TRUE)
bundle_data_dir <- normalizePath(file.path(results_dir, "planarsviz", "nyan1308", "data"), mustWork = TRUE)

position_labels <- read.delim(file.path(bundle_data_dir, "position_labels.tsv"), stringsAsFactors = FALSE)
posLabel <- as.list(setNames(as.character(position_labels$label), as.character(position_labels$position)))

# Forests to draw every individual tree for. Add more names here (they must
# match a file in data/forests/) rather than writing a second script.
FOREST_NAMES <- c("phonologylike", "syntaxlike")

draw_tree <- function(newick) {
  tree <- ape::read.tree(text = newick)
  ggtree::ggtree(tree, layout = "slanted", ladderize = FALSE) +
    ggtree::layout_dendrogram() +
    ggtree::geom_tiplab(geom = "label", size = 5, angle = 0,
      offset = -1, hjust = 0.5, vjust = 0.35, alpha = 1, label.size = 0,
      aes(label = paste(label, posLabel[label], sep = "\n")), lineheight = 1) +
    theme(panel.background = element_blank(),
      plot.background = element_blank(), legend.position = "none",
      plot.margin = margin(t = 10, r = 10, b = 25, l = 10, unit = "pt"))
}

for (forest_name in FOREST_NAMES) {
  forest_path <- file.path(bundle_data_dir, "forests", paste0(forest_name, ".tsv"))
  forest <- read.delim(forest_path, stringsAsFactors = FALSE)
  n_digits <- max(2, nchar(as.character(max(forest$tree_number))))
  cat(sprintf("%s: %d trees\n", forest_name, nrow(forest)))
  for (i in seq_len(nrow(forest))) {
    p <- draw_tree(forest$newick[i])
    tree_num_padded <- formatC(forest$tree_number[i], width = n_digits, flag = "0")
    out_path <- file.path(results_dir, sprintf("nyan1308_%s_tree_%s.pdf", forest_name, tree_num_padded))
    ggsave(out_path, p, device = "pdf", width = 12, height = 8, units = "in")
  }
  cat(sprintf("  wrote nyan1308_%s_tree_%s.pdf .. _%s.pdf\n",
              forest_name, formatC(1, width = n_digits, flag = "0"),
              formatC(nrow(forest), width = n_digits, flag = "0")))
}
