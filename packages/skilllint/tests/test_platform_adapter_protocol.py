"""Test adapter structural compatibility and concrete method contracts."""

from __future__ import annotations

import pathlib

import pytest

from skilllint.adapters.protocol import PlatformAdapter


class _FullAdapter:
    """A complete mock adapter implementing all five protocol methods."""

    def id(self) -> str:
        return "mock"

    def path_patterns(self) -> list[str]:
        return ["**/*.mock"]

    def applicable_rules(self) -> set[str]:
        return {"AS", "CC"}

    def constraint_scopes(self) -> set[str]:
        return {"shared"}

    def validate(self, path: pathlib.Path) -> list[dict]:
        return []


class _IncompleteAdapter:
    """A mock adapter missing constraint_scopes and validate methods."""

    def id(self) -> str:
        return "incomplete"

    def path_patterns(self) -> list[str]:
        return []

    def applicable_rules(self) -> set[str]:
        return set()


class TestPlatformAdapterProtocol:
    """Tests for the PlatformAdapter Protocol class."""

    def test_full_adapter_satisfies_protocol(self) -> None:
        """A class implementing all five methods is a PlatformAdapter."""
        adapter = _FullAdapter()
        assert isinstance(adapter, PlatformAdapter)

    def test_incomplete_adapter_does_not_satisfy_protocol(self) -> None:
        """A class missing required methods is not a PlatformAdapter."""
        adapter = _IncompleteAdapter()
        assert not isinstance(adapter, PlatformAdapter)

    def test_real_adapters_satisfy_protocol(self) -> None:
        """Built-in adapters (ClaudeCode, Cursor, Codex) satisfy PlatformAdapter."""
        from skilllint.adapters.claude_code import ClaudeCodeAdapter
        from skilllint.adapters.codex import CodexAdapter
        from skilllint.adapters.cursor import CursorAdapter

        for adapter_cls in (ClaudeCodeAdapter, CursorAdapter, CodexAdapter):
            adapter = adapter_cls()
            assert isinstance(adapter, PlatformAdapter), (
                f"{adapter_cls.__name__} should satisfy PlatformAdapter protocol"
            )

    def test_non_adapter_object_not_protocol(self) -> None:
        """A plain object without the required methods is not a PlatformAdapter."""
        assert not isinstance(object(), PlatformAdapter)
        assert not isinstance("string", PlatformAdapter)
        assert not isinstance(42, PlatformAdapter)


class TestProtocolMethodSignatures:
    """Tests for the concrete method behaviour on real adapters."""

    @pytest.fixture(params=["claude_code", "cursor", "codex"])
    def adapter(self, request: pytest.FixtureRequest) -> PlatformAdapter:
        """Parametrised fixture providing each built-in adapter."""
        if request.param == "claude_code":
            from skilllint.adapters.claude_code import ClaudeCodeAdapter

            return ClaudeCodeAdapter()
        if request.param == "cursor":
            from skilllint.adapters.cursor import CursorAdapter

            return CursorAdapter()
        from skilllint.adapters.codex import CodexAdapter

        return CodexAdapter()

    def test_id_returns_non_empty_string(self, adapter: PlatformAdapter) -> None:
        """id() returns a non-empty string."""
        result = adapter.id()
        assert isinstance(result, str)
        assert result

    def test_path_patterns_returns_list_of_strings(self, adapter: PlatformAdapter) -> None:
        """path_patterns() returns a non-empty list of strings."""
        result = adapter.path_patterns()
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(p, str) for p in result)

    def test_applicable_rules_returns_set_of_strings(self, adapter: PlatformAdapter) -> None:
        """applicable_rules() returns a set of strings."""
        result = adapter.applicable_rules()
        assert isinstance(result, set)
        assert all(isinstance(r, str) for r in result)

    def test_constraint_scopes_returns_set(self, adapter: PlatformAdapter) -> None:
        """constraint_scopes() returns a set."""
        result = adapter.constraint_scopes()
        assert isinstance(result, set)
