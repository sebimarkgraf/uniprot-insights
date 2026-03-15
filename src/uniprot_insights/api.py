from __future__ import annotations

import csv
import importlib
import math
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
) -> list[ClassificationResult]:
    rules = load_rules(rules_file)
    raw_entries = client.fetch_many(accessions)
    return [classify_entry(extract_entry(raw), rules) for raw in raw_entries]


def _classify_single_accession(
    accession: str,
    *,
    rules_file: Path | str | None,
    client: UniProtClient,
) -> ClassificationResult:
    return _classify_accessions([accession], rules_file=rules_file, client=client)[0]


def _load_accessions_from_file(path: Path, column: str) -> list[str]:
    if not path.is_file():
        raise ValueError(f"Input file does not exist: {path}")

    with path.open("r", encoding="utf-8", newline="") as handle:
        first_line = handle.readline()
        if "," in first_line or "\t" in first_line:
            handle.seek(0)
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError(f"Input file {path} is missing a header row.")
            if column not in reader.fieldnames:
                raise ValueError(f"Column '{column}' not found in input file {path}")
            return [
                str(row.get(column, "")).strip()
                for row in reader
                if str(row.get(column, "")).strip()
            ]

        handle.seek(0)
        return [line.strip() for line in handle if line.strip()]


def _resolve_accessions_from_input(
    accessions_or_path: str,
    *,
    strategy: str,
    column: str,
) -> list[str]:
    if strategy == "file":
        file_path = Path(accessions_or_path)
        if file_path.is_file():
            return _load_accessions_from_file(file_path, column=column)
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
        "organism": None,
        "entry_name": None,
        "broad_group": None,
        "subgroup": None,
        "confidence": None,
        "evidence": None,
        "matched_rule": None,
        "unresolved": None,
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
        "annotation_error": "",
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
    return _classify_accessions(normalized, rules_file=rules_file, client=resolved_client)


def annotate_accession(
    accession: str,
    *,
    rules_file: Path | str | None = None,
    client: Optional[UniProtClient] = None,
    base_url: str = "https://rest.uniprot.org/uniprotkb",
    timeout: float = 10.0,
    cache: Optional["CacheBackend"] = None,
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
    return _classify_single_accession(normalized, rules_file=rules_file, client=resolved_client)


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
    strict: bool = False,
) -> ClassificationResult | list[ClassificationResult] | "pd.DataFrame":
    if isinstance(accessions_or_df, (str, Path)):
        accession_input = str(accessions_or_df)
        if strategy == "file":
            file_path = Path(accession_input)
            if file_path.is_file():
                accessions = _load_accessions_from_file(file_path, column=accession_column)
                return annotate_accessions(
                    accessions,
                    rules_file=rules_file,
                    client=client,
                    base_url=base_url,
                    timeout=timeout,
                    cache=cache,
                )
            return annotate_accession(
                accession_input,
                rules_file=rules_file,
                client=client,
                base_url=base_url,
                timeout=timeout,
                cache=cache,
            )

        accessions = _resolve_accessions_from_input(
            accession_input,
            strategy=strategy,
            column=accession_column,
        )
        return annotate_accessions(
            accessions,
            rules_file=rules_file,
            client=client,
            base_url=base_url,
            timeout=timeout,
            cache=cache,
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
    )
