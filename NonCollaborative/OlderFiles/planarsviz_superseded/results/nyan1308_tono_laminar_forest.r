library(ape)
library(ggplot2)
library(ggtree)
library(patchwork)

posLabel <- list("1" = "QM", "2" = "PreSbj", "3" = "Sbj", "4" = "PostSbj", "5" = "Neg1", "6" = "SM", "7" = "Neg2", "8" = "TAM", "9" = "OM", "10" = "Root", "11" = "Ext", "12" = "STAT", "13" = "CAUS", "14" = "APPL", "15" = "REC", "16" = "PASS", "17" = "FV", "18" = "2P", "19" = "Enc", "20" = "Obj1", "21" = "Obj2", "22" = "PostObj")

alphaval <- 0.400516 / 2

nyan1308_tono_tree1 <- read.tree(text="(1,2,3,4,(5,((((6,7,8)6-8,(9,10)9-10)6-10,11,12,13,14,15,16)6-16,17)6-17)5-17)1-17;")
nyan1308_tono_tree1grouped <- groupOTU(nyan1308_tono_tree1, list(a = c(1, 17), b = c(5, 17), c = c(6, 17), d = c(6, 16), e = c(6, 10), f = c(6, 8), g = c(9, 10)))
strengthMap1 <- c(0.5, 3.0, 3.0, 3.0, 2.2361, 1.4142, 1.7321, 3.0)
nyan1308_tono_treeplot1 <- ggtree(nyan1308_tono_tree1grouped,
  aes(size=(strengthMap1[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_tono_tree2 <- read.tree(text="(1,2,3,4,(5,(((6,7,8)6-8,((9,10)9-10,11,12,13,14,15,16)9-16)6-16,17)6-17)5-17)1-17;")
nyan1308_tono_tree2grouped <- groupOTU(nyan1308_tono_tree2, list(a = c(1, 17), b = c(5, 17), c = c(6, 17), d = c(6, 16), e = c(6, 8), f = c(9, 16), g = c(9, 10)))
strengthMap2 <- c(0.5, 3.0, 3.0, 3.0, 2.2361, 1.7321, 2.2361, 3.0)
nyan1308_tono_treeplot2 <- ggtree(nyan1308_tono_tree2grouped,
  aes(size=(strengthMap2[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_tono_tree3 <- read.tree(text="(1,2,3,4,(5,((6,7,8)6-8,(((9,10)9-10,11,12,13,14,15,16)9-16,17)9-17)6-17)5-17)1-17;")
nyan1308_tono_tree3grouped <- groupOTU(nyan1308_tono_tree3, list(a = c(1, 17), b = c(5, 17), c = c(6, 17), d = c(6, 8), e = c(9, 17), f = c(9, 16), g = c(9, 10)))
strengthMap3 <- c(0.5, 3.0, 3.0, 3.0, 1.7321, 1.4142, 2.2361, 3.0)
nyan1308_tono_treeplot3 <- ggtree(nyan1308_tono_tree3grouped,
  aes(size=(strengthMap3[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_tono_tree4 <- read.tree(text="(1,2,3,4,(5,(((6,7,(8,(9,10)9-10)8-10)6-10,11,12,13,14,15,16)6-16,17)6-17)5-17)1-17;")
nyan1308_tono_tree4grouped <- groupOTU(nyan1308_tono_tree4, list(a = c(1, 17), b = c(5, 17), c = c(6, 17), d = c(6, 16), e = c(6, 10), f = c(8, 10), g = c(9, 10)))
strengthMap4 <- c(0.5, 3.0, 3.0, 3.0, 2.2361, 1.4142, 1.7321, 3.0)
nyan1308_tono_treeplot4 <- ggtree(nyan1308_tono_tree4grouped,
  aes(size=(strengthMap4[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_tono_tree5 <- read.tree(text="(1,2,3,4,(5,((6,7,((8,(9,10)9-10)8-10,11,12,13,14,15,16)8-16)6-16,17)6-17)5-17)1-17;")
nyan1308_tono_tree5grouped <- groupOTU(nyan1308_tono_tree5, list(a = c(1, 17), b = c(5, 17), c = c(6, 17), d = c(6, 16), e = c(8, 16), f = c(8, 10), g = c(9, 10)))
strengthMap5 <- c(0.5, 3.0, 3.0, 3.0, 2.2361, 2.0, 1.7321, 3.0)
nyan1308_tono_treeplot5 <- ggtree(nyan1308_tono_tree5grouped,
  aes(size=(strengthMap5[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_tono_tree6 <- read.tree(text="(1,2,3,4,(5,((6,7,(8,((9,10)9-10,11,12,13,14,15,16)9-16)8-16)6-16,17)6-17)5-17)1-17;")
nyan1308_tono_tree6grouped <- groupOTU(nyan1308_tono_tree6, list(a = c(1, 17), b = c(5, 17), c = c(6, 17), d = c(6, 16), e = c(8, 16), f = c(9, 16), g = c(9, 10)))
strengthMap6 <- c(0.5, 3.0, 3.0, 3.0, 2.2361, 2.0, 2.2361, 3.0)
nyan1308_tono_treeplot6 <- ggtree(nyan1308_tono_tree6grouped,
  aes(size=(strengthMap6[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_tono_tree7 <- read.tree(text="(1,2,3,4,(5,(6,7,(((8,(9,10)9-10)8-10,11,12,13,14,15,16)8-16,17)8-17)6-17)5-17)1-17;")
nyan1308_tono_tree7grouped <- groupOTU(nyan1308_tono_tree7, list(a = c(1, 17), b = c(5, 17), c = c(6, 17), d = c(8, 17), e = c(8, 16), f = c(8, 10), g = c(9, 10)))
strengthMap7 <- c(0.5, 3.0, 3.0, 3.0, 1.7321, 2.0, 1.7321, 3.0)
nyan1308_tono_treeplot7 <- ggtree(nyan1308_tono_tree7grouped,
  aes(size=(strengthMap7[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_tono_tree8 <- read.tree(text="(1,2,3,4,(5,(6,7,((8,((9,10)9-10,11,12,13,14,15,16)9-16)8-16,17)8-17)6-17)5-17)1-17;")
nyan1308_tono_tree8grouped <- groupOTU(nyan1308_tono_tree8, list(a = c(1, 17), b = c(5, 17), c = c(6, 17), d = c(8, 17), e = c(8, 16), f = c(9, 16), g = c(9, 10)))
strengthMap8 <- c(0.5, 3.0, 3.0, 3.0, 1.7321, 2.0, 2.2361, 3.0)
nyan1308_tono_treeplot8 <- ggtree(nyan1308_tono_tree8grouped,
  aes(size=(strengthMap8[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_tono_tree9 <- read.tree(text="(1,2,3,4,(5,(6,7,(8,(((9,10)9-10,11,12,13,14,15,16)9-16,17)9-17)8-17)6-17)5-17)1-17;")
nyan1308_tono_tree9grouped <- groupOTU(nyan1308_tono_tree9, list(a = c(1, 17), b = c(5, 17), c = c(6, 17), d = c(8, 17), e = c(9, 17), f = c(9, 16), g = c(9, 10)))
strengthMap9 <- c(0.5, 3.0, 3.0, 3.0, 1.7321, 1.4142, 2.2361, 3.0)
nyan1308_tono_treeplot9 <- ggtree(nyan1308_tono_tree9grouped,
  aes(size=(strengthMap9[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_tono_treeplot9 <- nyan1308_tono_treeplot9 + geom_tiplab(geom="label", size=6, angle=0,
  offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
  aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1)

treelayout <- c(
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1))

forest <- (
  nyan1308_tono_treeplot1 +
  nyan1308_tono_treeplot2 +
  nyan1308_tono_treeplot3 +
  nyan1308_tono_treeplot4 +
  nyan1308_tono_treeplot5 +
  nyan1308_tono_treeplot6 +
  nyan1308_tono_treeplot7 +
  nyan1308_tono_treeplot8 +
  nyan1308_tono_treeplot9 +
  plot_layout(design=treelayout))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/results/nyan1308_tono_laminar_forest.pdf", forest & theme(plot.background=element_rect(fill='white', color=NA)), width=20, height=14)
