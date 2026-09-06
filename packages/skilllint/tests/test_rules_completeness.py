"""Completeness tests for the skilllint rule registry.

These tests assert that all expected rule series are registered and that the CLI
output is consistent with the registry.  They gate the P038 migration: all 5 tests
must pass once T14 (final wire-up) is complete.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import pytest

import skilllint.plugin_validator as plugin_validator_module
import skilllint.rules

if TYPE_CHECKING:
    from typer.testing import CliRunner

# MIN_REGISTERED_SERIES and EXPECTED_SERIES are re-exported from skilllint.rules._constants.
# Sources: P038 architect spec section 8 (14 series) and issue #132 (AG, the
# fifteenth series).
from skilllint.plugin_validator import FrontmatterValidator, HookValidator, NameFormatValidator, SymlinkTargetValidator
from skilllint.rule_registry import RULE_REGISTRY
from skilllint.rules import EXPECTED_SERIES, MIN_REGISTERED_SERIES

# Local alias preserving the underscore-prefixed naming convention used in tests.
_EXPECTED_SERIES: frozenset[str] = EXPECTED_SERIES

# The _isolate_rule_registry autouse fixture now lives in conftest.py so that
# every test under packages/skilllint/tests/ snapshots and restores the rule
# registry (preventing test-only rules like TA001/TN001 from leaking across
# test modules). See conftest.py and commit d81d23f for history.


def _registered_prefixes() -> set[str]:
    """Return the set of two-letter series prefixes currently in RULE_REGISTRY."""
    from skilllint.rule_registry import RULE_REGISTRY

    return {rule_id[:2] for rule_id in RULE_REGISTRY}


def _cli_series_from_output(output: str) -> set[str]:
    """Parse series prefixes from ``skilllint rules`` table output.

    The table rows have the form ``| SK001 | ...``.  Extract the two-letter prefix
    from each rule ID column.

    Args:
        output: Captured stdout from ``skilllint rules``.

    Returns:
        Set of two-letter series prefix strings found in the output.
    """
    # Match rule IDs like AS001, FM002, SK003 in the table
    matches = re.findall(r"\b([A-Z]{2})\d{3}\b", output)
    return set(matches)


def _readme_series_from_table() -> set[str]:
    """Parse series prefixes from the README 'What gets validated' table.

    Reads the project README and extracts two-letter codes from table rows
    in the 'What gets validated' section.

    Returns:
        Set of two-letter series prefix strings found in the README table.
    """
    readme = Path(__file__).parents[3] / "README.md"
    if not readme.exists():
        pytest.skip(f"README.md not found at {readme}")

    content = readme.read_text(encoding="utf-8")

    # Find the "What gets validated" section
    section_match = re.search(r"## What gets validated\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if section_match is None:
        pytest.skip("README.md does not contain a 'What gets validated' section")

    section = section_match.group(1)

    # Match rule codes like FM001-FM010, SK001-SK009, PA001 at the start of table cells
    matches = re.findall(r"\|\s*([A-Z]{2})\d{3}", section)
    return set(matches)


class TestRegisteredSeriesCount:
    """Assert the registered series prefix count meets MIN_REGISTERED_SERIES."""

    def test_registered_series_count_meets_minimum(self) -> None:
        """Registry must contain at least MIN_REGISTERED_SERIES distinct series.

        This test fails pre-migration (only AS, FM, PA registered = 3 series)
        and passes once all 15 expected series are populated.
        """
        prefixes = _registered_prefixes()
        count = len(prefixes)
        assert count >= MIN_REGISTERED_SERIES, (
            f"RULE_REGISTRY has {count} distinct series prefixes but requires at least "
            f"{MIN_REGISTERED_SERIES}. Missing series: "
            f"{sorted(_EXPECTED_SERIES - prefixes)}. "
            f"Registered so far: {sorted(prefixes)}."
        )


class TestExpectedSeriesSubset:
    """Assert expected series set is a subset of registered prefixes."""

    def test_expected_series_subset_of_registered(self) -> None:
        """All 15 expected series prefixes must be present in RULE_REGISTRY.

        Expected: {AG, AS, FM, PA, SK, LK, PD, PL, HK, NR, SL, TC, PR, CU, CX}.
        This test fails whenever an expected series has not been registered.
        """
        prefixes = _registered_prefixes()
        missing = _EXPECTED_SERIES - prefixes
        assert not missing, (
            f"Expected series prefixes not yet registered: {sorted(missing)}. "
            f"Registered prefixes: {sorted(prefixes)}. "
            f"Complete T3-T13 to populate all series."
        )


class TestCliOutputMatchesRegistry:
    """Assert 'skilllint rules' CLI output lists the same series as RULE_REGISTRY."""

    def test_cli_rules_output_matches_registry(self, cli_runner: CliRunner) -> None:
        """CLI 'skilllint rules' output must list exactly the series in RULE_REGISTRY.

        Verifies that every series visible in the registry is surfaced by the CLI,
        and that no extra series appear in CLI output that are not in the registry.

        This test fails when RULE_REGISTRY and CLI discovery drift or the
        combined set contains fewer than 15 series.
        """
        import skilllint.plugin_validator as plugin_validator

        result = cli_runner.invoke(plugin_validator.app, ["rules"])
        assert result.exit_code == 0, f"'skilllint rules' exited with code {result.exit_code}. Output: {result.stdout}"

        cli_series = _cli_series_from_output(result.stdout)
        registry_series = _registered_prefixes()

        # Every series in the registry must appear in CLI output
        missing_from_cli = registry_series - cli_series
        assert not missing_from_cli, (
            f"Series in RULE_REGISTRY but not in 'skilllint rules' output: "
            f"{sorted(missing_from_cli)}. CLI output series: {sorted(cli_series)}."
        )

        # Every series in CLI output must be in the registry
        extra_in_cli = cli_series - registry_series
        assert not extra_in_cli, (
            f"Series in 'skilllint rules' output but not in RULE_REGISTRY: "
            f"{sorted(extra_in_cli)}. Registry series: {sorted(registry_series)}."
        )

        # Final gate: the combined set must reach MIN_REGISTERED_SERIES
        assert len(cli_series) >= MIN_REGISTERED_SERIES, (
            f"'skilllint rules' shows {len(cli_series)} series; "
            f"requires at least {MIN_REGISTERED_SERIES}. "
            f"Shown: {sorted(cli_series)}."
        )


class TestReadmeTableMatchesRegistry:
    """Assert README 'What gets validated' table matches registered series."""

    def test_readme_table_matches_registered_series(self) -> None:
        """README 'What gets validated' table must list every registered series.

        Each series prefix present in RULE_REGISTRY must appear in the README
        table so documentation stays in sync with code.

        Pre-migration this test passes trivially for the 3 existing series.
        It becomes a meaningful documentation-sync guard when all 15 series
        must be in both the registry and the README.
        """
        registry_series = _registered_prefixes()
        readme_series = _readme_series_from_table()

        missing_from_readme = registry_series - readme_series
        assert not missing_from_readme, (
            f"Series registered in RULE_REGISTRY but missing from README 'What gets validated' "
            f"table: {sorted(missing_from_readme)}. "
            f"README series: {sorted(readme_series)}. "
            f"Update README.md to document all registered series."
        )

    def test_readme_table_completeness_against_expected(self) -> None:
        """README table must eventually list all 15 expected series.

        This test fails until T14 updates the README to include all series.
        It is a documentation completeness gate, not a registry gate.
        """
        readme_series = _readme_series_from_table()
        missing = _EXPECTED_SERIES - readme_series
        assert not missing, (
            f"Expected series not yet in README 'What gets validated' table: "
            f"{sorted(missing)}. "
            f"README currently lists: {sorted(readme_series)}. "
            f"T14 must add documentation rows for these series."
        )


class TestFixableRulesHaveWorkingFixers:
    """Assert every rule marked ``fixable=True`` has a validator whose ``can_fix()`` is True.

    ``fixable`` used to be undeclared metadata that only existed as a hand-written
    "Auto-fix" column in the now-deleted rule-catalog.md, which drifted from
    reality (it said "no" for HK005 even though ``HookValidator.can_fix()`` is
    True and HK005's own docstring says it's auto-fixable). Pinning the exact set
    here, plus checking each one against its real validator, is strictly more
    coverage than the catalog ever enforced -- same pattern as
    test_client_load_behavior.py's "pin the exact classified set" test.

    This is a one-directional check: a validator's ``can_fix()`` covers a group
    of rules, not a 1:1 mapping, so the reverse (every rule a validator's
    ``can_fix()`` implies) is not asserted.
    """

    # Rule ID -> validator classes responsible for auto-fixing it. FM010 has two
    # because NameFormatValidator does the actual repair while FrontmatterValidator
    # remains FM010's sole reporter (see NameFormatValidator's docstring).
    _FIXABLE_VALIDATORS: ClassVar[dict[str, tuple[type, ...]]] = {
        "FM004": (FrontmatterValidator,),
        "FM007": (FrontmatterValidator,),
        "FM009": (FrontmatterValidator,),
        "FM010": (FrontmatterValidator, NameFormatValidator),
        "SL001": (SymlinkTargetValidator,),
        "HK005": (HookValidator,),
    }

    def test_exactly_six_rules_are_fixable(self) -> None:
        """Pin the exact fixable set so a future session cannot silently add one without a validator mapping."""
        fixable_ids = sorted(rule_id for rule_id, entry in RULE_REGISTRY.items() if entry.fixable)
        assert fixable_ids == sorted(self._FIXABLE_VALIDATORS)

    def test_fixable_rules_have_a_validator_that_can_fix(self) -> None:
        """Every fixable=True rule's mapped validator(s) must report can_fix() is True."""
        for rule_id, validator_classes in self._FIXABLE_VALIDATORS.items():
            assert RULE_REGISTRY[rule_id].fixable, f"{rule_id} is in _FIXABLE_VALIDATORS but not marked fixable=True"
            for validator_cls in validator_classes:
                assert validator_cls().can_fix() is True, (
                    f"{rule_id}: {validator_cls.__name__}.can_fix() must be True for a fixable=True rule"
                )


