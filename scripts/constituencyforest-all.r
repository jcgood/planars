library(ape)
library(ggplot2)
library(ggtree)
library(patchwork)

posLabel = list("1" = "QM",
"2" = "PreSbj",
"3" = "Sbj",
"4" = "PostSbj",
"5" = "Neg1",
"6" = "SM",
"7" = "Neg2",
"8" = "TAM",
"9" = "OM",
"10" = "Root",
"11" = "Ext",
"12" = "STAT",
"13" = "CAUS",
"14" = "APPL",
"15" = "REC",
"16" = "PASS",
"17" = "FV",
"18" = "2P",
"19" = "Enc",
"20" = "Obj1",
"21" = "Obj2",
"22" = "PostObj")

tree1 = read.tree(text="(1, (2, (3, 4, (((5, ((6, (7, (8, (9, ((10, 11, 12, (13, 14, 15) 13-15, 16) 10-16, 17) 10-17) 9-17) 8-17) 7-17) 6-17, 18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree1grouped = groupOTU(tree1, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(7, 17), e = c(10, 16), f = c(13, 15), g = c(1, 22), h = c(2, 22), i = c(3, 21), j = c(5, 21), k = c(9, 17), l = c(10, 17), m = c(8, 17), n = c(6, 17)))
strengthMap1 = c( .5, 1, 1, 1, 1, 1, 1, 2, 2, 4, 5, 5, 6, 8, 16)
treeplot1 = ggtree(tree1grouped,
	aes(size=(strengthMap1[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=1,
	aes(label=paste(label, posLabel[label], sep="\n")), lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree2 = read.tree(text="(1, (2, (3, 4, (((5, ((6, (7, (8, ((9, (10, 11, 12, (13, 14, 15) 13-15, 16) 10-16) 9-16, 17) 9-17) 8-17) 7-17) 6-17, 18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree2grouped = groupOTU(tree2, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(7, 17), e = c(9, 16), f = c(10, 16), g = c(13, 15), h = c(1, 22), i = c(2, 22), j = c(3, 21), k = c(5, 21), l = c(9, 17), m = c(8, 17), n = c(6, 17)))
strengthMap2 = c( .5, 1, 1, 1, 1, 1, 1, 1, 2, 2, 4, 5, 5, 8, 16)
treeplot2 = ggtree(tree2grouped,
	aes(size=(strengthMap2[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree3 = read.tree(text="(1, (2, (3, 4, (((5, ((6, (7, ((8, (9, (10, 11, 12, (13, 14, 15) 13-15, 16) 10-16) 9-16) 8-16, 17) 8-17) 7-17) 6-17, 18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree3grouped = groupOTU(tree3, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(7, 17), e = c(9, 16), f = c(10, 16), g = c(13, 15), h = c(1, 22), i = c(2, 22), j = c(8, 16), k = c(3, 21), l = c(5, 21), m = c(8, 17), n = c(6, 17)))
strengthMap3 = c( .5, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 4, 5, 8, 16)
treeplot3 = ggtree(tree3grouped,
	aes(size=(strengthMap3[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree4 = read.tree(text="(1, (2, (3, 4, ((((5, (6, (7, (8, (9, ((10, 11, 12, (13, 14, 15) 13-15, 16) 10-16, 17) 10-17) 9-17) 8-17) 7-17) 6-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree4grouped = groupOTU(tree4, list(a = c(5, 19), b = c(5, 18), c = c(7, 17), d = c(10, 16), e = c(13, 15), f = c(1, 22), g = c(2, 22), h = c(3, 21), i = c(5, 21), j = c(5, 17), k = c(9, 17), l = c(10, 17), m = c(8, 17), n = c(6, 17)))
strengthMap4 = c( .5, 1, 1, 1, 1, 1, 2, 2, 4, 5, 5, 5, 6, 8, 16)
treeplot4 = ggtree(tree4grouped,
	aes(size=(strengthMap4[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree5 = read.tree(text="(1, (2, (3, 4, ((((5, (6, (7, (8, ((9, (10, 11, 12, (13, 14, 15) 13-15, 16) 10-16) 9-16, 17) 9-17) 8-17) 7-17) 6-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree5grouped = groupOTU(tree5, list(a = c(5, 19), b = c(5, 18), c = c(7, 17), d = c(9, 16), e = c(10, 16), f = c(13, 15), g = c(1, 22), h = c(2, 22), i = c(3, 21), j = c(5, 21), k = c(5, 17), l = c(9, 17), m = c(8, 17), n = c(6, 17)))
strengthMap5 = c( .5, 1, 1, 1, 1, 1, 1, 2, 2, 4, 5, 5, 5, 8, 16)
treeplot5 = ggtree(tree5grouped,
	aes(size=(strengthMap5[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree6 = read.tree(text="(1, (2, (3, 4, ((((5, (6, (7, ((8, (9, (10, 11, 12, (13, 14, 15) 13-15, 16) 10-16) 9-16) 8-16, 17) 8-17) 7-17) 6-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree6grouped = groupOTU(tree6, list(a = c(5, 19), b = c(5, 18), c = c(7, 17), d = c(9, 16), e = c(10, 16), f = c(13, 15), g = c(1, 22), h = c(2, 22), i = c(8, 16), j = c(3, 21), k = c(5, 21), l = c(5, 17), m = c(8, 17), n = c(6, 17)))
strengthMap6 = c( .5, 1, 1, 1, 1, 1, 1, 2, 2, 2, 4, 5, 5, 8, 16)
treeplot6 = ggtree(tree6grouped,
	aes(size=(strengthMap6[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree7 = read.tree(text="(1, (2, (3, 4, (((5, (((6, 7, 8, (9, ((10, 11, 12, (13, 14, 15) 13-15, 16) 10-16, 17) 10-17) 9-17) 6-16) 6-17, 18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree7grouped = groupOTU(tree7, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(10, 16), e = c(13, 15), f = c(1, 22), g = c(2, 22), h = c(3, 21), i = c(5, 21), j = c(9, 17), k = c(10, 17), l = c(6, 16), m = c(6, 17)))
strengthMap7 = c( .5, 1, 1, 1, 1, 1, 2, 2, 4, 5, 5, 6, 10, 16)
treeplot7 = ggtree(tree7grouped,
	aes(size=(strengthMap7[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree8 = read.tree(text="(1, (2, (3, 4, (((5, (((6, 7, 8, ((9, (10, 11, 12, (13, 14, 15) 13-15, 16) 10-16) 9-16, 17) 9-17) 6-16) 6-17, 18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree8grouped = groupOTU(tree8, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(9, 16), e = c(10, 16), f = c(13, 15), g = c(1, 22), h = c(2, 22), i = c(3, 21), j = c(5, 21), k = c(9, 17), l = c(6, 16), m = c(6, 17)))
strengthMap8 = c( .5, 1, 1, 1, 1, 1, 1, 2, 2, 4, 5, 5, 10, 16)
treeplot8 = ggtree(tree8grouped,
	aes(size=(strengthMap8[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree9 = read.tree(text="(1, (2, (3, 4, (((5, (((6, 7, (8, (9, (10, 11, 12, (13, 14, 15) 13-15, 16) 10-16) 9-16) 8-16) 6-16, 17) 6-17, 18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree9grouped = groupOTU(tree9, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(9, 16), e = c(10, 16), f = c(13, 15), g = c(1, 22), h = c(2, 22), i = c(8, 16), j = c(3, 21), k = c(5, 21), l = c(6, 16), m = c(6, 17)))
strengthMap9 = c( .5, 1, 1, 1, 1, 1, 1, 2, 2, 2, 4, 5, 10, 16)
treeplot9 = ggtree(tree9grouped,
	aes(size=(strengthMap9[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree10 = read.tree(text="(1, (2, (3, 4, ((((5, ((6, 7, 8, (9, ((10, 11, 12, (13, 14, 15) 13-15, 16) 10-16, 17) 10-17) 9-17) 6-16) 6-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree10grouped = groupOTU(tree10, list(a = c(5, 19), b = c(5, 18), c = c(10, 16), d = c(13, 15), e = c(1, 22), f = c(2, 22), g = c(3, 21), h = c(5, 21), i = c(5, 17), j = c(9, 17), k = c(10, 17), l = c(6, 16), m = c(6, 17)))
strengthMap10 = c( .5, 1, 1, 1, 1, 2, 2, 4, 5, 5, 5, 6, 10, 16)
treeplot10 = ggtree(tree10grouped,
	aes(size=(strengthMap10[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree11 = read.tree(text="(1, (2, (3, 4, ((((5, ((6, 7, 8, ((9, (10, 11, 12, (13, 14, 15) 13-15, 16) 10-16) 9-16, 17) 9-17) 6-16) 6-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree11grouped = groupOTU(tree11, list(a = c(5, 19), b = c(5, 18), c = c(9, 16), d = c(10, 16), e = c(13, 15), f = c(1, 22), g = c(2, 22), h = c(3, 21), i = c(5, 21), j = c(5, 17), k = c(9, 17), l = c(6, 16), m = c(6, 17)))
strengthMap11 = c( .5, 1, 1, 1, 1, 1, 2, 2, 4, 5, 5, 5, 10, 16)
treeplot11 = ggtree(tree11grouped,
	aes(size=(strengthMap11[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree12 = read.tree(text="(1, (2, (3, 4, ((((5, ((6, 7, (8, (9, (10, 11, 12, (13, 14, 15) 13-15, 16) 10-16) 9-16) 8-16) 6-16, 17) 6-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree12grouped = groupOTU(tree12, list(a = c(5, 19), b = c(5, 18), c = c(9, 16), d = c(10, 16), e = c(13, 15), f = c(1, 22), g = c(2, 22), h = c(8, 16), i = c(3, 21), j = c(5, 21), k = c(5, 17), l = c(6, 16), m = c(6, 17)))
strengthMap12 = c( .5, 1, 1, 1, 1, 1, 2, 2, 2, 4, 5, 5, 10, 16)
treeplot12 = ggtree(tree12grouped,
	aes(size=(strengthMap12[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree13 = read.tree(text="(1, (2, (3, 4, (((5, (6, 7, 8, ((9, ((10, 11, 12, (13, 14, 15) 13-15, 16) 10-16, 17) 10-17) 9-17, 18) 9-18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree13grouped = groupOTU(tree13, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(10, 16), e = c(13, 15), f = c(1, 22), g = c(2, 22), h = c(9, 18), i = c(3, 21), j = c(5, 21), k = c(9, 17), l = c(10, 17)))
strengthMap13 = c( .5, 1, 1, 1, 1, 1, 2, 2, 2, 4, 5, 5, 6)
treeplot13 = ggtree(tree13grouped,
	aes(size=(strengthMap13[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree14 = read.tree(text="(1, (2, (3, 4, (((5, (6, 7, 8, (((9, (10, 11, 12, (13, 14, 15) 13-15, 16) 10-16) 9-16, 17) 9-17, 18) 9-18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree14grouped = groupOTU(tree14, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(9, 16), e = c(10, 16), f = c(13, 15), g = c(1, 22), h = c(2, 22), i = c(9, 18), j = c(3, 21), k = c(5, 21), l = c(9, 17)))
strengthMap14 = c( .5, 1, 1, 1, 1, 1, 1, 2, 2, 2, 4, 5, 5)
treeplot14 = ggtree(tree14grouped,
	aes(size=(strengthMap14[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree15 = read.tree(text="(1, (2, (3, 4, (((5, (6, 7, 8, (9, (((10, 11, 12, (13, 14, 15) 13-15, 16) 10-16, 17) 10-17, 18) 10-18) 9-18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree15grouped = groupOTU(tree15, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(10, 16), e = c(13, 15), f = c(1, 22), g = c(2, 22), h = c(9, 18), i = c(10, 18), j = c(3, 21), k = c(5, 21), l = c(10, 17)))
strengthMap15 = c( .5, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 5, 6)
treeplot15 = ggtree(tree15grouped,
	aes(size=(strengthMap15[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree16 = read.tree(text="(1, (2, (3, 4, (((5, ((((6, 7, (8, (9, 10) 9-10) 8-10) 6-10, 11, 12, 13, 14, 15, 16) 6-16, 17) 6-17, 18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree16grouped = groupOTU(tree16, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(8, 10), e = c(9, 10), f = c(1, 22), g = c(2, 22), h = c(6, 10), i = c(3, 21), j = c(5, 21), k = c(6, 16), l = c(6, 17)))
strengthMap16 = c( .5, 1, 1, 1, 1, 1, 2, 2, 3, 4, 5, 10, 16)
treeplot16 = ggtree(tree16grouped,
	aes(size=(strengthMap16[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree17 = read.tree(text="(1, (2, (3, 4, (((5, ((6, (7, (8, ((9, 10) 9-10, 11, 12, 13, 14, 15, 16, 17) 9-17) 8-17) 7-17) 6-17, 18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree17grouped = groupOTU(tree17, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(7, 17), e = c(9, 10), f = c(1, 22), g = c(2, 22), h = c(3, 21), i = c(5, 21), j = c(9, 17), k = c(8, 17), l = c(6, 17)))
strengthMap17 = c( .5, 1, 1, 1, 1, 1, 2, 2, 4, 5, 5, 8, 16)
treeplot17 = ggtree(tree17grouped,
	aes(size=(strengthMap17[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree18 = read.tree(text="(1, (2, (3, 4, ((((5, (((6, 7, (8, (9, 10) 9-10) 8-10) 6-10, 11, 12, 13, 14, 15, 16) 6-16, 17) 6-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree18grouped = groupOTU(tree18, list(a = c(5, 19), b = c(5, 18), c = c(8, 10), d = c(9, 10), e = c(1, 22), f = c(2, 22), g = c(6, 10), h = c(3, 21), i = c(5, 21), j = c(5, 17), k = c(6, 16), l = c(6, 17)))
strengthMap18 = c( .5, 1, 1, 1, 1, 2, 2, 3, 4, 5, 5, 10, 16)
treeplot18 = ggtree(tree18grouped,
	aes(size=(strengthMap18[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree19 = read.tree(text="(1, (2, (3, 4, ((((5, (6, (7, (8, ((9, 10) 9-10, 11, 12, 13, 14, 15, 16, 17) 9-17) 8-17) 7-17) 6-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree19grouped = groupOTU(tree19, list(a = c(5, 19), b = c(5, 18), c = c(7, 17), d = c(9, 10), e = c(1, 22), f = c(2, 22), g = c(3, 21), h = c(5, 21), i = c(5, 17), j = c(9, 17), k = c(8, 17), l = c(6, 17)))
strengthMap19 = c( .5, 1, 1, 1, 1, 2, 2, 4, 5, 5, 5, 8, 16)
treeplot19 = ggtree(tree19grouped,
	aes(size=(strengthMap19[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree20 = read.tree(text="(1, (2, (3, 4, (((5, (((((6, 7, 8) 6-8, 9, 10) 6-10, 11, 12, 13, 14, 15, 16) 6-16, 17) 6-17, 18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree20grouped = groupOTU(tree20, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(1, 22), e = c(2, 22), f = c(6, 10), g = c(6, 8), h = c(3, 21), i = c(5, 21), j = c(6, 16), k = c(6, 17)))
strengthMap20 = c( .5, 1, 1, 1, 2, 2, 3, 3, 4, 5, 10, 16)
treeplot20 = ggtree(tree20grouped,
	aes(size=(strengthMap20[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree21 = read.tree(text="(1, (2, (3, 4, (((5, (((6, 7, 8, ((9, 10) 9-10, 11, 12, 13, 14, 15, 16, 17) 9-17) 6-16) 6-17, 18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree21grouped = groupOTU(tree21, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(9, 10), e = c(1, 22), f = c(2, 22), g = c(3, 21), h = c(5, 21), i = c(9, 17), j = c(6, 16), k = c(6, 17)))
strengthMap21 = c( .5, 1, 1, 1, 1, 2, 2, 4, 5, 5, 10, 16)
treeplot21 = ggtree(tree21grouped,
	aes(size=(strengthMap21[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree22 = read.tree(text="(1, (2, (3, 4, ((((5, ((((6, 7, 8) 6-8, 9, 10) 6-10, 11, 12, 13, 14, 15, 16) 6-16, 17) 6-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree22grouped = groupOTU(tree22, list(a = c(5, 19), b = c(5, 18), c = c(1, 22), d = c(2, 22), e = c(6, 10), f = c(6, 8), g = c(3, 21), h = c(5, 21), i = c(5, 17), j = c(6, 16), k = c(6, 17)))
strengthMap22 = c( .5, 1, 1, 2, 2, 3, 3, 4, 5, 5, 10, 16)
treeplot22 = ggtree(tree22grouped,
	aes(size=(strengthMap22[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree23 = read.tree(text="(1, (2, (3, 4, ((((5, ((6, 7, 8, ((9, 10) 9-10, 11, 12, 13, 14, 15, 16, 17) 9-17) 6-16) 6-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree23grouped = groupOTU(tree23, list(a = c(5, 19), b = c(5, 18), c = c(9, 10), d = c(1, 22), e = c(2, 22), f = c(3, 21), g = c(5, 21), h = c(5, 17), i = c(9, 17), j = c(6, 16), k = c(6, 17)))
strengthMap23 = c( .5, 1, 1, 1, 2, 2, 4, 5, 5, 5, 10, 16)
treeplot23 = ggtree(tree23grouped,
	aes(size=(strengthMap23[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree24 = read.tree(text="(1, (2, (3, 4, ((((5, (6, 7, (8, (9, 10) 9-10) 8-10) 6-10, 11, 12, 13) 5-13, 14, 15, 16, 17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree24grouped = groupOTU(tree24, list(a = c(5, 19), b = c(5, 18), c = c(5, 13), d = c(8, 10), e = c(9, 10), f = c(1, 22), g = c(2, 22), h = c(6, 10), i = c(3, 21), j = c(5, 21)))
strengthMap24 = c( .5, 1, 1, 1, 1, 1, 2, 2, 3, 4, 5)
treeplot24 = ggtree(tree24grouped,
	aes(size=(strengthMap24[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree25 = read.tree(text="(1, (2, (3, 4, (((5, (6, 7, 8, (((9, 10) 9-10, 11, 12, 13, 14, 15, 16, 17) 9-17, 18) 9-18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree25grouped = groupOTU(tree25, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(9, 10), e = c(1, 22), f = c(2, 22), g = c(9, 18), h = c(3, 21), i = c(5, 21), j = c(9, 17)))
strengthMap25 = c( .5, 1, 1, 1, 1, 2, 2, 2, 4, 5, 5)
treeplot25 = ggtree(tree25grouped,
	aes(size=(strengthMap25[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree26 = read.tree(text="(1, (2, (3, 4, (((5, (((6, 7, 8, 9, (10, 11, 12, 13) 10-13, 14, 15, 16) 6-16, 17) 6-17, 18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree26grouped = groupOTU(tree26, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(10, 13), e = c(1, 22), f = c(2, 22), g = c(3, 21), h = c(5, 21), i = c(6, 16), j = c(6, 17)))
strengthMap26 = c( .5, 1, 1, 1, 1, 2, 2, 4, 5, 10, 16)
treeplot26 = ggtree(tree26grouped,
	aes(size=(strengthMap26[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree27 = read.tree(text="(1, (2, (3, 4, ((((5, ((6, 7, 8, 9, (10, 11, 12, 13) 10-13, 14, 15, 16) 6-16, 17) 6-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree27grouped = groupOTU(tree27, list(a = c(5, 19), b = c(5, 18), c = c(10, 13), d = c(1, 22), e = c(2, 22), f = c(3, 21), g = c(5, 21), h = c(5, 17), i = c(6, 16), j = c(6, 17)))
strengthMap27 = c( .5, 1, 1, 1, 2, 2, 4, 5, 5, 10, 16)
treeplot27 = ggtree(tree27grouped,
	aes(size=(strengthMap27[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree28 = read.tree(text="(1, (2, (3, 4, ((((5, ((6, 7, 8) 6-8, 9, 10) 6-10, 11, 12, 13) 5-13, 14, 15, 16, 17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree28grouped = groupOTU(tree28, list(a = c(5, 19), b = c(5, 18), c = c(5, 13), d = c(1, 22), e = c(2, 22), f = c(6, 10), g = c(6, 8), h = c(3, 21), i = c(5, 21)))
strengthMap28 = c( .5, 1, 1, 1, 2, 2, 3, 3, 4, 5)
treeplot28 = ggtree(tree28grouped,
	aes(size=(strengthMap28[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree29 = read.tree(text="(1, (2, (3, 4, ((((5, 6) 5-6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18) 5-18, 19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree29grouped = groupOTU(tree29, list(a = c(5, 19), b = c(5, 18), c = c(5, 6), d = c(1, 22), e = c(2, 22), f = c(3, 21), g = c(5, 21)))
strengthMap29 = c( .5, 1, 1, 1, 2, 2, 4, 5)
treeplot29 = ggtree(tree29grouped,
	aes(size=(strengthMap29[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tree30 = read.tree(text="(1, (2, (3, 4, ((5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, (17, 18, 19) 17-19) 5-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
tree30grouped = groupOTU(tree30, list(a = c(5, 19), b = c(17, 19), c = c(1, 22), d = c(2, 22), e = c(3, 21), f = c(5, 21)))
strengthMap30 = c( .5, 1, 1, 2, 2, 4, 5)
treeplot30 = ggtree(tree30grouped,
	aes(size=(strengthMap30[group])),
	layout='slanted', ladderize = FALSE, alpha=0.033333, color="black") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()


treelayout <- c(
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
area(t = 1, l = 1, b = 5, r = 1),
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
treeplot10+
treeplot11+
treeplot12+
treeplot13+
treeplot14+
treeplot15+
treeplot16+
treeplot17+
treeplot18+
treeplot19+
treeplot20+
treeplot21+
treeplot22+
treeplot23+
treeplot24+
treeplot25+
treeplot26+
treeplot27+
treeplot28+
treeplot29+
treeplot30+
plot_layout(design = treelayout))
