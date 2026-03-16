# create test display result for chapters

#setwd("C:/Users/Adan Tallman/Desktop/CCAmericas")

if (!require("pacman")) install.packages("pacman")
p_load(ggalt,
       ggsci,
       here,
       tidyverse,
       viridis)

# read in output files and metadata

metadata <- read_tsv("metadata.tsv")
domains <- read_tsv("cc_domains_output.tsv")
planar <- read_tsv("cc_planar_output.tsv")

# set up function for setting up dataframe for plotting
df.plot <- function(d){
    d %>%
    group_by(Size, Left_Edge) %>%
    mutate(Layer = cur_group_id()) %>%
    pivot_longer(Left_Edge:Right_Edge, names_to = "Edge_Type", values_to = "Edge")
}

# set up custom plot function
constituency.plot <- function(c, b, o){
  ggplot(c, aes(x = Edge, y = reorder(Test_Labels, desc(Layer)), label = Layer)) +
  geom_vline(xintercept = o, linetype = "dotted") +
  scale_color_nejm() +
  geom_line(aes(color = Domain_Type), linewidth=2) +
  labs(color = "Domain Type:") +
  geom_label(aes(color = Domain_Type), size = 4, show.legend=FALSE) +
  xlab("Positions on the verbal planar structure") +
  scale_x_continuous(breaks = seq(1, b, 1), limits = c(1, b)) +
  theme_bw() +
  theme(axis.title.y=element_blank(),
        legend.direction = "horizontal",
        legend.position="top",
        text = element_text(size = 15))
}

# set up custom plot function for only one domain
constituency.onedomain.plot <- function(c, b, o){
  ggplot(c, aes(x = Edge, y = reorder(Test_Labels, desc(Layer)), label = Layer)) +
    scale_color_nejm() +
    geom_vline(xintercept = o, linetype = "dotted") +
    geom_line(linewidth=2) +
    labs(color = "Domain Type:") +
    geom_label(size = 4) +
    xlab("Positions on the verbal planar structure") +
    scale_x_continuous(breaks = seq(1, b, 1), limits = c(1, b)) +
    theme_bw() +
    theme(axis.title.y=element_blank(),
          legend.position="none",
          text = element_text(size = 15))
}




# set up function for plotting edge counts
edge.plot <- function(e, b, m){
    ggplot(e) +
    geom_histogram(aes(x=Edge, fill=Edge_Type), bins=24) +
    scale_y_continuous(breaks = seq(0, m, 1)) +
    scale_x_continuous(breaks = seq(1, b, 1)) +
    scale_fill_manual(values = c("darkgreen", "purple4")) +
    theme_bw() +
    theme(legend.position = "top",
          legend.title = element_blank(),
          text = element_text(size = 12))
}

# 01 - Cupik
cup_tests <- filter(domains)
cup_tests_plot <- df.plot(cup_tests)

# pooled plot of verbal domain
# assing max number of tests and overlap position to variable
cup_o <- cup_tests_plot$Overlap_Verbal[1]
cup_b <- cup_tests_plot$Position_Total[1]
# make plot
cup_pooled_plot <- constituency.plot(cup_tests_plot, cup_b)
cup_pooled_plot
ggsave(here("07_figures/cupik_pooled_plot.png"), cup_pooled_plot, device = "png", dpi = 600, width = 25, height = nrow(cup_tests_plot)/2.5, units = "cm")



