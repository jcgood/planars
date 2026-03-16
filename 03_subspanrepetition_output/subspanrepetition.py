from pathlib import Path
from planars.subspanrepetition import derive_subspanrepetition_spans, format_result

if __name__ == "__main__":
    import sys
    tsv = sys.argv[1] if len(sys.argv) > 1 else "subspanrepetition_stan1293_andCoordination_full.tsv"
    result = derive_subspanrepetition_spans(Path(__file__).parent / tsv)
    print(format_result(result))
