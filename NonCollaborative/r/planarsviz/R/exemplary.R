# Exemplary trees and slides (chart 10 in docs/PLAN_planarsviz_library.md).
#
# STEP 1 COPY: everything below the header is copied verbatim from
# results/nyan1308_exemplary_trees.r, lines 1-225, at commit 43a308f
# (written by laminar_analysis.generate_r_exemplary_trees_script() via
# generate_exemplary_trees(include_sparsest=True)), wrapped in an uncalled
# function so loading the package doesn't run it. No other edits.
# Literals are replaced with bundle data in the next commit.

exemplary_step1_copy <- function() {
library(ape)
library(ggtree)
library(patchwork)

source(here::here("NonCollaborative", "scripts", "domain_charts-cgpt.r"))

posLabel <- list("1" = "QM", "2" = "PreSbj", "3" = "Sbj", "4" = "PostSbj", "5" = "Neg1", "6" = "SM", "7" = "Neg2", "8" = "TAM", "9" = "OM", "10" = "Root", "11" = "Ext", "12" = "STAT", "13" = "CAUS", "14" = "APPL", "15" = "REC", "16" = "PASS", "17" = "FV", "18" = "2P", "19" = "Enc", "20" = "Obj1", "21" = "Obj2", "22" = "PostObj")

ex_tree1 <- read.tree(text="(1,(2,(3,4,((((5,((6,7,8)6-8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)6-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ex_tp1 <- ggtree(ex_tree1, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ex_plot1_data <- filter(tests_plot, Test_Labels %in% c("Accent-PenultimateLengthening-Maximal-NoSubj", "Accent-PenultimateLengthening-Maximal-Subj", "BiuniquenessDeviation-TAMP", "BiuniquenessDeviation-Valency", "Ciscategorial-Maximal", "Downdrift-DeclarativeContentQ-Maximal", "Downdrift-DeclarativeContentQ-Minimal", "Downdrift-YesNoQ-Maximal", "Downdrift-YesNoQ-Minimal", "FinalPitch-Declarative-Maximal", "FinalPitch-Declarative-Minimal", "FinalPitch-YesNoQ-Maximal", "FinalPitch-YesNoQ-Minimal", "FreeOccurrence-Maximal-AFF/2pOBJ", "FreeOccurrence-Maximal-AFF/IMP2s", "FreeOccurrence-Maximal/elsewhere", "Length-DisyllabicMinimality", "NegTonePattern2-Neg1-NoOM-MonoSyll", "NegTonePattern2-Neg1-Other", "NegTonePattern2-Neg2-IMP-NoOM-MonoSyll", "NegTonePattern2-Neg2-SeqPFV-NoOM-MonoSyll", "NegTonePattern2-Neg2-SeqPFV-Other", "NegTonePattern3-PERM-NoOM-DiSyll", "NegTonePattern3-PERM-NoOM-MonoSyll", "NegTonePattern3-PERM-NoOM-Other", "NegTonePattern3-PERM-OM-MonoSyll", "NegTonePattern3-PERM-OM-Other", "NegTonePattern3-PfvSimPST-NoOM-MonoSyll", "NegTonePattern3-PfvSimPST-Other", "NonInterruptibility", "NonPermutability-Scopal", "PitchRange-Declarative-Maximal", "PitchRange-Declarative-Minimal", "PitchRange-Question-Maximal", "PitchRange-Question-Minimal", "Segmental-HiatusResolution-Deletion", "Segmental-HiatusResolution-Glide", "Segmental-VowelHarmony", "Segmental-muContraction", "SubspanRepetition-Coordination-Maximal", "Tonal-FinalRetraction-Maximal-NoSubj", "Tonal-FinalRetraction-Maximal-Subj", "Tonal-Plateauing-Maximal-NoSubj", "Tonal-Plateauing-Maximal-Subj", "Tonal-ToneDoubling-Maximal-NoSubj", "Tonal-ToneDoubling-Maximal-Subj", "Tonal-ToneDoubling-Minimal", "TonePattern2-OM-DiSyll", "TonePattern2-OM-MonoSyll", "TonePattern3-OM-MonoSyll", "TonePattern3-OM-Other", "TonePattern6-HAB-noOM-MonoSyll", "TonePattern6-RP-noOM-MonoSyll", "TonePattern7-OM-MonoSyll", "TonePattern7-noOM", "TonePattern8-OM-JST-DiTriSyll", "TonePattern8-OM-JST-MonoSyll", "TonePattern8-noOM-JST-DiSyll", "TonePattern8-noOM-JST-MonoSyll"))
ex_plot1 <- constituency.plot(ex_plot1_data, b, o)

ex_page1 <- (ex_tp1 | ex_plot1) +
  plot_layout(widths=c(51.0, 25.0))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_1.pdf", ex_page1, device="pdf",
  width=76.0, height=41.3, units="cm", limitsize=FALSE)

ex_slide_tp1 <- ggtree(ex_tree1, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=4.6, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    label.padding=unit(0.12, "lines"),
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_1_tree.pdf", ex_slide_tp1, device="pdf",
  width=13.333, height=7.5, units="in", limitsize=FALSE)
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_1_evidence.pdf", ex_plot1, device="pdf",
  width=25.0, height=41.3, units="cm", limitsize=FALSE)

