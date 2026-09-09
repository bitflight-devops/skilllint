from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

import skilllint.plugin_validator as plugin_validator_module
from skilllint.fixture_loader import FixtureCase, discover_fixtures
from skilllint.plugin_validator import ValidationIssue, ValidationResult, validate_single_path
from skilllint.rule_registry import RULE_REGISTRY
from skilllint.token_counter import TOKEN_ERROR_THRESHOLD, TOKEN_WARNING_THRESHOLD

if TYPE_CHECKING:
    from typer.testing import CliRunner


_STUB_MARKER: Final = "Always an empty list."
_PUBLIC_EMITTER_INVENTORY: Final[dict[str, str]] = {
    "FM002": "fixture:unclosed-brace",
    "FM003": "fixture:no-frontmatter",
    "FM005": "fixture:wrong-type-hooks",
    "FM006": "fixture:invalid-context-value",
    "FM009": "branch:check-only-warning-and-post-fix-info",
    "SK006": "branch:warning-token-band",
    "SK007": "branch:error-token-band",
    "SK008": "fixture:invalid-directory-name",
}
_REMOVED_STUB_CODES: Final[frozenset[str]] = frozenset({"PR003", "PR004", "SK009"})


def _stub_codes() -> set[str]:
    return {code for code, entry in RULE_REGISTRY.items() if _STUB_MARKER in entry.docstring}


def _fixture_case(rule_id: str, variant_name: str) -> FixtureCase:
    cases = [case for case in discover_fixtures(rule_id) if case.kind == "failing" and case.name == variant_name]
    assert len(cases) == 1, f"{rule_id}: expected one failing public fixture named {variant_name!r}, got {cases!r}"
    return cases[0]


def _public_issues(path: Path, *, fix: bool = False) -> list[ValidationIssue]:
    results = validate_single_path(path, check=True, fix=fix, verbose=False)
    return [
        issue
        for validator_pairs in results.values()
        for _validator_name, result in validator_pairs
        if isinstance(result, ValidationResult)
        for issue in result.errors + result.warnings + result.info
    ]


def _assert_public_emitter(rule_id: str, emitter: str, cli_runner: CliRunner, tmp_path: Path) -> None:
    if emitter.startswith("fixture:"):
        fixture = _fixture_case(rule_id, emitter.removeprefix("fixture:"))
        result = cli_runner.invoke(plugin_validator_module.app, ["check", "--no-color", str(fixture.path)])

        assert result.exit_code == 1, result.stdout
        assert f"[{rule_id}]" in result.stdout
        return

    if emitter == "branch:check-only-warning-and-post-fix-info":
        skill_dir = tmp_path / "colon-skill"
        skill_dir.mkdir()
        skill = skill_dir / "SKILL.md"
        skill.write_text("---\nname: colon-skill\ndescription: Use this: when testing colons\n---\n\nBody.\n")

        check_only = [issue for issue in _public_issues(skill_dir) if issue.code == rule_id]
        post_fix = [issue for issue in _public_issues(skill_dir, fix=True) if issue.code == rule_id]

        assert [issue.severity for issue in check_only] == ["warning"]
        assert [issue.severity for issue in post_fix] == ["info"]
        return

    token_branches = {
        "branch:warning-token-band": (TOKEN_WARNING_THRESHOLD, "warning"),
        "branch:error-token-band": (TOKEN_ERROR_THRESHOLD, "error"),
    }
    if emitter in token_branches:
        threshold, severity = token_branches[emitter]
        skill_dir = tmp_path / rule_id.lower()
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {rule_id.lower()}\ndescription: Use this skill when testing token threshold branches.\n---\n\n"
            + ("word " * (threshold + 100))
        )

        issues = [issue for issue in _public_issues(skill_dir) if issue.code == rule_id]

        assert [issue.severity for issue in issues] == [severity]
        return

    pytest.fail(f"{rule_id}: unsupported public emitter {emitter!r}")


def _assert_all_public_emitters(cli_runner: CliRunner, tmp_path: Path) -> None:
    for rule_id, emitter in _PUBLIC_EMITTER_INVENTORY.items():
        _assert_public_emitter(rule_id, emitter, cli_runner, tmp_path)


def test_stub_inventory_is_exact_and_excludes_removed_codes() -> None:
    assert _stub_codes() == set(_PUBLIC_EMITTER_INVENTORY)
    assert not _REMOVED_STUB_CODES & _PUBLIC_EMITTER_INVENTORY.keys()


def test_stub_inventory_rejects_an_unmapped_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(RULE_REGISTRY, "ZZ001", RULE_REGISTRY["FM002"])
    assert _stub_codes() - _PUBLIC_EMITTER_INVENTORY.keys() == {"ZZ001"}


def test_registration_only_fake_cannot_claim_a_mapped_public_emitter(
    monkeypatch: pytest.MonkeyPatch, cli_runner: CliRunner, tmp_path: Path
) -> None:
    monkeypatch.setitem(RULE_REGISTRY, "ZZ001", RULE_REGISTRY["FM002"])
    monkeypatch.setitem(_PUBLIC_EMITTER_INVENTORY, "ZZ001", "fixture:unclosed-brace")

    assert _stub_codes() == set(_PUBLIC_EMITTER_INVENTORY)
    with pytest.raises(AssertionError, match="ZZ001"):
        _assert_all_public_emitters(cli_runner, tmp_path)


def test_each_inventory_row_executes_its_public_emitter(cli_runner: CliRunner, tmp_path: Path) -> None:
    _assert_all_public_emitters(cli_runner, tmp_path)
