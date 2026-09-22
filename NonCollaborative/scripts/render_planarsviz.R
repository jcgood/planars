#!/usr/bin/env Rscript
# Render planarsviz charts from a data bundle (docs/PLAN_planarsviz_library.md
# section 8.3). The only planarsviz code that writes files.
#
# Which charts exist is read from the bundle, not typed in: one pooled chart
# per observed domain type, one forest per forests.json entry plus one chart
# per tree in that forest, one exemplary chart per selected family, a
# filtered variant for every filter subset (e.g. no_tono), a highlight
# variant for every highlight, the conflict-group
# charts only when the bundle defines groups. Each chart function carries its
# own canvas size (copied from the working script's ggsave() call when the
# chart was ported), so there is no second size table here to drift.
# Rendering choices that were separate script calls -- e.g. the overlay's
# second colour pair for a filtered variant -- are set in chart_table().
#
# A bundle whose family enumeration was truncated is refused (the package's
# validator stops on it). A chart that fails is reported and the script
# exits non-zero; nothing is skipped silently.
#
# Charts are written into a topic subfolder of the output directory --
# laminar-families/, pooled/, boundaries/, counts-and-chance/ -- named by the
# chart's own planarsviz_folder attribute, beside the attribute that gives its
# canvas size. <dataset>_planarsviz_manifest.tsv
# lists every file in the output directory, folder and all, not just the ones
# this run drew:
# a --plots run merges into the manifest already there rather than replacing
# it, and drops only rows whose file has gone. So it describes the directory,
# which is what makes it useful after a partial render. It is bookkeeping, not
# evidence that a chart is correct -- that is what scripts/planarsviz_checks/
# is for. It carries the dataset name because the output directory is
# results/, shared with everything else this project generates, where a file
# called "manifest" says nothing.
#
# Usage (from NonCollaborative/):
#   Rscript scripts/render_planarsviz.R --bundle results/planarsviz/nyan1308 \
#     [--output DIR] [--plots all|name,name,...] [--formats pdf,png] [--list]
# --output defaults to <bundle>/plots. --plots takes chart names as printed by
# --list (the file name without the dataset prefix). png is made from the PDF
# with pdftoppm at 100 dpi.
#
# File names differ from the old results/ files in one place: highlight
# variants are named after the highlight id (all_families_labeled_orthographic_word),
# not "wordhood", because the name has to come from the data.

parse_args <- function(args) {
  out <- list(bundle = NULL, output = NULL, plots = "all", formats = "pdf", list = FALSE)
  i <- 1
  while (i <= length(args)) {
    key <- args[[i]]
    if (key == "--list") { out$list <- TRUE; i <- i + 1; next }
    if (i == length(args)) stop("Missing value for ", key, call. = FALSE)
    value <- args[[i + 1]]
    switch(key,
      "--bundle" = out$bundle <- value,
      "--output" = out$output <- value,
      "--plots" = out$plots <- value,
      "--formats" = out$formats <- value,
      stop("Unknown argument: ", key, call. = FALSE))
    i <- i + 2
  }
  if (is.null(out$bundle)) stop("--bundle is required.", call. = FALSE)
  out
}
opts <- parse_args(commandArgs(trailingOnly = TRUE))

script_dir <- local({
  file_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
  if (length(file_arg)) dirname(normalizePath(sub("^--file=", "", file_arg[[1]]))) else getwd()
})
lib <- file.path(tempdir(), "planarsviz_lib")
dir.create(lib, showWarnings = FALSE)
status <- system2("R", c("CMD", "INSTALL", "--no-test-load", paste0("--library=", lib),
                         shQuote(file.path(script_dir, "..", "r", "planarsviz"))), stdout = FALSE, stderr = FALSE)
if (status != 0) stop("R CMD INSTALL of r/planarsviz failed.", call. = FALSE)
suppressPackageStartupMessages({
  library(planarsviz, lib.loc = lib)
  library(ggplot2)
})