ex_tree2 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(((8,(9,10)9-10)8-10,11,12,(13,14,15)13-15,16)8-16,17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ex_tp2 <- ggtree(ex_tree2, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ex_plot2_data <- filter(tests_plot, Test_Labels %in% c("Accent-PenultimateLengthening-Maximal-NoSubj", "Accent-PenultimateLengthening-Maximal-Subj", "BiuniquenessDeviation-TAMP", "BiuniquenessDeviation-Valency", "Ciscategorial-Maximal", "Downdrift-DeclarativeContentQ-Maximal", "Downdrift-YesNoQ-Maximal", "FinalPitch-Declarative-Maximal", "FinalPitch-YesNoQ-Maximal", "FreeOccurrence-Maximal-AFF/2pOBJ", "FreeOccurrence-Maximal/elsewhere", "Length-DisyllabicMinimality", "NegTonePattern2-Neg1-NoOM-MonoSyll", "NegTonePattern2-Neg1-Other", "NegTonePattern3-PERM-NoOM-DiSyll", "NegTonePattern3-PERM-NoOM-MonoSyll", "NegTonePattern3-PERM-NoOM-Other", "NegTonePattern3-PERM-OM-MonoSyll", "NegTonePattern3-PERM-OM-Other", "NegTonePattern4-OM", "NegTonePattern4-noOM", "NonInterruptibility", "NonPermutability-Scopal", "PitchRange-Declarative-Maximal", "PitchRange-Question-Maximal", "Segmental-Assimilation-Neg", "SubspanRepetition-Coordination-Maximal", "Tonal-FinalRetraction-Maximal-NoSubj", "Tonal-FinalRetraction-Maximal-Subj", "Tonal-Plateauing-Maximal-NoSubj", "Tonal-Plateauing-Maximal-Subj", "Tonal-ToneDoubling-Maximal-NoSubj", "Tonal-ToneDoubling-Maximal-Subj", "TonePattern2-OM-Other", "TonePattern4-OM-DiTriSyll", "TonePattern4-OM-MonoSyll", "TonePattern4-OM-Other", "TonePattern4-noOM-DiSyll", "TonePattern4-noOM-MonoSyll", "TonePattern4-noOM-Other", "TonePattern5-OM", "TonePattern5-noOM-MonoDiSyll", "TonePattern5-noOM-Other"))
ex_plot2 <- constituency.plot(ex_plot2_data, b, o)

ex_page2 <- (ex_tp2 | ex_plot2) +
  plot_layout(widths=c(51.0, 25.0))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_2.pdf", ex_page2, device="pdf",
  width=76.0, height=30.1, units="cm", limitsize=FALSE)

ex_slide_tp2 <- ggtree(ex_tree2, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=4.6, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    label.padding=unit(0.12, "lines"),
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_2_tree.pdf", ex_slide_tp2, device="pdf",
  width=13.333, height=7.5, units="in", limitsize=FALSE)
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_2_evidence.pdf", ex_plot2, device="pdf",
  width=25.0, height=30.1, units="cm", limitsize=FALSE)

