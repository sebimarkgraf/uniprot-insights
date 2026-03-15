from __future__ import annotations

import os

import pytest

from uniprot_insights.classifier import classify_entry
from uniprot_insights.client import UniProtClient
from uniprot_insights.extractors import extract_entry
from uniprot_insights.rules import load_rules


@pytest.mark.live
@pytest.mark.integration
@pytest.mark.skipif(os.getenv("RUN_LIVE_INTEGRATION", "").strip() != "1", reason="Set RUN_LIVE_INTEGRATION=1 to run live integration test.")
def test_live_fetch_entry_smoke() -> None:
    client = UniProtClient(base_url="https://rest.uniprot.org/uniprotkb")
    raw_entry = client.fetch_entry("P69905")

    assert "primaryAccession" in raw_entry
    extracted = extract_entry(raw_entry)
    classified = classify_entry(extracted, load_rules())

    assert classified.accession == extracted.accession
