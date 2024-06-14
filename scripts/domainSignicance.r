leftedges = tests$Left_Edge
leftedgedf = as.data.frame(leftedges)
leftedgeCounts = count(leftedgedf, leftedges)
lmin = min(leftedgeCounts$leftedges)
lmax = max(leftedgeCounts$leftedges)

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

		#print(nleftedgeCounts)
	
		nleftpositions = totalPositions - (n-1)
		nprob = rep(1/nleftpositions, nleftpositions)
		nchisq = chisq.test(nleftedgeCounts$n, p=nprob)
		
		print(n)
		print(nchisq)
	
		}

	}
