"""
Cursor platform adapter.

Data provider and file-type validator for Cursor platform files.
Validates .mdc frontmatter against the bundled cursor v1.json schema.
No rule-series logic lives here — rule series fire from the core validator.
"""

from __future__ import annotations

import pathlib

import frontmatter

from skilllint import load_bundled_schema


class CursorAdapter:
    """Adapter for Cursor **/*.mdc rule files and skill Markdown."""

    def id(self) -> str:
        return "cursor"

    def path_patterns(self) -> list[str]:
        # NOT ".cursor/**/*.md" — too broad (Pitfall 3 in RESEARCH.md)
        return [
            "**/*.mdc",
            ".cursor/skills/**/*.md",
            ".claude/skills/**/*.md",
            ".agents/skills/**/*.md",
        ]

    def applicable_rules(self) -> set[str]:
        return {"AS"}

    def get_schema(self, file_type: str) -> dict | None:
        """Return the bundled schema sub-object for the given file_type."""
        schema = load_bundled_schema("cursor", "v1")
        return schema.get("file_types", {}).get(file_type)

    def validate(self, path: pathlib.Path) -> list[dict]:
        """Validate .mdc files against the cursor mdc JSON Schema.

        Returns a list of violation dicts with keys: code, severity, message.
        Non-.mdc files are not validated here (rule series handle them).
        """
        if path.suffix != ".mdc":
            return []

        mdc_schema = self.get_schema("mdc")
        if mdc_schema is None:
            return []

        post = frontmatter.load(str(path))
        fm: dict = dict(post.metadata)

        violations: list[dict] = []
        known_fields: set[str] = set(mdc_schema.get("properties", {}).keys())
        required_fields: list[str] = mdc_schema.get("required", [])
        additional_properties: bool = mdc_schema.get("additionalProperties", True)

        # Check required fields
        for field in required_fields:
            if field not in fm:
                violations.append(
                    {
                        "code": "cursor-mdc-missing-required",
                        "severity": "error",
                        "message": f"Required field '{field}' is missing from .mdc frontmatter",
                    }
                )

        # Check for unknown fields when additionalProperties is false
        if not additional_properties:
            for field in fm:
                if field not in known_fields:
                    violations.append(
                        {
                            "code": "cursor-mdc-unknown-field",
                            "severity": "error",
                            "message": (
                                f"Unknown field '{field}' in .mdc frontmatter"
                                f" (additionalProperties is false)"
                            ),
                        }
                    )

        return violations
