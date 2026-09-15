library(ape)
library(ggplot2)
library(ggtree)
library(patchwork)

posLabel <- list("1" = "QM", "2" = "PreSbj", "3" = "Sbj", "4" = "PostSbj", "5" = "Neg1", "6" = "SM", "7" = "Neg2", "8" = "TAM", "9" = "OM", "10" = "Root", "11" = "Ext", "12" = "STAT", "13" = "CAUS", "14" = "APPL", "15" = "REC", "16" = "PASS", "17" = "FV", "18" = "2P", "19" = "Enc", "20" = "Obj1", "21" = "Obj2", "22" = "PostObj")

alphaval <- 0.250106 / 2

nyan1308_syntaxlike_tree1 <- read.tree(text="(1,2,3,4,((((5,((((6,7,8)6-8,(9,10)9-10)6-10,11,12,(13,14,15)13-15,16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree1grouped <- groupOTU(nyan1308_syntaxlike_tree1, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(6, 17), g = c(6, 16), h = c(6, 10), i = c(6, 8), j = c(9, 10), k = c(13, 15)))
strengthMap1 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 3.6056, 3.3166, 2.2361, 2.0, 2.8284, 3.4641, 3.7417)
nyan1308_syntaxlike_treeplot1 <- ggtree(nyan1308_syntaxlike_tree1grouped,
  aes(size=(strengthMap1[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree2 <- read.tree(text="(1,2,3,4,((((5,(((6,7,8)6-8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree2grouped <- groupOTU(nyan1308_syntaxlike_tree2, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(6, 17), g = c(6, 16), h = c(6, 8), i = c(9, 16), j = c(9, 10), k = c(13, 15)))
strengthMap2 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 3.6056, 3.3166, 2.2361, 2.8284, 2.4495, 3.4641, 3.7417)
nyan1308_syntaxlike_treeplot2 <- ggtree(nyan1308_syntaxlike_tree2grouped,
  aes(size=(strengthMap2[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree3 <- read.tree(text="(1,2,3,4,((((5,((6,7,8)6-8,(((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree3grouped <- groupOTU(nyan1308_syntaxlike_tree3, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(6, 17), g = c(6, 8), h = c(9, 17), i = c(9, 16), j = c(9, 10), k = c(13, 15)))
strengthMap3 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 3.6056, 3.3166, 2.8284, 2.4495, 2.4495, 3.4641, 3.7417)
nyan1308_syntaxlike_treeplot3 <- ggtree(nyan1308_syntaxlike_tree3grouped,
  aes(size=(strengthMap3[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree4 <- read.tree(text="(1,2,3,4,((((5,(((6,7,(8,(9,10)9-10)8-10)6-10,11,12,(13,14,15)13-15,16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree4grouped <- groupOTU(nyan1308_syntaxlike_tree4, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(6, 17), g = c(6, 16), h = c(6, 10), i = c(8, 10), j = c(9, 10), k = c(13, 15)))
strengthMap4 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 3.6056, 3.3166, 2.2361, 2.0, 2.0, 3.4641, 3.7417)
nyan1308_syntaxlike_treeplot4 <- ggtree(nyan1308_syntaxlike_tree4grouped,
  aes(size=(strengthMap4[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree5 <- read.tree(text="(1,2,3,4,((((5,((6,7,((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree5grouped <- groupOTU(nyan1308_syntaxlike_tree5, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(6, 17), g = c(6, 16), h = c(8, 16), i = c(8, 10), j = c(9, 10), k = c(13, 15)))
strengthMap5 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 3.6056, 3.3166, 2.2361, 2.0, 2.0, 3.4641, 3.7417)
nyan1308_syntaxlike_treeplot5 <- ggtree(nyan1308_syntaxlike_tree5grouped,
  aes(size=(strengthMap5[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree6 <- read.tree(text="(1,2,3,4,((((5,((6,7,(8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree6grouped <- groupOTU(nyan1308_syntaxlike_tree6, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(6, 17), g = c(6, 16), h = c(8, 16), i = c(9, 16), j = c(9, 10), k = c(13, 15)))
strengthMap6 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 3.6056, 3.3166, 2.2361, 2.0, 2.4495, 3.4641, 3.7417)
nyan1308_syntaxlike_treeplot6 <- ggtree(nyan1308_syntaxlike_tree6grouped,
  aes(size=(strengthMap6[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree7 <- read.tree(text="(1,2,3,4,((((5,(6,7,(((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree7grouped <- groupOTU(nyan1308_syntaxlike_tree7, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(6, 17), g = c(8, 17), h = c(8, 16), i = c(8, 10), j = c(9, 10), k = c(13, 15)))
strengthMap7 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 3.6056, 3.3166, 2.0, 2.0, 2.0, 3.4641, 3.7417)
nyan1308_syntaxlike_treeplot7 <- ggtree(nyan1308_syntaxlike_tree7grouped,
  aes(size=(strengthMap7[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree8 <- read.tree(text="(1,2,3,4,((((5,(6,7,((8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree8grouped <- groupOTU(nyan1308_syntaxlike_tree8, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(6, 17), g = c(8, 17), h = c(8, 16), i = c(9, 16), j = c(9, 10), k = c(13, 15)))
strengthMap8 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 3.6056, 3.3166, 2.0, 2.0, 2.4495, 3.4641, 3.7417)
nyan1308_syntaxlike_treeplot8 <- ggtree(nyan1308_syntaxlike_tree8grouped,
  aes(size=(strengthMap8[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree9 <- read.tree(text="(1,2,3,4,((((5,(6,7,(8,(((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree9grouped <- groupOTU(nyan1308_syntaxlike_tree9, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(6, 17), g = c(8, 17), h = c(9, 17), i = c(9, 16), j = c(9, 10), k = c(13, 15)))
strengthMap9 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 3.6056, 3.3166, 2.0, 2.4495, 2.4495, 3.4641, 3.7417)
nyan1308_syntaxlike_treeplot9 <- ggtree(nyan1308_syntaxlike_tree9grouped,
  aes(size=(strengthMap9[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree10 <- read.tree(text="(1,2,3,4,((((5,((6,7,8)6-8,(9,(10,11,12,(13,14,15)13-15,16,17)10-17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree10grouped <- groupOTU(nyan1308_syntaxlike_tree10, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(6, 17), g = c(6, 8), h = c(9, 17), i = c(10, 17), j = c(13, 15)))
strengthMap10 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 3.6056, 3.3166, 2.8284, 2.4495, 2.0, 3.7417)
nyan1308_syntaxlike_treeplot10 <- ggtree(nyan1308_syntaxlike_tree10grouped,
  aes(size=(strengthMap10[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree11 <- read.tree(text="(1,2,3,4,((((5,(6,7,(8,(9,(10,11,12,(13,14,15)13-15,16,17)10-17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree11grouped <- groupOTU(nyan1308_syntaxlike_tree11, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(6, 17), g = c(8, 17), h = c(9, 17), i = c(10, 17), j = c(13, 15)))
strengthMap11 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 3.6056, 3.3166, 2.0, 2.4495, 2.0, 3.7417)
nyan1308_syntaxlike_treeplot11 <- ggtree(nyan1308_syntaxlike_tree11grouped,
  aes(size=(strengthMap11[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree12 <- read.tree(text="(1,2,3,4,(((5,(6,7,8)6-8,((((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree12grouped <- groupOTU(nyan1308_syntaxlike_tree12, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(6, 8), f = c(9, 18), g = c(9, 17), h = c(9, 16), i = c(9, 10), j = c(13, 15)))
strengthMap12 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 2.8284, 1.7321, 2.4495, 2.4495, 3.4641, 3.7417)
nyan1308_syntaxlike_treeplot12 <- ggtree(nyan1308_syntaxlike_tree12grouped,
  aes(size=(strengthMap12[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree13 <- read.tree(text="(1,2,3,4,(((((5,((6,7,8)6-8,(9,10)9-10)6-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree13grouped <- groupOTU(nyan1308_syntaxlike_tree13, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(5, 13), g = c(6, 10), h = c(6, 8), i = c(9, 10)))
strengthMap13 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 3.6056, 1.4142, 2.0, 2.8284, 3.4641)
nyan1308_syntaxlike_treeplot13 <- ggtree(nyan1308_syntaxlike_tree13grouped,
  aes(size=(strengthMap13[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree14 <- read.tree(text="(1,2,3,4,(((((5,(6,7,(8,(9,10)9-10)8-10)6-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree14grouped <- groupOTU(nyan1308_syntaxlike_tree14, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(5, 13), g = c(6, 10), h = c(8, 10), i = c(9, 10)))
strengthMap14 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 3.6056, 1.4142, 2.0, 2.0, 3.4641)
nyan1308_syntaxlike_treeplot14 <- ggtree(nyan1308_syntaxlike_tree14grouped,
  aes(size=(strengthMap14[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree15 <- read.tree(text="(1,2,3,4,(((5,(6,7,8)6-8,((9,(10,11,12,(13,14,15)13-15,16,17)10-17)9-17,18)9-18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree15grouped <- groupOTU(nyan1308_syntaxlike_tree15, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(6, 8), f = c(9, 18), g = c(9, 17), h = c(10, 17), i = c(13, 15)))
strengthMap15 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 2.8284, 1.7321, 2.4495, 2.0, 3.7417)
nyan1308_syntaxlike_treeplot15 <- ggtree(nyan1308_syntaxlike_tree15grouped,
  aes(size=(strengthMap15[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_tree16 <- read.tree(text="(1,2,3,4,(((5,(6,7,8)6-8,(9,((10,11,12,(13,14,15)13-15,16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21,22)1-22;")
nyan1308_syntaxlike_tree16grouped <- groupOTU(nyan1308_syntaxlike_tree16, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(6, 8), f = c(9, 18), g = c(10, 18), h = c(10, 17), i = c(13, 15)))
strengthMap16 <- c(0.5, 4.0, 4.0, 4.0, 4.0, 2.8284, 1.7321, 1.0, 2.0, 3.7417)
nyan1308_syntaxlike_treeplot16 <- ggtree(nyan1308_syntaxlike_tree16grouped,
  aes(size=(strengthMap16[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_syntaxlike_treeplot16 <- nyan1308_syntaxlike_treeplot16 + geom_tiplab(geom="label", size=6, angle=0,
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
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1))

forest <- (
  nyan1308_syntaxlike_treeplot1 +
  nyan1308_syntaxlike_treeplot2 +
  nyan1308_syntaxlike_treeplot3 +
  nyan1308_syntaxlike_treeplot4 +
  nyan1308_syntaxlike_treeplot5 +
  nyan1308_syntaxlike_treeplot6 +
  nyan1308_syntaxlike_treeplot7 +
  nyan1308_syntaxlike_treeplot8 +
  nyan1308_syntaxlike_treeplot9 +
  nyan1308_syntaxlike_treeplot10 +
  nyan1308_syntaxlike_treeplot11 +
  nyan1308_syntaxlike_treeplot12 +
  nyan1308_syntaxlike_treeplot13 +
  nyan1308_syntaxlike_treeplot14 +
  nyan1308_syntaxlike_treeplot15 +
  nyan1308_syntaxlike_treeplot16 +
  plot_layout(design=treelayout))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/results/nyan1308_syntaxlike_laminar_forest.pdf", forest & theme(plot.background=element_rect(fill='white', color=NA)), width=20, height=14)
