"""LK-series internal link rules (LK001).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects.

LK001 is emitted by ``InternalLinkValidator`` in ``plugin_validator.py``
after reading file content and resolving filesystem paths.  The validator
function registered here is a **registration-only stub** — it exists to
make rule metadata available via ``RULE_REGISTRY`` (and therefore via
``skilllint rule LKxxx``) without duplicating the detection logic that
requires live file I/O.

Rule IDs and default severities:
    +-------+-----------------------------------------------+-----------+
    | ID    | Summary                                       | Severity  |
    +-------+-----------------------------------------------+-----------+
    | LK001 | Broken internal link (file does not exist)    | error     |
    +-------+-----------------------------------------------+-----------+

LK002 ("relative link missing ./ prefix") was deleted: both the
AgentSkills specification's own worked example
(``[the reference guide](references/REFERENCE.md)``) and Anthropic's
skills doc (``[reference.md](reference.md)``) use bare relative links
with no ``./`` prefix. LK002 fired on both specs' own examples and had no
sourced justification. The real ``./``-prefix requirement upstream
applies to ``plugin.json`` manifest path fields, a different thing
already covered by PL004.

Import note: ValidationIssue is deferred inside each function to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skilllint.rule_registry import skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# LK001 — Broken internal link (file does not exist)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "LK001",
    severity="error",
    category="link",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_lk001(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## LK001 — Broken internal link

    A relative markdown link in `SKILL.md` points to a file that does not
    exist on the filesystem.  Broken links prevent readers and tools from
    following references and indicate stale documentation.

    **Source:** `InternalLinkValidator` in `plugin_validator.py` — resolves
    each relative link path against the `SKILL.md` parent directory and
    checks for existence via ``Path.exists()``.

    Links containing Claude Code's documented ``${CLAUDE_SKILL_DIR}`` and
    ``${CLAUDE_PLUGIN_ROOT}`` substitution variables are resolved before the
    existence check (see `code.claude.com/docs/en/skills.md
    #available-string-substitutions`). Links containing any other
    unexpanded ``${...}`` token (e.g. ``${CLAUDE_PROJECT_DIR}``,
    ``${CLAUDE_PLUGIN_DATA}``, or an unrecognized variable) are skipped —
    skilllint has no static basis for resolving those targets and no basis
    for asserting they are broken.

    **Fix:** Either create the missing file at the referenced path, or
    correct the link to point to an existing file:

    ```markdown
    <!-- Before (file does not exist) -->
    See [Reference](./references/missing-file.md)

    <!-- After (file exists) -->
    See [Reference](./references/existing-file.md)
    ```

    Returns:
        Always an empty list.  LK001 is emitted by ``InternalLinkValidator``
        in ``plugin_validator.py`` after resolving the linked path on the
        filesystem; this function exists for rule metadata registration only.

    <!-- examples: LK001 -->
    """
    return []


__all__ = ["check_lk001"]
