"""The Action's structured path preserves rendering and invokes one scan."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from contextlib import redirect_stderr
from pathlib import Path

import pytest

from skilllint import action_runner, plugin_validator

FIXTURES = Path(__file__).parent / "fixtures/claude_code"


@pytest.fixture
def action_env(monkeypatch, tmp_path):
    output = tmp_path / "outputs"
    for key in (
        "CHECK_ONLY",
        "FIX",
        "VERBOSE",
        "NO_COLOR",
        "TOKENS_ONLY",
        "SHOW_PROGRESS",
        "SHOW_SUMMARY",
        "PLATFORM",
        "FILTER",
        "FILTER_TYPE",
        "PATHS",
    ):
        monkeypatch.delenv(f"INPUT_{key}", raising=False)
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("INPUT_PATHS", str(FIXTURES / "valid_skill.md"))
    monkeypatch.setenv("INPUT_PLATFORM", "claude-code")
    monkeypatch.setenv("INPUT_VERBOSE", "true")
    return output


def read_outputs(path):
    return dict(line.split("=", 1) for line in path.read_text().splitlines())


@pytest.mark.parametrize(
    ("no_color", "summary"), [("true", "true"), ("true", "false"), ("false", "true"), ("false", "false")]
)
def test_one_scan_regardless_of_human_display_flags(action_env, monkeypatch, mocker, capsys, no_color, summary):
    monkeypatch.setenv("INPUT_NO_COLOR", no_color)
    monkeypatch.setenv("INPUT_SHOW_SUMMARY", summary)
    scan = mocker.spy(plugin_validator, "collect_validation_results")
    assert action_runner.run() == 0
    assert scan.call_count == 1
    values = read_outputs(action_env)
    assert values["result"] == "passed"
    assert values["exit-code"] == "0"
    assert values["inspected-count"] == "1"
    assert "TC001" in values["findings"]
    assert values["tool-python"].startswith("Python ")
    assert values["tool-version"].startswith("skilllint ")
    log = capsys.readouterr().out
    assert ("Total files: 1" in log) == (summary == "true")
    assert "::notice " in log
    match = re.search(r"::stop-commands::([a-f0-9]+)", log)
    assert match is not None
    token = match.group(1)
    assert log.index(f"::{token}::") < log.index("::notice ")


def test_validation_failure_keeps_outputs_and_annotations(action_env, monkeypatch, capsys):
    monkeypatch.setenv("INPUT_PATHS", str(FIXTURES / "invalid-skill/SKILL.md"))
    assert action_runner.run() == 1
    values = read_outputs(action_env)
    assert values["result"] == "failed"
    assert values["inspected-count"] == "1"
    assert {"FM010", "SK005"} <= set(values["findings"].split())
    assert "::error " in capsys.readouterr().out


@pytest.mark.parametrize("absolute", [False, True])
def test_action_annotations_use_workspace_from_nested_cwd(action_env, monkeypatch, capsys, tmp_path, absolute):
    directory = tmp_path / "plugins/demo"
    directory.mkdir(parents=True)
    path = directory / "SKILL.md"
    path.write_text((FIXTURES / "invalid-skill/SKILL.md").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.chdir(directory)
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("INPUT_PATHS", str(path) if absolute else "SKILL.md")
    assert action_runner.run() == 1
    assert read_outputs(action_env)["inspected-count"] == "1"
    assert "::error file=plugins/demo/SKILL.md," in capsys.readouterr().out


def test_usage_failure_has_empty_counts_and_no_scan(action_env, monkeypatch, mocker):
    monkeypatch.setenv("INPUT_CHECK_ONLY", "true")
    monkeypatch.setenv("INPUT_FIX", "true")
    scan = mocker.spy(plugin_validator, "collect_validation_results")
    assert action_runner.run() == 2
    assert scan.call_count == 0
    values = read_outputs(action_env)
    assert values["result"] == "failed"
    assert values["inspected-count"] == values["findings"] == ""


def test_tokens_only_counts_once_and_has_no_annotations(action_env, monkeypatch, mocker, capsys):
    monkeypatch.setenv("INPUT_TOKENS_ONLY", "true")
    count = mocker.spy(plugin_validator, "_count_body_tokens")
    assert action_runner.run() == 0
    assert count.call_count == 1
    values = read_outputs(action_env)
    assert values["inspected-count"] == "1"
    assert values["findings"] == ""
    assert "::notice " not in capsys.readouterr().out


def test_zero_files_is_structured_zero(action_env, monkeypatch):
    monkeypatch.setenv("INPUT_PATHS", str(FIXTURES))
    monkeypatch.setenv("INPUT_FILTER", "*.does-not-exist")
    assert action_runner.run() == 0
    values = read_outputs(action_env)
    assert values["inspected-count"] == "0"
    assert values["findings"] == ""


def test_fix_retains_all_codes_without_second_scan(action_env, monkeypatch, tmp_path, mocker):
    source = Path(__file__).parents[3] / "tests/fixtures/action/skills/fixable-skill/SKILL.md"
    destination = tmp_path / "skills/fixable-skill/SKILL.md"
    destination.parent.mkdir(parents=True)
    destination.write_text(source.read_text())
    monkeypatch.setenv("INPUT_PATHS", str(destination.parent))
    monkeypatch.setenv("INPUT_PLATFORM", "")
    monkeypatch.setenv("INPUT_FIX", "true")
    monkeypatch.setenv("INPUT_VERBOSE", "false")
    scan = mocker.spy(plugin_validator, "collect_validation_results")
    assert action_runner.run() == 0
    assert scan.call_count == 1
    values = read_outputs(action_env)
    assert values["inspected-count"] == "1"
    assert {"FM004", "FM007", "SK005"} <= set(values["findings"].split())


def test_hostile_human_log_is_suspended_and_output_values_cannot_inject(action_env, monkeypatch, capsys):
    from skilllint.models import AppliedFix, ValidationIssue, ValidationResult
    from skilllint.scan_runtime import CheckRun

    path = Path("bad\n::error::injected.md")
    issue = ValidationIssue(field="field", severity="error", message="bad\n::error::injected", code="FM001")
    result = ValidationResult(passed=False, errors=[issue], warnings=[], info=[])
    run = CheckRun(
        results={path: [("test", result)]}, fixes=[AppliedFix(path, "test", ("ZZ001\nresult=passed",), "fix")]
    )

    def hostile_check(**kwargs):
        print("::error::injected human log")
        kwargs["action_report"](run)
        raise action_runner.typer.Exit(1)

    monkeypatch.setattr(action_runner, "check", hostile_check)
    assert action_runner.run() == 1
    log = capsys.readouterr().out
    match = re.search(r"::stop-commands::([a-f0-9]+)", log)
    assert match is not None
    token = match.group(1)
    assert log.index("::error::injected human log") < log.index(f"::{token}::")
    assert "file=bad%0A%3A%3Aerror%3A%3Ainjected.md" in log
    assert "bad%0A::error::injected" in log
    outputs = action_env.read_text()
    assert "findings<<" in outputs
    delimiter = outputs.split("findings<<", 1)[1].splitlines()[0]
    assert f"\n{delimiter}\n" in outputs
    assert outputs.endswith("result=failed\n")


def test_empty_paths_preserve_check_help_context(action_env, monkeypatch, capsys):
    monkeypatch.setenv("INPUT_PATHS", "")
    assert action_runner.run() == 0
    log = capsys.readouterr().out
    assert "skilllint check" in log
    assert "--tokens-only" in log
    assert read_outputs(action_env)["inspected-count"] == ""


def test_non_cpython_runtime_label_is_preserved(action_env, monkeypatch):
    monkeypatch.setattr(action_runner.platform, "python_implementation", lambda: "PyPy")
    assert action_runner.run() == 0
    assert read_outputs(action_env)["tool-python"].startswith("PyPy ")


def test_invalid_utf8_publishes_failure_outputs_and_suspends_traceback(action_env, monkeypatch, tmp_path):
    path = tmp_path / "broken/SKILL.md"
    path.parent.mkdir()
    path.write_bytes(b"---\nname: broken\n---\n\xff")
    monkeypatch.setenv("INPUT_PATHS", str(path))
    result = subprocess.run(
        [sys.executable, "-m", "skilllint.action_runner"],
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert result.returncode == 1
    values = read_outputs(action_env)
    assert values["result"] == "failed"
    assert values["exit-code"] == "1"
    assert values["inspected-count"] == ""
    assert values["findings"] == ""
    match = re.search(r"::stop-commands::([a-f0-9]+)", result.stdout)
    assert match is not None
    assert result.stdout.index("UnicodeDecodeError") < result.stdout.index(f"::{match.group(1)}::")


def test_input_validation_failure_preserves_outputs_and_command_protection(action_env, monkeypatch, capsys):
    from skilllint.boundary.action_inputs_ingest import ActionInputs

    def invalid_inputs(environment):
        return ActionInputs.model_validate({"INPUT_PATHS": ["\n::error::injected"]})

    monkeypatch.setattr(action_runner, "parse_action_inputs", invalid_inputs)
    with redirect_stderr(sys.stdout):
        assert action_runner.run() == 1
    values = read_outputs(action_env)
    assert values["result"] == "failed"
    assert values["inspected-count"] == values["findings"] == ""
    log = capsys.readouterr().out
    match = re.search(r"::stop-commands::([a-f0-9]+)", log)
    assert match is not None
    assert log.index(match.group(0)) < log.index("ValidationError") < log.index(f"::{match.group(1)}::")
