# This file runs every time R starts in NonCollaborative/. It does two things:
# it refuses to run the archived scripts, and it points R at the pinned package
# versions.

# ---------------------------------------------------------------------------
# 1. Refuse to run anything under OlderFiles/.
#
# OlderFiles/ holds superseded code. Most of it is simply old, but
# OlderFiles/planarsviz_superseded/ is worse than old: those scripts still
# work. They are the originals the planarsviz package replaced, kept because
# the porting checks run them to prove the package draws what they drew.
#
# The accident this prevents: running one of them directly. The checks read
# each script's text and evaluate it in memory with ggsave disabled, so
# nothing is written. Run the same file with Rscript and ggsave is live, and
# it writes old-code PDFs over charts the package produced -- silently, since
# the filenames are the same and nothing records which program made them.
#
# This catches the direct run and nothing else. The checks do not invoke these
# files through Rscript, so they are unaffected; confirmed when this was added
# by running all 21 afterwards.
#
# To run one deliberately, say so:
#   PLANARS_RUN_ARCHIVED=1 Rscript OlderFiles/...
local({
  if (nzchar(Sys.getenv("PLANARS_RUN_ARCHIVED"))) return(invisible(NULL))

  args <- commandArgs()
  file_arg <- grep("^--file=", args, value = TRUE)
  if (length(file_arg) != 1L) return(invisible(NULL))

  script <- normalizePath(sub("^--file=", "", file_arg[[1L]]), mustWork = FALSE)
  archive <- normalizePath("OlderFiles", mustWork = FALSE)
  if (!startsWith(script, paste0(archive, .Platform$file.sep))) {
    return(invisible(NULL))
  }

  message(
    "\nRefusing to run an archived script.\n\n  ", script, "\n\n",
    "Everything under OlderFiles/ has been superseded. The scripts in\n",
    "OlderFiles/planarsviz_superseded/ still work, which is the danger: the\n",
    "porting checks run them in memory with ggsave disabled, but running one\n",
    "directly writes its old output straight over charts the planarsviz\n",
    "package produced, under the same filenames.\n\n",
    "To draw a chart, use the package:\n",
    "  Rscript scripts/render_planarsviz.R --bundle results/planarsviz/nyan1308\n\n",
    "To check a chart against the script it replaced, use its check:\n",
    "  Rscript scripts/planarsviz_checks/check_<name>.R\n\n",
    "If you really do mean to run this file, say so:\n",
    "  PLANARS_RUN_ARCHIVED=1 Rscript <file>\n"
  )
  quit(status = 1, save = "no")
})

# ---------------------------------------------------------------------------
# 2. Use the pinned package versions.
#
# renv pins the versions of the R packages this project's charts were drawn
# with. renv.lock records them; renv/activate.R puts the project's own package
# library on the search path.
#
# The namespaces check below is turned off because renv sets it off itself.
# Bioconductor is enabled here (ggtree comes from there), which makes
# activate.R load BiocManager before renv has finished starting up -- and renv
# then warns that BiocManager "was loaded before renv activated this project".
# The warning is about renv's own bootstrap, not about anything in this
# project, and it carries no information a person could act on. Left on, it
# prints on every single R run, including into the porting checks' output,
# which is compared against a snapshot -- so it would read as 21 failures.
options(renv.config.namespaces.check = FALSE)

source("renv/activate.R")
