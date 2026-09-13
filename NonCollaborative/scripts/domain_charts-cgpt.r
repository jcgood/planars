# create test display result for chapters

if (!requireNamespace("pacman", quietly = TRUE)) install.packages("pacman")
pacman::p_load(ggsci, here, tidyverse)

# ---- data in ----
# metadata <- read_tsv("metadata.tsv") # to be added later
# Prefer project-relative path:
domains <- read_tsv("/Users/jcgood/gitrepos/planars/NonCollaborative/domains/domains_nyan1308.tsv")

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

# Shared finishing touches for both plot functions below. When the data covers only one
# Domain_Type (the per-class charts), a 5-item color legend is both misleading (it lists
# types that aren't in the chart) and a waste of vertical space on already-short charts —
# so swap it for a plain title instead. Multi-domain charts (the pooled ones) keep the legend.
finish.constituency.plot <- function(p, c){
  domain_types <- unique(na.omit(as.character(c$Domain_Type)))

  if (length(domain_types) == 1) {
    p +
      ggtitle(paste0(str_to_title(domain_types), " domains")) +
      # plot.title.position = "panel" (the theme_bw() default) already aligns the title to
      # the data panel rather than the full plot width, so hjust = 0.5 centers it over the
      # panel itself, not over the (variable-width) row-label column to its left.
      theme(legend.position = "none", plot.title = element_text(hjust = 0.5))
  } else {
    p +
      theme(
        legend.direction = "horizontal",
        legend.position = "top",
        legend.justification = c(1.25, 0)
      )
  }
}

