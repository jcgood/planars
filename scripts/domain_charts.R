# create test display result for chapters


if (!require("pacman")) install.packages("pacman")
p_load(ggsci,
       here,
       tidyverse)

# read in output files and metadata

#metadata <- read_tsv("metadata.tsv") # to be added later
domains <- read_tsv("/Users/jcgood/gitrepos/planars/domains/domains_nyan1308.tsv")


# set up function for setting up dataframe for plotting
# this code groups tests by domain types
# df.plot <- function(d){
#     d %>%
#    #group_by(Domain_Type, Size, Left_Edge) %>% # domain based ordering
#     group_by(desc(Size), Left_Edge) %>% # size based ordering
#     mutate(Layer = cur_group_id()) %>%
#     ungroup() %>% # reorder within Layer
#         group_by(Layer) %>%
#         arrange(Domain_Type, .by_group = TRUE) %>%
#         ungroup() %>%
#     pivot_longer(Left_Edge:Right_Edge, names_to = "Edge_Type", values_to = "Edge")
# }

# Creates a plot interleaving the tests from different domains, ordering in a sensible way
df.plot <- function(d){

  # Add a Layer column in the right order
  d <- d %>%
    mutate(Domain_Type = factor(Domain_Type, levels = c(
      "morphosyntactic", "tonosegmental", "length", "phonological", "intonational"
    ))) %>%
    arrange(desc(Size), Left_Edge) %>%
    group_by(Size, Left_Edge) %>%
    mutate(Layer = cur_group_id()) %>%
    ungroup()

  # Explicitly sort by Layer (ascending), Domain_Type, Left_Edge
  d <- d %>%
    arrange(Layer, Domain_Type, Left_Edge, Test_Labels)

  # Create factor levels for Test_Labels in the correct order
  d <- d %>%
    mutate(Test_Labels = factor(Test_Labels, levels = unique(Test_Labels)))

  # Expand the table to include two rows for each test, one left edge and one right edge
  d <- d %>%
    pivot_longer(Left_Edge:Right_Edge, names_to = "Edge_Type", values_to = "Edge")

  return(d)
 
 }

# colors are NEJM options.
#nejm_colors <- pal_nejm("default")(5)
#print(nejm_colors)

group.colors <- c(morphosyntactic = "#BC3C29", tonosegmental = "#0072B5", length ="#E18727", phonological = "#20845E", intonational = "#7876B1")

# Adapted plot function to get the ordering as wanted; note use of ReverseLayer label (see below)
constituency.plot <- function(c, b, o){
  ggplot(c, aes(x = Edge,
  y = reorder(Test_Labels, desc(Size*100 + as.numeric(Layer))), label = ReverseLayer)) +
  #y = reorder(Test_Labels, Layer), label = Layer)) +
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
        legend.justification = c(0,-.2),
        text = element_text(size = 15),
        panel.grid.minor = element_blank()
        )
	}


tests <- filter(domains) # vacuous at the moment
tests <- tests %>% filter(!startsWith(Test_Labels, "#")) # get rid of commented tests

# Plotify the dataframe
tests_plot <- df.plot(tests)

# After a lot of experimentation, to get the Layer numbering the way I wanted it, the best option was to reverse the output of the above functions
layer_levels <- sort(unique(tests_plot$Layer))
reverse_map <- setNames(rev(layer_levels), layer_levels)
tests_plot <- tests_plot %>%
  mutate(ReverseLayer = reverse_map[as.character(Layer)])
  

# Note using now, for different classes of tests 
tests_length <- filter(domains, Domain_Type == "length")
tests_plot_length <- df.plot(tests_length)

tests_morphosyntactic <- filter(domains, Domain_Type == "morphosyntactic")
tests_plot_morphosyntactic <- df.plot(tests_morphosyntactic)

tests_phonological <- filter(domains, Domain_Type == "phonological")
tests_plot_phonological <- df.plot(tests_phonological)

tests_tonosegmental <- filter(domains, Domain_Type == "tonosegmental")
tests_plot_tonosegmental <- df.plot(tests_tonosegmental)

tests_intonational <- filter(domains, Domain_Type == "intonational")
tests_plot_intonational <- df.plot(tests_tonosegmental)


# make the pooled plot of verbal domain
# adding max number of tests and overlap position to variable
o <- 10 # hard code position of root
b <- 22 # hard code number of positions


# make plots
pooled_plot <- constituency.plot(tests_plot, b, o)
ggsave(here("chichewa_pooled_plot.pdf"), pooled_plot, device = "pdf", width = 26, height = nrow(tests_plot)/4, units = "cm")


# These may not work now due to changes made above. They'd all need ReverseLayer, for example
pooled_plot_length <- constituency.plot(tests_plot_length, b, o)
#ggsave(here("chichewa_pooled_plot_length.pdf"), pooled_plot_length, device = "pdf", width = 25, height = nrow(tests_plot)/8, units = "cm")

pooled_plot_morphosyntactic <- constituency.plot(tests_plot_morphosyntactic, b, o)
#ggsave(here("chichewa_pooled_plot_morphosyntactic.pdf"), pooled_plot_morphosyntactic, device = "pdf", width = 25, height = nrow(tests_plot)/8, units = "cm")

pooled_plot_phonological <- constituency.plot(tests_plot_phonological, b, o)
#ggsave(here("chichewa_pooled_plot_phonological.pdf"), pooled_plot_phonological, device = "pdf", width = 25, height = nrow(tests_plot)/8, units = "cm")

pooled_plot_tonosegmental <- constituency.plot(tests_plot_tonosegmental, b, o)
#ggsave(here("chichewa_pooled_plot_tonosegmental.pdf"), pooled_plot_tonosegmental, device = "pdf", width = 25, height = nrow(tests_plot)/8, units = "cm")
#ggsave(here("chichewa_pooled_plot.pdf"), pooled_plot, device = "pdf", width = 26, height = nrow(tests_plot)/4, units = "cm")

pooled_plot_intonational <- constituency.plot(tests_plot_intonational, b, o)

# why does this repeat?
pooled_plot_length <- constituency.plot(tests_plot_length, b, o)
#ggsave(here("chichewa_pooled_plot_length.pdf"), pooled_plot_length, device = "pdf", width = 25, height = nrow(tests_plot)/8, units = "cm")

pooled_plot_morphosyntactic <- constituency.plot(tests_plot_morphosyntactic, b, o)
#ggsave(here("chichewa_pooled_plot_morphosyntactic.pdf"), pooled_plot_morphosyntactic, device = "pdf", width = 25, height = nrow(tests_plot)/8, units = "cm")

pooled_plot_phonological <- constituency.plot(tests_plot_phonological, b, o)
#ggsave(here("chichewa_pooled_plot_phonological.pdf"), pooled_plot_phonological, device = "pdf", width = 25, height = nrow(tests_plot)/8, units = "cm")

pooled_plot_tonosegmental <- constituency.plot(tests_plot_tonosegmental, b, o)
#ggsave(here("chichewa_pooled_plot_tonosegmental.pdf"), pooled_plot_tonosegmental, device = "pdf", width = 25, height = nrow(tests_plot)/8, units = "cm")
