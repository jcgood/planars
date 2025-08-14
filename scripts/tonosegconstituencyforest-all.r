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

tonosegtree1 = read.tree(text="(1, (2, 3, 4, (5, (6, 7, (((8, (9, 10) 9-10) 8-10, 11, 12, 13, 14, 15, 16, 17) 9-17) 8-17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree1grouped = groupOTU(tonosegtree1, list(a = c(8, 10), b = c(9, 10), c = c(1, 22), d = c(2, 22), e = c(9, 17), f = c(8, 17), g = c(5, 17), h = c(6, 17)))
strengthMap1 = c( .5, 1, 1, 2, 2, 5, 8, 10, 17)
tonosegtreeplot1 = ggtree(tonosegtree1grouped,
	aes(size=(strengthMap1[group])),
	layout='slanted', ladderize = FALSE, alpha=0.125, color="green") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=1,
	aes(label=paste(label, posLabel[label], sep="\n")), lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree2 = read.tree(text="(1, (2, 3, 4, (5, (6, 7, (((8, (9, 10) 9-10) 8-10, 11, 12, 13, 14, 15, 16) 8-16, 17) 8-17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree2grouped = groupOTU(tonosegtree2, list(a = c(8, 10), b = c(9, 10), c = c(1, 22), d = c(2, 22), e = c(8, 16), f = c(8, 17), g = c(5, 17), h = c(6, 17)))
strengthMap2 = c( .5, 1, 1, 2, 2, 2, 8, 10, 17)
tonosegtreeplot2 = ggtree(tonosegtree2grouped,
	aes(size=(strengthMap2[group])),
	layout='slanted', ladderize = FALSE, alpha=0.125, color="green") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree3 = read.tree(text="(1, (2, 3, 4, (5, (((6, 7, (8, (9, 10) 9-10) 8-10) 6-10, 11, 12, 13, 14, 15, 16) 6-16, 17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree3grouped = groupOTU(tonosegtree3, list(a = c(8, 10), b = c(9, 10), c = c(1, 22), d = c(2, 22), e = c(6, 10), f = c(6, 16), g = c(5, 17), h = c(6, 17)))
strengthMap3 = c( .5, 1, 1, 2, 2, 3, 9, 10, 17)
tonosegtreeplot3 = ggtree(tonosegtree3grouped,
	aes(size=(strengthMap3[group])),
	layout='slanted', ladderize = FALSE, alpha=0.125, color="green") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree4 = read.tree(text="(1, (2, 3, 4, (5, ((6, 7, ((8, (9, 10) 9-10) 8-10, 11, 12, 13, 14, 15, 16) 8-16) 6-16, 17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree4grouped = groupOTU(tonosegtree4, list(a = c(8, 10), b = c(9, 10), c = c(1, 22), d = c(2, 22), e = c(8, 16), f = c(6, 16), g = c(5, 17), h = c(6, 17)))
strengthMap4 = c( .5, 1, 1, 2, 2, 2, 9, 10, 17)
tonosegtreeplot4 = ggtree(tonosegtree4grouped,
	aes(size=(strengthMap4[group])),
	layout='slanted', ladderize = FALSE, alpha=0.125, color="green") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree5 = read.tree(text="(1, (2, 3, 4, (5, (6, 7, (8, ((9, 10, 11, 12, 13, 14, 15, 16) 9-16, 17) 9-17) 8-17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree5grouped = groupOTU(tonosegtree5, list(a = c(9, 16), b = c(1, 22), c = c(2, 22), d = c(9, 17), e = c(8, 17), f = c(5, 17), g = c(6, 17)))
strengthMap5 = c( .5, 1, 2, 2, 5, 8, 10, 17)
tonosegtreeplot5 = ggtree(tonosegtree5grouped,
	aes(size=(strengthMap5[group])),
	layout='slanted', ladderize = FALSE, alpha=0.125, color="green") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree6 = read.tree(text="(1, (2, 3, 4, (5, (6, 7, ((8, (9, 10, 11, 12, 13, 14, 15, 16) 9-16) 8-16, 17) 8-17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree6grouped = groupOTU(tonosegtree6, list(a = c(9, 16), b = c(1, 22), c = c(2, 22), d = c(8, 16), e = c(8, 17), f = c(5, 17), g = c(6, 17)))
strengthMap6 = c( .5, 1, 2, 2, 2, 8, 10, 17)
tonosegtreeplot6 = ggtree(tonosegtree6grouped,
	aes(size=(strengthMap6[group])),
	layout='slanted', ladderize = FALSE, alpha=0.125, color="green") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree7 = read.tree(text="(1, (2, 3, 4, (5, ((((6, 7, 8) 6-8, 9, 10) 6-10, 11, 12, 13, 14, 15, 16) 6-16, 17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree7grouped = groupOTU(tonosegtree7, list(a = c(1, 22), b = c(2, 22), c = c(6, 10), d = c(6, 8), e = c(6, 16), f = c(5, 17), g = c(6, 17)))
strengthMap7 = c( .5, 2, 2, 3, 3, 9, 10, 17)
tonosegtreeplot7 = ggtree(tonosegtree7grouped,
	aes(size=(strengthMap7[group])),
	layout='slanted', ladderize = FALSE, alpha=0.125, color="green") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree8 = read.tree(text="(1, (2, 3, 4, (5, ((6, 7, (8, (9, 10, 11, 12, 13, 14, 15, 16) 9-16) 8-16) 6-16, 17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree8grouped = groupOTU(tonosegtree8, list(a = c(9, 16), b = c(1, 22), c = c(2, 22), d = c(8, 16), e = c(6, 16), f = c(5, 17), g = c(6, 17)))
strengthMap8 = c( .5, 1, 2, 2, 2, 9, 10, 17)
tonosegtreeplot8 = ggtree(tonosegtree8grouped,
	aes(size=(strengthMap8[group])),
	layout='slanted', ladderize = FALSE, alpha=0.125, color="green") +
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
area(t = 1, l = 1, b = 5, r = 1))

print(
tonosegtreeplot1+
tonosegtreeplot2+
tonosegtreeplot3+
tonosegtreeplot4+
tonosegtreeplot5+
tonosegtreeplot6+
tonosegtreeplot7+
tonosegtreeplot8+
plot_layout(design = treelayout))
