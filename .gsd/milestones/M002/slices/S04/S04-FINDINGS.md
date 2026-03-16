# S04 Findings: Official-Repo Hard-Failure Truth Pass

**Date:** 2026-03-15
**Milestone:** M002
**Slice:** S04

## Executive Summary

After downgrading FM004, FM007, and AS004 from error to warning severity (T01), the three official repos now exit with codes that reflect only genuine schema violations. Runtime-accepted patterns are surfaced as warnings rather than blocking the build.

## Per-Repo Summary

### 1. claude-plugins-official

| Metric | Value |
|--------|-------|
| **Exit Code** | 1 |
| **Errors** | 6 (FM003: 3, FM005: 3) |
| **Warnings** | 56 (multiple rules) |
| **Files Scanned** | ~100+ |

**Justified Hard Failures (ERROR):**

| Rule | Count | Files |
|------|-------|-------|
| FM003 | 3 | `skill-creator/agents/analyzer.md`, `skill-creator/agents/comparator.md`, `skill-creator/agents/grader.md` |
| FM005 | 3 | `stripe/commands/explain-error.md`, `stripe/commands/test-cards.md`, `agent-sdk-dev/commands/new-sdk-app.md` |

**Downgraded Warnings (formerly ERROR):**

| Rule | Count | Description |
|------|-------|-------------|
| FM004 | 5 | Multiline YAML syntax |
| FM007 | 12 | Tools field as YAML array |
| AS004 | 6 | Unquoted colons in description |

**Other Warnings:** SK004 (description length), SK006 (complexity), LK002 (internal links), FM010 (name mismatch), SK005 (missing triggers)

### 2. skills

| Metric | Value |
|--------|-------|
| **Exit Code** | 1 |
| **Errors** | 3 (FM003 only) |
| **Warnings** | 12 |
| **Files Scanned** | ~15 |

**Justified Hard Failures (ERROR):**

| Rule | Count | Files |
|------|-------|-------|
| FM003 | 3 | `skill-creator/agents/analyzer.md`, `skill-creator/agents/comparator.md`, `skill-creator/agents/grader.md` |

**Downgraded Warnings:** None in this repo (no FM004/FM007/AS004 patterns found)

**Other Warnings:** SK006 (complexity), SK005 (missing triggers), LK002 (internal links)

### 3. claude-code-plugins

| Metric | Value |
|--------|-------|
| **Exit Code** | 0 |
| **Errors** | 0 |
| **Warnings** | 58 |
| **Files Scanned** | 15 |

**Justified Hard Failures (ERROR):** None

**Downgraded Warnings (formerly ERROR):**

| Rule | Count | Description |
|------|-------|-------------|
| FM004 | 9 | Multiline YAML syntax |
| FM007 | 8 | Tools field as YAML array |

**Other Warnings:** SK004 (description length), LK002 (internal links)

## Severity Classification Results

### Confirmed ERROR (justified hard failures)

| Rule | Rationale | Status |
|------|-----------|--------|
| FM003 | Frontmatter is required for agents/skills/commands to function | ✅ Correct |
| FM005 | Type mismatches are genuine schema violations | ✅ Correct |

### Confirmed WARNING (runtime-accepted patterns)

| Rule | Rationale | Status |
|------|-----------|--------|
| FM004 | Claude Code runtime accepts multiline YAML syntax | ✅ Correct |
| FM007 | Claude Code runtime accepts YAML arrays for tools | ✅ Correct |
| AS004 | Auto-fixable by quoting; valid YAML in most contexts | ✅ Correct |

## Exit Code Behavior

| Repo | Exit Code | Reason |
|------|-----------|--------|
| claude-plugins-official | 1 | FM003 (3) + FM005 (3) genuine errors |
| skills | 1 | FM003 (3) genuine errors |
| claude-code-plugins | 0 | Only warnings present |

**Conclusion:** Exit codes now correctly reflect only genuine schema violations. Files with FM004/FM007/AS004 warnings do not cause hard failures.

## Unexpected Results

1. **FM005 in stripe/commands/*.md**: The `argument-hint` field is receiving a nested object when a string is expected. This is a legitimate schema error — the field definition expects a string, not an object.

2. **Duplicate FM003 in skills repo**: The same `skill-creator/agents/` files exist in both `claude-plugins-official` and `skills` repos. These are likely copies or symlinks.

## Recommendations for Human Review

### Priority 1: FM003 Genuine Errors (6 files)

These agents have no frontmatter and will not function in Claude Code:

1. `claude-plugins-official/plugins/skill-creator/skills/skill-creator/agents/analyzer.md`
2. `claude-plugins-official/plugins/skill-creator/skills/skill-creator/agents/comparator.md`
3. `claude-plugins-official/plugins/skill-creator/skills/skill-creator/agents/grader.md`
4. `skills/skills/skill-creator/agents/analyzer.md`
5. `skills/skills/skill-creator/agents/comparator.md`
6. `skills/skills/skill-creator/agents/grader.md`

**Action Required:** Add frontmatter with required fields (name, description) or remove these files if they are not meant to be agents.

### Priority 2: FM005 Genuine Errors (3 files)

Schema violations in `argument-hint` field:

1. `claude-plugins-official/external_plugins/stripe/commands/explain-error.md`
2. `claude-plugins-official/external_plugins/stripe/commands/test-cards.md`
3. `claude-plugins-official/plugins/agent-sdk-dev/commands/new-sdk-app.md`

**Action Required:** Fix the `argument-hint` field to be a string value, not a nested object.

### Priority 3: Warnings (Optional Review)

The FM004, FM007, and AS004 warnings are style preferences and do not block validation. These can be addressed over time to improve consistency.

## Verification Commands

```bash
# Verify severity classification
uv run python -m skilllint.plugin_validator check ~/repos/claude-plugins-official --no-color; echo "exit: $?"
# Expected: exit 1 (due to FM003/FM005 errors)

uv run python -m skilllint.plugin_validator check ~/repos/skills --no-color; echo "exit: $?"
# Expected: exit 1 (due to FM003 errors)

uv run python -m skilllint.plugin_validator check ~/repos/claude-code-plugins --no-color; echo "exit: $?"
# Expected: exit 0 (only warnings)

# Verify severity tests pass
uv run pytest packages/skilllint/tests/test_rule_truth.py -v --no-cov
```

## Observability Impact

- CLI output shows WARN (⚠) vs ERROR (✗) icons per issue
- Exit code 1 only when genuine schema errors remain
- `result.warnings` list contains FM004/FM007/AS004 issues
- `result.errors` list contains FM003/FM005 issues
