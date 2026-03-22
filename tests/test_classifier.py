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

    by8_entry = {
        "primaryAccession": "W33333",
        "uniProtkbId": "HMW_BY8",
        "proteinDescription": {
            "submissionNames": [{"fullName": {"value": "HMW-GS BY8 (Fragment)"}}]
        },
        "organism": {"scientificName": "Triticum aestivum"},
    }
    by8_result = classify_entry(extract_entry(by8_entry), rules)
    assert by8_result.subgroup == "hmw_glutenin"
    assert by8_result.confidence == "high"

    dx5_entry = {
        "primaryAccession": "P10388",
        "uniProtkbId": "GLU_DX5_WHEAT",
        "proteinDescription": {
            "recommendedName": {
                "fullName": {"value": "Glutenin, high molecular weight subunit DX5"}
            }
        },
        "organism": {"scientificName": "Triticum aestivum"},
    }
    dx5_result = classify_entry(extract_entry(dx5_entry), rules)
    assert dx5_result.subgroup == "hmw_glutenin"
    assert dx5_result.broad_group == "glutenin"
    assert dx5_result.evidence == "protein_name"
    assert dx5_result.confidence == "high"

    pc256_entry = {
        "primaryAccession": "P02861",
        "uniProtkbId": "GLU_PC256_WHEAT",
        "proteinDescription": {
            "recommendedName": {
                "fullName": {
                    "value": "Glutenin, high molecular weight subunit PC256 (Fragment)"
                }
            }
        },
        "organism": {"scientificName": "Triticum aestivum"},
    }
    pc256_result = classify_entry(extract_entry(pc256_entry), rules)
    assert pc256_result.subgroup == "hmw_glutenin"
    assert pc256_result.broad_group == "glutenin"
    assert pc256_result.evidence == "protein_name"
    assert pc256_result.confidence == "high"

    pw212_entry = {
        "primaryAccession": "P08489",
        "uniProtkbId": "GLU_PW212_WHEAT",
        "proteinDescription": {
            "recommendedName": {
                "fullName": {"value": "Glutenin, high molecular weight subunit PW212"}
            }
        },
        "organism": {"scientificName": "Triticum aestivum"},
    }
    pw212_result = classify_entry(extract_entry(pw212_entry), rules)
    assert pw212_result.subgroup == "hmw_glutenin"
    assert pw212_result.broad_group == "glutenin"
    assert pw212_result.evidence == "protein_name"
    assert pw212_result.confidence == "high"


def test_classify_hyphenated_lmw_glutenin_variant() -> None:
    rules = load_rules(RULE_PATH)

    entry = {
        "primaryAccession": "M1GMA2",
        "uniProtkbId": "M1GMA2_WHEAT",
        "proteinDescription": {
            "submissionNames": [
                {"fullName": {"value": "Low-molecular-weight glutenin subunit"}}
            ]
        },
        "genes": [{"geneName": {"value": "Glu-A3"}}],
        "comments": [
            {
                "commentType": "SIMILARITY",
                "texts": [{"value": "Belongs to the gliadin/glutenin family"}],
            }
        ],
        "organism": {"scientificName": "Triticum aestivum"},
    }

    result = classify_entry(extract_entry(entry), rules)
    assert result.subgroup == "lmw_glutenin"
    assert result.broad_group == "glutenin"
    assert result.evidence == "protein_name"
    assert result.confidence == "high"
    assert result.unresolved is False

    lmw_b3_entry = {
        "primaryAccession": "M2GMA2",
        "uniProtkbId": "LMW_B3_WHEAT",
        "proteinDescription": {"submissionNames": [{"fullName": {"value": "LMW-B3"}}]},
        "organism": {"scientificName": "Triticum aestivum"},
    }

    lmw_b3_result = classify_entry(extract_entry(lmw_b3_entry), rules)
    assert lmw_b3_result.subgroup == "lmw_glutenin"
    assert lmw_b3_result.broad_group == "glutenin"
    assert lmw_b3_result.evidence == "protein_name"
    assert lmw_b3_result.confidence == "high"
    assert lmw_b3_result.unresolved is False


