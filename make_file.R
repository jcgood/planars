# --- CONFIG ----------------------------------------------------------

# Set this to your folder; or leave "" to use the script's folder (see note below)
DATA_DIR <- "D:/planars/01_planar_input"

# --- HELPERS ---------------------------------------------------------

resolve_path <- function(filename) {
  # If DATA_DIR is set, use it; otherwise use the directory of this script
  # In RStudio, this_script_dir() isn't always trivial; easiest is to set DATA_DIR.
  if (nzchar(DATA_DIR)) {
    file.path(DATA_DIR, filename)
  } else {
    # Fallback: current working directory
    file.path(getwd(), filename)
  }
}

infer_language_id_from_planar_filename <- function(planar_filename) {
  stem <- tools::file_path_sans_ext(basename(planar_filename))
  prefix <- "planar_"
  if (!startsWith(stem, prefix)) {
    stop(sprintf("Expected planar filename to start with '%s', got '%s'", prefix, planar_filename))
  }
  lang_id <- trimws(substr(stem, nchar(prefix) + 1, nchar(stem)))
  lang_id <- sub("-[0-9]{8}$", "", lang_id)
  if (!nzchar(lang_id)) stop(sprintf("Could not infer language id from '%s'", planar_filename))
  lang_id
}

# --- CORE ------------------------------------------------------------

build_element_index <- function(filename) {
  # Returns a data.frame analogous to the Python dict values:
  # key = element_plain@pos
  # columns: key, Position_Number, Position_Name, Language_ID, Element_Plain
  
  lang_id <- infer_language_id_from_planar_filename(filename)
  path <- resolve_path(filename)
  
  if (!file.exists(path)) {
    stop(paste0(
      "Could not find file:\n  ", path, "\n",
      "DATA_DIR is:\n  ", ifelse(nzchar(DATA_DIR), DATA_DIR, getwd()), "\n",
      "(R analogy: check getwd()/setwd() or DATA_DIR)"
    ))
  }
  
  df <- read.delim(path, sep = "\t", header = TRUE, stringsAsFactors = FALSE, quote = "", check.names = FALSE)
  
  required_cols <- c("Class_Type", "Elements", "Position_Name")
  missing <- setdiff(required_cols, names(df))
  if (length(missing) > 0) {
    stop(sprintf("Missing required column(s): %s", paste(missing, collapse = ", ")))
  }
  
  out_key <- character(0)
  out_pos <- integer(0)
  out_posname <- character(0)
  out_lang <- character(0)
  out_elem <- character(0)
  
  seen <- new.env(parent = emptyenv())
  
  add_element <- function(element_plain, pos, position_name) {
    element_plain <- trimws(ifelse(is.na(element_plain), "", element_plain))
    if (!nzchar(element_plain)) return(invisible(NULL))
    
    key <- paste0(element_plain, "@", pos)
    if (exists(key, envir = seen, inherits = FALSE)) {
      stop(sprintf("Duplicate unique key '%s' (element repeated within same position?)", key))
    }
    assign(key, TRUE, envir = seen)
    
    out_key <<- c(out_key, key)
    out_pos <<- c(out_pos, pos)
    out_posname <<- c(out_posname, position_name)
    out_lang <<- c(out_lang, lang_id)
    out_elem <<- c(out_elem, element_plain)
    
    invisible(NULL)
  }
  
  # Enumerate positions starting at 1 (like Python enumerate(..., start=1))
  for (pos in seq_len(nrow(df))) {
    class_type <- tolower(trimws(df$Class_Type[pos]))
    elements_raw <- trimws(df$Elements[pos])
    position_name <- trimws(df$Position_Name[pos])
    
    if (!nzchar(elements_raw)) next
    
    if (class_type == "open") {
      add_element(elements_raw, pos, position_name)
      
    } else if (class_type == "list") {
      parts <- strsplit(elements_raw, ",", fixed = TRUE)[[1]]
      parts <- trimws(parts)
      for (p in parts) add_element(p, pos, position_name)
      
    } else {
      stop(sprintf("Unexpected Class_Type '%s' at position %d", class_type, pos))
    }
  }
  
  data.frame(
    key = out_key,
    Position_Number = out_pos,
    Position_Name = out_posname,
    Language_ID = out_lang,
    Element_Plain = out_elem,
    stringsAsFactors = FALSE,
    check.names = FALSE
  )
}

