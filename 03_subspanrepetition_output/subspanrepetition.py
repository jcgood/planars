import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from planars.subspanrepetition import derive_subspanrepetition_spans, format_result

if __name__ == "__main__":
    tsv = sys.argv[1] if len(sys.argv) > 1 else "subspanrepetition_stan1293_andCoordination_full.tsv"
    result = derive_subspanrepetition_spans(Path(__file__).parent / tsv)
    print(format_result(result))
