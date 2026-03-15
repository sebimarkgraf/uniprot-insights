from __future__ import annotations

import json
from pathlib import Path

import pytest

from uniprot_insights.classifier import classify_entry
from uniprot_insights.extractors import extract_entry
from uniprot_insights.rules import load_rules
from uniprot_insights.exceptions import RuleValidationError


RULE_PATH = Path("src/uniprot_insights/data/default_rules.yaml")


def test_classify_priority_omega5_over_omega() -> None:
    rules = load_rules(RULE_PATH)
    data = json.loads(Path("tests/fixtures/omega5_gliadin.json").read_text())
    result = classify_entry(extract_entry(data), rules)
    assert result.subgroup == "omega_5_gliadin"
    assert result.evidence == "protein_name"
    assert result.confidence == "high"


def test_classify_medium_confidence_from_gene_name() -> None:
    rules = load_rules(RULE_PATH)
    data = {
        "primaryAccession": "X11111",
        "uniProtkbId": "GENE_ONLY",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Seed storage component"}}
        },
        "genes": [{"synonyms": [{"value": "gamma-gliadin"}]}],
        "keywords": [{"value": "Gliadin"}],
        "organism": {"scientificName": "Triticum aestivum"},
    }
    result = classify_entry(extract_entry(data), rules)
    assert result.subgroup == "gamma_gliadin"
    assert result.evidence == "gene_name"
    assert result.confidence == "medium"


def test_classify_fallback_gliadin_glutenin_prolamin() -> None:
    rules = load_rules(RULE_PATH)
    data_gliadin = json.loads(
        Path("tests/fixtures/prolamin_unspecified.json").read_text()
    )
    data_gliadin["keywords"][0]["value"] = "Gliadin"
    data_gliadin["uniProtkbId"] = "BROAD_GLIADIN"
    result_gliadin = classify_entry(extract_entry(data_gliadin), rules)
    assert result_gliadin.subgroup == "gliadin_unspecified"

    data_glutenin = json.loads(
        Path("tests/fixtures/prolamin_unspecified.json").read_text()
    )
    data_glutenin["keywords"] = [{"value": "Glutenin"}]
    data_glutenin["proteinDescription"]["recommendedName"]["fullName"]["value"] = (
        "Unknown glutenin family"
    )
    data_glutenin["uniProtkbId"] = "BROAD_GLUTENIN"
    result_glutenin = classify_entry(extract_entry(data_glutenin), rules)
    assert result_glutenin.subgroup == "glutenin_unspecified"

    data_prolamin = json.loads(
        Path("tests/fixtures/prolamin_unspecified.json").read_text()
    )
    data_prolamin["uniProtkbId"] = "BROAD_PROLAMIN"
    data_prolamin["keywords"] = [{"value": "Prolamin"}]
    result_prolamin = classify_entry(extract_entry(data_prolamin), rules)
    assert result_prolamin.subgroup == "prolamin_unspecified"


def test_classify_ambiguous_prolamin_and_unsupported_organism() -> None:
    rules = load_rules(RULE_PATH)
    ambiguous = json.loads(Path("tests/fixtures/ambiguous_prolamin.json").read_text())
    result_ambiguous = classify_entry(extract_entry(ambiguous), rules)
    assert result_ambiguous.subgroup == "gliadin_unspecified"

    unsupported = json.loads(
        Path("tests/fixtures/non_supported_gliadin.json").read_text()
    )
    result_unsupported = classify_entry(extract_entry(unsupported), rules)
    assert result_unsupported.subgroup == "unclassified"


def test_yaml_loading_and_validation_failure(tmp_path) -> None:
    bad_rule_file = tmp_path / "bad_rules.yaml"
    bad_rule_file.write_text("- name: bad\n  priority: 1\n", encoding="utf-8")
    with pytest.raises(RuleValidationError):
        load_rules(bad_rule_file)