def test_classify_lmw_m_glutenin_variant() -> None:
    rules = load_rules(RULE_PATH)

    entry = {
        "primaryAccession": "V9P6F2",
        "uniProtkbId": "V9P6F2_WHEAT",
        "proteinDescription": {
            "submissionNames": [
                {"fullName": {"value": "LMW-m glutenin subunit 47 (Fragment)"}}
            ]
        },
        "organism": {"scientificName": "Triticum aestivum"},
    }

    result = classify_entry(extract_entry(entry), rules)
    assert result.subgroup == "lmw_glutenin"
    assert result.broad_group == "glutenin"
    assert result.evidence == "protein_name"
    assert result.confidence == "high"
    assert result.unresolved is False


def test_classify_reversed_lmw_glutenin_variant() -> None:
    rules = load_rules(RULE_PATH)

    entry = {
        "primaryAccession": "P10385",
        "uniProtkbId": "GLTLM_WHEAT",
        "proteinDescription": {
            "recommendedName": {
                "fullName": {"value": "Glutenin, low molecular weight subunit"}
            }
        },
        "organism": {"scientificName": "Triticum aestivum"},
    }

    result = classify_entry(extract_entry(entry), rules)
    assert result.subgroup == "lmw_glutenin"
    assert result.broad_group == "glutenin"
    assert result.evidence == "protein_name"
    assert result.confidence == "high"
    assert result.unresolved is False


def test_classify_named_gamma_secalin_from_wheat_annotation() -> None:
    rules = load_rules(RULE_PATH)

    entry = {
        "primaryAccession": "S33333",
        "uniProtkbId": "GAMMA_SECALIN_WHEAT",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "75k gamma secalin"}}
        },
        "organism": {"scientificName": "Triticum aestivum"},
    }

    result = classify_entry(extract_entry(entry), rules)
    assert result.subgroup == "gamma_secalin"
    assert result.broad_group == "prolamin"
    assert result.evidence == "protein_name"
    assert result.confidence == "high"
    assert result.unresolved is False


