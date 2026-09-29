"""Contract tests for explicit --platform routing and discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from skilllint.adapters import ALL_RULE_SERIES, PlatformAdapter, PluginLayout
from skilllint.adapters.claude_code import ClaudeCodeAdapter
from skilllint.adapters.codex import CodexAdapter
from skilllint.adapters.cursor import CursorAdapter
from skilllint.plugin_validator import validate_file, violations_to_result
from skilllint.scan_runtime import _resolve_filter_and_expand_paths


def _write_invalid_skill(root: Path) -> Path:
    skill = root / "skills" / "routing-contract" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\n"
        "name: Bad_Name\n"
        "description: short\n"
        "---\n"
        "# Routing contract\n\n"
        "[missing](missing.md)\n"
    )
    return skill


@pytest.mark.parametrize("adapter", [CodexAdapter(), CursorAdapter()])
def test_explicit_shared_skill_findings_are_declared_by_adapter(
    tmp_path: Path, adapter: PlatformAdapter
) -> None:
    """Representative shared core findings flow only through declared series."""
    skill = _write_invalid_skill(tmp_path)

    violations = validate_file(skill, {adapter.id(): adapter}, platform_override=adapter.id())
    codes = {str(violation["code"]) for violation in violations}

    assert {"FM010", "SK004", "LK001"} <= codes
    declared = adapter.applicable_rules()
    assert all(ALL_RULE_SERIES in declared or code[:2] in declared for code in codes)


def test_claude_runtime_consumes_its_declaration_instead_of_type_branching(tmp_path: Path) -> None:
    """Changing Claude's declaration changes actual output from the same pipeline."""

    class AsOnlyClaude(ClaudeCodeAdapter):
        def applicable_rules(self) -> set[str]:
            return {"AS"}

    skill = tmp_path / "skills" / "routing-contract" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\n"
        "description: short\n"
        "---\n"
        "# Routing contract\n\n"
        "[missing](missing.md)\n"
    )
    adapter = AsOnlyClaude()

    violations = validate_file(skill, {adapter.id(): adapter}, platform_override=adapter.id())
    codes = {str(violation["code"]) for violation in violations}

    assert "AS001" in codes
    assert codes
    assert all(code.startswith("AS") for code in codes)
    assert ClaudeCodeAdapter().applicable_rules() == {ALL_RULE_SERIES}


def test_adapter_native_series_flow_through_explicit_router(tmp_path: Path) -> None:
    """Codex and Cursor native findings survive the same explicit route."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("")
    codex = CodexAdapter()

    codex_codes = {
        str(violation["code"])
        for violation in validate_file(agents, {codex.id(): codex}, platform_override=codex.id())
    }
    assert "CX001" in codex_codes

    cursor_rule = tmp_path / "invalid.mdc"
    cursor_rule.write_text("---\ntype: rule\n---\n# Invalid\n")
    cursor = CursorAdapter()
    cursor_codes = {
        str(violation["code"])
        for violation in validate_file(cursor_rule, {cursor.id(): cursor}, platform_override=cursor.id())
    }
    assert "CU002" in cursor_codes


def test_third_party_adapter_uses_same_route_and_preserves_diagnostic_identity(tmp_path: Path) -> None:
    """Unknown extension rules are routed by series and keep field/line identity."""

    class ThirdPartyAdapter:
        def id(self) -> str:
            return "third_party"

        def path_patterns(self) -> list[str]:
            return ["**/*.third"]

        def applicable_rules(self) -> set[str]:
            return {"TP"}

        def constraint_scopes(self) -> set[str]:
            return {"shared"}

        def validate(self, path: Path) -> list[dict]:
            return [
                {
                    "code": "TP001",
                    "severity": "error",
                    "message": "Third-party finding",
                    "field": "frontmatter.mode",
                    "line": 7,
                    "suggestion": "Use a supported mode",
                    "docs_url": "https://example.invalid/tp001",
                },
                {
                    "code": "ZZ001",
                    "severity": "error",
                    "message": "Undeclared series must not escape",
                },
            ]

    target = tmp_path / "rule.third"
    target.write_text("third party\n")
    adapter = ThirdPartyAdapter()

    violations = validate_file(target, {adapter.id(): adapter}, platform_override=adapter.id())
    assert [violation["code"] for violation in violations] == ["TP001"]

    result = violations_to_result(violations)
    issue = result.errors[0]
    assert issue.field == "frontmatter.mode"
    assert issue.line == 7
    assert issue.suggestion == "Use a supported mode"
    assert issue.docs_url == "https://example.invalid/tp001"


def test_rule_platform_metadata_narrows_adapter_series_declaration(tmp_path: Path) -> None:
    """A series declaration cannot opt another platform's registered rule back in."""

    class CursorClaimingCodexRule:
        def id(self) -> str:
            return "cursor"

        def path_patterns(self) -> list[str]:
            return ["**/*.claim"]

        def applicable_rules(self) -> set[str]:
            return {"CX"}

        def constraint_scopes(self) -> set[str]:
            return {"shared"}

        def validate(self, path: Path) -> list[dict]:
            return [{"code": "CX001", "severity": "error", "message": "Wrong platform"}]

    target = tmp_path / "rule.claim"
    target.write_text("")
    adapter = CursorClaimingCodexRule()

    assert validate_file(target, {adapter.id(): adapter}, platform_override=adapter.id()) == []


