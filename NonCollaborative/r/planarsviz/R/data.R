#' Read a planarsviz data bundle
#'
#' @param bundle_dir Dataset bundle directory containing a `data/` directory,
#'   or the `data/` directory itself.
#' @return A validated list with `metadata`, `spans`, `tests`, `families`,
#'   `family_membership`, `conflict_pairs`, and `position_labels`.
#' @export
read_planars_bundle <- function(bundle_dir) {
  bundle_dir <- normalizePath(bundle_dir, mustWork = TRUE)
  data_dir <- if (basename(bundle_dir) == "data") bundle_dir else file.path(bundle_dir, "data")
  if (!dir.exists(data_dir)) {
    stop("Bundle must contain a `data/` directory.", call. = FALSE)
  }

  required <- c(
    "metadata.json", "spans.tsv", "tests.tsv", "families.tsv",
    "family_membership.tsv", "conflict_pairs.tsv", "position_labels.tsv"
  )
  missing <- required[!file.exists(file.path(data_dir, required))]
  if (length(missing) > 0L) {
    stop("Bundle is missing: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  bundle <- list(
    metadata = jsonlite::read_json(file.path(data_dir, "metadata.json"), simplifyVector = TRUE),
    spans = read.delim(file.path(data_dir, "spans.tsv"), stringsAsFactors = FALSE),
    tests = read.delim(file.path(data_dir, "tests.tsv"), stringsAsFactors = FALSE),
    families = read.delim(file.path(data_dir, "families.tsv"), stringsAsFactors = FALSE),
    family_membership = read.delim(file.path(data_dir, "family_membership.tsv"), stringsAsFactors = FALSE),
    conflict_pairs = read.delim(file.path(data_dir, "conflict_pairs.tsv"), stringsAsFactors = FALSE),
    position_labels = read.delim(file.path(data_dir, "position_labels.tsv"), stringsAsFactors = FALSE),
    bundle_dir = dirname(data_dir)
  )
  class(bundle) <- "planarsviz_bundle"
  validate_planars_bundle(bundle)
  bundle
}

#' Read a domain-type-specific planarsviz sub-bundle
#'
#' @param bundle A bundle returned by [read_planars_bundle()].
#' @param subset_id Identifier from `data/subsets.json`, usually a normalized
#'   domain type such as `phonological`.
#' @return A validated `planarsviz_bundle` containing the subset's families and
#'   the parent bundle's position labels.
#' @export
read_planars_subset <- function(bundle, subset_id) {
  validate_planars_bundle(bundle)
  if (length(subset_id) != 1L || !is.character(subset_id)) {
    stop("`subset_id` must be one character identifier.", call. = FALSE)
  }
  index_path <- file.path(bundle$bundle_dir, "data", "subsets.json")
  if (!file.exists(index_path)) {
    stop("Bundle has no domain-type subset index.", call. = FALSE)
  }
  index <- jsonlite::read_json(index_path, simplifyVector = TRUE)
  match_row <- index[index$subset_id == subset_id, , drop = FALSE]
  if (!nrow(match_row)) stop("Unknown planarsviz subset: ", subset_id, call. = FALSE)
  subset_dir <- file.path(bundle$bundle_dir, "data", match_row$path[[1L]])
  required <- c("metadata.json", "spans.tsv", "tests.tsv", "families.tsv",
                "family_membership.tsv", "conflict_pairs.tsv")
  missing <- required[!file.exists(file.path(subset_dir, required))]
  if (length(missing)) stop("Subset is missing: ", paste(missing, collapse = ", "), call. = FALSE)
  subset <- list(
    metadata = jsonlite::read_json(file.path(subset_dir, "metadata.json"), simplifyVector = TRUE),
    spans = read.delim(file.path(subset_dir, "spans.tsv"), stringsAsFactors = FALSE),
    tests = read.delim(file.path(subset_dir, "tests.tsv"), stringsAsFactors = FALSE),
    families = read.delim(file.path(subset_dir, "families.tsv"), stringsAsFactors = FALSE),
    family_membership = read.delim(file.path(subset_dir, "family_membership.tsv"), stringsAsFactors = FALSE),
    conflict_pairs = read.delim(file.path(subset_dir, "conflict_pairs.tsv"), stringsAsFactors = FALSE),
    position_labels = bundle$position_labels,
    bundle_dir = dirname(subset_dir)
  )
  class(subset) <- "planarsviz_bundle"
  validate_planars_bundle(subset)
  subset
}

#' Validate a planarsviz data bundle
#'
#' @param bundle A bundle returned by [read_planars_bundle()].
#' @return The validated bundle, invisibly.
#' @export
validate_planars_bundle <- function(bundle) {
  if (!is.list(bundle) || is.null(bundle$metadata)) {
    stop("`bundle` must be a planarsviz bundle.", call. = FALSE)
  }
  metadata <- bundle$metadata
  required_metadata <- c(
    "contract_version", "n_positions", "n_active_tests", "n_unique_spans",
    "n_conflict_pairs", "n_maximal_families", "enumeration_truncated"
  )
  missing_metadata <- required_metadata[!required_metadata %in% names(metadata)]
  if (length(missing_metadata) > 0L) {
    stop("Metadata is missing: ", paste(missing_metadata, collapse = ", "), call. = FALSE)
  }
  if (isTRUE(metadata$enumeration_truncated)) {
    stop("Bundle contains truncated family enumeration data.", call. = FALSE)
  }

  required_columns <- list(
    spans = c("span_id", "left", "right", "size", "convergence", "family_frequency"),
    families = c("family_id", "family_number", "n_spans"),
    family_membership = c("family_id", "span_id"),
    conflict_pairs = c("span_id_a", "span_id_b"),
    position_labels = c("position", "label")
  )
  for (table_name in names(required_columns)) {
    missing_columns <- setdiff(required_columns[[table_name]], names(bundle[[table_name]]))
    if (length(missing_columns) > 0L) {
      stop(table_name, " is missing: ", paste(missing_columns, collapse = ", "), call. = FALSE)
    }
  }

  spans <- bundle$spans
  expected_span_ids <- paste(spans$left, spans$right, sep = "-")
  if (!identical(as.character(spans$span_id), expected_span_ids)) {
    stop("Span IDs do not match left/right coordinates.", call. = FALSE)
  }
  if (any(as.integer(spans$size) != as.integer(spans$right) - as.integer(spans$left) + 1L)) {
    stop("Span sizes do not match left/right coordinates.", call. = FALSE)
  }
  # A synthetic full root (spans.tsv `synthetic` = TRUE) is listed so family
  # memberships can name it, but it is not an observed span.
  n_observed_spans <- if ("synthetic" %in% names(spans)) {
    sum(!as.logical(spans$synthetic))
  } else {
    nrow(spans)
  }
  if (n_observed_spans != as.integer(metadata$n_unique_spans) ||
      nrow(bundle$families) != as.integer(metadata$n_maximal_families) ||
      nrow(bundle$conflict_pairs) != as.integer(metadata$n_conflict_pairs) ||
      nrow(bundle$tests) != as.integer(metadata$n_active_tests) ||
      nrow(bundle$position_labels) != as.integer(metadata$n_positions)) {
    stop("Bundle table counts do not match metadata.", call. = FALSE)
  }

  known_spans <- spans$span_id
  known_families <- bundle$families$family_id
  membership <- bundle$family_membership
  if (any(!membership$span_id %in% known_spans) ||
      any(!membership$family_id %in% known_families)) {
    stop("Family membership references an unknown family or span.", call. = FALSE)
  }
  if (any(!bundle$conflict_pairs$span_id_a %in% known_spans) ||
      any(!bundle$conflict_pairs$span_id_b %in% known_spans)) {
    stop("Conflict pairs reference an unknown span.", call. = FALSE)
  }
  invisible(bundle)
}