def test_classify_reported_unclassified_accessions() -> None:
    rules = load_rules(RULE_PATH)

    cases = [
        (
            {
                "primaryAccession": "B6UKJ6",
                "uniProtkbId": "B6UKJ6_AEGTA",
                "proteinDescription": {
                    "submissionNames": [{"fullName": {"value": "Gamma-gliadin"}}]
                },
                "organism": {"scientificName": "Aegilops tauschii"},
            },
            "gamma_gliadin",
            "gliadin",
            False,
        ),
        (
            {
                "primaryAccession": "H8Y0K4",
                "uniProtkbId": "H8Y0K4_SECCE",
                "proteinDescription": {
                    "submissionNames": [{"fullName": {"value": "Gamma prolamin"}}]
                },
                "organism": {"scientificName": "Secale cereale subsp. afghanicum"},
            },
            "gamma_prolamin",
            "prolamin",
            False,
        ),
        (
            {
                "primaryAccession": "H8Y0N7",
                "uniProtkbId": "H8Y0N7_SECCE",
                "proteinDescription": {
                    "submissionNames": [
                        {"fullName": {"value": "Gamma prolamin (Fragment)"}}
                    ]
                },
                "organism": {"scientificName": "Secale cereale subsp. afghanicum"},
            },
            "gamma_prolamin",
            "prolamin",
            False,
        ),
        (
            {
                "primaryAccession": "C4NFQ0",
                "uniProtkbId": "C4NFQ0_WHEAT",
                "proteinDescription": {
                    "submissionNames": [{"fullName": {"value": "Omega secalin"}}]
                },
                "organism": {"scientificName": "Triticum aestivum"},
            },
            "omega_secalin",
            "prolamin",
            False,
        ),
        (
            {
                "primaryAccession": "A0A159KI56",
                "uniProtkbId": "A0A159KI56_WHEAT",
                "proteinDescription": {
                    "submissionNames": [{"fullName": {"value": "Omega-secalin"}}]
                },
                "organism": {"scientificName": "Triticum aestivum"},
            },
            "omega_secalin",
            "prolamin",
            False,
        ),
        (
            {
                "primaryAccession": "Q93WF0",
                "uniProtkbId": "Q93WF0_SECCE",
                "proteinDescription": {
                    "submissionNames": [
                        {
                            "fullName": {
                                "value": "High molecular weight glutenin subunit x"
                            }
                        }
                    ]
                },
                "organism": {"scientificName": "Secale cereale"},
            },
            "hmw_glutenin",
            "glutenin",
            False,
        ),
        (
            {
                "primaryAccession": "D3XQB7",
                "uniProtkbId": "D3XQB7_SECCE",
                "proteinDescription": {
                    "submissionNames": [
                        {"fullName": {"value": "HMW glutenin subunit Rx"}}
                    ]
                },
                "organism": {"scientificName": "Secale cereale"},
            },
            "hmw_glutenin",
            "glutenin",
            False,
        ),
        (
            {
                "primaryAccession": "D3XQB8",
                "uniProtkbId": "D3XQB8_SECCE",
                "proteinDescription": {
                    "submissionNames": [
                        {"fullName": {"value": "HMW glutenin subunit Ry"}}
                    ]
                },
                "organism": {"scientificName": "Secale cereale"},
            },
            "hmw_glutenin",
            "glutenin",
            False,
        ),
        (
            {
                "primaryAccession": "A5JSA3",
                "uniProtkbId": "A5JSA3_AEGTA",
                "proteinDescription": {
                    "recommendedName": {"fullName": {"value": "Prolamin"}}
                },
                "organism": {"scientificName": "Aegilops tauschii"},
            },
            "gliadin_unspecified",
            "gliadin",
            True,
        ),
    ]

    for entry, expected_subgroup, expected_broad_group, expected_unresolved in cases:
        result = classify_entry(extract_entry(entry), rules)
        assert result.subgroup == expected_subgroup
        assert result.broad_group == expected_broad_group
        assert result.unresolved is expected_unresolved


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
    assert result_prolamin.subgroup == "gliadin_unspecified"
    assert result_prolamin.broad_group == "gliadin"


def test_explicit_glutenin_beats_ambiguous_gliadin_glutenin_family_text() -> None:
    rules = load_rules(RULE_PATH)
    entry = {
        "primaryAccession": "A0A1B0Z3C8",
        "uniProtkbId": "A0A1B0Z3C8_WHEAT",
        "proteinDescription": {
            "submissionNames": [{"fullName": {"value": "Glutenin"}}]
        },
        "genes": [{"geneName": {"value": "Glu1Bx6"}}],
        "comments": [
            {
                "commentType": "SIMILARITY",
                "texts": [{"value": "Belongs to the gliadin/glutenin family"}],
            }
        ],
        "organism": {"scientificName": "Triticum aestivum"},
    }

    result = classify_entry(extract_entry(entry), rules)
    assert result.subgroup == "glutenin_unspecified"
    assert result.broad_group == "glutenin"
    assert result.unresolved is True


def test_classify_uncharacterized_protein_as_resolved_group() -> None:
    rules = load_rules(RULE_PATH)
    data = {
        "primaryAccession": "U11111",
        "uniProtkbId": "UNCHARACTERIZED_1",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Uncharacterized protein"}}
        },
        "organism": {"scientificName": "Triticum aestivum"},
    }

    result = classify_entry(extract_entry(data), rules)
    assert result.broad_group == "uncharacterized_protein"
    assert result.subgroup == "uncharacterized_protein"
    assert result.evidence == "protein_name"
    assert result.confidence == "high"
    assert result.unresolved is False


