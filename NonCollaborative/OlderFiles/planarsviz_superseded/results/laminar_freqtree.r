library(ape)
library(ggplot2)
library(ggtree)

posLabel <- list("1" = "QM", "2" = "PreSbj", "3" = "Sbj", "4" = "PostSbj", "5" = "Neg1", "6" = "SM", "7" = "Neg2", "8" = "TAM", "9" = "OM", "10" = "Root", "11" = "Ext", "12" = "STAT", "13" = "CAUS", "14" = "APPL", "15" = "REC", "16" = "PASS", "17" = "FV", "18" = "2P", "19" = "Enc", "20" = "Obj1", "21" = "Obj2", "22" = "PostObj")

n_families <- 69
freq_tree <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")

node_freq <- data.frame(
  label      = c("1-22", "2-22", "3-21", "5-21", "5-19", "5-18", "5-17", "6-17", "9-17", "9-16", "10-16", "6-8", "13-15", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22"),
  freq       = c(69, 69, 69, 69, 69, 51, 37, 23, 25, 36, 38, 24, 40, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69, 69),
  freq_scaled= c(1.0, 1.0, 1.0, 1.0, 1.0, 0.73913, 0.536232, 0.333333, 0.362319, 0.521739, 0.550725, 0.347826, 0.57971, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
  edge_size  = c(4.0, 4.0, 4.0, 4.0, 4.0, 2.956522, 2.144928, 1.333333, 1.449275, 2.086957, 2.202899, 1.391304, 2.318841, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0)
)

p_freqtree <- ggtree(freq_tree, layout='slanted', ladderize=FALSE) %<+%
  node_freq +
  layout_dendrogram() +
  aes(alpha=freq_scaled, size=edge_size) +
  scale_size_identity() +
  scale_alpha_continuous(range=c(0.05, 1.0),
    name=paste0('Proportion of 69 families')) +
  geom_tiplab(geom='label', size=5, angle=0,
    offset=-1, hjust=0.5, alpha=1, label.size=0,
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank()) +
  ggtitle('69 maximal families — edge weight = family count')

ggsave('/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/../results/nyan1308_freqtree.pdf', p_freqtree, width=16, height=10)
