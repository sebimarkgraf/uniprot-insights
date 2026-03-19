# Rule configuration

Rules are ordered by `priority`; first match wins.

```yaml
- name: omega_5_gliadin
  priority: 10
  broad_group: gliadin
  subgroup: omega_5_gliadin
  organism_regex: triticum
  include_patterns:
    - "omega[- ]?5 gliadin"
  exclude_patterns: []
  confidence: high
```

## Field reference

- `name`: Unique identifier for the rule.
- `priority`: Lower values are evaluated first.
- `broad_group`: Primary classification group.
- `subgroup`: Optional subtype; defaults to a fallback when empty.
- `organism_regex`: Optional regex matched against extracted organism text.
- `include_patterns`: Regex patterns that must match the combined annotation text.
- `exclude_patterns`: Optional regex patterns that must **not** match.
- `confidence`: Human-readable confidence label.

## Matching behavior

- `organism_regex` must match when set.
- At least one `include_pattern` must match.
- None of `exclude_patterns` may match.
- The first rule that matches is selected.

Fallback classes:

- `gliadin_unspecified`
- `glutenin_unspecified`
- `prolamin_unspecified`
- `unclassified`

The packaged rules currently cover:

- Wheat gliadin and glutenin families.
- Related cereal prolamins such as secalins and maize gamma prolamins.
- Selected cereal seed-defense families including amylase/trypsin inhibitors,
  lipid-transfer proteins, puroindolines, and thionins.
