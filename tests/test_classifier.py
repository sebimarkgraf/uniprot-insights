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


def test_classify_related_cereal_storage_families() -> None:
    rules = load_rules(RULE_PATH)

    gamma_secalin = {
        "primaryAccession": "S11111",
        "uniProtkbId": "SECALE_GAMMA",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "75k gamma secalin"}}
        },
        "organism": {"scientificName": "Secale cereale"},
    }
    gamma_secalin_result = classify_entry(extract_entry(gamma_secalin), rules)
    assert gamma_secalin_result.subgroup == "gamma_secalin"
    assert gamma_secalin_result.broad_group == "prolamin"
    assert gamma_secalin_result.confidence == "high"

    omega_secalin = {
        "primaryAccession": "S22222",
        "uniProtkbId": "SECALE_OMEGA",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Omega-secalin"}}
        },
        "organism": {"scientificName": "Secale cereale"},
    }
    omega_secalin_result = classify_entry(extract_entry(omega_secalin), rules)
    assert omega_secalin_result.subgroup == "omega_secalin"
    assert omega_secalin_result.broad_group == "prolamin"

    gamma_prolamin = {
        "primaryAccession": "M11111",
        "uniProtkbId": "MAIZE_GAMMA",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Gamma prolamin"}}
        },
        "organism": {"scientificName": "Zea mays"},
    }
    gamma_prolamin_result = classify_entry(extract_entry(gamma_prolamin), rules)
    assert gamma_prolamin_result.subgroup == "gamma_prolamin"
    assert gamma_prolamin_result.broad_group == "prolamin"

    cereal_prolamin = {
        "primaryAccession": "M22222",
        "uniProtkbId": "MAIZE_PROLAMIN",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Prolamin seed storage protein"}}
        },
        "organism": {"scientificName": "Zea mays"},
    }
    cereal_prolamin_result = classify_entry(extract_entry(cereal_prolamin), rules)
    assert cereal_prolamin_result.subgroup == "prolamin_unspecified"
    assert cereal_prolamin_result.broad_group == "prolamin"


def test_classify_expanded_hmw_glutenin_variants() -> None:
    rules = load_rules(RULE_PATH)

    rx_entry = {
        "primaryAccession": "W11111",
        "uniProtkbId": "HMW_RX",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "HMW glutenin subunit Rx"}}
        },
        "organism": {"scientificName": "Triticum aestivum"},
    }
    rx_result = classify_entry(extract_entry(rx_entry), rules)
    assert rx_result.subgroup == "hmw_glutenin"
    assert rx_result.confidence == "high"

    y_entry = {
        "primaryAccession": "W22222",
        "uniProtkbId": "HMW_Y",
        "proteinDescription": {
            "recommendedName": {
                "fullName": {"value": "High molecular weight glutenin subunit y"}
            }
        },
        "organism": {"scientificName": "Triticum durum"},
    }
    y_result = classify_entry(extract_entry(y_entry), rules)
    assert y_result.subgroup == "hmw_glutenin"
    assert y_result.confidence == "high"


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


def test_classify_seed_defense_families() -> None:
    rules = load_rules(RULE_PATH)

    families = [
        (
            {
                "primaryAccession": "D11111",
                "uniProtkbId": "ATI_CM3",
                "proteinDescription": {
                    "recommendedName": {
                        "fullName": {"value": "Alpha-amylase/trypsin inhibitor CM3"}
                    }
                },
                "organism": {"scientificName": "Triticum aestivum"},
            },
            "amylase_trypsin_inhibitor",
        ),
        (
            {
                "primaryAccession": "D22222",
                "uniProtkbId": "LTP1",
                "proteinDescription": {
                    "recommendedName": {
                        "fullName": {"value": "Non-specific lipid-transfer protein"}
                    }
                },
                "organism": {"scientificName": "Triticum aestivum"},
            },
            "lipid_transfer_protein",
        ),
        (
            {
                "primaryAccession": "D33333",
                "uniProtkbId": "PIN_A",
                "proteinDescription": {
                    "recommendedName": {"fullName": {"value": "Puroindoline-A"}}
                },
                "organism": {"scientificName": "Triticum aestivum"},
            },
            "puroindoline",
        ),
        (
            {
                "primaryAccession": "D44444",
                "uniProtkbId": "THIONIN_1",
                "proteinDescription": {
                    "recommendedName": {"fullName": {"value": "Purothionin A-1"}}
                },
                "organism": {"scientificName": "Triticum aestivum"},
            },
            "thionin",
        ),
    ]

    for data, expected_subgroup in families:
        result = classify_entry(extract_entry(data), rules)
        assert result.subgroup == expected_subgroup
        assert result.broad_group == expected_subgroup
        assert result.confidence == "high"


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


def test_non_cereal_lipid_transfer_protein_stays_unclassified() -> None:
    rules = load_rules(RULE_PATH)
    data = {
        "primaryAccession": "N11111",
        "uniProtkbId": "ARABIDOPSIS_LTP",
        "proteinDescription": {
            "recommendedName": {
                "fullName": {"value": "Non-specific lipid-transfer protein"}
            }
        },
        "organism": {"scientificName": "Arabidopsis thaliana"},
    }

    result = classify_entry(extract_entry(data), rules)
    assert result.subgroup == "unclassified"


def test_casein_and_housekeeping_proteins_stay_unclassified() -> None:
    rules = load_rules(RULE_PATH)

    casein = {
        "primaryAccession": "N22222",
        "uniProtkbId": "CASEIN_1",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Kappa-casein"}}
        },
        "organism": {"scientificName": "Bos taurus"},
    }
    casein_result = classify_entry(extract_entry(casein), rules)
    assert casein_result.subgroup == "unclassified"

    housekeeping = {
        "primaryAccession": "N33333",
        "uniProtkbId": "ACTIN_1",
        "proteinDescription": {"recommendedName": {"fullName": {"value": "Actin"}}},
        "organism": {"scientificName": "Triticum aestivum"},
    }
    housekeeping_result = classify_entry(extract_entry(housekeeping), rules)
    assert housekeeping_result.subgroup == "unclassified"


def test_yaml_loading_and_validation_failure(tmp_path) -> None:
    bad_rule_file = tmp_path / "bad_rules.yaml"
    bad_rule_file.write_text("- name: bad\n  priority: 1\n", encoding="utf-8")
    with pytest.raises(RuleValidationError):
        load_rules(bad_rule_file)
