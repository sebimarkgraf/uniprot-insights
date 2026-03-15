from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import List, Optional

import typer

from .cache import FileSystemCache, InMemoryCache
from .client import UniProtClient
from .exceptions import RuleValidationError, UniProtAPIError, UniProtNotFoundError
from .extractors import extract_entry
from .models import ClassificationResult
from .rules import load_rules
from .classifier import classify_entry

app = typer.Typer(help="General UniProt annotation and subgroup classification tools")


CSV_HEADERS = [
    "accession",
    "organism",
    "entry_name",
    "broad_group",
    "subgroup",
    "confidence",
    "evidence",
    "matched_rule",
    "unresolved",
]


def _load_rules(rules_path: Optional[Path]) -> list:
    return load_rules(rules_path)


def _build_client(base_url: str, timeout: float, cache_path: Optional[Path]) -> UniProtClient:
    cache = (
        FileSystemCache(cache_path)
        if cache_path is not None
        else InMemoryCache()
    )
    return UniProtClient(base_url=base_url, timeout=timeout, cache=cache)


def _load_accessions_from_file(file_path: Path, column: str) -> list[str]:
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        first_line = handle.readline()
        if "," in first_line or "\t" in first_line:
            handle.seek(0)
            reader = csv.DictReader(handle)
            if not reader.fieldnames or column not in reader.fieldnames:
                raise typer.BadParameter(f"Column '{column}' not found in {file_path}")
            return [row.get(column, "").strip() for row in reader if row.get(column, "").strip()]

        handle.seek(0)
        return [line.strip() for line in handle if line.strip()]


def _write_csv(results: List[ClassificationResult], output: Optional[Path] = None) -> None:
    out_handle = output.open("w", encoding="utf-8", newline="") if output else sys.stdout
    close_output = bool(output)
    writer = csv.DictWriter(out_handle, fieldnames=CSV_HEADERS)
    writer.writeheader()
    for result in results:
        writer.writerow(
            {
                "accession": result.accession,
                "organism": result.organism,
                "entry_name": result.entry_name,
                "broad_group": result.broad_group,
                "subgroup": result.subgroup,
                "confidence": result.confidence,
                "evidence": result.evidence,
                "matched_rule": result.matched_rule or "",
                "unresolved": str(bool(result.unresolved)).lower(),
            }
        )
    if close_output:
        out_handle.close()


@app.command("classify-id")
def classify_id(
    accessions: List[str] = typer.Argument(..., help="UniProt accession(s) or one input file to classify"),
    strategy: str = typer.Option("file", "--strategy", help="Input strategy: 'file' or 'single'"),
    column: str = typer.Option("accession", "--column", help="Accession column when strategy='file'"),
    rules_file: Optional[Path] = typer.Option(None, "--rules", help="YAML rules file"),
    base_url: str = typer.Option("https://rest.uniprot.org/uniprotkb", "--base-url", help="UniProt API base URL"),
    timeout: float = typer.Option(10.0, "--timeout", help="HTTP timeout in seconds"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir", help="Optional filesystem cache directory"),
):
    try:
        if strategy == "file":
            if len(accessions) == 1:
                source_path = Path(accessions[0])
                if source_path.is_file():
                    accessions = _load_accessions_from_file(source_path, column=column)
        elif strategy != "single":
            raise typer.BadParameter("strategy must be one of: file, single")

        rules = _load_rules(rules_file)
        client = _build_client(base_url=base_url, timeout=timeout, cache_path=cache_dir)
        raw_entries = client.fetch_many(accessions)
        extracted = [extract_entry(raw) for raw in raw_entries]
        results = [classify_entry(item, rules) for item in extracted]
        _write_csv(results)
    except (RuleValidationError, UniProtAPIError, UniProtNotFoundError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)


@app.command("classify-file")
def classify_file(
    file_path: Path = typer.Argument(..., exists=True, readable=True, help="CSV file with accession column"),
    column: str = typer.Option("accession", "--column", help="Accession column in input CSV"),
    rules_file: Optional[Path] = typer.Option(None, "--rules", help="YAML rules file"),
    base_url: str = typer.Option("https://rest.uniprot.org/uniprotkb", "--base-url", help="UniProt API base URL"),
    timeout: float = typer.Option(10.0, "--timeout", help="HTTP timeout in seconds"),
    output: Optional[Path] = typer.Option(None, "--output", help="Optional output CSV path"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir", help="Optional filesystem cache directory"),
):
    try:
        rules = _load_rules(rules_file)
        client = _build_client(base_url=base_url, timeout=timeout, cache_path=cache_dir)
        accessions = _load_accessions_from_file(file_path, column=column)

        if not accessions:
            typer.echo("No accessions found in input file", err=True)
            raise typer.Exit(code=1)

        raw_entries = client.fetch_many(accessions)
        extracted = [extract_entry(raw) for raw in raw_entries]
        results = [classify_entry(item, rules) for item in extracted]
        _write_csv(results, output=output)
    except (RuleValidationError, UniProtAPIError, UniProtNotFoundError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)


@app.command("dump-entry")
def dump_entry(
    accession: str = typer.Argument(..., help="UniProt accession to fetch"),
    base_url: str = typer.Option("https://rest.uniprot.org/uniprotkb", "--base-url", help="UniProt API base URL"),
    timeout: float = typer.Option(10.0, "--timeout", help="HTTP timeout in seconds"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir", help="Optional filesystem cache directory"),
):
    try:
        client = _build_client(base_url=base_url, timeout=timeout, cache_path=cache_dir)
        raw_entry = client.fetch_entry(accession)
        typer.echo(json.dumps(raw_entry, indent=2))
    except (UniProtAPIError, UniProtNotFoundError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)


@app.command("validate-rules")
def validate_rules(
    rules_file: Optional[Path] = typer.Argument(None, help="Optional path to YAML rule file")
):
    try:
        _load_rules(rules_file)
    except RuleValidationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    typer.echo("Rules file is valid.")


def run() -> None:
    app()


if __name__ == "__main__":
    run()
