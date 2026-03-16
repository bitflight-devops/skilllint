# S06 Findings Report: External Repo Scan Results

**Generated:** 2026-03-16
**Milestone:** M002 — Agentskills Linter Refactor
**Slice:** S06 — External scan proof and findings report

## Executive Summary

All three external repositories were scanned using the refactored `skilllint.plugin_validator check` CLI. Exit codes match the S04 baseline:

| Repository | Exit Code | Expected | Result |
|------------|-----------|----------|--------|
| claude-plugins-official | 1 | 1 | ✓ |
| skills | 1 | 1 | ✓ |
| claude-code-plugins | 0 | 0 | ✓ |

The linter correctly identifies genuine schema violations (FM003/FM005) as hard failures and correctly classifies style/complexity issues (FM004/FM007/SK004/etc.) as warnings.

---

## Per-Repo Breakdown

### 1. claude-plugins-official

**Exit code:** 1 (hard failures present)

| Category | Count |
|----------|-------|
| Errors (FM003/FM005) | 7 |
| Warnings | 46+ |

#### Hard Failures (FM003/FM005)

| Rule | File Path | Description |
|------|-----------|-------------|
| FM005 | `external_plugins/stripe/commands/explain-error.md` | argument-hint: Input should be a valid string |
| FM005 | `external_plugins/stripe/commands/test-cards.md` | argument-hint: Input should be a valid string |
| FM005 | `plugins/agent-sdk-dev/commands/new-sdk-app.md` | argument-hint: Input should be a valid string |
| FM003 | `plugins/skill-creator/skills/skill-creator/agents/analyzer.md` | No YAML frontmatter found |
| FM003 | `plugins/skill-creator/skills/skill-creator/agents/comparator.md` | No YAML frontmatter found |
| FM003 | `plugins/skill-creator/skills/skill-creator/agents/grader.md` | No YAML frontmatter found |

#### Warning-Level Findings (Summary)

- **FM007** (12 occurrences): Tools field uses YAML array instead of preferred CSV string
- **FM004** (7 occurrences): Multiline YAML syntax in description field
- **SK004** (10 occurrences): Description exceeds 1024 characters
- **AS004** (5 occurrences): Unquoted colons in description that may break YAML parsing
- **LK002** (8 occurrences): Internal links missing `./` prefix
- **SK006** (2 occurrences): Skill body exceeds token threshold
- **FM010** (1 occurrence): Skill name does not match directory name

---

### 2. skills

**Exit code:** 1 (hard failures present)

| Category | Count |
|----------|-------|
| Hard Failures (FM003) | 3 |
| Warnings | 8 |

#### Hard Failures (FM003)

| Rule | File Path | Issue |
|------|-----------|-------|
| FM003 | `skills/skill-creator/agents/analyzer.md` | No YAML frontmatter found |
| FM003 | `skills/skill-creator/agents/comparator.md` | No YAML frontmatter found |
| FM003 | `skills/skill-creator/agents/grader.md` | No YAML frontmatter found |

#### Warning-Level Findings (Summary)

- **SK006** (3 occurrences): Skill body exceeds token threshold
- **LK002** (4 occurrences): Internal links missing `./` prefix
- **SK005** (3 occurrences): Description missing trigger phrases

---

### 3. claude-code-plugins

**Exit code:** 0 (warnings only, no hard failures)

| Category | Count |
|----------|-------|
| Hard Failures | 0 |
| Warnings | 46 |

#### Warning-Level Findings (Summary)

- **FM004** (7 occurrences): Multiline YAML syntax in description field
- **FM007** (6 occurrences): Tools field uses YAML array instead of CSV string
- **SK004** (6 occurrences): Description exceeds 1024 characters
- **LK002** (27 occurrences): Internal links missing `./` prefix

---

## Remaining Hard Failures Summary

All remaining hard failures are legitimate schema violations that require upstream fixes:

### FM003: Missing YAML Frontmatter

These agent files appear to be markdown content without the required YAML frontmatter delimiter (`---`):

| Repository | File Path |
|------------|-----------|
| claude-plugins-official | `plugins/skill-creator/skills/skill-creator/agents/analyzer.md` |
| claude-plugins-official | `plugins/skill-creator/skills/skill-creator/agents/comparator.md` |
| claude-plugins-official | `plugins/skill-creator/skills/skill-creator/agents/grader.md` |
| skills | `skills/skill-creator/agents/analyzer.md` |
| skills | `skills/skill-creator/agents/comparator.md` |
| skills | `skills/skill-creator/agents/grader.md` |

### FM005: Invalid `argument-hint` Format

These command files have invalid `argument-hint` field values that should be CSV strings:

| Repository | File Path |
|------------|-----------|
| claude-plugins-official | `external_plugins/stripe/commands/explain-error.md` |
| claude-plugins-official | `external_plugins/stripe/commands/test-cards.md` |
| claude-plugins-official | `plugins/agent-sdk-dev/commands/new-sdk-app.md` |

---

## Human Review Recommendations

### Immediate Actions Required

1. **Fix FM003 violations**: Add YAML frontmatter to the 6 agent files in skill-creator. These files are currently invalid and cannot be loaded by Claude Code.

2. **Fix FM005 violations**: Update `argument-hint` fields in the 3 command files to use CSV string format (e.g., `'tool1, tool2, tool3'`).

### Recommended for Quality

1. **Consider fixing AS004 warnings**: Unquoted colons in descriptions may cause YAML parsing issues. Quote these field values.

2. **Consider condensing SK004 warnings**: Descriptions exceeding 1024 characters may be truncated. Front-load critical information.

3. **Evaluate SK006 warnings**: Large skill bodies may indicate opportunities to extract content to `references/` or split into multiple skills.

### Low Priority

1. **FM007 style warnings**: YAML array format for tools is valid and functional. CSV string is only a style preference.

2. **LK002 link warnings**: Internal links without `./` prefix may still resolve correctly. Consider fixing for consistency.

3. **FM004 multiline warnings**: Multiline YAML is valid. Single-line is only a readability preference.

---

## Verification

Run `bash scripts/verify-s06.sh` to verify exit codes match expected values.

The regression test in `packages/skilllint/tests/test_external_scan_proof.py` (T02) will lock these exit codes for future CI runs.
