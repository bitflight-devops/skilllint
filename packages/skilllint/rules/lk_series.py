"""LK-series internal link rules (LK001, LK004).

LK001 and LK004 detection lives here.  ``InternalLinkValidator`` (LK001) and
``PluginLinkEscapeValidator`` (LK004) in ``plugin_validator.py`` are thin
wrappers that read files and call the rule functions, packaging their issues
into a ``ValidationResult``.

``_iter_links`` strips fenced code blocks and inline code spans, applies the
external/anchor/absolute skip list, and yields
``(text, url, url_without_fragment, line)`` tuples.

``check_lk001`` takes the markdown body plus the ``SKILL.md`` path it resolves
links against. ``check_lk004`` additionally takes the plugin root the links
must stay inside.

Rule IDs and default severities:
    +-------+-----------------------------------------------+-----------+
    | ID    | Summary                                       | Severity  |
    +-------+-----------------------------------------------+-----------+
    | LK001 | Broken internal link (file does not exist)    | error     |
    | LK004 | Link may dangle once the plugin is installed  | info      |
    +-------+-----------------------------------------------+-----------+

LK003 is reserved for the repo-doc broken-link rule proposed in
``docs/design-markdown-link-conventions.md``.

LK002 ("relative link missing ./ prefix") was deleted: both the
AgentSkills specification's own worked example
(``[the reference guide](references/REFERENCE.md)``) and Anthropic's
skills doc (``[reference.md](reference.md)``) use bare relative links
with no ``./`` prefix. LK002 fired on both specs' own examples and had no
sourced justification. The real ``./``-prefix requirement upstream
applies to ``plugin.json`` manifest path fields, a different thing
already covered by PL004.
"""

from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote

from skilllint.rule_registry import _make_issue, skilllint_rule

if TYPE_CHECKING:
    from collections.abc import Iterator

    from skilllint.models import ValidationIssue

# ---------------------------------------------------------------------------
# Shared link extraction
# ---------------------------------------------------------------------------

# Regex pattern for inline markdown links, per CommonMark 0.31.2 section 6.3
# (spec.commonmark.org/0.31.2/#links): the destination is ``<...>`` (spaces
# allowed) or a run with no spaces in which parentheses are balanced or
# backslash-escaped, followed by an optional title in double quotes, single
# quotes or parentheses. Group 2 is a bracketed destination, group 3 a bare one.
# ponytail: one level of nested parentheses (``a(b).md``, ``Foo_(bar)``);
# CommonMark allows 32, extend _BARE_DESTINATION if deeper nesting shows up.
_BARE_DESTINATION = r"(?!<)(?:[^\s()\\]|\\.|\((?:[^\s()\\]|\\.)*\))+"
LINK_PATTERN = (
    r"\[([^\]]+)\]\(\s*(?:<([^>\n]*)>|(" + _BARE_DESTINATION + r"))"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^()]*\)))?\s*\)"
)

# Raw HTML in Markdown (CommonMark 0.31.2 sections 4.6 and 6.6) links with an
# ``href`` or ``src`` attribute on any tag. A tag spans ``<name ... >``; each
# attribute value is double-quoted, single-quoted or unquoted.
HTML_TAG_PATTERN = r"<([A-Za-z][A-Za-z0-9-]*)(\s[^<>]*)>"
HTML_LINK_ATTRIBUTE_PATTERN = r"\s(href|src)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'=<>`]+))"

# Regex pattern for link reference definitions (``[label]: dest "title"``),
# per CommonMark 0.31.2 section 4.7 (spec.commonmark.org/0.31.2/#link-reference-definitions):
# up to three spaces of indentation, a destination optionally wrapped in
# ``<>``, and an optional title in double quotes, single quotes or parentheses.
# A ``[^label]:`` footnote definition is not a link and is excluded.
REFERENCE_DEFINITION_PATTERN = (
    r"^ {0,3}\[(?!\^)([^\]]+)\]:[ \t]*(?:<([^>\n]+)>|([^\s<]\S*))"
    r"(?:[ \t]+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^)\n]*\)))?[ \t]*$"
)

