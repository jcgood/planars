# create test display result for chapters


if (!require("pacman")) install.packages("pacman")
p_load(ggsci,
       here,
       tidyverse)

# read in output files and metadata

#metadata <- read_tsv("metadata.tsv") # to be added later
domains <- read_tsv("../planar_tables/domains_nyan1308.tsv")
#planar <- read_tsv("../planars/planar_nyan1308.tsv")

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



tests <- filter(domains) # vacuous at the moment
tests_plot <- df.plot(tests)

tests_length <- filter(domains, Domain_Type == "length")
tests_plot_length <- df.plot(tests_length)

tests_morphosyntactic <- filter(domains, Domain_Type == "morphosyntactic")
tests_plot_morphosyntactic <- df.plot(tests_morphosyntactic)

tests_phonological <- filter(domains, Domain_Type == "phonological")
tests_plot_phonological <- df.plot(tests_phonological)

tests_tonosegmental <- filter(domains, Domain_Type == "tonosegmental")
tests_plot_tonosegmental <- df.plot(tests_tonosegmental)



# pooled plot of verbal domain
# assing max number of tests and overlap position to variable
o <- 8 # hard code position of root
b <- 20 # hard code number of positions

# make plots
pooled_plot <- constituency.plot(tests_plot, b, o)
#ggsave(here("chichewa_pooled_plot.pdf"), pooled_plot, device = "pdf", width = 26, height = nrow(tests_plot)/4, units = "cm")

pooled_plot_length <- constituency.plot(tests_plot_length, b, o)
#ggsave(here("chichewa_pooled_plot_length.pdf"), pooled_plot_length, device = "pdf", width = 25, height = nrow(tests_plot)/8, units = "cm")

pooled_plot_morphosyntactic <- constituency.plot(tests_plot_morphosyntactic, b, o)
#ggsave(here("chichewa_pooled_plot_morphosyntactic.pdf"), pooled_plot_morphosyntactic, device = "pdf", width = 25, height = nrow(tests_plot)/8, units = "cm")

pooled_plot_phonological <- constituency.plot(tests_plot_phonological, b, o)
#ggsave(here("chichewa_pooled_plot_phonological.pdf"), pooled_plot_phonological, device = "pdf", width = 25, height = nrow(tests_plot)/8, units = "cm")


pooled_plot_tonosegmental <- constituency.plot(tests_plot_tonosegmental, b, o)
#ggsave(here("chichewa_pooled_plot_tonosegmental.pdf"), pooled_plot_tonosegmental, device = "pdf", width = 25, height = nrow(tests_plot)/8, units = "cm")
