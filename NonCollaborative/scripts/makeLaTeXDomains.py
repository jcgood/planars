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

def main():

	domainRows = pandas.read_csv(planarFolder + os.sep + domainFile,sep="\t")
	
	for index, row in domainRows.iterrows():
	
		label = row["Test_Labels"]
		type_ = row["Domain_Type"]
		left = row["Left_Edge"]
		right = row["Right_Edge"]
		size = row["Size"]
		
		# See if line is commented out
		if label.startswith("#"):
			continue
		
		# data integrity check
		calculatedSize = right - left + 1
		if size != calculatedSize:
			print("Mismatch between stored size and calculated size", row)
			quit()
		

	# get rid of commented lines
	domainRows = domainRows[~domainRows["Test_Labels"].str.startswith("#")]


	# Drop the Notes column
	outputRows = domainRows.drop(columns=["Notes"])
	
	# Convert to LaTeX tabular format
	tabular = outputRows.to_latex(index=False, escape=False)
	
	print(tabular)
		




main()