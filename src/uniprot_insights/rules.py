from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, List, Optional

import yaml
from importlib import resources

from .exceptions import RuleValidationError
from .models import Rule


RULE_REQUIRED_FIELDS = {
    "name",
    "priority",
    "broad_group",
    "subgroup",
    "include_patterns",
    "exclude_patterns",
    "confidence",
}

RULE_UNSUPPORTED_FIELDS = {
    "organism_regex",
}


def _default_rules_path() -> Path:
    try:
        base = resources.files("uniprot_insights")
        return Path(base / "data" / "default_rules.yaml")
    except Exception:
        return Path("src/uniprot_insights/data/default_rules.yaml")


def _validate_rules_item(item: Any, index: int) -> Rule:
    if not isinstance(item, dict):
        raise RuleValidationError(f"Rule at position {index} must be a mapping")
    missing = RULE_REQUIRED_FIELDS - set(item)
    if missing:
        raise RuleValidationError(
            f"Rule at position {index} missing fields: {sorted(missing)}"
        )
    unsupported = RULE_UNSUPPORTED_FIELDS & set(item)
    if unsupported:
        raise RuleValidationError(
            f"Rule at position {index} has unsupported fields: {sorted(unsupported)}"
        )

    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        raise RuleValidationError(f"Rule at position {index} has invalid name")

    priority = item.get("priority")
    if not isinstance(priority, int):
        raise RuleValidationError(f"Rule {name} has non-integer priority")

    broad_group = item.get("broad_group")
    if not isinstance(broad_group, str) or not broad_group.strip():
        raise RuleValidationError(f"Rule {name} has invalid broad_group")

    subgroup = item.get("subgroup")
    if not isinstance(subgroup, str) or not subgroup.strip():
        raise RuleValidationError(f"Rule {name} has invalid subgroup")

    include_patterns = item.get("include_patterns")
    if not isinstance(include_patterns, list) or not include_patterns:
        raise RuleValidationError(f"Rule {name} has invalid include_patterns")
    for pattern in include_patterns:
        if not isinstance(pattern, str):
            raise RuleValidationError(
                f"Rule {name} includes non-string include_patterns value"
            )
        try:
            re.compile(pattern, flags=re.IGNORECASE)
        except re.error as exc:
            raise RuleValidationError(
                f"Rule {name} has invalid include pattern {pattern!r}: {exc}"
            ) from exc

    exclude_patterns = item.get("exclude_patterns")
    if not isinstance(exclude_patterns, list):
        raise RuleValidationError(f"Rule {name} has invalid exclude_patterns")
    for pattern in exclude_patterns:
        if not isinstance(pattern, str):
            raise RuleValidationError(
                f"Rule {name} includes non-string exclude_patterns value"
            )
        try:
            re.compile(pattern, flags=re.IGNORECASE)
        except re.error as exc:
            raise RuleValidationError(
                f"Rule {name} has invalid exclude pattern {pattern!r}: {exc}"
            ) from exc

    confidence = item.get("confidence")
    if not isinstance(confidence, str) or not confidence.strip():
        raise RuleValidationError(f"Rule {name} has invalid confidence")

    return Rule(
        name=name,
        priority=priority,
        broad_group=broad_group,
        subgroup=subgroup,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        confidence=confidence,
    )


def load_rules(rule_file: Optional[Path | str] = None) -> List[Rule]:
    path = Path(rule_file) if rule_file else _default_rules_path()
    if not path.exists():
        raise RuleValidationError(f"Rules file does not exist: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, list):
        raise RuleValidationError("Rules file must define a YAML list")

    rules = [_validate_rules_item(item, index + 1) for index, item in enumerate(data)]
    names = [rule.name for rule in rules]
    if len(set(names)) != len(names):
        raise RuleValidationError("Rule names must be unique")

    return sorted(rules, key=lambda rule: rule.priority)
