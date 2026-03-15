from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from uniprot_insights.client import UniProtClient
from uniprot_insights.exceptions import UniProtAPIError, UniProtNotFoundError


def test_fetch_entry_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = json.loads(Path("tests/fixtures/omega5_gliadin.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/uniprotkb/P22222":
            return httpx.Response(status_code=200, json=fixture)
        return httpx.Response(status_code=404, json={"detail": "missing"})

    monkeypatch.setattr("uniprot_insights.client.time.sleep", lambda _: None)
    client = UniProtClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        base_url="https://rest.uniprot.org/uniprotkb",
    )
    result = client.fetch_entry("P22222")
    assert result["primaryAccession"] == "P22222"


def test_fetch_entry_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=404, json={"detail": "missing"})

    monkeypatch.setattr("uniprot_insights.client.time.sleep", lambda _: None)
    client = UniProtClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        base_url="https://rest.uniprot.org/uniprotkb",
    )
    with pytest.raises(UniProtNotFoundError):
        client.fetch_entry("MISSING")


def test_fetch_entry_retries_and_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = json.loads(Path("tests/fixtures/lmw_glutenin.json").read_text())
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(status_code=429, text="retry")
        return httpx.Response(status_code=200, json=fixture)

    monkeypatch.setattr("uniprot_insights.client.time.sleep", lambda _: None)
    client = UniProtClient(
        max_retries=3,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        base_url="https://rest.uniprot.org/uniprotkb",
    )
    result = client.fetch_entry("Q33333")
    assert result["primaryAccession"] == "Q33333"
    assert calls["count"] == 2


def test_fetch_entry_retries_and_fails_on_persistent_5xx(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(status_code=500, text="server error")

    monkeypatch.setattr("uniprot_insights.client.time.sleep", lambda _: None)
    client = UniProtClient(
        max_retries=3,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        base_url="https://rest.uniprot.org/uniprotkb",
    )
    with pytest.raises(UniProtAPIError):
        client.fetch_entry("BAD")
    assert calls["count"] == 3
