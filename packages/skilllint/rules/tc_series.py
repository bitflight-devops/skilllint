"""TC-series token count rules (TC001).

TC001 detection lives here.  ``MarkdownTokenCounter`` in ``plugin_validator.py``
is a thin wrapper: it reads the file (reporting FM002 when the read fails, which
is an FM-series concern rather than a TC one) and hands the content to
``check_tc001``.

TC001 measures content, not frontmatter fields, so ``check_tc001`` takes the
file content.

General token-counting infrastructure — ``count_tokens``, the threshold
constants, and ``count_file_tokens`` — stays in ``skilllint.token_counter`` and
on ``MarkdownTokenCounter``; other callers depend on it and none of it is
TC001-specific.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | TC001 | Token count info (total, frontmatter, body)               | info      |
    +-------+-----------------------------------------------------------+-----------+
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from skilllint.rule_registry import skilllint_rule
from skilllint.token_counter import count_tokens

if TYPE_CHECKING:
    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

#: Matches the closing ``---`` delimiter of a YAML frontmatter block.  Searched
#: against ``content[3:]`` so the opening delimiter cannot match itself.  Same
#: expression ``extract_frontmatter()`` uses, so both agree where the body starts.
_FRONTMATTER_CLOSE_RE = re.compile(r"\n---\s*\n")


def _make_issue(
    *, field: str, severity: Literal["error", "warning", "info"], message: str, code: str
) -> ValidationIssue:
    """Construct a ValidationIssue for a TC rule.

    TC issues carry no ``docs_url``: TC001 reports a measurement rather than a
    violation, so there is nothing for a reader to look up.

    Args:
        field: Issue field label.
        severity: Issue severity.
        message: Human-readable description.
        code: Rule code (e.g. "TC001").

    Returns:
        A frozen ValidationIssue instance.
    """
    # Deferred import to break the circular dependency: plugin_validator
    # imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    return ValidationIssue(field=field, severity=severity, message=message, code=code)


# ---------------------------------------------------------------------------
# TC001 — Token count info (total, frontmatter, body)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "TC001",
    severity="info",
    category="token-count",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills"},
)
def check_tc001(content: str) -> list[ValidationIssue]:
    """## TC001 — Token count info

    Reports the total token count of a markdown file, broken down into
    frontmatter tokens and body tokens.  This is an informational rule — it
    always passes, never blocks validation, and asserts no threshold.  The
    message format is:

    ```
    Total: <N> tokens (frontmatter: <F>, body: <B>)
    ```

    Token counts are computed using ``tiktoken`` (cl100k_base encoding) via the
    ``count_tokens()`` utility in ``skilllint.token_counter``.  The frontmatter
    count is derived as ``total - body``, where ``body`` is measured on the
    content after the closing ``---`` delimiter.  A file with no frontmatter, or
    with an unterminated frontmatter block, is measured as all body.

    **Fix:** No action required.  TC001 is informational only.  If the body
    token count approaches the ``TOKEN_WARNING_THRESHOLD`` or
    ``TOKEN_ERROR_THRESHOLD`` defined in ``skilllint.token_counter``, consider
    splitting the file or moving content to ``references/`` — but TC001 itself
    never checks those thresholds; AS005 / SK006 / SK007 do.

    Args:
        content: Full text of the markdown file, frontmatter included.

    Returns:
        A single info issue carrying the token breakdown.  Never empty, and
        never an error or warning.

    <!-- examples: TC001 -->
    """
    # Body starts after the closing ---; an absent or unterminated frontmatter
    # block means the whole file counts as body.
    end_match = _FRONTMATTER_CLOSE_RE.search(content[3:]) if content.startswith("---") else None
    body = content[end_match.end() + 3 :] if end_match else content

    total_tokens = count_tokens(content)
    body_tokens = count_tokens(body)
    frontmatter_tokens = total_tokens - body_tokens

    return [
        _make_issue(
            field="token-count",
            severity="info",
            message=f"Total: {total_tokens} tokens (frontmatter: {frontmatter_tokens}, body: {body_tokens})",
            code="TC001",
        )
    ]


__all__ = ["check_tc001"]