constituency.plot <- function(c, b, o){
  p <- ggplot(c, aes(
    x = Edge,
    # Largest domain on top: ascending Size puts the highest value (largest
    # domain) at the last factor level, which ggplot draws at the top.
    y = reorder(Test_Labels, Size*100 + as.numeric(Layer)),
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

    # Custom legend order (only shown for multi-domain charts; see finish.constituency.plot())
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
      text = element_text(size = 15),
      panel.grid.minor = element_blank()
    )

  finish.constituency.plot(p, c)
}


constituency.domain.plot <- function(c, b, o){
  p <- ggplot(c, aes(
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

    # Custom legend order (only shown for multi-domain charts; see finish.constituency.plot())
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
      text = element_text(size = 15),
      panel.grid.minor = element_blank()
    )

  finish.constituency.plot(p, c)
}

# ---- prepare data ----

tests <- domains %>% 
  filter(!startsWith(Test_Labels, "#"))

# Pooled tables
tests_plot        <- df.plot(tests)
tests_domainsplot <- df.domain.plot(tests)

# Per-domain subsets (each inherits Reverse_Layer from df.plot())
# Filtered from `tests`, not `domains`, so commented-out rows (e.g. "#DummyRoot",
# a placeholder that spans the full structure) stay excluded here too.
tests_plot_length          <- df.plot(filter(tests, Domain_Type == "length"))
tests_plot_morphosyntactic <- df.plot(filter(tests, Domain_Type == "morphosyntactic"))
tests_plot_phonological    <- df.plot(filter(tests, Domain_Type == "phonological"))
tests_plot_tonosegmental   <- df.plot(filter(tests, Domain_Type == "tonosegmental"))
tests_plot_intonational    <- df.plot(filter(tests, Domain_Type == "intonational"))

# ---- params ----
o <- 10 # position of root
b <- 22 # number of positions

# Standard output location for generated charts (see NonCollaborative/results/visualizations.md).
# Absolute path so it lands here regardless of where Rscript is invoked from.
output_dir <- "/Users/jcgood/gitrepos/planars/NonCollaborative/results"

# Chart height scales with how many tests it contains, with a floor so small
# classes (e.g. length, n=7 tests) don't render unreadably short.
plot_height <- function(d) max(7, n_distinct(d$Test_Labels) * 0.7)

# ---- plots ----
pooled_plot        <- constituency.plot(tests_plot, b, o)
pooled_domainplot  <- constituency.domain.plot(tests_domainsplot, b, o)

pooled_plot_length          <- constituency.plot(tests_plot_length, b, o)
pooled_plot_morphosyntactic <- constituency.plot(tests_plot_morphosyntactic, b, o)
pooled_plot_phonological    <- constituency.plot(tests_plot_phonological, b, o)
pooled_plot_tonosegmental   <- constituency.plot(tests_plot_tonosegmental, b, o)
pooled_plot_intonational    <- constituency.plot(tests_plot_intonational, b, o)

# ---- save ----
ggsave(file.path(output_dir, "nyan1308_pooled_plot.pdf"), pooled_plot,
       device = "pdf", width = 26, height = plot_height(tests_plot), units = "cm")
ggsave(file.path(output_dir, "nyan1308_pooled_domainplot.pdf"), pooled_domainplot,
       device = "pdf", width = 26, height = plot_height(tests_domainsplot), units = "cm")

ggsave(file.path(output_dir, "nyan1308_pooled_plot_length.pdf"), pooled_plot_length,
       device = "pdf", width = 25, height = plot_height(tests_plot_length), units = "cm")
ggsave(file.path(output_dir, "nyan1308_pooled_plot_morphosyntactic.pdf"), pooled_plot_morphosyntactic,
       device = "pdf", width = 25, height = plot_height(tests_plot_morphosyntactic), units = "cm")
ggsave(file.path(output_dir, "nyan1308_pooled_plot_phonological.pdf"), pooled_plot_phonological,
       device = "pdf", width = 25, height = plot_height(tests_plot_phonological), units = "cm")
ggsave(file.path(output_dir, "nyan1308_pooled_plot_tonosegmental.pdf"), pooled_plot_tonosegmental,
       device = "pdf", width = 25, height = plot_height(tests_plot_tonosegmental), units = "cm")
ggsave(file.path(output_dir, "nyan1308_pooled_plot_intonational.pdf"), pooled_plot_intonational,
       device = "pdf", width = 25, height = plot_height(tests_plot_intonational), units = "cm")

# ---- per-domain-type variant with pooled-plot-consistent layer numbers ----
# The per-domain-type charts above each call df.plot() on their own filtered subset, so
# their Layer/Reverse_Layer numbering is computed fresh from just that subset -- e.g.
# "layer 3" in the tonosegmental chart is unrelated to "layer 3" in the phonological
# chart or in the pooled plot; each chart renumbers its own domains from 1. This variant
# instead filters the *already-numbered* pooled tests_plot down to one Domain_Type, so
# every chart shares one numbering: whatever a domain is labeled in nyan1308_pooled_plot.pdf
# is the same number it carries here, letting you cross-reference a span between the
# overview and a single-type breakdown directly.
tests_plot_length_global          <- filter(tests_plot, Domain_Type == "length")
tests_plot_morphosyntactic_global <- filter(tests_plot, Domain_Type == "morphosyntactic")
tests_plot_phonological_global    <- filter(tests_plot, Domain_Type == "phonological")
tests_plot_tonosegmental_global   <- filter(tests_plot, Domain_Type == "tonosegmental")
tests_plot_intonational_global    <- filter(tests_plot, Domain_Type == "intonational")

pooled_plot_length_global          <- constituency.plot(tests_plot_length_global, b, o)
pooled_plot_morphosyntactic_global <- constituency.plot(tests_plot_morphosyntactic_global, b, o)
pooled_plot_phonological_global    <- constituency.plot(tests_plot_phonological_global, b, o)
pooled_plot_tonosegmental_global   <- constituency.plot(tests_plot_tonosegmental_global, b, o)
pooled_plot_intonational_global    <- constituency.plot(tests_plot_intonational_global, b, o)

ggsave(file.path(output_dir, "nyan1308_pooled_plot_length_global_layers.pdf"), pooled_plot_length_global,
       device = "pdf", width = 25, height = plot_height(tests_plot_length_global), units = "cm")
ggsave(file.path(output_dir, "nyan1308_pooled_plot_morphosyntactic_global_layers.pdf"), pooled_plot_morphosyntactic_global,
       device = "pdf", width = 25, height = plot_height(tests_plot_morphosyntactic_global), units = "cm")
ggsave(file.path(output_dir, "nyan1308_pooled_plot_phonological_global_layers.pdf"), pooled_plot_phonological_global,
       device = "pdf", width = 25, height = plot_height(tests_plot_phonological_global), units = "cm")
ggsave(file.path(output_dir, "nyan1308_pooled_plot_tonosegmental_global_layers.pdf"), pooled_plot_tonosegmental_global,
       device = "pdf", width = 25, height = plot_height(tests_plot_tonosegmental_global), units = "cm")
ggsave(file.path(output_dir, "nyan1308_pooled_plot_intonational_global_layers.pdf"), pooled_plot_intonational_global,
       device = "pdf", width = 25, height = plot_height(tests_plot_intonational_global), units = "cm")

# ---- counts ----
domain_summary <- tests %>%
  mutate(Domain = paste0(Left_Edge, "–", Right_Edge)) %>%
  count(Domain, Left_Edge, Right_Edge, name = "Count") %>%
  arrange(desc(Count))
print(domain_summary)
