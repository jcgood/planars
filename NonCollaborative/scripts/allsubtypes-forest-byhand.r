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

morsyntree1 = read.tree(text="(1, 2, 3, 4, (((5, (6, 7, 8, ((9, (10, 11, 12, (13, 14, 15) 13-15, 16, 17) 10-17) 9-17, 18) 9-18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21, 22) 1-22;")
morsyntree1grouped = groupOTU(morsyntree1, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(13, 15), e = c(1, 22), f = c(9, 18), g = c(5, 21), h = c(9, 17), i = c(10, 17)))
strengthMap1 = c( .5, 1, 1, 1, 1, 2, 2, 5, 5, 6)
morsyntreeplot1 = ggtree(morsyntree1grouped,
	aes(size=(strengthMap1[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="red") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

morsyntree2 = read.tree(text="(1, 2, 3, 4, (((5, (6, 7, 8, (9, ((10, 11, 12, (13, 14, 15) 13-15, 16, 17) 10-17, 18) 10-18) 9-18) 6-18) 5-18, 19) 5-19, 20, 21) 5-21, 22) 1-22;")
morsyntree2grouped = groupOTU(morsyntree2, list(a = c(5, 19), b = c(5, 18), c = c(6, 18), d = c(13, 15), e = c(1, 22), f = c(9, 18), g = c(10, 18), h = c(5, 21), i = c(10, 17)))
strengthMap2 = c( .5, 1, 1, 1, 1, 2, 2, 2, 5, 6)
morsyntreeplot2 = ggtree(morsyntree2grouped,
	aes(size=(strengthMap2[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="red") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

morsyntree3 = read.tree(text="(1, 2, 3, 4, ((((5, 6, 7, 8, 9, (10, 11, 12, (13, 14, 15) 13-15, 16, 17) 10-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21, 22) 1-22;")
morsyntree3grouped = groupOTU(morsyntree3, list(a = c(5, 19), b = c(5, 18), c = c(13, 15), d = c(1, 22), e = c(5, 21), f = c(10, 17), g = c(5, 17)))
strengthMap3 = c( .5, 1, 1, 1, 2, 5, 6, 10)
morsyntreeplot3 = ggtree(morsyntree3grouped,
	aes(size=(strengthMap3[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="red") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

morsyntree4 = read.tree(text="(1, 2, 3, 4, ((((5, 6, 7, 8, 9, 10, 11, 12, 13) 5-13, 14, 15, 16, 17, 18) 5-18, 19) 5-19, 20, 21) 5-21, 22) 1-22;")
morsyntree4grouped = groupOTU(morsyntree4, list(a = c(5, 19), b = c(5, 18), c = c(5, 13), d = c(1, 22), e = c(5, 21)))
strengthMap4 = c( .5, 1, 1, 1, 2, 5)
morsyntreeplot4 = ggtree(morsyntree4grouped,
	aes(size=(strengthMap4[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="red") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree1 = read.tree(text="(1, (2, 3, 4, (5, (6, 7, (((8, (9, 10) 9-10) 8-10, 11, 12, 13, 14, 15, 16, 17) 9-17) 8-17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree1grouped = groupOTU(tonosegtree1, list(a = c(8, 10), b = c(9, 10), c = c(1, 22), d = c(2, 22), e = c(9, 17), f = c(8, 17), g = c(5, 17), h = c(6, 17)))
strengthMap1 = c( .5, 1, 1, 2, 2, 5, 8, 10, 17)
tonosegtreeplot1 = ggtree(tonosegtree1grouped,
	aes(size=(strengthMap1[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="green4") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree2 = read.tree(text="(1, (2, 3, 4, (5, (6, 7, (((8, (9, 10) 9-10) 8-10, 11, 12, 13, 14, 15, 16) 8-16, 17) 8-17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree2grouped = groupOTU(tonosegtree2, list(a = c(8, 10), b = c(9, 10), c = c(1, 22), d = c(2, 22), e = c(8, 16), f = c(8, 17), g = c(5, 17), h = c(6, 17)))
strengthMap2 = c( .5, 1, 1, 2, 2, 2, 8, 10, 17)
tonosegtreeplot2 = ggtree(tonosegtree2grouped,
	aes(size=(strengthMap2[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="green4") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree3 = read.tree(text="(1, (2, 3, 4, (5, (((6, 7, (8, (9, 10) 9-10) 8-10) 6-10, 11, 12, 13, 14, 15, 16) 6-16, 17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree3grouped = groupOTU(tonosegtree3, list(a = c(8, 10), b = c(9, 10), c = c(1, 22), d = c(2, 22), e = c(6, 10), f = c(6, 16), g = c(5, 17), h = c(6, 17)))
strengthMap3 = c( .5, 1, 1, 2, 2, 3, 9, 10, 17)
tonosegtreeplot3 = ggtree(tonosegtree3grouped,
	aes(size=(strengthMap3[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="green4") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree4 = read.tree(text="(1, (2, 3, 4, (5, ((6, 7, ((8, (9, 10) 9-10) 8-10, 11, 12, 13, 14, 15, 16) 8-16) 6-16, 17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree4grouped = groupOTU(tonosegtree4, list(a = c(8, 10), b = c(9, 10), c = c(1, 22), d = c(2, 22), e = c(8, 16), f = c(6, 16), g = c(5, 17), h = c(6, 17)))
strengthMap4 = c( .5, 1, 1, 2, 2, 2, 9, 10, 17)
tonosegtreeplot4 = ggtree(tonosegtree4grouped,
	aes(size=(strengthMap4[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="green4") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree5 = read.tree(text="(1, (2, 3, 4, (5, (6, 7, (8, ((9, 10, 11, 12, 13, 14, 15, 16) 9-16, 17) 9-17) 8-17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree5grouped = groupOTU(tonosegtree5, list(a = c(9, 16), b = c(1, 22), c = c(2, 22), d = c(9, 17), e = c(8, 17), f = c(5, 17), g = c(6, 17)))
strengthMap5 = c( .5, 1, 2, 2, 5, 8, 10, 17)
tonosegtreeplot5 = ggtree(tonosegtree5grouped,
	aes(size=(strengthMap5[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="green4") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree6 = read.tree(text="(1, (2, 3, 4, (5, (6, 7, ((8, (9, 10, 11, 12, 13, 14, 15, 16) 9-16) 8-16, 17) 8-17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree6grouped = groupOTU(tonosegtree6, list(a = c(9, 16), b = c(1, 22), c = c(2, 22), d = c(8, 16), e = c(8, 17), f = c(5, 17), g = c(6, 17)))
strengthMap6 = c( .5, 1, 2, 2, 2, 8, 10, 17)
tonosegtreeplot6 = ggtree(tonosegtree6grouped,
	aes(size=(strengthMap6[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="green4") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree7 = read.tree(text="(1, (2, 3, 4, (5, ((((6, 7, 8) 6-8, 9, 10) 6-10, 11, 12, 13, 14, 15, 16) 6-16, 17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree7grouped = groupOTU(tonosegtree7, list(a = c(1, 22), b = c(2, 22), c = c(6, 10), d = c(6, 8), e = c(6, 16), f = c(5, 17), g = c(6, 17)))
strengthMap7 = c( .5, 2, 2, 3, 3, 9, 10, 17)
tonosegtreeplot7 = ggtree(tonosegtree7grouped,
	aes(size=(strengthMap7[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="green4") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

tonosegtree8 = read.tree(text="(1, (2, 3, 4, (5, ((6, 7, (8, (9, 10, 11, 12, 13, 14, 15, 16) 9-16) 8-16) 6-16, 17) 6-17) 5-17, 18, 19, 20, 21, 22) 2-22) 1-22;")
tonosegtree8grouped = groupOTU(tonosegtree8, list(a = c(9, 16), b = c(1, 22), c = c(2, 22), d = c(8, 16), e = c(6, 16), f = c(5, 17), g = c(6, 17)))
strengthMap8 = c( .5, 1, 2, 2, 2, 9, 10, 17)
tonosegtreeplot8 = ggtree(tonosegtree8grouped,
	aes(size=(strengthMap8[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="green4") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree1 = read.tree(text="(1, (2, (3, 4, (5, (6, 7, 8, ((9, ((10, 11, 12, 13, 14, 15, 16) 10-16, 17) 10-17) 9-17, 18) 9-18) 6-18, 19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
phontree1grouped = groupOTU(phontree1, list(a = c(6, 18), b = c(10, 16), c = c(1, 22), d = c(2, 22), e = c(9, 18), f = c(3, 21), g = c(5, 21), h = c(9, 17), i = c(10, 17)))
strengthMap1 = c( .5, 1, 1, 2, 2, 2, 4, 5, 5, 6)
phontreeplot1 = ggtree(phontree1grouped,
	aes(size=(strengthMap1[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="blue") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree2 = read.tree(text="(1, (2, (3, 4, (5, (6, 7, 8, (9, (((10, 11, 12, 13, 14, 15, 16) 10-16, 17) 10-17, 18) 10-18) 9-18) 6-18, 19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
phontree2grouped = groupOTU(phontree2, list(a = c(6, 18), b = c(10, 16), c = c(1, 22), d = c(2, 22), e = c(9, 18), f = c(10, 18), g = c(3, 21), h = c(5, 21), i = c(10, 17)))
strengthMap2 = c( .5, 1, 1, 2, 2, 2, 2, 4, 5, 6)
phontreeplot2 = ggtree(phontree2grouped,
	aes(size=(strengthMap2[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="blue") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree3 = read.tree(text="(1, (2, (3, 4, (5, ((((6, 7, 8) 6-8, 9, 10) 6-10, 11, 12, 13, 14, 15, 16, 17) 6-17, 18) 6-18, 19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
phontree3grouped = groupOTU(phontree3, list(a = c(6, 18), b = c(1, 22), c = c(2, 22), d = c(6, 10), e = c(6, 8), f = c(3, 21), g = c(5, 21), h = c(6, 17)))
strengthMap3 = c( .5, 1, 2, 2, 3, 3, 4, 5, 17)
phontreeplot3 = ggtree(phontree3grouped,
	aes(size=(strengthMap3[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="blue") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree4 = read.tree(text="(1, (2, (3, 4, (5, ((6, 7, 8, 9, ((10, 11, 12, 13, 14, 15, 16) 10-16, 17) 10-17) 6-17, 18) 6-18, 19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
phontree4grouped = groupOTU(phontree4, list(a = c(6, 18), b = c(10, 16), c = c(1, 22), d = c(2, 22), e = c(3, 21), f = c(5, 21), g = c(10, 17), h = c(6, 17)))
strengthMap4 = c( .5, 1, 1, 2, 2, 4, 5, 6, 17)
phontreeplot4 = ggtree(phontree4grouped,
	aes(size=(strengthMap4[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="blue") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree5 = read.tree(text="(1, (2, (3, 4, ((5, (((6, 7, 8) 6-8, 9, 10) 6-10, 11, 12, 13, 14, 15, 16, 17) 6-17) 5-17, 18, 19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
phontree5grouped = groupOTU(phontree5, list(a = c(1, 22), b = c(2, 22), c = c(6, 10), d = c(6, 8), e = c(3, 21), f = c(5, 21), g = c(5, 17), h = c(6, 17)))
strengthMap5 = c( .5, 2, 2, 3, 3, 4, 5, 10, 17)
phontreeplot5 = ggtree(phontree5grouped,
	aes(size=(strengthMap5[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="blue") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree6 = read.tree(text="(1, (2, (3, 4, ((5, (6, 7, 8, 9, ((10, 11, 12, 13, 14, 15, 16) 10-16, 17) 10-17) 6-17) 5-17, 18, 19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
phontree6grouped = groupOTU(phontree6, list(a = c(10, 16), b = c(1, 22), c = c(2, 22), d = c(3, 21), e = c(5, 21), f = c(10, 17), g = c(5, 17), h = c(6, 17)))
strengthMap6 = c( .5, 1, 2, 2, 4, 5, 6, 10, 17)
phontreeplot6 = ggtree(phontree6grouped,
	aes(size=(strengthMap6[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="blue") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree7 = read.tree(text="(1, (2, (3, 4, (5, ((6, 7, 8, 9, (10, 11, 12, 13) 10-13, 14, 15, 16, 17) 6-17, 18) 6-18, 19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
phontree7grouped = groupOTU(phontree7, list(a = c(6, 18), b = c(10, 13), c = c(1, 22), d = c(2, 22), e = c(3, 21), f = c(5, 21), g = c(6, 17)))
strengthMap7 = c( .5, 1, 1, 2, 2, 4, 5, 17)
phontreeplot7 = ggtree(phontree7grouped,
	aes(size=(strengthMap7[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="blue") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree8 = read.tree(text="(1, (2, (3, 4, ((5, (6, 7, 8, 9, (10, 11, 12, 13) 10-13, 14, 15, 16, 17) 6-17) 5-17, 18, 19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
phontree8grouped = groupOTU(phontree8, list(a = c(10, 13), b = c(1, 22), c = c(2, 22), d = c(3, 21), e = c(5, 21), f = c(5, 17), g = c(6, 17)))
strengthMap8 = c( .5, 1, 2, 2, 4, 5, 10, 17)
phontreeplot8 = ggtree(phontree8grouped,
	aes(size=(strengthMap8[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="blue") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree9 = read.tree(text="(1, (2, (3, 4, ((5, 6) 5-6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
phontree9grouped = groupOTU(phontree9, list(a = c(5, 6), b = c(1, 22), c = c(2, 22), d = c(3, 21), e = c(5, 21)))
strengthMap9 = c( .5, 1, 2, 2, 4, 5)
phontreeplot9 = ggtree(phontree9grouped,
	aes(size=(strengthMap9[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="blue") +
	layout_dendrogram() +
		theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree10 = read.tree(text="(1, (2, (3, 4, (5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, (17, 18, 19) 17-19, 20, 21) 5-21) 3-21, 22) 2-22) 1-22;")
phontree10grouped = groupOTU(phontree10, list(a = c(17, 19), b = c(1, 22), c = c(2, 22), d = c(3, 21), e = c(5, 21)))
strengthMap10 = c( .5, 1, 2, 2, 4, 5)
phontreeplot10 = ggtree(phontree10grouped,
	aes(size=(strengthMap10[group])),
	layout='slanted', ladderize = FALSE, alpha=(1/10), color="blue") +
	layout_dendrogram() +
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
area(t = 1, l = 1, b = 5, r = 1)
)

print(
tonosegtreeplot1+
tonosegtreeplot2+
tonosegtreeplot3+
tonosegtreeplot4+
tonosegtreeplot5+
tonosegtreeplot6+
tonosegtreeplot7+
tonosegtreeplot8+
phontreeplot1+
phontreeplot2+
phontreeplot3+
phontreeplot4+
phontreeplot5+
phontreeplot6+
phontreeplot7+
phontreeplot8+
phontreeplot9+
phontreeplot10+
morsyntreeplot1+
morsyntreeplot2+
morsyntreeplot3+
morsyntreeplot4+
plot_layout(design = treelayout)
& theme(plot.background = element_rect(fill = "grey75")))
