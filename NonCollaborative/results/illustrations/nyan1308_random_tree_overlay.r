library(ape)
library(ggplot2)
library(ggtree)
library(patchwork)

posLabel <- list("1" = "QM", "2" = "PreSbj", "3" = "Sbj", "4" = "PostSbj", "5" = "Neg1", "6" = "SM", "7" = "Neg2", "8" = "TAM", "9" = "OM", "10" = "Root", "11" = "Ext", "12" = "STAT", "13" = "CAUS", "14" = "APPL", "15" = "REC", "16" = "PASS", "17" = "FV", "18" = "2P", "19" = "Enc", "20" = "Obj1", "21" = "Obj2", "22" = "PostObj")

rt_tree1 <- read.tree(text="((1,(2,((3,4)3-4,5,6)3-6)2-6,(7,8)7-8,9,((10,11)10-11,(12,((13,14)13-14,15)13-15)12-15)10-15)1-15,(16,17,(18,19)18-19)16-19,(20,(21,22)21-22)20-22)1-22;")
rt_tp1 <- ggtree(rt_tree1, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp1$layers[[1]]$aes_params$alpha <- 0.02
rt_tp1$layers[[1]]$aes_params$colour <- 'black'

rt_tree2 <- read.tree(text="((((((1,2,3)1-3,4,5)1-5,6,(7,8)7-8,(9,10,11)9-11,12)1-12,13)1-13,14,(15,((16,(17,18)17-18)16-18,19)16-19,20,21)15-21)1-21,22)1-22;")
rt_tp2 <- ggtree(rt_tree2, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp2$layers[[1]]$aes_params$alpha <- 0.02
rt_tp2$layers[[1]]$aes_params$colour <- 'black'

rt_tree3 <- read.tree(text="(1,(2,3)2-3,((4,((5,6)5-6,(7,((8,9,10)8-10,11)8-11)7-11)5-11)4-11,12,13,14,15)4-15,(16,17,((18,(19,20)19-20)18-20,21)18-21,22)16-22)1-22;")
rt_tp3 <- ggtree(rt_tree3, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp3$layers[[1]]$aes_params$alpha <- 0.02
rt_tp3$layers[[1]]$aes_params$colour <- 'black'

rt_tree4 <- read.tree(text="((1,(2,(3,((4,5)4-5,6)4-6)3-6,7)2-7)1-7,(8,((9,(((10,11)10-11,12)10-12,13,((14,15)14-15,16)14-16)10-16)9-16,((17,(18,(19,20)19-20)18-20,21)17-21,22)17-22)9-22)8-22)1-22;")
rt_tp4 <- ggtree(rt_tree4, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp4$layers[[1]]$aes_params$alpha <- 0.02
rt_tp4$layers[[1]]$aes_params$colour <- 'black'

rt_tree5 <- read.tree(text="(1,((2,3)2-3,(4,(((5,(6,7,(8,9)8-9,10)6-10)5-10,11,(12,(13,14)13-14)12-14)5-14,15)5-15,(16,17,((18,19)18-19,(20,21,22)20-22)18-22)16-22)4-22)2-22)1-22;")
rt_tp5 <- ggtree(rt_tree5, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp5$layers[[1]]$aes_params$alpha <- 0.02
rt_tp5$layers[[1]]$aes_params$colour <- 'black'

rt_tree6 <- read.tree(text="((1,2)1-2,((3,(4,(5,6,((7,8)7-8,((9,10)9-10,11,(((((12,13,14)12-14,15)12-15,16)12-16,17)12-17,18)12-18)9-18)7-18,19)5-19)4-19,(20,21)20-21)3-21,22)3-22)1-22;")
rt_tp6 <- ggtree(rt_tree6, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp6$layers[[1]]$aes_params$alpha <- 0.02
rt_tp6$layers[[1]]$aes_params$colour <- 'black'

rt_tree7 <- read.tree(text="((((1,(2,3)2-3,((4,5)4-5,6)4-6)1-6,(7,8)7-8)1-8,9,10,((11,12,(13,((14,15)14-15,((16,17)16-17,18)16-18)14-18)13-18)11-18,(19,20)19-20,21)11-21)1-21,22)1-22;")
rt_tp7 <- ggtree(rt_tree7, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp7$layers[[1]]$aes_params$alpha <- 0.02
rt_tp7$layers[[1]]$aes_params$colour <- 'black'

rt_tree8 <- read.tree(text="(1,(((2,(3,4)3-4,((5,6,(((((7,8)7-8,9,10)7-10,11)7-11,12,13,14,15)7-15,16,(17,18)17-18)7-18)5-18,19)5-19)2-19,20)2-20,21)2-21,22)1-22;")
rt_tp8 <- ggtree(rt_tree8, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp8$layers[[1]]$aes_params$alpha <- 0.02
rt_tp8$layers[[1]]$aes_params$colour <- 'black'

rt_tree9 <- read.tree(text="((1,(2,3,((4,((5,6,7,8)5-8,((9,10)9-10,11,12,13,14)9-14)5-14)4-14,(((15,16,17,18)15-18,19)15-19,20)15-20)4-20)2-20,21)1-21,22)1-22;")
rt_tp9 <- ggtree(rt_tree9, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp9$layers[[1]]$aes_params$alpha <- 0.02
rt_tp9$layers[[1]]$aes_params$colour <- 'black'

rt_tree10 <- read.tree(text="((((((1,(2,((((3,(4,((5,((6,7)6-7,8,9,10,11)6-11)5-11,12)5-12)4-12)3-12,13)3-13,14)3-14,(15,16)15-16)3-16)2-16)1-16,17)1-17,(18,19)18-19)1-19,20)1-20,21)1-21,22)1-22;")
rt_tp10 <- ggtree(rt_tree10, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp10$layers[[1]]$aes_params$alpha <- 0.02
rt_tp10$layers[[1]]$aes_params$colour <- 'black'

rt_tree11 <- read.tree(text="(1,((2,((3,(4,(5,6)5-6)4-6)3-6,((((7,8,(9,10)9-10)7-10,((11,12)11-12,13)11-13)7-13,14,15)7-15,16,17,18)7-18)3-18)2-18,((19,20)19-20,21)19-21)2-21,22)1-22;")
rt_tp11 <- ggtree(rt_tree11, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp11$layers[[1]]$aes_params$alpha <- 0.02
rt_tp11$layers[[1]]$aes_params$colour <- 'black'

rt_tree12 <- read.tree(text="(1,((((2,3)2-3,((4,5)4-5,6)4-6,7)2-7,(8,(9,10)9-10)8-10)2-10,(11,12)11-12,(13,14)13-14,15,((16,(17,18)17-18)16-18,(19,20)19-20)16-20,21)2-21,22)1-22;")
rt_tp12 <- ggtree(rt_tree12, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp12$layers[[1]]$aes_params$alpha <- 0.02
rt_tp12$layers[[1]]$aes_params$colour <- 'black'

rt_tree13 <- read.tree(text="((1,2)1-2,(3,((4,(5,6)5-6)4-6,7)4-7,(((((8,9)8-9,((10,11,12)10-12,13)10-13)8-13,(14,15)14-15)8-15,(16,17)16-17,18,19,(20,21)20-21)8-21,22)8-22)3-22)1-22;")
rt_tp13 <- ggtree(rt_tree13, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp13$layers[[1]]$aes_params$alpha <- 0.02
rt_tp13$layers[[1]]$aes_params$colour <- 'black'

rt_tree14 <- read.tree(text="((1,((2,3,(4,5)4-5,6)2-6,((7,8,(((9,10)9-10,11)9-11,(12,13)12-13)9-13,14,15)7-15,16,17)7-17)2-17,18)1-18,(19,20,21)19-21,22)1-22;")
rt_tp14 <- ggtree(rt_tree14, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp14$layers[[1]]$aes_params$alpha <- 0.02
rt_tp14$layers[[1]]$aes_params$colour <- 'black'

rt_tree15 <- read.tree(text="(1,((2,(3,(4,(5,6,7)5-7,8)4-8,9)3-9)2-9,(10,11,12,((13,((((14,15)14-15,16)14-16,17,18)14-18,19)14-19)13-19,20)13-20)10-20)2-20,21,22)1-22;")
rt_tp15 <- ggtree(rt_tree15, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp15$layers[[1]]$aes_params$alpha <- 0.02
rt_tp15$layers[[1]]$aes_params$colour <- 'black'

rt_tree16 <- read.tree(text="((1,((2,((3,4,(((5,(6,(7,8)7-8)6-8)5-8,9)5-9,(10,11,12)10-12)5-12,(13,(14,(15,16)15-16)14-16,17)13-17)3-17,18)3-18)2-18,(19,20)19-20)2-20)1-20,(21,22)21-22)1-22;")
rt_tp16 <- ggtree(rt_tree16, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp16$layers[[1]]$aes_params$alpha <- 0.02
rt_tp16$layers[[1]]$aes_params$colour <- 'black'

rt_tree17 <- read.tree(text="((1,(((2,3)2-3,4,((5,6)5-6,7)5-7)2-7,((8,9,(10,11,(12,(13,14)13-14)12-14)10-14)8-14,15,(16,(17,((18,19)18-19,20)18-20)17-20)16-20)8-20,21)2-21)1-21,22)1-22;")
rt_tp17 <- ggtree(rt_tree17, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp17$layers[[1]]$aes_params$alpha <- 0.02
rt_tp17$layers[[1]]$aes_params$colour <- 'black'

rt_tree18 <- read.tree(text="((1,((2,3,4)2-4,((5,(6,7)6-7,8,((9,10)9-10,11)9-11)5-11,((12,13)12-13,14)12-14)5-14,15,16,17,18)2-18)1-18,(19,(20,(21,22)21-22)20-22)19-22)1-22;")
rt_tp18 <- ggtree(rt_tree18, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp18$layers[[1]]$aes_params$alpha <- 0.02
rt_tp18$layers[[1]]$aes_params$colour <- 'black'

rt_tree19 <- read.tree(text="(((1,2,3)1-3,4)1-4,5,(((6,7)6-7,8)6-8,9,10,(11,(12,(((13,(14,15,16)14-16)13-16,17)13-17,(18,19)18-19,((20,21)20-21,22)20-22)13-22)12-22)11-22)6-22)1-22;")
rt_tp19 <- ggtree(rt_tree19, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp19$layers[[1]]$aes_params$alpha <- 0.02
rt_tp19$layers[[1]]$aes_params$colour <- 'black'

rt_tree20 <- read.tree(text="(1,2,3,4,((5,(6,7)6-7,((8,9)8-9,(10,11)10-11)8-11,12)5-12,((((13,14,15)13-15,16)13-16,17)13-17,(18,19)18-19,(20,21)20-21)13-21)5-21,22)1-22;")
rt_tp20 <- ggtree(rt_tree20, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp20$layers[[1]]$aes_params$alpha <- 0.02
rt_tp20$layers[[1]]$aes_params$colour <- 'black'

rt_tree21 <- read.tree(text="(1,2,(3,(4,((5,6)5-6,7)5-7)4-7,(8,9,((10,(11,12)11-12)10-12,((13,14)13-14,((15,16)15-16,(17,18)17-18)15-18,(19,20,21)19-21)13-21)10-21)8-21)3-21,22)1-22;")
rt_tp21 <- ggtree(rt_tree21, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp21$layers[[1]]$aes_params$alpha <- 0.02
rt_tp21$layers[[1]]$aes_params$colour <- 'black'

rt_tree22 <- read.tree(text="(((1,2)1-2,((3,4,(5,6)5-6,(7,8)7-8)3-8,((9,10)9-10,((11,12,((13,14)13-14,(15,16)15-16)13-16)11-16,((17,18)17-18,19,(20,21)20-21)17-21)11-21)9-21)3-21)1-21,22)1-22;")
rt_tp22 <- ggtree(rt_tree22, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp22$layers[[1]]$aes_params$alpha <- 0.02
rt_tp22$layers[[1]]$aes_params$colour <- 'black'

rt_tree23 <- read.tree(text="((1,2)1-2,((3,((4,5)4-5,(6,(((7,8,9)7-9,10)7-10,(11,(12,13)12-13,14)11-14)7-14,(15,(16,(((17,18)17-18,19)17-19,(20,21)20-21)17-21)16-21)15-21)6-21)4-21)3-21,22)3-22)1-22;")
rt_tp23 <- ggtree(rt_tree23, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp23$layers[[1]]$aes_params$alpha <- 0.02
rt_tp23$layers[[1]]$aes_params$colour <- 'black'

rt_tree24 <- read.tree(text="(((((1,2)1-2,(3,(4,((5,(6,7)6-7)5-7,8)5-8,9)4-9)3-9)1-9,10)1-10,11)1-11,(((12,13,((((14,15,16)14-16,17)14-17,18)14-18,19)14-19)12-19,20)12-20,21,22)12-22)1-22;")
rt_tp24 <- ggtree(rt_tree24, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp24$layers[[1]]$aes_params$alpha <- 0.02
rt_tp24$layers[[1]]$aes_params$colour <- 'black'

rt_tree25 <- read.tree(text="(1,(2,(((3,4,((5,6)5-6,7,8)5-8)3-8,9)3-9,(10,(11,12)11-12)10-12,13,(14,((15,16,17)15-17,18,19)15-19)14-19,20)3-20)2-20,21,22)1-22;")
rt_tp25 <- ggtree(rt_tree25, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp25$layers[[1]]$aes_params$alpha <- 0.02
rt_tp25$layers[[1]]$aes_params$colour <- 'black'

rt_tree26 <- read.tree(text="(((1,((2,((3,4)3-4,5)3-5)2-5,(6,7)6-7,8)2-8)1-8,9)1-9,((((10,11)10-11,12)10-12,((13,14)13-14,15)13-15)10-15,((16,17,18)16-18,19)16-19)10-19,20,(21,22)21-22)1-22;")
rt_tp26 <- ggtree(rt_tree26, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp26$layers[[1]]$aes_params$alpha <- 0.02
rt_tp26$layers[[1]]$aes_params$colour <- 'black'

rt_tree27 <- read.tree(text="(((1,((((2,3)2-3,4)2-4,5)2-5,((((((6,(7,(8,((9,(10,11)10-11)9-11,12,13)9-13)8-13)7-13)6-13,14)6-14,15)6-15,16)6-16,17,18,19)6-19,20)6-20)2-20)1-20,21)1-21,22)1-22;")
rt_tp27 <- ggtree(rt_tree27, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp27$layers[[1]]$aes_params$alpha <- 0.02
rt_tp27$layers[[1]]$aes_params$colour <- 'black'

rt_tree28 <- read.tree(text="(1,(2,(3,(4,(((((5,6)5-6,(7,(8,(9,10,11)9-11)8-11,12)7-12,13)5-13,14)5-14,(15,16)15-16)5-16,(17,18)17-18,19,20)5-20,21)4-21)3-21,22)2-22)1-22;")
rt_tp28 <- ggtree(rt_tree28, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp28$layers[[1]]$aes_params$alpha <- 0.02
rt_tp28$layers[[1]]$aes_params$colour <- 'black'

rt_tree29 <- read.tree(text="(((1,(2,3,(4,(5,6,(7,8)7-8)5-8)4-8)2-8)1-8,(9,(10,11,12,13,(14,15)14-15)10-15)9-15)1-15,(16,(17,18,19)17-19,((20,21)20-21,22)20-22)16-22)1-22;")
rt_tp29 <- ggtree(rt_tree29, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp29$layers[[1]]$aes_params$alpha <- 0.02
rt_tp29$layers[[1]]$aes_params$colour <- 'black'

rt_tree30 <- read.tree(text="(1,((2,(((3,(4,(5,6)5-6,7)4-7)3-7,(8,9,(10,((11,12)11-12,(13,14)13-14)11-14,(15,(((16,17)16-17,18,19)16-19,20)16-20)15-20)10-20)8-20)3-20,21)3-21)2-21,22)2-22)1-22;")
rt_tp30 <- ggtree(rt_tree30, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp30$layers[[1]]$aes_params$alpha <- 0.02
rt_tp30$layers[[1]]$aes_params$colour <- 'black'

rt_tree31 <- read.tree(text="((1,2)1-2,((3,4)3-4,5,(6,7,((((8,9)8-9,10,11,12)8-12,(((((13,14)13-14,15,(16,17)16-17)13-17,18)13-18,19,20)13-20,21)13-21)8-21,22)8-22)6-22)3-22)1-22;")
rt_tp31 <- ggtree(rt_tree31, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp31$layers[[1]]$aes_params$alpha <- 0.02
rt_tp31$layers[[1]]$aes_params$colour <- 'black'

rt_tree32 <- read.tree(text="((((((1,((2,3,(4,5,6)4-6)2-6,7)2-7)1-7,(8,9,(10,11)10-11)8-11)1-11,(12,13)12-13,((14,15)14-15,16,17)14-17,18,19)1-19,20)1-20,21)1-21,22)1-22;")
rt_tp32 <- ggtree(rt_tree32, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp32$layers[[1]]$aes_params$alpha <- 0.02
rt_tp32$layers[[1]]$aes_params$colour <- 'black'

rt_tree33 <- read.tree(text="((1,2,(3,4)3-4)1-4,((5,(6,7,8)6-8)5-8,9,10,11)5-11,12,(13,14,15)13-15,16,((17,18)17-18,(19,20)19-20)17-20,21,22)1-22;")
rt_tp33 <- ggtree(rt_tree33, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp33$layers[[1]]$aes_params$alpha <- 0.02
rt_tp33$layers[[1]]$aes_params$colour <- 'black'

rt_tree34 <- read.tree(text="((((((1,2)1-2,3,4)1-4,((5,6)5-6,7,(8,9)8-9)5-9)1-9,(10,(11,(12,(13,14)13-14)12-14,(15,16)15-16)11-16,((17,18,19)17-19,20)17-20)10-20)1-20,21)1-21,22)1-22;")
rt_tp34 <- ggtree(rt_tree34, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp34$layers[[1]]$aes_params$alpha <- 0.02
rt_tp34$layers[[1]]$aes_params$colour <- 'black'

rt_tree35 <- read.tree(text="(1,((((2,3)2-3,4)2-4,5)2-5,(((6,7,(8,(9,10)9-10,(11,12)11-12,(13,14)13-14)8-14,15)6-15,((16,17)16-17,((18,(19,20)19-20)18-20,21)18-21)16-21)6-21,22)6-22)2-22)1-22;")
rt_tp35 <- ggtree(rt_tree35, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp35$layers[[1]]$aes_params$alpha <- 0.02
rt_tp35$layers[[1]]$aes_params$colour <- 'black'

rt_tree36 <- read.tree(text="(1,2,(3,((4,5,6,7)4-7,(8,(9,(10,(((11,12,(13,14)13-14)11-14,((15,16)15-16,17)15-17)11-17,18,19)11-19)10-19,20)9-20,(21,22)21-22)8-22)4-22)3-22)1-22;")
rt_tp36 <- ggtree(rt_tree36, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp36$layers[[1]]$aes_params$alpha <- 0.02
rt_tp36$layers[[1]]$aes_params$colour <- 'black'

rt_tree37 <- read.tree(text="((1,((((((((2,3)2-3,(4,5)4-5,6)2-6,(7,8,9)7-9)2-9,10,11)2-11,12)2-12,(((13,14)13-14,15)13-15,16)13-16)2-16,17)2-17,18,19)2-19,(20,21)20-21)1-21,22)1-22;")
rt_tp37 <- ggtree(rt_tree37, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp37$layers[[1]]$aes_params$alpha <- 0.02
rt_tp37$layers[[1]]$aes_params$colour <- 'black'

rt_tree38 <- read.tree(text="((1,2)1-2,(3,((4,5,6)4-6,((7,(((8,9)8-9,((((10,(11,12)11-12,(13,(14,15)14-15)13-15)10-15,16)10-16,17)10-17,18)10-18)8-18,19)8-19)7-19,20)7-20,21)4-21)3-21,22)1-22;")
rt_tp38 <- ggtree(rt_tree38, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp38$layers[[1]]$aes_params$alpha <- 0.02
rt_tp38$layers[[1]]$aes_params$colour <- 'black'

rt_tree39 <- read.tree(text="((1,2,3)1-3,(4,((5,6)5-6,(((7,((8,9)8-9,10)8-10,(11,12,13,14)11-14,15)7-15,(16,17)16-17)7-17,(18,19)18-19,(20,21)20-21,22)7-22)5-22)4-22)1-22;")
rt_tp39 <- ggtree(rt_tree39, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp39$layers[[1]]$aes_params$alpha <- 0.02
rt_tp39$layers[[1]]$aes_params$colour <- 'black'

rt_tree40 <- read.tree(text="(((1,(2,3,((4,(5,6)5-6,7)4-7,8,(9,10)9-10)4-10,11)2-11)1-11,((12,13)12-13,(14,15)14-15,(16,17)16-17,(18,19)18-19)12-19,20,21)1-21,22)1-22;")
rt_tp40 <- ggtree(rt_tree40, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp40$layers[[1]]$aes_params$alpha <- 0.02
rt_tp40$layers[[1]]$aes_params$colour <- 'black'

rt_tree41 <- read.tree(text="(1,(((2,3)2-3,4)2-4,((5,6,7)5-7,8,(((9,10,11)9-11,12)9-12,(((13,14,15,16)13-16,17)13-17,(18,19)18-19)13-19,(20,21)20-21,22)9-22)5-22)2-22)1-22;")
rt_tp41 <- ggtree(rt_tree41, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp41$layers[[1]]$aes_params$alpha <- 0.02
rt_tp41$layers[[1]]$aes_params$colour <- 'black'

rt_tree42 <- read.tree(text="(((1,(((2,3,(4,(5,6)5-6)4-6)2-6,(7,(8,(9,((10,(11,12)11-12)10-12,13)10-13)9-13)8-13)7-13,(14,(15,16)15-16)14-16)2-16,17)2-17)1-17,(18,19,20)18-20)1-20,(21,22)21-22)1-22;")
rt_tp42 <- ggtree(rt_tree42, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp42$layers[[1]]$aes_params$alpha <- 0.02
rt_tp42$layers[[1]]$aes_params$colour <- 'black'

rt_tree43 <- read.tree(text="((1,2)1-2,((3,4)3-4,5,((6,(7,8,9)7-9)6-9,(10,((11,(12,13)12-13)11-13,(14,((15,(16,(17,18)17-18)16-18,(19,20)19-20)15-20,21)15-21)14-21,22)11-22)10-22)6-22)3-22)1-22;")
rt_tp43 <- ggtree(rt_tree43, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp43$layers[[1]]$aes_params$alpha <- 0.02
rt_tp43$layers[[1]]$aes_params$colour <- 'black'

rt_tree44 <- read.tree(text="(1,(2,3)2-3,4,(5,(((6,7,8)6-8,(9,(10,11)10-11)9-11)6-11,(((12,13)12-13,(((14,15)14-15,16,17)14-17,18)14-18)12-18,19,20,21,22)12-22)6-22)5-22)1-22;")
rt_tp44 <- ggtree(rt_tree44, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp44$layers[[1]]$aes_params$alpha <- 0.02
rt_tp44$layers[[1]]$aes_params$colour <- 'black'

rt_tree45 <- read.tree(text="((1,(((2,((3,(4,5)4-5,6,7)3-7,8,((((9,10)9-10,11)9-11,12,(13,14)13-14)9-14,(15,16)15-16)9-16)3-16)2-16,17)2-17,18)2-18)1-18,(19,20)19-20,(21,22)21-22)1-22;")
rt_tp45 <- ggtree(rt_tree45, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp45$layers[[1]]$aes_params$alpha <- 0.02
rt_tp45$layers[[1]]$aes_params$colour <- 'black'

rt_tree46 <- read.tree(text="(1,2,((3,(4,(5,6)5-6)4-6)3-6,(7,((8,(9,10,11)9-11,12)8-12,((13,14)13-14,15,16,17)13-17,18,19)8-19,20,21)7-21)3-21,22)1-22;")
rt_tp46 <- ggtree(rt_tree46, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp46$layers[[1]]$aes_params$alpha <- 0.02
rt_tp46$layers[[1]]$aes_params$colour <- 'black'

rt_tree47 <- read.tree(text="(1,2,(((3,4,5)3-5,6)3-6,(((7,8)7-8,((((9,(10,11)10-11,12)9-12,13)9-13,(14,15)14-15)9-15,16)9-16,17)7-17,18,(19,(20,(21,22)21-22)20-22)19-22)7-22)3-22)1-22;")
rt_tp47 <- ggtree(rt_tree47, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp47$layers[[1]]$aes_params$alpha <- 0.02
rt_tp47$layers[[1]]$aes_params$colour <- 'black'

rt_tree48 <- read.tree(text="(((1,2)1-2,3,4,5)1-5,((6,(7,(8,9)8-9)7-9)6-9,((((10,11)10-11,12)10-12,(((13,14)13-14,(15,16)15-16)13-16,17)13-17)10-17,18)10-18,((19,20)19-20,21,22)19-22)6-22)1-22;")
rt_tp48 <- ggtree(rt_tree48, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp48$layers[[1]]$aes_params$alpha <- 0.02
rt_tp48$layers[[1]]$aes_params$colour <- 'black'

rt_tree49 <- read.tree(text="(((1,(2,(3,4,(5,(6,(7,8)7-8)6-8)5-8,(9,10,11,12)9-12)3-12)2-12)1-12,13)1-13,(14,15,(16,(((17,18)17-18,19)17-19,20)17-20,21,22)16-22)14-22)1-22;")
rt_tp49 <- ggtree(rt_tree49, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp49$layers[[1]]$aes_params$alpha <- 0.02
rt_tp49$layers[[1]]$aes_params$colour <- 'black'

rt_tree50 <- read.tree(text="(1,(2,(3,(4,(((5,6,7)5-7,8)5-8,9)5-9,(10,11)10-11)4-11)3-11,(12,(13,(14,15)14-15,16)13-16)12-16,(((17,(18,19)18-19)17-19,(20,21)20-21)17-21,22)17-22)2-22)1-22;")
rt_tp50 <- ggtree(rt_tree50, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp50$layers[[1]]$aes_params$alpha <- 0.02
rt_tp50$layers[[1]]$aes_params$colour <- 'black'

rt_tree51 <- read.tree(text="((1,2)1-2,(3,(((4,5)4-5,(6,(7,((8,(((9,10)9-10,11,12)9-12,13,((14,((15,16)15-16,17)15-17,18)14-18,19)14-19)9-19)8-19,20)8-20)7-20)6-20,21)4-21,22)4-22)3-22)1-22;")
rt_tp51 <- ggtree(rt_tree51, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp51$layers[[1]]$aes_params$alpha <- 0.02
rt_tp51$layers[[1]]$aes_params$colour <- 'black'

rt_tree52 <- read.tree(text="((((1,2)1-2,(3,4,5,6)3-6,7)1-7,8,((((9,((10,11)10-11,12)10-12)9-12,13)9-13,14,15,(16,17)16-17,18,19)9-19,(20,21)20-21)9-21)1-21,22)1-22;")
rt_tp52 <- ggtree(rt_tree52, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp52$layers[[1]]$aes_params$alpha <- 0.02
rt_tp52$layers[[1]]$aes_params$colour <- 'black'

rt_tree53 <- read.tree(text="(((1,2,(3,(((4,5)4-5,6)4-6,7)4-7)3-7,(8,9,10,(11,12)11-12)8-12)1-12,(13,(14,15,16)14-16)13-16)1-16,((17,((18,19)18-19,20)18-20,21)17-21,22)17-22)1-22;")
rt_tp53 <- ggtree(rt_tree53, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp53$layers[[1]]$aes_params$alpha <- 0.02
rt_tp53$layers[[1]]$aes_params$colour <- 'black'

rt_tree54 <- read.tree(text="((1,((2,3)2-3,(4,(5,6)5-6)4-6)2-6,(7,8,9)7-9)1-9,((10,(((11,12,13)11-13,((14,(15,16)15-16)14-16,17)14-17)11-17,(18,19)18-19)11-19)10-19,(20,21)20-21,22)10-22)1-22;")
rt_tp54 <- ggtree(rt_tree54, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp54$layers[[1]]$aes_params$alpha <- 0.02
rt_tp54$layers[[1]]$aes_params$colour <- 'black'

rt_tree55 <- read.tree(text="(((1,2)1-2,((3,4,(((5,6,7)5-7,8)5-8,((9,(10,11)10-11)9-11,(12,13)12-13,14,15)9-15)5-15)3-15,(((16,17,18)16-18,19)16-19,20)16-20,21)3-21)1-21,22)1-22;")
rt_tp55 <- ggtree(rt_tree55, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp55$layers[[1]]$aes_params$alpha <- 0.02
rt_tp55$layers[[1]]$aes_params$colour <- 'black'

rt_tree56 <- read.tree(text="(((1,2)1-2,(3,(4,((5,((6,(7,(8,9)8-9)7-9,10,((11,12)11-12,13)11-13)6-13,(14,15)14-15,16)6-16)5-16,(17,18,19)17-19)5-19)4-19)3-19)1-19,(20,21)20-21,22)1-22;")
rt_tp56 <- ggtree(rt_tree56, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp56$layers[[1]]$aes_params$alpha <- 0.02
rt_tp56$layers[[1]]$aes_params$colour <- 'black'

rt_tree57 <- read.tree(text="(1,((((((2,3)2-3,4,((5,6)5-6,7)5-7)2-7,8)2-8,((9,10)9-10,11,12)9-12,((13,(14,15)14-15)13-15,16,((17,18)17-18,19)17-19)13-19)2-19,20)2-20,(21,22)21-22)2-22)1-22;")
rt_tp57 <- ggtree(rt_tree57, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp57$layers[[1]]$aes_params$alpha <- 0.02
rt_tp57$layers[[1]]$aes_params$colour <- 'black'

rt_tree58 <- read.tree(text="(((1,(2,3,(4,5,6)4-6)2-6)1-6,7,8)1-8,(9,((10,11,12,(13,14)13-14)10-14,15,(16,(17,18)17-18)16-18,(19,(20,21)20-21)19-21)10-21,22)9-22)1-22;")
rt_tp58 <- ggtree(rt_tree58, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp58$layers[[1]]$aes_params$alpha <- 0.02
rt_tp58$layers[[1]]$aes_params$colour <- 'black'

rt_tree59 <- read.tree(text="(1,(2,(((3,(4,5)4-5)3-5,6)3-6,((((7,8)7-8,(9,(10,(((11,12)11-12,13,14)11-14,15,16)11-16)10-16)9-16)7-16,17,18)7-18,19,((20,21)20-21,22)20-22)7-22)3-22)2-22)1-22;")
rt_tp59 <- ggtree(rt_tree59, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp59$layers[[1]]$aes_params$alpha <- 0.02
rt_tp59$layers[[1]]$aes_params$colour <- 'black'

rt_tree60 <- read.tree(text="(1,2,(3,4)3-4,(5,(6,(7,8)7-8)6-8,9)5-9,((((10,((11,12)11-12,13,14)11-14,15)10-15,(16,17)16-17)10-17,18)10-18,(19,20,(21,22)21-22)19-22)10-22)1-22;")
rt_tp60 <- ggtree(rt_tree60, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp60$layers[[1]]$aes_params$alpha <- 0.02
rt_tp60$layers[[1]]$aes_params$colour <- 'black'

rt_tree61 <- read.tree(text="(1,2,(((3,(4,((5,6)5-6,(7,8)7-8,9)5-9)4-9)3-9,(10,(11,(12,(((13,14)13-14,((15,(16,17)16-17)15-17,18)15-18,19)13-19,20,21)13-21)12-21)11-21)10-21)3-21,22)3-22)1-22;")
rt_tp61 <- ggtree(rt_tree61, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp61$layers[[1]]$aes_params$alpha <- 0.02
rt_tp61$layers[[1]]$aes_params$colour <- 'black'

rt_tree62 <- read.tree(text="(1,((2,3)2-3,4,(((5,6,(((7,8,9,10,11)7-11,12,13)7-13,14,(15,16)15-16,17)7-17)5-17,(18,19)18-19,20)5-20,21,22)5-22)2-22)1-22;")
rt_tp62 <- ggtree(rt_tree62, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp62$layers[[1]]$aes_params$alpha <- 0.02
rt_tp62$layers[[1]]$aes_params$colour <- 'black'

rt_tree63 <- read.tree(text="((1,2)1-2,(((3,(4,(5,6)5-6,7,8)4-8,9,10)3-10,(11,(12,13)12-13)11-13,14,((15,(16,17)16-17)15-17,18)15-18,((19,20)19-20,21)19-21)3-21,22)3-22)1-22;")
rt_tp63 <- ggtree(rt_tree63, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp63$layers[[1]]$aes_params$alpha <- 0.02
rt_tp63$layers[[1]]$aes_params$colour <- 'black'

rt_tree64 <- read.tree(text="(1,(((2,((3,4,5)3-5,(6,7,((8,9)8-9,((10,11)10-11,12)10-12)8-12)6-12)3-12)2-12,13)2-13,14)2-14,((15,((16,(17,18)17-18)16-18,19,20)16-20,21)15-21,22)15-22)1-22;")
rt_tp64 <- ggtree(rt_tree64, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp64$layers[[1]]$aes_params$alpha <- 0.02
rt_tp64$layers[[1]]$aes_params$colour <- 'black'

rt_tree65 <- read.tree(text="((((1,2)1-2,3,4)1-4,5)1-5,(6,((7,(8,((9,((10,11,12,13)10-13,14)10-14)9-14,(15,16,17)15-17)9-17)8-17)7-17,((18,19)18-19,20,21,22)18-22)7-22)6-22)1-22;")
rt_tp65 <- ggtree(rt_tree65, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp65$layers[[1]]$aes_params$alpha <- 0.02
rt_tp65$layers[[1]]$aes_params$colour <- 'black'

rt_tree66 <- read.tree(text="((1,(2,((3,4)3-4,((5,6)5-6,((7,8)7-8,9)7-9,(10,(11,12,13)11-13)10-13)5-13,14)3-14,(15,(16,(17,18,(19,20)19-20)17-20)16-20,21)15-21)2-21)1-21,22)1-22;")
rt_tp66 <- ggtree(rt_tree66, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp66$layers[[1]]$aes_params$alpha <- 0.02
rt_tp66$layers[[1]]$aes_params$colour <- 'black'

rt_tree67 <- read.tree(text="(1,((2,3,(4,((5,6)5-6,(((7,8)7-8,(9,10)9-10,11)7-11,(12,(13,14,15)13-15)12-15)7-15)5-15,(16,17)16-17,(18,19,20)18-20)4-20)2-20,21,22)2-22)1-22;")
rt_tp67 <- ggtree(rt_tree67, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp67$layers[[1]]$aes_params$alpha <- 0.02
rt_tp67$layers[[1]]$aes_params$colour <- 'black'

rt_tree68 <- read.tree(text="(((((1,2,3,4)1-4,5,(6,7,(8,9)8-9)6-9,10,11)1-11,12)1-12,((13,14)13-14,(15,16,(17,18)17-18)15-18)13-18)1-18,((19,20,21)19-21,22)19-22)1-22;")
rt_tp68 <- ggtree(rt_tree68, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp68$layers[[1]]$aes_params$alpha <- 0.02
rt_tp68$layers[[1]]$aes_params$colour <- 'black'

rt_tree69 <- read.tree(text="((1,(2,(((3,((4,(5,6)5-6)4-6,7)4-7)3-7,8)3-8,((9,((10,((11,12)11-12,13,14)11-14)10-14,15,(16,17)16-17,18,19)10-19)9-19,20,21)9-21)3-21)2-21)1-21,22)1-22;")
rt_tp69 <- ggtree(rt_tree69, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp69$layers[[1]]$aes_params$alpha <- 0.02
rt_tp69$layers[[1]]$aes_params$colour <- 'black'

rt_tree70 <- read.tree(text="(((1,(((((2,(3,((((4,(5,6)5-6)4-6,7,8)4-8,(9,10)9-10)4-10,11)4-11)3-11)2-11,12)2-12,13)2-13,14)2-14,15,16)2-16)1-16,(((17,18)17-18,19)17-19,20,21)17-21)1-21,22)1-22;")
rt_tp70 <- ggtree(rt_tree70, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp70$layers[[1]]$aes_params$alpha <- 0.02
rt_tp70$layers[[1]]$aes_params$colour <- 'black'

rt_tree71 <- read.tree(text="((1,2)1-2,(3,(((4,5)4-5,6,7,(8,9,(10,11)10-11)8-11)4-11,(12,(13,(14,(15,(16,((17,18,19)17-19,20)17-20,21,22)16-22)15-22)14-22)13-22)12-22)4-22)3-22)1-22;")
rt_tp71 <- ggtree(rt_tree71, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp71$layers[[1]]$aes_params$alpha <- 0.02
rt_tp71$layers[[1]]$aes_params$colour <- 'black'

rt_tree72 <- read.tree(text="((1,(2,(3,4)3-4,((((5,6)5-6,((7,(8,9)8-9,(10,11)10-11)7-11,(12,13)12-13)7-13,14,15)5-15,16)5-16,17)5-17)2-17,18)1-18,19,(20,21)20-21,22)1-22;")
rt_tp72 <- ggtree(rt_tree72, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp72$layers[[1]]$aes_params$alpha <- 0.02
rt_tp72$layers[[1]]$aes_params$colour <- 'black'

rt_tree73 <- read.tree(text="(1,((2,(3,4,(5,(6,7)6-7)5-7,((8,9)8-9,10,11)8-11)3-11)2-11,((12,13,(((14,15)14-15,(16,((17,18)17-18,19)17-19)16-19)14-19,20)14-20)12-20,21,22)12-22)2-22)1-22;")
rt_tp73 <- ggtree(rt_tree73, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp73$layers[[1]]$aes_params$alpha <- 0.02
rt_tp73$layers[[1]]$aes_params$colour <- 'black'

rt_tree74 <- read.tree(text="((((1,2,(3,4,(5,6)5-6)3-6,((7,8)7-8,((9,(10,11)10-11,(12,13)12-13)9-13,(((14,15)14-15,16)14-16,17)14-17)9-17)7-17)1-17,18,19)1-19,20)1-20,21,22)1-22;")
rt_tp74 <- ggtree(rt_tree74, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp74$layers[[1]]$aes_params$alpha <- 0.02
rt_tp74$layers[[1]]$aes_params$colour <- 'black'

rt_tree75 <- read.tree(text="(1,((2,((3,((((4,5)4-5,6)4-6,7)4-7,((8,(9,10,((11,12)11-12,13,14)11-14)9-14)8-14,(15,16)15-16)8-16)4-16)3-16,17,(18,19)18-19)3-19)2-19,(20,(21,22)21-22)20-22)2-22)1-22;")
rt_tp75 <- ggtree(rt_tree75, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp75$layers[[1]]$aes_params$alpha <- 0.02
rt_tp75$layers[[1]]$aes_params$colour <- 'black'

rt_tree76 <- read.tree(text="((1,2)1-2,((((3,4,5,6)3-6,7,8)3-8,9)3-9,((10,(((11,(12,(13,(14,15,(16,(17,18)17-18)16-18)14-18)13-18)12-18,19)11-19,20)11-20,21)11-21)10-21,22)10-22)3-22)1-22;")
rt_tp76 <- ggtree(rt_tree76, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp76$layers[[1]]$aes_params$alpha <- 0.02
rt_tp76$layers[[1]]$aes_params$colour <- 'black'

rt_tree77 <- read.tree(text="((1,2,(3,((((4,(((5,(6,(7,8)7-8,9)6-9)5-9,10,11)5-11,12)5-12)4-12,13)4-13,14)4-14,15)4-15,(16,17,18,19)16-19)3-19,20)1-20,(21,22)21-22)1-22;")
rt_tp77 <- ggtree(rt_tree77, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp77$layers[[1]]$aes_params$alpha <- 0.02
rt_tp77$layers[[1]]$aes_params$colour <- 'black'

rt_tree78 <- read.tree(text="(1,(2,((3,4)3-4,5,6)3-6)2-6,(7,8)7-8,9,10,((11,12)11-12,(13,14)13-14,15,16,(((17,18)17-18,19,20)17-20,21)17-21)11-21,22)1-22;")
rt_tp78 <- ggtree(rt_tree78, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp78$layers[[1]]$aes_params$alpha <- 0.02
rt_tp78$layers[[1]]$aes_params$colour <- 'black'

rt_tree79 <- read.tree(text="(((1,(2,3)2-3)1-3,4,5)1-5,(6,(7,8,9)7-9)6-9,(10,(11,(((12,(13,14)13-14)12-14,(15,16,(17,18)17-18)15-18)12-18,19,(20,21)20-21,22)12-22)11-22)10-22)1-22;")
rt_tp79 <- ggtree(rt_tree79, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp79$layers[[1]]$aes_params$alpha <- 0.02
rt_tp79$layers[[1]]$aes_params$colour <- 'black'

rt_tree80 <- read.tree(text="((1,2)1-2,3,(4,5)4-5,(6,(7,(8,(9,(10,11)10-11,(12,(13,14)13-14)12-14)9-14)8-14,((15,(16,(17,(18,19)18-19,20)17-20)16-20)15-20,(21,22)21-22)15-22)7-22)6-22)1-22;")
rt_tp80 <- ggtree(rt_tree80, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp80$layers[[1]]$aes_params$alpha <- 0.02
rt_tp80$layers[[1]]$aes_params$colour <- 'black'

rt_tree81 <- read.tree(text="((((((1,2)1-2,3)1-3,4)1-4,(5,6)5-6)1-6,(7,8)7-8,(((9,((((10,(11,12)11-12)10-12,13)10-13,14,15)10-15,16)10-16)9-16,17)9-17,18)9-18,(19,20)19-20,21)1-21,22)1-22;")
rt_tp81 <- ggtree(rt_tree81, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp81$layers[[1]]$aes_params$alpha <- 0.02
rt_tp81$layers[[1]]$aes_params$colour <- 'black'

rt_tree82 <- read.tree(text="(1,(2,3,(((4,5,((((((6,(7,8,(9,10,11)9-11,((12,13)12-13,14)12-14)7-14)6-14,15)6-15,16)6-16,17)6-17,18,19)6-19,20)6-20)4-20,21)4-21,22)4-22)2-22)1-22;")
rt_tp82 <- ggtree(rt_tree82, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp82$layers[[1]]$aes_params$alpha <- 0.02
rt_tp82$layers[[1]]$aes_params$colour <- 'black'

rt_tree83 <- read.tree(text="(1,((((2,3)2-3,4,(((5,((6,(7,(8,(9,(((10,11,12,13)10-13,14)10-14,15,16,17)10-17)9-17)8-17)7-17)6-17,18)6-18)5-18,19)5-19,20)5-20)2-20,21)2-21,22)2-22)1-22;")
rt_tp83 <- ggtree(rt_tree83, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp83$layers[[1]]$aes_params$alpha <- 0.02
rt_tp83$layers[[1]]$aes_params$colour <- 'black'

rt_tree84 <- read.tree(text="((1,(((2,3)2-3,4,5)2-5,6)2-6,7)1-7,(8,9,((((10,11)10-11,12)10-12,(13,(14,(15,16,17)15-17)14-17)13-17,18)10-18,(19,20)19-20)10-20,21,22)8-22)1-22;")
rt_tp84 <- ggtree(rt_tree84, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp84$layers[[1]]$aes_params$alpha <- 0.02
rt_tp84$layers[[1]]$aes_params$colour <- 'black'

rt_tree85 <- read.tree(text="(1,2,((3,((4,5)4-5,(6,7,8,(9,(10,(11,12)11-12,13)10-13)9-13,(14,(15,(16,17)16-17,18)15-18)14-18)6-18)4-18,19,20,21)3-21,22)3-22)1-22;")
rt_tp85 <- ggtree(rt_tree85, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp85$layers[[1]]$aes_params$alpha <- 0.02
rt_tp85$layers[[1]]$aes_params$colour <- 'black'

rt_tree86 <- read.tree(text="(1,((((2,3)2-3,(4,(5,6)5-6)4-6)2-6,7)2-7,(8,(((9,10)9-10,((11,12)11-12,13,(14,15)14-15)11-15)9-15,16,17)9-17)8-17,18)2-18,((19,20)19-20,21)19-21,22)1-22;")
rt_tp86 <- ggtree(rt_tree86, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp86$layers[[1]]$aes_params$alpha <- 0.02
rt_tp86$layers[[1]]$aes_params$colour <- 'black'

rt_tree87 <- read.tree(text="((1,((2,3)2-3,(((((4,5)4-5,6,(((7,8)7-8,9)7-9,10)7-10)4-10,(11,(12,13,14)12-14,15)11-15)4-15,16,17)4-17,18)4-18,19)2-19,20,21)1-21,22)1-22;")
rt_tp87 <- ggtree(rt_tree87, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp87$layers[[1]]$aes_params$alpha <- 0.02
rt_tp87$layers[[1]]$aes_params$colour <- 'black'

rt_tree88 <- read.tree(text="(1,(((2,(3,((4,5)4-5,(6,(7,(8,9,10)8-10)7-10)6-10)4-10,11,(12,13)12-13,((((14,15)14-15,(16,(17,18)17-18)16-18)14-18,19)14-19,20)14-20)3-20)2-20,21)2-21,22)2-22)1-22;")
rt_tp88 <- ggtree(rt_tree88, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp88$layers[[1]]$aes_params$alpha <- 0.02
rt_tp88$layers[[1]]$aes_params$colour <- 'black'

rt_tree89 <- read.tree(text="(((1,2)1-2,3)1-3,((4,5,((6,(7,8,9)7-9)6-9,(((10,11)10-11,12)10-12,13)10-13)6-13,(14,15)14-15)4-15,(16,(17,((18,(19,20)19-20)18-20,21)18-21)17-21,22)16-22)4-22)1-22;")
rt_tp89 <- ggtree(rt_tree89, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp89$layers[[1]]$aes_params$alpha <- 0.02
rt_tp89$layers[[1]]$aes_params$colour <- 'black'

rt_tree90 <- read.tree(text="((1,(((2,3)2-3,(4,(5,6)5-6)4-6,7,(((8,(9,10)9-10)8-10,11)8-11,12,(13,14)13-14)8-14)2-14,(15,16)15-16,(17,18)17-18,(19,20)19-20)2-20)1-20,(21,22)21-22)1-22;")
rt_tp90 <- ggtree(rt_tree90, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp90$layers[[1]]$aes_params$alpha <- 0.02
rt_tp90$layers[[1]]$aes_params$colour <- 'black'

rt_tree91 <- read.tree(text="((((1,(2,3,((4,(5,6)5-6)4-6,(((7,8)7-8,(9,10)9-10)7-10,11)7-11)4-11)2-11,12)1-12,13)1-13,((14,(15,16,17)15-17)14-17,(18,19)18-19)14-19)1-19,20,21,22)1-22;")
rt_tp91 <- ggtree(rt_tree91, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp91$layers[[1]]$aes_params$alpha <- 0.02
rt_tp91$layers[[1]]$aes_params$colour <- 'black'

rt_tree92 <- read.tree(text="((((1,2)1-2,3)1-3,(((4,5,6)4-6,7)4-7,8,(9,10)9-10,((11,12)11-12,((13,14)13-14,(15,(16,17)16-17,(18,(19,(20,21)20-21)19-21)18-21)15-21)13-21)11-21)4-21)1-21,22)1-22;")
rt_tp92 <- ggtree(rt_tree92, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp92$layers[[1]]$aes_params$alpha <- 0.02
rt_tp92$layers[[1]]$aes_params$colour <- 'black'

rt_tree93 <- read.tree(text="((1,2)1-2,(3,((4,((5,(6,7,8,9)6-9)5-9,10,(11,12,13)11-13)5-13)4-13,14)4-14,(((15,16)15-16,17)15-17,18)15-18,(19,20)19-20)3-20,21,22)1-22;")
rt_tp93 <- ggtree(rt_tree93, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp93$layers[[1]]$aes_params$alpha <- 0.02
rt_tp93$layers[[1]]$aes_params$colour <- 'black'

rt_tree94 <- read.tree(text="(1,((2,((3,(4,(5,6)5-6)4-6)3-6,(7,8,9)7-9)3-9,10,11)2-11,((12,13)12-13,(14,((15,(16,(17,(18,19)18-19)17-19)16-19)15-19,20,21,22)15-22)14-22)12-22)2-22)1-22;")
rt_tp94 <- ggtree(rt_tree94, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp94$layers[[1]]$aes_params$alpha <- 0.02
rt_tp94$layers[[1]]$aes_params$colour <- 'black'

rt_tree95 <- read.tree(text="(1,(2,(3,4,(5,(6,7,((((8,9,((10,11,12,13)10-13,14,15)10-15)8-15,16,17,18,19)8-19,20)8-20,21)8-21)6-21)5-21,22)3-22)2-22)1-22;")
rt_tp95 <- ggtree(rt_tree95, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp95$layers[[1]]$aes_params$alpha <- 0.02
rt_tp95$layers[[1]]$aes_params$colour <- 'black'

rt_tree96 <- read.tree(text="(1,(2,((3,((4,5)4-5,6,(7,((8,((9,10)9-10,11)9-11,12)8-12,13)8-13,14)7-14)4-14,(15,16,17)15-17)3-17,((18,19,20)18-20,21,22)18-22)3-22)2-22)1-22;")
rt_tp96 <- ggtree(rt_tree96, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp96$layers[[1]]$aes_params$alpha <- 0.02
rt_tp96$layers[[1]]$aes_params$colour <- 'black'

rt_tree97 <- read.tree(text="(((1,(2,(3,(4,((5,6)5-6,(7,8)7-8)5-8)4-8,(((9,10)9-10,11)9-11,((12,13)12-13,14)12-14,(15,16)15-16)9-16,17,(18,19)18-19)3-19,20)2-20)1-20,21)1-21,22)1-22;")
rt_tp97 <- ggtree(rt_tree97, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp97$layers[[1]]$aes_params$alpha <- 0.02
rt_tp97$layers[[1]]$aes_params$colour <- 'black'

rt_tree98 <- read.tree(text="((1,(2,3,4)2-4,(((5,6)5-6,7,((8,((9,10)9-10,(11,12)11-12)9-12,13)8-13,14,((15,16)15-16,17)15-17)8-17,18)5-18,(19,20)19-20)5-20,21)1-21,22)1-22;")
rt_tp98 <- ggtree(rt_tree98, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp98$layers[[1]]$aes_params$alpha <- 0.02
rt_tp98$layers[[1]]$aes_params$colour <- 'black'

rt_tree99 <- read.tree(text="(1,(2,(((3,((4,5,6,((7,(8,(9,10,11)9-11)8-11)7-11,(12,13)12-13)7-13)4-13,((14,15)14-15,16)14-16)4-16)3-16,17)3-17,18)3-18,19,(20,21)20-21,22)2-22)1-22;")
rt_tp99 <- ggtree(rt_tree99, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp99$layers[[1]]$aes_params$alpha <- 0.02
rt_tp99$layers[[1]]$aes_params$colour <- 'black'

rt_tree100 <- read.tree(text="(((1,(2,(3,4)3-4)2-4)1-4,((((5,6)5-6,((7,((8,9)8-9,10)8-10)7-10,11)7-11)5-11,12)5-12,((13,14)13-14,15)13-15,(16,(17,18,19)17-19)16-19)5-19,(20,21)20-21)1-21,22)1-22;")
rt_tp100 <- ggtree(rt_tree100, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp100$layers[[1]]$aes_params$alpha <- 0.02
rt_tp100$layers[[1]]$aes_params$colour <- 'black'

rt_tree101 <- read.tree(text="((1,2,((3,(4,5)4-5)3-5,(6,(((7,8,9)7-9,10,(11,12,13,14)11-14)7-14,15)7-15)6-15)3-15,16,(17,18)17-18)1-18,19,((20,21)20-21,22)20-22)1-22;")
rt_tp101 <- ggtree(rt_tree101, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp101$layers[[1]]$aes_params$alpha <- 0.02
rt_tp101$layers[[1]]$aes_params$colour <- 'black'

rt_tree102 <- read.tree(text="(1,((2,(((3,4)3-4,((5,6,7)5-7,(((((8,9)8-9,10)8-10,11)8-11,12)8-12,13)8-13)5-13,(14,(15,16)15-16)14-16,(17,18,19)17-19)3-19,20)3-20)2-20,(21,22)21-22)2-22)1-22;")
rt_tp102 <- ggtree(rt_tree102, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp102$layers[[1]]$aes_params$alpha <- 0.02
rt_tp102$layers[[1]]$aes_params$colour <- 'black'

rt_tree103 <- read.tree(text="((1,2,(3,(((4,(5,6)5-6)4-6,7,8)4-8,9,10,(11,(12,13)12-13)11-13)4-13)3-13,14,(15,16)15-16,(17,18)17-18)1-18,((19,(20,21)20-21)19-21,22)19-22)1-22;")
rt_tp103 <- ggtree(rt_tree103, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp103$layers[[1]]$aes_params$alpha <- 0.02
rt_tp103$layers[[1]]$aes_params$colour <- 'black'

rt_tree104 <- read.tree(text="((((1,((2,(3,((4,(5,6,7)5-7)4-7,8)4-8)3-8)2-8,9)2-9)1-9,(10,(11,12,13)11-13)10-13)1-13,14)1-14,((15,16,(((17,18)17-18,19)17-19,(20,21)20-21)17-21)15-21,22)15-22)1-22;")
rt_tp104 <- ggtree(rt_tree104, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp104$layers[[1]]$aes_params$alpha <- 0.02
rt_tp104$layers[[1]]$aes_params$colour <- 'black'

rt_tree105 <- read.tree(text="(1,2,(((3,4,5)3-5,(6,7,(8,9)8-9)6-9)3-9,((((10,(11,12)11-12)10-12,13,14)10-14,(15,((16,17)16-17,18,19)16-19,20)15-20)10-20,(21,22)21-22)10-22)3-22)1-22;")
rt_tp105 <- ggtree(rt_tree105, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp105$layers[[1]]$aes_params$alpha <- 0.02
rt_tp105$layers[[1]]$aes_params$colour <- 'black'

rt_tree106 <- read.tree(text="(((((1,(((2,3)2-3,(4,5)4-5)2-5,((6,7)6-7,8)6-8,(9,10,11)9-11)2-11)1-11,(12,13,14)12-14)1-14,(15,16)15-16)1-16,17)1-17,((18,19)18-19,20,21)18-21,22)1-22;")
rt_tp106 <- ggtree(rt_tree106, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp106$layers[[1]]$aes_params$alpha <- 0.02
rt_tp106$layers[[1]]$aes_params$colour <- 'black'

rt_tree107 <- read.tree(text="(1,2,(3,((4,((5,((6,7,8)6-8,9,10,11,(12,13)12-13)6-13)5-13,14,((15,(16,17)16-17,18,19)15-19,20)15-20)5-20,21)4-21,22)4-22)3-22)1-22;")
rt_tp107 <- ggtree(rt_tree107, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp107$layers[[1]]$aes_params$alpha <- 0.02
rt_tp107$layers[[1]]$aes_params$colour <- 'black'

rt_tree108 <- read.tree(text="((1,(2,3,4,(5,(6,7)6-7)5-7)2-7)1-7,(((8,9)8-9,(10,11,12)10-12)8-12,(13,((14,15)14-15,((((16,17)16-17,18,19)16-19,20)16-20,21)16-21)14-21,22)13-22)8-22)1-22;")
rt_tp108 <- ggtree(rt_tree108, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp108$layers[[1]]$aes_params$alpha <- 0.02
rt_tp108$layers[[1]]$aes_params$colour <- 'black'

rt_tree109 <- read.tree(text="(((1,2,3,4)1-4,(5,(6,7)6-7,((8,9)8-9,((10,11)10-11,(12,13)12-13)10-13,14,(15,16)15-16)8-16,17)5-17,(18,19)18-19)1-19,(20,(21,22)21-22)20-22)1-22;")
rt_tp109 <- ggtree(rt_tree109, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp109$layers[[1]]$aes_params$alpha <- 0.02
rt_tp109$layers[[1]]$aes_params$colour <- 'black'

rt_tree110 <- read.tree(text="(((1,2,3)1-3,(4,5,((6,7,8)6-8,(9,10)9-10)6-10,11,12)4-12)1-12,(13,14,(15,(16,(17,(18,19)18-19,(20,21,22)20-22)17-22)16-22)15-22)13-22)1-22;")
rt_tp110 <- ggtree(rt_tree110, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp110$layers[[1]]$aes_params$alpha <- 0.02
rt_tp110$layers[[1]]$aes_params$colour <- 'black'

rt_tree111 <- read.tree(text="((1,2,(((3,((((4,(5,6)5-6)4-6,7)4-7,8)4-8,(9,(10,11,12)10-12,13)9-13)4-13)3-13,14)3-14,15)3-15,16)1-16,((17,18)17-18,(19,20,21)19-21)17-21,22)1-22;")
rt_tp111 <- ggtree(rt_tree111, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp111$layers[[1]]$aes_params$alpha <- 0.02
rt_tp111$layers[[1]]$aes_params$colour <- 'black'

rt_tree112 <- read.tree(text="((((((1,2,(3,4)3-4)1-4,(5,((((6,7)6-7,8,9)6-9,10)6-10,11,12)6-12)5-12)1-12,(13,((14,15,16)14-16,17)14-17)13-17,18)1-18,19,20)1-20,21)1-21,22)1-22;")
rt_tp112 <- ggtree(rt_tree112, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp112$layers[[1]]$aes_params$alpha <- 0.02
rt_tp112$layers[[1]]$aes_params$colour <- 'black'

rt_tree113 <- read.tree(text="(1,((2,3)2-3,(((4,5)4-5,((6,(7,8)7-8,(9,10)9-10)6-10,((11,12)11-12,13,(14,((15,16)15-16,17)15-17)14-17,18)11-18)6-18,19,20)4-20,(21,22)21-22)4-22)2-22)1-22;")
rt_tp113 <- ggtree(rt_tree113, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp113$layers[[1]]$aes_params$alpha <- 0.02
rt_tp113$layers[[1]]$aes_params$colour <- 'black'

rt_tree114 <- read.tree(text="(1,2,3,(((((4,5)4-5,6)4-6,(7,8,((9,10,11)9-11,12)9-12)7-12)4-12,(13,14)13-14,15,16,17,(18,19)18-19)4-19,20)4-20,(21,22)21-22)1-22;")
rt_tp114 <- ggtree(rt_tree114, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp114$layers[[1]]$aes_params$alpha <- 0.02
rt_tp114$layers[[1]]$aes_params$colour <- 'black'

rt_tree115 <- read.tree(text="(1,2,(((3,(4,(5,(6,7,8)6-8)5-8)4-8)3-8,9)3-9,10)3-10,(((((11,12)11-12,13)11-13,14)11-14,15)11-15,16)11-16,((17,(18,19,20)18-20,21)17-21,22)17-22)1-22;")
rt_tp115 <- ggtree(rt_tree115, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp115$layers[[1]]$aes_params$alpha <- 0.02
rt_tp115$layers[[1]]$aes_params$colour <- 'black'

rt_tree116 <- read.tree(text="(((1,(((2,(3,4)3-4)2-4,((5,(6,7,8)6-8)5-8,9)5-9)2-9,10)2-10,(((11,12)11-12,(13,14,15)13-15)11-15,16)11-16)1-16,17,18,((19,20)19-20,21)19-21)1-21,22)1-22;")
rt_tp116 <- ggtree(rt_tree116, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp116$layers[[1]]$aes_params$alpha <- 0.02
rt_tp116$layers[[1]]$aes_params$colour <- 'black'

rt_tree117 <- read.tree(text="(1,((((2,3)2-3,4)2-4,((5,(6,7)6-7,(8,(9,(10,11)10-11,12)9-12)8-12)5-12,13)5-13)2-13,((14,15,(16,(17,18)17-18)16-18)14-18,19,20)14-20,21)2-21,22)1-22;")
rt_tp117 <- ggtree(rt_tree117, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp117$layers[[1]]$aes_params$alpha <- 0.02
rt_tp117$layers[[1]]$aes_params$colour <- 'black'

rt_tree118 <- read.tree(text="((1,(2,(3,4)3-4)2-4)1-4,5,(6,7,(8,(9,10,11)9-11,12)8-12,(13,((((14,15)14-15,(16,17)16-17,18,19)14-19,20)14-20,21)14-21,22)13-22)6-22)1-22;")
rt_tp118 <- ggtree(rt_tree118, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp118$layers[[1]]$aes_params$alpha <- 0.02
rt_tp118$layers[[1]]$aes_params$colour <- 'black'

rt_tree119 <- read.tree(text="(((1,2)1-2,((3,4,5,((6,((7,(8,9)8-9)7-9,(10,11)10-11,12)7-12)6-12,13)6-13)3-13,14)3-14)1-14,15,16,(17,((18,19)18-19,20,21,22)18-22)17-22)1-22;")
rt_tp119 <- ggtree(rt_tree119, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp119$layers[[1]]$aes_params$alpha <- 0.02
rt_tp119$layers[[1]]$aes_params$colour <- 'black'

rt_tree120 <- read.tree(text="(1,((2,3,4)2-4,(5,6)5-6,7)2-7,8,9,((((10,11,12,13,(14,15)14-15)10-15,16,17)10-17,18)10-18,19,20,(21,22)21-22)10-22)1-22;")
rt_tp120 <- ggtree(rt_tree120, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp120$layers[[1]]$aes_params$alpha <- 0.02
rt_tp120$layers[[1]]$aes_params$colour <- 'black'

rt_tree121 <- read.tree(text="(1,((2,(3,((4,5)4-5,6)4-6)3-6)2-6,(7,(8,9)8-9,10)7-10)2-10,((((11,12)11-12,13,14)11-14,((15,16)15-16,17)15-17)11-17,(18,19)18-19,(20,21,22)20-22)11-22)1-22;")
rt_tp121 <- ggtree(rt_tree121, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp121$layers[[1]]$aes_params$alpha <- 0.02
rt_tp121$layers[[1]]$aes_params$colour <- 'black'

rt_tree122 <- read.tree(text="((((1,2,3)1-3,(4,5,6)4-6,((7,8)7-8,(9,(10,11,12)10-12,(((13,(14,15)14-15)13-15,(16,17)16-17)13-17,18)13-18)9-18,(19,20)19-20)7-20)1-20,21)1-21,22)1-22;")
rt_tp122 <- ggtree(rt_tree122, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp122$layers[[1]]$aes_params$alpha <- 0.02
rt_tp122$layers[[1]]$aes_params$colour <- 'black'

rt_tree123 <- read.tree(text="(1,(2,3,(((4,5)4-5,6,7)4-7,8,9)4-9,((10,11)10-11,((12,(13,(14,(((15,(16,(17,18)17-18)16-18)15-18,19)15-19,20)15-20)14-20,21)13-21)12-21,22)12-22)10-22)2-22)1-22;")
rt_tp123 <- ggtree(rt_tree123, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp123$layers[[1]]$aes_params$alpha <- 0.02
rt_tp123$layers[[1]]$aes_params$colour <- 'black'

rt_tree124 <- read.tree(text="((((1,2)1-2,3)1-3,4,((5,(6,((7,8)7-8,9)7-9)6-9)5-9,(10,(11,(12,13)12-13)11-13,(14,(15,16,17)15-17)14-17)10-17,18,((19,20)19-20,21)19-21)5-21)1-21,22)1-22;")
rt_tp124 <- ggtree(rt_tree124, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp124$layers[[1]]$aes_params$alpha <- 0.02
rt_tp124$layers[[1]]$aes_params$colour <- 'black'

rt_tree125 <- read.tree(text="(((1,((2,3)2-3,4)2-4,(5,(6,7,((8,9)8-9,(10,11,(12,13)12-13,(14,15)14-15)10-15)8-15)6-15)5-15,16)1-16,17,18)1-18,19,(20,21)20-21,22)1-22;")
rt_tp125 <- ggtree(rt_tree125, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp125$layers[[1]]$aes_params$alpha <- 0.02
rt_tp125$layers[[1]]$aes_params$colour <- 'black'

rt_tree126 <- read.tree(text="(1,2,((3,(((4,(5,(6,7)6-7)5-7)4-7,(8,(9,(10,(11,(12,(13,14)13-14)12-14,15)11-15)10-15)9-15)8-15)4-15,(16,(17,18,19)17-19,20)16-20)4-20)3-20,21,22)3-22)1-22;")
rt_tp126 <- ggtree(rt_tree126, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp126$layers[[1]]$aes_params$alpha <- 0.02
rt_tp126$layers[[1]]$aes_params$colour <- 'black'

rt_tree127 <- read.tree(text="(1,(2,(((3,4)3-4,(5,6,7,(((8,((9,10)9-10,11,(12,13)12-13)9-13)8-13,14)8-14,15)8-15,(16,((17,18)17-18,19,20)17-20,21)16-21)5-21)3-21,22)3-22)2-22)1-22;")
rt_tp127 <- ggtree(rt_tree127, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp127$layers[[1]]$aes_params$alpha <- 0.02
rt_tp127$layers[[1]]$aes_params$colour <- 'black'

rt_tree128 <- read.tree(text="(((1,2,3)1-3,(4,((5,6)5-6,(7,((8,(9,((10,11)10-11,(12,13)12-13)10-13,14)9-14)8-14,15)8-15)7-15)5-15)4-15,(16,((17,(18,19)18-19)17-19,20,21)17-21)16-21)1-21,22)1-22;")
rt_tp128 <- ggtree(rt_tree128, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp128$layers[[1]]$aes_params$alpha <- 0.02
rt_tp128$layers[[1]]$aes_params$colour <- 'black'

rt_tree129 <- read.tree(text="(1,((2,(3,((((4,5)4-5,6)4-6,7)4-7,8)4-8,9)3-9)2-9,(10,((11,12,(13,14)13-14)11-14,(((15,16)15-16,17)15-17,18)15-18,19)11-19)10-19)2-19,(20,21)20-21,22)1-22;")
rt_tp129 <- ggtree(rt_tree129, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp129$layers[[1]]$aes_params$alpha <- 0.02
rt_tp129$layers[[1]]$aes_params$colour <- 'black'

rt_tree130 <- read.tree(text="(1,(2,3,((4,5)4-5,(6,(7,8,9,(10,(11,12)11-12,13)10-13)7-13,14,15,((16,17)16-17,((18,19,20)18-20,21,22)18-22)16-22)6-22)4-22)2-22)1-22;")
rt_tp130 <- ggtree(rt_tree130, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp130$layers[[1]]$aes_params$alpha <- 0.02
rt_tp130$layers[[1]]$aes_params$colour <- 'black'

rt_tree131 <- read.tree(text="(1,((2,3)2-3,(4,((((5,6,7,8)5-8,9)5-9,((10,11)10-11,12)10-12,13)5-13,14)5-14,((15,(16,(17,18,(19,20)19-20)17-20,21)16-21)15-21,22)15-22)4-22)2-22)1-22;")
rt_tp131 <- ggtree(rt_tree131, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp131$layers[[1]]$aes_params$alpha <- 0.02
rt_tp131$layers[[1]]$aes_params$colour <- 'black'

rt_tree132 <- read.tree(text="((1,(2,((3,4,((5,6,7)5-7,8)5-8,(9,((10,11)10-11,(12,13)12-13)10-13)9-13,14)3-14,(15,(16,17)16-17,18,19)15-19)3-19)2-19)1-19,(20,21)20-21,22)1-22;")
rt_tp132 <- ggtree(rt_tree132, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp132$layers[[1]]$aes_params$alpha <- 0.02
rt_tp132$layers[[1]]$aes_params$colour <- 'black'

rt_tree133 <- read.tree(text="((1,(2,(3,4)3-4,5)2-5,6)1-6,((((((7,(8,9,(10,11,12)10-12)8-12)7-12,13)7-13,14)7-14,15)7-15,16,17,18,((19,20)19-20,21)19-21)7-21,22)7-22)1-22;")
rt_tp133 <- ggtree(rt_tree133, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp133$layers[[1]]$aes_params$alpha <- 0.02
rt_tp133$layers[[1]]$aes_params$colour <- 'black'

rt_tree134 <- read.tree(text="((((1,(2,3,(4,5)4-5)2-5)1-5,6)1-6,7)1-7,(((8,9,10)8-10,11)8-11,((12,(13,14)13-14,15)12-15,16)12-16)8-16,(17,18)17-18,19,(20,21,22)20-22)1-22;")
rt_tp134 <- ggtree(rt_tree134, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp134$layers[[1]]$aes_params$alpha <- 0.02
rt_tp134$layers[[1]]$aes_params$colour <- 'black'

rt_tree135 <- read.tree(text="(1,((2,3)2-3,4)2-4,(((5,((6,7)6-7,8,(9,10,11)9-11)6-11)5-11,((12,13)12-13,14)12-14)5-14,(((15,16)15-16,(17,18)17-18,(19,20,21)19-21)15-21,22)15-22)5-22)1-22;")
rt_tp135 <- ggtree(rt_tree135, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp135$layers[[1]]$aes_params$alpha <- 0.02
rt_tp135$layers[[1]]$aes_params$colour <- 'black'

rt_tree136 <- read.tree(text="((((1,2)1-2,3)1-3,(4,((5,6)5-6,((7,8)7-8,9,10,11)7-11)5-11)4-11)1-11,((12,13)12-13,14,(15,((16,17)16-17,(((18,19)18-19,20,21)18-21,22)18-22)16-22)15-22)12-22)1-22;")
rt_tp136 <- ggtree(rt_tree136, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp136$layers[[1]]$aes_params$alpha <- 0.02
rt_tp136$layers[[1]]$aes_params$colour <- 'black'

rt_tree137 <- read.tree(text="((1,(2,((((3,4,(5,(6,((7,8)7-8,(9,10)9-10,11)7-11)6-11)5-11,12)3-12,13,(14,15)14-15)3-15,16,17)3-17,18)3-18)2-18,19)1-19,(20,21,22)20-22)1-22;")
rt_tp137 <- ggtree(rt_tree137, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp137$layers[[1]]$aes_params$alpha <- 0.02
rt_tp137$layers[[1]]$aes_params$colour <- 'black'

rt_tree138 <- read.tree(text="((1,(((2,(3,(4,5)4-5)3-5)2-5,6,(7,((8,9)8-9,10,11,12)8-12)7-12)2-12,13)2-13,14)1-14,((15,(16,(17,(18,(19,20)19-20)18-20)17-20,21)16-21)15-21,22)15-22)1-22;")
rt_tp138 <- ggtree(rt_tree138, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp138$layers[[1]]$aes_params$alpha <- 0.02
rt_tp138$layers[[1]]$aes_params$colour <- 'black'

rt_tree139 <- read.tree(text="(((1,(2,(3,4)3-4,5)2-5,(6,7)6-7,8,9)1-9,10)1-10,((11,(((12,13)12-13,14)12-14,(15,16)15-16)12-16)11-16,(17,(18,19)18-19)17-19,(20,(21,22)21-22)20-22)11-22)1-22;")
rt_tp139 <- ggtree(rt_tree139, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp139$layers[[1]]$aes_params$alpha <- 0.02
rt_tp139$layers[[1]]$aes_params$colour <- 'black'

rt_tree140 <- read.tree(text="((((1,2,(3,(((4,(5,6)5-6,7)4-7,8)4-8,9)4-9)3-9)1-9,10)1-10,11,(12,13)12-13)1-13,(14,((15,16,17,18)15-18,(((19,20)19-20,21)19-21,22)19-22)15-22)14-22)1-22;")
rt_tp140 <- ggtree(rt_tree140, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp140$layers[[1]]$aes_params$alpha <- 0.02
rt_tp140$layers[[1]]$aes_params$colour <- 'black'

rt_tree141 <- read.tree(text="((1,(2,((3,(4,(5,6)5-6)4-6)3-6,7)3-7)2-7)1-7,(8,(9,10,((((11,(12,13)12-13)11-13,(14,15,16)14-16)11-16,17)11-17,18,((19,20)19-20,21)19-21,22)11-22)9-22)8-22)1-22;")
rt_tp141 <- ggtree(rt_tree141, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp141$layers[[1]]$aes_params$alpha <- 0.02
rt_tp141$layers[[1]]$aes_params$colour <- 'black'

rt_tree142 <- read.tree(text="((((1,2,3)1-3,(4,5)4-5,((6,((((7,(8,(9,10,(11,12)11-12)9-12)8-12)7-12,13,14,15)7-15,16)7-16,17)7-17)6-17,18,19)6-19)1-19,20)1-20,(21,22)21-22)1-22;")
rt_tp142 <- ggtree(rt_tree142, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp142$layers[[1]]$aes_params$alpha <- 0.02
rt_tp142$layers[[1]]$aes_params$colour <- 'black'

rt_tree143 <- read.tree(text="(1,((2,3)2-3,(4,(5,6,7)5-7)4-7,(8,(9,10,11,12)9-12)8-12,(13,14)13-14,15)2-15,(16,17,(18,(19,(20,21)20-21)19-21)18-21,22)16-22)1-22;")
rt_tp143 <- ggtree(rt_tree143, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp143$layers[[1]]$aes_params$alpha <- 0.02
rt_tp143$layers[[1]]$aes_params$colour <- 'black'

rt_tree144 <- read.tree(text="(((((((1,2)1-2,3)1-3,4)1-4,((5,6)5-6,(7,8,(9,(10,11)10-11)9-11)7-11,12)5-12,13)1-13,(14,15,(16,17)16-17,18)14-18)1-18,(19,20,21)19-21)1-21,22)1-22;")
rt_tp144 <- ggtree(rt_tree144, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp144$layers[[1]]$aes_params$alpha <- 0.02
rt_tp144$layers[[1]]$aes_params$colour <- 'black'

rt_tree145 <- read.tree(text="((1,(((2,(3,(4,5)4-5)3-5,6)2-6,(((7,(8,9,(10,11)10-11)8-11)7-11,12)7-12,((13,14)13-14,(15,(16,17)16-17)15-17)13-17,18)7-18)2-18,(19,20)19-20)2-20)1-20,(21,22)21-22)1-22;")
rt_tp145 <- ggtree(rt_tree145, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp145$layers[[1]]$aes_params$alpha <- 0.02
rt_tp145$layers[[1]]$aes_params$colour <- 'black'

rt_tree146 <- read.tree(text="((((1,2,3,(4,(5,(6,((7,(8,(9,10,11,12)9-12)8-12)7-12,13)7-13)6-13)5-13)4-13)1-13,14,(15,(16,17)16-17)15-17,(18,(19,20)19-20)18-20)1-20,21)1-21,22)1-22;")
rt_tp146 <- ggtree(rt_tree146, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp146$layers[[1]]$aes_params$alpha <- 0.02
rt_tp146$layers[[1]]$aes_params$colour <- 'black'

rt_tree147 <- read.tree(text="(1,((2,3)2-3,(4,(((5,((6,7,8,(9,(10,11)10-11,12)9-12)6-12,(13,14)13-14,15)6-15)5-15,16)5-16,17)5-17,(18,19)18-19)4-19,20)2-20,21,22)1-22;")
rt_tp147 <- ggtree(rt_tree147, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp147$layers[[1]]$aes_params$alpha <- 0.02
rt_tp147$layers[[1]]$aes_params$colour <- 'black'

rt_tree148 <- read.tree(text="(((1,(2,(3,((4,5)4-5,((6,7)6-7,8)6-8,9)4-9)3-9)2-9)1-9,10)1-10,(11,(12,(((13,((14,15,16)14-16,17)14-17)13-17,18)13-18,(19,20)19-20)13-20,21)12-21)11-21,22)1-22;")
rt_tp148 <- ggtree(rt_tree148, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp148$layers[[1]]$aes_params$alpha <- 0.02
rt_tp148$layers[[1]]$aes_params$colour <- 'black'

rt_tree149 <- read.tree(text="((1,2,((((3,(4,5,6)4-6,7)3-7,(8,9,((10,11,12,(13,14)13-14)10-14,15)10-15)8-15)3-15,(16,17,18)16-18)3-18,19,20)3-20)1-20,21,22)1-22;")
rt_tp149 <- ggtree(rt_tree149, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp149$layers[[1]]$aes_params$alpha <- 0.02
rt_tp149$layers[[1]]$aes_params$colour <- 'black'

rt_tree150 <- read.tree(text="((1,2,3,(4,(((5,((6,(7,((8,9,10)8-10,11,12)8-12)7-12)6-12,(13,(14,15)14-15,16)13-16)6-16,17)5-17,18,19)5-19,20)5-20,21)4-21)1-21,22)1-22;")
rt_tp150 <- ggtree(rt_tree150, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp150$layers[[1]]$aes_params$alpha <- 0.02
rt_tp150$layers[[1]]$aes_params$colour <- 'black'

rt_tree151 <- read.tree(text="((1,((((2,3)2-3,(4,5,(6,7)6-7)4-7,((8,9)8-9,10)8-10)2-10,11)2-11,12,(((13,14)13-14,15)13-15,16,17)13-17)2-17)1-17,(18,19)18-19,20,(21,22)21-22)1-22;")
rt_tp151 <- ggtree(rt_tree151, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp151$layers[[1]]$aes_params$alpha <- 0.02
rt_tp151$layers[[1]]$aes_params$colour <- 'black'

rt_tree152 <- read.tree(text="((((1,(2,((((3,4)3-4,5)3-5,((6,(7,8)7-8)6-8,9)6-9,10)3-10,11)3-11)2-11)1-11,12,13,14)1-14,(15,16,(17,18,19)17-19)15-19,(20,21)20-21)1-21,22)1-22;")
rt_tp152 <- ggtree(rt_tree152, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp152$layers[[1]]$aes_params$alpha <- 0.02
rt_tp152$layers[[1]]$aes_params$colour <- 'black'

rt_tree153 <- read.tree(text="(1,(2,(((3,4,(5,((6,(((7,(((8,9)8-9,10,11)8-11,12)8-12)7-12,((13,14)13-14,15)13-15)7-15,16)7-16)6-16,17)6-17,18)5-18)3-18,(19,(20,21)20-21)19-21)3-21,22)3-22)2-22)1-22;")
rt_tp153 <- ggtree(rt_tree153, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp153$layers[[1]]$aes_params$alpha <- 0.02
rt_tp153$layers[[1]]$aes_params$colour <- 'black'

rt_tree154 <- read.tree(text="(1,((2,(((3,4,(5,(((6,7,8)6-8,(9,10)9-10)6-10,11)6-11)5-11,(12,13)12-13)3-13,(14,((15,(16,17)16-17)15-17,18)15-18)14-18)3-18,19,20)3-20,21)2-21,22)2-22)1-22;")
rt_tp154 <- ggtree(rt_tree154, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp154$layers[[1]]$aes_params$alpha <- 0.02
rt_tp154$layers[[1]]$aes_params$colour <- 'black'

rt_tree155 <- read.tree(text="(((1,2)1-2,3)1-3,(4,5,(((6,7)6-7,8)6-8,9,10,((11,12,((13,14,15)13-15,16)13-16)11-16,17)11-17,(((18,19)18-19,20)18-20,21)18-21,22)6-22)4-22)1-22;")
rt_tp155 <- ggtree(rt_tree155, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp155$layers[[1]]$aes_params$alpha <- 0.02
rt_tp155$layers[[1]]$aes_params$colour <- 'black'

rt_tree156 <- read.tree(text="(((((1,2,3,((4,5)4-5,(6,7)6-7)4-7,8)1-8,((9,(10,11,12,(13,14)13-14)10-14,15)9-15,(16,17)16-17)9-17)1-17,(18,19)18-19)1-19,(20,21)20-21)1-21,22)1-22;")
rt_tp156 <- ggtree(rt_tree156, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp156$layers[[1]]$aes_params$alpha <- 0.02
rt_tp156$layers[[1]]$aes_params$colour <- 'black'

rt_tree157 <- read.tree(text="(((1,(2,3)2-3)1-3,4)1-4,5,(6,(((7,(8,9,10)8-10)7-10,(((11,12,(13,14)13-14)11-14,15)11-15,16,17)11-17)7-17,(18,19)18-19)7-19,((20,21)20-21,22)20-22)6-22)1-22;")
rt_tp157 <- ggtree(rt_tree157, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp157$layers[[1]]$aes_params$alpha <- 0.02
rt_tp157$layers[[1]]$aes_params$colour <- 'black'

rt_tree158 <- read.tree(text="(1,(((2,3,(4,(5,6,((7,8,9)7-9,10)7-10)5-10)4-10)2-10,(11,((12,13)12-13,(((14,15)14-15,16)14-16,17,18,19)14-19)12-19)11-19)2-19,(20,21)20-21,22)2-22)1-22;")
rt_tp158 <- ggtree(rt_tree158, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp158$layers[[1]]$aes_params$alpha <- 0.02
rt_tp158$layers[[1]]$aes_params$colour <- 'black'

rt_tree159 <- read.tree(text="(((((1,(2,3)2-3)1-3,(4,(5,6)5-6)4-6)1-6,(7,8)7-8,9,10)1-10,(11,12)11-12)1-12,13,(14,(15,((16,(17,(18,19)18-19)17-19)16-19,20,21)16-21,22)15-22)14-22)1-22;")
rt_tp159 <- ggtree(rt_tree159, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp159$layers[[1]]$aes_params$alpha <- 0.02
rt_tp159$layers[[1]]$aes_params$colour <- 'black'

rt_tree160 <- read.tree(text="(((1,((2,(3,(4,5)4-5)3-5,6)2-6,(7,8)7-8,9)2-9,(10,(((11,(12,13)12-13)11-13,14)11-14,15,(16,17)16-17)11-17,18)10-18)1-18,19)1-19,((20,21)20-21,22)20-22)1-22;")
rt_tp160 <- ggtree(rt_tree160, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp160$layers[[1]]$aes_params$alpha <- 0.02
rt_tp160$layers[[1]]$aes_params$colour <- 'black'

rt_tree161 <- read.tree(text="((1,((2,3,(4,(5,(6,7,((8,9)8-9,10)8-10,11)6-11)5-11)4-11)2-11,(12,13)12-13,(14,15,(16,17)16-17,18)14-18)2-18,((19,20)19-20,21)19-21)1-21,22)1-22;")
rt_tp161 <- ggtree(rt_tree161, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp161$layers[[1]]$aes_params$alpha <- 0.02
rt_tp161$layers[[1]]$aes_params$colour <- 'black'

rt_tree162 <- read.tree(text="((((1,((2,(3,4)3-4)2-4,5,((6,(7,8)7-8)6-8,9,10)6-10,(11,(12,(13,14,(15,16)15-16)13-16)12-16,(17,18)17-18)11-18)2-18)1-18,19)1-19,20,21)1-21,22)1-22;")
rt_tp162 <- ggtree(rt_tree162, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp162$layers[[1]]$aes_params$alpha <- 0.02
rt_tp162$layers[[1]]$aes_params$colour <- 'black'

rt_tree163 <- read.tree(text="(((1,2,3)1-3,4,(5,((6,7,8)6-8,9)6-9)5-9,((10,((((11,12,13)11-13,14,15)11-15,16,17)11-17,18)11-18)10-18,19,20,21)10-21)1-21,22)1-22;")
rt_tp163 <- ggtree(rt_tree163, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp163$layers[[1]]$aes_params$alpha <- 0.02
rt_tp163$layers[[1]]$aes_params$colour <- 'black'

rt_tree164 <- read.tree(text="((1,((2,3)2-3,4)2-4,(5,6)5-6,7)1-7,(8,((9,(10,11)10-11)9-11,12,(((13,14)13-14,(15,(16,((17,18,19)17-19,20)17-20,21)16-21)15-21)13-21,22)13-22)9-22)8-22)1-22;")
rt_tp164 <- ggtree(rt_tree164, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp164$layers[[1]]$aes_params$alpha <- 0.02
rt_tp164$layers[[1]]$aes_params$colour <- 'black'

rt_tree165 <- read.tree(text="((1,2,(((3,4)3-4,5)3-5,((((6,7,8)6-8,9)6-9,10)6-10,(11,12)11-12,(13,(14,15)14-15)13-15)6-15,(16,((17,(18,(19,20)19-20)18-20)17-20,21)17-21)16-21)3-21)1-21,22)1-22;")
rt_tp165 <- ggtree(rt_tree165, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp165$layers[[1]]$aes_params$alpha <- 0.02
rt_tp165$layers[[1]]$aes_params$colour <- 'black'

rt_tree166 <- read.tree(text="((1,((2,(((3,4)3-4,(5,6,((7,(8,9)8-9)7-9,((10,11)10-11,12,((13,14)13-14,15)13-15)10-15)7-15,16,17)5-17)3-17,18)3-18,19)2-19,20,21)2-21)1-21,22)1-22;")
rt_tp166 <- ggtree(rt_tree166, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp166$layers[[1]]$aes_params$alpha <- 0.02
rt_tp166$layers[[1]]$aes_params$colour <- 'black'

rt_tree167 <- read.tree(text="(1,((((2,3,4)2-4,5)2-5,(((6,7)6-7,8)6-8,(9,10,11)9-11)6-11)2-11,((12,(13,(14,(15,16)15-16)14-16)13-16,(17,((18,19)18-19,20)18-20)17-20)12-20,21)12-21,22)2-22)1-22;")
rt_tp167 <- ggtree(rt_tree167, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp167$layers[[1]]$aes_params$alpha <- 0.02
rt_tp167$layers[[1]]$aes_params$colour <- 'black'

rt_tree168 <- read.tree(text="(((1,(2,(3,(4,5,6,7,8)4-8)3-8,9)2-9)1-9,10)1-10,(((11,12)11-12,13,14)11-14,(((15,16)15-16,(((17,18)17-18,(19,20)19-20)17-20,21)17-21)15-21,22)15-22)11-22)1-22;")
rt_tp168 <- ggtree(rt_tree168, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp168$layers[[1]]$aes_params$alpha <- 0.02
rt_tp168$layers[[1]]$aes_params$colour <- 'black'

rt_tree169 <- read.tree(text="(1,(2,3,4)2-4,((5,((6,7,((8,9,10)8-10,11,((((12,(13,14)13-14)12-14,15)12-15,16)12-16,(17,18)17-18)12-18)8-18)6-18,19,20)6-20)5-20,(21,22)21-22)5-22)1-22;")
rt_tp169 <- ggtree(rt_tree169, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp169$layers[[1]]$aes_params$alpha <- 0.02
rt_tp169$layers[[1]]$aes_params$colour <- 'black'

rt_tree170 <- read.tree(text="(1,(2,(3,4)3-4,(((5,6,((7,8)7-8,9)7-9)5-9,10)5-10,11,(12,13,14,15,(16,17,18,19)16-19)12-19,(20,21,22)20-22)5-22)2-22)1-22;")
rt_tp170 <- ggtree(rt_tree170, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp170$layers[[1]]$aes_params$alpha <- 0.02
rt_tp170$layers[[1]]$aes_params$colour <- 'black'

rt_tree171 <- read.tree(text="(1,((2,(3,(4,5)4-5)3-5)2-5,6,7,(8,9)8-9)2-9,10,((11,12,13)11-13,14,15,((16,(17,18)17-18)16-18,(19,(20,21)20-21)19-21)16-21,22)11-22)1-22;")
rt_tp171 <- ggtree(rt_tree171, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp171$layers[[1]]$aes_params$alpha <- 0.02
rt_tp171$layers[[1]]$aes_params$colour <- 'black'

rt_tree172 <- read.tree(text="((1,((2,((3,(4,5)4-5,6)3-6,7,(8,9)8-9)3-9)2-9,((10,11,12,13,14)10-14,(15,(16,(17,18)17-18)16-18)15-18)10-18,19)2-19)1-19,((20,21)20-21,22)20-22)1-22;")
rt_tp172 <- ggtree(rt_tree172, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp172$layers[[1]]$aes_params$alpha <- 0.02
rt_tp172$layers[[1]]$aes_params$colour <- 'black'

rt_tree173 <- read.tree(text="(1,((((2,((3,4)3-4,5)3-5,6)2-6,7)2-7,((8,((9,10)9-10,(11,((12,13)12-13,14,15)12-15)11-15,16)9-16)8-16,17)8-17)2-17,18)2-18,((19,20)19-20,21,22)19-22)1-22;")
rt_tp173 <- ggtree(rt_tree173, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp173$layers[[1]]$aes_params$alpha <- 0.02
rt_tp173$layers[[1]]$aes_params$colour <- 'black'

rt_tree174 <- read.tree(text="(1,(2,(3,(4,5,(6,((7,((8,9)8-9,10,11,12)8-12)7-12,13,14,15)7-15,((16,17)16-17,18)16-18)6-18,(19,(20,21)20-21,22)19-22)4-22)3-22)2-22)1-22;")
rt_tp174 <- ggtree(rt_tree174, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp174$layers[[1]]$aes_params$alpha <- 0.02
rt_tp174$layers[[1]]$aes_params$colour <- 'black'

rt_tree175 <- read.tree(text="((1,((2,(3,(((4,5)4-5,6)4-6,(7,(8,9)8-9)7-9,(10,(11,(12,13)12-13,14)11-14)10-14)4-14,15)3-15)2-15,(16,17)16-17)2-17)1-17,(18,(19,(20,21)20-21,22)19-22)18-22)1-22;")
rt_tp175 <- ggtree(rt_tree175, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp175$layers[[1]]$aes_params$alpha <- 0.02
rt_tp175$layers[[1]]$aes_params$colour <- 'black'

rt_tree176 <- read.tree(text="(1,2,(((3,((4,(5,((6,7)6-7,8)6-8)5-8)4-8,(9,10)9-10)4-10)3-10,11,(12,(13,(14,15,((16,17,18)16-18,19)16-19,20)14-20)13-20,21)12-21)3-21,22)3-22)1-22;")
rt_tp176 <- ggtree(rt_tree176, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp176$layers[[1]]$aes_params$alpha <- 0.02
rt_tp176$layers[[1]]$aes_params$colour <- 'black'

rt_tree177 <- read.tree(text="(((1,2,3)1-3,4,5,6,((7,8,9)7-9,10)7-10,(11,(12,(((13,(14,15,16)14-16,(17,18)17-18)13-18,19)13-19,20)13-20)12-20)11-20,21)1-21,22)1-22;")
rt_tp177 <- ggtree(rt_tree177, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp177$layers[[1]]$aes_params$alpha <- 0.02
rt_tp177$layers[[1]]$aes_params$colour <- 'black'

rt_tree178 <- read.tree(text="(((1,(2,3,(4,((5,6)5-6,(7,8,((9,10)9-10,(11,(12,(((13,14)13-14,15)13-15,(16,17)16-17)13-17,18)12-18)11-18,19)9-19)7-19,20)5-20)4-20)2-20)1-20,21)1-21,22)1-22;")
rt_tp178 <- ggtree(rt_tree178, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp178$layers[[1]]$aes_params$alpha <- 0.02
rt_tp178$layers[[1]]$aes_params$colour <- 'black'

rt_tree179 <- read.tree(text="(((1,(2,(3,(4,((5,(6,(7,8,(9,10,(((11,12)11-12,13,14)11-14,15)11-15)9-15)7-15)6-15)5-15,16)5-16)4-16)3-16)2-16)1-16,(17,18)17-18)1-18,((19,20)19-20,(21,22)21-22)19-22)1-22;")
rt_tp179 <- ggtree(rt_tree179, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp179$layers[[1]]$aes_params$alpha <- 0.02
rt_tp179$layers[[1]]$aes_params$colour <- 'black'

rt_tree180 <- read.tree(text="(1,((((2,3,4)2-4,((5,((6,7,8,(9,10)9-10)6-10,(((11,12)11-12,13)11-13,14)11-14)6-14,15)5-15,(16,17)16-17)5-17)2-17,18,19,20)2-20,(21,22)21-22)2-22)1-22;")
rt_tp180 <- ggtree(rt_tree180, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp180$layers[[1]]$aes_params$alpha <- 0.02
rt_tp180$layers[[1]]$aes_params$colour <- 'black'

rt_tree181 <- read.tree(text="(1,((((((2,(3,(4,5,6)4-6,7)3-7)2-7,8)2-8,9)2-9,(10,(11,(12,(13,(14,15)14-15)13-15)12-15)11-15)10-15)2-15,(16,((17,18)17-18,(19,20)19-20)17-20)16-20,21)2-21,22)2-22)1-22;")
rt_tp181 <- ggtree(rt_tree181, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp181$layers[[1]]$aes_params$alpha <- 0.02
rt_tp181$layers[[1]]$aes_params$colour <- 'black'

rt_tree182 <- read.tree(text="(1,((2,((3,4,5)3-5,(((((6,7,8,9,10)6-10,(11,12)11-12)6-12,(13,14)13-14)6-14,15,16,17)6-17,(18,19)18-19,(20,21)20-21)6-21)3-21)2-21,22)2-22)1-22;")
rt_tp182 <- ggtree(rt_tree182, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp182$layers[[1]]$aes_params$alpha <- 0.02
rt_tp182$layers[[1]]$aes_params$colour <- 'black'

rt_tree183 <- read.tree(text="((((1,2,3)1-3,4)1-4,5)1-5,6,7,((((8,(((9,10,(11,12)11-12)9-12,13)9-13,14,((15,16)15-16,17,18)15-18)9-18)8-18,19)8-19,20,21)8-21,22)8-22)1-22;")
rt_tp183 <- ggtree(rt_tree183, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp183$layers[[1]]$aes_params$alpha <- 0.02
rt_tp183$layers[[1]]$aes_params$colour <- 'black'

rt_tree184 <- read.tree(text="(((1,(((2,(3,4)3-4)2-4,5,(6,7,(8,((9,(10,11)10-11)9-11,(12,13)12-13,14)9-14)8-14)6-14)2-14,(15,(16,17)16-17)15-17)2-17,((18,19)18-19,20)18-20)1-20,21)1-21,22)1-22;")
rt_tp184 <- ggtree(rt_tree184, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp184$layers[[1]]$aes_params$alpha <- 0.02
rt_tp184$layers[[1]]$aes_params$colour <- 'black'

rt_tree185 <- read.tree(text="(((1,2)1-2,3)1-3,((4,((((5,6,(7,8,9)7-9)5-9,(10,(11,((12,(13,(14,15)14-15)13-15)12-15,16)12-16)11-16,17)10-17)5-17,18)5-18,(19,20)19-20,21)5-21)4-21,22)4-22)1-22;")
rt_tp185 <- ggtree(rt_tree185, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp185$layers[[1]]$aes_params$alpha <- 0.02
rt_tp185$layers[[1]]$aes_params$colour <- 'black'

rt_tree186 <- read.tree(text="((((1,(2,(3,4)3-4)2-4)1-4,((5,(6,(7,8)7-8,(9,10)9-10)6-10,11)5-11,(12,((13,14)13-14,15)13-15,16)12-16)5-16)1-16,17)1-17,(18,19,20,21,22)18-22)1-22;")
rt_tp186 <- ggtree(rt_tree186, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp186$layers[[1]]$aes_params$alpha <- 0.02
rt_tp186$layers[[1]]$aes_params$colour <- 'black'

rt_tree187 <- read.tree(text="((1,2)1-2,(3,(4,(5,(6,7,8)6-8)5-8)4-8,9,(10,((11,12)11-12,((13,14)13-14,15)13-15,(((16,17)16-17,18)16-18,19,20,21,22)16-22)11-22)10-22)3-22)1-22;")
rt_tp187 <- ggtree(rt_tree187, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp187$layers[[1]]$aes_params$alpha <- 0.02
rt_tp187$layers[[1]]$aes_params$colour <- 'black'

rt_tree188 <- read.tree(text="(((((1,(2,3)2-3)1-3,(4,(5,6,7)5-7,8,((9,10)9-10,11)9-11)4-11)1-11,(((12,13,14)12-14,15)12-15,16,17,18,19)12-19,20)1-20,21)1-21,22)1-22;")
rt_tp188 <- ggtree(rt_tree188, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp188$layers[[1]]$aes_params$alpha <- 0.02
rt_tp188$layers[[1]]$aes_params$colour <- 'black'

rt_tree189 <- read.tree(text="((1,((2,3,((((4,5)4-5,6)4-6,7)4-7,8,9)4-9)2-9,10)2-10)1-10,((((11,12)11-12,(13,14,(15,16)15-16)13-16,17)11-17,18)11-18,(19,20)19-20,21,22)11-22)1-22;")
rt_tp189 <- ggtree(rt_tree189, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp189$layers[[1]]$aes_params$alpha <- 0.02
rt_tp189$layers[[1]]$aes_params$colour <- 'black'

rt_tree190 <- read.tree(text="(1,(2,(3,4)3-4)2-4,((5,((((6,7)6-7,8)6-8,9)6-9,(10,11)10-11)6-11,((12,13,(14,15)14-15)12-15,(16,17)16-17)12-17)5-17,18,19,(20,21,22)20-22)5-22)1-22;")
rt_tp190 <- ggtree(rt_tree190, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp190$layers[[1]]$aes_params$alpha <- 0.02
rt_tp190$layers[[1]]$aes_params$colour <- 'black'

rt_tree191 <- read.tree(text="((1,2,((3,(4,5)4-5,(6,(7,8,(9,(10,11)10-11)9-11)7-11)6-11,12,13)3-13,(14,15,((((16,17)16-17,18)16-18,19)16-19,20)16-20)14-20)3-20,21)1-21,22)1-22;")
rt_tp191 <- ggtree(rt_tree191, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp191$layers[[1]]$aes_params$alpha <- 0.02
rt_tp191$layers[[1]]$aes_params$colour <- 'black'

rt_tree192 <- read.tree(text="((1,(2,3)2-3)1-3,(4,((5,6)5-6,((7,8)7-8,9)7-9,((10,(11,(12,13)12-13)11-13)10-13,(14,15)14-15)10-15,16,17)5-17)4-17,(18,19,20,21,22)18-22)1-22;")
rt_tp192 <- ggtree(rt_tree192, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp192$layers[[1]]$aes_params$alpha <- 0.02
rt_tp192$layers[[1]]$aes_params$colour <- 'black'

rt_tree193 <- read.tree(text="((1,((2,3,((((4,5)4-5,6)4-6,(7,8,9)7-9)4-9,((10,11)10-11,(12,13)12-13)10-13)4-13)2-13,14)2-14,((15,16,((17,18)17-18,19)17-19)15-19,(20,21)20-21)15-21)1-21,22)1-22;")
rt_tp193 <- ggtree(rt_tree193, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp193$layers[[1]]$aes_params$alpha <- 0.02
rt_tp193$layers[[1]]$aes_params$colour <- 'black'

rt_tree194 <- read.tree(text="(1,(((2,(3,4,(((5,6)5-6,7)5-7,(8,((9,10)9-10,11,12)9-12)8-12)5-12)3-12)2-12,(13,14)13-14)2-14,(15,16,17)15-17)2-17,(((18,19)18-19,20)18-20,21)18-21,22)1-22;")
rt_tp194 <- ggtree(rt_tree194, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp194$layers[[1]]$aes_params$alpha <- 0.02
rt_tp194$layers[[1]]$aes_params$colour <- 'black'

rt_tree195 <- read.tree(text="((1,(((2,3)2-3,4)2-4,5)2-5,(6,(7,8)7-8)6-8,((9,10)9-10,11)9-11)1-11,((12,13)12-13,((14,15,16)14-16,(17,(18,(19,20)19-20)18-20)17-20,21)14-21)12-21,22)1-22;")
rt_tp195 <- ggtree(rt_tree195, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp195$layers[[1]]$aes_params$alpha <- 0.02
rt_tp195$layers[[1]]$aes_params$colour <- 'black'

rt_tree196 <- read.tree(text="(1,((2,(3,4)3-4,(5,((6,7,(8,9,((10,11)10-11,12)10-12,13)8-13)6-13,(14,((15,(16,17,(18,19)18-19,20)16-20)15-20,21)15-21)14-21)6-21)5-21)2-21,22)2-22)1-22;")
rt_tp196 <- ggtree(rt_tree196, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp196$layers[[1]]$aes_params$alpha <- 0.02
rt_tp196$layers[[1]]$aes_params$colour <- 'black'

rt_tree197 <- read.tree(text="((((1,2)1-2,3)1-3,((4,5)4-5,(((6,7,(8,9)8-9,10)6-10,(11,(12,13)12-13)11-13)6-13,14)6-14,((15,16)15-16,17,(18,19)18-19)15-19)4-19,20)1-20,21,22)1-22;")
rt_tp197 <- ggtree(rt_tree197, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp197$layers[[1]]$aes_params$alpha <- 0.02
rt_tp197$layers[[1]]$aes_params$colour <- 'black'

rt_tree198 <- read.tree(text="((1,(2,3,(4,(((5,6)5-6,(7,(8,((9,10)9-10,(11,12)11-12,13,14,15,16,17)9-17,18)8-18)7-18,19,20)5-20,21)5-21)4-21)2-21)1-21,22)1-22;")
rt_tp198 <- ggtree(rt_tree198, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp198$layers[[1]]$aes_params$alpha <- 0.02
rt_tp198$layers[[1]]$aes_params$colour <- 'black'

rt_tree199 <- read.tree(text="(1,(2,(3,((4,(5,6)5-6,((7,8,9,(10,11,12)10-12,13)7-13,(14,15)14-15)7-15,16)4-16,17)4-17,(18,19)18-19)3-19,20)2-20,21,22)1-22;")
rt_tp199 <- ggtree(rt_tree199, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp199$layers[[1]]$aes_params$alpha <- 0.02
rt_tp199$layers[[1]]$aes_params$colour <- 'black'

rt_tree200 <- read.tree(text="(1,((2,3)2-3,((4,5)4-5,6,((7,(8,((9,(10,11)10-11)9-11,((12,13,(14,15)14-15)12-15,(16,17,(18,19)18-19)16-19,20)12-20)9-20)8-20)7-20,21)7-21,22)4-22)2-22)1-22;")
rt_tp200 <- ggtree(rt_tree200, layout='slanted', ladderize=FALSE) +
  layout_dendrogram() +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position='none')
rt_tp200$layers[[1]]$aes_params$alpha <- 0.02
rt_tp200$layers[[1]]$aes_params$colour <- 'black'

rt_tp200 <- rt_tp200 + geom_tiplab(geom='label', size=5, angle=0,
  offset=-1, hjust=0.5, vjust=1.25, alpha=1, label.size=0,
  aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt"))

overlay_design <- c(
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1),
  area(t=1, l=1, b=1, r=1)
)
overlay <- (
rt_tp1 +
  rt_tp2 +
  rt_tp3 +
  rt_tp4 +
  rt_tp5 +
  rt_tp6 +
  rt_tp7 +
  rt_tp8 +
  rt_tp9 +
  rt_tp10 +
  rt_tp11 +
  rt_tp12 +
  rt_tp13 +
  rt_tp14 +
  rt_tp15 +
  rt_tp16 +
  rt_tp17 +
  rt_tp18 +
  rt_tp19 +
  rt_tp20 +
  rt_tp21 +
  rt_tp22 +
  rt_tp23 +
  rt_tp24 +
  rt_tp25 +
  rt_tp26 +
  rt_tp27 +
  rt_tp28 +
  rt_tp29 +
  rt_tp30 +
  rt_tp31 +
  rt_tp32 +
  rt_tp33 +
  rt_tp34 +
  rt_tp35 +
  rt_tp36 +
  rt_tp37 +
  rt_tp38 +
  rt_tp39 +
  rt_tp40 +
  rt_tp41 +
  rt_tp42 +
  rt_tp43 +
  rt_tp44 +
  rt_tp45 +
  rt_tp46 +
  rt_tp47 +
  rt_tp48 +
  rt_tp49 +
  rt_tp50 +
  rt_tp51 +
  rt_tp52 +
  rt_tp53 +
  rt_tp54 +
  rt_tp55 +
  rt_tp56 +
  rt_tp57 +
  rt_tp58 +
  rt_tp59 +
  rt_tp60 +
  rt_tp61 +
  rt_tp62 +
  rt_tp63 +
  rt_tp64 +
  rt_tp65 +
  rt_tp66 +
  rt_tp67 +
  rt_tp68 +
  rt_tp69 +
  rt_tp70 +
  rt_tp71 +
  rt_tp72 +
  rt_tp73 +
  rt_tp74 +
  rt_tp75 +
  rt_tp76 +
  rt_tp77 +
  rt_tp78 +
  rt_tp79 +
  rt_tp80 +
  rt_tp81 +
  rt_tp82 +
  rt_tp83 +
  rt_tp84 +
  rt_tp85 +
  rt_tp86 +
  rt_tp87 +
  rt_tp88 +
  rt_tp89 +
  rt_tp90 +
  rt_tp91 +
  rt_tp92 +
  rt_tp93 +
  rt_tp94 +
  rt_tp95 +
  rt_tp96 +
  rt_tp97 +
  rt_tp98 +
  rt_tp99 +
  rt_tp100 +
  rt_tp101 +
  rt_tp102 +
  rt_tp103 +
  rt_tp104 +
  rt_tp105 +
  rt_tp106 +
  rt_tp107 +
  rt_tp108 +
  rt_tp109 +
  rt_tp110 +
  rt_tp111 +
  rt_tp112 +
  rt_tp113 +
  rt_tp114 +
  rt_tp115 +
  rt_tp116 +
  rt_tp117 +
  rt_tp118 +
  rt_tp119 +
  rt_tp120 +
  rt_tp121 +
  rt_tp122 +
  rt_tp123 +
  rt_tp124 +
  rt_tp125 +
  rt_tp126 +
  rt_tp127 +
  rt_tp128 +
  rt_tp129 +
  rt_tp130 +
  rt_tp131 +
  rt_tp132 +
  rt_tp133 +
  rt_tp134 +
  rt_tp135 +
  rt_tp136 +
  rt_tp137 +
  rt_tp138 +
  rt_tp139 +
  rt_tp140 +
  rt_tp141 +
  rt_tp142 +
  rt_tp143 +
  rt_tp144 +
  rt_tp145 +
  rt_tp146 +
  rt_tp147 +
  rt_tp148 +
  rt_tp149 +
  rt_tp150 +
  rt_tp151 +
  rt_tp152 +
  rt_tp153 +
  rt_tp154 +
  rt_tp155 +
  rt_tp156 +
  rt_tp157 +
  rt_tp158 +
  rt_tp159 +
  rt_tp160 +
  rt_tp161 +
  rt_tp162 +
  rt_tp163 +
  rt_tp164 +
  rt_tp165 +
  rt_tp166 +
  rt_tp167 +
  rt_tp168 +
  rt_tp169 +
  rt_tp170 +
  rt_tp171 +
  rt_tp172 +
  rt_tp173 +
  rt_tp174 +
  rt_tp175 +
  rt_tp176 +
  rt_tp177 +
  rt_tp178 +
  rt_tp179 +
  rt_tp180 +
  rt_tp181 +
  rt_tp182 +
  rt_tp183 +
  rt_tp184 +
  rt_tp185 +
  rt_tp186 +
  rt_tp187 +
  rt_tp188 +
  rt_tp189 +
  rt_tp190 +
  rt_tp191 +
  rt_tp192 +
  rt_tp193 +
  rt_tp194 +
  rt_tp195 +
  rt_tp196 +
  rt_tp197 +
  rt_tp198 +
  rt_tp199 +
  rt_tp200
) + plot_layout(design=overlay_design)

ggsave('/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_random_tree_overlay.pdf', overlay, width=16, height=10)
