library(ape)
library(ggplot2)
library(ggtree)
library(patchwork)

posLabel <- list("1" = "QM", "2" = "PreSbj", "3" = "Sbj", "4" = "PostSbj", "5" = "Neg1", "6" = "SM", "7" = "Neg2", "8" = "TAM", "9" = "OM", "10" = "Root", "11" = "Ext", "12" = "STAT", "13" = "CAUS", "14" = "APPL", "15" = "REC", "16" = "PASS", "17" = "FV", "18" = "2P", "19" = "Enc", "20" = "Obj1", "21" = "Obj2", "22" = "PostObj")

alphaval <- 0.064563

# ── all: 69 families ──
alltree1 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree1grouped <- groupOTU(alltree1, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
allsmap1 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 4.7568, 1.6818, 1.0, 1.0, 1.0)
alltreeplot1 <- ggtree(alltree1grouped,
  aes(size=(allsmap1[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree2 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,((8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree2grouped <- groupOTU(alltree2, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
allsmap2 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 4.7568, 1.6818, 1.0, 1.0, 1.0)
alltreeplot2 <- ggtree(alltree2grouped,
  aes(size=(allsmap2[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree3 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,((8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree3grouped <- groupOTU(alltree3, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
allsmap3 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 4.7568, 1.6818, 1.0, 1.0, 1.0)
alltreeplot3 <- ggtree(alltree3grouped,
  aes(size=(allsmap3[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree4 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,((8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree4grouped <- groupOTU(alltree4, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
allsmap4 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 4.7568, 1.6818, 1.0, 1.0, 1.0)
alltreeplot4 <- ggtree(alltree4grouped,
  aes(size=(allsmap4[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree5 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,(((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree5grouped <- groupOTU(alltree5, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
allsmap5 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 4.7568, 3.3437, 1.0, 1.0, 1.0)
alltreeplot5 <- ggtree(alltree5grouped,
  aes(size=(allsmap5[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree6 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree6grouped <- groupOTU(alltree6, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
allsmap6 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 4.7568, 3.3437, 1.0, 1.0, 1.0)
alltreeplot6 <- ggtree(alltree6grouped,
  aes(size=(allsmap6[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree7 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree7grouped <- groupOTU(alltree7, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
allsmap7 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 4.7568, 3.3437, 1.0, 1.0, 1.0)
alltreeplot7 <- ggtree(alltree7grouped,
  aes(size=(allsmap7[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree8 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree8grouped <- groupOTU(alltree8, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(10, 13)))
allsmap8 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 4.7568, 3.3437, 3.8337, 1.0, 1.0)
alltreeplot8 <- ggtree(alltree8grouped,
  aes(size=(allsmap8[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree9 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,(9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree9grouped <- groupOTU(alltree9, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(13, 15)))
allsmap9 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 4.7568, 3.3437, 3.8337, 1.0, 1.0)
alltreeplot9 <- ggtree(alltree9grouped,
  aes(size=(allsmap9[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree10 <- read.tree(text="(1,(2,(3,4,((((5,((((6,7,8)6-8,(9,10)9-10)6-10,11,12,(13,14,15)13-15,16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree10grouped <- groupOTU(alltree10, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 10), k = c(6, 8), l = c(9, 10), m = c(13, 15)))
allsmap10 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.3035, 2.2795, 2.2795, 1.0, 1.0)
alltreeplot10 <- ggtree(alltree10grouped,
  aes(size=(allsmap10[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree11 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,8)6-8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree11grouped <- groupOTU(alltree11, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 8), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
allsmap11 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.3035, 2.2795, 1.0, 1.0, 1.0)
alltreeplot11 <- ggtree(alltree11grouped,
  aes(size=(allsmap11[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree12 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,8)6-8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree12grouped <- groupOTU(alltree12, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 8), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
allsmap12 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.3035, 2.2795, 1.0, 1.0, 1.0)
alltreeplot12 <- ggtree(alltree12grouped,
  aes(size=(allsmap12[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree13 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,8)6-8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree13grouped <- groupOTU(alltree13, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 8), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
allsmap13 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.3035, 2.2795, 1.0, 1.0, 1.0)
alltreeplot13 <- ggtree(alltree13grouped,
  aes(size=(allsmap13[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree14 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,(((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree14grouped <- groupOTU(alltree14, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
allsmap14 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 2.2795, 3.3437, 1.0, 1.0, 1.0)
alltreeplot14 <- ggtree(alltree14grouped,
  aes(size=(allsmap14[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree15 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree15grouped <- groupOTU(alltree15, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
allsmap15 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 2.2795, 3.3437, 1.0, 1.0, 1.0)
alltreeplot15 <- ggtree(alltree15grouped,
  aes(size=(allsmap15[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree16 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree16grouped <- groupOTU(alltree16, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
allsmap16 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 2.2795, 3.3437, 1.0, 1.0, 1.0)
alltreeplot16 <- ggtree(alltree16grouped,
  aes(size=(allsmap16[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree17 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree17grouped <- groupOTU(alltree17, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(10, 13)))
allsmap17 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 2.2795, 3.3437, 3.8337, 1.0, 1.0)
alltreeplot17 <- ggtree(alltree17grouped,
  aes(size=(allsmap17[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree18 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,(9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree18grouped <- groupOTU(alltree18, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(13, 15)))
allsmap18 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 2.2795, 3.3437, 3.8337, 1.0, 1.0)
alltreeplot18 <- ggtree(alltree18grouped,
  aes(size=(allsmap18[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree19 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,(8,(9,10)9-10)8-10)6-10,11,12,(13,14,15)13-15,16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree19grouped <- groupOTU(alltree19, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 10), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
allsmap19 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.3035, 2.2795, 1.0, 1.0, 1.0)
alltreeplot19 <- ggtree(alltree19grouped,
  aes(size=(allsmap19[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree20 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree20grouped <- groupOTU(alltree20, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(8, 16), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
allsmap20 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.3035, 1.6818, 1.0, 1.0, 1.0)
alltreeplot20 <- ggtree(alltree20grouped,
  aes(size=(allsmap20[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree21 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,(8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree21grouped <- groupOTU(alltree21, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(8, 16), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
allsmap21 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.3035, 1.6818, 1.0, 1.0, 1.0)
alltreeplot21 <- ggtree(alltree21grouped,
  aes(size=(allsmap21[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree22 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,(8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree22grouped <- groupOTU(alltree22, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
allsmap22 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.3035, 1.6818, 1.0, 1.0, 1.0)
alltreeplot22 <- ggtree(alltree22grouped,
  aes(size=(allsmap22[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree23 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,(8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree23grouped <- groupOTU(alltree23, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
allsmap23 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.3035, 1.6818, 1.0, 1.0, 1.0)
alltreeplot23 <- ggtree(alltree23grouped,
  aes(size=(allsmap23[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree24 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree24grouped <- groupOTU(alltree24, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(8, 16), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
allsmap24 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.7568, 1.6818, 1.0, 1.0, 1.0)
alltreeplot24 <- ggtree(alltree24grouped,
  aes(size=(allsmap24[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree25 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,((8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree25grouped <- groupOTU(alltree25, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
allsmap25 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.7568, 1.6818, 1.0, 1.0, 1.0)
alltreeplot25 <- ggtree(alltree25grouped,
  aes(size=(allsmap25[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree26 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,((8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree26grouped <- groupOTU(alltree26, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
allsmap26 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.7568, 1.6818, 1.0, 1.0, 1.0)
alltreeplot26 <- ggtree(alltree26grouped,
  aes(size=(allsmap26[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree27 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,((8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree27grouped <- groupOTU(alltree27, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
allsmap27 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.7568, 1.6818, 1.0, 1.0, 1.0)
alltreeplot27 <- ggtree(alltree27grouped,
  aes(size=(allsmap27[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree28 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,(((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree28grouped <- groupOTU(alltree28, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
allsmap28 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.7568, 3.3437, 1.0, 1.0, 1.0)
alltreeplot28 <- ggtree(alltree28grouped,
  aes(size=(allsmap28[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree29 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree29grouped <- groupOTU(alltree29, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
allsmap29 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.7568, 3.3437, 1.0, 1.0, 1.0)
alltreeplot29 <- ggtree(alltree29grouped,
  aes(size=(allsmap29[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree30 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree30grouped <- groupOTU(alltree30, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
allsmap30 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.7568, 3.3437, 1.0, 1.0, 1.0)
alltreeplot30 <- ggtree(alltree30grouped,
  aes(size=(allsmap30[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree31 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree31grouped <- groupOTU(alltree31, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(10, 13)))
allsmap31 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.7568, 3.3437, 3.8337, 1.0, 1.0)
alltreeplot31 <- ggtree(alltree31grouped,
  aes(size=(allsmap31[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree32 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,(9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree32grouped <- groupOTU(alltree32, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(13, 15)))
allsmap32 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 9.1005, 4.7568, 3.3437, 3.8337, 1.0, 1.0)
alltreeplot32 <- ggtree(alltree32grouped,
  aes(size=(allsmap32[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree33 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,((((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree33grouped <- groupOTU(alltree33, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(9, 10), l = c(13, 15)))
allsmap33 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 1.0, 1.6818, 3.3437, 1.0, 1.0, 1.0)
alltreeplot33 <- ggtree(alltree33grouped,
  aes(size=(allsmap33[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree34 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree34grouped <- groupOTU(alltree34, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(10, 16), l = c(10, 13)))
allsmap34 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 1.0, 1.6818, 3.3437, 1.0, 1.0, 1.0)
alltreeplot34 <- ggtree(alltree34grouped,
  aes(size=(allsmap34[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree35 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree35grouped <- groupOTU(alltree35, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(10, 16), l = c(13, 15)))
allsmap35 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 1.0, 1.6818, 3.3437, 1.0, 1.0, 1.0)
alltreeplot35 <- ggtree(alltree35grouped,
  aes(size=(allsmap35[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree36 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,((9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree36grouped <- groupOTU(alltree36, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(10, 17), k = c(10, 16), l = c(10, 13)))
allsmap36 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 1.0, 1.6818, 3.3437, 3.8337, 1.0, 1.0)
alltreeplot36 <- ggtree(alltree36grouped,
  aes(size=(allsmap36[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree37 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,((9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree37grouped <- groupOTU(alltree37, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(10, 17), k = c(10, 16), l = c(13, 15)))
allsmap37 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 1.0, 1.6818, 3.3437, 3.8337, 1.0, 1.0)
alltreeplot37 <- ggtree(alltree37grouped,
  aes(size=(allsmap37[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree38 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(9,((((10,11,12,13)10-13,14,15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree38grouped <- groupOTU(alltree38, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(10, 18), j = c(10, 17), k = c(10, 16), l = c(10, 13)))
allsmap38 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 1.0, 1.6818, 1.6818, 3.8337, 1.0, 1.0)
alltreeplot38 <- ggtree(alltree38grouped,
  aes(size=(allsmap38[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree39 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(9,(((10,11,12,(13,14,15)13-15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree39grouped <- groupOTU(alltree39, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(10, 18), j = c(10, 17), k = c(10, 16), l = c(13, 15)))
allsmap39 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 1.0, 1.6818, 1.6818, 3.8337, 1.0, 1.0)
alltreeplot39 <- ggtree(alltree39grouped,
  aes(size=(allsmap39[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree40 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,((((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree40grouped <- groupOTU(alltree40, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(9, 10), l = c(13, 15)))
allsmap40 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 2.2795, 1.6818, 3.3437, 1.0, 1.0, 1.0)
alltreeplot40 <- ggtree(alltree40grouped,
  aes(size=(allsmap40[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree41 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,(((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree41grouped <- groupOTU(alltree41, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(10, 16), l = c(10, 13)))
allsmap41 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 2.2795, 1.6818, 3.3437, 1.0, 1.0, 1.0)
alltreeplot41 <- ggtree(alltree41grouped,
  aes(size=(allsmap41[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree42 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,(((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree42grouped <- groupOTU(alltree42, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(10, 16), l = c(13, 15)))
allsmap42 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 2.2795, 1.6818, 3.3437, 1.0, 1.0, 1.0)
alltreeplot42 <- ggtree(alltree42grouped,
  aes(size=(allsmap42[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree43 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,((9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree43grouped <- groupOTU(alltree43, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(10, 17), k = c(10, 16), l = c(10, 13)))
allsmap43 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 2.2795, 1.6818, 3.3437, 3.8337, 1.0, 1.0)
alltreeplot43 <- ggtree(alltree43grouped,
  aes(size=(allsmap43[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree44 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,((9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree44grouped <- groupOTU(alltree44, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(10, 17), k = c(10, 16), l = c(13, 15)))
allsmap44 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 2.2795, 1.6818, 3.3437, 3.8337, 1.0, 1.0)
alltreeplot44 <- ggtree(alltree44grouped,
  aes(size=(allsmap44[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree45 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,(9,((((10,11,12,13)10-13,14,15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree45grouped <- groupOTU(alltree45, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(10, 18), j = c(10, 17), k = c(10, 16), l = c(10, 13)))
allsmap45 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 2.2795, 1.6818, 1.6818, 3.8337, 1.0, 1.0)
alltreeplot45 <- ggtree(alltree45grouped,
  aes(size=(allsmap45[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree46 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,(9,(((10,11,12,(13,14,15)13-15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree46grouped <- groupOTU(alltree46, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(10, 18), j = c(10, 17), k = c(10, 16), l = c(13, 15)))
allsmap46 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 2.2795, 1.6818, 1.6818, 3.8337, 1.0, 1.0)
alltreeplot46 <- ggtree(alltree46grouped,
  aes(size=(allsmap46[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree47 <- read.tree(text="(1,(2,(3,4,((((((5,6)5-6,7,(8,(9,10)9-10)8-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree47grouped <- groupOTU(alltree47, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(5, 6), j = c(8, 10), k = c(9, 10)))
allsmap47 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 1.0, 1.0, 1.0)
alltreeplot47 <- ggtree(alltree47grouped,
  aes(size=(allsmap47[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree48 <- read.tree(text="(1,(2,(3,4,(((5,6)5-6,7,((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree48grouped <- groupOTU(alltree48, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 6), g = c(8, 16), h = c(8, 10), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
allsmap48 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.0, 1.6818, 1.0, 1.0, 1.0, 1.0)
alltreeplot48 <- ggtree(alltree48grouped,
  aes(size=(allsmap48[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree49 <- read.tree(text="(1,(2,(3,4,(((5,6)5-6,7,(8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree49grouped <- groupOTU(alltree49, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 6), g = c(8, 16), h = c(9, 16), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
allsmap49 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.0, 1.6818, 1.0, 1.0, 1.0, 1.0)
alltreeplot49 <- ggtree(alltree49grouped,
  aes(size=(allsmap49[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree50 <- read.tree(text="(1,(2,(3,4,(((5,6)5-6,7,(8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree50grouped <- groupOTU(alltree50, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 6), g = c(8, 16), h = c(9, 16), i = c(10, 16), j = c(10, 13), k = c(17, 19)))
allsmap50 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.0, 1.6818, 1.0, 1.0, 1.0, 1.0)
alltreeplot50 <- ggtree(alltree50grouped,
  aes(size=(allsmap50[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree51 <- read.tree(text="(1,(2,(3,4,(((5,6)5-6,7,(8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree51grouped <- groupOTU(alltree51, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 6), g = c(8, 16), h = c(9, 16), i = c(10, 16), j = c(13, 15), k = c(17, 19)))
allsmap51 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.0, 1.6818, 1.0, 1.0, 1.0, 1.0)
alltreeplot51 <- ggtree(alltree51grouped,
  aes(size=(allsmap51[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree52 <- read.tree(text="(1,(2,(3,4,(((((5,((6,7,8)6-8,(9,10)9-10)6-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree52grouped <- groupOTU(alltree52, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(6, 10), j = c(6, 8), k = c(9, 10)))
allsmap52 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 2.2795, 2.2795, 1.0)
alltreeplot52 <- ggtree(alltree52grouped,
  aes(size=(allsmap52[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree53 <- read.tree(text="(1,(2,(3,4,(((((5,(6,7,(8,(9,10)9-10)8-10)6-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree53grouped <- groupOTU(alltree53, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(6, 10), j = c(8, 10), k = c(9, 10)))
allsmap53 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 2.2795, 1.0, 1.0)
alltreeplot53 <- ggtree(alltree53grouped,
  aes(size=(allsmap53[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree54 <- read.tree(text="(1,(2,(3,4,((5,(((6,7,8)6-8,(9,10)9-10)6-10,11,12,(13,14,15)13-15,16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree54grouped <- groupOTU(alltree54, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 10), h = c(6, 8), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
allsmap54 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 4.3035, 2.2795, 2.2795, 1.0, 1.0, 1.0)
alltreeplot54 <- ggtree(alltree54grouped,
  aes(size=(allsmap54[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree55 <- read.tree(text="(1,(2,(3,4,((5,((6,7,8)6-8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree55grouped <- groupOTU(alltree55, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 8), h = c(9, 16), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
allsmap55 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 4.3035, 2.2795, 1.0, 1.0, 1.0, 1.0)
alltreeplot55 <- ggtree(alltree55grouped,
  aes(size=(allsmap55[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree56 <- read.tree(text="(1,(2,(3,4,((5,((6,7,8)6-8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree56grouped <- groupOTU(alltree56, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 8), h = c(9, 16), i = c(10, 16), j = c(10, 13), k = c(17, 19)))
allsmap56 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 4.3035, 2.2795, 1.0, 1.0, 1.0, 1.0)
alltreeplot56 <- ggtree(alltree56grouped,
  aes(size=(allsmap56[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree57 <- read.tree(text="(1,(2,(3,4,((5,((6,7,8)6-8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree57grouped <- groupOTU(alltree57, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 8), h = c(9, 16), i = c(10, 16), j = c(13, 15), k = c(17, 19)))
allsmap57 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 4.3035, 2.2795, 1.0, 1.0, 1.0, 1.0)
alltreeplot57 <- ggtree(alltree57grouped,
  aes(size=(allsmap57[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree58 <- read.tree(text="(1,(2,(3,4,((5,((6,7,(8,(9,10)9-10)8-10)6-10,11,12,(13,14,15)13-15,16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree58grouped <- groupOTU(alltree58, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 10), h = c(8, 10), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
allsmap58 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 4.3035, 2.2795, 1.0, 1.0, 1.0, 1.0)
alltreeplot58 <- ggtree(alltree58grouped,
  aes(size=(allsmap58[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree59 <- read.tree(text="(1,(2,(3,4,((5,(6,7,((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree59grouped <- groupOTU(alltree59, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(8, 16), h = c(8, 10), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
allsmap59 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 4.3035, 1.6818, 1.0, 1.0, 1.0, 1.0)
alltreeplot59 <- ggtree(alltree59grouped,
  aes(size=(allsmap59[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree60 <- read.tree(text="(1,(2,(3,4,((5,(6,7,(8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree60grouped <- groupOTU(alltree60, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(8, 16), h = c(9, 16), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
allsmap60 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 4.3035, 1.6818, 1.0, 1.0, 1.0, 1.0)
alltreeplot60 <- ggtree(alltree60grouped,
  aes(size=(allsmap60[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree61 <- read.tree(text="(1,(2,(3,4,((5,(6,7,(8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree61grouped <- groupOTU(alltree61, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(8, 16), h = c(9, 16), i = c(10, 16), j = c(10, 13), k = c(17, 19)))
allsmap61 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 4.3035, 1.6818, 1.0, 1.0, 1.0, 1.0)
alltreeplot61 <- ggtree(alltree61grouped,
  aes(size=(allsmap61[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree62 <- read.tree(text="(1,(2,(3,4,((5,(6,7,(8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree62grouped <- groupOTU(alltree62, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(8, 16), h = c(9, 16), i = c(10, 16), j = c(13, 15), k = c(17, 19)))
allsmap62 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 4.3035, 1.6818, 1.0, 1.0, 1.0, 1.0)
alltreeplot62 <- ggtree(alltree62grouped,
  aes(size=(allsmap62[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree63 <- read.tree(text="(1,(2,(3,4,((((((5,6)5-6,7,8,9,(10,11,12,13)10-13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree63grouped <- groupOTU(alltree63, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(5, 6), j = c(10, 13)))
allsmap63 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 1.0, 1.0)
alltreeplot63 <- ggtree(alltree63grouped,
  aes(size=(allsmap63[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree64 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,(8,(9,10)9-10)8-10,11,12,13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree64grouped <- groupOTU(alltree64, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(5, 6), h = c(8, 10), i = c(9, 10), j = c(17, 19)))
allsmap64 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
alltreeplot64 <- ggtree(alltree64grouped,
  aes(size=(allsmap64[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree65 <- read.tree(text="(1,(2,(3,4,(((((5,(6,7,8)6-8,9,(10,11,12,13)10-13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree65grouped <- groupOTU(alltree65, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(6, 8), j = c(10, 13)))
allsmap65 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.6818, 5.6234, 1.0, 2.2795, 1.0)
alltreeplot65 <- ggtree(alltree65grouped,
  aes(size=(allsmap65[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree66 <- read.tree(text="(1,(2,(3,4,(((5,((6,7,8)6-8,(9,10)9-10)6-10,11,12,13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree66grouped <- groupOTU(alltree66, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(6, 10), h = c(6, 8), i = c(9, 10), j = c(17, 19)))
allsmap66 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.0, 2.2795, 2.2795, 1.0, 1.0)
alltreeplot66 <- ggtree(alltree66grouped,
  aes(size=(allsmap66[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree67 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,(8,(9,10)9-10)8-10)6-10,11,12,13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree67grouped <- groupOTU(alltree67, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(6, 10), h = c(8, 10), i = c(9, 10), j = c(17, 19)))
allsmap67 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.0, 2.2795, 1.0, 1.0, 1.0)
alltreeplot67 <- ggtree(alltree67grouped,
  aes(size=(allsmap67[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree68 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,9,(10,11,12,13)10-13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree68grouped <- groupOTU(alltree68, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(5, 6), h = c(10, 13), i = c(17, 19)))
allsmap68 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.0, 1.0, 1.0, 1.0)
alltreeplot68 <- ggtree(alltree68grouped,
  aes(size=(allsmap68[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltree69 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,9,(10,11,12,13)10-13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
alltree69grouped <- groupOTU(alltree69, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(6, 8), h = c(10, 13), i = c(17, 19)))
allsmap69 <- c(0.5, 3.3437, 1.6818, 2.8284, 3.3437, 1.0, 1.0, 2.2795, 1.0, 1.0)
alltreeplot69 <- ggtree(alltree69grouped,
  aes(size=(allsmap69[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="black") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

alltreeplot69 <- alltreeplot69 + geom_tiplab(geom="label", size=6, angle=0,
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
  alltreeplot1 +
  alltreeplot2 +
  alltreeplot3 +
  alltreeplot4 +
  alltreeplot5 +
  alltreeplot6 +
  alltreeplot7 +
  alltreeplot8 +
  alltreeplot9 +
  alltreeplot10 +
  alltreeplot11 +
  alltreeplot12 +
  alltreeplot13 +
  alltreeplot14 +
  alltreeplot15 +
  alltreeplot16 +
  alltreeplot17 +
  alltreeplot18 +
  alltreeplot19 +
  alltreeplot20 +
  alltreeplot21 +
  alltreeplot22 +
  alltreeplot23 +
  alltreeplot24 +
  alltreeplot25 +
  alltreeplot26 +
  alltreeplot27 +
  alltreeplot28 +
  alltreeplot29 +
  alltreeplot30 +
  alltreeplot31 +
  alltreeplot32 +
  alltreeplot33 +
  alltreeplot34 +
  alltreeplot35 +
  alltreeplot36 +
  alltreeplot37 +
  alltreeplot38 +
  alltreeplot39 +
  alltreeplot40 +
  alltreeplot41 +
  alltreeplot42 +
  alltreeplot43 +
  alltreeplot44 +
  alltreeplot45 +
  alltreeplot46 +
  alltreeplot47 +
  alltreeplot48 +
  alltreeplot49 +
  alltreeplot50 +
  alltreeplot51 +
  alltreeplot52 +
  alltreeplot53 +
  alltreeplot54 +
  alltreeplot55 +
  alltreeplot56 +
  alltreeplot57 +
  alltreeplot58 +
  alltreeplot59 +
  alltreeplot60 +
  alltreeplot61 +
  alltreeplot62 +
  alltreeplot63 +
  alltreeplot64 +
  alltreeplot65 +
  alltreeplot66 +
  alltreeplot67 +
  alltreeplot68 +
  alltreeplot69 +
  plot_layout(design=treelayout))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_all_families_labeled.pdf", forest & theme(plot.background=element_rect(fill='white', color=NA)), width=20, height=14)

legend_header_data <- data.frame(
  y = c(7, 3.65),
  label = c("Darkness: Trees sharing span",
    "Thickness: Tests supporting span")
)
legend_swatch_data <- data.frame(
  y = c(6.0, 5.15, 2.65, 1.8),
  alpha_val = c(0.99, 0.4, 1, 1),
  lw = c(3, 3, 4.3589, 1.0),
  label = c("More", "Fewer", "More", "Fewer")
)
legend_plot <- ggplot() +
  geom_text(data=legend_header_data, aes(x=0, y=y, label=label),
    hjust=0, size=7) +
  geom_segment(data=legend_swatch_data,
    aes(x=0, xend=0.9, y=y, yend=y, alpha=alpha_val, linewidth=lw),
    color="black", lineend="round") +
  geom_text(data=legend_swatch_data, aes(x=1.05, y=y, label=label),
    hjust=0, size=5.8) +
  scale_alpha_identity() + scale_linewidth_identity() +
  xlim(0, 4.9) + ylim(1.3, 7.5) +
  theme_void() +
  theme(plot.background=element_rect(fill="white", color="black", linewidth=1.2),
    plot.margin=margin(6, 8, 6, 6))
legend_version <- (forest & theme(plot.background=element_rect(fill='white', color=NA))) + inset_element(legend_plot,
  left=0.01, bottom=0.67, right=0.27, top=0.97,
  align_to="panel", on_top=TRUE)
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_all_families_labeled_legend.pdf", legend_version, width=20, height=14)
