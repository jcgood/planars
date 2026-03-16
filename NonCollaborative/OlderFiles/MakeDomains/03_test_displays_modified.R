# create test display result for chapters


if (!require("pacman")) install.packages("pacman")
p_load(ggsci,
       here,
       tidyverse)

# read in output files and metadata

metadata <- read_tsv("metadata.tsv")
domains <- read_tsv("cc_domains_output.tsv")
planar <- read_tsv("cc_planar_output.tsv")

# set up function for setting up dataframe for plotting
df.plot <- function(d){
    d %>%
    group_by(Domain_Type, Size, Left_Edge) %>%
    mutate(Layer = cur_group_id()) %>%
    pivot_longer(Left_Edge:Right_Edge, names_to = "Edge_Type", values_to = "Edge")
}


group.colors <- c(length = "#BC3C29", morphosyntactic = "#0072B5", phonological ="#E18727", tonosegmental = "#20845E")


# set up custom plot function
constituency.plot <- function(c, b, o){
  ggplot(c, aes(x = Edge, y = reorder(Test_Labels, desc(Layer)), label = Layer)) +
  scale_color_manual(values=group.colors) + 
  geom_vline(xintercept = o, linetype = "dotted") +
  geom_line(aes(color = Domain_Type), linewidth=2) +
  labs(color = "Domain Type:") +
  geom_label(aes(color = Domain_Type), size = 3, label.padding = unit(0.2, "lines"), show.legend=FALSE) +
  xlab("Positions on the verbal planar structure") +
  scale_x_continuous(breaks = seq(1, b, 1), limits = c(1, b)) +
  theme_bw() +
  theme(axis.title.y=element_blank(),
        legend.direction = "horizontal",
        legend.position="top",
        text = element_text(size = 15),
        panel.grid.minor = element_blank()
        )
}



cup_tests <- filter(domains)
cup_tests_plot <- df.plot(cup_tests)

cup_tests_length <- filter(domains, Domain_Type == "length")
cup_tests_plot_length <- df.plot(cup_tests_length)

cup_tests_morphosyntactic <- filter(domains, Domain_Type == "morphosyntactic")
cup_tests_plot_morphosyntactic <- df.plot(cup_tests_morphosyntactic)

cup_tests_phonological <- filter(domains, Domain_Type == "phonological")
cup_tests_plot_phonological <- df.plot(cup_tests_phonological)

cup_tests_tonosegmental <- filter(domains, Domain_Type == "tonosegmental")
cup_tests_plot_tonosegmental <- df.plot(cup_tests_tonosegmental)



# pooled plot of verbal domain
# assing max number of tests and overlap position to variable
cup_o <- 8 # hard code position of root
cup_b <- 20 # hard code number of positions

# make plots
cup_pooled_plot <- constituency.plot(cup_tests_plot, cup_b, cup_o)
ggsave(here("chichewa_pooled_plot.pdf"), cup_pooled_plot, device = "pdf", width = 26, height = nrow(cup_tests_plot)/4, units = "cm")

cup_pooled_plot_length <- constituency.plot(cup_tests_plot_length, cup_b, cup_o)
ggsave(here("chichewa_pooled_plot_length.pdf"), cup_pooled_plot_length, device = "pdf", width = 25, height = nrow(cup_tests_plot)/8, units = "cm")

cup_pooled_plot_morphosyntactic <- constituency.plot(cup_tests_plot_morphosyntactic, cup_b, cup_o)
ggsave(here("chichewa_pooled_plot_morphosyntactic.pdf"), cup_pooled_plot_morphosyntactic, device = "pdf", width = 25, height = nrow(cup_tests_plot)/8, units = "cm")

cup_pooled_plot_phonological <- constituency.plot(cup_tests_plot_phonological, cup_b, cup_o)
ggsave(here("chichewa_pooled_plot_phonological.pdf"), cup_pooled_plot_phonological, device = "pdf", width = 25, height = nrow(cup_tests_plot)/8, units = "cm")


cup_pooled_plot_tonosegmental <- constituency.plot(cup_tests_plot_tonosegmental, cup_b, cup_o)
ggsave(here("chichewa_pooled_plot_tonosegmental.pdf"), cup_pooled_plot_tonosegmental, device = "pdf", width = 25, height = nrow(cup_tests_plot)/8, units = "cm")
