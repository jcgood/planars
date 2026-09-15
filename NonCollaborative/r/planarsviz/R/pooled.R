# Pooled constituency plots (charts 1-4 in docs/PLAN_planarsviz_library.md).
#
# STEP 1 COPY: everything below is copied verbatim from
# scripts/domain_charts-cgpt.r, lines 14-202 (df.plot, df.domain.plot,
# group.colors, finish.constituency.plot, constituency.plot,
# constituency.domain.plot, plot_height), at commit 43a308f. No edits other
# than this header. Literals are replaced with bundle data in the next commit.

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

# Chart height scales with how many tests it contains, with a floor so small
# classes (e.g. length, n=7 tests) don't render unreadably short.
plot_height <- function(d) max(7, n_distinct(d$Test_Labels) * 0.7)
