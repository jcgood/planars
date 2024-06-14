# create test display result for chapters

setwd("C:/Users/Adan Tallman/Desktop/CCAmericas")

if (!require("pacman")) install.packages("pacman")
p_load(ggalt,
       ggsci,
       here,
       tidyverse,
       viridis)

# read in output files and metadata

metadata <- read_tsv("10_database/metadata.tsv")
domains <- read_tsv("10_database/cc_domains_output.tsv")
planar <- read_tsv("10_database/cc_planar_output.tsv")

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

# set up custom plot function for only one domain with nouns
constituency.noun.plot <- function(c, b, o){
  ggplot(c, aes(x = Edge, y = reorder(Test_Labels, desc(Layer)), label = Layer)) +
    scale_color_nejm() +
    geom_vline(xintercept = o, linetype = "dotted") +
    geom_line(linewidth=2) +
    labs(color = "Domain Type:") +
    geom_label(size = 4) +
    xlab("Positions on the nominal planar structure") +
    scale_x_continuous(breaks = seq(1, b, 1), limits = c(1, b)) +
    theme_bw() +
    theme(axis.title.y=element_blank(),
          legend.position="none",
          text = element_text(size = 15))
}

# function for getting max edge count
edge.max <- function(m){
    m %>%
    ungroup() %>%
    count(Edge) %>%
    arrange(desc(n)) %>%
    slice(1) %>%
    pull(n)
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
cup_tests <- filter(domains, Glottocode=="cent2127")
cup_tests_plot <- df.plot(cup_tests)

# pooled plot of verbal domain
# assing max number of tests and overlap position to variable
cup_o <- cup_tests_plot$Overlap_Verbal[1]
cup_b <- cup_tests_plot$Position_Total[1]
# make plot
cup_pooled_plot <- constituency.plot(cup_tests_plot, cup_b, cup_o)
cup_pooled_plot
ggsave(here("07_figures/cupik_pooled_plot.png"), cup_pooled_plot, device = "png", dpi = 600, width = 25, height = nrow(cup_tests_plot)/2.5, units = "cm")


# 02 - Cherokee
# subset data
cher_tests <- filter(domains, Glottocode=="cher1273")
# add Layer column; combine edges into one column with a separate one labeling the type of edge
cher_tests_plot <- df.plot(cher_tests)
glimpse(cher_tests_plot)

# pooled plot of verbal domain
# assing max number of tests and overlap position to variable
cher_o <- cher_tests_plot$Overlap_Verbal[1]
cher_b <- cher_tests_plot$Position_Total[1]
# make plot
cher_pooled_plot <- constituency.plot(cher_tests_plot, cher_b, cher_o)
cher_pooled_plot
ggsave("07_figures/cherokee_pooled_plot.png", cher_pooled_plot, device = "png", dpi = 600, width = 25, height = nrow(cher_tests_plot)/2.5, units = "cm")

# phonological tests only
cher_phon_tests <- filter(cher_tests, Domain_Type=="phonological") %>%
  df.plot(.)

cher_phon_plot <- constituency.onedomain.plot(cher_phon_tests, cher_b, cher_o)
cher_phon_plot
ggsave(here("07_figures/cherokee_phon_plot.png"), cher_phon_plot, device = "png", dpi = 600, width = 25, height = nrow(cher_phon_tests)/2.5, units = "cm")

# morphosyntactic tests only
cher_ms_tests <- filter(cher_tests, Domain_Type=="morphosyntactic") %>%
  df.plot(.)

cher_ms_plot <- constituency.onedomain.plot(cher_ms_tests, cher_b, cher_o)
cher_ms_plot
ggsave(here("07_figures/cherokee_ms_plot.png"), cher_ms_plot, device = "png", dpi = 600, width = 20, height = nrow(cher_ms_tests)/2.5, units = "cm")


# morphosyntactic +indeterminate tests only
cher_ms_mixed_tests <- filter(cher_tests, Domain_Type!="phonological") %>%
  df.plot(.)

cher_ms_mixed_plot <- constituency.onedomain.plot(cher_ms_mixed_tests, cher_b, cher_o)
cher_ms_mixed_plot
ggsave("07_figures/cherokee_ms_mixed_plot.png", cher_ms_mixed_plot, device = "png", dpi = 600, width = 20, height = nrow(cher_ms_mixed_tests)/2.5, units = "cm")

# plotting boundaries
# max of counts
cher_m <- edge.max(cher_tests_plot)
#plot
cher_edge_plot <- edge.plot(cher_tests_plot, cher_b, cher_m)
cher_edge_plot
ggsave(here("07_figures/cherokee_boundaries.png"), cher_edge_plot, device = "png", dpi = 600, width = 20, height = 10, units = "cm")


# 05 - Mazatec
# subset tests
maz_tests <- filter(domains, Glottocode=="ayau1235")
glimpse(maz_tests)

# variables and plot df
maz_tests_plot <- df.plot(maz_tests)
maz_b <- maz_tests_plot$Position_Total[1]
maz_o <- maz_tests_plot$Overlap_Verbal[1]

# pooled plot verbal domain
maz_pooled_plot <- constituency.plot(maz_tests_plot, maz_b, maz_o)
maz_pooled_plot
ggsave(here("07_figures/mazatec_pooled.png"), maz_pooled_plot, device = "png", dpi = 600, width = 25, height = nrow(maz_tests_plot)/2.5, units = "cm")

# phonological tests
maz_phon_tests <- filter(maz_tests, Domain_Type=="phonological") %>%
  df.plot(.)

maz_phon_plot <- constituency.onedomain.plot(maz_phon_tests, maz_b, maz_o)
maz_phon_plot
ggsave(here("07_figures/mazatec_phon_plot.png"), maz_phon_plot, device = "png", dpi = 600, width = 25, height = nrow(maz_phon_tests)/2.5, units = "cm")

# morphosyntactic tests
maz_ms_tests <- filter(maz_tests, Domain_Type=="morphosyntactic") %>%
  df.plot()

maz_ms_plot <- constituency.onedomain.plot(maz_ms_tests, maz_b, maz_o)
maz_ms_plot
ggsave(here("07_figures/mazatec_ms_plot.png"), maz_ms_plot, device = "png", dpi = 600, width = 25, height = nrow(maz_ms_tests)/2.5, units = "cm")

# plotting boundaries
maz_m <- edge.max(maz_tests_plot)
# plot
maz_edge_plot <- edge.plot(maz_tests_plot, maz_b, maz_m)
maz_edge_plot
ggsave(here("07_figures/mazatec_boundaries.png"), maz_edge_plot, device = "png", dpi = 600, width = 20, height = maz_m, units = "cm")


# 06 - Duraznos Mixtec
# subset tests
smd_tests <- filter(domains, Glottocode=="dura0000") %>%
  filter(Analysis_Type=="constituency") %>%
  filter(str_detect(Planar_ID, "verbal"))
glimpse(smd_tests)

# make plot df
smd_tests_plot <- df.plot(smd_tests)
# assign variables and make plot
smd_o <- smd_tests_plot$Overlap_Verbal[1]
smd_b <- smd_tests_plot$Position_Total[1]
smd_pooled_plot <- constituency.plot(smd_tests_plot, smd_b, smd_o)
smd_pooled_plot
# save plot
ggsave(here("07_figures/mixtec_pooled_plot.png"), smd_pooled_plot, device = "png", width = 25, height = nrow(smd_tests_plot)/2.5, units = "cm", dpi = 600)


# 07- Teotitlan dV Zapotec
# subset data - verbs
zap_tests_v <- filter(domains, Glottocode=="teot1238") %>%
  filter(str_detect(Planar_ID, "verbal"))
# add Layer column; combine edges into one column with a separate one labeling the type of edge
zap_verb_plot <- df.plot(zap_tests_v)
glimpse(zap_verb_plot)

# pooled plot of verbal domain
# assing max number of tests and overlap position to variable
zap_o <- zap_verb_plot$Overlap_Verbal[1]
zap_b <- zap_verb_plot$Position_Total[1]
# make plot
zap_pooled_plot <- constituency.plot(zap_verb_plot, zap_b, zap_o)
zap_pooled_plot
ggsave(here("07_figures/zapotec_verb_plot.png"), zap_pooled_plot, device = "png", dpi = 600, width = 25, height = nrow(zap_verb_plot)/2.5, units = "cm")

# phonological tests only
zap_phon_tests <- filter(zap_tests_v, Domain_Type=="phonological") %>%
  df.plot(.)

zap_phon_plot <- constituency.onedomain.plot(zap_phon_tests, zap_b, zap_o)
zap_phon_plot
ggsave(here("07_figures/zapotec_verb_phon.png"), zap_phon_plot, device = "png", dpi = 600, width = 25, height = nrow(zap_phon_tests)/2.5, units = "cm")

# morphosyntactic tests only
zap_ms_tests <- filter(zap_tests_v, Domain_Type=="morphosyntactic") %>%
  df.plot(.)

zap_ms_plot <- constituency.onedomain.plot(zap_ms_tests, zap_b, zap_o)
zap_ms_plot
ggsave(here("07_figures/zapotec_verb_ms.png"), zap_ms_plot, device = "png", dpi = 600, width = 20, height = nrow(zap_ms_tests)/2.5, units = "cm")

# morphosyntactic+indeterminate tests only (verb)
zap_ms_mixed_tests_v <- filter(zap_tests_v, Domain_Type!="phonological") %>%
  df.plot(.)

zap_ms_mixed_plot_v <- constituency.onedomain.plot(zap_ms_mixed_tests_v, zap_b, zap_o)
zap_ms_mixed_plot_v
ggsave(here("07_figures/zapotec_verb_ms_mixed.png"), zap_ms_mixed_plot_v, device = "png", dpi = 600, width = 20, height = nrow(zap_ms_mixed_tests_v)/2.5, units = "cm")


# plotting boundaries
# max of counts
zap_m <- edge.max(zap_verb_plot)
#plot
zap_edge_plot <- edge.plot(zap_verb_plot, zap_b, zap_m)
zap_edge_plot
ggsave(here("07_figures/zapotec_verb_edges.png"), zap_edge_plot, device = "png", dpi = 600, width = 20, height = zap_m, units = "cm")

# nouns
# subset data - nouns
zap_tests_n <- filter(domains, Glottocode=="teot1238") %>%
  filter(str_detect(Planar_ID, "nominal"))



# add Layer column; combine edges into one column with a separate one labeling the type of edge
zap_noun_plot <- df.plot(zap_tests_n)
glimpse(zap_noun_plot)
zap_o_n <- zap_noun_plot$Overlap_Nominal[1]
zap_b_n <- zap_noun_plot$Position_Total[1]


# make plot
zap_noun_pooled_plot <- constituency.noun.plot(zap_noun_plot, zap_b_n, zap_o_n)
zap_noun_pooled_plot
ggsave(here("07_figures/zapotec_noun_pooled_plot.png"), zap_noun_pooled_plot, device = "png", dpi = 600, width = 25, height = nrow(zap_noun_pooled_plot)/2.5, units = "cm")

# phonological tests only - nouns
zap_phon_tests_n <- filter(zap_tests_n, Domain_Type=="phonological") %>%
  df.plot(.)

zap_phon_plot_n <- constituency.noun.plot(zap_phon_tests_n, zap_b_n, zap_o_n)
zap_phon_plot_n
ggsave(here("07_figures/zapotec_noun_phon.png"), zap_phon_plot_n, device = "png", dpi = 600, width = 25, height = nrow(zap_phon_tests_n)/2.5, units = "cm")

# morphosyntactic tests only - nouns
zap_ms_tests_n <- filter(zap_tests_n, Domain_Type=="morphosyntactic") %>%
  df.plot(.)

zap_ms_plot_n <- constituency.noun.plot(zap_ms_tests_n, zap_b_n, zap_o_n)
zap_ms_plot_n
ggsave(here("07_figures/zapotec_noun_ms.png"), zap_ms_plot_n, device = "png", dpi = 600, width = 20, height = nrow(zap_ms_tests_n)/2.5, units = "cm")

# morphosyntactic + indeterminate tests only - nouns
zap_ms_mixed_tests_n <- filter(zap_tests_n, Domain_Type!="phonological") %>%
  df.plot(.)

zap_ms_mixed_plot_n <- constituency.noun.plot(zap_ms_mixed_tests_n, zap_b_n, zap_o_n)
zap_ms_mixed_plot_n
ggsave(here("07_figures/zapotec_noun_ms_mixed.png"), zap_ms_mixed_plot_n, device = "png", dpi = 600, width = 20, height = nrow(zap_ms_mixed_tests_n)/2.5, units = "cm")


# 11 - Yukuna
# subset data
yuc_tests <- filter(domains, Glottocode=="yucu1253")
# add Layer column; combine edges into one column with a separate one labeling the type of edge
yuc_tests_plot <- df.plot(yuc_tests)
glimpse(yuc_tests_plot)

# assing max number of tests and overlap position to variable
yuc_o <- yuc_tests_plot$Overlap_Verbal[1]
yuc_b <- yuc_tests_plot$Position_Total[1]

# pooled plot
# make plot df
yuc_tests_plot <- df.plot(yuc_tests)
# assign variables and make plot
yuc_pooled_plot <- constituency.plot(yuc_tests_plot, yuc_b, yuc_o)
yuc_pooled_plot
# save plot
ggsave(here("07_figures/yukuna_pooled_plot.png"), yuc_pooled_plot, device = "png", width = 25, height = nrow(yuc_tests_plot)/2.5, units = "cm", dpi = 600)

# phonological tests only
yuc_phon_tests <- filter(yuc_tests, Domain_Type=="phonological") %>%
  df.plot(.)

yuc_phon_plot <- constituency.onedomain.plot(yuc_phon_tests, yuc_b, yuc_o)
yuc_phon_plot
ggsave(here("07_figures/yukuna_phon_plot.png"), yuc_phon_plot, device = "png", dpi = 600, width = 25, height = nrow(yuc_phon_tests)/2.5, units = "cm")

# morphosyntactic tests only
yuc_ms_tests <- filter(yuc_tests, Domain_Type=="morphosyntactic") %>%
  df.plot(.)

yuc_ms_plot <- constituency.onedomain.plot(yuc_ms_tests, yuc_b, yuc_o)
yuc_ms_plot
ggsave(here("07_figures/yukuna_ms_plot.png"), yuc_ms_plot, device = "png", dpi = 600, width = 20, height = nrow(yuc_ms_tests)/2.5, units = "cm")

# max of counts
yuc_m <- edge.max(yuc_tests_plot)
#plot
yuc_edge_plot <- edge.plot(yuc_tests_plot, yuc_b, yuc_m)
yuc_edge_plot
ggsave(here("07_figures/yukuna_edges.png"), yuc_edge_plot, device = "png", dpi = 600, width = 20, height = yuc_m, units = "cm")


# 16 - Mocovi
# subset data
moc_tests <- filter(domains, Glottocode=="moco1246")
# add Layer column; combine edges into one column with a separate one labeling the type of edge
moc_tests_plot <- df.plot(moc_tests)
glimpse(moc_tests_plot)

# pooled plot of verbal domain
# assing max number of tests and overlap position to variable
moc_o <- moc_tests_plot$Overlap_Verbal[1]
moc_b <- moc_tests_plot$Position_Total[1]
# make plot
moc_pooled_plot <- constituency.plot(moc_tests_plot, moc_b, moc_o)
moc_pooled_plot
ggsave(here("07_figures/mocovi_pooled_plot.png"), moc_pooled_plot, device = "png", dpi = 600, width = 25, height = nrow(moc_tests_plot)/2.5, units = "cm")

# phonological tests only
moc_phon_tests <- filter(moc_tests, Domain_Type=="phonological") %>%
  df.plot(.)

moc_phon_plot <- constituency.onedomain.plot(moc_phon_tests, moc_b, moc_o)
moc_phon_plot
ggsave(here("07_figures/mocovi_phon_plot.png"), moc_phon_plot, device = "png", dpi = 600, width = 25, height = nrow(moc_phon_tests)/2.5, units = "cm")

# morphosyntactic tests only
moc_ms_tests <- filter(moc_tests, Domain_Type=="morphosyntactic") %>%
  df.plot(.)

moc_ms_plot <- constituency.onedomain.plot(moc_ms_tests, moc_b, moc_o)
moc_ms_plot
ggsave(here("07_figures/mocovi_ms_plot.png"), moc_ms_plot, device = "png", dpi = 600, width = 20, height = nrow(moc_ms_tests)/2.5, units = "cm")


# 10 - Hup
# subset data - verbal
hup_tests <- domains %>%
  filter(Glottocode=="hupd1244") %>%
  filter(str_detect(Planar_ID, "verbal"))
# add Layer column; combine edges into one column with a separate one labeling the type of edge
hup_tests_plot <- df.plot(hup_tests)
glimpse(hup_tests_plot)

# verbal plots
# pooled plot of verbal domain
# assing max number of tests and overlap position to variable
hup_o <- hup_tests_plot$Overlap_Verbal[1]
hup_b <- hup_tests_plot$Position_Total[1]
# make plot
hup_pooled_plot <- constituency.plot(hup_tests_plot, hup_b, hup_o)
hup_pooled_plot
ggsave(here("07_figures/hup_pooled_plot2.png"), hup_pooled_plot, device = "png", dpi = 600, width = 25, height = nrow(hup_tests_plot)/1.5, units = "cm")

# phonological tests only
hup_phon_tests <- filter(hup_tests, Domain_Type=="phonological") %>%
  df.plot()

hup_phon_plot <- constituency.onedomain.plot(hup_phon_tests, hup_b, hup_o)
hup_phon_plot
ggsave(here("07_figures/hup_phon_plot.png"), hup_phon_plot, device = "png", dpi = 600, width = 25, height = nrow(hup_phon_tests)/2.5, units = "cm")

# morphosyntactic tests only
hup_ms_tests <- filter(hup_tests, Domain_Type=="morphosyntactic") %>%
  df.plot()

hup_ms_plot <- constituency.onedomain.plot(hup_ms_tests, hup_b, hup_o)
hup_ms_plot
ggsave(here("07_figures/hup_ms_plot.png"), hup_ms_plot, device = "png", dpi = 600, width = 20, height = nrow(hup_ms_tests)/2.5, units = "cm")

# subset data - nominal
hup_tests_n <- domains %>%
  filter(Glottocode=="hupd1244") %>%
  filter(str_detect(Planar_ID, "nominal"))
# add Layer column; combine edges into one column with a separate one labeling the type of edge
hup_tests_plot_n <- df.plot(hup_tests_n)
glimpse(hup_tests_plot_n)

# verbal plots
# pooled plot of verbal domain
# assing max number of tests and overlap position to variable
hup_o_n <- hup_tests_plot_n$Overlap_Verbal[1]
hup_b_n <- hup_tests_plot_n$Position_Total[1]
# make plot
hup_pooled_plot_n <- constituency.plot(hup_tests_plot_n, hup_b_n, hup_o_n)
hup_pooled_plot_n
ggsave(here("07_figures/hup_pooled_nom_plot.png"), hup_pooled_plot_n, device = "png", dpi = 600, width = 25, height = nrow(hup_tests_plot)/2.5, units = "cm")

# phonological tests only
hup_phon_tests_n <- filter(hup_tests_n, Domain_Type=="phonological") %>%
  df.plot()

hup_phon_plot_n <- constituency.onedomain.plot(hup_phon_tests_n, hup_b_n, hup_o_n)
hup_phon_plot_n
ggsave(here("07_figures/hup_phon_nom_plot.png"), hup_phon_plot_n, device = "png", dpi = 600, width = 25, height = nrow(hup_phon_tests)/2.5, units = "cm")

# morphosyntactic tests only
hup_ms_tests_n <- filter(hup_tests_n, Domain_Type=="morphosyntactic") %>%
  df.plot()

hup_ms_plot_n <- constituency.onedomain.plot(hup_ms_tests_n, hup_b_n, hup_o_n)
hup_ms_plot_n
ggsave(here("07_figures/hup_ms_nom_plot.png"), hup_ms_plot_n, device = "png", dpi = 600, width = 20, height = nrow(hup_ms_tests)/2.5, units = "cm")


# South Bolivian Quechua -- FILES MISSING
# # read in custom test display
# sbq_tests = read_csv("05_data/sbqtestspooled.csv")
#
# # the tests are ordered corresponding to being pooled and the layer numbering is therefore different
#
# testspooled = read.csv("/Users/Adan Tallman/Desktop/quechuatestspooled.csv", header=TRUE)
#
# # library(lattice)
# # library(ggplot2)
# # library(grid)
# # library(egg)
# # library(dplyr)
# # library(rlist)
# # library(directlabels)
#
# tests <- filter(tests, Category =="verb")
#
# tests.left <- tests
# tests.right <- tests
# tests.left$Edge <- tests$Left.Edge
# tests.right$Edge <- tests$Right.Edge
#
# tests.left$Edge.type <- "Left"
# tests.right$Edge.type <- "Right"
#
# tests <- rbind(tests.left, tests.right)
# tests
#
# #Phonological vs. morphosyntactic tests
# fix(tests)
# ptests = filter(tests, Domain_Type=="Phonological")
# mstests =filter(tests, Domain_Type=="Morphosyntactic")
#
# #lock in the factor level orderso that ggplot doesn't reorder the factors alphabetically
# ptests$Constituency.test=with(ptests, reorder(Constituency.test, Layer.phon))
# mstests$Constituency.test=with(mstests, reorder(Constituency.test, Layer.ms))
# tests$Constituency.test=with(tests, reorder(Constituency.test, Layer.pooled))
#
# plabels = as.character(ptests$Layer.phon)
# mslabels = as.character(mstests$Layer.ms)
# pooledlabels = as.character(tests$Layer.pooled)
#
# #The stripplot with the labels on the edges
# p.plot= ggplot(ptests, aes(x=Edge,y=Constituency.test, label=plabels))+
#   geom_line()+
#   geom_label()+
#   xlab("Positions in the verbal planar structure")+ylab("Phonological constituent test results")+
#   scale_x_continuous(breaks = c(1,3,12,13,15,18,19,21,25,26,30,41,42))+
#   theme(axis.line = element_line(colour = "black"),
#         panel.grid.major = element_blank(),
#         panel.grid.minor = element_blank(),
#         panel.border = element_blank(),
#         panel.background = element_blank())
#
# ms.plot= ggplot(mstests, aes(x=Edge,y=Constituency.test, label=mslabels))+
#   geom_line()+
#   geom_label()+
#   xlab("Positions in the verbal planar structure")+ylab("Morphosyntactic constituent test results")+
#   scale_x_continuous(breaks = c(1,3,12,13,15,18,19,21,25,26,30,41,42))+
#   theme(axis.line = element_line(colour = "black"),
#         panel.grid.major = element_blank(),
#         panel.grid.minor = element_blank(),
#         panel.border = element_blank(),
#         panel.background = element_blank())
#
# pooled.plot = ggplot(tests, aes(x=Edge,y=Constituency.test, label=pooledlabels))+
#   geom_line()+
#   geom_label()+
#   xlab("Positions in the verbal planar structure")+ylab("Constituent test results pooled")+
#   scale_x_continuous(breaks = c(1,3,12,13,15,18,19,21,25,26,30,41,42))+
#   theme(axis.line = element_line(colour = "black"),
#         panel.grid.major = element_blank(),
#         panel.grid.minor = element_blank(),
#         panel.border = element_blank(),
#         panel.background = element_blank())
#
# #Here's the phonology plot
# phon.plot.fixed= set_panel_size(p.plot, width = unit(14, "cm"), height = unit(3, "in"))
# grid.newpage()
# grid.draw(phon.plot.fixed)
#
# #here's the morphosyntax plot
# morphsyn.plot.fixed= set_panel_size(ms.plot, width = unit(14, "cm"), height = unit(6, "in"))
# grid.newpage()
# grid.draw(morphsyn.plot.fixed)
#
# #Here's all the tests pooled
# pooled.plot.fixed= set_panel_size(pooled.plot, width = unit(14, "cm"), height = unit(6, "in"))
# grid.newpage()
# grid.draw(pooled.plot.fixed)
#
# ##Plotting boundaries
# testspooled <- tests
# testspooled$color <- ifelse(testspooled$Edge == 12 | testspooled$Edge ==30, T, F)
#
# ggplot(testspooled)+geom_histogram(aes(x=Edge, fill=color), bins=31)+
#   facet_grid(Edge.type~.)+coord_flip()+ scale_x_reverse()
#
# left <- subset(testspooled, Edge.type =="Left")
# right <- subset(testspooled, Edge.type =="Right")
# head(left)
#
# left$color <- ifelse(left$Edge == 5, T, F)
# right$color <- ifelse(right$Edge == 16, T, F)




