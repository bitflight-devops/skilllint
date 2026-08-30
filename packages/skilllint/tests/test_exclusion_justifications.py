"""Guard against ruff/ty exclusions carrying an unverified provenance claim.

#119 excluded ``.agents/skills/*`` from ruff and ty as "vendored ... and
maintained there", implying an upstream sync this repo could not safely
lint over. That claim was false: no sync script, CI job, or
``.gitmodules`` entry has ever moved those skills out of this repo (see
#135, #143, #154). Because a wrong suppression produces no output, nothing
ever contradicted the sentence -- unlike a wrong rule finding, which a
reviewer eventually notices and fixes.

Every path in ``[tool.ruff].exclude`` and ``[tool.ty.src].exclude`` must
have a ``REGISTRY`` entry declaring *why*. Any reason asserting a claim
outside this repo (vendored, third-party) must name a ``sync_artifact``
that actually exists on disk. "First-party code" is not a reason at all --
``ExclusionReason`` has no such member, so a registry entry claiming it
fails to construct.

Blind spots (not covered by this guard):
  * A ``sync_artifact`` that exists but is stale or no longer performs a
    sync -- existence is checked, not function.
  * A reason that's technically true but still a bad idea to suppress for.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import no_type_check

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"


class ExclusionReason(StrEnum):
    """Closed set of reasons a path may be excluded from ruff/ty.

    ``DELIBERATELY_BROKEN_FIXTURE`` is self-evident from the path itself and
    needs no external proof. The other two assert that something outside
    this repo owns the file -- exactly the class of claim #119 lied about --
    so those require ``sync_artifact``.
    """

    DELIBERATELY_BROKEN_FIXTURE = "deliberately_broken_fixture"
    VENDORED = "vendored"
    THIRD_PARTY = "third_party"


_SELF_EVIDENT_REASONS = frozenset({ExclusionReason.DELIBERATELY_BROKEN_FIXTURE})


@dataclass(frozen=True, slots=True)
class ExclusionJustification:
    """A registry entry justifying one excluded path."""

    reason: ExclusionReason
    sync_artifact: str | None = None

    def __post_init__(self) -> None:
        ExclusionReason(self.reason)  # raises ValueError if reason isn't a real member
        if self.reason not in _SELF_EVIDENT_REASONS and self.sync_artifact is None:
            msg = f"reason {self.reason!r} asserts external provenance; sync_artifact is required"
            raise ValueError(msg)


# The only exclusion this repo can currently justify. `.agents/skills/*` is
# deliberately absent from history: #119's "vendored" claim named no
# sync_artifact and none existed, so no valid entry could be constructed for
# it -- #154 removed the exclusion instead. That absence is the assertion.
REGISTRY: dict[str, ExclusionJustification] = {
    "packages/skilllint/tests/fixtures/providers/*/failing-examples/*": ExclusionJustification(
        reason=ExclusionReason.DELIBERATELY_BROKEN_FIXTURE
    )
}


def find_unjustified_exclusions(
    exclusions: list[str], registry: Mapping[str, ExclusionJustification], repo_root: Path
) -> list[str]:
    """Return one message per excluded path that fails the justification contract.

    Args:
        exclusions: Paths from a ruff or ty ``exclude`` list.
        registry: Path to its ``ExclusionJustification``, e.g. ``REGISTRY``.
        repo_root: Root that ``sync_artifact`` paths are resolved against.

    Returns:
        Empty list if every path is justified.
    """
    violations = []
    for path in exclusions:
        entry = registry.get(path)
        if entry is None:
            violations.append(f"{path}: excluded with no registry entry declaring a reason")
            continue
        if entry.sync_artifact is not None and not (repo_root / entry.sync_artifact).exists():
            violations.append(
                f"{path}: reason {entry.reason!r} names sync_artifact "
                f"{entry.sync_artifact!r}, which does not exist in this repo"
            )
    return violations


def _load_pyproject_exclusions() -> tuple[list[str], list[str]]:
    """Read ``[tool.ruff].exclude`` and ``[tool.ty.src].exclude`` from the real pyproject.toml."""
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    return data["tool"]["ruff"]["exclude"], data["tool"]["ty"]["src"]["exclude"]


def test_ruff_exclusions_are_justified() -> None:
    """Every path in [tool.ruff].exclude must have a REGISTRY entry with a real reason."""
    ruff_exclude, _ = _load_pyproject_exclusions()
    violations = find_unjustified_exclusions(ruff_exclude, REGISTRY, REPO_ROOT)
    assert not violations, violations


def test_ty_exclusions_are_justified() -> None:
    """Every path in [tool.ty.src].exclude must have a REGISTRY entry with a real reason."""
    _, ty_exclude = _load_pyproject_exclusions()
    violations = find_unjustified_exclusions(ty_exclude, REGISTRY, REPO_ROOT)
    assert not violations, violations


def test_registry_rejects_119s_unsynced_vendored_claim() -> None:
    """#119's exact claim -- 'vendored', no artifact named -- must fail to register at all."""
    with pytest.raises(ValueError, match="sync_artifact is required"):
        ExclusionJustification(reason=ExclusionReason.VENDORED)


def test_checker_rejects_exclusion_missing_from_registry() -> None:
    """Requirement 1: an exclusion with no declared reason fails."""
    violations = find_unjustified_exclusions(["some/new/path/*"], REGISTRY, REPO_ROOT)
    assert violations == ["some/new/path/*: excluded with no registry entry declaring a reason"]


def test_checker_rejects_external_provenance_naming_nonexistent_artifact() -> None:
    """Requirement 2: an external-provenance reason naming a nonexistent artifact fails."""
    registry = {
        "vendored/thing/*": ExclusionJustification(
            reason=ExclusionReason.VENDORED, sync_artifact="does/not/exist/VERSION"
        )
    }
    violations = find_unjustified_exclusions(["vendored/thing/*"], registry, REPO_ROOT)
    assert violations == [
        (
            "vendored/thing/*: reason <ExclusionReason.VENDORED: 'vendored'> names sync_artifact "
            "'does/not/exist/VERSION', which does not exist in this repo"
        )
    ]


@no_type_check
def _construct_with_first_party_reason() -> ExclusionJustification:
    """Statically invalid on purpose: exercises the runtime guard ty would otherwise catch."""
    return ExclusionJustification(reason="first_party")


def test_registry_rejects_first_party_as_a_reason() -> None:
    """Requirement 3: "first-party code" is not a valid reason -- it is not in the closed set."""
    with pytest.raises(ValueError, match="not a valid ExclusionReason"):
        _construct_with_first_party_reason()
