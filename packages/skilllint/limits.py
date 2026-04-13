"""Documented validation limits and planning checklist for skilllint.

This module currently centralizes constraint values that were previously spread
across validators and rule implementations. It also records the checklist used
when introducing new rules so invented constraints can be caught during review.

Long-term, structural constraints should migrate into versioned schemas with
explicit provenance; this module remains a transitional compatibility surface.
"""

# ---------------------------------------------------------------------------
# Skill Lint Limits
# ---------------------------------------------------------------------------
#
# This module is the single source of truth for all limits, thresholds,
# and constraints enforced by skilllint.
#
# IMPORTANT: Every limit MUST have a documented source. Do not add invented
# limits. Sources include:
#   - Official specifications (agentskills.io, platform docs)
#   - Platform-specific requirements (Claude Code, Cursor, Codex)
#   - Best practices with documented rationale
#
# When adding new limits:
#   1. Add to the appropriate section below
#   2. Include a source URL or reference in the docstring
#   3. Add corresponding entries to the RuleLimit enum (if applicable)
#   4. Update documentation (rule-catalog.md, README.md)
#
# ---------------------------------------------------------------------------
#
# RULE PLANNING CHECKLIST
# ---------------------------------------------------------------------------
# Before adding ANY new validation rule, complete this checklist:
#
# [ ] What is the rule checking for?
#     → e.g., "Skill name must be lowercase alphanumeric with hyphens"
#
# [ ] Which provider does this apply to?
#     → Options: agentskills.io, claude-code, cursor, codex, custom
#
# [ ] What is the authoritative source?
#     → Must include URL or spec reference:
#       - agentskills.io: https://agentskills.io/specification
#       - Claude Code: https://docs.anthropic.com/en/docs/claude-code
#       - Cursor: https://cursor.sh/docs
#       - Codex: https://platform.openai.com/docs/codex
#
# [ ] Is this a spec requirement or a best practice?
#     → Spec = hard requirement, best practice = recommendation
#
# [ ] What is the fix?
#     → e.g., "Quote the string", "Rename to lowercase", etc.
#
# [ ] Can it be auto-fixed?
#     → If yes, implement in the fix() method
#
# ---------------------------------------------------------------------------

from __future__ import annotations

from enum import Enum


class Provider(Enum):
    """Enumeration of skill rule providers.

    When creating new rules, document which provider the rule applies to
    using this enum. This tracks the authoritative source for each rule.
    """

    # Official open standard
    AGENTSKILLS_IO = "agentskills.io"

    # Platform-specific
    CLAUDE_CODE = "claude-code"
    CURSOR = "cursor"
    CODEX = "codex"

    # Custom / internal
    SKILL_LINT = "skilllint"


class RuleLimit(Enum):
    """Enum of all rule limits with their sources.

    Each entry maps a rule ID prefix to its limit category.
    Used for programmatic access to limits by rule type.
    """

    # Frontmatter limits (from agentskills.io spec)
    FM_NAME_MAX_LENGTH = "fm_name_max_length"  # agentskills.io spec
    FM_DESCRIPTION_MAX_LENGTH = "fm_desc_max_length"  # agentskills.io spec
    FM_LICENSE_MAX_LENGTH = "fm_license_max_length"  # agentskills.io spec
    FM_COMPATIBILITY_MAX_LENGTH = "fm_comp_max_length"  # agentskills.io spec

    # Skill name limits
    SK_NAME_MIN_LENGTH = "sk_name_min_length"  # agentskills.io spec
    SK_NAME_MAX_LENGTH = "sk_name_max_length"  # agentskills.io spec
    SK_NAME_PATTERN = "sk_name_pattern"  # agentskills.io spec

    # Threshold categories
    BODY_WARNING = "body_warning"
    BODY_ERROR = "body_error"
    METADATA_BUDGET = "metadata_budget"

    # Quality thresholds
    SK_DESCRIPTION_MIN_LENGTH = "sk_desc_min_length"  # Best practice


# ---------------------------------------------------------------------------
# Frontmatter Field Limits (from agentskills.io specification)
# ---------------------------------------------------------------------------
# Source: https://agentskills.io/specification

#: Maximum characters for skill name field.
#: Source: agentskills.io spec - "Max 64 characters"
NAME_MAX_LENGTH: int = 64

