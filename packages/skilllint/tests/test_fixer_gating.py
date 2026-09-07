"""Tests for the --fix rule-code gate (skilllint#144) and its fail-closed contract.

Covers:
- A fixer must not run against a path whose findings include none of its
  declared trigger codes (FIXER_TRIGGER_CODES), even though every shipping
  fixer happens to self-gate internally today -- see the assertions on
  ``fix()`` call counts, not on file bytes, which is the whole point.
- The fix-only NameFormatValidator (never a reporter) still runs when FM010
  fires, proving the gate is rule-code scoped rather than
  validator-identity scoped.
- FrontmatterValidator's AS001-only "add missing name" repair still fires.
- --fix still runs for findings a .skilllint.json ignore config suppresses
  from the report (ignore = suppress reporting, not fixing).
- NameFormatValidator stays last in fixer invocation order.
- Contract: every can_fix()=True validator has a non-empty trigger set,
  every trigger code is a real registered rule, and every fixable=True
  registry rule is covered by at least one trigger set.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from skilllint import plugin_validator as pv
from skilllint.rule_registry import get_rule, list_rules

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def _write_skill(directory: Path, frontmatter: str, body: str = "\n# Skill\n\nBody.\n") -> Path:
    """Write a SKILL.md with the given frontmatter block and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    skill_file = directory / "SKILL.md"
    skill_file.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")
    return skill_file


