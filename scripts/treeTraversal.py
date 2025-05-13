# Takes three sets of doculects and returns those at the intersection of all three sets
# and set1 and set2 and set2 and set3. Outputs stabilities alongside those, too
# Used now for Abar, Buu, and Munfabli


import pandas
import os
from collections import defaultdict

# Storage folders
planarFolder = "../domains/"
domainFile = "domains_nyan1293_test.tsv"

domains = defaultdict(list) # trying this to avoid try/except
trees = [ ]
domainsCollapsed = [ ]
treereductions = [ ]

def main():

	domainRows = pandas.read_csv(planarFolder + os.sep + domainFile,sep="\t")
	
	for index, row in domainRows.iterrows():
	
		label = row["Test_Labels"]
		type_ = row["Domain_Type"]
		left = row["Left_Edge"]
		right = row["Right_Edge"]
		size = row["Size"]
		
		domain = {	"label" : label, 
					"type" 	: type_,
					"left" 	: left,
					"right" : right,
					"size" : size, # redundant, but why not?
					}
		
		domains[size].append(domain) # Defaultdict makes this easier, use in future
		
		span = [left, right]
		
		# Using this to get a list of all domains for later use in tree analysis
		if span in domainsCollapsed: pass
		else: domainsCollapsed.append(span)
	
	maxDomain = max(domains.keys())
	minDomain = min(domains.keys())
	traverse(maxDomain, "root", ["root"], minDomain)

	treeCount = 1
	for tree in trees:
		#print(treeCount, tree)
		treeCount += 1
	
	# The algorithm produces subset trees of larger trees for reasons that I have not
	# worked out. This is intended to remove those
	# I'm going to try to keep looping until trees stop being excluded since there
	# are subsets in subsets in subsets
	excludedtrees = [ ]
	excludedCount = -1 # dummy
	prunedtrees = trees.copy()
	prunedtrees1 = trees.copy() # I'm going to remove elements from prunedtrees; so I need a copy
	prunedtrees2 = trees.copy() # I don't think I need a second copy, but I can read things easier this year, a reference may be enough
	previousExclusions = 0
	# Keep removing trees until no more can be removed
	while excludedCount != previousExclusions:
		excludedCount = previousExclusions
		for tree1 in prunedtrees1:
			for tree2 in prunedtrees2:
				# tree 2 ends up being the smaller one, if one is smaller
				if tree1 == tree2: pass
				elif all(e in tree1 for e in tree2):
					if tree2 in excludedtrees: pass
					else: excludedtrees.append(tree2)
					if tree2 in prunedtrees: prunedtrees.remove(tree2)
		previousExclusions = len(excludedtrees)	
	
	
	treeCount = 1
	print("Maximal trees")
	for tree in sorted(prunedtrees, key=len, reverse=True):
		print(treeCount, tree[1:], sep="\t") # remove 'root'
		treeCount += 1	
		print("")

	
	treeCount = 1
	print("Maximal newicks")
	for tree in sorted(prunedtrees, key=len, reverse=True):
		tree = tree[1:] # remove 'root'
		newicktree = newick(tree)
		rtree = "tree" + str(treeCount) + " = read.tree(text=\"" + newicktree + ";\")"
		print(rtree)
		rplot = "treeplot" + str(treeCount)  + " = ggtree(tree" + str(treeCount) + ", layout='slanted', ladderize = FALSE, alpha=.05) + layout_dendrogram() + geom_tiplab() + theme(panel.background = element_blank(), plot.background = element_blank())"
		print(rplot)
		treeCount += 1
	print("")
	
# layout <- c(
# area(t = 2, l = 1, b = 5, r = 4),
# area(t = 1, l = 3, b = 3, r = 5)
# )
# p1 + p2 +
# plot_layout(design = layout)


	# Trying to find minimum tree set that covers all domains
	print("Domains collapsed into unique domains")
	print(domainsCollapsed)
	print("\n")
	destroyDomains = domainsCollapsed.copy()
	getTopReducers(prunedtrees, destroyDomains, [])
		
	print("Reduced trees that still cover all domains.")
	for treereduction in sorted(treereductions, key=len):
		print(len(treereduction), treereduction, sep="\t")
		#for tree in treereduction:
		#	newicktree = newick(tree)
		#	print(newicktree)
		print("\n")
		pass
			