# CommonMark 0.31.2 section 2.4 (backslash escapes: any ASCII punctuation) and
# section 2.5 (entity and numeric character references, which require the
# trailing ``;``) both apply inside link destinations.
BACKSLASH_ESCAPE_PATTERN = r"\\([!-/:-@\[-`{-~])"
CHARACTER_REFERENCE_PATTERN = r"&(?:#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});"

# Both decode forms in one alternation, scanned left to right over the
# original string in a single pass: a character produced by decoding one form
# must never be re-scanned as input to the other (e.g. ``\&amp;evil.md`` is a
# backslash-escaped literal ``&`` followed by inert text, not the entity
# ``&amp;`` -- decoding the two forms as separate sequential passes would
# read pass 1's bare ``&`` output back into pass 2 as an entity).
_DESTINATION_DECODE_PATTERN = re.compile(f"{BACKSLASH_ESCAPE_PATTERN}|{CHARACTER_REFERENCE_PATTERN}")


def _decode_destination_replacement(match: re.Match[str]) -> str:
    # Group 1 is only set by the backslash-escape branch; the
    # character-reference branch has no group, so group 1 is None there and
    # the whole match is decoded as an entity/numeric reference instead.
    escaped_char = match.group(1)
    return escaped_char if escaped_char is not None else html.unescape(match.group(0))


def _decode_destination(url: str) -> str:
    """Return the destination a Markdown renderer produces from *url*.

    Backslash escapes and character references are decoded as CommonMark
    specifies, in a single left-to-right scan. Percent-encoding is left in
    place; the caller decodes the path part once the ``#fragment`` is split
    off, so ``%23`` stays part of the path.
    """
    return _DESTINATION_DECODE_PATTERN.sub(_decode_destination_replacement, url)


# Regex pattern for fenced code blocks (``` or ~~~, with optional language specifier).
# Uses backreference to match opening/closing fence of equal or greater length.
CODE_FENCE_PATTERN = r"^(`{3,}|~{3,})[^\n]*\n.*?\n\1\s*$"

# Regex pattern for inline code spans (single or multiple backticks)
INLINE_CODE_PATTERN = r"(`+)(?!`)(.+?)(?<!`)\1(?!`)"

# HTML comments (CommonMark 0.31.2 section 6.6) are not rendered, so a link
# inside one is not a link.
HTML_COMMENT_PATTERN = r"<!--.*?-->"


def _strip_code_blocks(content: str) -> str:
    """Remove fenced code blocks, inline code spans and HTML comments from content.

    Strips fenced code blocks delimited by ``` or ~~~ (with optional
    language specifiers), inline code spans wrapped in backticks, and
    ``<!-- ... -->`` comments. This prevents code examples and commented-out
    text from being scanned for markdown links.

    Args:
        content: Raw markdown content

    Returns:
        Content with code blocks, inline code spans and comments removed. A
        fenced block or comment is replaced by its own newlines so every
        remaining character keeps its original line number.
    """
    # Strip fenced code blocks first (handles nested fences via greedy
    # backreference matching: a 4-backtick fence won't close on 3 backticks)
    stripped = re.sub(
        CODE_FENCE_PATTERN, lambda m: "\n" * m.group(0).count("\n"), content, flags=re.MULTILINE | re.DOTALL
    )
    # Strip inline code spans, then comments (a `<!--` inside code is code)
    stripped = re.sub(INLINE_CODE_PATTERN, "", stripped)
    return re.sub(HTML_COMMENT_PATTERN, lambda m: "\n" * m.group(0).count("\n"), stripped, flags=re.DOTALL)


# CommonMark 0.31.2 section 6.9 (autolinks: spec.commonmark.org/0.31.2/#absolute-uri):
# a scheme is an ASCII letter followed by 1 to 31 further ASCII letters,
# digits, "+", "-" or "." (total length 2-32), followed by ":". Any such
# scheme prefix names an absolute URI, not a relative filesystem path --
# mailto:, tel: and custom schemes are external links, the same as http(s):
# and ftp:, not just the three hardcoded ones.
_URI_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]{1,31}:")


def _should_ignore_link(url: str) -> bool:
    """Check if link should be ignored during validation.

    Args:
        url: Link URL to check

    Returns:
        True if link should be ignored (external, anchor, absolute)
    """
    # Ignore any absolute-URI-scheme link (http:, https:, ftp:, mailto:, tel:, ...)
    if _URI_SCHEME_PATTERN.match(url):
        return True

    # Ignore anchor links
    if url.startswith("#"):
        return True

    # Ignore absolute paths
    return bool(url.startswith("/"))


