library(ggtree)
library(dplyr)

# Step 1: Get MRCA node
mrca_node <- getMRCA(tree14grouped, c("5", "17"))

# Step 2: Extract full tree data
p <- ggtree(tree14grouped, layout = "slanted", ladderize = FALSE, aes(size = strengthMap14[group]))
tree_data <- p$data

# Step 3: Recursively collect all edges in the subtree
collect_subtree_edges <- function(data, start_node) {
  edges <- data.frame()
  queue <- c(start_node)
  while (length(queue) > 0) {
    current <- queue[1]
    queue <- queue[-1]
    children <- data$node[data$parent == current]
    if (length(children) > 0) {
      edges <- rbind(edges, data.frame(parent = current, node = children))
      queue <- c(queue, children)
    }
  }
  return(edges)
}

subtree_edges <- collect_subtree_edges(tree_data, mrca_node)

# Step 4: Flag branches in the full tree
tree_data <- tree_data %>%
  mutate(branch_color = ifelse(paste(parent, node) %in% paste(subtree_edges$parent, subtree_edges$node), "red", "black"))

# Step 5: Inject modified data back into the plot
p$data <- tree_data

# Step 6: Final plot
treeplot14 <- p +
  aes(color = branch_color) +
  scale_color_identity() +
  scale_size_identity() +
  geom_tiplab(size = 5, angle = 0, offset = -0.5, hjust = 0.5, alpha = 0.066667) +
  layout_dendrogram() +
  theme(panel.background = element_blank(), plot.background = element_blank()) +
  theme(legend.position = "none")
