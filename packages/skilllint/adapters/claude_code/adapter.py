"""
Claude Code platform adapter.

Data provider for Claude Code platform files. Returns platform metadata
and delegates schema loading to load_bundled_schema(). No validation
logic lives here — the core validator (plan 02-05) runs the checks.
"""

from __future__ import annotations

import pathlib

from skilllint import load_bundled_schema


class ClaudeCodeAdapter:
    """Adapter for Claude Code .claude/**/*.md skill files."""

    def id(self) -> str:
        return "claude_code"

    def path_patterns(self) -> list[str]:
        return [
            ".claude/**/*.md",
            "plugin.json",
            "hooks.json",
            "agents/**/*.md",
            "commands/**/*.md",
        ]

    def applicable_rules(self) -> set[str]:
        return {"SK", "PR", "HK", "AS"}

    def get_schema(self, file_type: str) -> dict | None:
        """Return the bundled schema for the given file_type, or None if unrecognized."""
        schema = load_bundled_schema("claude_code", "v1")
        file_types = schema.get("file_types", {})
        if file_type in file_types:
            return file_types[file_type]
        # Top-level schema for plugin_json maps to root schema object
        if file_type == "plugin_json":
            return schema
        return None

    def validate(self, path: pathlib.Path) -> list[dict]:
        """Platform-level validation. Core validation handled by plan 02-05 validator."""
        return []