ex_tree3 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,(9,((((10,11,12,13)10-13,14,15,16)10-16,17)10-17,18)10-18)9-18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ex_tp3 <- ggtree(ex_tree3, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ex_plot3_data <- filter(tests_plot, Test_Labels %in% c("Accent-PenultimateLengthening-Maximal-NoSubj", "Accent-PenultimateLengthening-Maximal-Subj", "Accent-PenultimateLengthening-Minimal", "BiuniquenessDeviation-2pl", "Ciscategorial-Maximal", "Ciscategorial-Minimal", "Downdrift-DeclarativeContentQ-Maximal", "Downdrift-YesNoQ-Maximal", "FinalPitch-Declarative-Maximal", "FinalPitch-YesNoQ-Maximal", "FreeOccurrence-Maximal-AFF/2pOBJ", "FreeOccurrence-Maximal-AFF/IMP2p", "FreeOccurrence-Minimal-AFF/IMP2p", "FreeOccurrence-Minimal-AFF/IMP2s", "NonInterruptibility", "NonPermutability-Scopal", "PitchRange-Declarative-Maximal", "PitchRange-Question-Maximal", "Segmental-Assimilation-Neg", "Segmental-VowelHarmony", "SubspanRepetition-Coordination-Maximal", "SubspanRepetition-Coordination-Minimal", "SubspanRepetition-Reduplication", "Tonal-FinalRetraction-Maximal-NoSubj", "Tonal-FinalRetraction-Maximal-Subj", "Tonal-FinalRetraction-Minimal", "Tonal-Plateauing-Maximal-NoSubj", "Tonal-Plateauing-Maximal-Subj", "Tonal-Plateauing-Minimal", "Tonal-RootExtensionHighTone", "Tonal-ToneDoubling-Maximal-NoSubj", "Tonal-ToneDoubling-Maximal-Subj"))
ex_plot3 <- constituency.plot(ex_plot3_data, b, o)

ex_page3 <- (ex_tp3 | ex_plot3) +
  plot_layout(widths=c(51.0, 25.0))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_3.pdf", ex_page3, device="pdf",
  width=76.0, height=22.4, units="cm", limitsize=FALSE)

ex_slide_tp3 <- ggtree(ex_tree3, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=4.6, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    label.padding=unit(0.12, "lines"),
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_3_tree.pdf", ex_slide_tp3, device="pdf",
  width=13.333, height=7.5, units="in", limitsize=FALSE)
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_3_evidence.pdf", ex_plot3, device="pdf",
  width=25.0, height=22.4, units="cm", limitsize=FALSE)

ex_tree4 <- read.tree(text="(1,(2,(3,4,((5,(((6,7,8)6-8,(9,10)9-10)6-10,11,12,(13,14,15)13-15,16)6-16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ex_tp4 <- ggtree(ex_tree4, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ex_plot4_data <- filter(tests_plot, Test_Labels %in% c("Accent-PenultimateLengthening-Maximal-NoSubj", "Accent-PenultimateLengthening-Maximal-Subj", "BiuniquenessDeviation-Valency", "Downdrift-DeclarativeContentQ-Maximal", "Downdrift-YesNoQ-Maximal", "FinalPitch-Declarative-Maximal", "FinalPitch-YesNoQ-Maximal", "NegTonePattern2-Neg2-IMP-Other", "NonInterruptibility", "NonPermutability-Scopal", "PitchRange-Declarative-Maximal", "PitchRange-Question-Maximal", "Segmental-Assimilation", "Segmental-GlideInsertion", "Segmental-HiatusResolution-Deletion", "Segmental-HiatusResolution-Glide", "SubspanRepetition-Coordination-Maximal", "Tonal-EncliticToneShift", "Tonal-FinalRetraction-Maximal-NoSubj", "Tonal-FinalRetraction-Maximal-Subj", "Tonal-Plateauing-Maximal-NoSubj", "Tonal-Plateauing-Maximal-Subj", "Tonal-ToneDoubling-Maximal-NoSubj", "Tonal-ToneDoubling-Maximal-Subj", "TonePattern2-OM-Other", "TonePattern6-HAB-OM", "TonePattern6-HAB-noOM-Other", "TonePattern6-RP-OM", "TonePattern6-RP-noOM-Other", "TonePattern7-OM-Other", "TonePattern7-noOM", "TonePattern8-OM-JST-Other", "TonePattern8-noOM-JST-Other"))
ex_plot4 <- constituency.plot(ex_plot4_data, b, o)

ex_page4 <- (ex_tp4 | ex_plot4) +
  plot_layout(widths=c(51.0, 25.0))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_4.pdf", ex_page4, device="pdf",
  width=76.0, height=23.1, units="cm", limitsize=FALSE)

