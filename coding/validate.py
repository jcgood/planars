#!/usr/bin/env python3
"""Shared validation types for the planars coding workflow.

Imports from here:
  from .validate import ValidationIssue

Domain-specific validation lives in:
  validate_planar.py      — planar structure TSV validation
  validate_coding.py      — annotation sheet validation + validate-coding command
  validate_diagnostics.py — diagnostics_{lang_id}.tsv validation
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class ValidationIssue:
    level: str                           # "error" or "warning"
    location: str                        # human-readable location string
    message: str
    cell: Optional[Tuple[int, int]] = None  # (row_idx, col_idx) 0-based for Sheets
    blocking: bool = True                # False: reported as an error, but callers
                                          # that gate a write on "any error present"
                                          # may still proceed (e.g. a required class
                                          # that simply hasn't been drafted yet is not
                                          # a reason to withhold syncing the classes
                                          # that are already valid)

    def __str__(self) -> str:
        return f"[{self.level.upper()}] {self.location}: {self.message}"
