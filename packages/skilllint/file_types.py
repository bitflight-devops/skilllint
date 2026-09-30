"""Capability and scan-context classification contracts.

This module classifies paths without depending on validators, CLI wiring, or
scan orchestration. The legacy ``plugin_validator`` and ``scan_runtime``
modules re-export selected names for compatibility during #283.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from skilllint.frontmatter_core import FRONTMATTER_EXEMPT_FILENAMES
from skilllint.plugin_manifest import load_plugin_json


class ScanContext(StrEnum):
    """Structural context of a scan target directory."""

    PLUGIN = "plugin"
    PROVIDER = "provider"
    BARE = "bare"


class FileType(StrEnum):
    """Type of capability file."""

    SKILL = "skill"
    AGENT = "agent"
    COMMAND = "command"
    PLUGIN = "plugin"
    HOOK_CONFIG = "hook_config"
    HOOK_SCRIPT = "hook_script"
    CLAUDE_MD = "claude_md"
    REFERENCE = "reference"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"

    @staticmethod
    def _is_plugin_scoped_unknown(path: Path, plugin_root: Path) -> bool:
        """Return whether a plugin-scoped path is skill-internal."""
        if "agents" in path.parts and path.parent != plugin_root / "agents":
            return True
        return bool("commands" in path.parts and path.parent != plugin_root / "commands")

    @staticmethod
    def _manifest_declared_type(path: Path) -> FileType | None:
        """Return a file type declared by the nearest Claude plugin manifest."""
        for plugin_root in (path, *path.parents):
            if not (plugin_root / ".claude-plugin" / "plugin.json").is_file():
                continue
            manifest = load_plugin_json(plugin_root)
            if manifest is None:
                continue
            for field_name, file_type in (("agents", FileType.AGENT), ("commands", FileType.COMMAND)):
                declarations = manifest.get(field_name)
                if not isinstance(declarations, list):
                    continue
                for declaration in declarations:
                    if not isinstance(declaration, str):
                        continue
                    target = plugin_root / declaration
                    if path == target or (target.is_dir() and path.parent == target):
                        return file_type
        return None

    @staticmethod
    def detect_file_type(
        path: Path, scan_context: ScanContext | None = None, plugin_root: Path | None = None
    ) -> FileType:
        """Detect file type from path structure and optional scan context.

        Args:
            path: Path to classify.
            scan_context: Optional structural scan context.
            plugin_root: Optional plugin root for context-aware classification.

        Returns:
            Classified FileType.
        """
        if (
            scan_context == ScanContext.PLUGIN
            and plugin_root is not None
            and FileType._is_plugin_scoped_unknown(path, plugin_root)
        ):
            return FileType.UNKNOWN

        if path.name == "SKILL.md":
            return FileType.SKILL
        if (
            path.name in {"plugin.json", "marketplace.json"}
            or (path / ".claude-plugin/plugin.json").exists()
            or (path / ".claude-plugin/marketplace.json").exists()
        ):
            return FileType.PLUGIN
        if (manifest_type := FileType._manifest_declared_type(path)) is not None:
            return manifest_type
        if "agents" in path.parts:
            return FileType.AGENT
        if "commands" in path.parts:
            return FileType.COMMAND
        if path.name == "hooks.json":
            return FileType.HOOK_CONFIG
        if "hooks" in path.parts:
            return FileType.HOOK_SCRIPT
        if path.name == "CLAUDE.md":
            return FileType.CLAUDE_MD
        if "references" in path.parts and path.suffix == ".md":
            return FileType.REFERENCE
        if path.suffix == ".md":
            return FileType.MARKDOWN
        return FileType.UNKNOWN


class FrontmatterRequirement(StrEnum):
    """Whether a capability path requires YAML frontmatter."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    EXEMPT = "exempt"


NAME_BEARING_FILE_TYPES: frozenset[FileType] = frozenset({FileType.SKILL, FileType.AGENT, FileType.COMMAND})
"""File types whose frontmatter may carry a ``name`` field."""


def frontmatter_requirement(path: Path) -> FrontmatterRequirement:
    """Return the frontmatter requirement for a capability path."""
    if path.name in FRONTMATTER_EXEMPT_FILENAMES:
        return FrontmatterRequirement.EXEMPT
    if path.name == "SKILL.md":
        return FrontmatterRequirement.REQUIRED

    parent_name = path.parent.name
    if FileType.detect_file_type(path) in {FileType.AGENT, FileType.COMMAND} or parent_name in {"agents", "commands"}:
        return FrontmatterRequirement.REQUIRED

    parts = set(path.parts)
    if "agents" in parts or "commands" in parts:
        return FrontmatterRequirement.OPTIONAL
    return FrontmatterRequirement.REQUIRED


def file_has_frontmatter(path: Path) -> bool:
    """Return whether a file begins with a YAML frontmatter delimiter."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return content.startswith("---")


__all__ = [
    "FileType",
    "FrontmatterRequirement",
    "NAME_BEARING_FILE_TYPES",
    "ScanContext",
    "file_has_frontmatter",
    "frontmatter_requirement",
]
