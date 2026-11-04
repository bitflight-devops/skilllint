"""Cursor platform adapter.

Data provider and file-type validator for Cursor platform files.
Validates .mdc frontmatter against the provider cursor v1.json schema.
No rule-series logic lives here — rule series fire from the core validator.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from skilllint.adapters.protocol import PluginLayout
from skilllint.frontmatter_core import extract_frontmatter
from skilllint.frontmatter_yaml import safe_load_yaml_with_colon_fix
from skilllint.models import ValidationIssue
from skilllint.rule_registry import rule_reference
from skilllint.rules.cu_series import validate_mdc_frontmatter
from skilllint.rules.fm_series import _fm009_recovery_warnings
from skilllint.schemas import load_provider_schema

if TYPE_CHECKING:
    import pathlib

_logger = logging.getLogger(__name__)


class CursorAdapter:
    """Adapter for Cursor **/*.mdc rule files and skill Markdown."""

    def id(self) -> str:
        """Return the adapter ID."""
        return "cursor"

    def path_patterns(self) -> list[str]:
        """Return the glob patterns for files this adapter handles."""
        # NOT ".cursor/**/*.md" — too broad (Pitfall 3 in RESEARCH.md)
        return [
            "**/*.mdc",
            ".cursor/skills/**/*.md",
            ".claude/skills/**/*.md",
            ".agents/skills/**/*.md",
            "**/skills/*/SKILL.md",
        ]

    def applicable_rules(self) -> set[str]:
        """Return the rule series routed for explicit Cursor validation."""
        return {"AS", "CU", "FM", "SK", "LK"}

    def plugin_layouts(self) -> tuple[PluginLayout, ...]:
        """Return portable and Cursor-specific plugin-root markers.

        Source: https://docs.cursor.com/reference/plugins
        """
        return (PluginLayout("plugin.json"), PluginLayout(".cursor-plugin/plugin.json"))

    def constraint_scopes(self) -> set[str]:
        """Return the set of constraint_scope values from the provider schema.

        These are extracted from the field-level constraint_scope annotations
        in the loaded schema (values: 'shared' or 'provider_specific').

        Returns:
            Set of constraint_scope strings, defaulting to {'shared'} if schema
            cannot be loaded or has no constraint_scope annotations.
        """
        try:
            schema = load_provider_schema("cursor")
        except FileNotFoundError:
            _logger.debug("Schema not found for cursor, defaulting to 'shared' scope")
            return {"shared"}

        scopes: set[str] = set()
        for file_type_data in schema.get("file_types", {}).values():
            for field_meta in file_type_data.get("fields", {}).values():
                scope = field_meta.get("constraint_scope")
                if scope:
                    scopes.add(scope)
        return scopes or {"shared"}

    def get_schema(self, file_type: str) -> dict | None:
        """Return the provider schema sub-object for the given file_type."""
        schema = load_provider_schema("cursor")
        return schema.get("file_types", {}).get(file_type)

    def validate(self, path: pathlib.Path) -> list[dict]:
        """Validate .mdc files against the cursor mdc JSON Schema.

        Returns a list of violation dicts with keys: code, severity, message.
        Non-.mdc files are not validated here (rule series handle them).

        Returns:
            List of violation dicts.
        """
        if path.suffix != ".mdc":
            return []

        schema = self.get_schema("mdc")
        mdc_schema: dict[str, object] | None = schema if isinstance(schema, dict) else None
        if mdc_schema is None:
            return []

        content = path.read_text(encoding="utf-8")
        # Manual rules may omit frontmatter. The shared extractor expects a
        # newline after the closing delimiter; Cursor also accepts it at EOF.
        frontmatter_text, _start, _end = extract_frontmatter(content + "\n")
        if frontmatter_text is None:
            if not content.startswith("---"):
                return []
            return [
                ValidationIssue(
                    field="(file)",
                    code="FM003",
                    severity="error",
                    message="YAML frontmatter block not closed with '---'",
                    docs_url=rule_reference("FM003"),
                ).model_dump(exclude_none=True)
            ]

        fm, yaml_error, colon_fields, _used_text = safe_load_yaml_with_colon_fix(frontmatter_text)
        if fm is None:
            message = f"Invalid YAML syntax: {yaml_error}" if yaml_error else "Frontmatter must be a YAML mapping"
            return [
                ValidationIssue(
                    field="(yaml)", code="FM002", severity="error", message=message, docs_url=rule_reference("FM002")
                ).model_dump(exclude_none=True)
            ]

        issues = [
            issue.model_copy(update={"suggestion": f"Quote the value of '{issue.field}'"})
            for issue in _fm009_recovery_warnings(colon_fields)
        ]
        issues.extend(validate_mdc_frontmatter(fm, mdc_schema))
        return [i.model_dump(exclude_none=True) for i in issues]
