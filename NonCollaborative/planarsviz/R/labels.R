#' Position labels from a bundle
#'
#' Kept from the first (Codex) package attempt; it only reshapes the
#' bundle's `position_labels` table and draws nothing.
#'
#' @param position_labels A two-column data frame with `position` and `label`
#'   columns, such as `bundle$position_labels`.
#' @return A character vector of labels named by position number, in position
#'   order.
#' @export
planarsviz_position_labels <- function(position_labels) {
  required <- c("position", "label")
  if (!is.data.frame(position_labels) || !all(required %in% names(position_labels))) {
    stop("`position_labels` must contain `position` and `label` columns.", call. = FALSE)
  }
  positions <- as.integer(position_labels$position)
  if (anyNA(positions) || anyDuplicated(positions) || any(positions < 1L) ||
    any(!nzchar(as.character(position_labels$label)))) {
    stop("Position labels must have unique positive positions and non-empty labels.", call. = FALSE)
  }
  labels <- as.character(position_labels$label)
  names(labels) <- as.character(positions)
  labels[order(as.integer(names(labels)))]
}

# The boxed "N\nName" label drawn at a tree tip or under a position. A
# planar table with no position names (every CCDB one) falls back to the
# position number as the name, which would read "1\n1"; there the number is
# shown once. nyan1308's names are never bare numbers, so its labels are
# unchanged.
planarsviz_tip_label <- function(number, name) {
  both <- paste(number, name, sep = "\n")
  ifelse(both == paste(number, number, sep = "\n"), as.character(number), both)
}

# How much wider than its fixed canvas a chart with a position axis should
# be. Every fixed width in this package was tuned on nyan1308's 22 positions,
# so a structure with more gets proportionally more width and one with 22 or
# fewer keeps the width exactly as it was (never shrunk: the text sizes were
# chosen for that canvas, and a narrower one would crowd the labels instead).
# The factor is exactly 1 for nyan1308, which is what keeps its charts
# identical to the reference images.
planarsviz_position_scale <- function(bundle, baseline = 22L) {
  n_positions <- as.integer(bundle$metadata$n_positions)
  if (length(n_positions) != 1L || is.na(n_positions)) {
    return(1)
  }
  max(1, n_positions / baseline)
}
