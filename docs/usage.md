# Library and CLI usage

## Python API

```python
from uniprot_insights import annotate_accession, annotate_accessions

# Classify a single accession from UniProt.
result = annotate_accession("P12345")
print(result.broad_group)

# Classify a list of accessions at once.
results = annotate_accessions(["P12345", "Q9XYZ1"])
for item in results:
    print(item.accession, item.broad_group, item.subgroup)
```

## CLI usage

```bash
uniprot-insights classify-id P12345 Q67890
```

```bash
uniprot-insights classify-file proteins.csv --column accession --output classified.csv
```

```bash
uniprot-insights dump-entry P12345
```

### Validating rules

```bash
uniprot-insights validate-rules
uniprot-insights validate-rules path/to/custom_rules.yaml
```

## Custom rules

Pass a custom rule file with `--rules`:

```bash
uniprot-insights classify-file proteins.csv \
  --column accession \
  --rules ./my_rules.yaml
```

