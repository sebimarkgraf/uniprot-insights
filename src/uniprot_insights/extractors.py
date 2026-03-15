from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from .models import ExtractedEntry


def _collect_name_entries(values: Optional[Iterable[Dict[str, Any]]]) -> List[str]:
    collected: List[str] = []
    if not values:
        return collected
    for entry in values:
        if not isinstance(entry, dict):
            continue
        value = entry.get("value")
        if isinstance(value, str):
            collected.append(value)
            continue
        full_name = entry.get("fullName")
        if isinstance(full_name, dict):
            val = full_name.get("value")
            if isinstance(val, str):
                collected.append(val)
                continue
        short_name = entry.get("shortName")
        if isinstance(short_name, str):
            collected.append(short_name)
    return collected


def _collect_gene_values(gene_section: Dict[str, Any]) -> List[str]:
    values: List[str] = []
    for key in ("geneName", "synonyms", "synonym", "orfNames", "orderedLocusNames"):
        raw = gene_section.get(key)
        if not raw:
            continue
        if isinstance(raw, list):
            for candidate in raw:
                if isinstance(candidate, dict):
                    v = candidate.get("value")
                else:
                    v = candidate if isinstance(candidate, str) else None
                if isinstance(v, str):
                    values.append(v)
        elif isinstance(raw, dict):
            v = raw.get("value")
            if isinstance(v, str):
                values.append(v)
        elif isinstance(raw, str):
            values.append(raw)
    return values


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\\s+", " ", value.strip()).lower()


def extract_entry(raw_json: Dict[str, Any]) -> ExtractedEntry:
    accession = str(raw_json.get("primaryAccession") or raw_json.get("accession", "") or "")
    entry_name = str(raw_json.get("uniProtkbId") or raw_json.get("proteinName", "") or accession)

    protein_description = raw_json.get("proteinDescription", {}) if isinstance(raw_json.get("proteinDescription"), dict) else {}
    protein_names: List[str] = []

    recommended = protein_description.get("recommendedName")
    if isinstance(recommended, dict):
        protein_names.extend(_collect_name_entries([recommended.get("fullName")] if isinstance(recommended.get("fullName"), dict) else []))
        protein_names.extend(_collect_name_entries(recommended.get("shortNames")))

    alternative = protein_description.get("alternativeNames")
    if isinstance(alternative, list):
        protein_names.extend(_collect_name_entries(alternative))

    submission = protein_description.get("submissionNames")
    if isinstance(submission, list):
        protein_names.extend(_collect_name_entries(submission))

    genes = raw_json.get("genes", [])
    gene_names: List[str] = []
    if isinstance(genes, list):
        for gene in genes:
            if isinstance(gene, dict):
                gene_names.extend(_collect_gene_values(gene))

    keywords_section = raw_json.get("keywords", [])
    keywords: List[str] = []
    if isinstance(keywords_section, list):
        for item in keywords_section:
            if isinstance(item, str):
                keywords.append(item)
            elif isinstance(item, dict):
                value = item.get("value")
                if isinstance(value, str):
                    keywords.append(value)

    comments_section = raw_json.get("comments", [])
    comments: List[str] = []
    if isinstance(comments_section, list):
        for comment in comments_section:
            if not isinstance(comment, dict):
                continue
            comment_type = comment.get("commentType")
            if isinstance(comment_type, str):
                comments.append(comment_type)
            text_entries = comment.get("texts")
            if isinstance(text_entries, list):
                for text_entry in text_entries:
                    if isinstance(text_entry, dict):
                        value = text_entry.get("value")
                        if isinstance(value, str):
                            comments.append(value)

    organism_section = raw_json.get("organism", {})
    organism = ""
    if isinstance(organism_section, dict):
        scientific = organism_section.get("scientificName")
        if isinstance(scientific, str):
            organism = scientific

    all_text = [
        *protein_names,
        *gene_names,
        *keywords,
        *comments,
        organism,
        entry_name,
    ]
    combined_text = _normalize_whitespace(" ".join(part.strip() for part in all_text if isinstance(part, str)))

    return ExtractedEntry(
        accession=accession,
        organism=organism,
        entry_name=entry_name,
        protein_names=list(dict.fromkeys([v for v in protein_names if v])),
        gene_names=list(dict.fromkeys([v for v in gene_names if v])),
        keywords=list(dict.fromkeys([v for v in keywords if v])),
        comments=list(dict.fromkeys([v for v in comments if v])),
        combined_text=combined_text,
    )