def test_plugin_root_ownership_prevents_cross_platform_claims(tmp_path: Path) -> None:
    """Broad skill globs cannot claim another platform's marked plugin tree."""
    claude_root = tmp_path / "claude-plugin"
    codex_root = tmp_path / "codex-plugin"
    cursor_root = tmp_path / "cursor-plugin"
    portable_root = tmp_path / "portable-plugin"

    manifests = (
        claude_root / ".claude-plugin" / "plugin.json",
        codex_root / ".codex-plugin" / "plugin.json",
        cursor_root / ".cursor-plugin" / "plugin.json",
        portable_root / "plugin.json",
    )
    for manifest in manifests:
        manifest.parent.mkdir(parents=True)
        manifest.write_text('{"name": "plugin"}')

    skill_dirs: dict[str, Path] = {}
    for name, root in (
        ("claude", claude_root),
        ("codex", codex_root),
        ("cursor", cursor_root),
        ("portable", portable_root),
    ):
        skill_dir = root / "skills" / "sample"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: routing contract\n---\n# Sample\n")
        skill_dirs[name] = skill_dir

    claude = ClaudeCodeAdapter()
    codex = CodexAdapter()
    cursor = CursorAdapter()
    adapters: tuple[PlatformAdapter, ...] = (claude, codex, cursor)

    claude_paths, _ = _resolve_filter_and_expand_paths(
        [tmp_path], None, None, platform_adapter=claude, platform_adapters=adapters
    )
    codex_paths, _ = _resolve_filter_and_expand_paths(
        [tmp_path], None, None, platform_adapter=codex, platform_adapters=adapters
    )
    cursor_paths, _ = _resolve_filter_and_expand_paths(
        [tmp_path], None, None, platform_adapter=cursor, platform_adapters=adapters
    )

    assert skill_dirs["claude"] in claude_paths
    assert skill_dirs["codex"] not in claude_paths
    assert skill_dirs["cursor"] not in claude_paths
    assert skill_dirs["portable"] not in claude_paths

    assert skill_dirs["codex"] in codex_paths
    assert codex_root / ".codex-plugin" / "plugin.json" in codex_paths
    assert skill_dirs["portable"] in codex_paths
    assert portable_root / "plugin.json" in codex_paths
    assert skill_dirs["claude"] not in codex_paths
    assert skill_dirs["cursor"] not in codex_paths

    assert skill_dirs["cursor"] in cursor_paths
    assert skill_dirs["portable"] in cursor_paths
    assert skill_dirs["claude"] not in cursor_paths
    assert skill_dirs["codex"] not in cursor_paths


def test_third_party_plugin_root_contract_blocks_other_broad_adapter(tmp_path: Path) -> None:
    """Plugin ownership is extension-driven rather than a built-in ID table."""

    class OwnerAdapter:
        def id(self) -> str:
            return "vendor"

        def path_patterns(self) -> list[str]:
            return ["**/skills/*/SKILL.md"]

        def applicable_rules(self) -> set[str]:
            return set()

        def constraint_scopes(self) -> set[str]:
            return {"shared"}

        def validate(self, path: Path) -> list[dict]:
            return []

        def plugin_layouts(self) -> tuple[PluginLayout, ...]:
            return (PluginLayout(".vendor-plugin/plugin.json"),)

    class BroadAdapter:
        def id(self) -> str:
            return "broad"

        def path_patterns(self) -> list[str]:
            return ["**/skills/*/SKILL.md"]

        def applicable_rules(self) -> set[str]:
            return set()

        def constraint_scopes(self) -> set[str]:
            return {"shared"}

        def validate(self, path: Path) -> list[dict]:
            return []

    plugin_root = tmp_path / "plugin"
    manifest = plugin_root / ".vendor-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"name": "plugin"}')
    skill = plugin_root / "skills" / "sample" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\ndescription: sample\n---\n# Sample\n")

    owner = OwnerAdapter()
    broad = BroadAdapter()
    adapters: tuple[PlatformAdapter, ...] = (owner, broad)

    owner_paths, _ = _resolve_filter_and_expand_paths(
        [tmp_path], None, None, platform_adapter=owner, platform_adapters=adapters
    )
    broad_paths, _ = _resolve_filter_and_expand_paths(
        [tmp_path], None, None, platform_adapter=broad, platform_adapters=adapters
    )

    assert skill in owner_paths
    assert broad_paths == []

    direct_paths, _ = _resolve_filter_and_expand_paths(
        [skill], None, None, platform_adapter=owner, platform_adapters=adapters
    )
    assert direct_paths == [skill]
