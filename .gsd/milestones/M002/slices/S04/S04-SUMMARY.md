---
id: S04
parent: M002
milestone: M002
provides:
  - Evidence-based rule classification for FM003, FM004, FM005, FM007, AS004
  - Severity downgrade from error to warning for runtime-accepted patterns
  - Test coverage for severity assertions
  - Findings report for human review of remaining genuine errors
requires:
  - slice: S02
    provides: ValidatorOwnership enum and VALIDATOR_OWNERSHIP mapping for schema vs lint rule ownership
  - slice: S03
    provides: Correct scan target selection for manifest-driven and structure-based discovery
affects:
  - slice: S06
key_files:
  - packages/skilllint/plugin_validator.py
  - packages/skilllint/tests/test_rule_truth.py
  - .gsd/milestones/M002/slices/S04/S04-FINDINGS.md
key_decisions:
  - FM004 (multiline YAML) downgraded to warning because Claude Code runtime accepts these patterns
  - FM007 (YAML array tools) downgraded to warning because Claude Code runtime accepts YAML arrays
  - AS004 (unquoted colons) downgraded to warning because auto-fixable and valid YAML in most contexts
  - FM003 (missing frontmatter) remains error because agents/skills/commands genuinely require frontmatter
  - FM005 (type mismatch) remains error because type mismatches are genuine schema violations
patterns_established:
  - Severity classification comment block documents evidence-based truth decisions in code
  - ValidationIssue severity and list placement (errors vs warnings) must match
  - Pydantic error handler routes warning-severity issues to warnings list, not errors list
  - Exit code 0 when only warnings present, exit code 1 only when genuine schema errors present
observability_surfaces:
  - CLI output shows WARN (⚠) vs ERROR (✗) icons per issue
  - Exit code reflects only genuine schema violations (FM003, FM005)
  - test_rule_truth.py provides regression guard for severity decisions
drill_down_paths:
  - .gsd/milestones/M002/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002/slices/S04/tasks/T02-SUMMARY.md
duration: 40m
verification_result: passed
completed_at: 2026-03-15
---

# S04: Official-repo hard-failure truth pass

**Downgraded runtime-accepted patterns from error to warning severity based on evidence from official repos; genuine schema violations remain as errors.**

## What Happened

This slice classified disputed hard failures from official-repo scans and downgraded unjustified ones from errors to warnings. The classification was evidence-based, using:
- Claude Code runtime acceptance of multiline YAML, YAML arrays, and unquoted colons
- Schema requirements for frontmatter presence and type correctness

**T01: Classify hard-failure rules and downgrade unjustified ones**
- Created rule truth classification table documenting evidence for each rule
- Changed severity from "error" to "warning" for FM004, FM007, AS004
- Kept FM003 and FM005 as "error" (genuine schema violations)
- Fixed bug where warning-severity issues were incorrectly appended to errors list
- Created `test_rule_truth.py` with 11 tests verifying severity routing

**T02: Verify official-repo scan behavior and produce findings report**
- Scanned all three official repos: claude-plugins-official, skills, claude-code-plugins
- Verified exit codes reflect only genuine schema violations
- Produced findings report documenting remaining hard failures for human review
- Added integration tests confirming severity routing in real CLI context

## Verification

```bash
# All rule truth tests pass
uv run pytest packages/skilllint/tests/test_rule_truth.py -v --no-cov
# 11 passed

# No regressions in full suite
uv run pytest packages/skilllint/tests/ -q --no-cov
# 708 passed, 1 skipped

# Exit codes reflect classification
uv run python -m skilllint.plugin_validator check ~/repos/claude-plugins-official; echo "exit: $?"
# exit: 1 (due to FM003/FM005 genuine errors)

uv run python -m skilllint.plugin_validator check ~/repos/skills; echo "exit: $?"
# exit: 1 (due to FM003 genuine errors)

uv run python -m skilllint.plugin_validator check ~/repos/claude-code-plugins; echo "exit: $?"
# exit: 0 (only warnings)
```

## Requirements Advanced

- **R018** — Detect official-repo content without unjustified schema/frontmatter hard failures
  - FM004, FM007, AS004 now produce warnings instead of errors; exit code no longer blocked by runtime-accepted patterns

- **R019** — Provide evidence-driven rule-truth evaluation for disputed constraints
  - Classification documented with evidence in code comments and findings report; each rule justified by runtime behavior or schema requirements

## Requirements Validated

- **R013** — Separate schema validation from lint-rule validation cleanly
  - Severity routing proves schema errors (FM003, FM005) vs style warnings (FM004, FM007, AS004) are cleanly separated

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None. Implementation matched the task plan exactly.

## Known Limitations

1. **FM003/FM005 errors remain in official repos** — These are genuine schema violations that should be fixed upstream. The findings report documents 9 files needing human review.

2. **Style warnings (FM004, FM007, AS004) still appear** — While no longer causing exit code 1, these warnings remain visible for maintainers who want to improve consistency.

## Follow-ups

1. **S05 docs** should reference the rule classification from this slice when teaching how to add new lint rules
2. **S06** should use the verified exit code behavior as baseline for full external scan proof
3. Upstream repos should address the 9 genuine FM003/FM005 errors documented in findings report

## Files Created/Modified

- `packages/skilllint/plugin_validator.py` — Added classification comment block; changed FM004/FM007/AS004 severity to warning; fixed warning routing to warnings list
- `packages/skilllint/tests/test_rule_truth.py` — Created new test file with 11 tests for severity assertions and integration
- `.gsd/milestones/M002/slices/S04/S04-FINDINGS.md` — Evidence-based findings report with per-repo breakdown and human review recommendations
- `packages/skilllint/tests/test_frontmatter_validator.py` — Updated test_parametrized_error_codes to expect passed=True for FM004/FM007

## Forward Intelligence

### What the next slice should know
- Exit code behavior is now trustworthy: 0 = no blocking errors, 1 = genuine schema violation
- FM004/FM007/AS004 patterns appear frequently in official repos (dozens of warnings) — this is expected behavior
- The severity routing is tested in test_rule_truth.py and should not regress

### What's fragile
- The severity classification is hardcoded in plugin_validator.py — adding new rules requires deciding severity upfront
- Warning-severity issues must be explicitly routed to `warnings` list, not `errors` list — this pattern must be followed for new rules

### Authoritative diagnostics
- Run `skilllint check <path>` and look for ⚠ vs ✗ icons
- Check exit code: 0 for warnings-only, 1 for genuine errors
- Run `pytest packages/skilllint/tests/test_rule_truth.py -v` for regression verification

### What assumptions changed
- Originally assumed FM004/FM007 were schema requirements — evidence shows they are style preferences
- Previously FM004/FM007 caused exit code 1 in official repos — now they are warnings that don't block
