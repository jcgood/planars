from pathlib import Path
from planars.noninterruption import derive_noninterruption_domains, format_result

if __name__ == "__main__":
    import sys
    tsv = sys.argv[1] if len(sys.argv) > 1 else "noninterruption_stan1293_general_fill.tsv"
    result = derive_noninterruption_domains(Path(__file__).parent / tsv)
    print(format_result(result))
