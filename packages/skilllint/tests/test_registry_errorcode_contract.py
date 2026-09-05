"""Pin the intentional RULE_REGISTRY / ErrorCode divergence so it cannot drift (#40).

RULE_REGISTRY is authoritative for which rules exist; plugin_validator.ErrorCode
is a legacy, partial enum retained for specific historical consumers and was
never meant to mirror the registry 1:1 (see the contract note next to
RULE_REGISTRY in rule_registry.py). Two known divergences are intentional:

- Registry-only: AS001, AS006, AS008, AS009 -- real rules registered via
  @skilllint_rule. Their ErrorCode members were deliberately removed in PR
  #102 ("rule de-duplication + authority split") because they were
  false-positive-prone; the registry entries survived, the enum members did
  not.
- Enum-only: CM001 -- a reserved placeholder (plugin_validator.py, commented
  "Command-specific validation (reserved)") with no validator logic, so it
  was never registered. `_constants.py` already documents it as scoped out
  (P038 architect spec S9).

This test pins those two sets exactly. If a future change adds or removes a
rule such that the divergence shifts, this test fails and forces a conscious
choice: update the pinned sets here (with justification) if the new
divergence is also intentional, or fix the actual drift.
"""

from __future__ import annotations

import skilllint.rules  # noqa: F401  # populates RULE_REGISTRY via @skilllint_rule side effects
from skilllint.plugin_validator import ErrorCode
from skilllint.rule_registry import RULE_REGISTRY

_KNOWN_REGISTRY_ONLY = frozenset({"AS001", "AS006", "AS008", "AS009"})
_KNOWN_ENUM_ONLY = frozenset({"CM001"})


def test_registry_errorcode_divergence_is_the_known_intentional_set() -> None:
    """RULE_REGISTRY and ErrorCode must differ by exactly the pinned, intentional set."""
    registry_codes = set(RULE_REGISTRY)
    enum_codes = {member.name for member in ErrorCode}

    registry_only = registry_codes - enum_codes
    enum_only = enum_codes - registry_codes

    assert registry_only == _KNOWN_REGISTRY_ONLY, (
        f"RULE_REGISTRY codes missing from ErrorCode changed: got {sorted(registry_only)}, "
        f"expected {sorted(_KNOWN_REGISTRY_ONLY)}. If this is a new intentional divergence, "
        "update _KNOWN_REGISTRY_ONLY with justification; otherwise fix the drift."
    )
    assert enum_only == _KNOWN_ENUM_ONLY, (
        f"ErrorCode codes missing from RULE_REGISTRY changed: got {sorted(enum_only)}, "
        f"expected {sorted(_KNOWN_ENUM_ONLY)}. If this is a new intentional divergence, "
        "update _KNOWN_ENUM_ONLY with justification; otherwise fix the drift."
    )
