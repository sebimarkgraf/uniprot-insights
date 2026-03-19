# uniprot-insights documentation

`uniprot-insights` is a small UniProt-focused Python package for retrieving UniProtKB
entries, extracting normalized annotations, and classifying proteins with a YAML rule set.

## What this library provides

- CLI commands for batch or single-entry classification.
- A reusable API for annotation, rule loading, extraction, and classification.
- A default rule set for wheat storage proteins, related cereal storage proteins,
  and selected cereal seed-defense families, with room to add additional rule files.

## Get started

Install the package and run a quick CLI command:

```bash
pip install -e .
uniprot-insights classify-id P12345
```

For Python usage, see [Usage](usage.md).