def _iter_html_links(stripped: str) -> Iterator[tuple[int, str, str, bool]]:
    """Yield ``(offset, label, value, True)`` for each ``href``/``src`` attribute."""
    for tag in re.finditer(HTML_TAG_PATTERN, stripped):
        attributes_start = tag.start(2)
        for attribute in re.finditer(HTML_LINK_ATTRIBUTE_PATTERN, tag.group(2), flags=re.IGNORECASE):
            value = next(group for group in attribute.groups()[1:] if group is not None)
            label = f"<{tag.group(1)} {attribute.group(1).lower()}>"
            yield attributes_start + attribute.start(), label, value, True


def _iter_links(content: str, *, keep_root_absolute: bool = False) -> Iterator[tuple[str, str, str, int]]:
    r"""Yield every relative markdown link in *content*, in document order.

    Inline links (``[text](dest "title")``), link reference definitions
    (``[label]: dest "title"``) and ``href``/``src`` attributes of raw HTML
    tags are all links. ``link_text`` is the link text, the definition's
    label, or ``<tag attribute>`` for HTML. Code blocks and inline code spans are stripped first, then
    external, anchor and absolute links are skipped.

    Args:
        content: Raw markdown content
        keep_root_absolute: Also yield root-absolute ``/path`` links. A
            protocol-relative ``//host/path`` URL is still skipped.

    Yields:
        ``(link_text, link_url, link_url_without_fragment, line)`` for each
        relative link. ``link_url`` is the destination as written, without
        any title. The third element is the filesystem path it names:
        character references decoded (outside HTML, backslash escapes too;
        inside HTML, ``\`` read as ``/``), any ``#anchor`` suffix removed, then
        percent-decoded (e.g. ``./references/my%20file.md#heading`` becomes
        ``./references/my file.md``). ``line`` is the 1-based line of the
        link's opening ``[``, or of its HTML attribute, in *content*.
    """
    stripped = _strip_code_blocks(content)
    inline = (
        (m.start(), m.group(1), m.group(2) if m.group(2) is not None else m.group(3), False)
        for m in re.finditer(LINK_PATTERN, stripped)
    )
    definitions = (
        (m.start(), m.group(1), m.group(2) or m.group(3), False)
        for m in re.finditer(REFERENCE_DEFINITION_PATTERN, stripped, flags=re.MULTILINE)
    )
    for start, link_text, link_url, is_html in sorted([*inline, *definitions, *_iter_html_links(stripped)]):
        if not link_url:
            continue
        # Filter to relative file links only, judged on the decoded
        # destination so an escaped or entity-encoded form cannot hide a link.
        # An HTML attribute value takes character references but no backslash
        # escapes (CommonMark 0.31.2 section 6.6 leaves raw HTML as HTML), and
        # a browser resolves it as a URL whose ``\`` ends a path segment like
        # ``/`` (url.spec.whatwg.org/#path-state, special schemes). In a Markdown
        # destination a ``\`` that survives unescaping stays a literal
        # character: CommonMark renderers emit it as ``%5C``.
        destination = html.unescape(link_url).replace("\\", "/") if is_html else _decode_destination(link_url)
        root_absolute = destination.startswith("/") and not destination.startswith("//")
        if _should_ignore_link(destination) and not (keep_root_absolute and root_absolute):
            continue

        # Strip anchor fragment, then percent-decode the path for the filesystem
        line = stripped.count("\n", 0, start) + 1
        yield link_text, link_url, unquote(destination.split("#")[0]), line


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
    exist on the filesystem. Inline links (with or without a title), link
    reference definitions (``[label]: path "title"``) and the ``href``/``src``
    attributes of raw HTML tags are all checked: a missing ``<img src>``
    target is as broken as a missing ``[text](path)`` target. The destination is decoded
    as a Markdown renderer decodes it (backslash escapes, character
    references, then percent-encoding), so ``my%20file.md`` names
    ``my file.md``.  Broken links prevent readers and tools from
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
    # Resolve to absolute up front: callers (pre-commit, in particular) pass
    # relative paths, and every downstream use of skill_dir -- the
    # ${CLAUDE_SKILL_DIR} substitution, the find_plugin_dir() walk behind
    # ${CLAUDE_PLUGIN_ROOT}, and the final join below -- must operate on an
    # absolute base or a relative substituted path (e.g. "plugins/foo/README.md")
    # gets appended onto skill_dir instead of replacing it (Path.__truediv__
    # only discards the left operand when the right operand is absolute).
    skill_dir = path.parent.resolve()

    for link_text, link_url, link_url_no_fragment, _line in _iter_links(content):
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


