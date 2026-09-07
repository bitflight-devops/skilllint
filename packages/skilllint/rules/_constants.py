"""Rule-set constants for the skilllint rules package."""

from __future__ import annotations

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
