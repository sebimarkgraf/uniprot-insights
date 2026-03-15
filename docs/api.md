# API reference

## Package exports

The package exposes these public symbols in `uniprot_insights`:

```python
from uniprot_insights import (
    UniProtClient,
    ClassificationResult,
    ExtractedEntry,
    Rule,
    annotate,
    annotate_accession,
    annotate_accessions,
    classify_entry,
    extract_entry,
    load_rules,
    summarize_batch,
)
```

## Typical workflow

1. Load and validate rules (default is internal `default_rules.yaml`).
2. Fetch entries using the API client (or via the CLI).
3. Extract normalized annotation text.
4. Run classification and consume `ClassificationResult` records.

## Error handling

Public exception classes live in `uniprot_insights.exceptions` and are re-exported
through CLI behavior and tests. If the API request fails or returns unexpected payloads,
the client uses request/parse specific errors from the same module.

