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

alphaval = 0.601893

phontree1 = read.tree(text="(1, 2, (3, 4, (5, (((6, 7, 8) 6-8, 9, 10) 6-10, 11, 12, 13, 14, 15, 16, 17) 6-17, 18, 19, 20, 21) 5-21) 3-21, 22) 1-22;")
phontree1grouped = groupOTU(phontree1, list(a = c(6, 10), b = c(6, 8), c = c(3, 21), d = c(5, 21), e = c(1, 22), f = c(6, 17)))
strengthMap1 = c( .5, 1.732051, 1.732051, 2.0, 2.236068, 2.44949, 4.795832)
phontreeplot1 = ggtree(phontree1grouped,
	aes(size=(strengthMap1[group])),
	layout='slanted', ladderize = FALSE, alpha=alphaval, color="#4477AA") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=1,
	aes(label=paste(label, posLabel[label], sep="\n")), lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree2 = read.tree(text="(1, 2, (3, 4, (5, (6, 7, 8, 9, ((10, 11, 12, 13, 14, 15, 16) 10-16, 17) 10-17) 6-17, 18, 19, 20, 21) 5-21) 3-21, 22) 1-22;")
phontree2grouped = groupOTU(phontree2, list(a = c(10, 16), b = c(3, 21), c = c(5, 21), d = c(1, 22), e = c(10, 17), f = c(6, 17)))
strengthMap2 = c( .5, 1.0, 2.0, 2.236068, 2.44949, 2.44949, 4.795832)
phontreeplot2 = ggtree(phontree2grouped,
	aes(size=(strengthMap2[group])),
	layout='slanted', ladderize = FALSE, alpha=alphaval, color="#4477AA") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree3 = read.tree(text="(1, 2, (3, 4, (5, (6, 7, 8, 9, (10, 11, 12, 13) 10-13, 14, 15, 16, 17) 6-17, 18, 19, 20, 21) 5-21) 3-21, 22) 1-22;")
phontree3grouped = groupOTU(phontree3, list(a = c(10, 13), b = c(3, 21), c = c(5, 21), d = c(1, 22), e = c(6, 17)))
strengthMap3 = c( .5, 1.0, 2.0, 2.236068, 2.44949, 4.795832)
phontreeplot3 = ggtree(phontree3grouped,
	aes(size=(strengthMap3[group])),
	layout='slanted', ladderize = FALSE, alpha=alphaval, color="#4477AA") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree4 = read.tree(text="(1, 2, (3, 4, ((5, 6) 5-6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21) 5-21) 3-21, 22) 1-22;")
phontree4grouped = groupOTU(phontree4, list(a = c(5, 6), b = c(3, 21), c = c(5, 21), d = c(1, 22)))
strengthMap4 = c( .5, 1.0, 2.0, 2.236068, 2.44949)
phontreeplot4 = ggtree(phontree4grouped,
	aes(size=(strengthMap4[group])),
	layout='slanted', ladderize = FALSE, alpha=alphaval, color="#4477AA") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

phontree5 = read.tree(text="(1, 2, (3, 4, (5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, (17, 18, 19) 17-19, 20, 21) 5-21) 3-21, 22) 1-22;")
phontree5grouped = groupOTU(phontree5, list(a = c(17, 19), b = c(3, 21), c = c(5, 21), d = c(1, 22)))
strengthMap5 = c( .5, 1.0, 2.0, 2.236068, 2.44949)
phontreeplot5 = ggtree(phontree5grouped,
	aes(size=(strengthMap5[group])),
	layout='slanted', ladderize = FALSE, alpha=alphaval, color="#4477AA") +
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
area(t = 1, l = 1, b = 5, r = 1))

print(
phontreeplot1+
phontreeplot2+
phontreeplot3+
phontreeplot4+
phontreeplot5+
plot_layout(design = treelayout))
