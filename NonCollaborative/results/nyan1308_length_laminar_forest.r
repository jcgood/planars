library(ape)
library(ggplot2)
library(ggtree)
library(patchwork)

posLabel <- list("1" = "QM", "2" = "PreSbj", "3" = "Sbj", "4" = "PostSbj", "5" = "Neg1", "6" = "SM", "7" = "Neg2", "8" = "TAM", "9" = "OM", "10" = "Root", "11" = "Ext", "12" = "STAT", "13" = "CAUS", "14" = "APPL", "15" = "REC", "16" = "PASS", "17" = "FV", "18" = "2P", "19" = "Enc", "20" = "Obj1", "21" = "Obj2", "22" = "PostObj")

alphaval <- 0.784557 / 2

nyan1308_length_tree1 <- read.tree(text="(1,2,3,4,((5,6,7,8,(9,(10,11,12,13,14,15,16,17)10-17)9-17)5-17,18)5-18)1-18;")
nyan1308_length_tree1grouped <- groupOTU(nyan1308_length_tree1, list(a = c(1, 18), b = c(5, 18), c = c(5, 17), d = c(9, 17), e = c(10, 17)))
strengthMap1 <- c(0.5, 1.7321, 1.7321, 1.0, 1.4142, 1.7321)
nyan1308_length_treeplot1 <- ggtree(nyan1308_length_tree1grouped,
  aes(size=(strengthMap1[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#E18727") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_length_tree2 <- read.tree(text="(1,2,3,4,(5,6,7,8,((9,(10,11,12,13,14,15,16,17)10-17)9-17,18)9-18)5-18)1-18;")
nyan1308_length_tree2grouped <- groupOTU(nyan1308_length_tree2, list(a = c(1, 18), b = c(5, 18), c = c(9, 18), d = c(9, 17), e = c(10, 17)))
strengthMap2 <- c(0.5, 1.7321, 1.7321, 1.4142, 1.4142, 1.7321)
nyan1308_length_treeplot2 <- ggtree(nyan1308_length_tree2grouped,
  aes(size=(strengthMap2[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#E18727") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_length_tree3 <- read.tree(text="(1,2,3,4,(5,6,7,8,(9,((10,11,12,13,14,15,16,17)10-17,18)10-18)9-18)5-18)1-18;")
nyan1308_length_tree3grouped <- groupOTU(nyan1308_length_tree3, list(a = c(1, 18), b = c(5, 18), c = c(9, 18), d = c(10, 18), e = c(10, 17)))
strengthMap3 <- c(0.5, 1.7321, 1.7321, 1.4142, 1.0, 1.7321)
nyan1308_length_treeplot3 <- ggtree(nyan1308_length_tree3grouped,
  aes(size=(strengthMap3[group])),
  layout="slanted", ladderize=FALSE,
  alpha=alphaval, color="#E18727") +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,
    lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(),
    legend.position="none",
    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +
  scale_size_identity()

nyan1308_length_treeplot3 <- nyan1308_length_treeplot3 + geom_tiplab(geom="label", size=6, angle=0,
  offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
  aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1)

treelayout <- c(
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1),
  area(t=1, l=1, b=5, r=1))

forest <- (
  nyan1308_length_treeplot1 +
  nyan1308_length_treeplot2 +
  nyan1308_length_treeplot3 +
  plot_layout(design=treelayout))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/results/nyan1308_length_laminar_forest.pdf", forest & theme(plot.background=element_rect(fill='white', color=NA)), width=20, height=14)