ex_slide_tp4 <- ggtree(ex_tree4, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=4.6, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    label.padding=unit(0.12, "lines"),
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_4_tree.pdf", ex_slide_tp4, device="pdf",
  width=13.333, height=7.5, units="in", limitsize=FALSE)
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_4_evidence.pdf", ex_plot4, device="pdf",
  width=25.0, height=23.1, units="cm", limitsize=FALSE)

ex_tree5 <- read.tree(text="(1,(2,(3,4,((((((5,6)5-6,7,(8,(9,10)9-10)8-10,11,12,13)5-13,14,15,16,17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ex_tp5 <- ggtree(ex_tree5, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ex_plot5_data <- filter(tests_plot, Test_Labels %in% c("Accent-PenultimateLengthening-Maximal-NoSubj", "Accent-PenultimateLengthening-Maximal-Subj", "BiuniquenessDeviation-TAMP", "Ciscategorial-Maximal", "Downdrift-DeclarativeContentQ-Maximal", "Downdrift-YesNoQ-Maximal", "FinalPitch-Declarative-Maximal", "FinalPitch-YesNoQ-Maximal", "FreeOccurrence-Maximal-AFF/2pOBJ", "FreeOccurrence-Maximal/elsewhere", "Length-DisyllabicMinimality", "NegTonePattern2-Neg1-NoOM-MonoSyll", "NegTonePattern2-Neg1-Other", "NegTonePattern3-PERM-NoOM-DiSyll", "NegTonePattern3-PERM-NoOM-MonoSyll", "NegTonePattern3-PERM-NoOM-Other", "NegTonePattern3-PERM-OM-MonoSyll", "NegTonePattern3-PERM-OM-Other", "NonInterruptibility", "NonPermutability-Scopal", "NonPermutability-Strict", "PitchRange-Declarative-Maximal", "PitchRange-Question-Maximal", "Segmental-Assimilation-Neg", "SubspanRepetition-Coordination-Maximal", "Tonal-FinalRetraction-Maximal-NoSubj", "Tonal-FinalRetraction-Maximal-Subj", "Tonal-Plateauing-Maximal-NoSubj", "Tonal-Plateauing-Maximal-Subj", "Tonal-ToneDoubling-Maximal-NoSubj", "Tonal-ToneDoubling-Maximal-Subj", "TonePattern2-OM-Other", "TonePattern4-noOM-Other"))
ex_plot5 <- constituency.plot(ex_plot5_data, b, o)

ex_page5 <- (ex_tp5 | ex_plot5) +
  plot_layout(widths=c(51.0, 25.0))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_5.pdf", ex_page5, device="pdf",
  width=76.0, height=23.1, units="cm", limitsize=FALSE)

ex_slide_tp5 <- ggtree(ex_tree5, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=4.6, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    label.padding=unit(0.12, "lines"),
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_5_tree.pdf", ex_slide_tp5, device="pdf",
  width=13.333, height=7.5, units="in", limitsize=FALSE)
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_5_evidence.pdf", ex_plot5, device="pdf",
  width=25.0, height=23.1, units="cm", limitsize=FALSE)

