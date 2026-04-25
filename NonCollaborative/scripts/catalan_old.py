#https://stackoverflow.com/questions/31874784/how-to-list-all-binary-trees-ordered-by-the-catalan-relation
from functools import lru_cache

# Memoization: @lru_cache stores the result of each function call so that if the
# same input is seen again, the stored answer is returned immediately instead of
# recomputing. Without it, all_trees_new(20) would recompute all_trees_new(5)
# thousands of times; with it, each value is computed exactly once.

@lru_cache(maxsize=None)
def _ordered_forests(n):
    """Number of ordered sequences of >=1 trees covering n ordered leaves."""
    if n == 0:
        return 1
    return sum(all_trees_new(j) * _ordered_forests(n - j) for j in range(1, n + 1))

@lru_cache(maxsize=None)
def all_trees_new(n):
    """Number of rooted ordered trees with n ordered leaves (each internal node has >=2 children).
    Fixes all_trees(), which used (i+1) where it should use all_trees_new(i+1), and which
    also missed splits where one side is a single leaf."""
    if n == 1:
        return 1
    return sum(all_trees_new(j) * _ordered_forests(n - j) for j in range(1, n))

for i in range(1, 10):
	print("for", i, "nodes:", all_trees_new(i))


def gen_trees(a,b):
    left_trees = gen_all_trees(a)
    right_trees = gen_all_trees(b)

    trees = []
    for l in left_trees:
        for r in right_trees:
            trees.append([l,r])
    return trees

def gen_all_trees(items):
    trees = []
    if len(items) == 1:
        trees += [items[0]]
    else:
        for i in range(len(items)-1, 0,-1):
            a = items[:i]
            b = items[i:]
            trees += gen_trees(a,b)
    return trees


def gen_all_subdomains(domain):

	(left, right) = domain # tuples can be set elements, lists can't
	
	if left == right: pass
	else:
		domains.add(domain)
		gen_all_subdomains((left+1, right))
		gen_all_subdomains((left, right-1))

domains = set() # gen all subdomains adds to this list; ugly, but not sure how to get recursion right
#gen_all_subdomains((1, 8))
#print("Test_Labels\tDomain_Type\tLeft_Edge\tRight_Edge\tSize")
for domain in domains:
	(left, right) = domain
	domainName = str(left) + "_" +  str(right)
	length = right - left + 1
	print(domainName, "NA", left, right, length, sep="\t")

#print(gen_all_trees([1, 2, 3, 4, 5, 6]))

# trying to find number of all trees, not all trees
# seems to be the same as this: https://oeis.org/A007052
# "Number of order-consecutive partitions of n."
def all_trees(n):

	if n < 2: return(0)
	elif n==2: return(1)
	else:
		internalSum = 1 # set to one to start for n-ary branching tree
		for i in range(1, n - 1):
			#print(n, "nodes and iteration " + str(i) + ":", i+1, "*", "f(" + str(n-i) + ")")
			internalSum += (i + 1) * all_trees(n - i)
		return(internalSum)

for i in range(1, 10):
	print("for", i, "nodes:", all_trees(i))


# from OEIS paper via copilot
import math

def OCPSplus(n):
    total_sum = 0
    for p in range(1, n + 1):
        inner_sum = 0
        for k in range(p):
            term = (-1)**(p - 1 - k) * math.comb(p - 1, k) * math.comb(n + 2*k - 1, 2*k)
            inner_sum += term
        total_sum += inner_sum
    return total_sum

# Example usage
n=28
result = OCPSplus(n)
result = OCPSplus(n)
print(f"The result of the sum for n={n} is: {result}")


