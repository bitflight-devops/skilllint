from __future__ import annotations

from pathlib import Path

ACTION_FILE = Path(__file__).parents[1] / "action.yml"


def test_action_reports_tool_python_from_uv_tool_environment() -> None:
    action = ACTION_FILE.read_text(encoding="utf-8")

    assert "uv tool list --show-python" in action
    assert "command -v skilllint" not in action


def test_empty_platform_description_names_matching_adapters() -> None:
    action = ACTION_FILE.read_text(encoding="utf-8")

    assert "When omitted, validates each selected file with every matching platform adapter." in action


def test_action_normalizes_crlf_before_reading_inspected_count() -> None:
    action = ACTION_FILE.read_text(encoding="utf-8")

    assert "tr -d '\\r'" in action


def test_action_normalizes_crlf_before_counting_tokens_only_output() -> None:
    action = ACTION_FILE.read_text(encoding="utf-8")

    assert "grep -cE '^[0-9]+($|[[:blank:]])' <<< \"${NORMALIZED_OUTPUT}\"" in action
