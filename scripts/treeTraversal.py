import pandas
import os
from collections import defaultdict

# Storage folders
planarFolder = "../domains/"
#domainFile = "domains_nyan1293_test.tsv"
domainFile = "domains_nyan1308.tsv"
#domainFile = "domains_chac.tsv"
#domainFile = "domains_yupik.tsv"
#domainFile = "domains_mart.tsv"
#domainFile = "catalanPlus.tsv"

domains = defaultdict(list) # trying this to avoid try/except
trees = [ ]
domainsCollapsed = [ ]
treereductions = [ ]
domainStrength = defaultdict(int) # store tests for a domain

def main(subset=None, color="black", tpfx=""):

	domainRows = pandas.read_csv(planarFolder + os.sep + domainFile,sep="\t")
	
	for index, row in domainRows.iterrows():
	
		label = row["Test_Labels"]
		type_ = row["Domain_Type"]
		left = row["Left_Edge"]
		right = row["Right_Edge"]
		size = row["Size"]
		
		# See if line is commented out
		#if label.startswith("#"):
		#	print(label)
		#	continue
		
		# data integrity check
		calculatedSize = right - left + 1
		if size != calculatedSize:
			print("Mismatch between stored size and calculated size", row)
			quit()
		
		domain = {	"label" : label, 
					"type" 	: type_,
					"left" 	: left,
					"right" : right,
					"size" : size, # redundant, but why not?
					}
		
		# Filter domains of size 1
		#if size > 1: domains[size].append(domain) # Defaultdict makes this easier, use in future
		
		if size > 1:

			if subset is None:
				domains[size].append(domain) # Defaultdict makes this easier, use in future

			elif type_ in subset:
				domains[size].append(domain) # Defaultdict makes this easier, use in future
		

			#if type_ == "morphosyntactic" or type_ == "length" or type_ == "intonational" or type_ == "tonosegmental": # filter by type, it breaks without a full domain
			# if doing this, also need to make domains just for this type or minimal tree algorithm breaks
			# to self: trees reduce significantly when we don't mix morphosyntax and phonology
			# There's a "top-reducers" recursion problem when I just do phonological or morphosyntactic
			#else:
			#	color = "red"
		
		
		# store domain strength counts
		spanID = (left, right) # store as tuple
		domainStrength[spanID] += 1 # default dict as int defaults to 0

			
		# mapping based on order, not keys in R even though I can name a number
		# must only do domains in the tree
		
		span = [left, right]
				
		# Using this to get a list of all domains for later use in tree analysis
		if span in domainsCollapsed: pass
		else: domainsCollapsed.append(span)
		
	totalTests = sum(domainStrength.values())
	
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

	totalTrees = treeCount - 1 # counter had been set to 1 to avoid zero numbering
	alphaval = str(round(1/totalTrees, 6))
	treeCount = 1

	rout = open(tpfx + 'constituencyforest-all.r', 'w')
	#print("Maximal newicks", file=rout)
	print("library(ape)", file=rout)
	print("library(ggplot2)", file=rout)
	print("library(ggtree)", file=rout)
	print("library(patchwork)", file=rout)
	print("", file=rout)
	
	# to label the planar positions
	print("posLabel = list(\"1\" = \"QM\",", file=rout)
	print("\"2\" = \"PreSbj\",", file=rout)
	print("\"3\" = \"Sbj\",", file=rout)
	print("\"4\" = \"PostSbj\",", file=rout)
	print("\"5\" = \"Neg1\",", file=rout)
	print("\"6\" = \"SM\",", file=rout)
	print("\"7\" = \"Neg2\",", file=rout)
	print("\"8\" = \"TAM\",", file=rout)
	print("\"9\" = \"OM\",", file=rout)
	print("\"10\" = \"Root\",", file=rout)
	print("\"11\" = \"Ext\",", file=rout)
	print("\"12\" = \"STAT\",", file=rout)
	print("\"13\" = \"CAUS\",", file=rout)
	print("\"14\" = \"APPL\",", file=rout)
	print("\"15\" = \"REC\",", file=rout)
	print("\"16\" = \"PASS\",", file=rout)
	print("\"17\" = \"FV\",", file=rout)
	print("\"18\" = \"2P\",", file=rout)
	print("\"19\" = \"Enc\",", file=rout)
	print("\"20\" = \"Obj1\",", file=rout)
	print("\"21\" = \"Obj2\",", file=rout)
	print("\"22\" = \"PostObj\")", file=rout)

	print("", file=rout)
	
	for tree in sorted(prunedtrees, key=len, reverse=True):

		tree = tree[1:] # remove 'root'

		newicktree = newick(tree)
		
		treeNo = tpfx + "tree" + str(treeCount)
		rtree = treeNo + " = read.tree(text=\"" + newicktree + ";\")"
		print(rtree, file=rout)

		# After a lot of experimentation, to get the thickness to work, I need the
		# category labels to be in alphabetical order matching the strength map list
		# so I need to turn numbers into letters. That's done with chr 
		labelstart = 97 # 97 corresponds to "a"
		
		# reorder the spans by their weight (to get the r drawing system to work out)
		sortedSpans = sorted(tree, key = lambda e: domainStrength[tuple(e)])			

		# code courtesy of copilot, turn domains into list
		domains_toR = [f"{chr(labelstart+i)} = c({x}, {y})" for i, (x, y) in enumerate(sortedSpans)]
		domainsC = "list(" + ", ".join(domains_toR) + ")" # these are R factors
		groupedTree =  treeNo + "grouped = groupOTU(" + treeNo + ", " + domainsC + ")"

		print(groupedTree, file=rout)

		# Get weighting mapping from domains
		# list needs to follow order of the spans in the grouping above
		strengthR = "strengthMap" +  str(treeCount) + " = c( .5, " # why do I need the initial .5?; seems to be for ungrouped things
		for span in sortedSpans:
			strengthKey = tuple(span)
			strength = domainStrength[strengthKey]
			strengthR += str(strength) + ", "
		strengthR = strengthR[:-2] # remove trailing comma
		strengthR += ")"
		print(strengthR, file=rout)
		
		treeplotNo = tpfx + "treeplot" + str(treeCount)

		rplot = ( treeplotNo +
				  " = ggtree(" + treeNo + "grouped,\n" +
				  "\taes(size=(" + "strengthMap" +  str(treeCount) + "[group])),\n" +
				  "\tlayout='slanted', ladderize = FALSE, alpha=" + alphaval + ", color=\"" + color + "\") +\n" +
				  "\tlayout_dendrogram() +\n"
				  )
		
		if treeCount == 1: # different logic for first one to only draw labels once for cleaner output
			rplot += ( "\tgeom_tiplab(geom=\"label\", size=5, angle=0, offset=-1, hjust=.5, alpha=1" + ",\n" +
					   "\taes(label=paste(label, posLabel[label], sep=\"\\n\")), lineheight = 1) +\n"
					 )
		else: # Still need transparent labels to get alignment to work
			rplot += ( "\tgeom_tiplab(geom=\"label\", size=5, angle=0, offset=-1, hjust=.5, alpha=0" + ",\n" +
					   "\taes(label=paste(label, posLabel[label], sep=\"\\n\")), color=\"transparent\", lineheight = 1) +\n"
					 )

		rplot += ( "\ttheme(panel.background = element_blank(),\n" +
				   "\tplot.background = element_blank()) +\n" +
				   "\t\ttheme(legend.position=\"none\") +\n" +
				   "\t\tscale_size_identity()"
				  )
				  
		print(rplot, file=rout)
				
		# label the nodes with this to check the domains
		#+geom_text2(aes(label = label, size=6), hjust = -0.3)
				
		# Two issues: The tip labels drawing gives an error of some kind. can fix by specifying a size
		# Related? Doesn't work because some domains share an edge, and this breaks it.
		# I can't do domains. I need to do edges?
		
		# first fix: add size to tiplabels
		# add in a line for the zero conditon weight at beginning of mapping
		# look at open tree in R. 4-17 looks odd. bad algorithm for tree? Bad Newick?
		
		#ggtree(px, aes(size=unname(mp[group])), ladderize=FALSE, layout="slanted") + geom_tiplab(color="black", size=3, offset=-1) + layout_dendrogram() + scale_size_identity()
		
		treeCount += 1
		print("", file=rout)

	print("", file=rout)
	
	layoutCount = 2 # account for different last line
	print("treelayout <- c(", file=rout)
	while layoutCount < treeCount:
		print("area(t = 1, l = 1, b = 5, r = 1),", file=rout)
		layoutCount += 1
	print("area(t = 1, l = 1, b = 5, r = 1))", file=rout)
	print("", file=rout)
	
	plotCount = 1 # account for different last line
	print("print(", file=rout)
	while plotCount < treeCount:
		print(tpfx + "treeplot" + str(plotCount) + "+", file=rout)
		plotCount += 1
	print("plot_layout(design = treelayout))", file=rout)
	rout.close()
	
	# to self, what am I visualizing here precisely? What are these trees?	

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

