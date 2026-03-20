#!/usr/bin/env python3
"""Shared validation types for the planars coding workflow.

Imports from here:
  from .validate import ValidationIssue

Domain-specific validation lives in:
  validate_planar.py      — planar structure TSV validation
  validate_coding.py      — annotation sheet validation + validate-coding command
  validate_diagnostics.py — diagnostics.tsv validation
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

    def __str__(self) -> str:
        return f"[{self.level.upper()}] {self.location}: {self.message}"