#	destroyDomains = domainsCollapsed.copy()
#	for tree in sorted(prunedtrees, key=len, reverse=True):
#		
#		# Get rid of 'root' place holder node
#		derootedTree = tree[1:]
#
#		if destroyDomains == []:
#			break
#		else:
#			reducingTree = False
#			for span in derootedTree:
#				if span in destroyDomains: destroyDomains.remove(span)
#				reducingTree = True
#			if reducingTree:
#				print(derootedTree)
#				pass



# Workhorse function
# This will be called recursively to traverse the tree
# I hope the logic is right
def traverse(size, parentSpan, tree, minDomain):

	# To do: I don't think this will handle two small domains at different spans contained
	# in a larger parent (e.g., add another two element domain to Chichewa)
	# Probably, it means a condition on the splitting in a for loop below for
	# When a span size has multiple domains

	#print("This is the current tree:", tree)

	# Exit condition
	if size == minDomain:
		# The algorithm generates duplicate trees (for reasons I did not work out)
		# So, we filter on that here
		if tree in trees:
			pass
		else: trees.append(tree)
		#print("Saving Tree condition 1:", "\n", tree)
		return
				
	# If we escape the exit condition, find next domain size that has spans
	domain, size = getNextDomain(size, parentSpan, tree, minDomain)

	# If the getNextDomain returns False (because it reached the minDomain internally)
	# Then, that becomes another exit condition
	if not domain:
		if tree in trees:
			pass
		else: trees.append(tree)
		#print("Saving Tree condition 2:",  "\n", tree)
		return
	
	# Go through each test in domain size, they may have different spans
	seenSpans = [ ]
	for test in domain:
		
		# To do: See note above, maybe here I need to see if the tests in the domain
		# nest or not and, if not, have a new condition
		
		left = test["left"]
		right = test["right"]
		
		testSpan = [left, right]
		#print("Processing test span:", testSpan)

		# This domain span is in the parent, so we can keep building this tree and
		# Add this span to the good spans in this domain size
		if contains(parentSpan,testSpan):
			#print("The test span is contained in the parent", parentSpan, testSpan)
			if testSpan not in seenSpans:
				seenSpans.append(testSpan)
		
		# This overgenerates trees, but we will prune them later
		# If it finds a span that doesn't fit in the parent, it rebuilds the tree
		# from the lowest enclosing parent. Depending on the state of the tree, this
		# can produce extra trees
		else:
			#print("The test span is not contained in the parent", parentSpan, testSpan)
			# Go back up to rebuild new tree from here
			
			enclosingSpan = getEnclosingParent(size,testSpan,tree)
			#print("The span's nearest enclosing span is", enclosingSpan, testSpan)

			enclosingIndex = tree.index(enclosingSpan)
			enclosingTree = tree[:enclosingIndex+1]
			#print("The span and its enclosing tree are:", testSpan, enclosingTree)
			newtree = enclosingTree.copy()
			newtree.append(testSpan)
			traverse(size-1, testSpan, newtree, minDomain)
			# We keep jumping ahead in the traversal to avoid certain kinds of lost
			# trees. This solution seems to work by always pushing the traversal forward.
			#It generates lots of extra trees that aren't maximal and get pruned later.
			traverse(size-2, testSpan, newtree, minDomain)

		
	# There may just be one span, but, if not, here the function can be called
	# multiple times to do a tree search		
	if seenSpans:
		#print("Processing subspans:", seenSpans)
		for span in seenSpans:
			newtree = tree.copy()
			newtree.append(span)
			traverse(size-1, span, newtree, minDomain)	
			# We keep jumping ahead in the traversal to avoid certain kinds of lost
			# trees. This solution seems to work by always pushing the traversal forward.
			#It generates lots of extra trees that aren't maximal and get pruned later.
			traverse(size-2, testSpan, newtree, minDomain)

	# If we reached here, then nothing in this domain is enclosed by the
	# parent span. So, we need to skip this level and see what else might be there
	# that this parent encloses
	else:		
		#print("I didn't contain anything here:", parentSpan, size)
		traverse(size-2, parentSpan, tree, minDomain)



		
#Minor helper functions

def contains(parentSpan,childSpan):
	
	if parentSpan == "root":
		return(True)
	
	else:
		parentLeft = parentSpan[0]
		parentRight = parentSpan[1]
		childLeft = childSpan[0]
		childRight = childSpan[1]
		
		if childLeft >= parentLeft and childRight <= parentRight:
			return(True)
		else: return(False)


def getNextDomain(size, parentSpan, tree, minDomain):

	domain = domains[size]

	if domain:
		return(domain, size)
	elif size <= minDomain:
		return(False,False)
	else:
		return(getNextDomain(size-1, parentSpan, tree, minDomain))


