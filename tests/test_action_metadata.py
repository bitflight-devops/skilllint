from __future__ import annotations

from pathlib import Path

ACTION_FILE = Path(__file__).parents[1] / "action.yml"
LEGACY_FILE = ACTION_FILE.parent / "scripts/action_legacy.sh"


def test_action_reports_tool_python_from_uv_tool_environment() -> None:
    action = LEGACY_FILE.read_text(encoding="utf-8")

    assert "uv tool list --show-python" in action
    assert "command -v skilllint" not in action


def test_action_reports_non_cpython_tool_runtime() -> None:
    action = LEGACY_FILE.read_text(encoding="utf-8")

    assert "s/^CPython /Python /" in action
    assert "[CPython " not in action


def test_empty_platform_description_names_matching_adapters() -> None:
    action = ACTION_FILE.read_text(encoding="utf-8")

    assert "When omitted, validates each selected file with every matching platform adapter." in action


def test_action_normalizes_crlf_before_reading_inspected_count() -> None:
    action = LEGACY_FILE.read_text(encoding="utf-8")

    assert "tr -d '\\r'" in action


def test_action_normalizes_crlf_before_counting_tokens_only_output() -> None:
    action = LEGACY_FILE.read_text(encoding="utf-8")

    assert "grep -cE '^[0-9]+($|[[:blank:]])' <<< \"${NORMALIZED_OUTPUT}\"" in action.replace("<<<", "<<< ").replace(
        "<<<  ", "<<< "
    )


def test_action_findings_accept_rich_variation_selectors() -> None:
    action = LEGACY_FILE.read_text(encoding="utf-8")

    assert "⚠️? (WARN|INFO)" in action
    assert "\u2139\ufe0f? (WARN|INFO)" in action


def test_action_findings_accept_plain_rich_symbols() -> None:
    action = LEGACY_FILE.read_text(encoding="utf-8")

    assert "⚠ (WARN|INFO)" in action
    assert "\u2139 (WARN|INFO)" in action
    assert "|\u2139|i INFO" in action


def test_action_calls_testable_helpers_instead_of_inline_logic() -> None:
    action = ACTION_FILE.read_text()
    assert 'run: bash "${GITHUB_ACTION_PATH}/scripts/action_run.sh"' in action
    assert 'run: bash "${GITHUB_ACTION_PATH}/scripts/action_install.sh"' in action
    assert "run: |" not in action


def test_integration_exercises_source_and_legacy_versions() -> None:
    workflow = (ACTION_FILE.parent / ".github/workflows/action-integration.yml").read_text()
    assert 'version: ["source", "1.19.2"]' in workflow
    assert "version: ${{ matrix.version }}" in workflow


def test_fix_integration_does_not_dirty_source_version() -> None:
    workflow = (ACTION_FILE.parent / ".github/workflows/action-integration.yml").read_text()
    assert 'cp -R tests/fixtures/action "${RUNNER_TEMP}/skilllint-action"' in workflow
    assert "format('{0}/skilllint-action/skills/fixable-skill', runner.temp)" in workflow
