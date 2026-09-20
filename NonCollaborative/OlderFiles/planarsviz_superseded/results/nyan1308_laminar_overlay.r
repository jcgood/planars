library(ape)
library(ggplot2)
library(ggtree)
library(patchwork)

posLabel <- list("1" = "QM", "2" = "PreSbj", "3" = "Sbj", "4" = "PostSbj", "5" = "Neg1", "6" = "SM", "7" = "Neg2", "8" = "TAM", "9" = "OM", "10" = "Root", "11" = "Ext", "12" = "STAT", "13" = "CAUS", "14" = "APPL", "15" = "REC", "16" = "PASS", "17" = "FV", "18" = "2P", "19" = "Enc", "20" = "Obj1", "21" = "Obj2", "22" = "PostObj")

alphaval <- 0.094435

# ── morsyn: 3 families ──
morsyntree1 <- read.tree(text="(1,2,3,4,(((5,6,7,8,(9,((10,11,12,(13,14,15)13-15,16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21,22)1-22;")
morsyntree1grouped <- groupOTU(morsyntree1, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(9, 18), f = c(10, 18), g = c(10, 17), h = c(13, 15)))
morsynsmap1 <- c(0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.4142, 1.0)
morsyntreeplot1 <- ggtree(morsyntree1grouped,
  aes(size=(morsynsmap1[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

morsyntree2 <- read.tree(text="(1,2,3,4,((((5,6,7,8,9,(10,11,12,(13,14,15)13-15,16,17)10-17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
morsyntree2grouped <- groupOTU(morsyntree2, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(10, 17), g = c(13, 15)))
morsynsmap2 <- c(0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.4142, 1.0)
morsyntreeplot2 <- ggtree(morsyntree2grouped,
  aes(size=(morsynsmap2[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

morsyntree3 <- read.tree(text="(1,2,3,4,(((((5,6,7,8,9,10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21,22)1-22;")
morsyntree3grouped <- groupOTU(morsyntree3, list(a = c(1, 22), b = c(5, 21), c = c(5, 19), d = c(5, 18), e = c(5, 17), f = c(5, 13)))
morsynsmap3 <- c(0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
morsyntreeplot3 <- ggtree(morsyntree3grouped,
  aes(size=(morsynsmap3[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#BC3C29") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

# ── tono: 9 families ──
tonotree1 <- read.tree(text="(1,2,3,4,(5,((((6,7,8)6-8,(9,10)9-10)6-10,11,12,13,14,15,16)6-16,17)6-17)5-17,18,19,20,21,22)1-22;")
tonotree1grouped <- groupOTU(tonotree1, list(a = c(1, 22), b = c(5, 17), c = c(6, 17), d = c(6, 16), e = c(6, 10), f = c(6, 8), g = c(9, 10)))
tonosmap1 <- c(0.5, 1.0, 2.6458, 3.4641, 2.6458, 1.0, 1.0, 1.0)
tonotreeplot1 <- ggtree(tonotree1grouped,
  aes(size=(tonosmap1[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

tonotree2 <- read.tree(text="(1,2,3,4,(5,(((6,7,8)6-8,((9,10)9-10,11,12,13,14,15,16)9-16)6-16,17)6-17)5-17,18,19,20,21,22)1-22;")
tonotree2grouped <- groupOTU(tonotree2, list(a = c(1, 22), b = c(5, 17), c = c(6, 17), d = c(6, 16), e = c(6, 8), f = c(9, 16), g = c(9, 10)))
tonosmap2 <- c(0.5, 1.0, 2.6458, 3.4641, 2.6458, 1.0, 1.0, 1.0)
tonotreeplot2 <- ggtree(tonotree2grouped,
  aes(size=(tonosmap2[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

tonotree3 <- read.tree(text="(1,2,3,4,(5,((6,7,8)6-8,(((9,10)9-10,11,12,13,14,15,16)9-16,17)9-17)6-17)5-17,18,19,20,21,22)1-22;")
tonotree3grouped <- groupOTU(tonotree3, list(a = c(1, 22), b = c(5, 17), c = c(6, 17), d = c(6, 8), e = c(9, 17), f = c(9, 16), g = c(9, 10)))
tonosmap3 <- c(0.5, 1.0, 2.6458, 3.4641, 1.0, 1.7321, 1.0, 1.0)
tonotreeplot3 <- ggtree(tonotree3grouped,
  aes(size=(tonosmap3[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

tonotree4 <- read.tree(text="(1,2,3,4,(5,(((6,7,(8,(9,10)9-10)8-10)6-10,11,12,13,14,15,16)6-16,17)6-17)5-17,18,19,20,21,22)1-22;")
tonotree4grouped <- groupOTU(tonotree4, list(a = c(1, 22), b = c(5, 17), c = c(6, 17), d = c(6, 16), e = c(6, 10), f = c(8, 10), g = c(9, 10)))
tonosmap4 <- c(0.5, 1.0, 2.6458, 3.4641, 2.6458, 1.0, 1.0, 1.0)
tonotreeplot4 <- ggtree(tonotree4grouped,
  aes(size=(tonosmap4[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

tonotree5 <- read.tree(text="(1,2,3,4,(5,((6,7,((8,(9,10)9-10)8-10,11,12,13,14,15,16)8-16)6-16,17)6-17)5-17,18,19,20,21,22)1-22;")
tonotree5grouped <- groupOTU(tonotree5, list(a = c(1, 22), b = c(5, 17), c = c(6, 17), d = c(6, 16), e = c(8, 16), f = c(8, 10), g = c(9, 10)))
tonosmap5 <- c(0.5, 1.0, 2.6458, 3.4641, 2.6458, 1.4142, 1.0, 1.0)
tonotreeplot5 <- ggtree(tonotree5grouped,
  aes(size=(tonosmap5[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

tonotree6 <- read.tree(text="(1,2,3,4,(5,((6,7,(8,((9,10)9-10,11,12,13,14,15,16)9-16)8-16)6-16,17)6-17)5-17,18,19,20,21,22)1-22;")
tonotree6grouped <- groupOTU(tonotree6, list(a = c(1, 22), b = c(5, 17), c = c(6, 17), d = c(6, 16), e = c(8, 16), f = c(9, 16), g = c(9, 10)))
tonosmap6 <- c(0.5, 1.0, 2.6458, 3.4641, 2.6458, 1.4142, 1.0, 1.0)
tonotreeplot6 <- ggtree(tonotree6grouped,
  aes(size=(tonosmap6[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

tonotree7 <- read.tree(text="(1,2,3,4,(5,(6,7,(((8,(9,10)9-10)8-10,11,12,13,14,15,16)8-16,17)8-17)6-17)5-17,18,19,20,21,22)1-22;")
tonotree7grouped <- groupOTU(tonotree7, list(a = c(1, 22), b = c(5, 17), c = c(6, 17), d = c(8, 17), e = c(8, 16), f = c(8, 10), g = c(9, 10)))
tonosmap7 <- c(0.5, 1.0, 2.6458, 3.4641, 2.8284, 1.4142, 1.0, 1.0)
tonotreeplot7 <- ggtree(tonotree7grouped,
  aes(size=(tonosmap7[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

tonotree8 <- read.tree(text="(1,2,3,4,(5,(6,7,((8,((9,10)9-10,11,12,13,14,15,16)9-16)8-16,17)8-17)6-17)5-17,18,19,20,21,22)1-22;")
tonotree8grouped <- groupOTU(tonotree8, list(a = c(1, 22), b = c(5, 17), c = c(6, 17), d = c(8, 17), e = c(8, 16), f = c(9, 16), g = c(9, 10)))
tonosmap8 <- c(0.5, 1.0, 2.6458, 3.4641, 2.8284, 1.4142, 1.0, 1.0)
tonotreeplot8 <- ggtree(tonotree8grouped,
  aes(size=(tonosmap8[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

tonotree9 <- read.tree(text="(1,2,3,4,(5,(6,7,(8,(((9,10)9-10,11,12,13,14,15,16)9-16,17)9-17)8-17)6-17)5-17,18,19,20,21,22)1-22;")
tonotree9grouped <- groupOTU(tonotree9, list(a = c(1, 22), b = c(5, 17), c = c(6, 17), d = c(8, 17), e = c(9, 17), f = c(9, 16), g = c(9, 10)))
tonosmap9 <- c(0.5, 1.0, 2.6458, 3.4641, 2.8284, 1.7321, 1.0, 1.0)
tonotreeplot9 <- ggtree(tonotree9grouped,
  aes(size=(tonosmap9[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#0072B5") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

# ── length: 3 families ──
lengthtree1 <- read.tree(text="(1,2,3,4,((5,6,7,8,(9,(10,11,12,13,14,15,16,17)10-17)9-17)5-17,18)5-18,19,20,21,22)1-22;")
lengthtree1grouped <- groupOTU(lengthtree1, list(a = c(1, 22), b = c(5, 18), c = c(5, 17), d = c(9, 17), e = c(10, 17)))
lengthsmap1 <- c(0.5, 1.0, 1.0, 1.4142, 1.0, 1.0)
lengthtreeplot1 <- ggtree(lengthtree1grouped,
  aes(size=(lengthsmap1[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#E18727") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

lengthtree2 <- read.tree(text="(1,2,3,4,(5,6,7,8,((9,(10,11,12,13,14,15,16,17)10-17)9-17,18)9-18)5-18,19,20,21,22)1-22;")
lengthtree2grouped <- groupOTU(lengthtree2, list(a = c(1, 22), b = c(5, 18), c = c(9, 18), d = c(9, 17), e = c(10, 17)))
lengthsmap2 <- c(0.5, 1.0, 1.0, 1.0, 1.0, 1.0)
lengthtreeplot2 <- ggtree(lengthtree2grouped,
  aes(size=(lengthsmap2[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#E18727") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

lengthtree3 <- read.tree(text="(1,2,3,4,(5,6,7,8,(9,((10,11,12,13,14,15,16,17)10-17,18)10-18)9-18)5-18,19,20,21,22)1-22;")
lengthtree3grouped <- groupOTU(lengthtree3, list(a = c(1, 22), b = c(5, 18), c = c(9, 18), d = c(10, 18), e = c(10, 17)))
lengthsmap3 <- c(0.5, 1.0, 1.0, 1.0, 1.0, 1.0)
lengthtreeplot3 <- ggtree(lengthtree3grouped,
  aes(size=(lengthsmap3[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#E18727") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

# ── phon: 6 families ──
phontree1 <- read.tree(text="(1,2,(3,4,(5,((6,7,8)6-8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17)6-17,18,19,20,21)5-21)3-21,22)1-22;")
phontree1grouped <- groupOTU(phontree1, list(a = c(1, 22), b = c(3, 21), c = c(5, 21), d = c(6, 17), e = c(6, 8), f = c(9, 17), g = c(10, 17), h = c(10, 16), i = c(10, 13)))
phonsmap1 <- c(0.5, 1.0, 2.0, 2.0, 1.0, 1.4142, 1.0, 1.7321, 1.0, 1.0)
phontreeplot1 <- ggtree(phontree1grouped,
  aes(size=(phonsmap1[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#20845E") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

phontree2 <- read.tree(text="(1,2,(3,4,((5,6)5-6,7,8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17,18,19,20,21)5-21)3-21,22)1-22;")
phontree2grouped <- groupOTU(phontree2, list(a = c(1, 22), b = c(3, 21), c = c(5, 21), d = c(5, 6), e = c(9, 17), f = c(10, 17), g = c(10, 16), h = c(10, 13)))
phonsmap2 <- c(0.5, 1.0, 2.0, 2.0, 1.0, 1.0, 1.7321, 1.0, 1.0)
phontreeplot2 <- ggtree(phontree2grouped,
  aes(size=(phonsmap2[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#20845E") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

phontree3 <- read.tree(text="(1,2,(3,4,((5,6)5-6,7,8,9,((10,11,12,13)10-13,14,15,16)10-16,(17,18,19)17-19,20,21)5-21)3-21,22)1-22;")
phontree3grouped <- groupOTU(phontree3, list(a = c(1, 22), b = c(3, 21), c = c(5, 21), d = c(5, 6), e = c(10, 16), f = c(10, 13), g = c(17, 19)))
phonsmap3 <- c(0.5, 1.0, 2.0, 2.0, 1.0, 1.0, 1.0, 1.0)
phontreeplot3 <- ggtree(phontree3grouped,
  aes(size=(phonsmap3[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#20845E") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

phontree4 <- read.tree(text="(1,2,(3,4,(5,(6,7,8)6-8,9,((10,11,12,13)10-13,14,15,16)10-16,(17,18,19)17-19,20,21)5-21)3-21,22)1-22;")
phontree4grouped <- groupOTU(phontree4, list(a = c(1, 22), b = c(3, 21), c = c(5, 21), d = c(6, 8), e = c(10, 16), f = c(10, 13), g = c(17, 19)))
phonsmap4 <- c(0.5, 1.0, 2.0, 2.0, 1.4142, 1.0, 1.0, 1.0)
phontreeplot4 <- ggtree(phontree4grouped,
  aes(size=(phonsmap4[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#20845E") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

phontree5 <- read.tree(text="(1,2,(3,4,(5,(((6,7,8)6-8,9,10)6-10,11,12,13,14,15,16,17)6-17,18,19,20,21)5-21)3-21,22)1-22;")
phontree5grouped <- groupOTU(phontree5, list(a = c(1, 22), b = c(3, 21), c = c(5, 21), d = c(6, 17), e = c(6, 10), f = c(6, 8)))
phonsmap5 <- c(0.5, 1.0, 2.0, 2.0, 1.0, 1.4142, 1.4142)
phontreeplot5 <- ggtree(phontree5grouped,
  aes(size=(phonsmap5[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#20845E") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

phontree6 <- read.tree(text="(1,2,(3,4,(5,((6,7,8)6-8,9,10)6-10,11,12,13,14,15,16,(17,18,19)17-19,20,21)5-21)3-21,22)1-22;")
phontree6grouped <- groupOTU(phontree6, list(a = c(1, 22), b = c(3, 21), c = c(5, 21), d = c(6, 10), e = c(6, 8), f = c(17, 19)))
phonsmap6 <- c(0.5, 1.0, 2.0, 2.0, 1.4142, 1.4142, 1.0)
phontreeplot6 <- ggtree(phontree6grouped,
  aes(size=(phonsmap6[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#20845E") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

# ── inton: 1 families ──
intontree1 <- read.tree(text="(1,(2,3,4,5,(6,7,8,9,10,11,12,13,14,15,16,17)6-17,18,19,20,21,22)2-22)1-22;")
intontree1grouped <- groupOTU(intontree1, list(a = c(1, 22), b = c(2, 22), c = c(6, 17)))
intonsmap1 <- c(0.5, 2.0, 1.4142, 2.4495)
intontreeplot1 <- ggtree(intontree1grouped,
  aes(size=(intonsmap1[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#7876B1") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

intontreeplot1 <- intontreeplot1 + geom_tiplab(geom="label", size=6, angle=0,
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
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1))

forest <- (
  morsyntreeplot1 +
  morsyntreeplot2 +
  morsyntreeplot3 +
  tonotreeplot1 +
  tonotreeplot2 +
  tonotreeplot3 +
  tonotreeplot4 +
  tonotreeplot5 +
  tonotreeplot6 +
  tonotreeplot7 +
  tonotreeplot8 +
  tonotreeplot9 +
  lengthtreeplot1 +
  lengthtreeplot2 +
  lengthtreeplot3 +
  phontreeplot1 +
  phontreeplot2 +
  phontreeplot3 +
  phontreeplot4 +
  phontreeplot5 +
  phontreeplot6 +
  intontreeplot1 +
  plot_layout(design=treelayout))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_laminar_overlay.pdf", forest & theme(plot.background=element_rect(fill='white', color=NA)), width=20, height=14)

legend_data <- data.frame(
  Domain_Type = factor(c("morphosyntactic", "tonosegmental", "length", "phonological", "intonational"),
    levels=c("morphosyntactic", "tonosegmental", "length", "phonological", "intonational")),
  x=1, y=1
)
legend_plot <- ggplot(legend_data, aes(x=x, y=y, color=Domain_Type)) +
  geom_point(size=3, alpha=0) +
  scale_color_manual(values=c(morphosyntactic="#BC3C29", tonosegmental="#0072B5", length="#E18727", phonological="#20845E", intonational="#7876B1"),
    name="Domain type") +
  guides(color=guide_legend(override.aes=list(alpha=1))) +
  theme_void() + theme(legend.position="inside", legend.position.inside=c(0.02, 0.98), legend.justification=c("left", "top"), legend.direction="vertical",
    legend.background=element_rect(fill="white", color="black", linewidth=0.5),
    legend.text=element_text(size=26), legend.title=element_text(size=28, face="bold"),
    legend.key.height=unit(2.2, "lines"), legend.key.width=unit(1.2, "lines"),
    legend.spacing.y=unit(0.45, "in"), legend.margin=margin(18, 20, 18, 20),
    plot.margin=margin(8, 8, 8, 8))
legend_version <- forest + inset_element(legend_plot, left=0.002, bottom=0.55, right=0.40, top=0.97, align_to="panel", on_top=TRUE)
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_laminar_overlay_legend.pdf", legend_version, width=20, height=14)