def getEnclosingParent(size, span, tree):
		
	higherDomain = domains[size+1]
	#print("Trying to find enclosing parent:", size, span, tree)
	if higherDomain == []:
		return(getEnclosingParent(size+1, span, tree))
	
	for test in higherDomain:
		lefttest = test["left"]
		righttest = test["right"]
		enclosingSpan = [lefttest, righttest]
		leftspan, rightspan = span
		#print("I am currently comparing the spans:", enclosingSpan, span)
		if leftspan >= lefttest and rightspan <= righttest:
			if enclosingSpan in tree:
				#print("I have found the encolosing span:", enclosingSpan, span)
				return(enclosingSpan)
			else: return(getEnclosingParent(size+1, span, tree))
		else:
			return(getEnclosingParent(size+1, span, tree))

# Workhorse function to find minimum covering
# This really confused me because of the way lists are handled in Python.
# Once I copied them more often, it worked better.
def getTopReducers(reducingtrees, reducingdomains, reducedTreeSet):

	# Exit condition; all domains accounted for
	if reducingdomains == []:
		if reducedTreeSet in treereductions: pass
		else:
			# Python list assignment eludes me. I need copies or things break
			storedReducedTree = reducedTreeSet.copy()
			treereductions.append(storedReducedTree)
		return

	# For each tree in the set, find out how much it reduces the currently non-accounted-for domains
	reductions = defaultdict(list)
	for reducingtree in reducingtrees:		
		reducingtree = reducingtree[1:] # remove 'root'
		reduceddomains = reducingdomains.copy()		
		for reducingtreeDomain in reducingtree:
			if reducingtreeDomain in reduceddomains: reduceddomains.remove(reducingtreeDomain)
		reduction = len(reducingdomains) - len(reduceddomains)
		reductions[reduction].append(reducingtree)
		#print("Here is a reduction count:", reduction, reducingtree)
		
	# Get the trees that do the maximal reduction for this domain set
	maxReduction = max(reductions.keys())
	maxReducedTrees = reductions[maxReduction]
	#print("Number of maximal reduction trees:", len(maxReducedTrees))
	#print("Maximal reduction trees:", maxReducedTrees)

	# I learned that I really don't understand how Python handles variables.
	# Since everything is a reference, the algorithm kept adding elements to
	# the same list and the list identity did not reset with each function call
	# So, I need a copy here to keep that from happening.
	
	# Run through the maximum reducing trees, work out their reductions
	# Recursively call function
	workingTreeSet = reducedTreeSet.copy()
	for maxReducedTree in maxReducedTrees:

		#print("This is a maximum reducing tree:", maxReducedTree)

		workingTreeSet.append(maxReducedTree)

		reduceddomains = reducingdomains.copy()

		for maxTreeDomain in maxReducedTree:
			if maxTreeDomain in reduceddomains: reduceddomains.remove(maxTreeDomain)
		
		#print("Domains left", reduceddomains)
		#print("Reduced tree set", reducedTreeSet)
		getTopReducers(reducingtrees,reduceddomains,workingTreeSet)

def newick(tree):
	
	maximal = tree[0] # First element should be maximal span
	revtree = list(reversed(tree))
	
	prevleftedge = 0 # placeholder
	prevrightedge = 0
	justlabeledanode = False # needed to get commas to come out right
	seenpositions = [ ]
	newicktree = "("
	for span in revtree:


		leftedge, rightedge = span
		spanpositions = range(leftedge, rightedge + 1) # second element of range is stop condition, not included

		leftappend =  ""
		rightappend = ""
		for spanposition in spanpositions:
			if spanposition in seenpositions:
				pass
			else:
				if spanposition <= prevleftedge:
					leftappend = leftappend + str(spanposition) + ", "
					seenpositions.append(spanposition)
				elif spanposition >= prevrightedge: # need to handle the comma interfix problem
					if justlabeledanode:
						rightappend = rightappend + ", " + str(spanposition)
						justlabeledanode = False # hack to get punctuation right			
					elif rightappend == "":
						rightappend = rightappend + str(spanposition)
					else:
						rightappend = rightappend + ", " + str(spanposition)
					seenpositions.append(spanposition)
				else: print("Span position not written yet, but probable should have been.")

		prevleftedge = leftedge
		prevrighedge = rightedge

		newicktree = "(" + leftappend + newicktree + rightappend + ") " + str(leftedge) + "-"+ str(rightedge)
		justlabeledanode = True
				
	
	newicktree = newicktree +  ")"
	
	return(newicktree)




main()