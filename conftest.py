"""Root conftest.py — ensures the repo root is on sys.path.

This lets test files import both the installed planars package and the
uninstalled coding/ package (e.g. `from coding.restructure_sheets import ...`)
without manual sys.path manipulation in each test file.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
