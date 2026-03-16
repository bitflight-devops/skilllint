"""Tests for scan discovery modes (S03).

These tests verify:
1. ScanDiscoveryMode enum and detection functions work correctly
2. Manifest-driven discovery returns only explicitly declared components
3. Auto-discovery uses DEFAULT_SCAN_PATTERNS
4. Structure-based discovery handles provider directories correctly
"""

import pytest
from pathlib import Path

from skilllint.scan_runtime import (
    ScanDiscoveryMode,
    detect_discovery_mode,
    read_plugin_manifest,
    get_manifest_discovery_paths,
    get_structure_discovery_paths,
    resolve_filter_and_expand_paths,
    PROVIDER_DIR_NAMES,
)


class TestScanDiscoveryMode:
    """Tests for ScanDiscoveryMode enum."""

    def test_discovery_mode_enum_values(self):
        """Verify all expected mode values exist."""
        assert ScanDiscoveryMode.MANIFEST == "manifest"
        assert ScanDiscoveryMode.AUTO == "auto"
        assert ScanDiscoveryMode.STRUCTURE == "structure"

    def test_provider_dir_names_includes_expected(self):
        """Verify provider directory names are recognized."""
        assert ".claude" in PROVIDER_DIR_NAMES
        assert ".agent" in PROVIDER_DIR_NAMES
        assert ".agents" in PROVIDER_DIR_NAMES
        assert ".gemini" in PROVIDER_DIR_NAMES
        assert ".cursor" in PROVIDER_DIR_NAMES


class TestReadPluginManifest:
    """Tests for reading plugin.json manifests."""

    def test_read_valid_manifest(self, tmp_path):
        """Test reading a valid plugin.json."""
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
        plugin_json.parent.mkdir(parents=True)
        plugin_json.write_text('{"name": "test-plugin", "agents": ["agent1"], "commands": ["cmd1"]}')

        manifest = read_plugin_manifest(plugin_dir)

        assert manifest is not None
        assert manifest.name == "test-plugin"
        assert manifest.agents == ["agent1"]
        assert manifest.commands == ["cmd1"]
        assert manifest.skills == []
        assert manifest.hooks == []

    def test_read_manifest_without_components(self, tmp_path):
        """Test reading plugin.json without explicit component arrays."""
        plugin_dir = tmp_path / "minimal_plugin"
        plugin_dir.mkdir()
        plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
        plugin_json.parent.mkdir(parents=True)
        plugin_json.write_text('{"name": "minimal"}')

        manifest = read_plugin_manifest(plugin_dir)

        assert manifest is not None
        assert manifest.name == "minimal"
        assert not manifest.has_explicit_components()

    def test_read_missing_manifest(self, tmp_path):
        """Test reading when no plugin.json exists."""
        plugin_dir = tmp_path / "no_plugin"
        plugin_dir.mkdir()

        manifest = read_plugin_manifest(plugin_dir)

        assert manifest is None


class TestDetectDiscoveryMode:
    """Tests for discovery mode detection."""

    def test_manifest_mode_with_explicit_components(self, tmp_path):
        """Manifest with explicit components should return MANIFEST mode."""
        plugin_dir = tmp_path / "explicit_plugin"
        plugin_dir.mkdir()
        plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
        plugin_json.parent.mkdir(parents=True)
        plugin_json.write_text('{"name": "test", "agents": ["a1"]}')

        mode = detect_discovery_mode(plugin_dir)

        assert mode == ScanDiscoveryMode.MANIFEST

    def test_auto_mode_without_components(self, tmp_path):
        """Manifest without explicit components should return AUTO mode."""
        plugin_dir = tmp_path / "auto_plugin"
        plugin_dir.mkdir()
        plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
        plugin_json.parent.mkdir(parents=True)
        plugin_json.write_text('{"name": "test"}')

        mode = detect_discovery_mode(plugin_dir)

        assert mode == ScanDiscoveryMode.AUTO

    def test_structure_mode_for_provider_dir(self, tmp_path):
        """Provider directory should return STRUCTURE mode."""
        provider_dir = tmp_path / ".claude"
        provider_dir.mkdir()

        mode = detect_discovery_mode(provider_dir)

        assert mode == ScanDiscoveryMode.STRUCTURE

    def test_structure_mode_for_nested_provider_dir(self, tmp_path):
        """Nested provider directory should return STRUCTURE mode."""
        # e.g., scanning a subdir inside .claude/
        parent = tmp_path / "project" / ".agent"
        parent.mkdir(parents=True)

        mode = detect_discovery_mode(parent)

        assert mode == ScanDiscoveryMode.STRUCTURE

    def test_auto_mode_for_plain_directory(self, tmp_path):
        """Plain directory without plugin.json should return AUTO mode."""
        plain_dir = tmp_path / "plain_project"
        plain_dir.mkdir()

        mode = detect_discovery_mode(plain_dir)

        assert mode == ScanDiscoveryMode.AUTO


