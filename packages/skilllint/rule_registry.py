"""Rule registry and @skilllint_rule decorator.

Each validator function is decorated with @skilllint_rule:

    @skilllint_rule(
        "SK004",
        severity="warning",
        category="skill",
        platforms=["agentskills"],
        authority={"origin": "agent-skills.io", "reference": "/rules/SK004"},
    )
    def check_description_length(frontmatter: dict, path: Path) -> list[ValidationIssue]:
        \"\"\"
        ## SK004 — Description too short

        A SKILL.md description shorter than the minimum is unlikely to trigger
        auto-invocation.

        **Fix:** Expand the `description` field to state when the skill applies.
        \"\"\"

The decorator registers the rule in RULE_REGISTRY for `skilllint rule <ID>` lookup.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Annotated, Literal
from urllib.parse import urljoin

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from collections.abc import Callable

    from skilllint.plugin_validator import ValidationIssue

_logger = logging.getLogger(__name__)


def rule_reference(code: str) -> str:
    """Return the command that renders a rule's full documentation.

    Findings point here rather than at an external URL. The reference is
    derived from the rule code, so it cannot drift from the registry, and it
    resolves for every user of the published CLI regardless of which
    repository they are linting.

    Args:
        code: Rule code, e.g. "FM001".

    Returns:
        The ``skilllint rule <CODE>`` invocation for that rule.
    """
    return f"skilllint rule {str(code).upper()}"


def _make_issue(
    *, field: str, severity: Literal["error", "warning", "info"], message: str, code: str, suggestion: str | None = None
) -> ValidationIssue:
    """Construct a ValidationIssue for a rule.

    Shared across the rules/*.py series modules to avoid duplicating the same
    construction across files.

    Args:
        field: Issue field label (meaning varies by rule series).
        severity: Issue severity.
        message: Human-readable description.
        code: Rule code (e.g. "FM001").
        suggestion: Optional repair hint.

    Returns:
        A frozen ValidationIssue instance.
    """
    # Deferred import to break the circular dependency: plugin_validator
    # imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    return ValidationIssue(
        field=field, severity=severity, message=message, code=code, docs_url=rule_reference(code), suggestion=suggestion
    )


class RuleAuthority(BaseModel):
    """Structured authority metadata for a validation rule.

    Captures where a rule originates and where its documentation lives.
    This enables tracing any validation back to its source authority.
    """

    origin: str  # e.g., "agent-skills.io", "anthropic.com"
    reference: str | None = None  # URL or doc path, e.g., "/rules/SK004"


class RuleEntry(BaseModel):
    """Registry entry for a single validation rule."""

    id: Annotated[str, Field(pattern=r"^[A-Z]{2}\d{3}$")]
    severity: Literal["error", "warning", "info"]
    category: str  # "frontmatter", "skill", "plugin", "hook", etc.
    platforms: list[str]  # ["agentskills"] = all platforms, or specific like ["claude-code"]
    docstring: str
    authority: RuleAuthority | None = None


# Global registry: rule ID → RuleEntry
#
# RULE_REGISTRY is authoritative for which rules exist -- it backs `skilllint
# rules`, `skilllint rule <ID>`, and rule-catalog.md. plugin_validator.ErrorCode
# is a legacy, partial enum kept only for specific historical consumers; it is
# not expected to have 1:1 membership with RULE_REGISTRY (see #40 and
# packages/skilllint/tests/test_registry_errorcode_contract.py, which pins the
# known, intentional divergence).
RULE_REGISTRY: dict[str, RuleEntry] = {}


def skilllint_rule(
    rule_id: str,
    *,
    severity: Literal["error", "warning", "info"],
    category: str,
    platforms: list[str] | None = None,
    authority: dict | None = None,
) -> Callable[[Callable], Callable]:
    """Decorator to register a validator function as a rule.

    Args:
        rule_id: Rule identifier (e.g., "SK004", "FM002")
        severity: One of "error", "warning", "info"
        category: Rule category (e.g., "frontmatter", "skill", "plugin")
        platforms: List of platforms this rule applies to. ["agentskills"] means all platforms.
                   Defaults to ["agentskills"].
        authority: Optional authority metadata dict with 'origin' and optional 'reference' keys.
                   Converted to RuleAuthority dataclass.

    Returns:
        Decorated function (unchanged) that's registered in RULE_REGISTRY.

    Example:
        @skilllint_rule(
            "SK004",
            severity="warning",
            category="skill",
            authority={"origin": "agent-skills.io", "reference": "/rules/SK004"},
        )
        def check_description_length(frontmatter: dict) -> list[ValidationIssue]:
            '''## SK004 — Description too short

            A short description is unlikely to trigger auto-invocation.
            '''
            ...
    """
    if platforms is None:
        platforms = ["agentskills"]

    # Convert authority dict to RuleAuthority if provided
    rule_authority: RuleAuthority | None = None
    if authority is not None:
        rule_authority = RuleAuthority(origin=authority.get("origin", ""), reference=authority.get("reference"))

    def decorator(fn: Callable) -> Callable:
        entry = RuleEntry(
            id=rule_id.upper(),
            severity=severity,
            category=category,
            platforms=platforms,
            docstring=fn.__doc__ or f"Rule {rule_id}",
            authority=rule_authority,
        )
        RULE_REGISTRY[rule_id.upper()] = entry
        return fn

    return decorator


def get_rule(rule_id: str) -> RuleEntry | None:
    """Look up a rule by ID (case-insensitive).

    Args:
        rule_id: Rule identifier (e.g., "SK004", "sk004")

    Returns:
        RuleEntry if found, None otherwise.
    """
    return RULE_REGISTRY.get(rule_id.upper())


def rule_authority(code: str) -> dict[str, str] | None:
    """Return a rule's authority metadata as a plain dict for violation output.

    Args:
        code: Rule identifier (e.g., "FM010", "as006"). Case-insensitive.

    Returns:
        ``{"origin": ..., "reference": ...}`` (reference omitted when the rule
        declares none), or None when the rule is unknown or declares no
        authority.
    """
    entry = RULE_REGISTRY.get(code.upper())
    if entry is None or entry.authority is None:
        return None
    result = {"origin": entry.authority.origin}
    if entry.authority.reference:
        result["reference"] = entry.authority.reference
    return result


def list_rules(
    *, platform: str | None = None, category: str | None = None, severity: str | None = None
) -> list[RuleEntry]:
    """List rules, optionally filtered.

    Args:
        platform: Filter to rules that apply to this platform
        category: Filter to rules in this category
        severity: Filter to rules with this severity

    Returns:
        List of matching RuleEntry objects, sorted by ID.
    """
    rules = list(RULE_REGISTRY.values())

    if platform:
        rules = [r for r in rules if "agentskills" in r.platforms or platform in r.platforms]

    if category:
        rules = [r for r in rules if r.category == category]

    if severity:
        rules = [r for r in rules if r.severity == severity]

    return sorted(rules, key=lambda r: r.id)


def iter_authority_urls(*, unique: bool = True) -> Iterator[str]:
    """Iterate normalized authority documentation URLs from registered rules.

    Rules whose ``authority`` is ``None`` are silently skipped — a ``None``
    authority is the conventional sentinel for "this rule has no external
    reference" and is not an authoring error.

    Rules whose ``authority.reference`` is ``None`` are also silently skipped
    for the same reason: ``None`` is the intentional "no reference" value as
    defined by :class:`RuleAuthority`.

    Rules that are malformed — where ``reference`` is present but empty or
    whitespace-only, or where a relative ``reference`` cannot be resolved
    because ``origin`` is empty after stripping — are skipped with a
    ``WARNING`` log at logger ``skilllint.rule_registry`` (i.e. this module).
    The log message identifies the rule by its ``id`` and states the reason,
    so authoring mistakes surface in application logs without aborting
    iteration.

    Args:
        unique: When True, yield each normalized URL at most once while preserving
            first-seen order (by sorted rule ID). When False, include duplicates.

    Yields:
        Absolute authority documentation URLs.

    Note:
        **urljoin root-relative reference invariant.**
        When ``reference`` is not already absolute, this function resolves it
        against ``origin`` using ``urljoin``.  RFC 3986 §5.2 defines a
        root-relative reference (one that starts with ``/``) as resolving
        against the *scheme and host only* — the path component of the base
        URL is discarded.  Concretely::

            urljoin("https://github.com/org/repo/", "/docs#foo")
            # -> "https://github.com/docs#foo"   # /org/repo silently dropped

            urljoin("https://github.com/org/repo/", "docs#foo")
            # -> "https://github.com/org/repo/docs#foo"   # correct

        The current registry is safe: every rule whose ``origin`` contains a
        path component (e.g. ``"github.com/org/repo"``) already stores an
        absolute URL in ``reference`` (starts with ``https://``), so the
        ``urljoin`` branch is never reached for those entries.  Rules that
        use a root-relative ``reference`` (e.g. ``"/rules/SK004"``) pair it
        with a bare-host origin (e.g. ``"agentskills.io"``), where
        root-relative resolution is correct.

        **Registry constraint:** if a new rule is added with a path-containing
        origin *and* a root-relative reference, the path portion of the origin
        will be silently dropped.  Use an absolute URL in ``reference``
        whenever ``origin`` contains a path segment.
    """
    seen: set[str] = set()
    for rule in list_rules():
        if rule.authority is None:
            continue

        reference = rule.authority.reference
        # None means "intentionally no reference" — silent skip, not an error.
        if reference is None:
            continue

        # An empty or whitespace-only string is present-but-malformed.
        if not reference.strip():
            _logger.warning(
                "Rule %s: authority.reference is present but empty or whitespace — skipping URL resolution", rule.id
            )
            continue

        normalized = reference
        if not normalized.startswith(("https://", "http://")):
            origin = rule.authority.origin.strip()
            if not origin:
                _logger.warning(
                    "Rule %s: authority.reference %r is a relative reference but authority.origin is empty"
                    " — cannot resolve URL, skipping",
                    rule.id,
                    reference,
                )
                continue
            if "://" not in origin:
                origin = f"https://{origin}"
            normalized = urljoin(f"{origin.rstrip('/')}/", normalized)

        if unique:
            if normalized in seen:
                continue
            seen.add(normalized)

        yield normalized


__all__ = [
    "RULE_REGISTRY",
    "RuleAuthority",
    "RuleEntry",
    "get_rule",
    "iter_authority_urls",
    "list_rules",
    "rule_authority",
    "skilllint_rule",
]