generate_test_files <- function(test_type, element_index_df) {
  # element_index_df = output of build_element_index()
  
  param_path <- resolve_path(paste0(test_type, "_parameters.tsv"))
  if (!file.exists(param_path)) {
    stop(sprintf("Could not find parameter file:\n  %s", param_path))
  }
  
  params_df <- read.delim(param_path, sep = "\t", header = FALSE, stringsAsFactors = FALSE, quote = "", check.names = FALSE)
  
  if (ncol(params_df) < 2) {
    stop(sprintf("%s must have at least 2 columns: language_id + >=1 parameter name.", basename(param_path)))
  }
  
  # Build lang -> param names (list)
  lang_to_paramnames <- list()
  for (i in seq_len(nrow(params_df))) {
    lang <- trimws(as.character(params_df[i, 1]))
    if (!nzchar(lang)) next
    
    param_names <- as.character(params_df[i, 2:ncol(params_df)])
    param_names <- trimws(param_names)
    param_names <- param_names[nzchar(param_names)]
    
    if (length(param_names) > 0) {
      lang_to_paramnames[[lang]] <- param_names
    }
  }
  
  # Split elements by language
  langs <- unique(element_index_df$Language_ID)
  written <- character(0)
  
  for (lang_id in langs) {
    if (is.null(lang_to_paramnames[[lang_id]])) {
      stop(sprintf("No parameter row found in %s for language '%s'.", basename(param_path), lang_id))
    }
    param_names <- lang_to_paramnames[[lang_id]]
    
    items <- element_index_df[element_index_df$Language_ID == lang_id, c("Position_Number", "Element_Plain", "Position_Name")]
    # Sort by Position_Number asc, then element alpha (case-insensitive then original)
    o <- order(items$Position_Number, tolower(items$Element_Plain), items$Element_Plain)
    items <- items[o, , drop = FALSE]
    
    # Build output rows
    n <- nrow(items)
    out <- data.frame(
      Element = character(n),
      Position_Name = character(n),
      Position_Number = integer(n),
      stringsAsFactors = FALSE,
      check.names = FALSE
    )
    
    # Add param columns
    for (pname in param_names) out[[pname]] <- character(n)
    
    for (i in seq_len(n)) {
      pos <- items$Position_Number[i]
      element_plain <- items$Element_Plain[i]
      pos_name <- items$Position_Name[i]
      
      # Excel hyphen workaround
      if (startsWith(element_plain, "-") || endsWith(element_plain, "-")) {
        element_plain <- paste0("[", element_plain, "]")
      }
      
      out$Element[i] <- element_plain
      out$Position_Name[i] <- pos_name
      out$Position_Number[i] <- pos
      
      if (trimws(pos_name) == "Keystone") {
        for (pname in param_names) out[[pname]][i] <- "NA"
      } else {
        for (pname in param_names) out[[pname]][i] <- ""
      }
    }
    
    out_path <- resolve_path(paste0(test_type, "_", lang_id, "_blank.tsv"))
    
    # Write TSV without quoting (closest to csv.QUOTE_NONE)
    write.table(
      out,
      file = out_path,
      sep = "\t",
      row.names = FALSE,
      col.names = TRUE,
      quote = FALSE
    )
    
    written <- c(written, out_path)
  }
  
  written
}

# --- RUN -------------------------------------------------------------

element_index <- build_element_index("planar_stan1293-20260209.tsv")
written <- generate_test_files("ciscategorial", element_index)

for (p in written) {
  cat("Wrote:", p, "\n")
}