bundle <- read_planars_bundle(opts$bundle)
dataset <- bundle$metadata$dataset
data_dir <- file.path(bundle$bundle_dir, "data")
read_json <- function(name) jsonlite::read_json(file.path(data_dir, name), simplifyVector = FALSE)
read_tsv <- function(name) {
  path <- file.path(data_dir, name)
  if (file.exists(path)) utils::read.delim(path, stringsAsFactors = FALSE, colClasses = "character") else data.frame()
}

chart_table <- function() {
  charts <- list()
  add <- function(name, make) charts[[name]] <<- make

  types <- sort(unique(trimws(bundle$tests$Domain_Type)))
  add("pooled_plot", function() plot_pooled(bundle))
  add("pooled_domainplot", function() plot_pooled(bundle, group_by_domain = TRUE))
  for (t in types) {
    local({
      type <- t
      add(paste0("pooled_plot_", type), function() plot_pooled(bundle, domain_types = type, layers = "local"))
      add(paste0("pooled_plot_", type, "_global_layers"), function() plot_pooled(bundle, domain_types = type, layers = "global"))
    })
  }
  add("boundary_skyline", function() plot_boundary_skyline(bundle))
  add("spanchart", function() plot_span_chart(bundle))

  for (f in read_json("forests.json")) {
    local({
      id <- f$forest_id
      add(paste0(id, "_laminar_forest"), function() plot_laminar_forest(bundle, id))
      # Plus every one of that forest's families as its own tree. Every
      # forest gets these, not only the three bundle forests, because the
      # loop is the same either way and --plots decides what is drawn.
      # Numbers are padded to at least two digits, as bundle_forest_trees.r
      # padded them before the package absorbed it, so tree 10 sorts after
      # tree 9 in a directory listing.
      n_trees <- as.integer(f$n_trees)
      digits <- max(2L, nchar(as.character(n_trees)))
      for (k in seq_len(n_trees)) {
        local({
          number <- k
          add(paste0(id, "_tree_", formatC(number, width = digits, flag = "0")),
              function() plot_forest_tree(bundle, id, number))
        })
      }
    })
  }

  all_group <- list(groups = "all", alpha_divisor = 1, thickness_exponent = 0.75)
  add("laminar_overlay", function() plot_laminar_overlay(bundle))
  add("laminar_overlay_legend", function() plot_laminar_overlay(bundle, legend = TRUE))
  add("all_families_labeled", function() do.call(plot_laminar_overlay, c(list(bundle), all_group)))
  add("all_families_labeled_legend", function() do.call(plot_laminar_overlay, c(list(bundle), all_group, list(legend = TRUE))))
  highlights <- read_tsv("highlights.tsv")
  for (h in unique(highlights$highlight_id)) {
    local({
      id <- h
      add(paste0("all_families_labeled_", id),
          function() do.call(plot_laminar_overlay, c(list(bundle), all_group, list(highlight = id))))
      add(paste0("all_families_labeled_", id, "_legend"),
          function() do.call(plot_laminar_overlay, c(list(bundle), all_group, list(highlight = id, legend = TRUE))))
    })
  }

  add("freqtree", function() plot_frequency_tree(bundle))
  selection_names <- unique(read_tsv("selections.tsv")$selection)
  if ("most_binary" %in% selection_names) {
    # Illustration: the most binary branching the evidence supports.
    add("most_binary_tree", function() plot_frequency_tree(
      bundle, selection = "most_binary", weight = "none",
      title = 'Maximal binary branching supported by the data'))
    for (h in unique(highlights$highlight_id)) {
      local({
        id <- h
        name <- gsub("_", " ", id, fixed = TRUE)
        # Same tree, with the edges out to the highlight's first and last
        # positions traced thicker.
        add(paste0("most_binary_tree_", id), function() plot_frequency_tree(
          bundle, selection = "most_binary", weight = "none", emphasis = id,
          title = paste0('Maximal binary branching, with the extent of the ', name, ' traced')))
      })
    }
  }
  if (nrow(read_tsv("conflict_groups.tsv"))) {
    add("four_trees", function() plot_four_trees(bundle))
    add("conflict_groups", function() plot_conflict_groups(bundle))
  }

  selections <- read_tsv("selections.tsv")
  for (r in sort(as.integer(selections$rank[selections$selection == "exemplary"]))) {
    local({
      rank <- r
      add(paste0("exemplary_trees_", rank), function() plot_exemplary_tree(bundle, rank, "page"))
      add(paste0("exemplary_trees_slide_", rank, "_tree"), function() plot_exemplary_tree(bundle, rank, "slide_tree"))
      add(paste0("exemplary_trees_slide_", rank, "_evidence"), function() plot_exemplary_tree(bundle, rank, "slide_evidence"))
    })
  }

  filters <- Filter(function(s) identical(s$kind, "filter"), read_json("subsets.json"))
  add("forestspans_plot", function() plot_forestspans(bundle))
  for (chart in c("by_class", "bundles", "all", "without_adjacent")) {
    local({
      which <- chart
      add(paste0("tree_count_", which), function() plot_tree_counts(bundle, which))
    })
  }
  # Only when the bundle has it: the permutation test is slow enough that the
  # exporter runs it on request, so a bundle without it is normal, not broken.
  if (file.exists(file.path(data_dir, "fragmentation_test.tsv"))) {
    add("fragmentation_test_plot", function() plot_fragmentation_test(bundle))
    # The pair of bundles on their own, which the script this was ported from
    # drew as a second call for presenting them without the domain types
    # around them. Which two is a presentation choice rather than anything in
    # the data, so it is set here with the other choices that were separate
    # script calls -- and only when the bundle has both.
    syntax_phon <- c("phonologylike", "syntaxlike")
    if (all(syntax_phon %in% read_tsv("fragmentation_test.tsv")$group)) {
      add("fragmentation_test_syntax_phon_plot",
          function() plot_fragmentation_test(bundle, groups = syntax_phon))
    }
  }
  # Only when the bundle has it, same as the fragmentation tables above.
  # The grid is every group at once; the two standalone charts are the
  # bundles someone presents on their own, so which two is a presentation
  # choice and sits here rather than in the data.
  if (file.exists(file.path(data_dir, "span_placement_test.tsv"))) {
    add("span_placement_test_by_group_plot", function() plot_span_placement_test(bundle))
    for (group in c("syntaxlike", "phonologylike")) {
      local({
        g <- group
        if (g %in% read_tsv("span_placement_test.tsv")$group) {
          add(paste0("span_placement_test_", g, "_plot"),
              function() plot_span_placement_test(bundle, groups = g, view = "standalone"))
        }
      })
    }
  }
  # Only when the bundle has it: the permutation test is slow enough that the
  # exporter runs it on request (--boundary-strength-test-permutations), so a
  # bundle without it is normal, not broken.
  if (file.exists(file.path(data_dir, "boundary_strength_test.tsv"))) {
    for (group in unique(read_tsv("boundary_strength_test.tsv")$group)) {
      local({
        g <- group
        add(paste0("boundary_strength_test_jump_", g), function() plot_boundary_strength_test(bundle, group = g, statistic = "jump"))
        add(paste0("boundary_strength_test_level_", g), function() plot_boundary_strength_test(bundle, group = g, statistic = "level"))
      })
    }
  }
  add("boundary_strength", function() plot_boundary_strength(bundle))
  add("boundary_strength_distributions", function() plot_boundary_strength_distributions(bundle))
  add("boundary_strength_overlay", function() plot_boundary_strength_overlay(bundle))
  for (f in filters) {
    local({
      id <- f$subset_id
      add(paste0("forestspans_plot_", id), function() plot_forestspans(bundle, subset = id))
      add(paste0("boundary_strength_", id), function() plot_boundary_strength(bundle, subset = id))
      # The working script drew filtered overlays in a second colour pair so
      # the two are never mistaken for each other.
      add(paste0("boundary_strength_overlay_", id), function()
        plot_boundary_strength_overlay(bundle, subset = id, colours = c(Left = "#009E73", Right = "#CC79A7")))
    })
  }
  charts
}

