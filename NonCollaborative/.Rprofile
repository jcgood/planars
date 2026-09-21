# renv pins the versions of the R packages this project's charts were drawn
# with. renv.lock records them; renv/activate.R puts the project's own package
# library on the search path whenever R starts in this directory.
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