def test_classify_ambiguous_prolamin_and_non_wheat_gliadin_name() -> None:
    rules = load_rules(RULE_PATH)
    ambiguous = json.loads(Path("tests/fixtures/ambiguous_prolamin.json").read_text())
    result_ambiguous = classify_entry(extract_entry(ambiguous), rules)
    assert result_ambiguous.subgroup == "gliadin_unspecified"

    non_wheat_named_entry = json.loads(
        Path("tests/fixtures/non_supported_gliadin.json").read_text()
    )
    result_non_wheat = classify_entry(extract_entry(non_wheat_named_entry), rules)
    assert result_non_wheat.subgroup == "gliadin_unspecified"
    assert result_non_wheat.broad_group == "gliadin"
    assert result_non_wheat.unresolved is True


def test_non_gliadin_storage_proteins_do_not_fall_into_gliadin() -> None:
    rules = load_rules(RULE_PATH)

    avenin_like = {
        "primaryAccession": "Q2A783",
        "uniProtkbId": "AVENIN_LIKE_1",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Avenin-like b1"}}
        },
        "keywords": [{"value": "Seed storage protein"}],
        "organism": {"scientificName": "Triticum aestivum"},
    }
    avenin_like_result = classify_entry(extract_entry(avenin_like), rules)
    assert avenin_like_result.subgroup == "unclassified"

    lipid_transfer = {
        "primaryAccession": "A0A3B6T7X8",
        "uniProtkbId": "LTP_STORAGE_1",
        "proteinDescription": {
            "recommendedName": {
                "fullName": {
                    "value": (
                        "Bifunctional inhibitor/plant lipid transfer protein/"
                        "seed storage helical domain-containing protein"
                    )
                }
            }
        },
        "comments": [
            {
                "commentType": "FUNCTION",
                "texts": [
                    {
                        "value": (
                            "Seed storage protein. Might be integrated via "
                            "inter-chain disulfide bonds within the glutenin polymer"
                        )
                    }
                ],
            },
            {
                "commentType": "SIMILARITY",
                "texts": [{"value": "Belongs to the prolamin family"}],
            },
        ],
        "organism": {"scientificName": "Triticum aestivum"},
    }
    lipid_transfer_result = classify_entry(extract_entry(lipid_transfer), rules)
    assert lipid_transfer_result.subgroup == "unclassified"


def test_generic_prolamin_locus_hints_stay_unspecified() -> None:
    rules = load_rules(RULE_PATH)

    for accession, gene_name in (
        ("P11111", "Gli-2"),
        ("P22222", "Gli-4"),
        ("P33333", "Gli-1"),
    ):
        entry = {
            "primaryAccession": accession,
            "uniProtkbId": f"{gene_name}_WHEAT",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Prolamin"}}
            },
            "genes": [{"geneName": {"value": gene_name}}],
            "comments": [
                {
                    "commentType": "FUNCTION",
                    "texts": [
                        {"value": "Gliadin is the major seed storage protein in wheat"}
                    ],
                },
                {
                    "commentType": "SIMILARITY",
                    "texts": [{"value": "Belongs to the gliadin/glutenin family"}],
                },
            ],
            "organism": {"scientificName": "Triticum aestivum"},
        }
        result = classify_entry(extract_entry(entry), rules)
        assert result.subgroup == "gliadin_unspecified"
        assert result.broad_group == "gliadin"
        assert result.unresolved is True


def test_non_matching_named_protein_stays_unclassified() -> None:
    rules = load_rules(RULE_PATH)
    data = {
        "primaryAccession": "N11111",
        "uniProtkbId": "ARABIDOPSIS_NAMED",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Cellulose synthase"}}
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


def test_yaml_loading_rejects_organism_regex_field(tmp_path) -> None:
    bad_rule_file = tmp_path / "bad_rules.yaml"
    bad_rule_file.write_text(
        """
- name: bad
  priority: 1
  broad_group: gliadin
  subgroup: gliadin
  organism_regex: triticum
  include_patterns:
    - gliadin
  exclude_patterns: []
  confidence: high
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(RuleValidationError, match="unsupported fields"):
        load_rules(bad_rule_file)
