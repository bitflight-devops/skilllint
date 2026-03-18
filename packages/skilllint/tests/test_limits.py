"""Tests for skilllint.limits module.

Tests:
- Constant values match specification sources
- Provider and RuleLimit enums have expected members
- Legacy alias constants equal the canonical values
- Token thresholds are logically ordered

How: Direct attribute and enum-member inspection.
Why: limits.py is the single source of truth for all validation thresholds;
     regressions here silently break rule enforcement without these tests.
"""

from __future__ import annotations

from skilllint.limits import (
    BODY_TOKEN_ERROR,
    BODY_TOKEN_WARNING,
    COMPATIBILITY_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    DESCRIPTION_MIN_LENGTH,
    LICENSE_MAX_LENGTH,
    MAX_SKILL_NAME_LENGTH,
    METADATA_TOKEN_BUDGET,
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
    NAME_PATTERN,
    RECOMMENDED_DESCRIPTION_LENGTH,
    TOKEN_ERROR_THRESHOLD,
    TOKEN_WARNING_THRESHOLD,
    Provider,
    RuleLimit,
)


class TestProviderEnum:
    """Tests for the Provider enumeration."""

    def test_agentskills_io_member(self) -> None:
        """Provider.AGENTSKILLS_IO has value 'agentskills.io'."""
        assert Provider.AGENTSKILLS_IO.value == "agentskills.io"

    def test_claude_code_member(self) -> None:
        """Provider.CLAUDE_CODE has value 'claude-code'."""
        assert Provider.CLAUDE_CODE.value == "claude-code"

    def test_cursor_member(self) -> None:
        """Provider.CURSOR has value 'cursor'."""
        assert Provider.CURSOR.value == "cursor"

    def test_codex_member(self) -> None:
        """Provider.CODEX has value 'codex'."""
        assert Provider.CODEX.value == "codex"

    def test_skilllint_member(self) -> None:
        """Provider.SKILL_LINT has value 'skilllint'."""
        assert Provider.SKILL_LINT.value == "skilllint"

    def test_all_providers_accounted_for(self) -> None:
        """Provider enum contains exactly the expected set of members."""
        expected = {"AGENTSKILLS_IO", "CLAUDE_CODE", "CURSOR", "CODEX", "SKILL_LINT"}
        assert {m.name for m in Provider} == expected


class TestRuleLimitEnum:
    """Tests for the RuleLimit enumeration."""

    def test_fm_name_max_length_member(self) -> None:
        """RuleLimit.FM_NAME_MAX_LENGTH is accessible."""
        assert RuleLimit.FM_NAME_MAX_LENGTH.value == "fm_name_max_length"

    def test_fm_description_max_length_member(self) -> None:
        """RuleLimit.FM_DESCRIPTION_MAX_LENGTH is accessible."""
        assert RuleLimit.FM_DESCRIPTION_MAX_LENGTH.value == "fm_desc_max_length"

    def test_body_warning_member(self) -> None:
        """RuleLimit.BODY_WARNING is accessible."""
        assert RuleLimit.BODY_WARNING.value == "body_warning"

    def test_body_error_member(self) -> None:
        """RuleLimit.BODY_ERROR is accessible."""
        assert RuleLimit.BODY_ERROR.value == "body_error"

    def test_metadata_budget_member(self) -> None:
        """RuleLimit.METADATA_BUDGET is accessible."""
        assert RuleLimit.METADATA_BUDGET.value == "metadata_budget"

    def test_sk_description_min_length_member(self) -> None:
        """RuleLimit.SK_DESCRIPTION_MIN_LENGTH is accessible."""
        assert RuleLimit.SK_DESCRIPTION_MIN_LENGTH.value == "sk_desc_min_length"


class TestFrontmatterFieldLimits:
    """Tests for frontmatter field limit constants."""

    def test_name_max_length(self) -> None:
        """NAME_MAX_LENGTH is 64 per spec."""
        assert NAME_MAX_LENGTH == 64

    def test_description_max_length(self) -> None:
        """DESCRIPTION_MAX_LENGTH is 1024 per spec."""
        assert DESCRIPTION_MAX_LENGTH == 1024

    def test_license_max_length(self) -> None:
        """LICENSE_MAX_LENGTH is 500 per spec."""
        assert LICENSE_MAX_LENGTH == 500

    def test_compatibility_max_length(self) -> None:
        """COMPATIBILITY_MAX_LENGTH is 500 per spec."""
        assert COMPATIBILITY_MAX_LENGTH == 500

    def test_name_min_length(self) -> None:
        """NAME_MIN_LENGTH is 1 per spec."""
        assert NAME_MIN_LENGTH == 1

    def test_name_pattern(self) -> None:
        """NAME_PATTERN is the expected regex string."""
        assert NAME_PATTERN == r"^[a-z0-9]+(-[a-z0-9]+)*$"

    def test_description_min_length(self) -> None:
        """DESCRIPTION_MIN_LENGTH is 20 (best practice)."""
        assert DESCRIPTION_MIN_LENGTH == 20


class TestTokenThresholds:
    """Tests for token threshold constants."""

    def test_body_token_warning(self) -> None:
        """BODY_TOKEN_WARNING is 4400."""
        assert BODY_TOKEN_WARNING == 4400

    def test_body_token_error(self) -> None:
        """BODY_TOKEN_ERROR is 8800."""
        assert BODY_TOKEN_ERROR == 8800

    def test_warning_below_error(self) -> None:
        """Warning threshold is strictly less than error threshold."""
        assert BODY_TOKEN_WARNING < BODY_TOKEN_ERROR

    def test_metadata_token_budget(self) -> None:
        """METADATA_TOKEN_BUDGET is 100."""
        assert METADATA_TOKEN_BUDGET == 100

    def test_backward_compat_aliases(self) -> None:
        """TOKEN_WARNING_THRESHOLD and TOKEN_ERROR_THRESHOLD match canonical values."""
        assert TOKEN_WARNING_THRESHOLD == BODY_TOKEN_WARNING
        assert TOKEN_ERROR_THRESHOLD == BODY_TOKEN_ERROR


class TestLegacyAliases:
    """Tests for deprecated / legacy alias constants."""

    def test_max_skill_name_length_is_40(self) -> None:
        """Legacy MAX_SKILL_NAME_LENGTH is 40 (differs from spec 64)."""
        assert MAX_SKILL_NAME_LENGTH == 40

    def test_recommended_description_length_matches_max(self) -> None:
        """RECOMMENDED_DESCRIPTION_LENGTH equals DESCRIPTION_MAX_LENGTH."""
        assert RECOMMENDED_DESCRIPTION_LENGTH == DESCRIPTION_MAX_LENGTH
