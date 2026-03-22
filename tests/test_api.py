from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx
import pytest

from uniprot_insights import api
from uniprot_insights.api import (
    annotate,
    annotate_accession,
    annotate_accessions,
    summarize_batch,
)
from uniprot_insights.client import UniProtClient

RULE_PATH = Path("src/uniprot_insights/data/default_rules.yaml")
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _build_client_with_fixtures(fixtures: dict[str, dict]) -> UniProtClient:
    def handler(request: httpx.Request) -> httpx.Response:
        accession = request.url.path.rsplit("/", 1)[-1]
        payload = fixtures.get(accession)
        if payload is None:
            return httpx.Response(status_code=404, json={"detail": "missing"})
        return httpx.Response(status_code=200, json=payload)

    return UniProtClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_annotate_accession() -> None:
    client = _build_client_with_fixtures(
        {"P22222": _load_fixture("omega5_gliadin.json")}
    )

    result = annotate_accession("P22222", client=client, rules_file=RULE_PATH)

    assert result.accession == "P22222"
    assert result.subgroup == "omega_5_gliadin"
    assert result.confidence == "high"


def test_annotate_accessions_preserves_input_order() -> None:
    client = _build_client_with_fixtures(
        {
            "P22222": _load_fixture("omega5_gliadin.json"),
            "Q33333": _load_fixture("lmw_glutenin.json"),
        }
    )

    results = annotate_accessions(
        ["Q33333", "P22222"], client=client, rules_file=RULE_PATH
    )

    assert len(results) == 2
    assert [item.accession for item in results] == ["Q33333", "P22222"]
    assert results[0].subgroup == "lmw_glutenin"
    assert results[1].subgroup == "omega_5_gliadin"


def test_annotate_accessions_fail_soft_records_errors() -> None:
    client = _build_client_with_fixtures(
        {"P22222": _load_fixture("omega5_gliadin.json")}
    )

    results = annotate_accessions(
        ["P22222", "UNKNOWN"], client=client, rules_file=RULE_PATH
    )
    assert len(results) == 2
    assert results[0].subgroup == "omega_5_gliadin"
    assert results[0].annotation_error is None
    assert results[1].subgroup == "unclassified"
    assert results[1].unresolved is True
    assert results[1].annotation_error


def test_annotate_accessions_strict_raises_errors() -> None:
    client = _build_client_with_fixtures({})

    with pytest.raises(Exception):
        annotate_accessions(
            ["UNKNOWN"], client=client, rules_file=RULE_PATH, strict=True
        )


def test_load_accessions_file_with_accession_header_skipped() -> None:
    with NamedTemporaryFile("w+", suffix=".txt", delete=False) as handle:
        handle.write("accession\nP22222\n")
        handle.flush()
        path = Path(handle.name)

    with NamedTemporaryFile("w+", suffix=".txt", delete=False) as tabbed:
        tabbed.write("accession\tid\nP22222\tignored\nQ33333\tignored\n")
        tabbed.flush()
        path_tsv = Path(tabbed.name)

    with NamedTemporaryFile("w+", suffix=".txt", delete=False) as csv_file:
        csv_file.write("accession,id\nP22222,ignored\nQ33333,ignored\n")
        csv_file.flush()
        path_csv = Path(csv_file.name)

    assert api._load_accessions_from_file(path, "accession") == ["P22222"]
    assert api._load_accessions_from_file(
        path_tsv, "accession", delimiter="\t", has_header=True
    ) == [
        "P22222",
        "Q33333",
    ]
    assert api._load_accessions_from_file(
        path_csv, "accession", delimiter=",", has_header=True
    ) == [
        "P22222",
        "Q33333",
    ]


def test_annotate_dataframe_appends_rows_and_annotations() -> None:
    pd = pytest.importorskip("pandas")

    client = _build_client_with_fixtures(
        {
            "P22222": _load_fixture("omega5_gliadin.json"),
            "Q33333": _load_fixture("lmw_glutenin.json"),
        }
    )

    frame = pd.DataFrame(
        {
            "accession": ["P22222", "UNKNOWN", "Q33333"],
            "protein": ["one", "two", "three"],
        }
    )

    annotated = annotate(frame, client=client, rules_file=RULE_PATH)

    expected = {
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
    }
    assert expected.issubset(set(annotated.columns))
    assert annotated.loc[0, "annotation_error"] == ""
    assert annotated.loc[0, "subgroup"] == "omega_5_gliadin"
    assert annotated.loc[1, "annotation_error"]
    assert annotated.loc[1, "subgroup"] == "unclassified"
    assert annotated.loc[2, "subgroup"] == "lmw_glutenin"


def test_summarize_batch() -> None:
    client = _build_client_with_fixtures(
        {
            "P22222": _load_fixture("omega5_gliadin.json"),
            "Q33333": _load_fixture("lmw_glutenin.json"),
            "Q77777": _load_fixture("non_supported_gliadin.json"),
        }
    )

    results = annotate_accessions(
        ["P22222", "Q33333", "Q77777"], client=client, rules_file=RULE_PATH
    )
    summary = summarize_batch(results)
    assert summary["broad_group"]["gliadin"] == 2
    assert summary["broad_group"]["glutenin"] == 1
    assert summary["broad_group"].get("unclassified", 0) == 0
    assert summary["unresolved"][False] == 2
    assert summary["unresolved"][True] == 1


def test_annotate_dataframe_without_pandas_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataframe_type = type("DataFrame", (), {})
    dataframe_type.__module__ = "pandas.core.frame"

    original_import = api.importlib.import_module

    def fake_import_module(name: str):
        if name == "pandas":
            raise ModuleNotFoundError("No module named 'pandas'")
        return original_import(name)

    monkeypatch.setattr(api.importlib, "import_module", fake_import_module)

    with pytest.raises(
        ImportError, match="pandas is required for DataFrame annotation"
    ):
        api.annotate(dataframe_type())
