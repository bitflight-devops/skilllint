"""CX-series Codex platform file validation rules (CX001-CX002).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects. The validator logic was previously inlined in
packages/skilllint/adapters/codex/adapter.py as raw dict construction,
bypassing @skilllint_rule registration entirely. This module lifts that
logic into the registry so CX001 and CX002 are discoverable via
``skilllint rule CX001`` and appear in RULE_REGISTRY.

Architectural note — adapter-backed series:
    CX is one of two rule series (the other is CU) where detection was
    originally owned by a platform adapter rather than the core validator.
    Per architect spec §3.3, the resolution is: this series module OWNS the
    validator logic and the @skilllint_rule registration; the codex adapter
    imports ``validate_codex_content`` and converts its output to
    ``list[dict]`` at the adapter boundary.

    Unlike CU (which validates frontmatter dicts), CX validates raw file
    content strings: CX001 checks AGENTS.md non-emptiness and CX002 checks
    prefix_rule() field names in .rules files. The entry point therefore
    accepts ``content: str`` and an optional ``schema: dict[str, object]``
    rather than a frontmatter dict.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | CX001 | AGENTS.md content is empty                                | error     |
    | CX002 | Unknown field in prefix_rule() block                      | error     |
    +-------+-----------------------------------------------------------+-----------+

Import note: ValidationIssue is deferred inside each function to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from skilllint.rule_registry import skilllint_rule

if TYPE_CHECKING:
    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

_CODEX_AUTHORITY_URL = "https://github.com/openai/codex"
_CX_DOCS_BASE = "https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md"

# Matches: prefix_rule(\n    key = value,\n    ...\n)
# Captures the body between the outer parentheses.
# Source: adapters/codex/adapter.py — same regex, moved here with the logic.
_PREFIX_RULE_RE = re.compile(r"prefix_rule\s*\(([^)]*)\)", re.DOTALL)
# Matches individual key = value pairs inside a prefix_rule() body.
_FIELD_RE = re.compile(r"^\s*(\w+)\s*=", re.MULTILINE)


def _docs_url(code: str) -> str:
    """Return the documentation URL for a CX rule code.

    Args:
        code: Rule code string (e.g., "CX001").

    Returns:
        Full URL with anchor for the error code documentation.
    """
    return f"{_CX_DOCS_BASE}#{code.lower()}"


# ---------------------------------------------------------------------------
# CX001 — AGENTS.md content is empty
# ---------------------------------------------------------------------------


@skilllint_rule(
    "CX001",
    severity="error",
    category="codex",
    platforms=["codex"],
    authority={"origin": "openai/codex", "reference": _CODEX_AUTHORITY_URL},
)
def check_cx001(content: str) -> list[ValidationIssue]:
    """## CX001 — AGENTS.md content is empty

    The ``AGENTS.md`` file exists but contains no non-whitespace content.
    Codex requires ``AGENTS.md`` to be non-empty so that it can provide
    agent context and instructions to the model.

    **Source:** Codex CLI README — ``AGENTS.md`` must exist and contain
    non-empty content.
    ``https://github.com/openai/codex`` (codex-cli/README.md)

    **Fix:** Add meaningful agent context to ``AGENTS.md``:

    ```markdown
    # Agent Instructions

    You are an assistant working in this repository...
    ```

    Returns:
        A single-element list with an error issue when the content is empty
        or whitespace-only; empty list when the file has non-empty content.

    <!-- examples: CX001 -->
    """
    # Deferred import to break circular dependency:
    # plugin_validator imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    if not content.strip():
        return [
            ValidationIssue(
                field="content",
                severity="error",
                message="AGENTS.md is empty",
                code="CX001",
                docs_url=_docs_url("CX001"),
            )
        ]
    return []


# ---------------------------------------------------------------------------
# CX002 — Unknown field in prefix_rule() block
# ---------------------------------------------------------------------------


@skilllint_rule(
    "CX002",
    severity="error",
    category="codex",
    platforms=["codex"],
    authority={"origin": "openai/codex", "reference": _CODEX_AUTHORITY_URL},
)
def check_cx002(content: str, schema: dict[str, object]) -> list[ValidationIssue]:
    """## CX002 — Unknown field in prefix_rule() block

    A ``prefix_rule()`` call in a ``.rules`` file contains a field that is
    not declared in the Codex provider schema's ``prefix_rule.fields``
    object. Unknown fields are not recognised by the Codex execution policy
    engine and will be silently ignored or cause parse errors.

    **Source:** Codex execution policy schema ``codex/v1.json`` —
    ``file_types.prefix_rule.fields`` object.
    Audited from ``codex-rs/execpolicy/README.md``.

    **Fix:** Remove the unknown field, or check for a typo in the field name.
    Known fields are listed in the error message:

    ```
    # Before (unknown field)
    prefix_rule(
        pattern="*.py",
        owner="backend-team",  # not a valid field
    )

    # After
    prefix_rule(pattern="*.py", decision="allow")
    ```

    Returns:
        List of error issues, one per unknown field found across all
        ``prefix_rule()`` blocks; empty when all fields are known or the
        schema has no ``fields`` object.

    <!-- examples: CX002 -->
    """
    # Deferred import to break circular dependency:
    # plugin_validator imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    fields_val: object = schema.get("fields", {})
    known_fields: set[str] = {k for k in fields_val if isinstance(k, str)} if isinstance(fields_val, dict) else set()

    issues: list[ValidationIssue] = []
    for match in _PREFIX_RULE_RE.finditer(content):
        body = match.group(1)
        for field_match in _FIELD_RE.finditer(body):
            field = field_match.group(1)
            if field not in known_fields:
                issues.append(
                    ValidationIssue(
                        field=field,
                        severity="error",
                        message=f"Unknown field '{field}' in prefix_rule() (known fields: {sorted(known_fields)})",
                        code="CX002",
                        docs_url=_docs_url("CX002"),
                    )
                )
    return issues


# ---------------------------------------------------------------------------
# Public entry point for the codex adapter
# ---------------------------------------------------------------------------


def validate_codex_content(
    content: str, file_type: str, schema: dict[str, object] | None = None
) -> list[ValidationIssue]:
    """Public entry point for the codex adapter. Covers CX001 and CX002.

    Dispatches to the appropriate validator based on ``file_type``:
    - ``"agents_md"``: runs CX001 (AGENTS.md non-empty check)
    - ``"prefix_rule"``: runs CX002 (unknown field check, requires ``schema``)

    Args:
        content: Raw file content string.
        file_type: One of ``"agents_md"`` or ``"prefix_rule"``.
        schema: The provider schema sub-object for ``prefix_rule`` file type.
                Required when ``file_type`` is ``"prefix_rule"``; ignored
                otherwise.

    Returns:
        List of ValidationIssue objects from the applicable CX check, or an
        empty list when ``file_type`` is not recognised or ``schema`` is None
        for a ``prefix_rule`` check.
    """
    if file_type == "agents_md":
        return check_cx001(content)
    if file_type == "prefix_rule":
        if schema is None:
            return []
        return check_cx002(content, schema)
    return []


__all__ = ["check_cx001", "check_cx002", "validate_codex_content"]