_STUB_MARKER = "Always an empty list."
# `[\w.]*` (not `\w*`) so a dotted attribute path like `FrontmatterValidator.
# _extract_frontmatter` captures whole -- `\w*` alone stops at the first
# `.`, silently truncating the capture to just `FrontmatterValidator` and
# letting the hasattr check below pass on the class existing without ever
# checking the named method exists.
_BACKTICKED_SYMBOL = re.compile(r"`([A-Za-z_][\w.]*)")


def _resolves(symbol: str) -> bool:
    """True if *symbol* -- a plain name or a dotted `Class.method` path -- exists.

    `hasattr` alone only resolves a single attribute hop, so a dotted path
    (e.g. ``FrontmatterValidator._extract_frontmatter``) is walked one
    segment at a time.
    """
    for module in (plugin_validator_module, skilllint.rules):
        obj = module
        for part in symbol.split("."):
            if not hasattr(obj, part):
                break
            obj = getattr(obj, part)
        else:
            return True
    return False


def test_stub_docstrings_name_a_resolvable_emitter() -> None:
    """A registration-only stub must name a real emitter symbol in backticks.

    Finds stubs by their docstring's "Always an empty list." sentence rather
    than a hand-maintained code list, so it self-scopes to whatever the
    registry actually contains today.
    """
    for code, entry in RULE_REGISTRY.items():
        marker_index = entry.docstring.find(_STUB_MARKER)
        if marker_index == -1:
            continue
        tail = entry.docstring[marker_index + len(_STUB_MARKER) :]
        match = _BACKTICKED_SYMBOL.search(tail)
        assert match is not None, f"{code}: stub docstring must name its emitter in backticks"

        symbol = match.group(1)
        assert _resolves(symbol), (
            f"{code}: stub docstring names `{symbol}` as its emitter, "
            f"but that symbol does not exist in plugin_validator or skilllint.rules"
        )
