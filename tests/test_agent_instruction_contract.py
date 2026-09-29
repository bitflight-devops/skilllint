from __future__ import annotations

from pathlib import Path
import tomllib

ROOT = Path(__file__).parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_claude_orchestration_is_not_universal_repository_policy() -> None:
    agents = _read("AGENTS.md")
    claude = _read("CLAUDE.md")

    assert "@AGENTS.md" in claude
    assert "## Orchestrator delegation discipline" in claude
    assert "Claude operates as an orchestrator" in claude
    assert "## Orchestrator delegation discipline" not in agents
    assert "Claude operates as an orchestrator" not in agents


def test_agents_exposes_primary_change_routing_seams() -> None:
    agents = _read("AGENTS.md")
    expected = {
        "packages/skilllint/plugin_validator.py",
        "packages/skilllint/models.py",
        "packages/skilllint/scan_runtime.py",
        "packages/skilllint/rules/",
        "packages/skilllint/rule_registry.py",
        "packages/skilllint/adapters/",
        "packages/skilllint/boundary/",
        "packages/skilllint/schemas/",
        "packages/skilllint/reporting.py",
        "scripts/",
        "packages/skilllint/tests/",
        "tests/",
    }

    assert "## Repository change map" in agents
    assert all(value in agents for value in expected)


def test_documentation_ownership_matches_instruction_boundary() -> None:
    ownership = tomllib.loads(_read("docs/documentation-ownership.toml"))["owners"]

    assert ownership["AGENTS.md"] == "Universal contributor/agent repository contract and change routing"
    assert ownership["CLAUDE.md"] == "Claude-specific orchestration additions"


def test_cursor_uses_agents_as_repository_authority() -> None:
    cursor = _read(".cursor/rules/typing-and-design-standards.mdc")

    assert "test layout per `AGENTS.md`" in cursor
    assert "source (`AGENTS.md`)" in cursor
    assert "test layout per `CLAUDE.md`" not in cursor
    assert "source (`CLAUDE.md`)" not in cursor
