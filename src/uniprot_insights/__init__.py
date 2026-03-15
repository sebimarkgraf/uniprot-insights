"""Core package for UniProt access and subgroup classification."""

from .client import UniProtClient
from .classifier import classify_entry
from .extractors import extract_entry
from .models import ClassificationResult, ExtractedEntry, Rule
from .rules import load_rules

__all__ = [
    "UniProtClient",
    "classify_entry",
    "extract_entry",
    "ClassificationResult",
    "ExtractedEntry",
    "Rule",
    "load_rules",
]

