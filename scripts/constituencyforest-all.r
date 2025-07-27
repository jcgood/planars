library(ape)
library(ggplot2)
library(ggtree)
library(patchwork)

tree1 = read.tree(text="(1, (2, (3, 4, (((5, ((6, 7, (8, (9, ((10, 11, 12, (13, 14, 15) 13-15, 16) 10-16, 17) 10-17) 9-17) 8-17) 6-17, 18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree1grouped = groupOTU(tree1, list(a = c(5, 18), b = c(6, 18), c = c(10, 16), d = c(13, 15), e = c(1, 22), f = c(2, 22), g = c(5, 19), h = c(3, 21), i = c(9, 17), j = c(5, 21), k = c(8, 17), l = c(6, 17), m = c(10, 17)))
strengthMap1 = c( .5, 1, 1, 1, 1, 2, 2, 2, 4, 4, 5, 5, 6, 8)
treeplot1 = ggtree(tree1grouped, aes(size=(strengthMap1[group])), layout='slanted', ladderize = FALSE, alpha=0.111111) + layout_dendrogram() + geom_tiplab(size=5, angle=0, offset=-.5, hjust=.5, alpha=0.111111) + theme(panel.background = element_blank(),  plot.background = element_blank()) + theme(legend.position="none") + scale_size_identity()

tree2 = read.tree(text="(1, (2, (3, 4, ((((5, (6, 7, (8, (9, ((10, 11, 12, (13, 14, 15) 13-15, 16) 10-16, 17) 10-17) 9-17) 8-17) 6-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree2grouped = groupOTU(tree2, list(a = c(5, 18), b = c(10, 16), c = c(13, 15), d = c(1, 22), e = c(2, 22), f = c(5, 19), g = c(3, 21), h = c(9, 17), i = c(5, 21), j = c(8, 17), k = c(6, 17), l = c(5, 17), m = c(10, 17)))
strengthMap2 = c( .5, 1, 1, 1, 2, 2, 2, 4, 4, 5, 5, 6, 7, 8)
treeplot2 = ggtree(tree2grouped, aes(size=(strengthMap2[group])), layout='slanted', ladderize = FALSE, alpha=0.111111) + layout_dendrogram() + geom_tiplab(size=5, angle=0, offset=-.5, hjust=.5, alpha=0.111111) + theme(panel.background = element_blank(),  plot.background = element_blank()) + theme(legend.position="none") + scale_size_identity()

tree3 = read.tree(text="(1, (2, (3, 4, (((5, (6, 7, 8, ((9, ((10, 11, 12, (13, 14, 15) 13-15, 16) 10-16, 17) 10-17) 9-17, 18) 9-18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree3grouped = groupOTU(tree3, list(a = c(5, 18), b = c(6, 18), c = c(10, 16), d = c(13, 15), e = c(1, 22), f = c(2, 22), g = c(5, 19), h = c(9, 18), i = c(3, 21), j = c(9, 17), k = c(5, 21), l = c(10, 17)))
strengthMap3 = c( .5, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 5, 8)
treeplot3 = ggtree(tree3grouped, aes(size=(strengthMap3[group])), layout='slanted', ladderize = FALSE, alpha=0.111111) + layout_dendrogram() + geom_tiplab(size=5, angle=0, offset=-.5, hjust=.5, alpha=0.111111) + theme(panel.background = element_blank(),  plot.background = element_blank()) + theme(legend.position="none") + scale_size_identity()

tree4 = read.tree(text="(1, (2, (3, 4, (((5, (6, 7, 8, (9, (((10, 11, 12, (13, 14, 15) 13-15, 16) 10-16, 17) 10-17, 18) 10-18) 9-18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree4grouped = groupOTU(tree4, list(a = c(5, 18), b = c(6, 18), c = c(10, 16), d = c(13, 15), e = c(1, 22), f = c(2, 22), g = c(5, 19), h = c(9, 18), i = c(10, 18), j = c(3, 21), k = c(5, 21), l = c(10, 17)))
strengthMap4 = c( .5, 1, 1, 1, 1, 2, 2, 2, 2, 2, 4, 5, 8)
treeplot4 = ggtree(tree4grouped, aes(size=(strengthMap4[group])), layout='slanted', ladderize = FALSE, alpha=0.111111) + layout_dendrogram() + geom_tiplab(size=5, angle=0, offset=-.5, hjust=.5, alpha=0.111111) + theme(panel.background = element_blank(),  plot.background = element_blank()) + theme(legend.position="none") + scale_size_identity()

tree5 = read.tree(text="(1, (2, (3, 4, (((5, ((((6, 7, 8) 6-8, 9, 10) 6-10, 11, 12, 13, 14, 15, 16, 17) 6-17, 18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree5grouped = groupOTU(tree5, list(a = c(5, 18), b = c(6, 18), c = c(1, 22), d = c(2, 22), e = c(5, 19), f = c(6, 10), g = c(6, 8), h = c(3, 21), i = c(5, 21), j = c(6, 17)))
strengthMap5 = c( .5, 1, 1, 2, 2, 2, 2, 2, 4, 5, 6)
treeplot5 = ggtree(tree5grouped, aes(size=(strengthMap5[group])), layout='slanted', ladderize = FALSE, alpha=0.111111) + layout_dendrogram() + geom_tiplab(size=5, angle=0, offset=-.5, hjust=.5, alpha=0.111111) + theme(panel.background = element_blank(),  plot.background = element_blank()) + theme(legend.position="none") + scale_size_identity()

tree6 = read.tree(text="(1, (2, (3, 4, ((((5, (((6, 7, 8) 6-8, 9, 10) 6-10, 11, 12, 13, 14, 15, 16, 17) 6-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree6grouped = groupOTU(tree6, list(a = c(5, 18), b = c(1, 22), c = c(2, 22), d = c(5, 19), e = c(6, 10), f = c(6, 8), g = c(3, 21), h = c(5, 21), i = c(6, 17), j = c(5, 17)))
strengthMap6 = c( .5, 1, 2, 2, 2, 2, 2, 4, 5, 6, 7)
treeplot6 = ggtree(tree6grouped, aes(size=(strengthMap6[group])), layout='slanted', ladderize = FALSE, alpha=0.111111) + layout_dendrogram() + geom_tiplab(size=5, angle=0, offset=-.5, hjust=.5, alpha=0.111111) + theme(panel.background = element_blank(),  plot.background = element_blank()) + theme(legend.position="none") + scale_size_identity()

tree7 = read.tree(text="(1, (2, (3, 4, ((((5, ((6, 7, 8) 6-8, 9, 10) 6-10, 11, 12, 13) 5-13, 14, 15, 16, 17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree7grouped = groupOTU(tree7, list(a = c(5, 18), b = c(5, 13), c = c(1, 22), d = c(2, 22), e = c(5, 19), f = c(6, 10), g = c(6, 8), h = c(3, 21), i = c(5, 21)))
strengthMap7 = c( .5, 1, 1, 2, 2, 2, 2, 2, 4, 5)
treeplot7 = ggtree(tree7grouped, aes(size=(strengthMap7[group])), layout='slanted', ladderize = FALSE, alpha=0.111111) + layout_dendrogram() + geom_tiplab(size=5, angle=0, offset=-.5, hjust=.5, alpha=0.111111) + theme(panel.background = element_blank(),  plot.background = element_blank()) + theme(legend.position="none") + scale_size_identity()

tree8 = read.tree(text="(1, (2, (3, 4, ((((5, 6) 5-6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree8grouped = groupOTU(tree8, list(a = c(5, 18), b = c(5, 6), c = c(1, 22), d = c(2, 22), e = c(5, 19), f = c(3, 21), g = c(5, 21)))
strengthMap8 = c( .5, 1, 1, 2, 2, 2, 4, 5)
treeplot8 = ggtree(tree8grouped, aes(size=(strengthMap8[group])), layout='slanted', ladderize = FALSE, alpha=0.111111) + layout_dendrogram() + geom_tiplab(size=5, angle=0, offset=-.5, hjust=.5, alpha=0.111111) + theme(panel.background = element_blank(),  plot.background = element_blank()) + theme(legend.position="none") + scale_size_identity()

tree9 = read.tree(text="(1, (2, (3, 4, ((5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, (17, 18, 19) 17-19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree9grouped = groupOTU(tree9, list(a = c(17, 19), b = c(1, 22), c = c(2, 22), d = c(5, 19), e = c(3, 21), f = c(5, 21)))
strengthMap9 = c( .5, 1, 2, 2, 2, 4, 5)
treeplot9 = ggtree(tree9grouped, aes(size=(strengthMap9[group])), layout='slanted', ladderize = FALSE, alpha=0.111111) + layout_dendrogram() + geom_tiplab(size=5, angle=0, offset=-.5, hjust=.5, alpha=0.111111) + theme(panel.background = element_blank(),  plot.background = element_blank()) + theme(legend.position="none") + scale_size_identity()


treelayout <- c(
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1))

print(
treeplot1+
treeplot2+
treeplot3+
treeplot4+
treeplot5+
treeplot6+
treeplot7+
treeplot8+
treeplot9+
plot_layout(design = treelayout))
