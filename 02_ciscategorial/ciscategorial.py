import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from planars.ciscategorial import derive_v_ciscategorial_fractures, format_result

if __name__ == "__main__":
    tsv = sys.argv[1] if len(sys.argv) > 1 else "ciscategorial_stan1293_general_filled.tsv"
    result = derive_v_ciscategorial_fractures(Path(__file__).parent / tsv)
    print(format_result(result))
