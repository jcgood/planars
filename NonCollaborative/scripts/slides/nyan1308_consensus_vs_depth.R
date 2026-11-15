#!/usr/bin/env Rscript
# Slide figure: every one of nyan1308's maximal laminar families (trees),
# placed by its consensus score against its depth, with the number of binary
# nodes beside it. A one-off for a talk, not one of the package's charts.
#
# - Consensus score: for each distinct domain (span), count how many of the
#   trees contain it; a tree's score is the sum of those counts over its own
#   domains. The same score that picks `consensus_all` in selections.tsv
#   (laminar/export_planarsviz_data.py, export_selections); this script checks
#   that its top tree is that one and stops if not.
# - Depth: the most domains nested one inside another on the way from the
#   whole structure (1-22) down to a single position.
# - Binary nodes: domains that split into exactly two parts. The most binary
#   tree (`most_binary` in selections.tsv) is the one with the most of them.
#
# Two panels with the same vertical scale, so a tree sits at the same height
# in both. The consensus tree and the most binary tree are labelled.
#
# Run from the repository root (where .Rprofile sets up the pinned packages):
#   Rscript NonCollaborative/scripts/slides/nyan1308_consensus_vs_depth.R
# Writes NonCollaborative/results/nyan1308/slides/
#   nyan1308_consensus_vs_depth.pdf / .png  (16 x 9 in; png 3840 x 2160)
#   nyan1308_consensus_vs_depth.tsv         (the numbers behind it, one row per tree)

bundle_dir <- "NonCollaborative/results/chart_data/nyan1308"
out_dir <- "NonCollaborative/results/nyan1308/slides"
out_stem <- "nyan1308_consensus_vs_depth"
if (!dir.exists(bundle_dir)) stop("Run this from the repository root.", call. = FALSE)

suppressPackageStartupMessages({
  library(ggplot2)
  library(ape)
})

data_dir <- file.path(bundle_dir, "data")
read_tsv <- function(name) utils::read.delim(file.path(data_dir, name), colClasses = "character")
families <- read_tsv("families.tsv")
membership <- read_tsv("family_membership.tsv")
selections <- read_tsv("selections.tsv")

span_count <- table(membership$span_id)
consensus <- tapply(membership$span_id, membership$family_id, function(s) sum(span_count[s]))

tree_shape <- function(newick) {
  tree <- ape::read.tree(text = newick)
  n_tips <- length(tree$tip.label)
  internal <- seq(n_tips + 1, n_tips + tree$Nnode)
  children <- table(factor(tree$edge[, 1], levels = internal))
  # Internal nodes on the path from the root to each tip; the root (1-22)
  # counts as one, so a flat tree has depth 1.
  depth <- max(vapply(seq_len(n_tips), function(tip) {
    n <- 0L
    node <- tip
    repeat {
      parent <- tree$edge[tree$edge[, 2] == node, 1]
      if (length(parent) == 0) break
      n <- n + 1L
      node <- parent
    }
    n
  }, integer(1)))
  c(depth = depth, binary = sum(children == 2))
}
shape <- do.call(rbind, lapply(families$newick, tree_shape))

trees <- data.frame(
  family_id = families$family_id,
  consensus = as.numeric(consensus[families$family_id]),
  depth = shape[, "depth"],
  binary_nodes = shape[, "binary"],
  n_domains = as.integer(families$n_spans)
)

pick <- function(name) selections$family_id[selections$selection == name & selections$rank == "1"]
consensus_id <- pick("consensus_all")
binary_id <- pick("most_binary")
top <- trees$family_id[trees$consensus == max(trees$consensus)]
if (!identical(top, consensus_id)) {
  stop("The highest consensus score here (", paste(top, collapse = ", "),
       ") is not selections.tsv's consensus_all (", consensus_id, ").", call. = FALSE)
}
if (trees$binary_nodes[trees$family_id == binary_id] != max(trees$binary_nodes)) {
  stop("selections.tsv's most_binary (", binary_id, ") does not have the most binary nodes.", call. = FALSE)
}

trees$role <- "other"
trees$role[trees$family_id == consensus_id] <- "consensus"
trees$role[trees$family_id == binary_id] <- "binary"
trees$note <- ""
trees$note[trees$family_id == consensus_id] <- "Consensus (slide 32)"
trees$note[trees$family_id == binary_id] <- "Most binary (slides 12–13)"

n_top_binary <- sum(trees$binary_nodes == max(trees$binary_nodes))
binary_panel <- paste0("Binary nodes: domains that split into exactly two\n(",
                       n_top_binary, " trees tie at ", max(trees$binary_nodes),
                       "; the most tests breaks the tie)")
long <- rbind(
  data.frame(trees, panel = "Depth: most domains nested inside one another\n", x = trees$depth),
  data.frame(trees, panel = binary_panel, x = trees$binary_nodes)
)
long$panel <- factor(long$panel, levels = unique(long$panel))

ink <- "#222222"
muted <- "#8C8C8C"
highlight <- c(consensus = "#0072B2", binary = "#A50F15", other = muted)

set.seed(1)
long$xj <- long$x + ifelse(long$role == "other", stats::runif(nrow(long), -0.18, 0.18), 0)

p <- ggplot(long, aes(xj, consensus)) +
  geom_point(data = long[long$role == "other", ], colour = muted, size = 3.2, alpha = 0.75) +
  geom_point(data = long[long$role != "other", ], aes(colour = role), size = 6) +
  geom_text(data = long[long$role != "other", ], aes(label = note, colour = role),
            hjust = 0, nudge_x = 0.3, size = 6, family = "Gill Sans") +
  scale_colour_manual(values = highlight, guide = "none") +
  # Ticks only where there is data, so the room kept for the labels on the
  # right doesn't read as values no tree reaches.
  scale_x_continuous(breaks = function(l) seq(round(l[1] + 0.6), round(l[2] - 3.6)),
                     expand = expansion(add = c(0.6, 3.6))) +
  facet_wrap(~panel, nrow = 1, scales = "free_x") +
  coord_cartesian(clip = "off") +
  labs(x = NULL, y = "Consensus score\n(how widely the tree’s domains are shared by the 69 trees)") +
  theme_minimal(base_size = 20, base_family = "Gill Sans") +
  theme(
    plot.background = element_rect(fill = "white", colour = NA),
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_blank(),
    panel.grid.major.y = element_line(colour = "#E6E6E6"),
    strip.text = element_text(size = 20, hjust = 0, colour = ink),
    axis.text = element_text(colour = ink),
    axis.title.y = element_text(colour = ink, margin = margin(r = 12)),
    panel.spacing = unit(2.5, "lines"),
    plot.margin = margin(20, 150, 20, 20)
  )

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
pdf_path <- file.path(out_dir, paste0(out_stem, ".pdf"))
# Quartz, for Gill Sans and the typographic apostrophe.
suppressMessages(ggsave(pdf_path, p, width = 16, height = 9, units = "in",
                        device = function(filename, ...) grDevices::quartz(file = filename, type = "pdf", ...)))
system2("pdftocairo", c("-png", "-r", "240", "-singlefile", shQuote(pdf_path),
                        shQuote(file.path(out_dir, out_stem))))
utils::write.table(trees[order(-trees$consensus), c("family_id", "consensus", "depth", "binary_nodes", "n_domains")],
                   file.path(out_dir, paste0(out_stem, ".tsv")), sep = "\t", quote = FALSE, row.names = FALSE)
cat("Wrote", pdf_path, ".png and .tsv\n")
