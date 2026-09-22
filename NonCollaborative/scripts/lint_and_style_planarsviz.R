#!/usr/bin/env Rscript
# Run styler then lintr over r/planarsviz -- the manual entry point for phase
# D's tooling pass (2026-09-22). tests/test_styler_up_to_date.py and
# tests/test_lint_clean.py call styler::style_pkg()/lintr::lint_package()
# directly rather than sourcing this file, so it is not part of either guard;
# it exists so a person (or Claude) fixing a finding by hand has one command
# to run, and so this project's dependency scan sees a real library() call
# for both packages -- without one, renv has no R source to notice either is
# used, and reports the project as out-of-sync every time R starts here even
# though both are correctly pinned in renv.lock.
#
# Run from NonCollaborative/:
#   Rscript scripts/lint_and_style_planarsviz.R
library(styler)
library(lintr)

style_pkg("r/planarsviz", filetype = "R")
lints <- lint_package("r/planarsviz")
print(lints)
if (length(lints)) quit(status = 1)