charts <- chart_table()
if (opts$list) {
  cat(names(charts), sep = "\n")
  quit(status = 0)
}
wanted <- if (identical(opts$plots, "all")) names(charts) else strsplit(opts$plots, ",", fixed = TRUE)[[1]]
unknown <- setdiff(wanted, names(charts))
if (length(unknown)) {
  stop("Not a chart for this bundle: ", paste(unknown, collapse = ", "),
       ". Run with --list to see the charts it has.", call. = FALSE)
}
formats <- strsplit(opts$formats, ",", fixed = TRUE)[[1]]
if (length(setdiff(formats, c("pdf", "png")))) stop("--formats takes pdf and/or png.", call. = FALSE)

output <- if (is.null(opts$output)) file.path(bundle$bundle_dir, "plots") else opts$output
dir.create(output, recursive = TRUE, showWarnings = FALSE)

manifest <- data.frame()
failed <- character()
for (name in wanted) {
  base <- paste0(dataset, "_", name)
  result <- tryCatch({
    p <- suppressMessages(suppressWarnings(charts[[name]]()))
    size <- attr(p, "planarsviz_size")
    units <- attr(p, "planarsviz_units")
    if (is.null(size) || is.null(units)) stop("chart function returned no canvas size")
    # Each chart says which topic folder it belongs in, the same way it says
    # how big its canvas is, so there is no second table here to drift.
    folder <- attr(p, "planarsviz_folder")
    if (is.null(folder)) stop("chart function returned no folder")
    dest <- file.path(output, folder)
    dir.create(dest, recursive = TRUE, showWarnings = FALSE)
    pdf_path <- file.path(dest, paste0(base, ".pdf"))
    suppressMessages(suppressWarnings(ggplot2::ggsave(pdf_path, p, device = "pdf", width = size[["width"]],
                                                      height = size[["height"]], units = units, limitsize = FALSE)))
    files <- if ("pdf" %in% formats) pdf_path else character()
    if ("png" %in% formats) {
      stem <- file.path(dest, base)
      system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(stem)))
      files <- c(files, paste0(stem, ".png"))
      if (!"pdf" %in% formats) unlink(pdf_path)
    }
    data.frame(chart = name, file = file.path(folder, basename(files)), width = size[["width"]],
               height = size[["height"]], units = units)
  }, error = function(e) {
    failed <<- c(failed, name)
    cat("FAILED ", name, ": ", conditionMessage(e), "\n", sep = "")
    NULL
  })
  if (!is.null(result)) {
    manifest <- rbind(manifest, result)
    cat("wrote ", paste(result$file, collapse = ", "), "\n", sep = "")
  }
}
# Merge into any manifest already there, rather than replacing it: a --plots
# run draws some of the charts, and a manifest that then listed only those
# would stop describing what is in the directory. Rows this run produced win;
# older rows for charts it did not draw are kept -- but only if their file is
# still on disk, so a chart that has gone away (the fragmentation chart
# disappears from a bundle exported without --fragmentation-permutations)
# drops out instead of being claimed forever.
manifest_path <- file.path(output, paste0(dataset, "_planarsviz_manifest.tsv"))
kept <- 0L
if (file.exists(manifest_path)) {
  previous <- utils::read.delim(manifest_path, stringsAsFactors = FALSE)
  if (nrow(previous) && all(names(manifest) %in% names(previous))) {
    stale <- previous[!previous$chart %in% manifest$chart, names(manifest), drop = FALSE]
    stale <- stale[file.exists(file.path(output, stale$file)), , drop = FALSE]
    kept <- nrow(stale)
    manifest <- rbind(manifest, stale)
  }
}
manifest <- manifest[order(match(manifest$chart, names(charts)), manifest$file), , drop = FALSE]
utils::write.table(manifest, manifest_path, sep = "\t", quote = FALSE, row.names = FALSE)
cat(nrow(manifest), " files for ", length(wanted) - length(failed), " of ", length(wanted), " charts",
    if (kept) paste0(" (plus ", kept, " kept from an earlier run)") else "", "; manifest: ",
    manifest_path, "\n", sep = "")
if (length(failed)) {
  cat("Charts that failed: ", paste(failed, collapse = ", "), "\n", sep = "")
  quit(status = 1)
}
