"""LK-series internal link rules (LK001).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects.

LK001 detection lives here.  ``InternalLinkValidator`` in
``plugin_validator.py`` is a thin wrapper that reads the file and calls the
rule function, packaging its issues into a ``ValidationResult``.

``_iter_links`` strips fenced code blocks and inline code spans, applies the
external/anchor/absolute skip list, and yields
``(text, url, url_without_fragment)`` triples.

``check_lk001`` takes the markdown body plus the ``SKILL.md`` path it resolves
links against.

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

import re
from typing import TYPE_CHECKING

from skilllint.rule_registry import _make_issue, skilllint_rule

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Shared link extraction
# ---------------------------------------------------------------------------

# Regex pattern for extracting markdown links (Architecture line 1219)
LINK_PATTERN = r"\[([^\]]+)\]\(([^)]+)\)"

# Regex pattern for fenced code blocks (``` or ~~~, with optional language specifier).
# Uses backreference to match opening/closing fence of equal or greater length.
CODE_FENCE_PATTERN = r"^(`{3,}|~{3,})[^\n]*\n.*?\n\1\s*$"

# Regex pattern for inline code spans (single or multiple backticks)
INLINE_CODE_PATTERN = r"(`+)(?!`)(.+?)(?<!`)\1(?!`)"


def _strip_code_blocks(content: str) -> str:
    """Remove fenced code blocks and inline code spans from content.

    Strips fenced code blocks delimited by ``` or ~~~ (with optional
    language specifiers) and inline code spans wrapped in backticks.
    This prevents code examples from being scanned for markdown links.

    Args:
        content: Raw markdown content

    Returns:
        Content with code blocks and inline code spans removed
    """
    # Strip fenced code blocks first (handles nested fences via greedy
    # backreference matching: a 4-backtick fence won't close on 3 backticks)
    stripped = re.sub(CODE_FENCE_PATTERN, "", content, flags=re.MULTILINE | re.DOTALL)
    # Strip inline code spans
    return re.sub(INLINE_CODE_PATTERN, "", stripped)


def _should_ignore_link(url: str) -> bool:
    """Check if link should be ignored during validation.

    Args:
        url: Link URL to check

    Returns:
        True if link should be ignored (external, anchor, absolute)
    """
    # Ignore external links
    if url.startswith(("http://", "https://", "ftp://")):
        return True

    # Ignore anchor links
    if url.startswith("#"):
        return True

    # Ignore absolute paths
    return bool(url.startswith("/"))


def _iter_links(content: str) -> Iterator[tuple[str, str, str]]:
    """Yield every relative markdown link in *content*.

    Code blocks and inline code spans are stripped first, then external,
    anchor and absolute links are skipped.

    Args:
        content: Raw markdown content

    Yields:
        ``(link_text, link_url, link_url_without_fragment)`` for each
        relative link, where the third element has any ``#anchor`` suffix
        removed (e.g. ``./references/file.md#heading`` becomes
        ``./references/file.md``).
    """
    for match in re.finditer(LINK_PATTERN, _strip_code_blocks(content)):
        link_text = match.group(1)
        link_url = match.group(2)

        # Filter to relative file links only
        if _should_ignore_link(link_url):
            continue

        # Strip anchor fragment before resolving path
        yield link_text, link_url, link_url.split("#")[0]


# Regex pattern for any ${...} substitution-style token. Matches both
# Claude Code's documented ${CLAUDE_*} variables
# (code.claude.com/docs/en/skills.md#available-string-substitutions)
# and any other unrecognized ${...} token, so both can be routed through
# _STATICALLY_RESOLVABLE_CLAUDE_VARS and skipped when unresolvable.
CLAUDE_VAR_PATTERN = r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}"

# Of the four documented variables, only these two have a target skilllint can
# determine statically from the plugin source tree. ${CLAUDE_PROJECT_DIR} and
# ${CLAUDE_PLUGIN_DATA} target install-time locations (the invoking project
# root; the plugin's persistent data directory) that do not exist in the plugin
# source, so skilllint has no basis for resolving or asserting them broken.
_STATICALLY_RESOLVABLE_CLAUDE_VARS: frozenset[str] = frozenset({"CLAUDE_SKILL_DIR", "CLAUDE_PLUGIN_ROOT"})


def _resolve_claude_variables(url: str, skill_dir: Path) -> str | None:
    """Substitute ${CLAUDE_*} variables skilllint can statically resolve.

    Claude Code substitutes ``${CLAUDE_SKILL_DIR}``, ``${CLAUDE_PROJECT_DIR}``,
    ``${CLAUDE_PLUGIN_ROOT}``, and ``${CLAUDE_PLUGIN_DATA}`` in skill markdown
    content at runtime (code.claude.com/docs/en/skills.md
    #available-string-substitutions). ``${CLAUDE_SKILL_DIR}`` always resolves to
    the directory containing ``SKILL.md``. ``${CLAUDE_PLUGIN_ROOT}`` resolves via
    :func:`skilllint.plugin_validator.find_plugin_dir` when the link's SKILL.md
    lives inside a plugin (same lookup ``HookValidator`` uses for
    ``${CLAUDE_PLUGIN_ROOT}`` in hook commands).

    ``${CLAUDE_PROJECT_DIR}`` and ``${CLAUDE_PLUGIN_DATA}`` target install-time
    locations skilllint cannot determine from the plugin source tree, and any
    other ``${...}`` token is not a documented substitution variable at all.
    skilllint has no basis for asserting either kind of target is broken, so the
    link is skipped rather than reported.

    Args:
        url: The link URL (fragment already stripped) as written in the
            markdown source.
        skill_dir: Directory containing the ``SKILL.md`` file being validated --
            used both as the ``${CLAUDE_SKILL_DIR}`` target and as the search
            start for ``${CLAUDE_PLUGIN_ROOT}``.

    Returns:
        The URL with resolvable variables substituted, or ``None`` if the link
        should be skipped because a variable's target cannot be determined.
    """
    tokens = set(re.findall(CLAUDE_VAR_PATTERN, url))
    if not tokens:
        return url
    if tokens - _STATICALLY_RESOLVABLE_CLAUDE_VARS:
        return None

    resolved = url
    if "${CLAUDE_SKILL_DIR}" in resolved:
        resolved = resolved.replace("${CLAUDE_SKILL_DIR}", str(skill_dir))
    if "${CLAUDE_PLUGIN_ROOT}" in resolved:
        # Deferred import to break the circular dependency: plugin_validator
        # imports rules/, so rules/ cannot import plugin_validator at module level.
        from skilllint.plugin_validator import find_plugin_dir  # noqa: PLC0415

        plugin_root = find_plugin_dir(skill_dir)
        if plugin_root is None:
            return None
        resolved = resolved.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root))
    return resolved


# ---------------------------------------------------------------------------
# LK001 — Broken internal link (file does not exist)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "LK001",
    severity="error",
    category="link",
    platforms=["agentskills"],
    # No authority: no vendor doc documents a "check that internal markdown
    # links resolve" requirement. Broken links are skilllint's own
    # documentation-hygiene check, not a claim traceable to an upstream spec.
)
def check_lk001(content: str, path: Path) -> list[ValidationIssue]:
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

    Args:
        content: Raw markdown body of the file being checked.
        path: Path to the file the links live in; relative links resolve
            against its parent directory.

    Returns:
        One issue per relative link whose target does not exist on disk;
        empty when every link resolves.

    <!-- examples: LK001 -->
    """
    issues: list[ValidationIssue] = []
    skill_dir = path.parent

    for link_text, link_url, link_url_no_fragment in _iter_links(content):
        # Resolve documented ${CLAUDE_*} substitution variables before the
        # existence check. None means the link must be skipped because a
        # variable's target cannot be determined statically.
        resolved_url = _resolve_claude_variables(link_url_no_fragment, skill_dir)
        if resolved_url is None:
            continue

        # Resolve link path relative to SKILL.md directory
        link_path = (skill_dir / resolved_url).resolve()

        if not link_path.exists():
            issues.append(
                _make_issue(
                    field="internal-links",
                    severity="error",
                    message=f"Broken link: [{link_text}]({link_url}) (file not found)",
                    code="LK001",
                    suggestion=f"Create missing file or fix link path: {link_url}",
                )
            )

    return issues


__all__ = ["check_lk001"]
