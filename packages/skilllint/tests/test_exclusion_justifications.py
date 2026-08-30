"""Guard against ruff/ty exclusions carrying an unverified provenance claim.

#119 excluded ``.agents/skills/*`` from ruff and ty as "vendored ... and
maintained there", implying an upstream sync this repo could not safely
lint over. That claim was false: no sync script, CI job, or
``.gitmodules`` entry has ever moved those skills out of this repo (see
#135, #143). Because a wrong suppression produces no output, nothing ever
contradicted the sentence -- unlike a wrong rule finding, which a reviewer
eventually notices and fixes.

This test requires every path in ``[tool.ruff].exclude`` and
``[tool.ty.src].exclude`` to have a ``REGISTRY`` entry declaring *why*, and
rejects any reason that asserts a claim outside this repo (vendored,
third-party, generated elsewhere) unless it names a ``sync_artifact`` that
actually exists on disk. "First-party code" is not a reason at all --
``ExclusionReason`` has no such member, so a registry entry claiming it
fails to construct.

Blind spots (not covered by this guard):
  * A ``sync_artifact`` that exists but is stale, unrelated, or no longer
    performs a sync -- existence is checked, not function.
  * A reason that is technically true but still a bad idea to suppress for
    (e.g. real vendored code that should be linted anyway).
  * ``find_ty_hook_drift`` compares literal substrings between a glob prefix
    and the prek hook's regex source text; it does not parse either as a
    formal pattern language, so a mismatch expressed through different-but
    equivalent syntax (e.g. a character class instead of a literal dot)
    would slip past it.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Self

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).parent.parent.parent.parent
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
PRE_COMMIT_CONFIG_PATH = REPO_ROOT / ".pre-commit-config.yaml"


class ExclusionReason(StrEnum):
    """Closed set of reasons a path may be excluded from ruff/ty.

    ``DELIBERATELY_BROKEN_FIXTURE`` is self-evident from the path itself
    (a fixtures directory of intentionally-invalid examples) and needs no
    external proof. The other three assert that something outside this
    repo produced or owns the file -- exactly the class of claim #119 got
    away with lying about -- so those require ``sync_artifact``.
    """

    DELIBERATELY_BROKEN_FIXTURE = "deliberately_broken_fixture"
    VENDORED = "vendored"
    THIRD_PARTY = "third_party"
    GENERATED_ELSEWHERE = "generated_elsewhere"


_SELF_EVIDENT_REASONS = frozenset({ExclusionReason.DELIBERATELY_BROKEN_FIXTURE})


class ExclusionJustification(BaseModel):
    """A registry entry justifying one excluded path.

    Not marked strict: this data is authored in-repo as Python literals
    (see ``REGISTRY`` below), not ingested from an external payload, so
    Pydantic's plain (coercing) enum validation is used deliberately -- it
    produces a "must be one of {...}" message that names the closed set,
    which is what a sabotaged ``reason`` needs to surface.
    """

    model_config = ConfigDict(frozen=True)

    reason: ExclusionReason
    sync_artifact: str | None = None

    @model_validator(mode="after")
    def _external_provenance_requires_an_artifact(self) -> Self:
        if self.reason not in _SELF_EVIDENT_REASONS and self.sync_artifact is None:
            msg = f"reason {self.reason!r} asserts external provenance; sync_artifact is required"
            raise ValueError(msg)
        return self


# The only exclusion this repo can currently justify. `.agents/skills/*` is
# deliberately absent: #119's "vendored" claim named no sync_artifact and
# none exists anywhere in this repo (see module docstring), so no valid
# entry can be constructed for it. That absence is the assertion.
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


def find_ty_hook_drift(
    exclusions: list[str], registry: Mapping[str, ExclusionJustification], hook_exclude_regex: str
) -> list[str]:
    """Return one message per provenance-requiring exclusion missing from the prek ty hook.

    ``pass_filenames: true`` on the local ``ty`` hook bypasses
    ``[tool.ty.src]`` entirely, so its ``exclude:`` regex has to repeat the
    same paths by hand. Self-evident (fixture) exclusions are skipped: the
    hook only ever sees ``*.py`` files (``types: [python]``), and the
    fixtures directory this repo currently excludes holds none, so it
    cannot drift in a way that changes hook behavior.
    """
    violations = []
    for path in exclusions:
        entry = registry.get(path)
        if entry is None or entry.reason in _SELF_EVIDENT_REASONS:
            continue
        prefix = path.removesuffix("*")
        if prefix not in hook_exclude_regex:
            violations.append(f"{path}: prek ty hook exclude regex {hook_exclude_regex!r} does not mention {prefix!r}")
    return violations


def _load_pyproject_exclusions() -> tuple[list[str], list[str]]:
    """Read ``[tool.ruff].exclude`` and ``[tool.ty.src].exclude`` from the real pyproject.toml."""
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    return data["tool"]["ruff"]["exclude"], data["tool"]["ty"]["src"]["exclude"]


def _load_ty_hook_exclude_regex() -> str:
    """Read the local ``ty`` hook's ``exclude:`` regex from the real pre-commit config."""
    config = YAML(typ="safe").load(PRE_COMMIT_CONFIG_PATH.read_text(encoding="utf-8"))
    for repo in config["repos"]:
        if repo.get("repo") != "local":
            continue
        for hook in repo["hooks"]:
            if hook["id"] == "ty":
                return hook["exclude"]
    raise AssertionError("no 'ty' hook found in .pre-commit-config.yaml")