# to do: something wrong in the minimal coverage sets, not removed duplicates


# Workhorse function
# This will be called recursively to traverse the tree
# I hope the logic is right
def traverse(size, parentSpan, tree, minDomain):

	# To do: I don't think this will handle two small domains at different spans contained
	# in a larger parent (e.g., add another two element domain to Chichewa)
	# Probably, it means a condition on the splitting in a for loop below for
	# When a span size has multiple domains
	# Is this why Chacobo breaks?

	# print("This is the current tree:", tree)

	# Exit condition
	if size < minDomain:
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
			# print("The test span is not contained in the parent", parentSpan, testSpan)
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
		#print("DS:", minDomain, size)
		return(domain, size)
	elif size <= minDomain:
		#print("DSmin:", size)
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

	#print(reducingdomains)

	# For some of Adam's project, there are domains where left=right
	# Also breaks on Chichewa for just phonological or just morsyntactic, but I don't know why yet, maybe same issue?
	# These broke the logic. I need to account for that.
	# This is inefficient since we should do this at the start instead of every time
	# This may be redundant since I'm not filtering sooner
	for reducingdomain in reducingdomains:
		[left, right] = reducingdomain
		if left == right:
			reducingdomains.remove(reducingdomain)

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
	# Multiple trees might reduce to the same degree
	# We need to run through each of them recursively as we build the tree lists
	#print("Starting")
	for maxReducedTree in maxReducedTrees:

		#print("This is a maximum reducing tree:", maxReducedTree)

		# Move the copy in here. I think that's the right thing to do.
		# Need to check new output carefully.
		workingTreeSet = reducedTreeSet.copy()
		workingTreeSet.append(maxReducedTree)

		reduceddomains = reducingdomains.copy()

		for maxTreeDomain in maxReducedTree:
			if maxTreeDomain in reduceddomains: reduceddomains.remove(maxTreeDomain)
		
		#print("Domains left", reduceddomains)
		#print("Reduced tree set", reducedTreeSet)
		getTopReducers(reducingtrees,reduceddomains,workingTreeSet)
	#print("Finishing")


def newick(tree):
	
	maximal = tree[0] # First element should be maximal span
	revtree = list(reversed(tree)) # reorder smallest to largest
	
	prevleftedge = 0 # placeholder
	prevrightedge = 0
	justlabeledanode = False # needed to get commas to come out right
	seenpositions = [ ]
	#newicktree = "("
	newicktree = ""
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
				
	
	#newicktree = newicktree +  ")"
	
	#print("NN", newicktree)
	return(newicktree)




main(["tonosegmental", "intonational"], "green", "tonoseg")