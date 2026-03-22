from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ExtractedEntry:
    accession: str
    organism: str
    entry_name: str
    protein_names: List[str] = field(default_factory=list)
    gene_names: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)
    combined_text: str = ""


@dataclass
class Rule:
    name: str
    priority: int
    broad_group: str
    subgroup: str
    include_patterns: List[str]
    exclude_patterns: List[str]
    confidence: str


@dataclass
class ClassificationResult:
    accession: str
    organism: str
    entry_name: str
    protein_name: str
    broad_group: str
    subgroup: str
    confidence: str
    evidence: str
    matched_rule: Optional[str]
    matched_pattern: Optional[str] = None
    pattern_source: Optional[str] = None
    annotation_error: Optional[str] = None
    unresolved: bool = False
