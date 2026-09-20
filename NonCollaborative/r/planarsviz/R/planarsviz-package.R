# This file has no functions of its own. It exists so roxygen2 has one
# place to read the package's imports from — the chart code in the other
# R/ files was written assuming ggplot2, dplyr, tidyr, %>%, and a few other
# functions are already attached, and roxygen2 only wires up NAMESPACE
# imports it is told about via @import/@importFrom tags. These tags mirror
# the hand-written NAMESPACE's import lines exactly.

#' planarsviz: visualizations for planar constituency analyses
#'
#' @keywords internal
#' @import ggplot2
#' @importFrom dplyr arrange cur_group_id desc filter group_by mutate n_distinct ungroup
#' @importFrom grid unit
#' @importFrom magrittr %>%
#' @importFrom patchwork plot_annotation plot_layout
#' @importFrom stats na.omit reorder
#' @importFrom stringr str_to_title
#' @importFrom tidyr pivot_longer
"_PACKAGE"
