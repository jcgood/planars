if (!require("pacman")) install.packages("pacman")
library(pacman)
p_load(ggsci,
       tidyverse)

domains <- read_tsv("../planar_tables/domains_nyan1308.tsv")
tests <- filter(domains) # vacuous at the moment


leftedges = tests$Left_Edge
leftedgedf = as.data.frame(leftedges)
leftedgeCounts = count(leftedgedf, leftedges)
lmin = min(leftedgeCounts$leftedges)
lmax = max(leftedgeCounts$leftedges)

# Adds in zeroes for edges in range of left edges where there happen to
# be no diagnostics. This is position 9 for Chichewa/
for(n in lmin:lmax) {
	if (n %in% leftedgeCounts$leftedges) { }
	else(leftedgeCounts[nrow(leftedgeCounts) + 1,] = c(n,0))
		}
		
noleftpositions = nrow(leftedgeCounts)
leftprob = rep(1/noleftpositions, noleftpositions)

leftchisq = chisq.test(leftedgeCounts$n, p=leftprob)

rightedges = tests$Right_Edge
rightedgedf = as.data.frame(rightedges)
rightedgeCounts = count(rightedgedf, rightedges)
lmin = min(rightedgeCounts$rightedges)
lmax = max(rightedgeCounts$rightedges)

for(n in lmin:lmax) {
	if (n %in% rightedgeCounts$rightedges) { }
	else(rightedgeCounts[nrow(rightedgeCounts) + 1,] = c(n,0))
		}
		
norightpositions = nrow(rightedgeCounts)
rightprob = rep(1/norightpositions, norightpositions)

rightchisq = chisq.test(rightedgeCounts$n, p=rightprob)

# I don't recall the motivation for this. It tests the distribution of left edges
# by the size of each test. Maybe it was an attempt at quantal patterning?
totalPositions = max(tests$Right_Edge)
for(n in 2:(totalPositions-1)) {
	
	nTests = filter(tests, Size == n)
	
	if (dim(nTests)[1] == 0) { } # skip empty ones
	
	else{
		nleftedges = nTests$Left_Edge
		nleftedgedf = as.data.frame(nleftedges)
		nleftedgeCounts = count(nleftedgedf, nleftedges)
		
		for(m in 1:(totalPositions - (n-1))) {
			if (m %in% nleftedgeCounts$nleftedges) { }
			else(nleftedgeCounts[nrow(nleftedgeCounts) + 1,] = c(m,0))
			}

		print(n)
		print(nleftedgeCounts)
	
		nleftpositions = totalPositions - (n-1)
		nprob = rep(1/nleftpositions, nleftpositions)
		nchisq = chisq.test(nleftedgeCounts$n, p=nprob)
		
		print(n)
		print(nchisq)
	
		}

	}
