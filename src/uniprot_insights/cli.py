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
from .models import ClassificationResult
from .api import annotate_accessions, _load_accessions_from_file
from .rules import load_rules

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
    "annotation_error",
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


def _write_csv(
    results: List[ClassificationResult],
    output: Optional[Path] = None,
    *,
    include_debug: bool = False,
    quiet_errors: bool = False,
) -> None:
    fieldnames = CSV_HEADERS.copy()
    if include_debug:
        fieldnames.extend(["matched_pattern", "pattern_source"])

    out_handle = output.open("w", encoding="utf-8", newline="") if output else sys.stdout
    close_output = bool(output)
    writer = csv.DictWriter(out_handle, fieldnames=fieldnames)
    writer.writeheader()
    for result in results:
        annotation_error = result.annotation_error or ""
        if quiet_errors:
            annotation_error = ""
        row = {
            "accession": result.accession,
            "organism": result.organism,
            "entry_name": result.entry_name,
            "broad_group": result.broad_group,
            "subgroup": result.subgroup,
            "confidence": result.confidence,
            "evidence": result.evidence,
            "matched_rule": result.matched_rule or "",
            "unresolved": str(bool(result.unresolved)).lower(),
            "annotation_error": annotation_error,
        }
        if include_debug:
            row["matched_pattern"] = result.matched_pattern or ""
            row["pattern_source"] = result.pattern_source or ""
        writer.writerow(row)
    if close_output:
        out_handle.close()


@app.command("classify-id")
def classify_id(
    accessions: List[str] = typer.Argument(..., help="UniProt accession(s) or one input file to classify"),
    strategy: str = typer.Option("file", "--strategy", help="Input strategy: 'file' or 'single'"),
    column: str = typer.Option("accession", "--column", help="Accession column when strategy='file'"),
    has_header: bool = typer.Option(True, "--has-header/--no-header", help="Whether the accession file has a header row"),
    delimiter: str = typer.Option("auto", "--delimiter", help="Input delimiter: ',', '\\t', or 'auto'"),
    ignore_header: bool = typer.Option(
        False,
        "--ignore-header",
        help="Skip the first line in file inputs, even when it does not look like a header",
    ),
    fail_fast: bool = typer.Option(False, "--fail-fast", help="Raise on first failed accession"),
    quiet_errors: bool = typer.Option(False, "--quiet-errors", help="Suppress annotation_error text in output"),
    rules_file: Optional[Path] = typer.Option(None, "--rules", help="YAML rules file"),
    base_url: str = typer.Option("https://rest.uniprot.org/uniprotkb", "--base-url", help="UniProt API base URL"),
    timeout: float = typer.Option(10.0, "--timeout", help="HTTP timeout in seconds"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir", help="Optional filesystem cache directory"),
    verbose: bool = typer.Option(False, "--verbose", help="Include matching pattern diagnostics"),
):
    try:
        if strategy == "file":
            if len(accessions) == 1:
                source_path = Path(accessions[0])
                if source_path.is_file():
                    accessions = _load_accessions_from_file(
                        source_path,
                        column,
                        has_header=has_header,
                        delimiter=delimiter,
                        ignore_header=ignore_header,
                    )
        elif strategy != "single":
            raise typer.BadParameter("strategy must be one of: file, single")

        client = _build_client(base_url=base_url, timeout=timeout, cache_path=cache_dir)
        results = annotate_accessions(
            accessions,
            rules_file=rules_file,
            client=client,
            strict=fail_fast,
        )
        _write_csv(results, include_debug=verbose, quiet_errors=quiet_errors)
    except (RuleValidationError, UniProtAPIError, UniProtNotFoundError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)


@app.command("classify-file")
def classify_file(
    file_path: Path = typer.Argument(..., exists=True, readable=True, help="CSV file with accession column"),
    column: str = typer.Option("accession", "--column", help="Accession column in input CSV"),
    has_header: bool = typer.Option(True, "--has-header/--no-header", help="Whether the accession file has a header row"),
    delimiter: str = typer.Option("auto", "--delimiter", help="Input delimiter: ',', '\\t', or 'auto'"),
    ignore_header: bool = typer.Option(
        False,
        "--ignore-header",
        help="Skip the first line in file inputs, even when it does not look like a header",
    ),
    fail_fast: bool = typer.Option(False, "--fail-fast", help="Raise on first failed accession"),
    quiet_errors: bool = typer.Option(False, "--quiet-errors", help="Suppress annotation_error text in output"),
    rules_file: Optional[Path] = typer.Option(None, "--rules", help="YAML rules file"),
    base_url: str = typer.Option("https://rest.uniprot.org/uniprotkb", "--base-url", help="UniProt API base URL"),
    timeout: float = typer.Option(10.0, "--timeout", help="HTTP timeout in seconds"),
    output: Optional[Path] = typer.Option(None, "--output", help="Optional output CSV path"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir", help="Optional filesystem cache directory"),
    verbose: bool = typer.Option(False, "--verbose", help="Include matching pattern diagnostics"),
):
    try:
        client = _build_client(base_url=base_url, timeout=timeout, cache_path=cache_dir)
        accessions = _load_accessions_from_file(
            file_path,
            column,
            has_header=has_header,
            delimiter=delimiter,
            ignore_header=ignore_header,
        )

        if not accessions:
            typer.echo("No accessions found in input file", err=True)
            raise typer.Exit(code=1)

        results = annotate_accessions(
            accessions,
            rules_file=rules_file,
            client=client,
            strict=fail_fast,
        )
        _write_csv(results, output=output, include_debug=verbose, quiet_errors=quiet_errors)
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
