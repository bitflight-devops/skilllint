"""CU-series Cursor .mdc frontmatter validation rules (CU001-CU002).

Architectural note — adapter-backed series:
    CU is one of two rule series (the other is CX) where detection was
    originally owned by a platform adapter rather than the core validator.
    Per architect spec §3.3, the resolution is: this series module OWNS the
    validator logic and the @skilllint_rule registration; the cursor adapter
    imports ``validate_mdc_source`` and converts its output to
    ``list[dict]`` at the adapter boundary.

    CU001/CU002 were previously inlined in that adapter as raw dict
    construction, bypassing ``@skilllint_rule`` registration entirely; this
    module lifted that logic into the registry so both are discoverable via
    ``skilllint rule CU001`` and appear in ``RULE_REGISTRY``.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | CU001 | Required field missing from .mdc frontmatter              | error     |
    | CU002 | Unknown field in .mdc frontmatter                         | error     |
    +-------+-----------------------------------------------------------+-----------+
"""

from __future__ import annotations

from skilllint.frontmatter_core import extract_frontmatter
from skilllint.frontmatter_yaml import safe_load_yaml_with_colon_fix
from skilllint.models import ValidationIssue
from skilllint.rule_registry import rule_reference, skilllint_rule
from skilllint.rules.fm_series import _fm009_recovery_warnings

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

_CURSOR_DOCS_URL = "https://docs.cursor.com/context/rules-for-ai"


# ---------------------------------------------------------------------------
# CU001 — Required field missing from .mdc frontmatter
# ---------------------------------------------------------------------------


@skilllint_rule(
    "CU001",
    severity="error",
    category="cursor",
    platforms=["cursor"],
    authority={"origin": "cursor.com", "reference": _CURSOR_DOCS_URL},
)
def check_cu001(frontmatter: dict[str, object], mdc_schema: dict[str, object]) -> list[ValidationIssue]:
    """## CU001 — Required field missing from .mdc frontmatter

    The `.mdc` frontmatter is missing a field declared as required in the
    Cursor provider schema. Each required field must be present for the rule
    file to be valid.

    **Source:** Cursor provider schema `cursor v1.json` — `required` array
    in the `mdc` file-type definition.

    **Fix:** Add the missing required field to the frontmatter block:

    ```yaml
    ---
    description: What this rule does
    globs: "**/*.ts"
    alwaysApply: false
    ---
    ```

    Returns:
        List of error issues, one per missing required field; empty when all
        required fields are present or when the schema has no required fields.

    <!-- examples: CU001 -->
    """
    required_val: object = mdc_schema.get("required", [])
    required_fields: list[str] = (
        [f for f in required_val if isinstance(f, str)] if isinstance(required_val, list) else []
    )
    return [
        ValidationIssue(
            field=field,
            severity="error",
            message=f"Required field '{field}' is missing from .mdc frontmatter",
            code="CU001",
            docs_url=rule_reference("CU001"),
        )
        for field in required_fields
        if field not in frontmatter
    ]


# ---------------------------------------------------------------------------
# CU002 — Unknown field in .mdc frontmatter
# ---------------------------------------------------------------------------


@skilllint_rule(
    "CU002",
    severity="error",
    category="cursor",
    platforms=["cursor"],
    authority={"origin": "cursor.com", "reference": _CURSOR_DOCS_URL},
)
def check_cu002(frontmatter: dict[str, object], mdc_schema: dict[str, object]) -> list[ValidationIssue]:
    """## CU002 — Unknown field in .mdc frontmatter

    The `.mdc` frontmatter contains a field that is not defined in the
    Cursor provider schema, and the schema disallows additional properties
    (`additionalProperties: false`). Unknown fields are rejected by Cursor
    when strict schema validation is enforced.

    **Source:** Cursor provider schema `cursor v1.json` — `additionalProperties`
    flag in the `mdc` file-type definition.

    **Fix:** Remove the unknown field from the frontmatter, or verify that
    the field name is spelled correctly:

    ```yaml
    ---
    # Before (unknown field)
    description: My rule
    unknown_key: value

    # After
    description: My rule
    ---
    ```

    Returns:
        List of error issues, one per unknown field; empty when
        ``additionalProperties`` is not ``false`` or all fields are known.

    <!-- examples: CU002 -->
    """
    additional_properties: object = mdc_schema.get("additionalProperties", True)
    if additional_properties is not False:
        return []

    properties_val: object = mdc_schema.get("properties", {})
    if not isinstance(properties_val, dict):
        return []
    known_fields: set[str] = {k for k in properties_val if isinstance(k, str)}
    if not known_fields:
        return []
    return [
        ValidationIssue(
            field=field,
            severity="error",
            message=f"Unknown field '{field}' in .mdc frontmatter (additionalProperties is false)",
            code="CU002",
            docs_url=rule_reference("CU002"),
        )
        for field in frontmatter
        if field not in known_fields
    ]


# ---------------------------------------------------------------------------
# Public entry point for the cursor adapter
# ---------------------------------------------------------------------------


def validate_mdc_frontmatter(frontmatter: dict[str, object], mdc_schema: dict[str, object]) -> list[ValidationIssue]:
    """Public entry point for the cursor adapter. Covers CU001 and CU002.

    Args:
        frontmatter: Parsed frontmatter dict from the .mdc file.
        mdc_schema: The provider schema sub-object for the ``mdc`` file type.

    Returns:
        Combined list of ValidationIssue objects from CU001 and CU002 checks.
    """
    issues: list[ValidationIssue] = []
    issues.extend(check_cu001(frontmatter, mdc_schema))
    issues.extend(check_cu002(frontmatter, mdc_schema))
    return issues


def validate_mdc_source(content: str, mdc_schema: dict[str, object]) -> list[ValidationIssue]:
    """Recover and validate Cursor source using the shared frontmatter parser.

    Args:
        content: Authored .mdc source, optionally containing frontmatter.
        mdc_schema: The Cursor provider schema for .mdc frontmatter.

    Returns:
        Syntax/recovery findings and CU findings when parsing can continue.
    """
    # Longer hyphen runs are Markdown thematic breaks, not YAML delimiters.
    if content.partition("\n")[0].rstrip(" \t") != "---":
        return validate_mdc_frontmatter({}, mdc_schema)

    # The shared extractor expects a newline after the closing delimiter;
    # Cursor also accepts it at EOF.
    frontmatter_text, _start, _end = extract_frontmatter(content + "\n")
    if frontmatter_text is None:
        return [
            ValidationIssue(
                field="(file)",
                code="FM003",
                severity="error",
                message="YAML frontmatter block not closed with '---'",
                docs_url=rule_reference("FM003"),
            )
        ]

    fm, yaml_error, colon_fields, _used_text = safe_load_yaml_with_colon_fix(frontmatter_text)
    if fm is None:
        message = f"Invalid YAML syntax: {yaml_error}" if yaml_error else "Frontmatter must be a YAML mapping"
        return [
            ValidationIssue(
                field="(yaml)", code="FM002", severity="error", message=message, docs_url=rule_reference("FM002")
            )
        ]

    issues = [
        issue.model_copy(update={"suggestion": f"Quote the value of '{issue.field}'"})
        for issue in _fm009_recovery_warnings(colon_fields)
    ]
    issues.extend(validate_mdc_frontmatter(fm, mdc_schema))
    return issues


__all__ = ["check_cu001", "check_cu002", "validate_mdc_frontmatter", "validate_mdc_source"]
