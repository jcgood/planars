import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from planars.noninterruption import derive_noninterruption_domains, format_result

if __name__ == "__main__":
    tsv = sys.argv[1] if len(sys.argv) > 1 else "noninterruption_stan1293_general_fill.tsv"
    result = derive_noninterruption_domains(Path(__file__).parent / tsv)
    print(format_result(result))
