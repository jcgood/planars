# create test display result for chapters

if (!requireNamespace("pacman", quietly = TRUE)) install.packages("pacman")
pacman::p_load(ggsci, here, tidyverse)

# ---- data in ----
# metadata <- read_tsv("metadata.tsv") # to be added later
# Prefer project-relative path:
domains <- read_tsv("/Users/jcgood/gitrepos/planars/domains/domains_nyan1308.tsv")

# ---- helpers ----

# Ensures test rows become two edges (L/R) and layers are computed consistently
df.plot <- function(d){
  d <- d %>%
    mutate(
      Domain_Type = factor(
        Domain_Type,
        levels = c("morphosyntactic", "tonosegmental", "length", "phonological", "intonational")
      )
    ) %>%
    arrange(desc(Size), Left_Edge) %>%
    group_by(Size, Left_Edge) %>%              # group for layer IDs
    mutate(Layer = cur_group_id()) %>%
    ungroup() %>%
    arrange(Layer, Domain_Type, Left_Edge, Test_Labels) %>%
    mutate(Test_Labels = factor(Test_Labels, levels = unique(Test_Labels))) %>%
    pivot_longer(Left_Edge:Right_Edge, names_to = "Edge_Type", values_to = "Edge")

  # Provide Reverse_Layer universally so any subset will work with constituency.plot()
  max_layer <- max(d$Layer, na.rm = TRUE)
  d <- d %>% mutate(Reverse_Layer = max_layer + 1 - Layer)
  d
}

# Domain-focused version; remove desc() from group_by
df.domain.plot <- function(d){
  d <- d %>%
    mutate(
      Domain_Type = factor(
        Domain_Type,
        levels = c("morphosyntactic", "tonosegmental", "length", "phonological", "intonational")
      )
    ) %>%
    group_by(Domain_Type, Size, Left_Edge) %>%
    mutate(Layer = cur_group_id()) %>%
    ungroup() %>%
    arrange(desc(Size), Left_Edge) %>%
    group_by(Size, Left_Edge) %>%
    mutate(Domain_Layer = cur_group_id()) %>%
    ungroup() %>%
    pivot_longer(Left_Edge:Right_Edge, names_to = "Edge_Type", values_to = "Edge")

  # Provide Reverse_Domain_Layer universally
  max_dlayer <- max(d$Domain_Layer, na.rm = TRUE)
  d <- d %>% mutate(Reverse_Domain_Layer = max_dlayer + 1 - Domain_Layer)
  d
}

group.colors <- c(
  morphosyntactic = "#BC3C29",
  tonosegmental   = "#0072B5",
  length          = "#E18727",
  phonological    = "#20845E",
  intonational    = "#7876B1"
)

constituency.plot <- function(c, b, o){
  ggplot(c, aes(
    x = Edge,
    y = reorder(Test_Labels, desc(Size*100 + as.numeric(Layer))),
    label = Reverse_Layer
  )) +
    geom_vline(xintercept = o, linetype = "dotted") +
    geom_line(aes(color = Domain_Type), linewidth = 2) +
    labs(color = "Domain Type:") +
    geom_label(
      aes(color = Domain_Type),
      size = 3, label.padding = unit(0.2, "lines"),
      show.legend = FALSE
    ) +
    xlab("Positions on the verbal planar structure") +
    scale_x_continuous(breaks = seq(1, b, 1), limits = c(1, b)) +
    
    # Custom legend order
    scale_color_manual(
      values = group.colors,
      breaks = c(
        "morphosyntactic",
        "phonological",
        "length",
        "intonational",
        "tonosegmental"
      )
    ) +

    theme_bw() +
    theme(
      axis.title.y = element_blank(),
      legend.direction = "horizontal",
      legend.position = "top",
      legend.justification = c(1.25, 0),
      text = element_text(size = 15),
      panel.grid.minor = element_blank()
    )
}


constituency.domain.plot <- function(c, b, o){
  ggplot(c, aes(
    x = Edge,
    y = reorder(Test_Labels, Layer),
    label = Reverse_Domain_Layer
  )) +
    geom_vline(xintercept = o, linetype = "dotted") +
    geom_line(aes(color = Domain_Type), linewidth = 2) +
    labs(color = "Domain Type:") +
    geom_label(
      aes(color = Domain_Type),
      size = 3, label.padding = unit(0.2, "lines"),
      show.legend = FALSE
    ) +
    xlab("Positions on the verbal planar structure") +
    scale_x_continuous(breaks = seq(1, b, 1), limits = c(1, b)) +
    
    # Custom legend order
    scale_color_manual(
      values = group.colors,
      breaks = c(
        "morphosyntactic",
        "phonological",
        "length",
        "intonational",
        "tonosegmental"
      )
    ) +

    theme_bw() +
    theme(
      axis.title.y = element_blank(),
      legend.direction = "horizontal",
      legend.position = "top",
      legend.justification = c(1.25, 0),
      text = element_text(size = 15),
      panel.grid.minor = element_blank()
    )
}

# ---- prepare data ----

tests <- domains %>% 
  filter(!startsWith(Test_Labels, "#"))

# Pooled tables
tests_plot        <- df.plot(tests)
tests_domainsplot <- df.domain.plot(tests)

# Per-domain subsets (each inherits Reverse_Layer from df.plot())
tests_plot_length          <- df.plot(filter(domains, Domain_Type == "length"))
tests_plot_morphosyntactic <- df.plot(filter(domains, Domain_Type == "morphosyntactic"))
tests_plot_phonological    <- df.plot(filter(domains, Domain_Type == "phonological"))
tests_plot_tonosegmental   <- df.plot(filter(domains, Domain_Type == "tonosegmental"))
tests_plot_intonational    <- df.plot(filter(domains, Domain_Type == "intonational"))

# ---- params ----
o <- 10 # position of root
b <- 22 # number of positions

# ---- plots ----
pooled_plot        <- constituency.plot(tests_plot, b, o)
pooled_domainplot  <- constituency.domain.plot(tests_domainsplot, b, o)

pooled_plot_length          <- constituency.plot(tests_plot_length, b, o)
pooled_plot_morphosyntactic <- constituency.plot(tests_plot_morphosyntactic, b, o)
pooled_plot_phonological    <- constituency.plot(tests_plot_phonological, b, o)
pooled_plot_tonosegmental   <- constituency.plot(tests_plot_tonosegmental, b, o)
pooled_plot_intonational    <- constituency.plot(tests_plot_intonational, b, o)

ggsave("/Users/jcgood/Library/CloudStorage/Box-Box/PresentationsAndAbstracts/Constituency/ChichewaPaper/chichewa_pooled_plot.pdf", pooled_plot, device = "pdf", width = 26, height = nrow(tests_plot)/5, units = "cm")


# ---- counts ----
domain_summary <- tests %>%
  mutate(Domain = paste0(Left_Edge, "–", Right_Edge)) %>%
  count(Domain, Left_Edge, Right_Edge, name = "Count") %>%
  arrange(desc(Count))
print(domain_summary)

# Example saves (relative paths)
# ggsave(here::here("figs", "chichewa_pooled_plot.pdf"), pooled_plot,
#        width = 26, height = nrow(tests_plot)/5, units = "cm")
