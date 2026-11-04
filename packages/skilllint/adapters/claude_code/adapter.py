"""Claude Code platform adapter.

Data provider for Claude Code platform files. Returns platform metadata
and delegates schema loading to load_provider_schema(). No validation
logic lives here — the core validator (plan 02-05) runs the checks.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from skilllint.adapters.protocol import ALL_RULE_SERIES, PluginLayout
from skilllint.schemas import load_provider_schema

if TYPE_CHECKING:
    import pathlib

_logger = logging.getLogger(__name__)


class ClaudeCodeAdapter:
    """Adapter for Claude Code .claude/**/*.md skill files."""

    def id(self) -> str:
        """Return the adapter ID."""
        return "claude_code"

    def path_patterns(self) -> list[str]:
        """Return the glob patterns for files this adapter handles."""
        return [
            ".claude/**/*.md",
            "plugin.json",
            "hooks.json",
            "skills/*/SKILL.md",
            "agents/*.md",
            "agents/**/*.md",
            "commands/*.md",
            "commands/**/*.md",
            "CLAUDE.md",
        ]

    def applicable_rules(self) -> set[str]:
        """Route every registered core series applicable to Claude Code.

        Returns:
            The all-applicable-series sentinel.
        """
        return {ALL_RULE_SERIES}

    def plugin_layouts(self) -> tuple[PluginLayout, ...]:
        """Return the structural marker for a manifest-backed Claude plugin root.

        Claude also accepts a manifestless directory passed explicitly with
        --plugin-dir. Static recursive discovery has no unique marker for that
        case, so unmarked directories continue through ordinary path semantics.
        Source: https://code.claude.com/docs/en/plugins-reference
        """
        return (PluginLayout(".claude-plugin/plugin.json", validation_target="root"),)

    def constraint_scopes(self) -> set[str]:
        """Return the set of constraint_scope values from the provider schema.

        These are extracted from the field-level constraint_scope annotations
        in the loaded schema (values: 'shared' or 'provider_specific').

        Returns:
            Set of constraint_scope strings, defaulting to {'shared'} if schema
            cannot be loaded or has no constraint_scope annotations.
        """
        try:
            schema = load_provider_schema("claude_code")
        except FileNotFoundError:
            _logger.debug("Schema not found for claude_code, defaulting to 'shared' scope")
            return {"shared"}

        scopes: set[str] = set()
        for file_type_data in schema.get("file_types", {}).values():
            for field_meta in file_type_data.get("fields", {}).values():
                scope = field_meta.get("constraint_scope")
                if scope:
                    scopes.add(scope)
        return scopes or {"shared"}

    def get_schema(self, file_type: str) -> dict | None:
        """Return the provider schema for the given file_type, or None if unrecognized."""
        schema = load_provider_schema("claude_code")
        file_types = schema.get("file_types", {})
        if file_type in file_types:
            return file_types[file_type]
        # Top-level schema for plugin_json maps to root schema object
        if file_type == "plugin_json":
            return schema
        return None

    def validate(self, path: pathlib.Path) -> list[dict]:
        """Return no native findings; Claude file kinds use the core validators.

        PluginStructureValidator owns plugin manifests and HookValidator owns
        hooks.json. The platform router collects their findings for this adapter.
        """
        return []
