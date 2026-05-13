"""Tests for rule registry helper iteration APIs."""

from __future__ import annotations

from skilllint.rule_registry import RULE_REGISTRY, RuleAuthority, RuleEntry, iter_authority_urls


def _entry(rule_id: str, reference: str | None, origin: str = "example.test") -> RuleEntry:
    authority = None if reference is None else RuleAuthority(origin=origin, reference=reference)
    return RuleEntry(
        id=rule_id,
        fn=lambda: None,
        severity="info",
        category="test",
        platforms=["agentskills"],
        docstring=f"Rule {rule_id}",
        authority=authority,
    )


def test_iter_authority_urls_unique_filters_empty_and_dedupes() -> None:
    """Default unique iteration dedupes while preserving first-seen order."""
    RULE_REGISTRY.clear()
    RULE_REGISTRY.update(
        {
            "AA001": _entry("AA001", "https://example.test/spec#a"),
            "AA002": _entry("AA002", "https://example.test/spec#a"),
            "AA003": _entry("AA003", None),
            "AA004": _entry("AA004", ""),
            "AA005": _entry("AA005", "https://example.test/spec#b"),
        }
    )

    urls = list(iter_authority_urls())

    assert urls == ["https://example.test/spec#a", "https://example.test/spec#b"]


def test_iter_authority_urls_non_unique_keeps_duplicates() -> None:
    """unique=False includes duplicated references from multiple rules."""
    RULE_REGISTRY.clear()
    RULE_REGISTRY.update(
        {
            "AA001": _entry("AA001", "https://example.test/spec#a"),
            "AA002": _entry("AA002", "https://example.test/spec#a"),
            "AA003": _entry("AA003", "https://example.test/spec#b"),
        }
    )

    urls = list(iter_authority_urls(unique=False))

    assert urls == [
        "https://example.test/spec#a",
        "https://example.test/spec#a",
        "https://example.test/spec#b",
    ]


def test_iter_authority_urls_resolves_relative_references() -> None:
    """Relative references are resolved against origin and deduped when normalized."""
    RULE_REGISTRY.clear()
    RULE_REGISTRY.update(
        {
            "AA001": _entry("AA001", "/specification#name"),
            "AA002": _entry("AA002", "specification#name"),
            "AA003": _entry("AA003", "https://example.test/specification#limits"),
            "AA004": _entry("AA004", "/ignored", origin=""),
        }
    )

    urls = list(iter_authority_urls())

    assert urls == [
        "https://example.test/specification#name",
        "https://example.test/specification#limits",
    ]