#: Maximum characters for description field.
#: Source: agentskills.io spec - "Max 1024 characters"
DESCRIPTION_MAX_LENGTH: int = 1024

#: Maximum characters for license field (optional).
#: Source: agentskills.io spec - "Max 500 characters"
LICENSE_MAX_LENGTH: int = 500

#: Maximum characters for compatibility field (optional).
#: Source: agentskills.io spec - "Max 500 characters"
COMPATIBILITY_MAX_LENGTH: int = 500


# ---------------------------------------------------------------------------
# Skill Name Format (from agentskills.io specification)
# ---------------------------------------------------------------------------
# Source: https://agentskills.io/specification

#: Minimum skill name length.
#: Source: agentskills.io spec - "Must be 1-64 characters"
NAME_MIN_LENGTH: int = 1

#: Regex pattern for valid skill names.
#: Source: agentskills.io spec - "Lowercase letters, numbers, and hyphens only.
#: Must not start or end with a hyphen. No consecutive hyphens."
#: Pattern: ^[a-z0-9]+(-[a-z0-9]+)*$
NAME_PATTERN: str = r"^[a-z0-9]+(-[a-z0-9]+)*$"


# ---------------------------------------------------------------------------
# Token Thresholds (from agentskills.io progressive disclosure)
# ---------------------------------------------------------------------------
# Source: https://agentskills.io/specification#progressive-disclosure
#
# The spec recommends < 5000 tokens for SKILL.md body. We use thresholds
# to warn before hitting the limit and error when exceeded.

#: Token count at which to emit a warning for large skill body.
#: Source: agentskills.io spec - "< 5000 tokens recommended"
#: We use 4400 as a warning to give headroom before hitting 5000.
BODY_TOKEN_WARNING: int = 4400

#: Token count at which to emit an error for oversized skill body.
#: Source: agentskills.io spec - "< 5000 tokens recommended"
#: We use 8800 as a hard limit (2x recommended) for critical warnings.
BODY_TOKEN_ERROR: int = 8800

#: Approximate token budget for metadata (name + description).
#: Source: agentskills.io spec - "Metadata (~100 tokens): name and description
#: loaded at startup for all skills"
METADATA_TOKEN_BUDGET: int = 100


# ---------------------------------------------------------------------------
# Quality Thresholds (best practices)
# ---------------------------------------------------------------------------

#: Minimum recommended description length for effective skill discovery.
#: Source: Best practice - descriptions under 20 chars don't provide enough
#: context for AI agents to determine relevance.
DESCRIPTION_MIN_LENGTH: int = 20


# ---------------------------------------------------------------------------
# Deprecated / Legacy Limits
# ---------------------------------------------------------------------------
# These are kept for backwards compatibility but should not be used for
# new validation logic. They may be removed in future versions.

#: Legacy description length recommendation.
#: Matches agentskills.io spec exactly.
RECOMMENDED_DESCRIPTION_LENGTH: int = DESCRIPTION_MAX_LENGTH


# ---------------------------------------------------------------------------
# AS Rules Reference
# ---------------------------------------------------------------------------
# AS (AgentSkills) rules enforce agentskills.io specification compliance.
# See: https://agentskills.io/specification
#
# Rule Source Map:
#   AS001 - Skill name format     → agentskills.io spec
#   AS002 - Name matches dir      → agentskills.io spec
#   AS003 - Description required  → agentskills.io spec
#   AS004 - YAML parsing          → YAML spec (not agentskills.io)
#   AS005 - Token limit           → agentskills.io spec
#   AS006 - Eval queries          → Best practice (not required by spec)
#
# IMPORTANT: AS004 and AS006 are NOT from the agentskills.io spec:
#   - AS004: Detects unquoted colons that break YAML parsing
#   - AS006: Recommends eval_queries.json for quality testing
# These are skilllint-specific heuristics, not spec requirements.


# ---------------------------------------------------------------------------
# Token Threshold Aliases (for backwards compatibility)
# ---------------------------------------------------------------------------
# These are kept for import compatibility with existing code.

TOKEN_WARNING_THRESHOLD: int = BODY_TOKEN_WARNING
TOKEN_ERROR_THRESHOLD: int = BODY_TOKEN_ERROR
