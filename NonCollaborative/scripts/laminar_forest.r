library(ape)
library(ggplot2)
library(ggtree)
library(patchwork)

alphaval <- 0.064563 / 2

tree1 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree1grouped <- groupOTU(tree1, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
strengthMap1 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 4.4721, 3.3166, 5.1962, 6.3246)
treeplot1 <- ggtree(tree1grouped,
  aes(size=(strengthMap1[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=1,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree2 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,((8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree2grouped <- groupOTU(tree2, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
strengthMap2 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 4.4721, 6.0, 5.1962, 6.3246)
treeplot2 <- ggtree(tree2grouped,
  aes(size=(strengthMap2[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree3 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,((8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree3grouped <- groupOTU(tree3, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
strengthMap3 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 4.4721, 6.0, 6.1644, 4.7958)
treeplot3 <- ggtree(tree3grouped,
  aes(size=(strengthMap3[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree4 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,((8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree4grouped <- groupOTU(tree4, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
strengthMap4 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 4.4721, 6.0, 6.1644, 6.3246)
treeplot4 <- ggtree(tree4grouped,
  aes(size=(strengthMap4[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree5 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,(((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree5grouped <- groupOTU(tree5, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
strengthMap5 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 6.0, 5.1962, 6.3246)
treeplot5 <- ggtree(tree5grouped,
  aes(size=(strengthMap5[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree6 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree6grouped <- groupOTU(tree6, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
strengthMap6 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 6.0, 6.1644, 4.7958)
treeplot6 <- ggtree(tree6grouped,
  aes(size=(strengthMap6[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree7 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree7grouped <- groupOTU(tree7, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
strengthMap7 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 6.0, 6.1644, 6.3246)
treeplot7 <- ggtree(tree7grouped,
  aes(size=(strengthMap7[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree8 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree8grouped <- groupOTU(tree8, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(10, 13)))
strengthMap8 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 3.7417, 6.1644, 4.7958)
treeplot8 <- ggtree(tree8grouped,
  aes(size=(strengthMap8[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree9 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,(9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree9grouped <- groupOTU(tree9, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(13, 15)))
strengthMap9 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 3.7417, 6.1644, 6.3246)
treeplot9 <- ggtree(tree9grouped,
  aes(size=(strengthMap9[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree10 <- read.tree(text="(1,(2,(3,4,((((5,((((6,7,8)6-8,(9,10)9-10)6-10,11,12,(13,14,15)13-15,16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree10grouped <- groupOTU(tree10, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 10), k = c(6, 8), l = c(9, 10), m = c(13, 15)))
strengthMap10 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 2.8284, 4.899, 5.1962, 6.3246)
treeplot10 <- ggtree(tree10grouped,
  aes(size=(strengthMap10[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree11 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,8)6-8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree11grouped <- groupOTU(tree11, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 8), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
strengthMap11 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.899, 6.0, 5.1962, 6.3246)
treeplot11 <- ggtree(tree11grouped,
  aes(size=(strengthMap11[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree12 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,8)6-8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree12grouped <- groupOTU(tree12, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 8), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
strengthMap12 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.899, 6.0, 6.1644, 4.7958)
treeplot12 <- ggtree(tree12grouped,
  aes(size=(strengthMap12[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree13 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,8)6-8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree13grouped <- groupOTU(tree13, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 8), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
strengthMap13 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.899, 6.0, 6.1644, 6.3246)
treeplot13 <- ggtree(tree13grouped,
  aes(size=(strengthMap13[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree14 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,(((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree14grouped <- groupOTU(tree14, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
strengthMap14 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 6.0, 5.1962, 6.3246)
treeplot14 <- ggtree(tree14grouped,
  aes(size=(strengthMap14[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree15 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree15grouped <- groupOTU(tree15, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
strengthMap15 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 6.0, 6.1644, 4.7958)
treeplot15 <- ggtree(tree15grouped,
  aes(size=(strengthMap15[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree16 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree16grouped <- groupOTU(tree16, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
strengthMap16 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 6.0, 6.1644, 6.3246)
treeplot16 <- ggtree(tree16grouped,
  aes(size=(strengthMap16[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree17 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree17grouped <- groupOTU(tree17, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(10, 13)))
strengthMap17 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 3.7417, 6.1644, 4.7958)
treeplot17 <- ggtree(tree17grouped,
  aes(size=(strengthMap17[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree18 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,(9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree18grouped <- groupOTU(tree18, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(13, 15)))
strengthMap18 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 3.7417, 6.1644, 6.3246)
treeplot18 <- ggtree(tree18grouped,
  aes(size=(strengthMap18[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree19 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,(8,(9,10)9-10)8-10)6-10,11,12,(13,14,15)13-15,16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree19grouped <- groupOTU(tree19, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 10), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
strengthMap19 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 2.8284, 3.3166, 5.1962, 6.3246)
treeplot19 <- ggtree(tree19grouped,
  aes(size=(strengthMap19[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree20 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree20grouped <- groupOTU(tree20, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(8, 16), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
strengthMap20 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 3.3166, 5.1962, 6.3246)
treeplot20 <- ggtree(tree20grouped,
  aes(size=(strengthMap20[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree21 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,(8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree21grouped <- groupOTU(tree21, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(8, 16), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
strengthMap21 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 6.0, 5.1962, 6.3246)
treeplot21 <- ggtree(tree21grouped,
  aes(size=(strengthMap21[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree22 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,(8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree22grouped <- groupOTU(tree22, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
strengthMap22 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 6.0, 6.1644, 4.7958)
treeplot22 <- ggtree(tree22grouped,
  aes(size=(strengthMap22[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree23 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,(8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree23grouped <- groupOTU(tree23, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
strengthMap23 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 6.0, 6.1644, 6.3246)
treeplot23 <- ggtree(tree23grouped,
  aes(size=(strengthMap23[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree24 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree24grouped <- groupOTU(tree24, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(8, 16), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
strengthMap24 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 3.3166, 5.1962, 6.3246)
treeplot24 <- ggtree(tree24grouped,
  aes(size=(strengthMap24[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree25 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,((8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree25grouped <- groupOTU(tree25, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
strengthMap25 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 6.0, 5.1962, 6.3246)
treeplot25 <- ggtree(tree25grouped,
  aes(size=(strengthMap25[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree26 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,((8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree26grouped <- groupOTU(tree26, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
strengthMap26 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 6.0, 6.1644, 4.7958)
treeplot26 <- ggtree(tree26grouped,
  aes(size=(strengthMap26[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree27 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,((8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree27grouped <- groupOTU(tree27, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
strengthMap27 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 6.0, 6.1644, 6.3246)
treeplot27 <- ggtree(tree27grouped,
  aes(size=(strengthMap27[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree28 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,(((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree28grouped <- groupOTU(tree28, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
strengthMap28 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 5.0, 6.0, 5.1962, 6.3246)
treeplot28 <- ggtree(tree28grouped,
  aes(size=(strengthMap28[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree29 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree29grouped <- groupOTU(tree29, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
strengthMap29 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 5.0, 6.0, 6.1644, 4.7958)
treeplot29 <- ggtree(tree29grouped,
  aes(size=(strengthMap29[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree30 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree30grouped <- groupOTU(tree30, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
strengthMap30 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 5.0, 6.0, 6.1644, 6.3246)
treeplot30 <- ggtree(tree30grouped,
  aes(size=(strengthMap30[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree31 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree31grouped <- groupOTU(tree31, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(10, 13)))
strengthMap31 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 5.0, 3.7417, 6.1644, 4.7958)
treeplot31 <- ggtree(tree31grouped,
  aes(size=(strengthMap31[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree32 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,(9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree32grouped <- groupOTU(tree32, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(13, 15)))
strengthMap32 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 5.0, 3.7417, 6.1644, 6.3246)
treeplot32 <- ggtree(tree32grouped,
  aes(size=(strengthMap32[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree33 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,((((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree33grouped <- groupOTU(tree33, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(9, 10), l = c(13, 15)))
strengthMap33 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 6.0, 5.1962, 6.3246)
treeplot33 <- ggtree(tree33grouped,
  aes(size=(strengthMap33[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree34 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree34grouped <- groupOTU(tree34, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(10, 16), l = c(10, 13)))
strengthMap34 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 6.0, 6.1644, 4.7958)
treeplot34 <- ggtree(tree34grouped,
  aes(size=(strengthMap34[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree35 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree35grouped <- groupOTU(tree35, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(10, 16), l = c(13, 15)))
strengthMap35 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 6.0, 6.1644, 6.3246)
treeplot35 <- ggtree(tree35grouped,
  aes(size=(strengthMap35[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree36 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,((9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree36grouped <- groupOTU(tree36, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(10, 17), k = c(10, 16), l = c(10, 13)))
strengthMap36 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 3.7417, 6.1644, 4.7958)
treeplot36 <- ggtree(tree36grouped,
  aes(size=(strengthMap36[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree37 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,((9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree37grouped <- groupOTU(tree37, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(10, 17), k = c(10, 16), l = c(13, 15)))
strengthMap37 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 3.7417, 6.1644, 6.3246)
treeplot37 <- ggtree(tree37grouped,
  aes(size=(strengthMap37[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree38 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(9,((((10,11,12,13)10-13,14,15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree38grouped <- groupOTU(tree38, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(10, 18), j = c(10, 17), k = c(10, 16), l = c(10, 13)))
strengthMap38 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 2.0, 3.7417, 6.1644, 4.7958)
treeplot38 <- ggtree(tree38grouped,
  aes(size=(strengthMap38[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree39 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(9,(((10,11,12,(13,14,15)13-15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree39grouped <- groupOTU(tree39, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(10, 18), j = c(10, 17), k = c(10, 16), l = c(13, 15)))
strengthMap39 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 2.0, 3.7417, 6.1644, 6.3246)
treeplot39 <- ggtree(tree39grouped,
  aes(size=(strengthMap39[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree40 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,((((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree40grouped <- groupOTU(tree40, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(9, 10), l = c(13, 15)))
strengthMap40 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 6.0, 5.1962, 6.3246)
treeplot40 <- ggtree(tree40grouped,
  aes(size=(strengthMap40[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree41 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,(((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree41grouped <- groupOTU(tree41, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(10, 16), l = c(10, 13)))
strengthMap41 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 6.0, 6.1644, 4.7958)
treeplot41 <- ggtree(tree41grouped,
  aes(size=(strengthMap41[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree42 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,(((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree42grouped <- groupOTU(tree42, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(10, 16), l = c(13, 15)))
strengthMap42 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 6.0, 6.1644, 6.3246)
treeplot42 <- ggtree(tree42grouped,
  aes(size=(strengthMap42[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree43 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,((9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree43grouped <- groupOTU(tree43, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(10, 17), k = c(10, 16), l = c(10, 13)))
strengthMap43 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 3.7417, 6.1644, 4.7958)
treeplot43 <- ggtree(tree43grouped,
  aes(size=(strengthMap43[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree44 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,((9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree44grouped <- groupOTU(tree44, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(10, 17), k = c(10, 16), l = c(13, 15)))
strengthMap44 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 3.7417, 6.1644, 6.3246)
treeplot44 <- ggtree(tree44grouped,
  aes(size=(strengthMap44[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree45 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,(9,((((10,11,12,13)10-13,14,15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree45grouped <- groupOTU(tree45, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(10, 18), j = c(10, 17), k = c(10, 16), l = c(10, 13)))
strengthMap45 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 2.0, 3.7417, 6.1644, 4.7958)
treeplot45 <- ggtree(tree45grouped,
  aes(size=(strengthMap45[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree46 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,(9,(((10,11,12,(13,14,15)13-15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree46grouped <- groupOTU(tree46, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(10, 18), j = c(10, 17), k = c(10, 16), l = c(13, 15)))
strengthMap46 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 2.0, 3.7417, 6.1644, 6.3246)
treeplot46 <- ggtree(tree46grouped,
  aes(size=(strengthMap46[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree47 <- read.tree(text="(1,(2,(3,4,((((((5,6)5-6,7,(8,(9,10)9-10)8-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree47grouped <- groupOTU(tree47, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(5, 6), j = c(8, 10), k = c(9, 10)))
strengthMap47 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 4.899, 3.3166, 5.1962)
treeplot47 <- ggtree(tree47grouped,
  aes(size=(strengthMap47[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree48 <- read.tree(text="(1,(2,(3,4,(((5,6)5-6,7,((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree48grouped <- groupOTU(tree48, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 6), g = c(8, 16), h = c(8, 10), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
strengthMap48 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.899, 4.4721, 3.3166, 5.1962, 6.3246, 4.2426)
treeplot48 <- ggtree(tree48grouped,
  aes(size=(strengthMap48[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree49 <- read.tree(text="(1,(2,(3,4,(((5,6)5-6,7,(8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree49grouped <- groupOTU(tree49, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 6), g = c(8, 16), h = c(9, 16), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
strengthMap49 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.899, 4.4721, 6.0, 5.1962, 6.3246, 4.2426)
treeplot49 <- ggtree(tree49grouped,
  aes(size=(strengthMap49[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree50 <- read.tree(text="(1,(2,(3,4,(((5,6)5-6,7,(8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree50grouped <- groupOTU(tree50, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 6), g = c(8, 16), h = c(9, 16), i = c(10, 16), j = c(10, 13), k = c(17, 19)))
strengthMap50 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.899, 4.4721, 6.0, 6.1644, 4.7958, 4.2426)
treeplot50 <- ggtree(tree50grouped,
  aes(size=(strengthMap50[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree51 <- read.tree(text="(1,(2,(3,4,(((5,6)5-6,7,(8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree51grouped <- groupOTU(tree51, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 6), g = c(8, 16), h = c(9, 16), i = c(10, 16), j = c(13, 15), k = c(17, 19)))
strengthMap51 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.899, 4.4721, 6.0, 6.1644, 6.3246, 4.2426)
treeplot51 <- ggtree(tree51grouped,
  aes(size=(strengthMap51[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree52 <- read.tree(text="(1,(2,(3,4,(((((5,((6,7,8)6-8,(9,10)9-10)6-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree52grouped <- groupOTU(tree52, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(6, 10), j = c(6, 8), k = c(9, 10)))
strengthMap52 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 2.8284, 4.899, 5.1962)
treeplot52 <- ggtree(tree52grouped,
  aes(size=(strengthMap52[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree53 <- read.tree(text="(1,(2,(3,4,(((((5,(6,7,(8,(9,10)9-10)8-10)6-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree53grouped <- groupOTU(tree53, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(6, 10), j = c(8, 10), k = c(9, 10)))
strengthMap53 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 2.8284, 3.3166, 5.1962)
treeplot53 <- ggtree(tree53grouped,
  aes(size=(strengthMap53[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree54 <- read.tree(text="(1,(2,(3,4,((5,(((6,7,8)6-8,(9,10)9-10)6-10,11,12,(13,14,15)13-15,16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree54grouped <- groupOTU(tree54, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 10), h = c(6, 8), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
strengthMap54 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 2.8284, 4.899, 5.1962, 6.3246, 4.2426)
treeplot54 <- ggtree(tree54grouped,
  aes(size=(strengthMap54[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree55 <- read.tree(text="(1,(2,(3,4,((5,((6,7,8)6-8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree55grouped <- groupOTU(tree55, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 8), h = c(9, 16), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
strengthMap55 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.899, 6.0, 5.1962, 6.3246, 4.2426)
treeplot55 <- ggtree(tree55grouped,
  aes(size=(strengthMap55[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree56 <- read.tree(text="(1,(2,(3,4,((5,((6,7,8)6-8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree56grouped <- groupOTU(tree56, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 8), h = c(9, 16), i = c(10, 16), j = c(10, 13), k = c(17, 19)))
strengthMap56 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.899, 6.0, 6.1644, 4.7958, 4.2426)
treeplot56 <- ggtree(tree56grouped,
  aes(size=(strengthMap56[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree57 <- read.tree(text="(1,(2,(3,4,((5,((6,7,8)6-8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree57grouped <- groupOTU(tree57, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 8), h = c(9, 16), i = c(10, 16), j = c(13, 15), k = c(17, 19)))
strengthMap57 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.899, 6.0, 6.1644, 6.3246, 4.2426)
treeplot57 <- ggtree(tree57grouped,
  aes(size=(strengthMap57[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree58 <- read.tree(text="(1,(2,(3,4,((5,((6,7,(8,(9,10)9-10)8-10)6-10,11,12,(13,14,15)13-15,16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree58grouped <- groupOTU(tree58, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 10), h = c(8, 10), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
strengthMap58 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 2.8284, 3.3166, 5.1962, 6.3246, 4.2426)
treeplot58 <- ggtree(tree58grouped,
  aes(size=(strengthMap58[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree59 <- read.tree(text="(1,(2,(3,4,((5,(6,7,((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree59grouped <- groupOTU(tree59, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(8, 16), h = c(8, 10), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
strengthMap59 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.4721, 3.3166, 5.1962, 6.3246, 4.2426)
treeplot59 <- ggtree(tree59grouped,
  aes(size=(strengthMap59[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree60 <- read.tree(text="(1,(2,(3,4,((5,(6,7,(8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree60grouped <- groupOTU(tree60, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(8, 16), h = c(9, 16), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
strengthMap60 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.4721, 6.0, 5.1962, 6.3246, 4.2426)
treeplot60 <- ggtree(tree60grouped,
  aes(size=(strengthMap60[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree61 <- read.tree(text="(1,(2,(3,4,((5,(6,7,(8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree61grouped <- groupOTU(tree61, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(8, 16), h = c(9, 16), i = c(10, 16), j = c(10, 13), k = c(17, 19)))
strengthMap61 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.4721, 6.0, 6.1644, 4.7958, 4.2426)
treeplot61 <- ggtree(tree61grouped,
  aes(size=(strengthMap61[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree62 <- read.tree(text="(1,(2,(3,4,((5,(6,7,(8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree62grouped <- groupOTU(tree62, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(8, 16), h = c(9, 16), i = c(10, 16), j = c(13, 15), k = c(17, 19)))
strengthMap62 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.4721, 6.0, 6.1644, 6.3246, 4.2426)
treeplot62 <- ggtree(tree62grouped,
  aes(size=(strengthMap62[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree63 <- read.tree(text="(1,(2,(3,4,((((((5,6)5-6,7,8,9,(10,11,12,13)10-13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree63grouped <- groupOTU(tree63, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(5, 6), j = c(10, 13)))
strengthMap63 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 4.899, 4.7958)
treeplot63 <- ggtree(tree63grouped,
  aes(size=(strengthMap63[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree64 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,(8,(9,10)9-10)8-10,11,12,13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree64grouped <- groupOTU(tree64, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(5, 6), h = c(8, 10), i = c(9, 10), j = c(17, 19)))
strengthMap64 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 4.899, 3.3166, 5.1962, 4.2426)
treeplot64 <- ggtree(tree64grouped,
  aes(size=(strengthMap64[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree65 <- read.tree(text="(1,(2,(3,4,(((((5,(6,7,8)6-8,9,(10,11,12,13)10-13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree65grouped <- groupOTU(tree65, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(6, 8), j = c(10, 13)))
strengthMap65 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 4.899, 4.7958)
treeplot65 <- ggtree(tree65grouped,
  aes(size=(strengthMap65[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree66 <- read.tree(text="(1,(2,(3,4,(((5,((6,7,8)6-8,(9,10)9-10)6-10,11,12,13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree66grouped <- groupOTU(tree66, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(6, 10), h = c(6, 8), i = c(9, 10), j = c(17, 19)))
strengthMap66 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 2.8284, 4.899, 5.1962, 4.2426)
treeplot66 <- ggtree(tree66grouped,
  aes(size=(strengthMap66[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree67 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,(8,(9,10)9-10)8-10)6-10,11,12,13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree67grouped <- groupOTU(tree67, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(6, 10), h = c(8, 10), i = c(9, 10), j = c(17, 19)))
strengthMap67 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 2.8284, 3.3166, 5.1962, 4.2426)
treeplot67 <- ggtree(tree67grouped,
  aes(size=(strengthMap67[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree68 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,9,(10,11,12,13)10-13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree68grouped <- groupOTU(tree68, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(5, 6), h = c(10, 13), i = c(17, 19)))
strengthMap68 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 4.899, 4.7958, 4.2426)
treeplot68 <- ggtree(tree68grouped,
  aes(size=(strengthMap68[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

tree69 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,9,(10,11,12,13)10-13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
tree69grouped <- groupOTU(tree69, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(6, 8), h = c(10, 13), i = c(17, 19)))
strengthMap69 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 4.899, 4.7958, 4.2426)
treeplot69 <- ggtree(tree69grouped,
  aes(size=(strengthMap69[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, alpha=0,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none") +
  scale_size_identity()

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
  treeplot1 +
  treeplot2 +
  treeplot3 +
  treeplot4 +
  treeplot5 +
  treeplot6 +
  treeplot7 +
  treeplot8 +
  treeplot9 +
  treeplot10 +
  treeplot11 +
  treeplot12 +
  treeplot13 +
  treeplot14 +
  treeplot15 +
  treeplot16 +
  treeplot17 +
  treeplot18 +
  treeplot19 +
  treeplot20 +
  treeplot21 +
  treeplot22 +
  treeplot23 +
  treeplot24 +
  treeplot25 +
  treeplot26 +
  treeplot27 +
  treeplot28 +
  treeplot29 +
  treeplot30 +
  treeplot31 +
  treeplot32 +
  treeplot33 +
  treeplot34 +
  treeplot35 +
  treeplot36 +
  treeplot37 +
  treeplot38 +
  treeplot39 +
  treeplot40 +
  treeplot41 +
  treeplot42 +
  treeplot43 +
  treeplot44 +
  treeplot45 +
  treeplot46 +
  treeplot47 +
  treeplot48 +
  treeplot49 +
  treeplot50 +
  treeplot51 +
  treeplot52 +
  treeplot53 +
  treeplot54 +
  treeplot55 +
  treeplot56 +
  treeplot57 +
  treeplot58 +
  treeplot59 +
  treeplot60 +
  treeplot61 +
  treeplot62 +
  treeplot63 +
  treeplot64 +
  treeplot65 +
  treeplot66 +
  treeplot67 +
  treeplot68 +
  treeplot69 +
  plot_layout(design=treelayout))
print(forest)