# ---------------------------------------------------------------------------
# LK004 — Link may dangle at runtime when the plugin is installed
# ---------------------------------------------------------------------------

_LK004_COPIED_PLUGINS_URL = "https://code.claude.com/docs/en/plugins/loading.md#in-place-and-copied-plugins"


@skilllint_rule(
    "LK004",
    # Observation, not a defect: linking outside the plugin is a legitimate
    # choice; it only means the reference may dangle once installed.
    severity="info",
    category="link",
    # Codex also installs a plugin into a cache and loads that copy
    # (developers.openai.com/codex/plugins/build.md#how-local-marketplaces-work).
    # Cursor is excluded: its docs do not say that only the plugin directory is
    # installed, and a served marketplace is "a synced copy of this repository"
    # (cursor.com/docs/plugins.md).
    platforms=["claude-code", "codex"],
    # Grounding, not a vendor rule: the cited page states that a marketplace
    # plugin is copied into the plugin cache and that files outside the plugin
    # directory are not copied. No vendor doc requires Markdown links to stay
    # inside the plugin; this is skilllint's own observation.
    authority={"origin": "code.claude.com", "reference": _LK004_COPIED_PLUGINS_URL},
)
def check_lk004(content: str, path: Path, plugin_root: Path) -> list[ValidationIssue]:
    r"""## LK004 — Link may dangle at runtime when the plugin is installed

    An observation, reported at ``info`` level so it never fails a check. A
    markdown link that an agent reads from an installed plugin points
    somewhere the installed copy may not reach. Linking outside the plugin is
    a legitimate choice; the rule only says the reference may dangle at
    runtime when the plugin is installed. Two cases are reported:

    - Under ``skills/``: a link whose target resolves outside the plugin
      root, whether or not the target exists. A relative link resolves
      against the linking file's own directory (``SKILL.md`` against its
      skill directory, ``references/*.md`` against ``references/``), so it
      escapes by climbing past the root (``../../../rules/x.md``). A
      root-absolute link (``/docs/x.md``) is always outside.
    - Under ``agents/`` and ``commands/``: any relative link. These bodies
      are injected as prompts that run in the user's project, not the
      plugin: an agent file's body "becomes the system prompt" and "a
      subagent starts in the main conversation's current working directory"
      (`code.claude.com/docs/en/sub-agents.md`), and a command body runs in
      the main conversation. So a relative link resolves against the
      project root. ``${CLAUDE_PLUGIN_ROOT}`` links and root-absolute links
      there are checked as under ``skills/``.

    **Authority:** skilllint's own observation, grounded in plugin
    self-containment. Claude Code copies a marketplace plugin into
    ``~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`` at install
    and loads that copy; "Files outside the plugin directory aren't copied"
    (`code.claude.com/docs/en/plugins/loading.md#in-place-and-copied-plugins`).
    Codex installs a plugin into
    ``~/.codex/plugins/cache/$MARKETPLACE_NAME/$PLUGIN_NAME/$VERSION/`` and
    "loads the installed copy from that cache path"
    (`developers.openai.com/codex/plugins/build.md#how-local-marketplaces-work`).
    No vendor doc states a rule about Markdown links. Cursor is not covered: its plugin docs do not say that only
    the plugin directory is installed.

    **Scope:** the ``*.md`` files under ``agents/``, ``skills/`` and
    ``commands/`` of a plugin root, a directory that holds
    ``.claude-plugin/plugin.json`` or ``.codex-plugin/plugin.json``. Those
    are the files an agent reads from the installed copy. READMEs,
    ``CLAUDE.md``, ``AGENTS.md``, ``docs/`` and ADRs are read in the source
    repository and are not checked. The walk skips ``.git``,
    ``node_modules``, ``.venv``, files excluded by ``.pluginvalidatorignore``
    or git, and observations a path-scoped ignore config suppresses for the
    linking file. The rule runs when skilllint validates the plugin itself: the
    plugin directory, a tree containing it, or its manifest. Passing only one
    Markdown file does not run it. A standalone skill with neither manifest
    has no plugin root, is not copied into a plugin cache, and is not checked.

    Paths are compared lexically, after ``..`` segments are collapsed and
    without following symlinks, so a symlink inside the plugin does not
    count as an escape. Links are found the same way as LK001: inline links
    (a title is not part of the path), link reference definitions
    (``[label]: path "title"``), and the ``href``/``src`` attributes of raw
    HTML such as ``<a href>`` and ``<img src>``, since a file outside the
    plugin is missing from the cache whatever syntax links to it. Code
    blocks and inline code are skipped, and URLs, ``#anchor`` links and
    ``//host`` links are ignored. A destination is decoded as a Markdown
    renderer decodes it before it is resolved: backslash escapes (not in
    HTML attributes) and character references first (``\.\./`` and
    ``&#46;&#46;/`` both become ``../``), then percent-encoding (``%2E%2E/``).
    In an HTML ``href``/``src``, ``\`` separates path segments as ``/`` does,
    as a browser's URL parser reads it (``..\..\x.md`` escapes); in a
    Markdown destination a ``\`` left after unescaping is a literal
    character, which CommonMark renderers emit as ``%5C``.
    ``${CLAUDE_PLUGIN_ROOT}`` and
    ``${CLAUDE_SKILL_DIR}`` are substituted as in LK001;
    ``${CLAUDE_SKILL_DIR}`` becomes the linking file's own directory. A link
    with any other ``${...}`` token is skipped.

    **If the reference must work once installed:** move or copy the target
    into the plugin and link to it there (in an agent file, through
    ``${CLAUDE_PLUGIN_ROOT}``), or link to a published URL:

    ```markdown
    <!-- May dangle once installed -->
    See [Rules](../../rules/python.md)

    <!-- Inside the plugin -->
    See [Rules](./references/python.md)
    ```

    Args:
        content: Raw markdown body of the file being checked.
        path: Path to the file the links live in; relative links resolve
            against its parent directory.
        plugin_root: The plugin root directory the links must stay inside.

    Returns:
        One ``info`` issue per reported link (see the two cases above), with
        ``field`` set to the file path relative to *plugin_root* and
        ``line`` set to the link's line in *content*.

    <!-- examples: LK004 -->
    """
    issues: list[ValidationIssue] = []
    root = Path(os.path.normpath(plugin_root.absolute()))
    base_dir = Path(os.path.normpath(path.parent.absolute()))
    relative_file = Path(os.path.normpath(path.absolute())).relative_to(root).as_posix()
    is_prompt_file = relative_file.split("/", 1)[0] in {"agents", "commands"}

    for link_text, link_url, link_url_no_fragment, line in _iter_links(content, keep_root_absolute=True):
        resolved_url = _resolve_claude_variables(link_url_no_fragment, base_dir)
        if resolved_url is None:
            continue

        if is_prompt_file and resolved_url == link_url_no_fragment and not resolved_url.startswith("/"):
            message = (
                f"Link [{link_text}]({link_url}) in an agent or command body resolves against the user's project "
                "root, not the plugin, and may dangle at runtime when the plugin is installed"
            )
            suggestion = "Link through ${CLAUDE_PLUGIN_ROOT}/... to reach a file in the plugin, or link to a URL"
        else:
            target = Path(os.path.normpath(base_dir / resolved_url))
            if target.is_relative_to(root):
                continue
            message = (
                f"Link [{link_text}]({link_url}) points outside the plugin ({target}) "
                "and may dangle at runtime when the plugin is installed"
            )
            suggestion = "If it must work once installed, move the target into the plugin or link to a URL"
        issues.append(
            _make_issue(
                field=relative_file, severity="info", message=message, code="LK004", suggestion=suggestion, line=line
            )
        )

    return issues


__all__ = ["check_lk001", "check_lk004"]
