from __future__ import annotations

import pytest

from uniprot_insights.rules import load_rules


@pytest.mark.integration
def test_default_rules_are_loadable_from_packaged_resources() -> None:
    rules = load_rules()

    assert len(rules) > 0
    assert [rule.priority for rule in rules] == sorted(rule.priority for rule in rules)
