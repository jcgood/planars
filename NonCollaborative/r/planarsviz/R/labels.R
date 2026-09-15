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