ex_tree6 <- read.tree(text="(1,(2,(3,4,(((((5,6)5-6,7,(8,((9,(10,11,12,(13,14,15)13-15,16)10-16)9-16,17)9-17)8-17)5-17,18)5-18,19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ex_tp6 <- ggtree(ex_tree6, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ex_plot6_data <- filter(tests_plot, Test_Labels %in% c("Accent-PenultimateLengthening-Maximal-NoSubj", "Accent-PenultimateLengthening-Maximal-Subj", "BiuniquenessDeviation-TAMP", "BiuniquenessDeviation-Valency", "Ciscategorial-Maximal", "Downdrift-DeclarativeContentQ-Maximal", "Downdrift-YesNoQ-Maximal", "FinalPitch-Declarative-Maximal", "FinalPitch-YesNoQ-Maximal", "FreeOccurrence-Maximal-AFF/2pOBJ", "FreeOccurrence-Maximal-AFF/IMP2s", "FreeOccurrence-Maximal/elsewhere", "Length-DisyllabicMinimality", "NegTonePattern2-Neg1-NoOM-MonoSyll", "NegTonePattern2-Neg1-Other", "NegTonePattern3-PERM-NoOM-DiSyll", "NegTonePattern3-PERM-NoOM-MonoSyll", "NegTonePattern3-PERM-NoOM-Other", "NegTonePattern3-PERM-OM-MonoSyll", "NegTonePattern3-PERM-OM-Other", "NegTonePattern4-OM", "NegTonePattern4-noOM", "NonInterruptibility", "NonPermutability-Scopal", "PitchRange-Declarative-Maximal", "PitchRange-Question-Maximal", "Segmental-Assimilation-Neg", "Segmental-VowelHarmony", "SubspanRepetition-Coordination-Maximal", "Tonal-FinalRetraction-Maximal-NoSubj", "Tonal-FinalRetraction-Maximal-Subj", "Tonal-Plateauing-Maximal-NoSubj", "Tonal-Plateauing-Maximal-Subj", "Tonal-ToneDoubling-Maximal-NoSubj", "Tonal-ToneDoubling-Maximal-Subj", "Tonal-ToneDoubling-Minimal", "TonePattern2-OM-DiSyll", "TonePattern2-OM-MonoSyll", "TonePattern3-OM-MonoSyll", "TonePattern3-OM-Other", "TonePattern4-OM-DiTriSyll", "TonePattern4-OM-MonoSyll", "TonePattern4-OM-Other", "TonePattern4-noOM-DiSyll", "TonePattern4-noOM-MonoSyll", "TonePattern5-noOM-MonoDiSyll"))
ex_plot6 <- constituency.plot(ex_plot6_data, b, o)

ex_page6 <- (ex_tp6 | ex_plot6) +
  plot_layout(widths=c(51.0, 25.0))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_6.pdf", ex_page6, device="pdf",
  width=76.0, height=32.2, units="cm", limitsize=FALSE)

ex_slide_tp6 <- ggtree(ex_tree6, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=4.6, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    label.padding=unit(0.12, "lines"),
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_6_tree.pdf", ex_slide_tp6, device="pdf",
  width=13.333, height=7.5, units="in", limitsize=FALSE)
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_6_evidence.pdf", ex_plot6, device="pdf",
  width=25.0, height=32.2, units="cm", limitsize=FALSE)

ex_tree7 <- read.tree(text="(1,(2,(3,4,((((5,6)5-6,7,8,9,(10,11,12,13)10-13)5-13,14,15,16,(17,18,19)17-19)5-19,20,21)5-21)3-21,22)2-22)1-22;")
ex_tp7 <- ggtree(ex_tree7, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=5, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ex_plot7_data <- filter(tests_plot, Test_Labels %in% c("Accent-PenultimateLengthening-Maximal-NoSubj", "Accent-PenultimateLengthening-Maximal-Subj", "Downdrift-DeclarativeContentQ-Maximal", "Downdrift-YesNoQ-Maximal", "FinalPitch-Declarative-Maximal", "FinalPitch-YesNoQ-Maximal", "NonInterruptibility", "NonPermutability-Scopal", "NonPermutability-Strict", "PitchRange-Declarative-Maximal", "PitchRange-Question-Maximal", "Segmental-Assimilation-Neg", "SubspanRepetition-Coordination-Maximal", "Tonal-EncliticToneShift", "Tonal-FinalRetraction-Maximal-NoSubj", "Tonal-FinalRetraction-Maximal-Subj", "Tonal-Plateauing-Maximal-NoSubj", "Tonal-Plateauing-Maximal-Subj", "Tonal-RootExtensionHighTone", "Tonal-ToneDoubling-Maximal-NoSubj", "Tonal-ToneDoubling-Maximal-Subj"))
ex_plot7 <- constituency.plot(ex_plot7_data, b, o)

ex_page7 <- (ex_tp7 | ex_plot7) +
  plot_layout(widths=c(51.0, 25.0))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_7.pdf", ex_page7, device="pdf",
  width=76.0, height=14.7, units="cm", limitsize=FALSE)

ex_slide_tp7 <- ggtree(ex_tree7, layout="slanted", ladderize=FALSE) +
  layout_dendrogram() +
  geom_tiplab(geom="label", size=4.6, angle=0,
    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
    label.padding=unit(0.12, "lines"),
    aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1) +
  theme(panel.background=element_blank(),
    plot.background=element_blank(), legend.position="none",
    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_7_tree.pdf", ex_slide_tp7, device="pdf",
  width=13.333, height=7.5, units="in", limitsize=FALSE)
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_exemplary_trees_slide_7_evidence.pdf", ex_plot7, device="pdf",
  width=25.0, height=14.7, units="cm", limitsize=FALSE)

}
