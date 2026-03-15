from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from .models import ClassificationResult, ExtractedEntry, Rule


SPECIFIC_SUBGROUPS = {
    "omega_5_gliadin",
    "alpha_beta_gliadin",
    "gamma_gliadin",
    "omega_gliadin",
    "lmw_glutenin",
    "hmw_glutenin",
}

BROAD_TO_UNSPECIFIED = {
    "gliadin": "gliadin_unspecified",
    "glutenin": "glutenin_unspecified",
    "prolamin": "prolamin_unspecified",
}


def _matches(patterns: Iterable[str], text: str, *, ignore_case: bool = True) -> bool:
    flags = re.IGNORECASE if ignore_case else 0
    for pattern in patterns:
        if re.search(pattern, text, flags=flags):
            return True
    return False


def _match_rule(rule: Rule, entry: ExtractedEntry) -> Tuple[bool, str]:
    organism = entry.organism or ""
    if rule.organism_regex and not re.search(rule.organism_regex, organism, flags=re.IGNORECASE):
        return False, ""

    if rule.exclude_patterns and _matches(rule.exclude_patterns, entry.combined_text):
        return False, ""

    for pattern in rule.include_patterns:
        if re.search(pattern, entry.combined_text, flags=re.IGNORECASE):
            return True, pattern
    return False, ""


def _matching_source(entry: ExtractedEntry, matched_pattern: str) -> str:
    protein_fields = [entry.entry_name, *entry.protein_names]
    for value in protein_fields:
        if re.search(matched_pattern, value, flags=re.IGNORECASE):
            return "protein_name"
    for value in entry.gene_names:
        if re.search(matched_pattern, value, flags=re.IGNORECASE):
            return "gene_name"
    return "other"


def _confidence_from_source(source: str, is_specific: bool) -> str:
    if not is_specific:
        return "low"
    if source == "protein_name":
        return "high"
    if source == "gene_name":
        return "medium"
    return "low"


def _protein_name_for_output(entry: ExtractedEntry, source: str) -> str:
    if source == "protein_name" and entry.protein_names:
        return entry.protein_names[0]
    if source == "gene_name" and entry.gene_names:
        return entry.gene_names[0]
    if entry.entry_name:
        return entry.entry_name
    if entry.protein_names:
        return entry.protein_names[0]
    return ""


def classify_entry(entry: ExtractedEntry, rules: List[Rule]) -> ClassificationResult:
    for rule in rules:
        matched, pattern = _match_rule(rule, entry)
        if not matched:
            continue

        is_specific = rule.subgroup in SPECIFIC_SUBGROUPS
        if is_specific:
            source = _matching_source(entry, pattern)
            return ClassificationResult(
                accession=entry.accession,
                organism=entry.organism,
                entry_name=entry.entry_name,
                protein_name=_protein_name_for_output(entry, source),
                broad_group=rule.broad_group,
                subgroup=rule.subgroup,
                confidence=_confidence_from_source(source, is_specific=True),
                evidence=source,
                matched_rule=rule.name,
                matched_pattern=pattern,
                pattern_source=source,
                unresolved=False,
            )

        unresolved_subgroup = BROAD_TO_UNSPECIFIED.get(rule.subgroup)
        if unresolved_subgroup:
            return ClassificationResult(
                accession=entry.accession,
                organism=entry.organism,
                entry_name=entry.entry_name,
                protein_name=entry.entry_name,
                broad_group=rule.broad_group,
                subgroup=unresolved_subgroup,
                confidence="low",
                evidence="broad_match",
                matched_rule=rule.name,
                matched_pattern=pattern,
                pattern_source=_matching_source(entry, pattern),
                unresolved=True,
            )

        return ClassificationResult(
            accession=entry.accession,
            organism=entry.organism,
            entry_name=entry.entry_name,
            protein_name=entry.entry_name,
            broad_group=rule.broad_group,
            subgroup=rule.subgroup,
            confidence="none",
            evidence="rule_match",
            matched_rule=rule.name,
            matched_pattern=pattern,
            pattern_source=_matching_source(entry, pattern),
            unresolved=True,
        )

    return ClassificationResult(
        accession=entry.accession,
        organism=entry.organism,
        entry_name=entry.entry_name,
        protein_name=entry.entry_name,
        broad_group="unclassified",
        subgroup="unclassified",
        confidence="none",
        evidence="no_match",
        matched_rule=None,
        matched_pattern=None,
        pattern_source=None,
        unresolved=False,
    )
