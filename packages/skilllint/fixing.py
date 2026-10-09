"""Dependency-light fixer authorization and execution orchestration.

The legacy skilllint.plugin_validator module re-exports the public fixer
contract while #283 decomposes the central validator. This module deliberately
does not select fixers or import concrete validator implementations.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from pathlib import Path

from skilllint.models import AppliedFix, RelocatingFixer, Validator

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


@dataclass(frozen=True)
class FixOutcome:
    """Result of running the authorised fixers against one path.

    Attributes:
        applied: True when at least one fixer reported an applied mutation and
            the caller should revalidate.
        path: Where the file is after the fixers ran. It differs from the path
            passed in when a fixer renamed or moved it.
    """

    applied: bool
    path: Path


def apply_authorized_fixes(
    fixers: Sequence[Validator], path: Path, *, raw_codes: Collection[str], fixes_out: list[AppliedFix] | None = None
) -> FixOutcome:
    """Run ordered fixers whose declared rule codes fired for path.

    raw_codes must contain pre-suppression findings. Reporting suppression
    does not revoke authorization to repair a finding.

    A fixer that moves the file (a :class:`~skilllint.models.RelocatingFixer`)
    hands the new path to the fixers after it, and every fix recorded in
    ``fixes_out`` carries the final path: the one that exists after the run.

    Args:
        fixers: Already ordered fixer sequence selected for the path.
        path: Path to mutate.
        raw_codes: Finding codes emitted before reporting suppression.
        fixes_out: Optional append-only record of applied fixes.

    Returns:
        The outcome: whether a fixer applied a mutation, and the path the file
        has afterwards.
    """
    applied = False
    current = path
    recorded: list[tuple[str, tuple[str, ...], str]] = []
    for fixer in fixers:
        if not fixer.can_fix():
            continue

        triggered_codes = get_fixer_trigger_codes(fixer).intersection(raw_codes)
        if not triggered_codes:
            continue

        try:
            descriptions = fixer.fix(current)
        except NotImplementedError:
            continue

        if not descriptions:
            continue

        applied = True
        codes = tuple(sorted(triggered_codes))
        recorded.extend((type(fixer).__name__, codes, description) for description in descriptions)
        if isinstance(fixer, RelocatingFixer):
            current = fixer.relocated_path() or current

    if fixes_out is not None:
        fixes_out.extend(
            AppliedFix(path=current, validator=validator, codes=codes, description=description)
            for validator, codes, description in recorded
        )
    return FixOutcome(applied=applied, path=current)


__all__ = ["FIXER_TRIGGER_CODES", "FixOutcome", "apply_authorized_fixes", "get_fixer_trigger_codes"]
