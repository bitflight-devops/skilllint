"""Tests for the ``client_load_behavior`` field on ``RuleEntry``.

This field records what a real Claude Code / agent-skill client actually does
for a rule's finding, per the client-implementation guide's "Lenient
validation" section
(https://agentskills.io/client-implementation/adding-skills-support#lenient-validation).
It is purely additive metadata: ``None`` means the guide does not say,
matching how ``RuleEntry.authority`` already works. See PR 10 in
`.claude/plans/what-needs-to-happen-functional-bumblebee.md`.
"""

from __future__ import annotations

import skilllint.rules  # noqa: F401 — registers every rule via import side effects
from skilllint.rule_registry import RuleEntry, list_rules, skilllint_rule


def test_rule_entry_client_load_behavior_defaults_to_none() -> None:
    """A RuleEntry built without client_load_behavior leaves it unset (None)."""
    entry = RuleEntry(id="ZZ001", severity="info", category="skill", platforms=["agentskills"], docstring="Rule ZZ001")

    assert entry.client_load_behavior is None


def test_skilllint_rule_decorator_threads_client_load_behavior_kwarg() -> None:
    """The @skilllint_rule decorator accepts and stores client_load_behavior."""
    from skilllint.rule_registry import RULE_REGISTRY

    original = dict(RULE_REGISTRY)
    try:

        @skilllint_rule("ZZ002", severity="info", category="skill", client_load_behavior="skip-skill")
        def _fake_rule() -> list:  # pragma: no cover — never invoked
            """Fake rule for decorator threading test."""
            return []

        assert RULE_REGISTRY["ZZ002"].client_load_behavior == "skip-skill"
    finally:
        RULE_REGISTRY.clear()
        RULE_REGISTRY.update(original)


def test_exactly_fm001_fm002_fm010_are_classified() -> None:
    """Pin the exact classified set so a future session cannot silently add a fourth.

    Per the client-implementation guide's "Lenient validation" bullets:
      - FM001 (missing/empty description branch) -> "skip-skill"
      - FM002 (unparseable YAML) -> "skip-skill"
      - FM010 (name/directory mismatch and >64 chars branches) -> "warn-and-load"

    Every other rule in the registry must stay unset (None) — this is not
    exhaustive of everything each rule checks, only the branches the guide is
    explicit about. See each rule's "Client behaviour" docstring paragraph for
    the branch-granularity caveat.
    """
    classified = sorted((r.id, r.client_load_behavior) for r in list_rules() if r.client_load_behavior)

    assert classified == [("FM001", "skip-skill"), ("FM002", "skip-skill"), ("FM010", "warn-and-load")]
