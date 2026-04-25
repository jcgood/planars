library(ape)
library(ggplot2)
library(ggtree)
library(patchwork)

posLabel <- list("1" = "QM", "2" = "PreSbj", "3" = "Sbj", "4" = "PostSbj", "5" = "Neg1", "6" = "SM", "7" = "Neg2", "8" = "TAM", "9" = "OM", "10" = "Root", "11" = "Ext", "12" = "STAT", "13" = "CAUS", "14" = "APPL", "15" = "REC", "16" = "PASS", "17" = "FV", "18" = "2P", "19" = "Enc", "20" = "Obj1", "21" = "Obj2", "22" = "PostObj")

# ── All 69 families (representative) ──
p_all_tree <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
p_all_nf <- data.frame(
  label      = c("1-22", "2-22", "3-21", "5-21", "5-19", "5-18", "5-17", "6-17", "9-17", "9-16", "10-16", "6-8", "13-15", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22"),
  freq       = c(69, 69, 69, 69, 69, 51, 37, 23, 25, 36, 38, 24, 40, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69),
  freq_scaled= c(1.0, 1.0, 1.0, 1.0, 1.0, 0.73913, 0.536232, 0.333333, 0.362319, 0.521739, 0.550725, 0.347826, 0.57971, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
  edge_size  = c(4.0, 4.0, 4.0, 4.0, 4.0, 2.956522, 2.144928, 1.333333, 1.449275, 2.086957, 2.202899, 1.391304, 2.318841, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0)
)
p_all <- ggtree(p_all_tree, layout='slanted', ladderize=FALSE) %<+%
  p_all_nf +
  layout_dendrogram() +
  aes(alpha=freq_scaled, size=edge_size) +
  scale_size_identity() +
  scale_alpha_continuous(range=c(0.05, 1.0),
    name=paste0('Prop. of 69 families')) +
  geom_tiplab(geom='label', size=5, angle=0,
    offset=-1, hjust=0.5, alpha=1, label.size=0,
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  ggtitle('All 69 families (representative)')

# ── Group A: [5-13] (10 families) ──
p_A_tree <- read.tree(text="(1,(2,(3,4,((((((5,6)5-6,7,(8,(9,10)9-10)8-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
p_A_nf <- data.frame(
  label      = c("1-22", "2-22", "3-21", "5-21", "5-19", "5-18", "5-17", "5-13", "8-10", "9-10", "5-6", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22"),
  freq       = c(10, 10, 10, 10, 10, 5, 5, 10, 4, 6, 4, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10),
  freq_scaled= c(1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.5, 1.0, 0.4, 0.6, 0.4, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
  edge_size  = c(4.0, 4.0, 4.0, 4.0, 4.0, 2.0, 2.0, 4.0, 1.6, 2.4, 1.6, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0)
)
p_A <- ggtree(p_A_tree, layout='slanted', ladderize=FALSE) %<+%
  p_A_nf +
  layout_dendrogram() +
  aes(alpha=freq_scaled, size=edge_size) +
  scale_size_identity() +
  scale_alpha_continuous(range=c(0.05, 1.0),
    name=paste0('Prop. of 10 families')) +
  geom_tiplab(geom='label', size=5, angle=0,
    offset=-1, hjust=0.5, alpha=1, label.size=0,
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  ggtitle('Group A: [5-13] (10 families)')

# ── Group B: [6-17] (23 families) ──
p_B_tree <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
p_B_nf <- data.frame(
  label      = c("1-22", "2-22", "3-21", "5-21", "5-19", "5-18", "5-17", "6-17", "9-17", "9-16", "10-16", "6-8", "13-15", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22"),
  freq       = c(23, 23, 23, 23, 23, 23, 23, 23, 10, 15, 14, 9, 16, 23, 23, 23, 23, 23, 23, 23, 23, 23, 23, 23, 23, 23, 23, 23, 23, 23, 23, 23, 23, 23, 23),
  freq_scaled= c(1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.434783, 0.652174, 0.608696, 0.391304, 0.695652, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
  edge_size  = c(4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 1.73913, 2.608696, 2.434783, 1.565217, 2.782609, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0)
)
p_B <- ggtree(p_B_tree, layout='slanted', ladderize=FALSE) %<+%
  p_B_nf +
  layout_dendrogram() +
  aes(alpha=freq_scaled, size=edge_size) +
  scale_size_identity() +
  scale_alpha_continuous(range=c(0.05, 1.0),
    name=paste0('Prop. of 23 families')) +
  geom_tiplab(geom='label', size=5, angle=0,
    offset=-1, hjust=0.5, alpha=1, label.size=0,
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  ggtitle('Group B: [6-17] (23 families)')

# ── Group C: neither (36 families) ──
p_C_tree <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
p_C_nf <- data.frame(
  label      = c("1-22", "2-22", "3-21", "5-21", "5-19", "5-18", "5-17", "8-17", "9-17", "9-16", "10-16", "13-15", "5-6", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22"),
  freq       = c(36, 36, 36, 36, 36, 23, 9, 9, 15, 21, 24, 24, 20, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36),
  freq_scaled= c(1.0, 1.0, 1.0, 1.0, 1.0, 0.638889, 0.25, 0.25, 0.416667, 0.583333, 0.666667, 0.666667, 0.555556, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
  edge_size  = c(4.0, 4.0, 4.0, 4.0, 4.0, 2.555556, 1.0, 1.0, 1.666667, 2.333333, 2.666667, 2.666667, 2.222222, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0)
)
p_C <- ggtree(p_C_tree, layout='slanted', ladderize=FALSE) %<+%
  p_C_nf +
  layout_dendrogram() +
  aes(alpha=freq_scaled, size=edge_size) +
  scale_size_identity() +
  scale_alpha_continuous(range=c(0.05, 1.0),
    name=paste0('Prop. of 36 families')) +
  geom_tiplab(geom='label', size=5, angle=0,
    offset=-1, hjust=0.5, alpha=1, label.size=0,
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  ggtitle('Group C: neither (36 families)')

# ── 2x2 layout ──
forest <- (p_all | p_A) / (p_B | p_C) +
  plot_layout(guides='collect')

ggsave('/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/../results/nyan1308_four_trees.pdf', forest, width=24, height=16)
