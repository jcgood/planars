# Boundary charts (charts 5, 17, 18 in docs/PLAN_planarsviz_library.md).
#
# STEP 1 COPY (chart 5): everything below the header is copied verbatim from
# scripts/nyan_boundary_skyline.r, lines 1-129, at commit 43a308f, wrapped in
# a function body so sourcing the package doesn't run it. No other edits.
# Literals are replaced with bundle data in the next commit.

skyline_step1_copy <- function() {
# Boundary-frequency skyline for the nyan1308 domain file.
#
# Each active test contributes two observations: where its span starts and
# where it ends.  The resulting chart shows the empirical distribution of
# boundary points, both pooled across tests and split by domain type.

library(ggplot2)
library(patchwork)

# Paths are relative to this script's own location (scripts/), per the
# convention documented in NonCollaborative/CLAUDE.md: run from the script's
# directory, or adjust as needed.
input_file <- "../domains/domains_nyan1308.tsv"
output_dir <- "../results"

position_labels <- c(
  "QM", "PreSbj", "Sbj", "PostSbj", "Neg1", "SM", "Neg2", "TAM",
  "OM", "Root", "Ext", "STAT", "CAUS", "APPL", "REC", "PASS",
  "FV", "2P", "Enc", "Obj1", "Obj2", "PostObj"
)

domains <- read.delim(input_file, stringsAsFactors = FALSE, check.names = FALSE)
domains <- domains[!grepl("^#", domains$Test_Labels), ]
domains$Left_Edge <- as.integer(domains$Left_Edge)
domains$Right_Edge <- as.integer(domains$Right_Edge)

boundary_data <- rbind(
  data.frame(
    Position = domains$Left_Edge,
    Boundary = "Start",
    Domain_Type = domains$Domain_Type
  ),
  data.frame(
    Position = domains$Right_Edge,
    Boundary = "End",
    Domain_Type = domains$Domain_Type
  )
)

boundary_data$Position <- factor(boundary_data$Position, levels = 1:22)
boundary_data$Boundary <- factor(boundary_data$Boundary, levels = c("Start", "End"))
boundary_data$Domain_Type <- factor(
  boundary_data$Domain_Type,
  levels = c("morphosyntactic", "phonological", "tonosegmental", "intonational", "length")
)

counts <- as.data.frame(table(
  Position = boundary_data$Position,
  Boundary = boundary_data$Boundary,
  Domain_Type = boundary_data$Domain_Type
))
names(counts)[names(counts) == "Freq"] <- "Count"
counts <- counts[counts$Count > 0, ]
write.table(
  counts,
  file.path(output_dir, "nyan1308_boundary_counts.tsv"),
  sep = "\t", row.names = FALSE, quote = FALSE
)

boundary_colors <- c(Start = "#D55E00", End = "#0072B2")
type_colors <- c(
  morphosyntactic = "#CC6677",
  phonological = "#4477AA",
  tonosegmental = "#228833",
  intonational = "#CCBB44",
  length = "#AA4499"
)

axis_theme <- theme(
  axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1),
  axis.title.y = element_text(margin = margin(r = 8)),
  panel.grid.minor = element_blank()
)

all_counts <- as.data.frame(table(
  Position = boundary_data$Position,
  Boundary = boundary_data$Boundary
))
names(all_counts)[names(all_counts) == "Freq"] <- "Count"

p_all <- ggplot(all_counts, aes(x = Position, y = Count, fill = Boundary)) +
  geom_col(position = "dodge", width = 0.82, color = "white", linewidth = 0.2) +
  scale_fill_manual(values = boundary_colors) +
  scale_x_discrete(labels = position_labels, drop = FALSE) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.08)), breaks = scales::pretty_breaks(5)) +
  labs(
    title = "All active tests",
    x = "Planar position",
    y = "Number of tests",
    fill = "Boundary"
  ) +
  theme_bw(base_size = 11) +
  axis_theme +
  theme(legend.position = "top")

p_by_type <- ggplot(counts, aes(x = Position, y = Count, fill = Boundary)) +
  geom_col(position = "dodge", width = 0.82, color = "white", linewidth = 0.2) +
  facet_grid(Boundary ~ Domain_Type, scales = "free_y") +
  scale_fill_manual(values = boundary_colors, drop = FALSE) +
  scale_x_discrete(labels = position_labels, drop = FALSE) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.08)), breaks = scales::pretty_breaks(5)) +
  labs(
    x = "Planar position",
    y = "Number of tests",
    fill = "Boundary"
  ) +
  theme_bw(base_size = 11) +
  theme(
    strip.background = element_rect(fill = "grey92", color = "grey60"),
    panel.grid.minor = element_blank(),
    axis.text.x = element_blank(),
    axis.title.x = element_blank(),
    legend.position = "none"
  )

p <- p_all / p_by_type +
  plot_layout(heights = c(1, 1.7)) +
  plot_annotation(
    title = "Chichewa (nyan1308): distribution of span boundaries",
    subtitle = paste0(
      nrow(domains), " active tests; each test contributes one start and one end boundary. ",
      "Bars show counts at each planar position."
    )
  )

ggsave(
  file.path(output_dir, "nyan1308_boundary_skyline.pdf"),
  p, device = "pdf", width = 16, height = 11, units = "in"
)
}
