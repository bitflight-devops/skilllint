"""Dependency-light fixer authorization and execution orchestration.

The legacy skilllint.plugin_validator module re-exports the public fixer
contract while #283 decomposes the central validator. This module deliberately
does not select fixers or import concrete validator implementations.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from pathlib import Path

from skilllint.models import AppliedFix, Validator

# Rule codes that authorise a fixer to run against a path under --fix.
# Keyed by validator class name, matching the historical compatibility
# contract in plugin_validator. An undeclared fixer receives no triggers and
# therefore never runs (fail closed).
#
# The trigger set for a validator is not always the codes it reports:
# - NameFormatValidator repairs FM010 even though FrontmatterValidator reports it.
# - FrontmatterValidator also repairs a missing name reported as AS001.
FIXER_TRIGGER_CODES: dict[str, frozenset[str]] = {
    "SymlinkTargetValidator": frozenset({"SL001"}),
    "FrontmatterValidator": frozenset({"FM004", "FM007", "FM009", "FM010", "AS001"}),
    "NameFormatValidator": frozenset({"FM010"}),
    "HookValidator": frozenset({"HK005"}),
}


def get_fixer_trigger_codes(validator: Validator) -> frozenset[str]:
    """Return the rule codes that authorise a validator's fixer.

    Args:
        validator: Validator instance being considered for auto-fixing.

    Returns:
        Declared trigger codes for the validator class, or an empty set for an
        undeclared fixer so authorization fails closed.
    """
    return FIXER_TRIGGER_CODES.get(type(validator).__name__, frozenset())


def apply_authorized_fixes(
    fixers: Sequence[Validator], path: Path, *, raw_codes: Collection[str], fixes_out: list[AppliedFix] | None = None
) -> bool:
    """Run ordered fixers whose declared rule codes fired for path.

    raw_codes must contain pre-suppression findings. Reporting suppression
    does not revoke authorization to repair a finding.

    Args:
        fixers: Already ordered fixer sequence selected for the path.
        path: Path to mutate.
        raw_codes: Finding codes emitted before reporting suppression.
        fixes_out: Optional append-only record of applied fixes.

    Returns:
        True when at least one fixer reports an applied mutation and the
        caller should revalidate the path.
    """
    applied = False
    for fixer in fixers:
        if not fixer.can_fix():
            continue

        triggered_codes = get_fixer_trigger_codes(fixer).intersection(raw_codes)
        if not triggered_codes:
            continue

        try:
            descriptions = fixer.fix(path)
        except NotImplementedError:
            continue

        if not descriptions:
            continue

        applied = True
        if fixes_out is not None:
            codes = tuple(sorted(triggered_codes))
            fixes_out.extend(
                AppliedFix(path=path, validator=type(fixer).__name__, codes=codes, description=description)
                for description in descriptions
            )

    return applied


__all__ = ["FIXER_TRIGGER_CODES", "apply_authorized_fixes", "get_fixer_trigger_codes"]
