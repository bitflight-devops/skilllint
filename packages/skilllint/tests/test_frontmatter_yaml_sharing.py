"""Tests for sharing frontmatter YAML parses within one path's validation."""

from __future__ import annotations

import pytest

from skilllint import frontmatter_yaml
from skilllint.frontmatter_yaml import _safe_load_yaml, shared_yaml_parses

TEXT = "name: demo\ntools:\n  - Read\n"


@pytest.fixture
def load_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every text the underlying ruamel loader parses."""
    calls: list[str] = []
    real_load = frontmatter_yaml._yaml_safe.load

    def recording_load(text: str) -> object:
        calls.append(text)
        return real_load(text)

    monkeypatch.setattr(frontmatter_yaml._yaml_safe, "load", recording_load)
    return calls


def test_a_text_is_parsed_once_inside_a_scope(load_calls: list[str]) -> None:
    """Repeated loads of one text inside the scope reach the parser once."""
    with shared_yaml_parses():
        first = _safe_load_yaml(TEXT)
        second = _safe_load_yaml(TEXT)

    assert first == second == {"name": "demo", "tools": ["Read"]}
    assert load_calls == [TEXT]


def test_every_load_parses_outside_a_scope(load_calls: list[str]) -> None:
    """Without a scope nothing is shared, so each load parses."""
    _safe_load_yaml(TEXT)
    _safe_load_yaml(TEXT)

    assert load_calls == [TEXT, TEXT]


def test_a_caller_mutating_its_result_does_not_change_another_callers(load_calls: list[str]) -> None:
    """Each caller receives its own copy, nested values included."""
    with shared_yaml_parses():
        first = _safe_load_yaml(TEXT)
        assert isinstance(first, dict)
        tools = first["tools"]
        assert isinstance(tools, list)
        tools.append("Write")
        first["name"] = "changed"
        second = _safe_load_yaml(TEXT)

    assert second == {"name": "demo", "tools": ["Read"]}
    assert load_calls == [TEXT]


def test_a_new_scope_does_not_reuse_an_earlier_scopes_parses(load_calls: list[str]) -> None:
    """Parses are dropped when their scope ends, so a later scope parses again."""
    with shared_yaml_parses():
        _safe_load_yaml(TEXT)
    with shared_yaml_parses():
        _safe_load_yaml(TEXT)

    assert load_calls == [TEXT, TEXT]