class TestFixGating:
    """--fix must gate each fixer on that path's own findings (#144)."""

    def test_fix_does_not_invoke_fixer_when_its_rules_did_not_fire(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """A file whose only finding is SK005 (non-fixable) must invoke no fixer.

        Red before the gate exists: every shipping fixer happens to self-gate
        on its own read of the file today, so an "unchanged bytes" assertion
        would already pass. Spying on fix() and asserting zero calls is the
        only assertion that distinguishes "gated" from "ran and no-opped".
        """
        skill_file = _write_skill(
            tmp_path / "clean-skill",
            "name: clean-skill\n"
            "description: A short description without any keywords for automatic loading here.\n"
            "tools: Read, Write",
        )
        frontmatter_fix = mocker.spy(pv.FrontmatterValidator, "fix")
        name_format_fix = mocker.spy(pv.NameFormatValidator, "fix")
        symlink_fix = mocker.spy(pv.SymlinkTargetValidator, "fix")

        results = pv.validate_single_path(skill_file, check=False, fix=True, verbose=False)

        all_codes = {
            str(issue.code)
            for validator_results in results.values()
            for _, vr in validator_results
            for issue in (*vr.errors, *vr.warnings, *vr.info)
        }
        assert "SK005" in all_codes
        assert frontmatter_fix.call_count == 0
        assert name_format_fix.call_count == 0
        assert symlink_fix.call_count == 0

    def test_fix_invokes_frontmatter_fixer_when_fm007_fires(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """FrontmatterValidator.fix() runs when FM007 fires; NameFormatValidator does not."""
        skill_file = _write_skill(
            tmp_path / "fm007-skill",
            "name: fm007-skill\n"
            "description: Use when testing the FM007 auto-fix gate for this skill.\n"
            "tools:\n  - Read\n  - Write",
        )
        frontmatter_fix = mocker.spy(pv.FrontmatterValidator, "fix")
        name_format_fix = mocker.spy(pv.NameFormatValidator, "fix")

        pv.validate_single_path(skill_file, check=False, fix=True, verbose=False)

        assert frontmatter_fix.call_count == 1
        assert name_format_fix.call_count == 0
        assert "tools: Read, Write" in skill_file.read_text(encoding="utf-8")

    def test_fix_invokes_name_format_fixer_when_fm010_fires(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """NameFormatValidator.fix() runs on FM010 even though it never reports.

        NameFormatValidator is appended by _get_fixers_for_path as a fix-only
        participant (FrontmatterValidator is the sole reporter of FM010). A
        validator-identity-scoped gate ("did this instance report?") would
        disable this fix entirely -- this test kills that design.
        """
        command_file = tmp_path / "commands" / "My_Command.md"
        command_file.parent.mkdir(parents=True)
        command_file.write_text(
            "---\nname: My_Command\ndescription: A short description of what this command does.\n---\n\nBody.\n",
            encoding="utf-8",
        )
        name_format_fix = mocker.spy(pv.NameFormatValidator, "fix")

        pv.validate_single_path(command_file, check=False, fix=True, verbose=False)

        assert name_format_fix.call_count == 1
        assert "name: my-command" in command_file.read_text(encoding="utf-8")

    def test_fix_adds_missing_name_when_only_as001_fires(self, tmp_path: Path) -> None:
        """FrontmatterValidator adds a missing `name` field triggered by AS001 alone."""
        skill_dir = tmp_path / "no-name-skill"
        skill_file = _write_skill(
            skill_dir, "description: Use when testing the AS001 add-missing-name auto-fix gate.\ntools: Read"
        )

        pv.validate_single_path(skill_file, check=False, fix=True, verbose=False)

        assert "name: no-name-skill" in skill_file.read_text(encoding="utf-8")

    def test_fixer_ordering_name_format_last(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """NameFormatValidator must run after FrontmatterValidator, never before.

        Their fixes converge only in this order: FrontmatterValidator's
        fix_skill_name_field() sets `name` from the directory first, so
        NameFormatValidator's normalize-and-compare no-ops on an already
        correct name instead of racing it from a different source of truth.
        """
        call_order: list[str] = []
        original_frontmatter_fix = pv.FrontmatterValidator.fix
        original_name_format_fix = pv.NameFormatValidator.fix

        def frontmatter_fix(self: pv.FrontmatterValidator, path: Path) -> list[str]:
            call_order.append("FrontmatterValidator")
            return original_frontmatter_fix(self, path)

        def name_format_fix(self: pv.NameFormatValidator, path: Path) -> list[str]:
            call_order.append("NameFormatValidator")
            return original_name_format_fix(self, path)

        mocker.patch.object(pv.FrontmatterValidator, "fix", frontmatter_fix)
        mocker.patch.object(pv.NameFormatValidator, "fix", name_format_fix)

        skill_file = _write_skill(
            tmp_path / "my-bad-skill",
            "name: My_Bad_Skill\ndescription: Use when testing fixer ordering convergence here.\ntools: Read",
        )

        pv.validate_single_path(skill_file, check=False, fix=True, verbose=False)

        assert call_order == ["FrontmatterValidator", "NameFormatValidator"]


class TestFixGatingIgnoreSemantics:
    """--fix must still apply to findings a .skilllint.json ignore suppresses."""

    def test_fix_runs_for_ignore_suppressed_findings(self, tmp_path: Path) -> None:
        """FM007 is fixed even when .skilllint.json suppresses it from the report.

        Pins the documented invariant at the --fix call site: "ignore =
        suppress reporting, not fixing". Gating on the post-ignore-filter
        codes would silently disable this fix and regress that invariant.
        """
        skill_dir = tmp_path / "suppressed-skill"
        skill_file = _write_skill(
            skill_dir,
            "name: suppressed-skill\n"
            "description: Use when testing ignore-suppressed fix behavior here.\n"
            "tools:\n  - Read\n  - Write",
        )
        (tmp_path / ".skilllint.json").write_text(json.dumps({"ignore": {"": ["FM007"]}}), encoding="utf-8")

        results = pv.validate_single_path(skill_file, check=False, fix=True, verbose=False)

        all_codes = {
            str(issue.code)
            for validator_results in results.values()
            for _, vr in validator_results
            for issue in (*vr.errors, *vr.warnings, *vr.info)
        }
        assert "FM007" not in all_codes, "FM007 should still be suppressed from the report"
        assert "tools: Read, Write" in skill_file.read_text(encoding="utf-8"), "but the fixer should still have run"


# ---------------------------------------------------------------------------
# Fail-closed contract tests
# ---------------------------------------------------------------------------

# Every validator class reachable from _get_validators_for_path's universe,
# plus NameFormatValidator (fix-only, appended by _get_fixers_for_path).
_ALL_VALIDATOR_CLASSES: list[type] = [
    pv.SymlinkTargetValidator,
    pv.FrontmatterValidator,
    pv.NameFormatValidator,
    pv.HookValidator,
    pv.PluginStructureValidator,
    pv.PluginRegistrationValidator,
    pv.ProgressiveDisclosureValidator,
    pv.InternalLinkValidator,
    pv.NamespaceReferenceValidator,
    pv.DescriptionValidator,
    pv.ComplexityValidator,
    pv.MarkdownTokenCounter,
    pv.AsSeriesValidator,
]


class TestFixerTriggerCodesContract:
    """FIXER_TRIGGER_CODES must fail closed and stay consistent with the rule registry."""

    def test_every_can_fix_validator_has_trigger_codes(self) -> None:
        """Every validator whose can_fix() is True has a non-empty trigger set."""
        for validator_class in _ALL_VALIDATOR_CLASSES:
            validator = validator_class()
            if not validator.can_fix():
                continue
            trigger_codes = pv.get_fixer_trigger_codes(validator)
            assert trigger_codes, f"{validator_class.__name__}.can_fix() is True but has no FIXER_TRIGGER_CODES entry"

    def test_trigger_codes_exist_in_rule_registry(self) -> None:
        """Every code in every trigger set resolves to a registered rule."""
        for validator_name, codes in pv.FIXER_TRIGGER_CODES.items():
            for code in codes:
                assert get_rule(code) is not None, f"{validator_name} declares unknown rule code {code!r}"

    def test_every_fixable_rule_has_a_fixer(self) -> None:
        """Every fixable=True registry rule is covered by at least one trigger set."""
        declared_codes = {code for codes in pv.FIXER_TRIGGER_CODES.values() for code in codes}
        fixable_codes = {rule.id for rule in list_rules() if rule.fixable}
        missing = fixable_codes - declared_codes
        assert not missing, f"fixable=True rules with no fixer trigger entry: {missing}"
