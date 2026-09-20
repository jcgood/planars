library(ape)
library(ggplot2)
library(ggtree)
library(patchwork)



# ── Panel ALL: 69 families ──
all_tree1 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree1_g <- groupOTU(all_tree1, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
all_sm1 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 4.4721, 3.3166, 5.1962, 6.3246)
all_tp1 <- ggtree(all_tree1_g,
  aes(size=(all_sm1[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp1$layers[[1]]$aes_params$alpha <- 0.064563
all_tp1$layers[[1]]$aes_params$colour <- 'black'

all_tree2 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,((8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree2_g <- groupOTU(all_tree2, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
all_sm2 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 4.4721, 6.0, 5.1962, 6.3246)
all_tp2 <- ggtree(all_tree2_g,
  aes(size=(all_sm2[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp2$layers[[1]]$aes_params$alpha <- 0.064563
all_tp2$layers[[1]]$aes_params$colour <- 'black'

all_tree3 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,((8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree3_g <- groupOTU(all_tree3, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
all_sm3 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 4.4721, 6.0, 6.1644, 4.7958)
all_tp3 <- ggtree(all_tree3_g,
  aes(size=(all_sm3[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp3$layers[[1]]$aes_params$alpha <- 0.064563
all_tp3$layers[[1]]$aes_params$colour <- 'black'

all_tree4 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,((8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree4_g <- groupOTU(all_tree4, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
all_sm4 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 4.4721, 6.0, 6.1644, 6.3246)
all_tp4 <- ggtree(all_tree4_g,
  aes(size=(all_sm4[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp4$layers[[1]]$aes_params$alpha <- 0.064563
all_tp4$layers[[1]]$aes_params$colour <- 'black'

all_tree5 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,(((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree5_g <- groupOTU(all_tree5, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
all_sm5 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 6.0, 5.1962, 6.3246)
all_tp5 <- ggtree(all_tree5_g,
  aes(size=(all_sm5[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp5$layers[[1]]$aes_params$alpha <- 0.064563
all_tp5$layers[[1]]$aes_params$colour <- 'black'

all_tree6 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree6_g <- groupOTU(all_tree6, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
all_sm6 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 6.0, 6.1644, 4.7958)
all_tp6 <- ggtree(all_tree6_g,
  aes(size=(all_sm6[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp6$layers[[1]]$aes_params$alpha <- 0.064563
all_tp6$layers[[1]]$aes_params$colour <- 'black'

all_tree7 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree7_g <- groupOTU(all_tree7, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
all_sm7 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 6.0, 6.1644, 6.3246)
all_tp7 <- ggtree(all_tree7_g,
  aes(size=(all_sm7[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp7$layers[[1]]$aes_params$alpha <- 0.064563
all_tp7$layers[[1]]$aes_params$colour <- 'black'

all_tree8 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree8_g <- groupOTU(all_tree8, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(10, 13)))
all_sm8 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 3.7417, 6.1644, 4.7958)
all_tp8 <- ggtree(all_tree8_g,
  aes(size=(all_sm8[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp8$layers[[1]]$aes_params$alpha <- 0.064563
all_tp8$layers[[1]]$aes_params$colour <- 'black'

all_tree9 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,(9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree9_g <- groupOTU(all_tree9, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(13, 15)))
all_sm9 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 3.7417, 6.1644, 6.3246)
all_tp9 <- ggtree(all_tree9_g,
  aes(size=(all_sm9[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp9$layers[[1]]$aes_params$alpha <- 0.064563
all_tp9$layers[[1]]$aes_params$colour <- 'black'

all_tree10 <- read.tree(text="(1,(2,(3,4,((((5,((((6,7,8)6-8,(9,10)9-10)6-10,11,12,(13,14,15)13-15,16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree10_g <- groupOTU(all_tree10, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 10), k = c(6, 8), l = c(9, 10), m = c(13, 15)))
all_sm10 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 2.8284, 4.899, 5.1962, 6.3246)
all_tp10 <- ggtree(all_tree10_g,
  aes(size=(all_sm10[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp10$layers[[1]]$aes_params$alpha <- 0.064563
all_tp10$layers[[1]]$aes_params$colour <- 'black'

all_tree11 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,8)6-8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree11_g <- groupOTU(all_tree11, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 8), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
all_sm11 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.899, 6.0, 5.1962, 6.3246)
all_tp11 <- ggtree(all_tree11_g,
  aes(size=(all_sm11[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp11$layers[[1]]$aes_params$alpha <- 0.064563
all_tp11$layers[[1]]$aes_params$colour <- 'black'

all_tree12 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,8)6-8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree12_g <- groupOTU(all_tree12, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 8), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
all_sm12 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.899, 6.0, 6.1644, 4.7958)
all_tp12 <- ggtree(all_tree12_g,
  aes(size=(all_sm12[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp12$layers[[1]]$aes_params$alpha <- 0.064563
all_tp12$layers[[1]]$aes_params$colour <- 'black'

all_tree13 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,8)6-8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree13_g <- groupOTU(all_tree13, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 8), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
all_sm13 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.899, 6.0, 6.1644, 6.3246)
all_tp13 <- ggtree(all_tree13_g,
  aes(size=(all_sm13[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp13$layers[[1]]$aes_params$alpha <- 0.064563
all_tp13$layers[[1]]$aes_params$colour <- 'black'

all_tree14 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,(((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree14_g <- groupOTU(all_tree14, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
all_sm14 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 6.0, 5.1962, 6.3246)
all_tp14 <- ggtree(all_tree14_g,
  aes(size=(all_sm14[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp14$layers[[1]]$aes_params$alpha <- 0.064563
all_tp14$layers[[1]]$aes_params$colour <- 'black'

all_tree15 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree15_g <- groupOTU(all_tree15, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
all_sm15 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 6.0, 6.1644, 4.7958)
all_tp15 <- ggtree(all_tree15_g,
  aes(size=(all_sm15[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp15$layers[[1]]$aes_params$alpha <- 0.064563
all_tp15$layers[[1]]$aes_params$colour <- 'black'

all_tree16 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree16_g <- groupOTU(all_tree16, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
all_sm16 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 6.0, 6.1644, 6.3246)
all_tp16 <- ggtree(all_tree16_g,
  aes(size=(all_sm16[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp16$layers[[1]]$aes_params$alpha <- 0.064563
all_tp16$layers[[1]]$aes_params$colour <- 'black'

all_tree17 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree17_g <- groupOTU(all_tree17, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(10, 13)))
all_sm17 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 3.7417, 6.1644, 4.7958)
all_tp17 <- ggtree(all_tree17_g,
  aes(size=(all_sm17[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp17$layers[[1]]$aes_params$alpha <- 0.064563
all_tp17$layers[[1]]$aes_params$colour <- 'black'

all_tree18 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,(9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree18_g <- groupOTU(all_tree18, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(13, 15)))
all_sm18 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 3.7417, 6.1644, 6.3246)
all_tp18 <- ggtree(all_tree18_g,
  aes(size=(all_sm18[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp18$layers[[1]]$aes_params$alpha <- 0.064563
all_tp18$layers[[1]]$aes_params$colour <- 'black'

all_tree19 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,(8,(9,10)9-10)8-10)6-10,11,12,(13,14,15)13-15,16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree19_g <- groupOTU(all_tree19, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 10), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
all_sm19 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 2.8284, 3.3166, 5.1962, 6.3246)
all_tp19 <- ggtree(all_tree19_g,
  aes(size=(all_sm19[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp19$layers[[1]]$aes_params$alpha <- 0.064563
all_tp19$layers[[1]]$aes_params$colour <- 'black'

all_tree20 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree20_g <- groupOTU(all_tree20, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(8, 16), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
all_sm20 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 3.3166, 5.1962, 6.3246)
all_tp20 <- ggtree(all_tree20_g,
  aes(size=(all_sm20[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp20$layers[[1]]$aes_params$alpha <- 0.064563
all_tp20$layers[[1]]$aes_params$colour <- 'black'

all_tree21 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,(8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree21_g <- groupOTU(all_tree21, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(8, 16), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
all_sm21 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 6.0, 5.1962, 6.3246)
all_tp21 <- ggtree(all_tree21_g,
  aes(size=(all_sm21[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp21$layers[[1]]$aes_params$alpha <- 0.064563
all_tp21$layers[[1]]$aes_params$colour <- 'black'

all_tree22 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,(8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree22_g <- groupOTU(all_tree22, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
all_sm22 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 6.0, 6.1644, 4.7958)
all_tp22 <- ggtree(all_tree22_g,
  aes(size=(all_sm22[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp22$layers[[1]]$aes_params$alpha <- 0.064563
all_tp22$layers[[1]]$aes_params$colour <- 'black'

all_tree23 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,(8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree23_g <- groupOTU(all_tree23, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
all_sm23 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 6.0, 6.1644, 6.3246)
all_tp23 <- ggtree(all_tree23_g,
  aes(size=(all_sm23[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp23$layers[[1]]$aes_params$alpha <- 0.064563
all_tp23$layers[[1]]$aes_params$colour <- 'black'

all_tree24 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree24_g <- groupOTU(all_tree24, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(8, 16), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
all_sm24 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 3.3166, 5.1962, 6.3246)
all_tp24 <- ggtree(all_tree24_g,
  aes(size=(all_sm24[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp24$layers[[1]]$aes_params$alpha <- 0.064563
all_tp24$layers[[1]]$aes_params$colour <- 'black'

all_tree25 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,((8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree25_g <- groupOTU(all_tree25, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
all_sm25 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 6.0, 5.1962, 6.3246)
all_tp25 <- ggtree(all_tree25_g,
  aes(size=(all_sm25[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp25$layers[[1]]$aes_params$alpha <- 0.064563
all_tp25$layers[[1]]$aes_params$colour <- 'black'

all_tree26 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,((8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree26_g <- groupOTU(all_tree26, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
all_sm26 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 6.0, 6.1644, 4.7958)
all_tp26 <- ggtree(all_tree26_g,
  aes(size=(all_sm26[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp26$layers[[1]]$aes_params$alpha <- 0.064563
all_tp26$layers[[1]]$aes_params$colour <- 'black'

all_tree27 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,((8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree27_g <- groupOTU(all_tree27, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
all_sm27 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 6.0, 6.1644, 6.3246)
all_tp27 <- ggtree(all_tree27_g,
  aes(size=(all_sm27[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp27$layers[[1]]$aes_params$alpha <- 0.064563
all_tp27$layers[[1]]$aes_params$colour <- 'black'

all_tree28 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,(((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree28_g <- groupOTU(all_tree28, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
all_sm28 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 5.0, 6.0, 5.1962, 6.3246)
all_tp28 <- ggtree(all_tree28_g,
  aes(size=(all_sm28[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp28$layers[[1]]$aes_params$alpha <- 0.064563
all_tp28$layers[[1]]$aes_params$colour <- 'black'

all_tree29 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree29_g <- groupOTU(all_tree29, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
all_sm29 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 5.0, 6.0, 6.1644, 4.7958)
all_tp29 <- ggtree(all_tree29_g,
  aes(size=(all_sm29[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp29$layers[[1]]$aes_params$alpha <- 0.064563
all_tp29$layers[[1]]$aes_params$colour <- 'black'

all_tree30 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree30_g <- groupOTU(all_tree30, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
all_sm30 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 5.0, 6.0, 6.1644, 6.3246)
all_tp30 <- ggtree(all_tree30_g,
  aes(size=(all_sm30[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp30$layers[[1]]$aes_params$alpha <- 0.064563
all_tp30$layers[[1]]$aes_params$colour <- 'black'

all_tree31 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree31_g <- groupOTU(all_tree31, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(10, 13)))
all_sm31 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 5.0, 3.7417, 6.1644, 4.7958)
all_tp31 <- ggtree(all_tree31_g,
  aes(size=(all_sm31[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp31$layers[[1]]$aes_params$alpha <- 0.064563
all_tp31$layers[[1]]$aes_params$colour <- 'black'

all_tree32 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,(8,(9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree32_g <- groupOTU(all_tree32, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(13, 15)))
all_sm32 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 5.0, 3.7417, 6.1644, 6.3246)
all_tp32 <- ggtree(all_tree32_g,
  aes(size=(all_sm32[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp32$layers[[1]]$aes_params$alpha <- 0.064563
all_tp32$layers[[1]]$aes_params$colour <- 'black'

all_tree33 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,((((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree33_g <- groupOTU(all_tree33, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(9, 10), l = c(13, 15)))
all_sm33 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 6.0, 5.1962, 6.3246)
all_tp33 <- ggtree(all_tree33_g,
  aes(size=(all_sm33[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp33$layers[[1]]$aes_params$alpha <- 0.064563
all_tp33$layers[[1]]$aes_params$colour <- 'black'

all_tree34 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree34_g <- groupOTU(all_tree34, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(10, 16), l = c(10, 13)))
all_sm34 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 6.0, 6.1644, 4.7958)
all_tp34 <- ggtree(all_tree34_g,
  aes(size=(all_sm34[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp34$layers[[1]]$aes_params$alpha <- 0.064563
all_tp34$layers[[1]]$aes_params$colour <- 'black'

all_tree35 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree35_g <- groupOTU(all_tree35, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(10, 16), l = c(13, 15)))
all_sm35 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 6.0, 6.1644, 6.3246)
all_tp35 <- ggtree(all_tree35_g,
  aes(size=(all_sm35[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp35$layers[[1]]$aes_params$alpha <- 0.064563
all_tp35$layers[[1]]$aes_params$colour <- 'black'

all_tree36 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,((9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree36_g <- groupOTU(all_tree36, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(10, 17), k = c(10, 16), l = c(10, 13)))
all_sm36 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 3.7417, 6.1644, 4.7958)
all_tp36 <- ggtree(all_tree36_g,
  aes(size=(all_sm36[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp36$layers[[1]]$aes_params$alpha <- 0.064563
all_tp36$layers[[1]]$aes_params$colour <- 'black'

all_tree37 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,((9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree37_g <- groupOTU(all_tree37, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(9, 17), j = c(10, 17), k = c(10, 16), l = c(13, 15)))
all_sm37 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 3.7417, 6.1644, 6.3246)
all_tp37 <- ggtree(all_tree37_g,
  aes(size=(all_sm37[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp37$layers[[1]]$aes_params$alpha <- 0.064563
all_tp37$layers[[1]]$aes_params$colour <- 'black'

all_tree38 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(9,((((10,11,12,13)10-13,14,15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree38_g <- groupOTU(all_tree38, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(10, 18), j = c(10, 17), k = c(10, 16), l = c(10, 13)))
all_sm38 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 2.0, 3.7417, 6.1644, 4.7958)
all_tp38 <- ggtree(all_tree38_g,
  aes(size=(all_sm38[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp38$layers[[1]]$aes_params$alpha <- 0.064563
all_tp38$layers[[1]]$aes_params$colour <- 'black'

all_tree39 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(9,(((10,11,12,(13,14,15)13-15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree39_g <- groupOTU(all_tree39, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(10, 18), j = c(10, 17), k = c(10, 16), l = c(13, 15)))
all_sm39 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 2.0, 3.7417, 6.1644, 6.3246)
all_tp39 <- ggtree(all_tree39_g,
  aes(size=(all_sm39[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp39$layers[[1]]$aes_params$alpha <- 0.064563
all_tp39$layers[[1]]$aes_params$colour <- 'black'

all_tree40 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,((((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree40_g <- groupOTU(all_tree40, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(9, 10), l = c(13, 15)))
all_sm40 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 6.0, 5.1962, 6.3246)
all_tp40 <- ggtree(all_tree40_g,
  aes(size=(all_sm40[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp40$layers[[1]]$aes_params$alpha <- 0.064563
all_tp40$layers[[1]]$aes_params$colour <- 'black'

all_tree41 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,(((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree41_g <- groupOTU(all_tree41, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(10, 16), l = c(10, 13)))
all_sm41 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 6.0, 6.1644, 4.7958)
all_tp41 <- ggtree(all_tree41_g,
  aes(size=(all_sm41[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp41$layers[[1]]$aes_params$alpha <- 0.064563
all_tp41$layers[[1]]$aes_params$colour <- 'black'

all_tree42 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,(((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree42_g <- groupOTU(all_tree42, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(10, 16), l = c(13, 15)))
all_sm42 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 6.0, 6.1644, 6.3246)
all_tp42 <- ggtree(all_tree42_g,
  aes(size=(all_sm42[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp42$layers[[1]]$aes_params$alpha <- 0.064563
all_tp42$layers[[1]]$aes_params$colour <- 'black'

all_tree43 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,((9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree43_g <- groupOTU(all_tree43, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(10, 17), k = c(10, 16), l = c(10, 13)))
all_sm43 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 3.7417, 6.1644, 4.7958)
all_tp43 <- ggtree(all_tree43_g,
  aes(size=(all_sm43[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp43$layers[[1]]$aes_params$alpha <- 0.064563
all_tp43$layers[[1]]$aes_params$colour <- 'black'

all_tree44 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,((9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree44_g <- groupOTU(all_tree44, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(10, 17), k = c(10, 16), l = c(13, 15)))
all_sm44 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 3.7417, 6.1644, 6.3246)
all_tp44 <- ggtree(all_tree44_g,
  aes(size=(all_sm44[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp44$layers[[1]]$aes_params$alpha <- 0.064563
all_tp44$layers[[1]]$aes_params$colour <- 'black'

all_tree45 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,(9,((((10,11,12,13)10-13,14,15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree45_g <- groupOTU(all_tree45, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(10, 18), j = c(10, 17), k = c(10, 16), l = c(10, 13)))
all_sm45 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 2.0, 3.7417, 6.1644, 4.7958)
all_tp45 <- ggtree(all_tree45_g,
  aes(size=(all_sm45[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp45$layers[[1]]$aes_params$alpha <- 0.064563
all_tp45$layers[[1]]$aes_params$colour <- 'black'

all_tree46 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,(9,(((10,11,12,(13,14,15)13-15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree46_g <- groupOTU(all_tree46, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(10, 18), j = c(10, 17), k = c(10, 16), l = c(13, 15)))
all_sm46 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 2.0, 3.7417, 6.1644, 6.3246)
all_tp46 <- ggtree(all_tree46_g,
  aes(size=(all_sm46[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp46$layers[[1]]$aes_params$alpha <- 0.064563
all_tp46$layers[[1]]$aes_params$colour <- 'black'

all_tree47 <- read.tree(text="(1,(2,(3,4,((((((5,6)5-6,7,(8,(9,10)9-10)8-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree47_g <- groupOTU(all_tree47, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(5, 6), j = c(8, 10), k = c(9, 10)))
all_sm47 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 4.899, 3.3166, 5.1962)
all_tp47 <- ggtree(all_tree47_g,
  aes(size=(all_sm47[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp47$layers[[1]]$aes_params$alpha <- 0.064563
all_tp47$layers[[1]]$aes_params$colour <- 'black'

all_tree48 <- read.tree(text="(1,(2,(3,4,(((5,6)5-6,7,((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree48_g <- groupOTU(all_tree48, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 6), g = c(8, 16), h = c(8, 10), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
all_sm48 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.899, 4.4721, 3.3166, 5.1962, 6.3246, 4.2426)
all_tp48 <- ggtree(all_tree48_g,
  aes(size=(all_sm48[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp48$layers[[1]]$aes_params$alpha <- 0.064563
all_tp48$layers[[1]]$aes_params$colour <- 'black'

all_tree49 <- read.tree(text="(1,(2,(3,4,(((5,6)5-6,7,(8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree49_g <- groupOTU(all_tree49, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 6), g = c(8, 16), h = c(9, 16), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
all_sm49 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.899, 4.4721, 6.0, 5.1962, 6.3246, 4.2426)
all_tp49 <- ggtree(all_tree49_g,
  aes(size=(all_sm49[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp49$layers[[1]]$aes_params$alpha <- 0.064563
all_tp49$layers[[1]]$aes_params$colour <- 'black'

all_tree50 <- read.tree(text="(1,(2,(3,4,(((5,6)5-6,7,(8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree50_g <- groupOTU(all_tree50, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 6), g = c(8, 16), h = c(9, 16), i = c(10, 16), j = c(10, 13), k = c(17, 19)))
all_sm50 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.899, 4.4721, 6.0, 6.1644, 4.7958, 4.2426)
all_tp50 <- ggtree(all_tree50_g,
  aes(size=(all_sm50[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp50$layers[[1]]$aes_params$alpha <- 0.064563
all_tp50$layers[[1]]$aes_params$colour <- 'black'

all_tree51 <- read.tree(text="(1,(2,(3,4,(((5,6)5-6,7,(8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree51_g <- groupOTU(all_tree51, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 6), g = c(8, 16), h = c(9, 16), i = c(10, 16), j = c(13, 15), k = c(17, 19)))
all_sm51 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.899, 4.4721, 6.0, 6.1644, 6.3246, 4.2426)
all_tp51 <- ggtree(all_tree51_g,
  aes(size=(all_sm51[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp51$layers[[1]]$aes_params$alpha <- 0.064563
all_tp51$layers[[1]]$aes_params$colour <- 'black'

all_tree52 <- read.tree(text="(1,(2,(3,4,(((((5,((6,7,8)6-8,(9,10)9-10)6-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree52_g <- groupOTU(all_tree52, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(6, 10), j = c(6, 8), k = c(9, 10)))
all_sm52 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 2.8284, 4.899, 5.1962)
all_tp52 <- ggtree(all_tree52_g,
  aes(size=(all_sm52[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp52$layers[[1]]$aes_params$alpha <- 0.064563
all_tp52$layers[[1]]$aes_params$colour <- 'black'

all_tree53 <- read.tree(text="(1,(2,(3,4,(((((5,(6,7,(8,(9,10)9-10)8-10)6-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree53_g <- groupOTU(all_tree53, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(6, 10), j = c(8, 10), k = c(9, 10)))
all_sm53 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 2.8284, 3.3166, 5.1962)
all_tp53 <- ggtree(all_tree53_g,
  aes(size=(all_sm53[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp53$layers[[1]]$aes_params$alpha <- 0.064563
all_tp53$layers[[1]]$aes_params$colour <- 'black'

all_tree54 <- read.tree(text="(1,(2,(3,4,((5,(((6,7,8)6-8,(9,10)9-10)6-10,11,12,(13,14,15)13-15,16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree54_g <- groupOTU(all_tree54, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 10), h = c(6, 8), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
all_sm54 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 2.8284, 4.899, 5.1962, 6.3246, 4.2426)
all_tp54 <- ggtree(all_tree54_g,
  aes(size=(all_sm54[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp54$layers[[1]]$aes_params$alpha <- 0.064563
all_tp54$layers[[1]]$aes_params$colour <- 'black'

all_tree55 <- read.tree(text="(1,(2,(3,4,((5,((6,7,8)6-8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree55_g <- groupOTU(all_tree55, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 8), h = c(9, 16), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
all_sm55 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.899, 6.0, 5.1962, 6.3246, 4.2426)
all_tp55 <- ggtree(all_tree55_g,
  aes(size=(all_sm55[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp55$layers[[1]]$aes_params$alpha <- 0.064563
all_tp55$layers[[1]]$aes_params$colour <- 'black'

all_tree56 <- read.tree(text="(1,(2,(3,4,((5,((6,7,8)6-8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree56_g <- groupOTU(all_tree56, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 8), h = c(9, 16), i = c(10, 16), j = c(10, 13), k = c(17, 19)))
all_sm56 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.899, 6.0, 6.1644, 4.7958, 4.2426)
all_tp56 <- ggtree(all_tree56_g,
  aes(size=(all_sm56[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp56$layers[[1]]$aes_params$alpha <- 0.064563
all_tp56$layers[[1]]$aes_params$colour <- 'black'

all_tree57 <- read.tree(text="(1,(2,(3,4,((5,((6,7,8)6-8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree57_g <- groupOTU(all_tree57, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 8), h = c(9, 16), i = c(10, 16), j = c(13, 15), k = c(17, 19)))
all_sm57 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.899, 6.0, 6.1644, 6.3246, 4.2426)
all_tp57 <- ggtree(all_tree57_g,
  aes(size=(all_sm57[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp57$layers[[1]]$aes_params$alpha <- 0.064563
all_tp57$layers[[1]]$aes_params$colour <- 'black'

all_tree58 <- read.tree(text="(1,(2,(3,4,((5,((6,7,(8,(9,10)9-10)8-10)6-10,11,12,(13,14,15)13-15,16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree58_g <- groupOTU(all_tree58, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 10), h = c(8, 10), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
all_sm58 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 2.8284, 3.3166, 5.1962, 6.3246, 4.2426)
all_tp58 <- ggtree(all_tree58_g,
  aes(size=(all_sm58[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp58$layers[[1]]$aes_params$alpha <- 0.064563
all_tp58$layers[[1]]$aes_params$colour <- 'black'

all_tree59 <- read.tree(text="(1,(2,(3,4,((5,(6,7,((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree59_g <- groupOTU(all_tree59, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(8, 16), h = c(8, 10), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
all_sm59 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.4721, 3.3166, 5.1962, 6.3246, 4.2426)
all_tp59 <- ggtree(all_tree59_g,
  aes(size=(all_sm59[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp59$layers[[1]]$aes_params$alpha <- 0.064563
all_tp59$layers[[1]]$aes_params$colour <- 'black'

all_tree60 <- read.tree(text="(1,(2,(3,4,((5,(6,7,(8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree60_g <- groupOTU(all_tree60, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(8, 16), h = c(9, 16), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
all_sm60 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.4721, 6.0, 5.1962, 6.3246, 4.2426)
all_tp60 <- ggtree(all_tree60_g,
  aes(size=(all_sm60[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp60$layers[[1]]$aes_params$alpha <- 0.064563
all_tp60$layers[[1]]$aes_params$colour <- 'black'

all_tree61 <- read.tree(text="(1,(2,(3,4,((5,(6,7,(8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree61_g <- groupOTU(all_tree61, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(8, 16), h = c(9, 16), i = c(10, 16), j = c(10, 13), k = c(17, 19)))
all_sm61 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.4721, 6.0, 6.1644, 4.7958, 4.2426)
all_tp61 <- ggtree(all_tree61_g,
  aes(size=(all_sm61[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp61$layers[[1]]$aes_params$alpha <- 0.064563
all_tp61$layers[[1]]$aes_params$colour <- 'black'

all_tree62 <- read.tree(text="(1,(2,(3,4,((5,(6,7,(8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree62_g <- groupOTU(all_tree62, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(8, 16), h = c(9, 16), i = c(10, 16), j = c(13, 15), k = c(17, 19)))
all_sm62 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 4.4721, 6.0, 6.1644, 6.3246, 4.2426)
all_tp62 <- ggtree(all_tree62_g,
  aes(size=(all_sm62[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp62$layers[[1]]$aes_params$alpha <- 0.064563
all_tp62$layers[[1]]$aes_params$colour <- 'black'

all_tree63 <- read.tree(text="(1,(2,(3,4,((((((5,6)5-6,7,8,9,(10,11,12,13)10-13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree63_g <- groupOTU(all_tree63, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(5, 6), j = c(10, 13)))
all_sm63 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 4.899, 4.7958)
all_tp63 <- ggtree(all_tree63_g,
  aes(size=(all_sm63[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp63$layers[[1]]$aes_params$alpha <- 0.064563
all_tp63$layers[[1]]$aes_params$colour <- 'black'

all_tree64 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,(8,(9,10)9-10)8-10,11,12,13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree64_g <- groupOTU(all_tree64, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(5, 6), h = c(8, 10), i = c(9, 10), j = c(17, 19)))
all_sm64 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 4.899, 3.3166, 5.1962, 4.2426)
all_tp64 <- ggtree(all_tree64_g,
  aes(size=(all_sm64[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp64$layers[[1]]$aes_params$alpha <- 0.064563
all_tp64$layers[[1]]$aes_params$colour <- 'black'

all_tree65 <- read.tree(text="(1,(2,(3,4,(((((5,(6,7,8)6-8,9,(10,11,12,13)10-13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree65_g <- groupOTU(all_tree65, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(6, 8), j = c(10, 13)))
all_sm65 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 4.899, 4.7958)
all_tp65 <- ggtree(all_tree65_g,
  aes(size=(all_sm65[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp65$layers[[1]]$aes_params$alpha <- 0.064563
all_tp65$layers[[1]]$aes_params$colour <- 'black'

all_tree66 <- read.tree(text="(1,(2,(3,4,(((5,((6,7,8)6-8,(9,10)9-10)6-10,11,12,13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree66_g <- groupOTU(all_tree66, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(6, 10), h = c(6, 8), i = c(9, 10), j = c(17, 19)))
all_sm66 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 2.8284, 4.899, 5.1962, 4.2426)
all_tp66 <- ggtree(all_tree66_g,
  aes(size=(all_sm66[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp66$layers[[1]]$aes_params$alpha <- 0.064563
all_tp66$layers[[1]]$aes_params$colour <- 'black'

all_tree67 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,(8,(9,10)9-10)8-10)6-10,11,12,13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree67_g <- groupOTU(all_tree67, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(6, 10), h = c(8, 10), i = c(9, 10), j = c(17, 19)))
all_sm67 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 2.8284, 3.3166, 5.1962, 4.2426)
all_tp67 <- ggtree(all_tree67_g,
  aes(size=(all_sm67[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp67$layers[[1]]$aes_params$alpha <- 0.064563
all_tp67$layers[[1]]$aes_params$colour <- 'black'

all_tree68 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,9,(10,11,12,13)10-13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree68_g <- groupOTU(all_tree68, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(5, 6), h = c(10, 13), i = c(17, 19)))
all_sm68 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 4.899, 4.7958, 4.2426)
all_tp68 <- ggtree(all_tree68_g,
  aes(size=(all_sm68[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp68$layers[[1]]$aes_params$alpha <- 0.064563
all_tp68$layers[[1]]$aes_params$colour <- 'black'

all_tree69 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,9,(10,11,12,13)10-13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
all_tree69_g <- groupOTU(all_tree69, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(6, 8), h = c(10, 13), i = c(17, 19)))
all_sm69 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 4.899, 4.7958, 4.2426)
all_tp69 <- ggtree(all_tree69_g,
  aes(size=(all_sm69[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
all_tp69$layers[[1]]$aes_params$alpha <- 0.064563
all_tp69$layers[[1]]$aes_params$colour <- 'black'

panel_all_design <- c(
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
panel_all <- (
  all_tp1 +
  all_tp2 +
  all_tp3 +
  all_tp4 +
  all_tp5 +
  all_tp6 +
  all_tp7 +
  all_tp8 +
  all_tp9 +
  all_tp10 +
  all_tp11 +
  all_tp12 +
  all_tp13 +
  all_tp14 +
  all_tp15 +
  all_tp16 +
  all_tp17 +
  all_tp18 +
  all_tp19 +
  all_tp20 +
  all_tp21 +
  all_tp22 +
  all_tp23 +
  all_tp24 +
  all_tp25 +
  all_tp26 +
  all_tp27 +
  all_tp28 +
  all_tp29 +
  all_tp30 +
  all_tp31 +
  all_tp32 +
  all_tp33 +
  all_tp34 +
  all_tp35 +
  all_tp36 +
  all_tp37 +
  all_tp38 +
  all_tp39 +
  all_tp40 +
  all_tp41 +
  all_tp42 +
  all_tp43 +
  all_tp44 +
  all_tp45 +
  all_tp46 +
  all_tp47 +
  all_tp48 +
  all_tp49 +
  all_tp50 +
  all_tp51 +
  all_tp52 +
  all_tp53 +
  all_tp54 +
  all_tp55 +
  all_tp56 +
  all_tp57 +
  all_tp58 +
  all_tp59 +
  all_tp60 +
  all_tp61 +
  all_tp62 +
  all_tp63 +
  all_tp64 +
  all_tp65 +
  all_tp66 +
  all_tp67 +
  all_tp68 +
  all_tp69) +
  plot_layout(design=panel_all_design)
panel_all <- panel_all + plot_annotation(title='All 69 families')

# ── Panel A: Group A: [5–13] (10 families) ──
ga_tree1 <- read.tree(text="(1,(2,(3,4,((((((5,6)5-6,7,(8,(9,10)9-10)8-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ga_tree1_g <- groupOTU(ga_tree1, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(5, 6), j = c(8, 10), k = c(9, 10)))
ga_sm1 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 4.899, 3.3166, 5.1962)
ga_tp1 <- ggtree(ga_tree1_g,
  aes(size=(ga_sm1[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
ga_tp1$layers[[1]]$aes_params$alpha <- 0.369043
ga_tp1$layers[[1]]$aes_params$colour <- 'black'

ga_tree2 <- read.tree(text="(1,(2,(3,4,(((((5,((6,7,8)6-8,(9,10)9-10)6-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ga_tree2_g <- groupOTU(ga_tree2, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(6, 10), j = c(6, 8), k = c(9, 10)))
ga_sm2 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 2.8284, 4.899, 5.1962)
ga_tp2 <- ggtree(ga_tree2_g,
  aes(size=(ga_sm2[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
ga_tp2$layers[[1]]$aes_params$alpha <- 0.369043
ga_tp2$layers[[1]]$aes_params$colour <- 'black'

ga_tree3 <- read.tree(text="(1,(2,(3,4,(((((5,(6,7,(8,(9,10)9-10)8-10)6-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ga_tree3_g <- groupOTU(ga_tree3, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(6, 10), j = c(8, 10), k = c(9, 10)))
ga_sm3 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 2.8284, 3.3166, 5.1962)
ga_tp3 <- ggtree(ga_tree3_g,
  aes(size=(ga_sm3[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
ga_tp3$layers[[1]]$aes_params$alpha <- 0.369043
ga_tp3$layers[[1]]$aes_params$colour <- 'black'

ga_tree4 <- read.tree(text="(1,(2,(3,4,((((((5,6)5-6,7,8,9,(10,11,12,13)10-13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ga_tree4_g <- groupOTU(ga_tree4, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(5, 6), j = c(10, 13)))
ga_sm4 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 4.899, 4.7958)
ga_tp4 <- ggtree(ga_tree4_g,
  aes(size=(ga_sm4[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
ga_tp4$layers[[1]]$aes_params$alpha <- 0.369043
ga_tp4$layers[[1]]$aes_params$colour <- 'black'

ga_tree5 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,(8,(9,10)9-10)8-10,11,12,13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ga_tree5_g <- groupOTU(ga_tree5, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(5, 6), h = c(8, 10), i = c(9, 10), j = c(17, 19)))
ga_sm5 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 4.899, 3.3166, 5.1962, 4.2426)
ga_tp5 <- ggtree(ga_tree5_g,
  aes(size=(ga_sm5[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
ga_tp5$layers[[1]]$aes_params$alpha <- 0.369043
ga_tp5$layers[[1]]$aes_params$colour <- 'black'

ga_tree6 <- read.tree(text="(1,(2,(3,4,(((((5,(6,7,8)6-8,9,(10,11,12,13)10-13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ga_tree6_g <- groupOTU(ga_tree6, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 13), i = c(6, 8), j = c(10, 13)))
ga_sm6 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 3.1623, 4.899, 4.7958)
ga_tp6 <- ggtree(ga_tree6_g,
  aes(size=(ga_sm6[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
ga_tp6$layers[[1]]$aes_params$alpha <- 0.369043
ga_tp6$layers[[1]]$aes_params$colour <- 'black'

ga_tree7 <- read.tree(text="(1,(2,(3,4,(((5,((6,7,8)6-8,(9,10)9-10)6-10,11,12,13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ga_tree7_g <- groupOTU(ga_tree7, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(6, 10), h = c(6, 8), i = c(9, 10), j = c(17, 19)))
ga_sm7 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 2.8284, 4.899, 5.1962, 4.2426)
ga_tp7 <- ggtree(ga_tree7_g,
  aes(size=(ga_sm7[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
ga_tp7$layers[[1]]$aes_params$alpha <- 0.369043
ga_tp7$layers[[1]]$aes_params$colour <- 'black'

ga_tree8 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,(8,(9,10)9-10)8-10)6-10,11,12,13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ga_tree8_g <- groupOTU(ga_tree8, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(6, 10), h = c(8, 10), i = c(9, 10), j = c(17, 19)))
ga_sm8 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 2.8284, 3.3166, 5.1962, 4.2426)
ga_tp8 <- ggtree(ga_tree8_g,
  aes(size=(ga_sm8[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
ga_tp8$layers[[1]]$aes_params$alpha <- 0.369043
ga_tp8$layers[[1]]$aes_params$colour <- 'black'

ga_tree9 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,9,(10,11,12,13)10-13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ga_tree9_g <- groupOTU(ga_tree9, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(5, 6), h = c(10, 13), i = c(17, 19)))
ga_sm9 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 4.899, 4.7958, 4.2426)
ga_tp9 <- ggtree(ga_tree9_g,
  aes(size=(ga_sm9[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
ga_tp9$layers[[1]]$aes_params$alpha <- 0.369043
ga_tp9$layers[[1]]$aes_params$colour <- 'black'

ga_tree10 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,9,(10,11,12,13)10-13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ga_tree10_g <- groupOTU(ga_tree10, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 13), g = c(6, 8), h = c(10, 13), i = c(17, 19)))
ga_sm10 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 3.1623, 4.899, 4.7958, 4.2426)
ga_tp10 <- ggtree(ga_tree10_g,
  aes(size=(ga_sm10[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
ga_tp10$layers[[1]]$aes_params$alpha <- 0.369043
ga_tp10$layers[[1]]$aes_params$colour <- 'black'

panel_A_design <- c(
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
panel_A <- (
  ga_tp1 +
  ga_tp2 +
  ga_tp3 +
  ga_tp4 +
  ga_tp5 +
  ga_tp6 +
  ga_tp7 +
  ga_tp8 +
  ga_tp9 +
  ga_tp10) +
  plot_layout(design=panel_A_design)
panel_A <- panel_A + plot_annotation(title='Group A: [5–13] (10 families)')

# ── Panel B: Group B: [6–17] (23 families) ──
gb_tree1 <- read.tree(text="(1,(2,(3,4,((((5,((((6,7,8)6-8,(9,10)9-10)6-10,11,12,(13,14,15)13-15,16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gb_tree1_g <- groupOTU(gb_tree1, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 10), k = c(6, 8), l = c(9, 10), m = c(13, 15)))
gb_sm1 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 2.8284, 4.899, 5.1962, 6.3246)
gb_tp1 <- ggtree(gb_tree1_g,
  aes(size=(gb_sm1[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gb_tp1$layers[[1]]$aes_params$alpha <- 0.318708
gb_tp1$layers[[1]]$aes_params$colour <- 'black'

gb_tree2 <- read.tree(text="(1,(2,(3,4,((((5,(6,7,((8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16,17)8-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gb_tree2_g <- groupOTU(gb_tree2, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
gb_sm2 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 6.0, 6.1644, 4.7958)
gb_tp2 <- ggtree(gb_tree2_g,
  aes(size=(gb_sm2[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gb_tp2$layers[[1]]$aes_params$alpha <- 0.318708
gb_tp2$layers[[1]]$aes_params$colour <- 'black'

gb_tree3 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gb_tree3_g <- groupOTU(gb_tree3, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(10, 13)))
gb_sm3 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 3.7417, 6.1644, 4.7958)
gb_tp3 <- ggtree(gb_tree3_g,
  aes(size=(gb_sm3[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gb_tp3$layers[[1]]$aes_params$alpha <- 0.318708
gb_tp3$layers[[1]]$aes_params$colour <- 'black'

gb_tree4 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,(8,(9,10)9-10)8-10)6-10,11,12,(13,14,15)13-15,16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gb_tree4_g <- groupOTU(gb_tree4, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 10), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
gb_sm4 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 2.8284, 3.3166, 5.1962, 6.3246)
gb_tp4 <- ggtree(gb_tree4_g,
  aes(size=(gb_sm4[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gb_tp4$layers[[1]]$aes_params$alpha <- 0.318708
gb_tp4$layers[[1]]$aes_params$colour <- 'black'

gb_tree5 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,8)6-8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gb_tree5_g <- groupOTU(gb_tree5, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 8), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
gb_sm5 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.899, 6.0, 5.1962, 6.3246)
gb_tp5 <- ggtree(gb_tree5_g,
  aes(size=(gb_sm5[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gb_tp5$layers[[1]]$aes_params$alpha <- 0.318708
gb_tp5$layers[[1]]$aes_params$colour <- 'black'

gb_tree6 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,8)6-8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gb_tree6_g <- groupOTU(gb_tree6, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 8), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
gb_sm6 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.899, 6.0, 6.1644, 4.7958)
gb_tp6 <- ggtree(gb_tree6_g,
  aes(size=(gb_sm6[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gb_tp6$layers[[1]]$aes_params$alpha <- 0.318708
gb_tp6$layers[[1]]$aes_params$colour <- 'black'

gb_tree7 <- read.tree(text="(1,(2,(3,4,((((5,(((6,7,8)6-8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gb_tree7_g <- groupOTU(gb_tree7, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(6, 8), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
gb_sm7 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.899, 6.0, 6.1644, 6.3246)
gb_tp7 <- ggtree(gb_tree7_g,
  aes(size=(gb_sm7[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gb_tp7$layers[[1]]$aes_params$alpha <- 0.318708
gb_tp7$layers[[1]]$aes_params$colour <- 'black'

gb_tree8 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,(((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gb_tree8_g <- groupOTU(gb_tree8, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
gb_sm8 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 6.0, 5.1962, 6.3246)
gb_tp8 <- ggtree(gb_tree8_g,
  aes(size=(gb_sm8[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gb_tp8$layers[[1]]$aes_params$alpha <- 0.318708
gb_tp8$layers[[1]]$aes_params$colour <- 'black'

gb_tree9 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gb_tree9_g <- groupOTU(gb_tree9, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
gb_sm9 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 6.0, 6.1644, 4.7958)
gb_tp9 <- ggtree(gb_tree9_g,
  aes(size=(gb_sm9[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gb_tp9$layers[[1]]$aes_params$alpha <- 0.318708
gb_tp9$layers[[1]]$aes_params$colour <- 'black'

gb_tree10 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gb_tree10_g <- groupOTU(gb_tree10, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
gb_sm10 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 6.0, 6.1644, 6.3246)
gb_tp10 <- ggtree(gb_tree10_g,
  aes(size=(gb_sm10[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gb_tp10$layers[[1]]$aes_params$alpha <- 0.318708
gb_tp10$layers[[1]]$aes_params$colour <- 'black'

gb_tree11 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,(9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gb_tree11_g <- groupOTU(gb_tree11, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 8), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(13, 15)))
gb_sm11 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.899, 5.0, 3.7417, 6.1644, 6.3246)
gb_tp11 <- ggtree(gb_tree11_g,
  aes(size=(gb_sm11[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gb_tp11$layers[[1]]$aes_params$alpha <- 0.318708
gb_tp11$layers[[1]]$aes_params$colour <- 'black'

gb_tree12 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16)6-16,17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gb_tree12_g <- groupOTU(gb_tree12, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(6, 17), i = c(6, 16), j = c(8, 16), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
gb_sm12 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.7958, 4.2426, 4.4721, 3.3166, 5.1962, 6.3246)
gb_tp12 <- ggtree(gb_tree12_g,
  aes(size=(gb_sm12[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gb_tp12$layers[[1]]$aes_params$alpha <- 0.318708
gb_tp12$layers[[1]]$aes_params$colour <- 'black'

panel_B_design <- c(
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
panel_B <- (
  gb_tp1 +
  gb_tp2 +
  gb_tp3 +
  gb_tp4 +
  gb_tp5 +
  gb_tp6 +
  gb_tp7 +
  gb_tp8 +
  gb_tp9 +
  gb_tp10 +
  gb_tp11 +
  gb_tp12) +
  plot_layout(design=panel_B_design)
panel_B <- panel_B + plot_annotation(title='Group B: [6–17] (23 families)')

# ── Panel C: Group C: neither (36 families) ──
gc_tree1 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gc_tree1_g <- groupOTU(gc_tree1, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(8, 10), l = c(9, 10), m = c(13, 15)))
gc_sm1 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 4.4721, 3.3166, 5.1962, 6.3246)
gc_tp1 <- ggtree(gc_tree1_g,
  aes(size=(gc_sm1[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gc_tp1$layers[[1]]$aes_params$alpha <- 0.318708
gc_tp1$layers[[1]]$aes_params$colour <- 'black'

gc_tree2 <- read.tree(text="(1,(2,(3,4,(((5,(6,7,8)6-8,(((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17,18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gc_tree2_g <- groupOTU(gc_tree2, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(6, 8), h = c(9, 18), i = c(9, 17), j = c(9, 16), k = c(10, 16), l = c(10, 13)))
gc_sm2 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 5.0, 6.0, 6.1644, 4.7958)
gc_tp2 <- ggtree(gc_tree2_g,
  aes(size=(gc_sm2[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gc_tp2$layers[[1]]$aes_params$alpha <- 0.318708
gc_tp2$layers[[1]]$aes_params$colour <- 'black'

gc_tree3 <- read.tree(text="(1,(2,(3,4,((5,(((6,7,8)6-8,(9,10)9-10)6-10,11,12,(13,14,15)13-15,16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gc_tree3_g <- groupOTU(gc_tree3, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(6, 16), g = c(6, 10), h = c(6, 8), i = c(9, 10), j = c(13, 15), k = c(17, 19)))
gc_sm3 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 4.2426, 2.8284, 4.899, 5.1962, 6.3246, 4.2426)
gc_tp3 <- ggtree(gc_tree3_g,
  aes(size=(gc_sm3[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gc_tp3$layers[[1]]$aes_params$alpha <- 0.318708
gc_tp3$layers[[1]]$aes_params$colour <- 'black'

gc_tree4 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(9,((((10,11,12,13)10-13,14,15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gc_tree4_g <- groupOTU(gc_tree4, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 6), h = c(9, 18), i = c(10, 18), j = c(10, 17), k = c(10, 16), l = c(10, 13)))
gc_sm4 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 4.899, 3.7417, 2.0, 3.7417, 6.1644, 4.7958)
gc_tp4 <- ggtree(gc_tree4_g,
  aes(size=(gc_sm4[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gc_tp4$layers[[1]]$aes_params$alpha <- 0.318708
gc_tp4$layers[[1]]$aes_params$colour <- 'black'

gc_tree5 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,((8,((9,10)9-10,11,12,(13,14,15)13-15,16)9-16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gc_tree5_g <- groupOTU(gc_tree5, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
gc_sm5 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 4.4721, 6.0, 5.1962, 6.3246)
gc_tp5 <- ggtree(gc_tree5_g,
  aes(size=(gc_sm5[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gc_tp5$layers[[1]]$aes_params$alpha <- 0.318708
gc_tp5$layers[[1]]$aes_params$colour <- 'black'

gc_tree6 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,((8,(9,((10,11,12,13)10-13,14,15,16)10-16)9-16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gc_tree6_g <- groupOTU(gc_tree6, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
gc_sm6 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 4.4721, 6.0, 6.1644, 4.7958)
gc_tp6 <- ggtree(gc_tree6_g,
  aes(size=(gc_sm6[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gc_tp6$layers[[1]]$aes_params$alpha <- 0.318708
gc_tp6$layers[[1]]$aes_params$colour <- 'black'

gc_tree7 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,((8,(9,(10,11,12,(13,14,15)13-15,16)10-16)9-16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gc_tree7_g <- groupOTU(gc_tree7, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(8, 16), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
gc_sm7 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 4.4721, 6.0, 6.1644, 6.3246)
gc_tp7 <- ggtree(gc_tree7_g,
  aes(size=(gc_sm7[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gc_tp7$layers[[1]]$aes_params$alpha <- 0.318708
gc_tp7$layers[[1]]$aes_params$colour <- 'black'

gc_tree8 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,(((9,10)9-10,11,12,(13,14,15)13-15,16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gc_tree8_g <- groupOTU(gc_tree8, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(9, 10), m = c(13, 15)))
gc_sm8 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 6.0, 5.1962, 6.3246)
gc_tp8 <- ggtree(gc_tree8_g,
  aes(size=(gc_sm8[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gc_tp8$layers[[1]]$aes_params$alpha <- 0.318708
gc_tp8$layers[[1]]$aes_params$colour <- 'black'

gc_tree9 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,((9,((10,11,12,13)10-13,14,15,16)10-16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gc_tree9_g <- groupOTU(gc_tree9, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(10, 13)))
gc_sm9 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 6.0, 6.1644, 4.7958)
gc_tp9 <- ggtree(gc_tree9_g,
  aes(size=(gc_sm9[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gc_tp9$layers[[1]]$aes_params$alpha <- 0.318708
gc_tp9$layers[[1]]$aes_params$colour <- 'black'

gc_tree10 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gc_tree10_g <- groupOTU(gc_tree10, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(9, 16), l = c(10, 16), m = c(13, 15)))
gc_sm10 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 6.0, 6.1644, 6.3246)
gc_tp10 <- ggtree(gc_tree10_g,
  aes(size=(gc_sm10[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gc_tp10$layers[[1]]$aes_params$alpha <- 0.318708
gc_tp10$layers[[1]]$aes_params$colour <- 'black'

gc_tree11 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,(9,(((10,11,12,13)10-13,14,15,16)10-16,17)10-17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gc_tree11_g <- groupOTU(gc_tree11, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(10, 13)))
gc_sm11 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 3.7417, 6.1644, 4.7958)
gc_tp11 <- ggtree(gc_tree11_g,
  aes(size=(gc_sm11[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gc_tp11$layers[[1]]$aes_params$alpha <- 0.318708
gc_tp11$layers[[1]]$aes_params$colour <- 'black'

gc_tree12 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,(9,((10,11,12,(13,14,15)13-15,16)10-16,17)10-17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
gc_tree12_g <- groupOTU(gc_tree12, list(a = c(1, 22), b = c(2, 22), c = c(3, 21), d = c(5, 21), e = c(5, 19), f = c(5, 18), g = c(5, 17), h = c(5, 6), i = c(8, 17), j = c(9, 17), k = c(10, 17), l = c(10, 16), m = c(13, 15)))
gc_sm12 <- c(0.5, 8.3066, 8.3066, 8.3066, 8.3066, 8.3066, 7.1414, 6.0828, 4.899, 4.2426, 5.0, 3.7417, 6.1644, 6.3246)
gc_tp12 <- ggtree(gc_tree12_g,
  aes(size=(gc_sm12[group])),
  layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none') +
  scale_size_identity()
gc_tp12$layers[[1]]$aes_params$alpha <- 0.318708
gc_tp12$layers[[1]]$aes_params$colour <- 'black'

panel_C_design <- c(
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
panel_C <- (
  gc_tp1 +
  gc_tp2 +
  gc_tp3 +
  gc_tp4 +
  gc_tp5 +
  gc_tp6 +
  gc_tp7 +
  gc_tp8 +
  gc_tp9 +
  gc_tp10 +
  gc_tp11 +
  gc_tp12) +
  plot_layout(design=panel_C_design)
panel_C <- panel_C + plot_annotation(title='Group C: neither (36 families)')

# ── Final layout ──
forest <- (panel_all / (panel_A | panel_B | panel_C)) +
  plot_layout(heights=c(2, 1))

ggsave('/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/../results/nyan1308_conflict_groups.pdf', forest, width=24, height=20)
