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
# Charts are written into <dataset>/<topic>/, where <topic> is one of
# laminar-families/, pooled/, boundaries/, counts-and-chance/ -- named by the
# chart's own planarsviz_folder attribute, beside the attribute that gives its
# canvas size. So a second dataset's charts land beside the first's rather
# than colliding with it. <dataset>/<dataset>_planarsviz_manifest.tsv
# lists every chart file in that dataset's folder, by its path within the
# folder, with its title and its part (the chapter the contributor PDFs put
# it in; both set in chart_table()), not just the ones this run drew:
# a --plots run merges into the manifest already there rather than replacing
# it, and drops only rows whose file has gone. So it describes the directory,
# which is what makes it useful after a partial render. It is bookkeeping, not
# evidence that a chart is correct -- that is what
# NonCollaborative/scripts/planarsviz_checks/ is for. It carries the dataset
# name because the output directory is results/, shared with everything else
# this project generates, where a file called "manifest" says nothing.
#
# `python -m laminar charts <dataset>` runs this with the dataset's options.
# On its own (from the repository root, where .Rprofile sets up the pinned
# packages):
#   Rscript laminar/render_planarsviz.R --bundle NonCollaborative/results/chart_data/nyan1308 \
#     [--output DIR] [--plots all|name,name,...] [--formats pdf,png] [--list]
# --output defaults to <bundle>/plots. --plots takes chart names as printed by
# --list (the file name without the dataset prefix). png is made from the PDF
# with pdftoppm at 100 dpi.
#
# File names differ from the old results/ files in one place: highlight
# variants are named after the highlight id (all_families_labeled_orthographic_word),
# not "wordhood", because the name has to come from the data.
#
# --bundle can also be the illustrations bundle (results/chart_data/illustrations),
# detected by the presence of data/tree_shapes.tsv rather than a flag, since
# that bundle has no language behind it to name one. Its random-tree overlay
# needs a real language's position labels, which is what --positions-bundle
# is for (any ordinary --bundle path); the tree-shape and tree-count-growth
# charts don't need it and are still listed without it.
#   Rscript laminar/render_planarsviz.R \
#     --bundle NonCollaborative/results/chart_data/illustrations \
#     --positions-bundle NonCollaborative/results/chart_data/nyan1308 \
#     --output NonCollaborative/results
#
# --bundle can also be the cross-language bundle (results/chart_data/cross_language),
# detected by data/structures.tsv. Its charts, like the illustrations', land
# with no topic subfolder, in <output>/cross_language/.
#   Rscript laminar/render_planarsviz.R \
#     --bundle NonCollaborative/results/chart_data/cross_language \
#     --output NonCollaborative/results

