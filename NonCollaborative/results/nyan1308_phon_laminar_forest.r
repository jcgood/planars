library(ape)
library(ggplot2)
library(ggtree)
library(patchwork)

posLabel <- list("1" = "QM", "2" = "PreSbj", "3" = "Sbj", "4" = "PostSbj", "5" = "Neg1", "6" = "SM", "7" = "Neg2", "8" = "TAM", "9" = "OM", "10" = "Root", "11" = "Ext", "12" = "STAT", "13" = "CAUS", "14" = "APPL", "15" = "REC", "16" = "PASS", "17" = "FV", "18" = "2P", "19" = "Enc", "20" = "Obj1", "21" = "Obj2", "22" = "PostObj")

alphaval <- 0.535841 / 2

nyan1308_phon_tree1 <- read.tree(text="(1,2,(3,4,(5,((6,7,8)6-8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17)6-17,18,19,20,21)5-21)3-21)1-21;")
nyan1308_phon_tree1grouped <- groupOTU(nyan1308_phon_tree1, list(a = c(1, 21), b = c(3, 21), c = c(5, 21), d = c(6, 17), e = c(6, 8), f = c(9, 17), g = c(10, 17), h = c(10, 16), i = c(10, 13)))
strengthMap1 <- c(0.5, 2.4495, 2.4495, 2.4495, 1.4142, 2.0, 1.4142, 1.4142, 2.0, 2.0)
nyan1308_phon_treeplot1 <- ggtree(nyan1308_phon_tree1grouped,
  aes(size=(strengthMap1[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#20845E") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_phon_tree2 <- read.tree(text="(1,2,(3,4,((5,6)5-6,7,8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17,18,19,20,21)5-21)3-21)1-21;")
nyan1308_phon_tree2grouped <- groupOTU(nyan1308_phon_tree2, list(a = c(1, 21), b = c(3, 21), c = c(5, 21), d = c(5, 6), e = c(9, 17), f = c(10, 17), g = c(10, 16), h = c(10, 13)))
strengthMap2 <- c(0.5, 2.4495, 2.4495, 2.4495, 1.4142, 1.4142, 1.4142, 2.0, 2.0)
nyan1308_phon_treeplot2 <- ggtree(nyan1308_phon_tree2grouped,
  aes(size=(strengthMap2[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#20845E") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_phon_tree3 <- read.tree(text="(1,2,(3,4,((5,6)5-6,7,8,9,((10,11,12,13)10-13,14,15,16)10-16,(17,18,19)17-19,20,21)5-21)3-21)1-21;")
nyan1308_phon_tree3grouped <- groupOTU(nyan1308_phon_tree3, list(a = c(1, 21), b = c(3, 21), c = c(5, 21), d = c(5, 6), e = c(10, 16), f = c(10, 13), g = c(17, 19)))
strengthMap3 <- c(0.5, 2.4495, 2.4495, 2.4495, 1.4142, 2.0, 2.0, 1.7321)
nyan1308_phon_treeplot3 <- ggtree(nyan1308_phon_tree3grouped,
  aes(size=(strengthMap3[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#20845E") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_phon_tree4 <- read.tree(text="(1,2,(3,4,(5,(6,7,8)6-8,9,((10,11,12,13)10-13,14,15,16)10-16,(17,18,19)17-19,20,21)5-21)3-21)1-21;")
nyan1308_phon_tree4grouped <- groupOTU(nyan1308_phon_tree4, list(a = c(1, 21), b = c(3, 21), c = c(5, 21), d = c(6, 8), e = c(10, 16), f = c(10, 13), g = c(17, 19)))
strengthMap4 <- c(0.5, 2.4495, 2.4495, 2.4495, 2.0, 2.0, 2.0, 1.7321)
nyan1308_phon_treeplot4 <- ggtree(nyan1308_phon_tree4grouped,
  aes(size=(strengthMap4[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#20845E") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_phon_tree5 <- read.tree(text="(1,2,(3,4,(5,(((6,7,8)6-8,9,10)6-10,11,12,13,14,15,16,17)6-17,18,19,20,21)5-21)3-21)1-21;")
nyan1308_phon_tree5grouped <- groupOTU(nyan1308_phon_tree5, list(a = c(1, 21), b = c(3, 21), c = c(5, 21), d = c(6, 17), e = c(6, 10), f = c(6, 8)))
strengthMap5 <- c(0.5, 2.4495, 2.4495, 2.4495, 1.4142, 1.4142, 2.0)
nyan1308_phon_treeplot5 <- ggtree(nyan1308_phon_tree5grouped,
  aes(size=(strengthMap5[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#20845E") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_phon_tree6 <- read.tree(text="(1,2,(3,4,(5,((6,7,8)6-8,9,10)6-10,11,12,13,14,15,16,(17,18,19)17-19,20,21)5-21)3-21)1-21;")
nyan1308_phon_tree6grouped <- groupOTU(nyan1308_phon_tree6, list(a = c(1, 21), b = c(3, 21), c = c(5, 21), d = c(6, 10), e = c(6, 8), f = c(17, 19)))
strengthMap6 <- c(0.5, 2.4495, 2.4495, 2.4495, 1.4142, 2.0, 1.7321)
nyan1308_phon_treeplot6 <- ggtree(nyan1308_phon_tree6grouped,
  aes(size=(strengthMap6[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#20845E") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_phon_treeplot6 <- nyan1308_phon_treeplot6 + geom_tiplab(geom="label", size=6, angle=0,
  offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
  aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1)

treelayout <- c(
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1))

forest <- (
  nyan1308_phon_treeplot1 +
  nyan1308_phon_treeplot2 +
  nyan1308_phon_treeplot3 +
  nyan1308_phon_treeplot4 +
  nyan1308_phon_treeplot5 +
  nyan1308_phon_treeplot6 +
  plot_layout(design=treelayout))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/results/nyan1308_phon_laminar_forest.pdf", forest & theme(plot.background=element_rect(fill='white', color=NA)), width=20, height=14)
