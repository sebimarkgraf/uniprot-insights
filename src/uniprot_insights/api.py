from __future__ import annotations

import csv
import importlib
import math
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, overload

from .client import UniProtClient
from .classifier import classify_entry
from .extractors import extract_entry
from .models import ClassificationResult
from .rules import load_rules

if TYPE_CHECKING:
    import pandas as pd

    from .cache import CacheBackend


ANNOTATION_COLUMNS = [
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


def _build_client(
    *,
    base_url: str,
    timeout: float,
    cache: Optional["CacheBackend"],
    provided_client: Optional[UniProtClient] = None,
) -> UniProtClient:
    if provided_client is not None:
        return provided_client
    return UniProtClient(base_url=base_url, timeout=timeout, cache=cache)


def _normalize_accession(accession: object) -> str:
    if accession is None:
        return ""
    if isinstance(accession, float) and math.isnan(accession):
        return ""
    return str(accession).strip()


def _looks_like_pandas_dataframe(value: object) -> bool:
    value_type = type(value)
    return (
        getattr(value_type, "__module__", "") == "pandas.core.frame"
        and value_type.__name__ == "DataFrame"
    )


def _load_pandas() -> Any:
    try:
        return importlib.import_module("pandas")
    except ImportError as exc:
        raise ImportError(
            "pandas is required for DataFrame annotation. Install pandas and retry."
        ) from exc


def _classify_accessions(
    accessions: Sequence[str],
    *,
    rules_file: Path | str | None,
    client: UniProtClient,
    strict: bool = False,
) -> list[ClassificationResult]:
    rules = load_rules(rules_file)
    results: list[ClassificationResult] = []
    for accession in accessions:
        try:
            raw = client.fetch_entry(accession)
            results.append(classify_entry(extract_entry(raw), rules))
        except Exception as exc:
            if strict:
                raise
            results.append(
                ClassificationResult(
                    accession=accession,
                    organism="",
                    entry_name="",
                    protein_name="",
                    broad_group="unclassified",
                    subgroup="unclassified",
                    confidence="none",
                    evidence="error",
                    matched_rule=None,
                    matched_pattern=None,
                    pattern_source=None,
                    annotation_error=_format_exception_message(exc),
                    unresolved=True,
                )
            )
    return results


def _classify_single_accession(
    accession: str,
    *,
    rules_file: Path | str | None,
    client: UniProtClient,
    strict: bool = False,
) -> ClassificationResult:
    return _classify_accessions(
        [accession],
        rules_file=rules_file,
        client=client,
        strict=strict,
    )[0]


def _looks_like_accession_header(value: str) -> bool:
    return value.strip().lower() in {"accession", "accessions", "id", "uniprot", "uniprot_id", "uniprotid"}


def _load_accessions_from_file(
    path: Path,
    column: str,
    *,
    has_header: bool = True,
    delimiter: str = "auto",
    ignore_header: bool = False,
) -> list[str]:
    if not path.is_file():
        raise ValueError(f"Input file does not exist: {path}")

    if delimiter == "\\t":
        delimiter = "\t"

    if delimiter not in {"auto", ",", "\t"}:
        raise ValueError("delimiter must be ',', '\\t', or 'auto'")

    lines = [line.rstrip("\n\r") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return []

    sample = "\n".join(lines[:20])
    detected_delimiter: str | None = None

    if delimiter == "auto":
        try:
            detected = csv.Sniffer().sniff(sample, delimiters=",\t")
            if detected.delimiter in {",", "\t"}:
                detected_delimiter = detected.delimiter
        except csv.Error:
            detected_delimiter = None
    else:
        detected_delimiter = delimiter

    if detected_delimiter is not None:
        if has_header:
            reader = csv.DictReader(lines, delimiter=detected_delimiter)
            if not reader.fieldnames:
                raise ValueError(f"Input file {path} is missing a header row.")
            if column not in reader.fieldnames:
                raise ValueError(f"Column '{column}' not found in input file {path}")
            return [
                str(row.get(column, "")).strip()
                for row in reader
                if str(row.get(column, "")).strip()
            ]

        reader = csv.reader(lines, delimiter=detected_delimiter)
        return [row[0].strip() for row in reader if row and row[0].strip()]

    header = lines[0]
    if has_header:
        if ignore_header or _looks_like_accession_header(header):
            return lines[1:]
        return lines

    if ignore_header:
        return lines[1:]
    return lines


def _resolve_accessions_from_input(
    accessions_or_path: str,
    *,
    strategy: str,
    column: str,
    has_header: bool = True,
    delimiter: str = "auto",
    ignore_header: bool = False,
) -> list[str]:
    if strategy == "file":
        file_path = Path(accessions_or_path)
        if file_path.is_file():
            return _load_accessions_from_file(
                file_path,
                column=column,
                has_header=has_header,
                delimiter=delimiter,
                ignore_header=ignore_header,
            )
        return [accessions_or_path]

    if strategy == "single":
        normalized = _normalize_accession(accessions_or_path)
        if not normalized:
            raise ValueError("Accession must be a non-empty string.")
        return [normalized]

    raise ValueError(f"Unknown strategy '{strategy}'. Use 'file' or 'single'.")


def _to_error_row(accession: str, error_message: str) -> dict[str, Any]:
    return {
        "accession": accession,
        "organism": "",
        "entry_name": "",
        "broad_group": "unclassified",
        "subgroup": "unclassified",
        "confidence": "none",
        "evidence": "error",
        "matched_rule": None,
        "unresolved": True,
        "annotation_error": error_message,
    }


def _to_output_row(result: ClassificationResult) -> dict[str, Any]:
    return {
        "accession": result.accession,
        "organism": result.organism,
        "entry_name": result.entry_name,
        "broad_group": result.broad_group,
        "subgroup": result.subgroup,
        "confidence": result.confidence,
        "evidence": result.evidence,
        "matched_rule": result.matched_rule,
        "unresolved": result.unresolved,
        "annotation_error": result.annotation_error or "",
    }


def _format_exception_message(exc: Exception) -> str:
    return str(exc) if str(exc) else exc.__class__.__name__


def annotate_accessions(
    accessions: Sequence[str],
    *,
    rules_file: Path | str | None = None,
    client: Optional[UniProtClient] = None,
    base_url: str = "https://rest.uniprot.org/uniprotkb",
    timeout: float = 10.0,
    cache: Optional["CacheBackend"] = None,
    strict: bool = False,
) -> list[ClassificationResult]:
    if not accessions:
        return []

    normalized: list[str] = []
    for accession in accessions:
        if not isinstance(accession, str):
            raise TypeError("All accessions must be strings.")
        normalized_accession = _normalize_accession(accession)
        if not normalized_accession:
            raise ValueError("Accession must be a non-empty string.")
        normalized.append(normalized_accession)

    resolved_client = _build_client(
        base_url=base_url,
        timeout=timeout,
        cache=cache,
        provided_client=client,
    )
    return _classify_accessions(
        normalized,
        rules_file=rules_file,
        client=resolved_client,
        strict=strict,
    )


def annotate_accession(
    accession: str,
    *,
    rules_file: Path | str | None = None,
    client: Optional[UniProtClient] = None,
    base_url: str = "https://rest.uniprot.org/uniprotkb",
    timeout: float = 10.0,
    cache: Optional["CacheBackend"] = None,
    strict: bool = False,
) -> ClassificationResult:
    normalized = _normalize_accession(accession)
    if not normalized:
        raise ValueError("Accession must be a non-empty string.")

    resolved_client = _build_client(
        base_url=base_url,
        timeout=timeout,
        cache=cache,
        provided_client=client,
    )
    return _classify_single_accession(
        normalized,
        rules_file=rules_file,
        client=resolved_client,
        strict=strict,
    )


def _annotate_dataframe(
    frame: "pd.DataFrame",
    *,
    accession_column: str,
    rules_file: Path | str | None,
    client: Optional[UniProtClient],
    base_url: str,
    timeout: float,
    cache: Optional["CacheBackend"],
    strict: bool,
) -> "pd.DataFrame":
    if accession_column not in frame.columns:
        raise ValueError(f"Column '{accession_column}' not found in DataFrame")

    resolved_client = _build_client(
        base_url=base_url,
        timeout=timeout,
        cache=cache,
        provided_client=client,
    )
    rules = load_rules(rules_file)

    annotation_rows: list[dict[str, Any]] = []
    accessions = frame[accession_column].tolist()

    for raw_accession in accessions:
        accession = _normalize_accession(raw_accession)
        if not accession:
            message = f"Missing accession in column '{accession_column}'"
            if strict:
                raise ValueError(message)
            annotation_rows.append(_to_error_row("", message))
            continue

        try:
            raw = resolved_client.fetch_entry(accession)
            result = classify_entry(extract_entry(raw), rules)
        except Exception as exc:
            message = _format_exception_message(exc)
            if strict:
                raise
            annotation_rows.append(_to_error_row(accession, message))
        else:
            annotation_rows.append(_to_output_row(result))

    annotations = frame.__class__.from_records(annotation_rows, index=frame.index)
    output = frame.copy()
    for column in ANNOTATION_COLUMNS:
        output[column] = annotations[column]
    return output


@overload
def annotate(
    accessions_or_df: str | Path,
    *,
    strategy: str = "file",
    accession_column: str = "accession",
    rules_file: Path | str | None = None,
    client: Optional[UniProtClient] = None,
    base_url: str = ...,
    timeout: float = ...,
    cache: Optional["CacheBackend"] = None,
    has_header: bool = True,
    delimiter: str = "auto",
    ignore_header: bool = False,
    strict: bool = False,
) -> ClassificationResult | list[ClassificationResult]:
    ...


@overload
def annotate(
    accessions_or_df: Sequence[str],
    *,
    strategy: str = "file",
    accession_column: str = "accession",
    rules_file: Path | str | None = None,
    client: Optional[UniProtClient] = None,
    base_url: str = ...,
    timeout: float = ...,
    cache: Optional["CacheBackend"] = None,
    has_header: bool = True,
    delimiter: str = "auto",
    ignore_header: bool = False,
    strict: bool = False,
) -> list[ClassificationResult]:
    ...


@overload
def annotate(
    accessions_or_df: "pd.DataFrame",
    *,
    strategy: str = "file",
    accession_column: str = "accession",
    rules_file: Path | str | None = None,
    client: Optional[UniProtClient] = None,
    base_url: str = ...,
    timeout: float = ...,
    cache: Optional["CacheBackend"] = None,
    has_header: bool = True,
    delimiter: str = "auto",
    ignore_header: bool = False,
    strict: bool = False,
) -> "pd.DataFrame":
    ...


def annotate(
    accessions_or_df: str | Path | Sequence[str] | "pd.DataFrame",
    *,
    strategy: str = "file",
    accession_column: str = "accession",
    rules_file: Path | str | None = None,
    client: Optional[UniProtClient] = None,
    base_url: str = "https://rest.uniprot.org/uniprotkb",
    timeout: float = 10.0,
    cache: Optional["CacheBackend"] = None,
    has_header: bool = True,
    delimiter: str = "auto",
    ignore_header: bool = False,
    strict: bool = False,
) -> ClassificationResult | list[ClassificationResult] | "pd.DataFrame":
    if isinstance(accessions_or_df, (str, Path)):
        accession_input = str(accessions_or_df)
        if strategy == "file":
            file_path = Path(accession_input)
            if file_path.is_file():
                accessions = _load_accessions_from_file(
                    file_path,
                    column=accession_column,
                    has_header=has_header,
                    delimiter=delimiter,
                    ignore_header=ignore_header,
                )
                return annotate_accessions(
                    accessions,
                    rules_file=rules_file,
                    client=client,
                    base_url=base_url,
                    timeout=timeout,
                    cache=cache,
                    strict=strict,
                )
            return annotate_accession(
                accession_input,
                rules_file=rules_file,
                client=client,
                base_url=base_url,
                timeout=timeout,
                cache=cache,
                strict=strict,
            )

        accessions = _resolve_accessions_from_input(
            accession_input,
            strategy=strategy,
            column=accession_column,
            has_header=has_header,
            delimiter=delimiter,
            ignore_header=ignore_header,
        )
        return annotate_accessions(
            accessions,
            rules_file=rules_file,
            client=client,
            base_url=base_url,
            timeout=timeout,
            cache=cache,
            strict=strict,
        )

    if _looks_like_pandas_dataframe(accessions_or_df):
        pandas = _load_pandas()
        if not isinstance(accessions_or_df, pandas.DataFrame):
            raise TypeError("Provided object appears to be a pandas DataFrame but is not.")
        return _annotate_dataframe(
            accessions_or_df,
            accession_column=accession_column,
            rules_file=rules_file,
            client=client,
            base_url=base_url,
            timeout=timeout,
            cache=cache,
            strict=strict,
        )

    if not isinstance(accessions_or_df, Sequence):
        raise TypeError("`accessions_or_df` must be a string, sequence of accessions, or a DataFrame.")

    return annotate_accessions(
        list(accessions_or_df),
        rules_file=rules_file,
        client=client,
        base_url=base_url,
        timeout=timeout,
        cache=cache,
        strict=strict,
    )


def summarize_batch(results: Sequence[ClassificationResult]) -> dict[str, dict[str | bool, int]]:
    return {
        "broad_group": dict(Counter(item.broad_group for item in results)),
        "subgroup": dict(Counter(item.subgroup for item in results)),
        "unresolved": dict(Counter(bool(item.unresolved) for item in results)),
        "confidence": dict(Counter(item.confidence for item in results)),
        "pattern_source": dict(Counter(item.pattern_source or "" for item in results)),
    }
