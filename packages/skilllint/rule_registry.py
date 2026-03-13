"""Rule registry and @skilllint_rule decorator.

Each validator function is decorated with @skilllint_rule:

    @skilllint_rule(
        "SK001",
        severity="error",
        category="skill",
        platforms=["agentskills"],
    )
    def check_name_field(frontmatter: dict, path: Path) -> list[ValidationIssue]:
        \"\"\"
        ## SK001 — Missing `name` field

        Every SKILL.md must declare a `name` field in its frontmatter.

        **Fix:** Add `name: your-skill-name` to the frontmatter block.
        \"\"\"

The decorator registers the rule in RULE_REGISTRY for `skilllint rule <ID>` lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class RuleEntry:
    """Registry entry for a single validation rule."""

    id: str
    fn: Callable
    severity: str  # "error", "warning", "info"
    category: str  # "frontmatter", "skill", "plugin", "hook", etc.
    platforms: list[str]  # ["agentskills"] = all platforms, or specific like ["claude-code"]
    docstring: str


# Global registry: rule ID → RuleEntry
RULE_REGISTRY: dict[str, RuleEntry] = {}


def skilllint_rule(
    rule_id: str, *, severity: str, category: str, platforms: list[str] | None = None
) -> Callable[[Callable], Callable]:
    """Decorator to register a validator function as a rule.

    Args:
        rule_id: Rule identifier (e.g., "SK001", "FM002")
        severity: One of "error", "warning", "info"
        category: Rule category (e.g., "frontmatter", "skill", "plugin")
        platforms: List of platforms this rule applies to. ["agentskills"] means all platforms.
                   Defaults to ["agentskills"].

    Returns:
        Decorated function (unchanged) that's registered in RULE_REGISTRY.

    Example:
        @skilllint_rule("SK001", severity="error", category="skill")
        def check_name(frontmatter: dict) -> list[ValidationIssue]:
            '''## SK001 — Missing name field

            Every skill must have a name.
            '''
            ...
    """
    if platforms is None:
        platforms = ["agentskills"]

    def decorator(fn: Callable) -> Callable:
        entry = RuleEntry(
            id=rule_id.upper(),
            fn=fn,
            severity=severity,
            category=category,
            platforms=platforms,
            docstring=fn.__doc__ or f"Rule {rule_id}",
        )
        RULE_REGISTRY[rule_id.upper()] = entry
        return fn

    return decorator


def get_rule(rule_id: str) -> RuleEntry | None:
    """Look up a rule by ID (case-insensitive).

    Args:
        rule_id: Rule identifier (e.g., "SK001", "sk001")

    Returns:
        RuleEntry if found, None otherwise.
    """
    return RULE_REGISTRY.get(rule_id.upper())


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


__all__ = ["RULE_REGISTRY", "RuleEntry", "get_rule", "list_rules", "skilllint_rule"]
