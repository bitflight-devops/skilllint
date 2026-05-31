"""Tests for rule registry helper iteration APIs."""

from __future__ import annotations

import logging

import pytest

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


# ---------------------------------------------------------------------------
# Regression tests for warning / silent-skip behaviour
# ---------------------------------------------------------------------------


def test_iter_authority_urls_warns_and_skips_empty_reference(caplog: pytest.LogCaptureFixture) -> None:
    """An empty-string authority.reference is skipped with a WARNING naming the rule.

    Tests: iter_authority_urls malformed-reference warning path (empty string)
    How: Register a rule whose authority.reference is "" (empty); set caplog to
         WARNING on logger "skilllint.rule_registry"; call iter_authority_urls;
         assert the URL is absent from results and a WARNING record containing
         the rule id is present in caplog.
    Why: An empty reference is present-but-malformed — the author intended to
         add a URL but left it blank.  The function must surface this mistake via
         a warning so it appears in application logs, while continuing iteration
         rather than aborting.  This regression test locks in that the
         ``if not reference.strip()`` branch emits a WARNING and names the rule.
    """
    # Arrange
    RULE_REGISTRY.clear()
    RULE_REGISTRY["FM004"] = _entry("FM004", "")

    # Act
    with caplog.at_level(logging.WARNING, logger="skilllint.rule_registry"):
        urls = list(iter_authority_urls())

    # Assert — URL is skipped
    assert urls == []
    # Assert — a warning was logged that names the rule
    assert any("FM004" in record.message for record in caplog.records)
    assert all(record.levelno >= logging.WARNING for record in caplog.records if "FM004" in record.message)


def test_iter_authority_urls_warns_and_skips_whitespace_reference(caplog: pytest.LogCaptureFixture) -> None:
    """A whitespace-only authority.reference is skipped with a WARNING naming the rule.

    Tests: iter_authority_urls malformed-reference warning path (whitespace)
    How: Register a rule whose authority.reference is "   " (spaces only);
         capture WARNING-level logs; assert the URL is absent and the rule id
         appears in a warning record.
    Why: The strip() check treats whitespace-only the same as empty — both are
         present-but-malformed and indicate an authoring error.  This test
         exercises the same branch as the empty-string test with a distinct
         input to confirm strip() is applied.
    """
    # Arrange
    RULE_REGISTRY.clear()
    RULE_REGISTRY["FM007"] = _entry("FM007", "   ")

    # Act
    with caplog.at_level(logging.WARNING, logger="skilllint.rule_registry"):
        urls = list(iter_authority_urls())

    # Assert — URL is skipped
    assert urls == []
    # Assert — a warning was logged that names the rule
    assert any("FM007" in record.message for record in caplog.records)


def test_iter_authority_urls_warns_and_skips_relative_reference_with_empty_origin(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A relative reference with an empty origin is skipped with a WARNING naming the rule.

    Tests: iter_authority_urls unresolvable-relative-reference warning path
    How: Register a rule whose authority.reference is a relative path
         ("/rules/FM008") but whose authority.origin is "" (empty after strip);
         capture WARNING-level logs; assert the URL is absent and the rule id
         appears in a warning record.
    Why: A relative reference without an origin cannot be resolved to an
         absolute URL.  The function must warn rather than silently skip or
         raise an exception so authoring errors are visible in logs.
    """
    # Arrange
    RULE_REGISTRY.clear()
    RULE_REGISTRY["FM008"] = _entry("FM008", "/rules/FM008", origin="")

    # Act
    with caplog.at_level(logging.WARNING, logger="skilllint.rule_registry"):
        urls = list(iter_authority_urls())

    # Assert — URL is skipped
    assert urls == []
    # Assert — a warning was logged that names the rule
    assert any("FM008" in record.message for record in caplog.records)


def test_iter_authority_urls_silently_skips_none_reference(caplog: pytest.LogCaptureFixture) -> None:
    """A rule whose authority.reference is None is skipped silently — no warning.

    Tests: iter_authority_urls silent-skip path for reference=None
    How: Register a rule whose authority.reference is None; capture WARNING-level
         logs on "skilllint.rule_registry"; call iter_authority_urls; assert no
         URL is yielded AND no log record mentions the rule id.
    Why: None is the intentional "this rule has no external reference" sentinel
         as defined by RuleAuthority.  It is not an authoring error and must not
         produce log noise.  This regression test ensures the ``if reference is
         None: continue`` branch does not accidentally call _logger.warning.
    """
    # Arrange
    RULE_REGISTRY.clear()
    RULE_REGISTRY["FM009"] = _entry("FM009", reference=None)

    # Act
    with caplog.at_level(logging.WARNING, logger="skilllint.rule_registry"):
        urls = list(iter_authority_urls())

    # Assert — URL is skipped
    assert urls == []
    # Assert — no warning was logged for this rule
    assert not any("FM009" in record.message for record in caplog.records)
