from __future__ import annotations

from pathlib import Path

ACTION_FILE = Path(__file__).parents[1] / "action.yml"


def test_action_reports_tool_python_from_uv_tool_environment() -> None:
    action = ACTION_FILE.read_text(encoding="utf-8")

    assert "uv tool list --show-python" in action
    assert "command -v skilllint" not in action


def test_action_reports_non_cpython_tool_runtime() -> None:
    action = ACTION_FILE.read_text(encoding="utf-8")

    assert "s/^CPython /Python /" in action
    assert "[CPython " not in action


def test_empty_platform_description_names_matching_adapters() -> None:
    action = ACTION_FILE.read_text(encoding="utf-8")

    assert "When omitted, validates each selected file with every matching platform adapter." in action


def test_action_normalizes_crlf_before_reading_inspected_count() -> None:
    action = ACTION_FILE.read_text(encoding="utf-8")

    assert "tr -d '\\r'" in action


def test_action_normalizes_crlf_before_counting_tokens_only_output() -> None:
    action = ACTION_FILE.read_text(encoding="utf-8")

    assert "grep -cE '^[0-9]+($|[[:blank:]])' <<< \"${NORMALIZED_OUTPUT}\"" in action


def test_action_findings_accept_rich_variation_selectors() -> None:
    action = ACTION_FILE.read_text(encoding="utf-8")

    assert "⚠️? (WARN|INFO)" in action
    assert "\u2139\ufe0f? (WARN|INFO)" in action


def test_action_findings_accept_plain_rich_symbols() -> None:
    action = ACTION_FILE.read_text(encoding="utf-8")

    assert "⚠ (WARN|INFO)" in action
    assert "\u2139 (WARN|INFO)" in action
    assert "|\u2139|i INFO" in action