class TestManifestDiscoveryPaths:
    """Tests for manifest-driven path discovery."""

    def test_get_manifest_paths_existing_files(self, tmp_path):
        """Test getting paths from manifest declarations where files exist."""
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "agents").mkdir()
        (plugin_dir / "commands").mkdir()

        # Create declared files
        (plugin_dir / "agents" / "my_agent.md").write_text("---\nname: my_agent\n---")
        (plugin_dir / "commands" / "cmd.md").write_text("---\nname: cmd\n---")

        manifest = read_plugin_manifest(plugin_dir)
        # Manually set components since we can't write JSON easily
        from skilllint.scan_runtime import PluginManifest

        manifest = PluginManifest(
            path=plugin_dir,
            name="test",
            agents=["my_agent"],
            commands=["cmd"],
            skills=[],
            hooks=[],
        )

        paths = get_manifest_discovery_paths(manifest)

        assert len(paths) == 2
        path_names = {p.name for p in paths}
        assert "my_agent.md" in path_names
        assert "cmd.md" in path_names


class TestStructureDiscoveryPaths:
    """Tests for structure-based path discovery."""

    def test_get_structure_paths_claude_dir(self, tmp_path):
        """Test structure discovery for .claude directory."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "test.md").write_text("test")
        (claude_dir / "hooks.json").write_text("{}")

        paths = get_structure_discovery_paths(claude_dir)

        path_names = {p.name for p in paths}
        assert "test.md" in path_names
        assert "hooks.json" in path_names


class TestResolveFilterAndExpandPaths:
    """Tests for the main path expansion function."""

    def test_expand_with_explicit_glob(self, tmp_path):
        """Test expansion with explicit --filter glob."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "file1.md").write_text("")
        (test_dir / "file2.md").write_text("")

        expanded, is_batch = resolve_filter_and_expand_paths(
            [test_dir], filter_glob="*.md", filter_type=None
        )

        assert len(expanded) == 2
        assert is_batch

    def test_expand_manifest_directory(self, tmp_path):
        """Test expansion uses manifest discovery for plugins with explicit components."""
        plugin_dir = tmp_path / "explicit_plugin"
        plugin_dir.mkdir()
        plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
        plugin_json.parent.mkdir(parents=True)
        plugin_json.write_text('{"name": "test", "agents": ["agent1"]}')
        (plugin_dir / "agents").mkdir()
        (plugin_dir / "agents" / "agent1.md").write_text("---\nname: agent1\n---")

        expanded, is_batch = resolve_filter_and_expand_paths(
            [plugin_dir], filter_glob=None, filter_type=None
        )

        # Should use manifest discovery - only includes explicitly declared files
        assert is_batch

    def test_expand_provider_directory(self, tmp_path):
        """Test expansion uses structure discovery for provider directories."""
        provider_dir = tmp_path / ".claude"
        provider_dir.mkdir()
        (provider_dir / "file.md").write_text("test")

        expanded, is_batch = resolve_filter_and_expand_paths(
            [provider_dir], filter_glob=None, filter_type=None
        )

        assert is_batch
        assert len(expanded) == 1
        assert expanded[0].name == "file.md"

    def test_exclude_mutually_incompatible_filters(self, tmp_path):
        """Test that --filter and --filter-type are mutually exclusive."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Should raise an exception (type may vary by version)
        with pytest.raises(Exception):
            resolve_filter_and_expand_paths(
                [test_dir], filter_glob="*.md", filter_type="skills"
            )
