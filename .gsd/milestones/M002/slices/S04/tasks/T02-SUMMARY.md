---
id: T02
parent: S04
milestone: M002
provides:
  - Official-repo scan results confirming severity downgrades
  - Findings report for human review of remaining errors
  - Integration tests for severity routing
key_files:
  - .gsd/milestones/M002/slices/S04/S04-FINDINGS.md
  - packages/skilllint/tests/test_rule_truth.py
key_decisions:
  - Exit codes now reflect only genuine schema violations (FM003, FM005)
  - FM004/FM007/AS004 patterns confirmed as warnings via real CLI scans
  - Integration tests added to prevent severity routing regressions
patterns_established:
  - Integration tests use both fixture files and inline content
  - Findings report documents per-repo exit codes and error/warning counts
  - Severity routing verified via both test assertions and CLI exit codes
observability_surfaces:
  - CLI exit code 1 only when genuine schema errors present
  - S04-FINDINGS.md provides human-readable breakdown
  - test_rule_truth.py integration tests lock severity routing behavior
duration: 15m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Verify official-repo scan behavior and produce findings report

**Ran CLI scans against three official repos, confirmed FM004/FM007/AS004 appear as warnings, and produced findings report documenting remaining hard failures for human review.**

## What Happened

1. **Scanned all three official repos** with `uv run python -m skilllint.plugin_validator check`:
   - `claude-plugins-official`: Exit 1 (6 errors: 3 FM003 + 3 FM005)
   - `skills`: Exit 1 (3 errors: FM003 only)
   - `claude-code-plugins`: Exit 0 (only warnings)

2. **Verified severity classifications**:
   - FM004 (multiline YAML) → ⚠ WARN ✓
   - FM007 (tools as YAML array) → ⚠ WARN ✓
   - AS004 (unquoted colons) → ⚠ WARN ✓
   - FM003 (missing frontmatter) → ✗ ERROR ✓
   - FM005 (type mismatch) → ✗ ERROR ✓

3. **Wrote findings report** at `.gsd/milestones/M002/slices/S04/S04-FINDINGS.md`:
   - Per-repo summary with exit codes and error/warning counts
   - List of remaining justified hard failures with file paths
   - Count of downgraded warnings by rule
   - Recommendations for human review

4. **Added integration tests** to `test_rule_truth.py`:
   - `test_valid_skill_fixture_produces_no_errors` — fixture validation
   - `test_fm004_fm007_patterns_route_to_warnings_not_errors` — combined FM004/FM007 test
   - `test_as004_patterns_route_to_warnings_not_errors` — AS004 routing
   - `test_fm003_missing_frontmatter_remains_error` — confirms FM003 stays error

## Verification

```bash
# All rule truth tests pass
uv run pytest packages/skilllint/tests/test_rule_truth.py -v --no-cov
# 11 passed

# No regressions in full suite
uv run pytest packages/skilllint/tests/ -q --no-cov
# 708 passed, 1 skipped

# Exit codes reflect classification
uv run python -m skilllint.plugin_validator check ~/repos/claude-plugins-official --no-color; echo "exit: $?"
# exit: 1 (due to FM003/FM005 genuine errors)

uv run python -m skilllint.plugin_validator check ~/repos/claude-code-plugins --no-color; echo "exit: $?"
# exit: 0 (only warnings)
```

## Diagnostics

- Run `skilllint check <repo-path>` to see WARN vs ERROR classification
- Check S04-FINDINGS.md for per-repo breakdown of remaining errors
- Run `pytest packages/skilllint/tests/test_rule_truth.py::TestSeverityRoutingIntegration -v` for integration verification

## Deviations

None. Implementation matched the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `.gsd/milestones/M002/slices/S04/S04-FINDINGS.md` — Evidence-based findings report with per-repo summary, error listings, and human review recommendations
- `packages/skilllint/tests/test_rule_truth.py` — Added `TestSeverityRoutingIntegration` class with 4 integration tests
- `.gsd/milestones/M002/slices/S04/S04-PLAN.md` — Marked T02 as complete
