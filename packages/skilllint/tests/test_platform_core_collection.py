"""Platform dispatch collects core work once without changing output routes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from skilllint import plugin_validator as validator
from skilllint.adapters import PlatformAdapter
from skilllint.adapters.claude_code import ClaudeCodeAdapter
from skilllint.adapters.codex import CodexAdapter
from skilllint.adapters.cursor import CursorAdapter
from skilllint.validators import rule_series


def _skill(root: Path, content: str | None = None) -> Path:
    path = root / "skills" / "sample" / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(content or "---\nname: Bad_Name\ndescription: short\n---\n# Sample\n\n[missing](missing.md)\n")
    return path


def _adapters() -> dict[str, PlatformAdapter]:
    return {adapter.id(): adapter for adapter in (ClaudeCodeAdapter(), CodexAdapter(), CursorAdapter())}


@pytest.mark.parametrize("platform", ["claude_code", "codex", "cursor", None])
def test_platform_dispatch_collects_core_and_as_once(
    tmp_path: Path, mocker: MockerFixture, platform: str | None
) -> None:
    """Adapter count affects output projection, not validation execution count."""
    path = _skill(tmp_path)
    shared_as = mocker.spy(validator, "run_as_series")
    core_as = mocker.spy(rule_series, "run_as_series")
    collection = mocker.spy(validator, "_collect_validator_results")

    violations = validator.validate_file(path, _adapters(), platform)

    assert violations
    assert shared_as.call_count + core_as.call_count == 1
    collection.assert_called_once()
    assert [item["code"] for item in violations].count("AS006") == 1


def test_standalone_platform_checks_do_not_execute_discarded_as(tmp_path: Path, mocker: MockerFixture) -> None:
    """The standalone platform seam continues to omit AS from its results."""
    path = _skill(tmp_path)
    core_as = mocker.spy(rule_series, "run_as_series")
    collection = mocker.spy(validator, "_collect_validator_results")

    violations = validator.run_platform_checks(path, CodexAdapter())

    assert "FM010" in {item["code"] for item in violations}
    assert not any(item["code"].startswith("AS") for item in violations)
    core_as.assert_not_called()
    collection.assert_called_once()


def test_default_core_path_keeps_its_as_owner(tmp_path: Path, mocker: MockerFixture) -> None:
    """The ordinary CLI/library core route still includes its AS validator."""
    path = _skill(tmp_path)
    core_as = mocker.spy(rule_series, "run_as_series")
    shared_as = mocker.spy(validator, "run_as_series")
    collection = mocker.spy(validator, "_collect_validator_results")

    results = validator.validate_single_path(path, check=True, fix=False, verbose=False)

    assert "AsSeriesValidator" in dict(results[path])
    core_as.assert_called_once()
    shared_as.assert_not_called()
    collection.assert_called_once()


def test_unclaimed_skill_keeps_legacy_fallback(tmp_path: Path, mocker: MockerFixture) -> None:
    """No matching adapter still means AS plus the existing FM/SK fallback."""
    path = _skill(tmp_path)
    shared_as = mocker.spy(validator, "run_as_series")
    collection = mocker.spy(validator, "_collect_validator_results")

    violations = validator.validate_file(path, {})

    assert {"AS006", "FM010"} == {item["code"] for item in violations}
    shared_as.assert_called_once()
    collection.assert_not_called()


@pytest.mark.parametrize(
    "content",
    [
        "---\nname: Bad_Name\ndescription: short\n---\n# Sample\n\n[missing](missing.md)\n",
        "---\ndescription: [unclosed\n---\nBody\n",
        "---\nname: sample\ndescription: Use this: when testing recovery\n---\nBody\n",
        "---\nname: Bad_Name\ndescription: short\nallowed-tools: mcp__Missing__read\n---\nBody\n",
    ],
)
def test_multi_adapter_output_preserves_order_multiplicity_and_metadata(tmp_path: Path, content: str) -> None:
    """Shared AS appears once, while each adapter retains its routed core copy."""
    path = _skill(tmp_path, content)
    adapters = _adapters()
    explicit = {name: validator.validate_file(path, adapters, name) for name in adapters}
    shared_as = [item for item in explicit["claude_code"] if item["code"].startswith("AS")]
    expected = shared_as + [
        item for result in explicit.values() for item in result if not item["code"].startswith("AS")
    ]

    assert validator.validate_file(path, adapters) == expected
    assert any(item.get("source_location") is not None for item in expected)


def test_multi_adapter_policy_is_applied_once_without_changing_suppression(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    """AS/core severity and ignore decisions survive shared result projection."""
    path = _skill(tmp_path)
    (tmp_path / ".skilllint.json").write_text(
        json.dumps({
            "thresholds": {"AS005": 1, "SK006": 1},
            "severity": {"SK006": "info"},
            "ignore": {"skills": ["AS006", "SK004"]},
        })
    )
    collection = mocker.spy(validator, "_collect_validator_results")

    violations = validator.validate_file(path, _adapters())

    assert capsys.readouterr().err.count("AS005 is not a configurable threshold") == 1
    assert not {"AS006", "SK004"} & {item["code"] for item in violations}
    name_issues = [item for item in violations if item["code"] == "FM010"]
    assert len(name_issues) == 3
    token_issues = [item for item in violations if item["code"] == "SK006"]
    assert len(token_issues) == 3
    assert all(item["severity"] == "info" for item in token_issues)
    assert all(item.get("source_location") is not None for item in name_issues)
    collection.assert_called_once()


def test_platform_results_remain_independent_mutable_dictionaries(tmp_path: Path) -> None:
    """Reusing immutable findings must not alias per-adapter output dictionaries."""
    path = _skill(tmp_path)
    names = [item for item in validator.validate_file(path, _adapters()) if item["code"] == "FM010"]

    assert len(names) == 3
    names[0]["message"] = "changed by caller"
    names[0]["source_location"]["start"]["line"] = 999
    assert names[1]["message"] != "changed by caller"
    assert names[1]["source_location"]["start"]["line"] == 2


def test_standalone_platform_keeps_unknown_skill_folder_unclaimed(tmp_path: Path, mocker: MockerFixture) -> None:
    """Only validate_single_path normalizes an otherwise unknown skill folder."""
    path = _skill(tmp_path).parent
    collection = mocker.spy(validator, "_collect_validator_results")

    assert validator.run_platform_checks(path, CodexAdapter()) == []
    collection.assert_not_called()


def test_standalone_platform_preserves_missing_path_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Supported nonexistent paths retain the public core's usage error."""
    path = tmp_path / "missing.md"

    with pytest.raises(validator.typer.Exit) as error:
        validator.run_platform_checks(path, CodexAdapter())

    assert error.value.exit_code == 2
    assert capsys.readouterr().err == f"Error: Path does not exist: {path}\n"


def test_non_skill_core_collection_is_shared_too(tmp_path: Path, mocker: MockerFixture) -> None:
    """Once-per-file collection is not specific to the AS/SKILL.md case."""
    path = tmp_path / "README.md"
    path.write_text("# Readme\n")
    mocker.patch.object(validator, "matches_file", return_value=True)
    collection = mocker.spy(validator, "_collect_validator_results")
    core_as = mocker.spy(rule_series, "run_as_series")
    shared_as = mocker.spy(validator, "run_as_series")

    violations = validator.validate_file(path, _adapters())
    assert not any(item["code"].startswith("AS") for item in violations)
    collection.assert_called_once()
    core_as.assert_not_called()
    shared_as.assert_not_called()
