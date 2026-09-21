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
#' @importFrom utils read.delim
"_PACKAGE"

# Column names used inside aes() and dplyr verbs. R's code checker cannot see
# that these are columns of a data frame rather than variables that were never
# defined, so it reports each one; declaring them here keeps a real "you used a
# name that does not exist" warning visible among them.
#
# They are declared rather than rewritten as .data$column because the chart
# code was copied line for line from the scripts the package replaced, and the
# porting checks compare it against those scripts. Rewriting every aes() call
# would break that correspondence for a cosmetic gain.
utils::globalVariables(c(
  "alpha_val", "Boundary", "capped", "Color", "colour", "Colour", "Count",
  "Density", "Domain_Layer", "Domain_Type", "Edge", "edge_size",
  "family_count", "freq_scaled", "group", "label", "Label", "label_x",
  "Layer", "left", "Left", "Left_Edge", "lw", "observed_families",
  "p_value_le_observed", "position", "Reverse_Domain_Layer",
  "Reverse_Layer", "right", "Right", "Right_Edge", "side", "size", "Size",
  "Strength", "summed", "Test_Labels", "value", "x", "x0", "x1", "y",
  "y_rank"
))
