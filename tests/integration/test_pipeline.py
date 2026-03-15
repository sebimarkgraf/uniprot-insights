from __future__ import annotations

import json
from pathlib import Path

import httpx

from uniprot_insights.cache import FileSystemCache
from uniprot_insights.classifier import classify_entry
from uniprot_insights.client import UniProtClient
from uniprot_insights.extractors import extract_entry
from uniprot_insights.rules import load_rules


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_client_cache_extract_classify_end_to_end(tmp_path: Path) -> None:
    fixtures = {
        "P22222": _load_fixture(FIXTURES_DIR / "omega5_gliadin.json"),
        "Q33333": _load_fixture(FIXTURES_DIR / "lmw_glutenin.json"),
    }
    hits = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        hits["count"] += 1
        accession = request.url.path.rsplit("/", 1)[-1]
        payload = fixtures.get(accession)
        if payload is None:
            return httpx.Response(status_code=404, json={"detail": "missing"})
        return httpx.Response(status_code=200, json=payload)

    transport = httpx.MockTransport(handler)
    cache_dir = tmp_path / "cache"

    rules = load_rules()
    client = UniProtClient(
        http_client=httpx.Client(transport=transport),
        cache=FileSystemCache(cache_dir),
    )

    raw_entries = client.fetch_many(["P22222", "Q33333"])
    assert len(raw_entries) == 2
    assert hits["count"] == 2
    assert (cache_dir / "P22222.json").exists()
    assert (cache_dir / "Q33333.json").exists()

    extracted = [extract_entry(raw) for raw in raw_entries]
    result = [classify_entry(item, rules) for item in extracted]
    assert result[0].subgroup == "omega_5_gliadin"
    assert result[1].subgroup == "lmw_glutenin"

    client_with_cache = UniProtClient(
        http_client=httpx.Client(transport=transport),
        cache=FileSystemCache(cache_dir),
    )
    second_fetch = client_with_cache.fetch_many(["P22222", "Q33333"])
    assert len(second_fetch) == 2
    assert hits["count"] == 2