parse_args <- function(args) {
  out <- list(bundle = NULL, positions_bundle = NULL, output = NULL, plots = "all",
              formats = "pdf", list = FALSE)
  i <- 1
  while (i <= length(args)) {
    key <- args[[i]]
    if (key == "--list") { out$list <- TRUE; i <- i + 1; next }
    if (i == length(args)) stop("Missing value for ", key, call. = FALSE)
    value <- args[[i + 1]]
    switch(key,
      "--bundle" = out$bundle <- value,
      "--positions-bundle" = out$positions_bundle <- value,
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
                         shQuote(file.path(script_dir, "..", "planarsviz"))), stdout = FALSE, stderr = FALSE)
if (status != 0) stop("R CMD INSTALL of planarsviz failed.", call. = FALSE)
suppressPackageStartupMessages({
  library(planarsviz, lib.loc = lib)
  library(ggplot2)
})

# The illustrations bundle has no spans/tests/families -- read_planars_bundle()
# would just fail its validation on it -- so which reader to use is decided by
# what the bundle actually contains, not a flag naming a language that doesn't
# exist for it.
is_illustrations <- file.exists(file.path(opts$bundle, "data", "tree_shapes.tsv")) ||
  file.exists(file.path(opts$bundle, "tree_shapes.tsv"))
# Likewise the cross-language bundle, which has one row per structure rather
# than one language's spans; recognised by its structures.tsv.
is_cross_language <- file.exists(file.path(opts$bundle, "data", "structures.tsv")) ||
  file.exists(file.path(opts$bundle, "structures.tsv"))
bundle <- if (is_illustrations) {
  read_planars_illustrations(opts$bundle)
} else if (is_cross_language) {
  read_planars_cross_language(opts$bundle)
} else {
  read_planars_bundle(opts$bundle)
}
dataset <- bundle$metadata$dataset
positions_bundle <- if (!is.null(opts$positions_bundle)) read_planars_bundle(opts$positions_bundle) else NULL
data_dir <- file.path(bundle$bundle_dir, "data")
read_json <- function(name) jsonlite::read_json(file.path(data_dir, name), simplifyVector = FALSE)
read_tsv <- function(name) {
  path <- file.path(data_dir, name)
  if (file.exists(path)) utils::read.delim(path, stringsAsFactors = FALSE, colClasses = "character") else data.frame()
}

# Every chart is added with its title (what the chart shows, in words a
# contributor reads; the manifest's `title` column, which the contributor
# PDFs put above each page) and its part (the chapter it goes in there:
# laminar/contributor_charts.py's PARTS, which fails on a part it doesn't
# list). Both are written here, beside the chart, so a new chart can't be
# added without them.
readable <- function(x) {
  # free_occurrence -> Free occurrence; phonological-prosodic -> Phonological (prosodic)
  x <- gsub("_", " ", x, fixed = TRUE)
  head <- sub("-.*$", "", x)
  sub_part <- if (grepl("-", x, fixed = TRUE)) paste0(" (", sub("^[^-]*-", "", x), ")") else ""
  paste0(toupper(substring(head, 1, 1)), substring(head, 2), sub_part)
}

chart_table <- function() {
  charts <- list()
  titles <- character()
  parts <- character()
  add <- function(name, title, part, make) {
    charts[[name]] <<- make
    titles[[name]] <<- title
    parts[[name]] <<- part
  }
  finish <- function() {
    attr(charts, "titles") <- titles
    attr(charts, "parts") <- parts
    charts
  }

  if (is_illustrations) {
    for (n in sort(unique(bundle$tree_shapes$n))) {
      local({
        nn <- n
        add(paste0("tree_shapes_n", nn), paste0("Every tree shape over ", nn, " positions"),
            "illustrations", function() plot_tree_shapes(bundle, nn))
      })
    }
    add("tree_count_growth", "How the number of possible trees grows with the number of positions",
        "illustrations", function() plot_tree_count_growth(bundle, positions_bundle))
    if (!is.null(positions_bundle)) {
      add("random_tree_overlay", "Randomly drawn trees, stacked", "illustrations",
          function() plot_random_tree_overlay(bundle, positions_bundle))
    }
    return(finish())
  }

  if (is_cross_language) {
    for (role in c("all", "syntax_side", "phonology_side")) {
      local({
        r <- role
        suffix <- if (r == "all") "" else paste0("_", r)
        add(paste0("tree_likeness", suffix),
            paste0("How tree-like each structure is", if (r == "all") "" else paste0(" (", gsub("_", " ", r), ")")),
            "cross_language", function() plot_cross_language_tree_likeness(bundle, r))
      })
    }
    add("families_vs_size", "Families against the number of tests", "cross_language",
        function() plot_cross_language_families_vs_size(bundle))
    add("divide", "Conflicts within and across the morphosyntax/phonology divide", "cross_language",
        function() plot_cross_language_divide(bundle))
    add("side_p", "Which side of the divide is more tree-like", "cross_language",
        function() plot_cross_language_side_p(bundle))
    add("edges", "Span edges around the root", "cross_language",
        function() plot_cross_language_edges(bundle))
    add("convergence", "The most convergent spans", "cross_language",
        function() plot_cross_language_convergence(bundle))
    return(finish())
  }

  types <-sort(unique(trimws(bundle$tests$Domain_Type)))
  add("pooled_plot", "Every test's span over the planar structure", "spans",
      function() plot_pooled(bundle))
  add("pooled_domainplot", "Every test's span, grouped by domain type", "spans",
      function() plot_pooled(bundle, group_by_domain = TRUE))
  for (t in types) {
    local({
      type <- t
      add(paste0("pooled_plot_", type), paste0(readable(type), " tests: their spans"), "spans",
          function() plot_pooled(bundle, domain_types = type, layers = "local"))
      add(paste0("pooled_plot_", type, "_global_layers"),
          paste0(readable(type), " tests: their spans, numbered as in the chart of every test"), "spans",
          function() plot_pooled(bundle, domain_types = type, layers = "global"))
    })
  }
  add("boundary_skyline", "How often each position starts or ends a span", "boundaries",
      function() plot_boundary_skyline(bundle))
  add("spanchart", "Every span, by how many families contain it", "spans",
      function() plot_span_chart(bundle))

  for (f in read_json("forests.json")) {
    local({
      id <- f$forest_id
      # A bundle exported before forests had labels (2026-10-25) names the forest by its id.
      label <- if (is.null(f$label)) id else f$label
      add(paste0(id, "_laminar_forest"), paste0("Laminar forest: ", label, " (", f$n_trees,
                                                if (as.integer(f$n_trees) == 1) " family)" else " families)"),
          "forests", function() plot_laminar_forest(bundle, id))
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
              paste0(label, ": family ", number, " of ", n_trees), "families",
              function() plot_forest_tree(bundle, id, number))
        })
      }
    })
  }

  all_group <- list(groups = "all", alpha_divisor = 1, thickness_exponent = 0.75)
  add("laminar_overlay", "Every family of each domain type, stacked and coloured by type", "overview",
      function() plot_laminar_overlay(bundle))
  add("laminar_overlay_legend", "Every family of each domain type, stacked and coloured by type (with key)",
      "overview", function() plot_laminar_overlay(bundle, legend = TRUE))
  add("all_families_labeled", "Combined constituency forest: every family of every test, stacked", "overview",
      function() do.call(plot_laminar_overlay, c(list(bundle), all_group)))
  add("all_families_labeled_legend",
      "Combined constituency forest: every family of every test, stacked (with key)", "overview",
      function() do.call(plot_laminar_overlay, c(list(bundle), all_group, list(legend = TRUE))))
  highlights <- read_tsv("highlights.tsv")
  for (h in unique(highlights$highlight_id)) {
    local({
      id <- h
      name <- gsub("_", " ", id, fixed = TRUE)
      add(paste0("all_families_labeled_", id),
          paste0("Combined constituency forest, with the ", name, " marked"), "overview",
          function() do.call(plot_laminar_overlay, c(list(bundle), all_group, list(highlight = id))))
      add(paste0("all_families_labeled_", id, "_legend"),
          paste0("Combined constituency forest, with the ", name, " marked (with key)"), "overview",
          function() do.call(plot_laminar_overlay, c(list(bundle), all_group, list(highlight = id, legend = TRUE))))
    })
  }

  add("freqtree", "Frequency tree: the family whose spans the most families share", "overview",
      function() plot_frequency_tree(bundle))
  selection_names <- unique(read_tsv("selections.tsv")$selection)
  if ("most_binary" %in% selection_names) {
    # Illustration: the most binary branching the evidence supports.
    add("most_binary_tree", "Maximal binary branching supported by the data", "overview",
        function() plot_frequency_tree(
          bundle, selection = "most_binary", weight = "none",
          title = 'Maximal binary branching supported by the data'))
    for (h in unique(highlights$highlight_id)) {
      local({
        id <- h
        name <- gsub("_", " ", id, fixed = TRUE)
        # Same tree, with the edges out to the highlight's first and last
        # positions traced thicker.
        add(paste0("most_binary_tree_", id),
            paste0("Maximal binary branching, with the extent of the ", name, " traced"), "overview",
            function() plot_frequency_tree(
              bundle, selection = "most_binary", weight = "none", emphasis = id,
              title = paste0('Maximal binary branching, with the extent of the ', name, ' traced')))
      })
    }
  }
  if (nrow(read_tsv("conflict_groups.tsv"))) {
    add("four_trees", "Four trees the conflicting spans allow", "overview", function() plot_four_trees(bundle))
    add("conflict_groups", "Groups of spans that conflict", "overview", function() plot_conflict_groups(bundle))
  }

  selections <- read_tsv("selections.tsv")
  for (r in sort(as.integer(selections$rank[selections$selection == "exemplary"]))) {
    local({
      rank <- r
      add(paste0("exemplary_trees_", rank), paste0("Exemplary tree ", rank, ", with the tests behind it"),
          "exemplary", function() plot_exemplary_tree(bundle, rank, "page"))
      add(paste0("exemplary_trees_slide_", rank, "_tree"), paste0("Exemplary tree ", rank, ": the tree (slide)"),
          "exemplary", function() plot_exemplary_tree(bundle, rank, "slide_tree"))
      add(paste0("exemplary_trees_slide_", rank, "_evidence"),
          paste0("Exemplary tree ", rank, ": the tests behind it (slide)"),
          "exemplary", function() plot_exemplary_tree(bundle, rank, "slide_evidence"))
    })
  }

  filters <- Filter(function(s) identical(s$kind, "filter"), read_json("subsets.json"))
  add("forestspans_plot", "Every span, with how many families contain it", "spans",
      function() plot_forestspans(bundle))
  count_titles <- c(by_class = "How many families each group of tests allows",
                    bundles = "How many families each bundle of types allows",
                    all = "How many families all the tests allow",
                    without_adjacent = "How many families all the tests allow, leaving out two-position spans")
  for (chart in names(count_titles)) {
    local({
      which <- chart
      add(paste0("tree_count_", which), count_titles[[which]], "counts",
          function() plot_tree_counts(bundle, which))
    })
  }
  # Only when the bundle has it: the permutation test is slow enough that the
  # exporter runs it on request, so a bundle without it is normal, not broken.
  if (file.exists(file.path(data_dir, "fragmentation_test.tsv"))) {
    add("fragmentation_test_plot", "Fragmentation test: more families than the number of tests predicts?",
        "tests", function() plot_fragmentation_test(bundle))
    # The pair of bundles on their own, which the script this was ported from
    # drew as a second call for presenting them without the domain types
    # around them. Which two is a presentation choice rather than anything in
    # the data, so it is set here with the other choices that were separate
    # script calls -- and only when the bundle has both.
    syntax_phon <- c("phonologylike", "syntaxlike")
    if (all(syntax_phon %in% read_tsv("fragmentation_test.tsv")$group)) {
      add("fragmentation_test_syntax_phon_plot", "Fragmentation test: the syntax-like and phonology-like bundles",
          "tests", function() plot_fragmentation_test(bundle, groups = syntax_phon))
    }
  }
  # Only when the bundle has it, same as the fragmentation tables above.
  # The grid is every group at once; the two standalone charts are the
  # bundles someone presents on their own, so which two is a presentation
  # choice and sits here rather than in the data.
  if (file.exists(file.path(data_dir, "span_placement_test.tsv"))) {
    add("span_placement_test_by_group_plot", "Span-placement test, by group", "tests",
        function() plot_span_placement_test(bundle))
    for (group in c("syntaxlike", "phonologylike")) {
      local({
        g <- group
        if (g %in% read_tsv("span_placement_test.tsv")$group) {
          add(paste0("span_placement_test_", g, "_plot"), paste0("Span-placement test: ", g), "tests",
              function() plot_span_placement_test(bundle, groups = g, view = "standalone"))
        }
      })
    }
  }
  # The same chart from the weakest of the three nulls. Grid only: nobody has
  # asked for a standalone group here, and a chart nobody wants is still a
  # chart someone has to look at.
  if (file.exists(file.path(data_dir, "arbitrary_layers_test.tsv"))) {
    add("arbitrary_layers_test_by_group_plot", "Arbitrary-layers test, by group", "tests",
        function() plot_arbitrary_layers_test(bundle))
  }
  # Only when the bundle has it: the permutation test is slow enough that the
  # exporter runs it on request (--boundary-strength-test-permutations), so a
  # bundle without it is normal, not broken.
  if (file.exists(file.path(data_dir, "boundary_strength_test.tsv"))) {
    test_rows <- read_tsv("boundary_strength_test.tsv")
    for (group in unique(test_rows$group)) {
      local({
        g <- group
        label <- test_rows$label[match(g, test_rows$group)]
        add(paste0("boundary_strength_test_jump_", g), paste0("Boundary-strength test (jumps): ", label), "tests",
            function() plot_boundary_strength_test(bundle, group = g, statistic = "jump"))
        add(paste0("boundary_strength_test_level_", g), paste0("Boundary-strength test (levels): ", label), "tests",
            function() plot_boundary_strength_test(bundle, group = g, statistic = "level"))
      })
    }
  }
  add("boundary_strength", "How strongly each position is a left or right edge", "boundaries",
      function() plot_boundary_strength(bundle))
  add("boundary_strength_distributions", "Left and right edge strength, as curves", "boundaries",
      function() plot_boundary_strength_distributions(bundle))
  # The overlay colours its position labels by nyan1308's orthographic word;
  # a bundle without that highlight (every CCDB one) gets black labels rather
  # than a failed chart.
  overlay_highlight <- if ("orthographic_word" %in% highlights$highlight_id) "orthographic_word" else NULL
  add("boundary_strength_overlay", "Left and right edge strength, bars and curves together", "boundaries",
      function() plot_boundary_strength_overlay(bundle, highlight = overlay_highlight))
  for (f in filters) {
    local({
      id <- f$subset_id
      what <- paste0(" (", gsub("_", " ", id, fixed = TRUE), ")")
      add(paste0("forestspans_plot_", id), paste0("Every span, with how many families contain it", what), "spans",
          function() plot_forestspans(bundle, subset = id))
      add(paste0("boundary_strength_", id), paste0("How strongly each position is a left or right edge", what),
          "boundaries", function() plot_boundary_strength(bundle, subset = id))
      # The working script drew filtered overlays in a second colour pair so
      # the two are never mistaken for each other.
      add(paste0("boundary_strength_overlay_", id),
          paste0("Left and right edge strength, bars and curves together", what), "boundaries", function()
        plot_boundary_strength_overlay(bundle, subset = id, colours = c(Left = "#009E73", Right = "#CC79A7"),
                                       highlight = overlay_highlight))
    })
  }
  finish()
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

