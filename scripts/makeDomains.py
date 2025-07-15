# Morph	Position(s)	Construction	Widescope	Filled-in-both-conjuncts
# re-	27	and-conjunction	no	yes
# again	7, 11, 16, 21, 25, 37	and-conjunction	yes	yes
# ed, ing, etc.	30	and-conjunction	no	yes
# BASE	29			
# 				
# 1. Take all morphs that have Widescope "no" (NARROWSCOPE)				
# 2. Define BASE				
# 3. Make group STRING which starts as BASE				
# 4. Add morpheme to STRING fro NARROWSCOPE when morpheme is +1 and -1 position of BASE				
# 5. Repeat 4 until STRING does not change				
# 6. This gets the MIN domain				


# Transcategorial/ciscategorial facture has a different, span-based logic
	# Min-Max and contiguity
	# transcategorial requires knowledge of n-combines, v-combines
	# columns vs rows, and figure it out
	# coord fracture needs both rows, yes and no.
	# non-interruptability...can fracture
	# try a phonology one
		# post-aspiration
		# Some prefixes are "N/A"
		# Then, if not N/A, then process yes/no

# files/tables
# planar structure
# elements (generate from planar structure; look for accidental overlaps)
# tests
# testClasses

import pandas
import os
from collections import defaultdict
   
# Storage folders
domainFolder = "../domains/"
diagnosticFile = "construction_domains.txt"

# Will need to rethink table structures...tried AirTable, but it's weird and very AI now
# Maybe Baserow?

# Make a dictionary of how element fillers map to positions
def filler_positions(file):
	pass
		

def get_diagnostics(file):

	diagnostics = defaultdict(list) # trying this to avoid try/except

	# Just what are we coding in this file?
	diagnosticRecords = pandas.read_csv(file,sep="\t")
	
	headers = list(diagnosticRecords.columns.values)
	diagnostics = headers[3:] # The first headers are known, the rest are diagnostics
	
	# Get the position of the planar base, which is contained in a special record
	# I don't know if I need this or  not, but I'll leave it here for now
	basePosition = diagnosticRecords.loc[diagnosticRecords["Construction"] == "PlanarBase"]["Positions"].item()
	
	constructions = diagnosticRecords["Construction"].unique().tolist()
	constructions.remove("PlanarBase")
	
	# defaultdict of defaultdicts
	constructionSpans = defaultdict(lambda: defaultdict(lambda: defaultdict(int))) # https://stackoverflow.com/questions/5029934/defaultdict-of-defaultdict
	for construction in constructions:
	
		diagconstructions = diagnosticRecords.loc[diagnosticRecords["Construction"] == construction]
		
		# Get the sign sets and positions in a dictionary
		for index, diagconstruction in diagconstructions.iterrows():

			signSet = diagconstruction["SignSet"]
			positions = diagconstruction["Positions"]
			scope = diagconstruction["D1.Widescope"]

			positionList = [int(x) for x in positions.split(", ")]
			leftmostPosition = min(positionList)
			rightmostPosition = max(positionList)
			
			if scope == "yes":						

				leftEdge = constructionSpans[construction]["Max"]["Left"]
				rightEdge = constructionSpans[construction]["Max"]["Right"]
								
				if leftEdge:
					if leftmostPosition < leftEdge:
						constructionSpans[construction]["Max"]["Left"] = leftmostPosition
				else: constructionSpans[construction]["Max"]["Left"] = leftmostPosition

				if rightEdge and rightmostPosition > rightEdge:
					constructionSpans[construction]["Max"]["Right"] = rightmostPosition
				else: constructionSpans[construction]["Max"]["Right"] = rightmostPosition				

			elif scope == "no":

				leftEdge = constructionSpans[construction]["Min"]["Left"]
				rightEdge = constructionSpans[construction]["Min"]["Right"]
								
				if leftEdge:
					if leftmostPosition < leftEdge:
						constructionSpans[construction]["Min"]["Left"] = leftmostPosition
				else: constructionSpans[construction]["Min"]["Left"] = leftmostPosition

				if rightEdge and rightmostPosition > rightEdge:
					constructionSpans[construction]["Min"]["Right"] = rightmostPosition
				else: constructionSpans[construction]["Min"]["Right"] = rightmostPosition				

			elif scope == "NA":
				pass
		

	for construction in constructionSpans.keys():
	
		spans = constructionSpans[construction]

		minSpan = spans["Min"]
		minLeft = minSpan["Left"]
		minRight = minSpan["Right"]

		maxSpan = spans["Max"]	
		maxLeft = maxSpan["Left"]
		maxRight =  maxSpan["Right"]

		print(construction, "minimum", minLeft, minRight)

		intermediateSpans = getIntermediateSpans([minLeft, minRight], [maxLeft, maxRight])
		
		for intermediateSpan in intermediateSpans:
			[left, right] = intermediateSpan
			print(construction, "intermediate", left, right)

		print(construction, "maximum", maxLeft, maxRight)

	
# 	for index, row in diagnosticRecords.iterrows():
# 		signSet = row["SignSet"]
# 		positions = row["Positions"]
# 		construction = row["Construction"] # This is wrong. We don't want to have to specify this again and again
# 		print(signSet, positions, construction)
# 		
# 	for diagnostic in diagnostics:
# 		diagnosticValue = row[diagnostic]
# 		print(diagnostic + ": " + diagnosticValue)
		


# With help from Copilot
def getIntermediateSpans(innerSpan, outerSpan):
	
	outerStart, outerEnd = outerSpan
	innerStart, innerEnd = innerSpan
	
	coveringSpans = [ ]
	
	for start in range(outerStart, innerStart + 1): # range excludes the end of the range, so add 1
		for end in range(innerEnd, outerEnd + 1):
			if start <= innerStart and end >= innerEnd:
				coveringSpans.append([start, end])

	coveringSpans.remove(innerSpan)
	coveringSpans.remove(outerSpan)
	return coveringSpans




get_diagnostics(domainFolder + os.sep + diagnosticFile)

