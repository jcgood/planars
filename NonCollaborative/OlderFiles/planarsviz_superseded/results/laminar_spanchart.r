library(ggplot2)

pos_labels_vec <- c("QM", "PreSbj", "Sbj", "PostSbj", "Neg1", "SM", "Neg2", "TAM", "OM", "Root", "Ext", "STAT", "CAUS", "APPL", "REC", "PASS", "FV", "2P", "Enc", "Obj1", "Obj2", "PostObj")

span_data <- data.frame(
  left        = c(10, 6, 5, 8, 10, 9, 8, 6, 17, 8, 10, 6, 5, 6, 9, 9, 9, 5, 10, 13, 5, 5, 2, 5, 3),
  right       = c(18, 10, 13, 10, 17, 18, 17, 16, 19, 16, 13, 17, 6, 8, 17, 10, 16, 17, 16, 15, 18, 21, 22, 19, 21),
  freq        = c(4, 8, 10, 11, 14, 14, 18, 18, 18, 20, 23, 23, 24, 24, 25, 27, 36, 37, 38, 40, 51, 69, 69, 69, 69),
  freq_scaled = c(0.057971, 0.115942, 0.144928, 0.15942, 0.202899, 0.202899, 0.26087, 0.26087, 0.26087, 0.289855, 0.333333, 0.333333, 0.347826, 0.347826, 0.362319, 0.391304, 0.521739, 0.536232, 0.550725, 0.57971, 0.73913, 1.0, 1.0, 1.0, 1.0),
  domain      = c("length/morphosyntactic", "phonological/tonosegmental", "morphosyntactic", "tonosegmental", "length/morphosyntactic/phonological", "length/morphosyntactic", "tonosegmental", "tonosegmental", "phonological", "tonosegmental", "phonological", "intonational/phonological/tonosegmental", "phonological", "phonological/tonosegmental", "length/phonological/tonosegmental", "tonosegmental", "tonosegmental", "length/morphosyntactic/tonosegmental", "phonological", "morphosyntactic", "length/morphosyntactic", "morphosyntactic/phonological", "intonational", "morphosyntactic", "phonological"),
  color       = c("#EE6677", "#4477AA", "#EE6677", "#228833", "#EE6677", "#EE6677", "#228833", "#228833", "#4477AA", "#228833", "#4477AA", "#4477AA", "#4477AA", "#4477AA", "#4477AA", "#228833", "#228833", "#EE6677", "#4477AA", "#EE6677", "#EE6677", "#EE6677", "#CCBB44", "#EE6677", "#4477AA"),
  lw          = c(0.7899, 1.0797, 1.2246, 1.2971, 1.5145, 1.5145, 1.8043, 1.8043, 1.8043, 1.9493, 2.1667, 2.1667, 2.2391, 2.2391, 2.3116, 2.4565, 3.1087, 3.1812, 3.2536, 3.3985, 4.1956, 5.5, 5.5, 5.5, 5.5),
  label       = c("[10-18] 4/69", "[6-10] 8/69", "[5-13] 10/69", "[8-10] 11/69", "[10-17] 14/69", "[9-18] 14/69", "[8-17] 18/69", "[6-16] 18/69", "[17-19] 18/69", "[8-16] 20/69", "[10-13] 23/69", "[6-17] 23/69", "[5-6] 24/69", "[6-8] 24/69", "[9-17] 25/69", "[9-10] 27/69", "[9-16] 36/69", "[5-17] 37/69", "[10-16] 38/69", "[13-15] 40/69", "[5-18] 51/69", "[5-21] 69/69", "[2-22] 69/69", "[5-19] 69/69", "[3-21] 69/69"),
  y_rank      = c(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25)
)

p_spanchart <- ggplot(span_data) +
  geom_segment(aes(x=left, xend=right, y=y_rank, yend=y_rank,
    color=color, alpha=freq_scaled, linewidth=lw)) +
  geom_text(aes(x=(left+right)/2, y=y_rank+0.45, label=label),
    size=2.8, hjust=0.5) +
  scale_color_identity(guide='none') +
  scale_alpha_continuous(range=c(0.15, 1.0),
    name='Proportion of 69 families') +
  scale_linewidth_identity() +
  scale_x_continuous(breaks=1:22,
    labels=pos_labels_vec, name='Position',
    expand=expansion(add=0.5)) +
  scale_y_continuous(name='', breaks=NULL) +
  theme_minimal() +
  theme(panel.grid.major.y=element_blank(),
    axis.text.x=element_text(angle=90, vjust=0.5, hjust=1)) +
  ggtitle('69 maximal families: span frequencies')

ggsave('/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/../results/nyan1308_spanchart.pdf', p_spanchart, width=14, height=8)