# The device for charts whose text the standard PDF fonts can't draw; see
# save_pdf() below.
if (identical(Sys.info()[["sysname"]], "Darwin") && isTRUE(capabilities("aqua"))) {
  fallback_name <- "quartz"
  fallback_device <- function(filename, ...) grDevices::quartz(file = filename, type = "pdf", ...)
} else {
  fallback_name <- "cairo"
  fallback_device <- grDevices::cairo_pdf
}

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
    # "" (the illustrations bundle's charts) means no second-level folder --
    # that bundle has exactly one topic, itself, so nesting one more level
    # would just repeat the dataset name.
    folder <- attr(p, "planarsviz_folder")
    if (is.null(folder)) stop("chart function returned no folder")
    dest <- if (nzchar(folder)) file.path(output, dataset, folder) else file.path(output, dataset)
    dir.create(dest, recursive = TRUE, showWarnings = FALSE)
    pdf_path <- file.path(dest, paste0(base, ".pdf"))
    # R's standard PDF device, whose fonts cover only Windows Latin-1, draws
    # any other character (IPA such as ʔ or ɛ) as a period, and says so with
    # a "conversion failure" warning. Only a chart that raises one is redrawn
    # with a device that can draw it (Jeff, 2026-09-23): every other chart,
    # nyan1308's included, keeps the standard device and stays as it was.
    # That device is macOS's own (Quartz, which embeds Arial) where there is
    # one, else cairo. Not cairo on a Mac: R's cairo there needs XQuartz, and
    # without it fails to load with only a warning, leaving the periods.
    # So any warning from the second device stops the chart.
    save_pdf <- function(device, fallback = FALSE) {
      unencodable <- FALSE
      withCallingHandlers(
        suppressMessages(ggplot2::ggsave(pdf_path, p, device = device, width = size[["width"]],
                                         height = size[["height"]], units = units, limitsize = FALSE)),
        warning = function(w) {
          if (fallback) stop(fallback_name, " could not draw this chart: ", conditionMessage(w), call. = FALSE)
          if (grepl("conversion failure", conditionMessage(w), fixed = TRUE)) unencodable <<- TRUE
          invokeRestart("muffleWarning")
        })
      unencodable
    }
    if (save_pdf("pdf")) {
      unlink(pdf_path)
      save_pdf(fallback_device, fallback = TRUE)
      if (!file.exists(pdf_path)) stop(fallback_name, " wrote no file")
      cat(fallback_name, " ", name, ": text the standard PDF fonts can't draw\n", sep = "")
    }
    files <- if ("pdf" %in% formats) pdf_path else character()
    if ("png" %in% formats) {
      stem <- file.path(dest, base)
      system2("pdftoppm", c("-png", "-r", "100", "-singlefile", shQuote(pdf_path), shQuote(stem)))
      files <- c(files, paste0(stem, ".png"))
      if (!"pdf" %in% formats) unlink(pdf_path)
    }
    # Relative to the dataset's own folder, where the manifest sits.
    manifest_file <- if (nzchar(folder)) file.path(folder, basename(files)) else basename(files)
    data.frame(chart = name, file = manifest_file, width = size[["width"]],
               height = size[["height"]], units = units,
               title = attr(charts, "titles")[[name]], part = attr(charts, "parts")[[name]])
  }, error = function(e) {
    failed <<- c(failed, name)
    cat("FAILED ", name, ": ", conditionMessage(e), "\n", sep = "")
    NULL
  })
  if (!is.null(result)) {
    manifest <- rbind(manifest, result)
    cat("wrote ", paste(file.path(dataset, result$file), collapse = ", "), "\n", sep = "")
  }
}
# Merge into any manifest already there, rather than replacing it: a --plots
# run draws some of the charts, and a manifest that then listed only those
# would stop describing what is in the directory. Rows this run produced win;
# older rows for charts it did not draw are kept -- but only if their file is
# still on disk and the bundle can still draw that chart. A chart the bundle
# no longer has (the fragmentation chart, after an export without
# --fragmentation-permutations) was drawn from data that is gone, so its file
# is removed and its row dropped rather than left to pass for current.
manifest_dir <- file.path(output, dataset)
dir.create(manifest_dir, recursive = TRUE, showWarnings = FALSE)
manifest_path <- file.path(manifest_dir, paste0(dataset, "_planarsviz_manifest.tsv"))
kept <- 0L
if (file.exists(manifest_path)) {
  previous <- utils::read.delim(manifest_path, stringsAsFactors = FALSE)
  if (nrow(previous) && all(names(manifest) %in% names(previous))) {
    gone <- previous[!previous$chart %in% names(charts), , drop = FALSE]
    if (nrow(gone)) {
      unlink(file.path(manifest_dir, gone$file))
      cat("removed ", paste(file.path(dataset, gone$file), collapse = ", "),
          ": this bundle no longer has these charts\n", sep = "")
    }
    previous <- previous[previous$chart %in% names(charts), , drop = FALSE]
    stale <- previous[!previous$chart %in% manifest$chart, names(manifest), drop = FALSE]
    stale <- stale[file.exists(file.path(manifest_dir, stale$file)), , drop = FALSE]
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
