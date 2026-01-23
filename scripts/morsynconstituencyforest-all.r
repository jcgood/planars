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

alphaval = 0.5

morsyntree1 = read.tree(text="(1, 2, 3, 4, (((5, 6, 7, 8, (9, ((10, 11, 12, (13, 14, 15) 13-15, 16, 17) 10-17, 18) 10-18) 9-18) 5-18, 19) 5-19, 20, 21) 5-21, 22) 1-22;")
morsyntree1grouped = groupOTU(morsyntree1, list(a = c(5, 19), b = c(5, 18), c = c(13, 15), d = c(9, 18), e = c(10, 18), f = c(1, 22), g = c(5, 21), h = c(10, 17)))
strengthMap1 = c( .5, 1.0, 1.0, 1.0, 1.4142135623730951, 1.4142135623730951, 2.23606797749979, 2.23606797749979, 2.449489742783178)
morsyntreeplot1 = ggtree(morsyntree1grouped,
	aes(size=(strengthMap1[group])),
	layout='slanted', ladderize = FALSE, alpha=alphaval, color="#EE6677") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=1,
	aes(label=paste(label, posLabel[label], sep="\n")), lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

morsyntree2 = read.tree(text="(1, 2, 3, 4, ((((5, 6, 7, 8, 9, (10, 11, 12, (13, 14, 15) 13-15, 16, 17) 10-17) 5-17, 18) 5-18, 19) 5-19, 20, 21) 5-21, 22) 1-22;")
morsyntree2grouped = groupOTU(morsyntree2, list(a = c(5, 19), b = c(5, 18), c = c(13, 15), d = c(1, 22), e = c(5, 21), f = c(10, 17), g = c(5, 17)))
strengthMap2 = c( .5, 1.0, 1.0, 1.0, 2.23606797749979, 2.23606797749979, 2.449489742783178, 3.1622776601683795)
morsyntreeplot2 = ggtree(morsyntree2grouped,
	aes(size=(strengthMap2[group])),
	layout='slanted', ladderize = FALSE, alpha=alphaval, color="#EE6677") +
	layout_dendrogram() +
	geom_tiplab(geom="label", size=5, angle=0, offset=-1, hjust=.5, alpha=0,
	aes(label=paste(label, posLabel[label], sep="\n")), color="transparent", lineheight = 1) +
	theme(panel.background = element_blank(),
	plot.background = element_blank()) +
		theme(legend.position="none") +
		scale_size_identity()

morsyntree3 = read.tree(text="(1, 2, 3, 4, ((((5, 6, 7, 8, 9, 10, 11, 12, 13) 5-13, 14, 15, 16, 17, 18) 5-18, 19) 5-19, 20, 21) 5-21, 22) 1-22;")
morsyntree3grouped = groupOTU(morsyntree3, list(a = c(5, 19), b = c(5, 18), c = c(5, 13), d = c(1, 22), e = c(5, 21)))
strengthMap3 = c( .5, 1.0, 1.0, 1.0, 2.23606797749979, 2.23606797749979)
morsyntreeplot3 = ggtree(morsyntree3grouped,
	aes(size=(strengthMap3[group])),
	layout='slanted', ladderize = FALSE, alpha=alphaval, color="#EE6677") +
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
area(t = 1, l = 1, b = 5, r = 1))

print(
morsyntreeplot1+
morsyntreeplot2+
morsyntreeplot3+
plot_layout(design = treelayout))
