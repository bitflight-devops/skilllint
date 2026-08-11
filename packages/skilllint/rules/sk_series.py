"""SK-series skill quality rules (SK004-SK009).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects. Functions receive the parsed frontmatter dict,
the file path, and additional keyword arguments as needed.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | SK004 | Description too short or exceeds recommended length       | warning   |
    | SK005 | Description missing trigger phrases                       | warning   |
    | SK006 | Skill body exceeds token warning threshold                | warning   |
    | SK007 | Skill body exceeds token error threshold (must split)     | error     |
    | SK008 | Skill directory name violates naming convention           | error     |
    | SK009 | Plugin uses manual skill selection (informational)        | info      |
    +-------+-----------------------------------------------------------+-----------+

Import note: ValidationIssue is deferred inside each function to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from skilllint.rule_registry import rule_reference, skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

_SKILLS_SPEC_URL = "https://docs.anthropic.com/en/docs/claude-code/skills"
# Name pattern: lowercase alphanumeric with hyphens, no leading/trailing/consecutive hyphens.
# Source: skills.md — "Lowercase letters, numbers, and hyphens only (max 64 characters)"
_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Directory naming pattern: same constraints as skill name.
# Source: agentskills.io skill directory convention.
_DIR_CONVENTION_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


# ---------------------------------------------------------------------------
# SK004 — Description too short or exceeds recommended length
# ---------------------------------------------------------------------------

# Minimum length for description field.
# Source: Lint opinion — no upstream spec mandates a 20-char minimum.
# (Distinct from _spec_constants.MIN_DESCRIPTION_LENGTH = 1, which is
# the agentskills.io absolute minimum used by FM-series existence checks.)
_MIN_DESCRIPTION_LENGTH = 20


@skilllint_rule(
    "SK004",
    severity="warning",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk004(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK004 — Description too short or exceeds recommended length

    For SKILL and AGENT files, the `description` must be at least
    20 characters long. Descriptions shorter than this provide insufficient
    context for Claude Code to determine when to load the skill. Descriptions
    longer than the recommended 1024 characters may be truncated or reduce
    context efficiency.

    **Source:** Lint opinion (no upstream spec).

    **Source:** `frontmatter_core.RECOMMENDED_DESCRIPTION_LENGTH` = 1024.

    **Fix:** Write a concise, informative description between 20 and 1024
    characters. Front-load the most important information. Run
    `/plugin-creator:write-frontmatter-description` to generate an optimized
    description with proper length and trigger phrases.

    Returns:
        List of warning issues for length violations; empty when the
        description is absent, not a string, or within the allowed range.

    <!-- examples: SK004 -->
    """
    # Deferred import to break circular dependency:
    # plugin_validator imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.frontmatter_core import RECOMMENDED_DESCRIPTION_LENGTH  # noqa: PLC0415
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    if file_type not in {"skill", "agent"}:
        return []

    desc_val = frontmatter.get("description")
    if not isinstance(desc_val, str):
        return []

    issues: list[ValidationIssue] = []
    desc_len = len(desc_val)

    if desc_len < _MIN_DESCRIPTION_LENGTH:
        issues.append(
            ValidationIssue(
                field="description",
                severity="warning",
                message=f"Description too short (minimum {_MIN_DESCRIPTION_LENGTH} characters, got {desc_len})",
                code="SK004",
                docs_url=rule_reference("SK004"),
                suggestion="Run /plugin-creator:write-frontmatter-description to generate an optimized description",
            )
        )
    elif desc_len > RECOMMENDED_DESCRIPTION_LENGTH:
        issues.append(
            ValidationIssue(
                field="description",
                severity="warning",
                message=f"Exceeds recommended length of {RECOMMENDED_DESCRIPTION_LENGTH} characters (got {desc_len})",
                code="SK004",
                docs_url=rule_reference("SK004"),
                suggestion=f"Front-load critical information in first {RECOMMENDED_DESCRIPTION_LENGTH} characters. Run /plugin-creator:write-frontmatter-description to generate an optimized description",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# SK005 — Description missing trigger phrases
# ---------------------------------------------------------------------------

# Trigger phrases for skill auto-loading.
# Source: Lint opinion — no vendor spec lists required trigger phrases.
# Quality heuristic for skill discoverability.
_REQUIRED_TRIGGER_PHRASES = [
    "use when",
    "use this",
    "use on",
    "used when",
    "used by",
    "when ",
    "trigger",
    "activate",
    "load this",
    "load when",
    "invoke",
]


@skilllint_rule(
    "SK005",
    severity="warning",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk005(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK005 — Description missing trigger phrases

    Skill descriptions should include a trigger phrase that tells Claude Code
    when to load the skill. Without trigger phrases, the skill may not be
    activated at the right moment in a conversation.

    Required trigger phrases (at least one must appear):
    `use when`, `use this`, `use on`, `used when`, `used by`, `when`,
    `trigger`, `activate`, `load this`, `load when`, `invoke`.

    **Source:** Lint opinion (no upstream spec).

    **Fix:** Add a trigger phrase to the description:

    ```yaml
    description: "Use when building Python CLI tools. Provides patterns for
      argument parsing, output formatting, and error handling."
    ```

    Run `/plugin-creator:write-frontmatter-description` to generate a
    compliant description automatically.

    Returns:
        List containing one warning when no trigger phrase is found in a
        SKILL file's description; empty otherwise.

    <!-- examples: SK005 -->
    """
    # Deferred import to break circular dependency:
    # plugin_validator imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    if file_type != "skill":
        return []

    desc_val = frontmatter.get("description")
    if not isinstance(desc_val, str):
        return []

    desc_lower = desc_val.lower()
    if any(phrase in desc_lower for phrase in _REQUIRED_TRIGGER_PHRASES):
        return []

    return [
        ValidationIssue(
            field="description",
            severity="warning",
            message="Description missing trigger phrases",
            code="SK005",
            docs_url=rule_reference("SK005"),
            suggestion=f"Required trigger phrases: {', '.join(_REQUIRED_TRIGGER_PHRASES)}. Run /plugin-creator:write-frontmatter-description to generate a compliant description",
        )
    ]


# ---------------------------------------------------------------------------
# SK006 — Token count exceeds warning threshold
# ---------------------------------------------------------------------------


@skilllint_rule(
    "SK006",
    severity="warning",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk006(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK006 — Skill body exceeds token warning threshold

    The skill body is larger than Anthropic's official skills. Skills with
    very large bodies increase context consumption and may slow response
    times. Consider splitting the skill or moving content to `references/`.

    **Source:** `token_counter.TOKEN_WARNING_THRESHOLD` — sourced from
    `skilllint.token_counter` module.

    **Fix:** Review whether the content can be moved to `references/` or
    whether the skill covers multiple domains that could be separated into
    distinct skills.

    Returns:
        Always an empty list. SK006 is emitted by `ComplexityValidator` in
        `plugin_validator.py` after computing the body token count; this
        function exists for rule metadata registration only.

    <!-- examples: SK006 -->
    """
    return []


# ---------------------------------------------------------------------------
# SK007 — Token count exceeds error threshold (must split)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "SK007",
    severity="error",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk007(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK007 — Skill body exceeds token error threshold

    The skill body has grown so large that it exceeds the hard token limit.
    At this size, loading the skill risks hitting context-window limits and
    the skill must be split into multiple smaller skills.

    **Source:** `token_counter.TOKEN_ERROR_THRESHOLD` — sourced from
    `skilllint.token_counter` module.

    **Fix:** Run `/plugin-creator:refactor-skill` to split the skill into
    multiple smaller, focused skills.

    Returns:
        Always an empty list. SK007 is emitted by `ComplexityValidator` in
        `plugin_validator.py` after computing the body token count; this
        function exists for rule metadata registration only.

    <!-- examples: SK007 -->
    """
    return []


# ---------------------------------------------------------------------------
# SK008 — Skill directory name violates naming convention
# ---------------------------------------------------------------------------


@skilllint_rule(
    "SK008",
    severity="error",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk008(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK008 — Skill directory name violates naming convention

    The directory containing `SKILL.md` must follow the same naming
    convention as the `name` field: lowercase letters, digits, and hyphens
    only; no leading, trailing, or consecutive hyphens; no underscores;
    maximum 64 characters.

    **Source:** https://agentskills.io/specification.md — the spec applies
    the same 64-character limit to both the frontmatter ``name`` field and
    the skill directory name (``_spec_constants.MAX_NAME_LENGTH = 64``).

    **Fix:** Rename the skill directory to follow the convention:

    ```bash
    # Before
    skills/My_Skill/SKILL.md

    # After
    skills/my-skill/SKILL.md
    ```

    Returns:
        Always an empty list. SK008 is emitted by `_check_skill_name_and_directory`
        in `plugin_validator.py` after inspecting the filesystem path; this
        function exists for rule metadata registration only.

    <!-- examples: SK008 -->
    """
    return []


# ---------------------------------------------------------------------------
# SK009 — Plugin uses manual skill selection (informational)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "SK009",
    severity="info",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk009(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK009 — Plugin uses manual skill selection

    When the `skills` field is present in `plugin.json`, Claude Code uses
    only the explicitly listed skills and will not auto-discover new skills
    added to `skills/`. This is an `info` notice, not an error — manual
    selection is a valid configuration choice.

    **Source:** Claude Code plugin documentation — auto-discovery behaviour
    when `skills` field is omitted from `plugin.json`.

    **Fix (optional):** To switch to auto-discovery mode, remove the
    `skills` field from `plugin.json`. Claude Code will then discover all
    skills under `./skills/` automatically.

    Returns:
        Always an empty list. SK009 is emitted by `PluginRegistrationValidator`
        in `plugin_validator.py` when `plugin.json` contains a `skills` key;
        this function exists for rule metadata registration only.

    <!-- examples: SK009 -->
    """
    return []


__all__ = ["check_sk004", "check_sk005", "check_sk006", "check_sk007", "check_sk008", "check_sk009"]
