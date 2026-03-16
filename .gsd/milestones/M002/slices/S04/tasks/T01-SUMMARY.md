---
id: T01
parent: S04
milestone: M002
provides:
  - Rule truth classification for FM003, FM004, FM005, FM007, AS004
  - Severity downgrade for runtime-accepted patterns (FM004, FM007, AS004)
  - Test coverage for severity assertions
key_files:
  - packages/skilllint/plugin_validator.py
  - packages/skilllint/tests/test_rule_truth.py
key_decisions:
  - FM004/FM007/AS004 downgraded to warning because Claude Code runtime accepts these patterns
  - FM003/FM005 remain as errors because they are genuine schema violations
  - Warning-severity issues appended to warnings list, not errors list (passed=True when only warnings)
patterns_established:
  - Severity classification comment block documents evidence-based truth decisions
  - ValidationIssue severity and list placement (errors vs warnings) must match
  - Pydantic error handler routes warning-severity issues to warnings list
observability_surfaces:
  - CLI output shows WARN vs ERROR icons per issue
  - Exit code 1 only when genuine schema errors remain (FM003, FM005)
  - test_rule_truth.py provides regression guard for severity decisions
duration: 25m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Classify hard-failure rules and downgrade unjustified ones

**Downgraded FM004, FM007, AS004 from error to warning severity based on evidence from official repos; FM003 and FM005 remain as errors.**

## What Happened

The task reclassified rule severities based on evidence from official repos (claude-plugins-official, claude-code-plugins, skills):

1. **FM004 (multiline YAML)**: Changed from error to warning. Claude Code runtime accepts multiline YAML syntax (`|`, `>`, `|-`, `>-`). This is a style preference, not a schema requirement.

2. **FM007 (YAML array tools)**: Changed from error to warning. Claude Code runtime accepts YAML arrays for tools fields. This is a format preference, not a hard requirement.

3. **AS004 (unquoted colons)**: Changed from error to warning. When the YAML can be auto-fixed by quoting, it's a style issue rather than a hard failure. Also changed the code to continue validation with the fixed YAML instead of terminating early.

4. **FM003 (missing frontmatter)**: Kept as error. Agents/skills/commands genuinely require frontmatter to function.

5. **FM005 (type mismatch)**: Kept as error. Type mismatches are genuine schema violations.

Implementation details:
- Added classification comment block in `plugin_validator.py` documenting evidence-based truth decisions
- Fixed issue where warning-severity issues were being appended to `errors` list instead of `warnings`
- Updated `_check_list_valued_tool_fields` to take `warnings` parameter
- Updated Pydantic error handler to route warning-severity issues to `warnings` list
- Fixed `test_parametrized_error_codes` test that expected FM004/FM007 to fail validation

## Verification

```bash
# New tests pass
uv run pytest packages/skilllint/tests/test_rule_truth.py -v --no-cov
# 7 passed

# No regressions
uv run pytest packages/skilllint/tests/ -q --no-cov
# 704 passed, 1 skipped

# Official repo scan shows correct classification
uv run python -m skilllint.plugin_validator check ~/repos/claude-plugins-official --no-color
# Exit code: 1 (due to genuine errors: FM003, FM005)
# FM004/FM007/AS004 show as "⚠ WARN"
# FM003/FM005 show as "✗ ERROR"
```

## Diagnostics

- Run `skilllint check <path>` to see WARN vs ERROR classification
- Check `result.warnings` list for FM004/FM007/AS004 issues
- Check `result.errors` list for FM003/FM005 issues
- Exit code 0 when only warnings, exit code 1 when genuine errors present

## Deviations

None. Implementation matched the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `packages/skilllint/plugin_validator.py` — Added classification comment block; changed FM004/FM007/AS004 severity to warning; fixed warning-severity issues to append to warnings list instead of errors; updated `_check_list_valued_tool_fields` signature; updated Pydantic error handler routing
- `packages/skilllint/tests/test_rule_truth.py` — Created new test file with severity assertions for FM003/FM004/FM005/FM007/AS004
- `packages/skilllint/tests/test_frontmatter_validator.py` — Updated `test_parametrized_error_codes` to expect `passed=True` for FM004/FM007 (now warnings)
- `.gsd/milestones/M002/slices/S04/tasks/T01-PLAN.md` — Added Observability Impact section
