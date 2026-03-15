from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from uniprot_insights import cli
from uniprot_insights.client import UniProtClient


RUNNER = CliRunner()
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _build_client_with_fixtures(fixtures: dict[str, dict], hits: dict[str, int] | None = None) -> UniProtClient:
    hits_dict = hits if hits is not None else {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        hits_dict["count"] = hits_dict.get("count", 0) + 1
        accession = request.url.path.rsplit("/", 1)[-1]
        payload = fixtures.get(accession)
        if payload is None:
            return httpx.Response(status_code=404, json={"detail": "missing"})
        return httpx.Response(status_code=200, json=payload)

    return UniProtClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))


@pytest.mark.integration
def test_classify_id_full_pipeline_writes_csv_to_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures = {
        "P22222": _load_fixture("omega5_gliadin.json"),
        "Q33333": _load_fixture("lmw_glutenin.json"),
    }
    client = _build_client_with_fixtures(fixtures)
    monkeypatch.setattr(cli, "_build_client", lambda *_args, **_kwargs: client)

    result = RUNNER.invoke(cli.app, ["classify-id", "P22222", "Q33333"])
    assert result.exit_code == 0

    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    assert len(rows) == 2
    assert list(rows[0].keys()) == cli.CSV_HEADERS
    assert rows[0]["subgroup"] == "omega_5_gliadin"
    assert rows[0]["confidence"] == "high"
    assert rows[1]["subgroup"] == "lmw_glutenin"
    assert rows[1]["confidence"] == "high"
    assert rows[0]["accession"] == "P22222"
    assert rows[1]["accession"] == "Q33333"

@pytest.mark.integration
def test_classify_id_with_cache_reuses_same_accession_once(monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures = {"P22222": _load_fixture("omega5_gliadin.json")}
    hits: dict[str, int] = {"count": 0}
    client = _build_client_with_fixtures(fixtures, hits=hits)
    monkeypatch.setattr(cli, "_build_client", lambda *_args, **_kwargs: client)

    result = RUNNER.invoke(cli.app, ["classify-id", "P22222", "P22222"])
    assert result.exit_code == 0

    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    assert len(rows) == 2
    assert rows[0]["accession"] == "P22222"
    assert rows[1]["accession"] == "P22222"
    assert hits["count"] == 1


@pytest.mark.integration
def test_classify_file_reads_column_and_writes_output_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixtures = {
        "P22222": _load_fixture("omega5_gliadin.json"),
        "Q33333": _load_fixture("lmw_glutenin.json"),
    }
    client = _build_client_with_fixtures(fixtures)
    monkeypatch.setattr(cli, "_build_client", lambda *_args, **_kwargs: client)

    input_csv = tmp_path / "input.csv"
    input_csv.write_text("id,description\nP22222,first\nQ33333,second\n\n", encoding="utf-8")
    output_csv = tmp_path / "classified.csv"

    result = RUNNER.invoke(
        cli.app,
        [
            "classify-file",
            str(input_csv),
            "--column",
            "id",
            "--output",
            str(output_csv),
        ],
    )
    assert result.exit_code == 0
    assert output_csv.exists()

    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == cli.CSV_HEADERS
        rows = list(reader)
    assert len(rows) == 2


@pytest.mark.integration
def test_dump_entry_returns_json_for_known_accession(monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures = {"P22222": _load_fixture("omega5_gliadin.json")}
    client = _build_client_with_fixtures(fixtures)
    monkeypatch.setattr(cli, "_build_client", lambda *_args, **_kwargs: client)

    result = RUNNER.invoke(cli.app, ["dump-entry", "P22222"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["primaryAccession"] == "P22222"


@pytest.mark.integration
def test_validate_rules_default_and_custom_failure(tmp_path: Path) -> None:
    default_rules = RUNNER.invoke(cli.app, ["validate-rules"])
    assert default_rules.exit_code == 0
    assert "Rules file is valid." in default_rules.stdout

    bad_rules = tmp_path / "bad_rules.yaml"
    bad_rules.write_text("not: a list\n", encoding="utf-8")

    bad_validation = RUNNER.invoke(cli.app, ["validate-rules", str(bad_rules)])
    assert bad_validation.exit_code == 1
    assert bad_validation.stderr
