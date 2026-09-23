# R packages this project needs that no other R file mentions.
#
# renv works out what to pin by reading every R file for library() calls.
# That misses tools invoked from outside R -- and roxygen2 is one:
# tests/test_roxygen_up_to_date.py runs it through Rscript to check that the
# package's NAMESPACE and man/ still match what the roxygen comments in
# planarsviz/R/ would generate.
#
# Left unpinned, that test does not fail -- it *skips*, because it skips when
# roxygen2 is not installed, and the project library would not have it. A
# skip reads as a pass, so the drift guard would quietly stop guarding.
#
# The version matters as well as the presence. roxygen2 stamps a
# Config/roxygen2/version line into DESCRIPTION and different versions write
# man/ differently, so an unpinned roxygen2 can fail the guard over nothing.
#
# This file is never run. It exists so renv reads the line below.

library(roxygen2)
