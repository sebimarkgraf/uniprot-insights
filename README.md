# uniprot-insights

[![CI](https://img.shields.io/github/actions/workflow/status/sebimarkgraf/uniprot-insights/ci.yml?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/sebimarkgraf/uniprot-insights/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/github/actions/workflow/status/sebimarkgraf/uniprot-insights/docs.yml?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/sebimarkgraf/uniprot-insights/actions/workflows/docs.yml)
[![Python](https://img.shields.io/badge/Python-%3E%3D3.10-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Issues](https://img.shields.io/github/issues/sebimarkgraf/uniprot-insights?style=flat-square&logo=github)](https://github.com/sebimarkgraf/uniprot-insights/issues)
[![Last Commit](https://img.shields.io/github/last-commit/sebimarkgraf/uniprot-insights?style=flat-square&logo=github)](https://github.com/sebimarkgraf/uniprot-insights/commits/main)
[![Stars](https://img.shields.io/github/stars/sebimarkgraf/uniprot-insights?style=flat-square&logo=github)](https://github.com/sebimarkgraf/uniprot-insights/stargazers)

`uniprot_insights` is a small UniProt-focused Python package for:

- downloading UniProtKB entries from the UniProt REST API
- extracting normalized annotation text from JSON payloads
- classifying entries with YAML-driven rules
- providing a practical CLI for annotation at scale

The packaged rule set covers wheat storage protein groups, related cereal storage proteins,
and a dedicated `uncharacterized_protein` class for entries explicitly annotated as
`Uncharacterized protein`, while the architecture is intentionally general enough to support
additional UniProt analyses later.

## Installation

```bash
pip install -e .
```

## Project layout

```text
uniprot-insights/
  pyproject.toml
  README.md
  src/uniprot_insights/
    __init__.py
    client.py
    models.py
    extractors.py
    rules.py
    classifier.py
    cache.py
    cli.py
    exceptions.py
    data/default_rules.yaml
  tests/
    test_client.py
    test_extractors.py
    test_classifier.py
    fixtures/
```

## Quick start

### Classify one or more accessions

```bash
uniprot-insights classify-id P12345 Q67890
```

### Classify all accessions in a CSV

```bash
uniprot-insights classify-file proteins.csv --column accession --output classified.csv
```

To extract entries that were not classified, use `--only-unclassified`. In output files,
"not classified" corresponds to `subgroup=unclassified`.

```bash
uniprot-insights classify-file proteins.csv \
  --column accession \
  --only-unclassified \
  --output unclassified.csv
```

### Dump the raw UniProt payload

```bash
uniprot-insights dump-entry P12345
```

### Validate rule file

```bash
uniprot-insights validate-rules
uniprot-insights validate-rules path/to/custom_rules.yaml
```

All classification commands output CSV by default with the columns:

`accession, organism, entry_name, broad_group, subgroup, confidence, evidence, matched_rule, unresolved`

## Rule format

Rules are stored in YAML and applied by ascending `priority`.

```yaml
- name: omega_5_gliadin
  priority: 10
  broad_group: gliadin
  subgroup: omega_5_gliadin
  include_patterns:
    - "omega[- ]?5 gliadin"
  exclude_patterns: []
  confidence: high
```

### Matching requirements

For each rule:

- at least one `include_pattern` must match `combined_text`
- no `exclude_pattern` may match
- first matching rule wins (priority order)

### Fallback behavior

- gliadin subtype match: `gliadin_unspecified`
- glutenin subtype match: `glutenin_unspecified`
- prolamin-only match: `prolamin_unspecified`
- explicit `Uncharacterized protein` annotation: `uncharacterized_protein`
- no match: `unclassified`

Use `dump-entry` on an accession with `subgroup=unclassified` to inspect the source UniProt
payload when debugging missing classifications.

## Development

Run tests:

```bash
pytest
```

## Documentation

This repository ships with MkDocs documentation:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv pip install -p .venv/bin/python "mkdocs>=1.6"
UV_CACHE_DIR=/tmp/uv-cache .venv/bin/mkdocs serve -a 0.0.0.0:8000
```

Open `http://127.0.0.1:8000` to view docs.

## Extending

Add new rule files with the same schema and point the CLI at them with `--rules`.
