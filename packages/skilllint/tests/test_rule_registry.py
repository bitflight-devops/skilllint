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
    RULE_REGISTRY.update({
        "AA001": _entry("AA001", "https://example.test/spec#a"),
        "AA002": _entry("AA002", "https://example.test/spec#a"),
        "AA003": _entry("AA003", None),
        "AA004": _entry("AA004", ""),
        "AA005": _entry("AA005", "https://example.test/spec#b"),
    })

    urls = list(iter_authority_urls())

    assert urls == ["https://example.test/spec#a", "https://example.test/spec#b"]


def test_iter_authority_urls_non_unique_keeps_duplicates() -> None:
    """unique=False includes duplicated references from multiple rules."""
    RULE_REGISTRY.clear()
    RULE_REGISTRY.update({
        "AA001": _entry("AA001", "https://example.test/spec#a"),
        "AA002": _entry("AA002", "https://example.test/spec#a"),
        "AA003": _entry("AA003", "https://example.test/spec#b"),
    })

    urls = list(iter_authority_urls(unique=False))

    assert urls == ["https://example.test/spec#a", "https://example.test/spec#a", "https://example.test/spec#b"]


def test_iter_authority_urls_resolves_relative_reference_to_absolute_url() -> None:
    """Relative references are resolved against the authority origin.

    Tests: iter_authority_urls relative-to-absolute URL resolution
    How: AA001 uses an absolute-path reference (/specification#name) with a
         valid origin; AA003 already carries an absolute URL; AA004 has an
         absolute-path reference but an empty origin so it cannot be resolved
         and must be dropped.
    Why: Verifies that the resolver correctly constructs full URLs from
         relative references and silently discards entries whose origin is
         absent (rather than surfacing a malformed URL).
    """
    RULE_REGISTRY.clear()
    RULE_REGISTRY.update({
        "AA001": _entry("AA001", "/specification#name"),
        "AA003": _entry("AA003", "https://example.test/specification#limits"),
        "AA004": _entry("AA004", "/ignored", origin=""),
    })

    urls = list(iter_authority_urls())

    assert urls == ["https://example.test/specification#name", "https://example.test/specification#limits"]


def test_iter_authority_urls_deduplicates_references_that_normalize_to_same_url() -> None:
    """Multiple references that resolve to the same URL are deduplicated.

    Tests: iter_authority_urls deduplication after relative-reference resolution
    How: AA001 ("/specification#name") and AA002 ("specification#name") both
         resolve to "https://example.test/specification#name" against the same
         origin.  The two distinct input forms must collapse to a single output
         URL.  AA003 carries a different absolute URL to confirm the other entry
         is still present.
    Why: Separate rules may cite the same spec page with different syntactic
         forms (leading slash vs. no slash).  Without deduplication,
         fetch-authorities would fetch the same page twice and silently mask
         the duplication.
    """
    RULE_REGISTRY.clear()
    RULE_REGISTRY.update({
        # Both forms resolve to https://example.test/specification#name
        "AA001": _entry("AA001", "/specification#name"),
        "AA002": _entry("AA002", "specification#name"),
        "AA003": _entry("AA003", "https://example.test/specification#limits"),
    })

    urls = list(iter_authority_urls())

    assert urls == ["https://example.test/specification#name", "https://example.test/specification#limits"]
