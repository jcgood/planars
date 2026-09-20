# Where the R scripts the planarsviz library replaced now live.
#
# These checks prove the library draws what the old scripts drew, by running
# the old script in memory and comparing. That makes the old scripts evidence:
# they are archived rather than deleted, and the checks stop working if they
# go. See OlderFiles/planarsviz_superseded/README.md.
#
# One place holds the path so that moving the archive again is one edit, not
# eleven. Every check sources this file and calls superseded():
#
#   source("scripts/planarsviz_checks/superseded.R")
#   src <- readLines(superseded("results", "laminar_spanchart.r"))
#
# Paths are relative to NonCollaborative/, which is where the checks run from.
#
# superseded.py is the twin of this file, for the checks written in Python.
# Both must name the same directory.

SUPERSEDED_DIR <- file.path("OlderFiles", "planarsviz_superseded")

superseded <- function(...) {
  path <- file.path(SUPERSEDED_DIR, ...)
  if (!file.exists(path)) {
    stop("Superseded script not found: ", path,
         "\nThese scripts are the evidence the porting checks compare against.",
         " If one is missing, restore it from git rather than skipping the check.",
         call. = FALSE)
  }
  path
}
