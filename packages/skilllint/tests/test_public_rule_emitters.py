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


def test_stub_inventory_is_exact_and_excludes_removed_codes() -> None:
    assert _stub_codes() == set(_PUBLIC_EMITTER_INVENTORY)
    assert not _REMOVED_STUB_CODES & _PUBLIC_EMITTER_INVENTORY.keys()


def test_stub_inventory_rejects_an_unmapped_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(RULE_REGISTRY, "ZZ001", RULE_REGISTRY["FM002"])
    assert _stub_codes() - _PUBLIC_EMITTER_INVENTORY.keys() == {"ZZ001"}


@pytest.mark.parametrize(
    ("rule_id", "variant_name"),
    [
        ("FM002", "unclosed-brace"),
        ("FM003", "no-frontmatter"),
        ("FM005", "wrong-type-hooks"),
        ("FM006", "invalid-context-value"),
        ("SK008", "invalid-directory-name"),
    ],
)
def test_fixture_inventory_rows_emit_through_the_cli(cli_runner: CliRunner, rule_id: str, variant_name: str) -> None:
    fixture = _fixture_case(rule_id, variant_name)
    result = cli_runner.invoke(plugin_validator_module.app, ["check", "--no-color", str(fixture.path)])

    assert result.exit_code == 1, result.stdout
    assert f"[{rule_id}]" in result.stdout


def test_fm009_emits_warning_before_fix_and_info_after_fix(tmp_path: Path) -> None:
    skill_dir = tmp_path / "colon-skill"
    skill_dir.mkdir()
    skill = skill_dir / "SKILL.md"
    skill.write_text("---\nname: colon-skill\ndescription: Use this: when testing colons\n---\n\nBody.\n")

    check_only = [issue for issue in _public_issues(skill_dir) if issue.code == "FM009"]
    post_fix = [issue for issue in _public_issues(skill_dir, fix=True) if issue.code == "FM009"]

    assert [issue.severity for issue in check_only] == ["warning"]
    assert [issue.severity for issue in post_fix] == ["info"]


@pytest.mark.parametrize(
    ("rule_id", "threshold", "severity"),
    [("SK006", TOKEN_WARNING_THRESHOLD, "warning"), ("SK007", TOKEN_ERROR_THRESHOLD, "error")],
)
def test_token_stub_branch_severity(tmp_path: Path, rule_id: str, threshold: int, severity: str) -> None:
    skill_dir = tmp_path / rule_id.lower()
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {rule_id.lower()}\ndescription: Use this skill when testing token threshold branches.\n---\n\n"
        + ("word " * (threshold + 100))
    )

    issues = [issue for issue in _public_issues(skill_dir) if issue.code == rule_id]

    assert [issue.severity for issue in issues] == [severity]
