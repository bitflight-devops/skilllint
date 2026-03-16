---
id: T02
parent: S06
milestone: M002
provides:
  - Regression integration test for external scan proof
key_files:
  - packages/skilllint/tests/test_external_scan_proof.py
key_decisions:
  - Strip ANSI escape codes before parsing rule codes from output
  - Use bracket pattern `[FM003]` to extract rule codes from Rich-formatted output
patterns_established:
  - Subprocess isolation with PYTHONPATH cleared (D009) for installed package testing
  - pytest.mark.skipif for graceful test skipping when external repos absent
observability_surfaces:
  - Test output shows pass/fail per repo
  - Rule code extraction shows which codes were found in scan output
duration: 20m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Add regression integration test for external scan proof

**Created pytest integration test that exercises skilllint check via subprocess against three external repos, asserting exit codes and output patterns match S04 truth classification.**

## What Happened

Created `packages/skilllint/tests/test_external_scan_proof.py` with 9 test functions across 3 test classes:

- **TestClaudePluginsOfficial**: 3 tests — exit code 1, warning rules present, FM003/FM005 present
- **TestSkillsRepo**: 3 tests — exit code 1, FM003 errors present, no FM005 errors
- **TestClaudeCodePlugins**: 3 tests — exit code 0, no error-level rules, warning rules present

Initial test run failed because output contained ANSI escape codes. Fixed by:
1. Adding ANSI escape code pattern to strip color codes before parsing
2. Updating regex pattern to match bracketed rule codes `[FM003]` as they appear in Rich-formatted output

All 9 tests now pass. Tests skip gracefully when external repos are absent (uses `pytest.mark.skipif`).

## Verification

- `uv run pytest packages/skilllint/tests/test_external_scan_proof.py -v --no-cov` — 9 passed ✓
- `bash scripts/verify-s06.sh` — all exit codes match expected values ✓

## Diagnostics

- Run `uv run pytest packages/skilllint/tests/test_external_scan_proof.py -v --no-cov` to verify regression tests
- Run `bash scripts/verify-s06.sh` to verify exit codes directly
- Check `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` for detailed findings

## Deviations

None. Task plan executed as specified.

## Known Issues

None. All tests pass.

## Files Created/Modified

- `packages/skilllint/tests/test_external_scan_proof.py` — Created regression integration test with 9 test functions
- `.gsd/milestones/M002/slices/S06/S06-PLAN.md` — Marked T02 as done
