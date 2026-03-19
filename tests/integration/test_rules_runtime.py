from __future__ import annotations

import pytest

from uniprot_insights.rules import load_rules


@pytest.mark.integration
def test_default_rules_are_loadable_from_packaged_resources() -> None:
    rules = load_rules()

    assert len(rules) > 0
    assert [rule.priority for rule in rules] == sorted(rule.priority for rule in rules)


@pytest.mark.integration
def test_specific_storage_rules_precede_generic_prolamin_rules() -> None:
    rules = load_rules()
    priorities = {rule.name: rule.priority for rule in rules}

    assert priorities["gamma_secalin"] < priorities["cereal_prolamin"]
    assert priorities["omega_secalin"] < priorities["cereal_prolamin"]
    assert priorities["gamma_prolamin"] < priorities["cereal_prolamin"]
