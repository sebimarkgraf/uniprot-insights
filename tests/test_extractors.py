from __future__ import annotations

from pathlib import Path

import json

from uniprot_insights.extractors import extract_entry


def test_extract_entry_collects_required_fields() -> None:
    data = json.loads(Path("tests/fixtures/alpha_beta_gliadin.json").read_text())
    extracted = extract_entry(data)

    assert extracted.accession == "P11111"
    assert extracted.organism == "Triticum aestivum"
    assert extracted.entry_name == "ALPHA_BETA_1"
    assert "Alpha/Beta-gliadin precursor" in extracted.protein_names
    assert "alpha-gliadin precursor" in extracted.protein_names
    assert "GYI" in extracted.gene_names
    assert "Alpha-gliadin 5" in extracted.gene_names
    assert "Gliadin" in extracted.keywords
    assert "FUNCTION" in extracted.comments
    assert "wheat storage proteins" in extracted.comments


def test_extract_entry_combined_text_is_normalized() -> None:
    data = {
        "primaryAccession": "Q99999",
        "uniProtkbId": "SPACING_1",
        "proteinDescription": {
            "recommendedName": {
                "fullName": {
                    "value": "   Alpha\tBeta   gliadin  "
                }
            }
        },
        "organism": {"scientificName": "   Triticum \n aestivum "},
        "comments": [
            {"commentType": "FUNCTION", "texts": [{"value": "   Stored   Protein   "}]} 
        ],
    }
    extracted = extract_entry(data)
    assert extracted.combined_text == (
        "alpha beta gliadin triticum aestivum "
        "function stored protein spacing_1"
    )