# --- Guard, run against the real repo config -------------------------------
#
# Both are expected to fail (xfail, strict) until #154 lands: it deletes the
# still-live `.agents/skills/*` exclusion this guard has no registry entry
# for. strict=True turns an unexpected pass into a hard failure, so the
# xfail marker itself forces its own removal on the rebase after #154 merges
# rather than silently going stale.
_PENDING_154 = "pending #154 removing the unjustified .agents/skills/* exclusion (see module docstring)"


@pytest.mark.xfail(reason=_PENDING_154, strict=True)
def test_ruff_exclusions_are_justified() -> None:
    """Every path in [tool.ruff].exclude must have a REGISTRY entry with a real reason."""
    ruff_exclude, _ = _load_pyproject_exclusions()
    violations = find_unjustified_exclusions(ruff_exclude, REGISTRY, REPO_ROOT)
    assert not violations, violations


@pytest.mark.xfail(reason=_PENDING_154, strict=True)
def test_ty_exclusions_are_justified() -> None:
    """Every path in [tool.ty.src].exclude must have a REGISTRY entry with a real reason."""
    _, ty_exclude = _load_pyproject_exclusions()
    violations = find_unjustified_exclusions(ty_exclude, REGISTRY, REPO_ROOT)
    assert not violations, violations


def test_ty_hook_regex_does_not_drift_from_pyproject() -> None:
    """The prek ty hook's exclude regex must cover every provenance-requiring ty exclusion."""
    _, ty_exclude = _load_pyproject_exclusions()
    hook_regex = _load_ty_hook_exclude_regex()
    violations = find_ty_hook_drift(ty_exclude, REGISTRY, hook_regex)
    assert not violations, violations


# --- Historical case: reconstruct #119 exactly ------------------------------


def test_registry_rejects_119s_unsynced_vendored_claim() -> None:
    """#119's exact claim -- 'vendored', no artifact named -- must fail to register at all."""
    with pytest.raises(ValidationError, match="sync_artifact is required"):
        ExclusionJustification(reason=ExclusionReason.VENDORED)


# --- Sabotage cases, one per rule in the task ------------------------------


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


def test_registry_rejects_first_party_as_a_reason() -> None:
    """Requirement 3: "first-party code" is not a valid reason -- it is not in the closed set."""
    with pytest.raises(ValidationError, match="deliberately_broken_fixture"):
        ExclusionJustification(reason="first_party")
