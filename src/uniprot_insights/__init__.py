"""Core package for UniProt access and subgroup classification."""

from .api import annotate, annotate_accession, annotate_accessions, summarize_batch
from .client import UniProtClient
from .classifier import classify_entry
from .extractors import extract_entry
from .models import ClassificationResult, ExtractedEntry, Rule
from .rules import load_rules

__all__ = [
    "UniProtClient",
    "classify_entry",
    "extract_entry",
    "annotate",
    "annotate_accession",
    "annotate_accessions",
    "summarize_batch",
    "ClassificationResult",
    "ExtractedEntry",
    "Rule",
    "load_rules",
]
