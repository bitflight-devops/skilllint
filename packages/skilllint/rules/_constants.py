"""Rule-set constants for the skilllint rules package."""

from __future__ import annotations

from typing import Literal

# Live value space of RuleEntry.category, grepped from every @skilllint_rule(...)
# call site in packages/skilllint/rules/*_series.py (issue #41 item 3). Adding a
# new category requires adding it here first, or Pydantic rejects the
# registration at import time.
RuleCategory = Literal[
    "agent",
    "codex",
    "cursor",
    "frontmatter",
    "hook",
    "link",
    "namespace-reference",
    "plugin",
    "plugin-registration",
    "progressive-disclosure",
    "skill",
    "symlink",
    "token-count",
]

# Live value space of RuleEntry.platforms elements, including sites that omit
# platforms= and take the @skilllint_rule decorator's ["agentskills"] default.
RulePlatform = Literal["agentskills", "claude-code", "codex", "cursor"]

# Live value space of RuleEntry.client_load_behavior. Populated only when the
# client-implementation guide is explicit about what a real client does for a
# rule's finding — "warn-and-load" (validation is lenient; the client logs a
# warning and loads the skill anyway) or "skip-skill" (the client refuses to
# load the skill and logs an error). None (the RuleEntry default) means the
# guide does not say, mirroring RuleEntry.authority's None-means-unstated
# semantics rather than adding a separate "unknown" member.
# Source: https://agentskills.io/client-implementation/adding-skills-support#lenient-validation
ClientLoadBehavior = Literal["warn-and-load", "skip-skill"]

# Full set of expected series prefixes: the 14 series from P038 plus the AG
# agent-frontmatter series added for issue #132.
# CM001 is scoped out — reserved, no validator logic (P038 architect spec §9).
# Sources: P038 architect spec section 8; issue #132.
EXPECTED_SERIES: frozenset[str] = frozenset({
    "AG",
    "AS",
    "FM",
    "PA",
    "SK",
    "LK",
    "PD",
    "PL",
    "HK",
    "NR",
    "SL",
    "TC",
    "PR",
    "CU",
    "CX",
})

# Derived from EXPECTED_SERIES so the count never drifts from the canonical set.
MIN_REGISTERED_SERIES: int = len(EXPECTED_SERIES)
