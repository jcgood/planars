# Stacked laminar overlays (charts 7, 8, 9 in docs/PLAN_planarsviz_library.md).
#
# STEP 1 COPY: the blocks below are copied verbatim, at commit 43a308f, from
# the R that laminar_analysis.generate_r_overlay_script() writes, plus the
# hand edits in the wordhood variant, each wrapped in an uncalled function so
# loading the package doesn't run them. No other edits. Literals are replaced
# with bundle data in the next commit.
#
#   overlay_step1_header_and_tree()   results/nyan1308_laminar_overlay.r, lines 1-27
#                                     (header, alphaval, first group's first tree;
#                                     the generator repeats the tree block per tree)
#   overlay_step1_label_layout()      results/nyan1308_all_families_labeled.r,
#                                     lines 1115-1117 (visible label on the last tree)
#                                     and the forest/ggsave pattern (lines 1119-1121,
#                                     1190-1191, 1261, abbreviated to one tree)
#   overlay_step1_colour_legend()     results/nyan1308_laminar_overlay.r, final
#                                     legend block (multi-group case)
#   overlay_step1_darkness_legend()   results/nyan1308_all_families_labeled.r,
#                                     lines 1263-1290 (single-group case)
#   overlay_step1_wordhood()          results/nyan1308_all_families_labeled_wordhood.r,
#                                     lines 8-18 and 1128-1130 (hand edits; no generator)

overlay_step1_header_and_tree <- function() {
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
}

overlay_step1_label_layout <- function() {
alltreeplot69 <- alltreeplot69 + geom_tiplab(geom="label", size=6, angle=0,
  offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
  aes(label=paste(label, posLabel[label], sep="\n")), lineheight=1)

treelayout <- c(
  area(t=1, l=1, b=5, r=1))

forest <- (
  alltreeplot69 +
  plot_layout(design=treelayout))
ggsave("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis/../../results/nyan1308_all_families_labeled.pdf", forest & theme(plot.background=element_rect(fill='white', color=NA)), width=20, height=14)
}

overlay_step1_colour_legend <- function() {
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
}

overlay_step1_darkness_legend <- function() {
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
}

overlay_step1_wordhood <- function() {
# Orthographic-word highlighting: positions 5-19 (Neg1..Enc) in red, position
# 17 (FV, the final vowel) called out separately in blue -- not green, since
# red/green is exactly the pair a red-green colorblind reader can't tell
# apart. This blue (#0072B5) is the same one already used for "tonosegmental"
# in this project's pooled-plot palette (laminar_tree_counts.py's
# CLASS_COLORS), reused here rather than picking a new arbitrary color.
# Everything outside 5-19 keeps the default label color (black).
wordColor <- setNames(rep("black", 22), as.character(1:22))
wordColor[as.character(5:19)] <- "red"
wordColor["17"] <- "#0072B5"

alltreeplot69 <- alltreeplot69 + geom_tiplab(geom="label", size=6, angle=0,
  offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,
  aes(label=paste(label, posLabel[label], sep="\n"), colour=wordColor[label]),
  lineheight=1) +
  scale_colour_identity()
}
