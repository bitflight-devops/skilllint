---
id: T01
parent: S06
milestone: M002
provides:
  - External repo scan verification script (scripts/verify-s06.sh)
  - Structured findings report for human review
key_files:
  - scripts/verify-s06.sh
  - .gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md
key_decisions:
  - Verification script suppresses stdout to focus on exit code validation
  - Findings report categorizes all hard failures with file paths for upstream action
patterns_established:
  - Exit code assertions as regression proof for linter behavior
observability_surfaces:
  - scripts/verify-s06.sh prints per-repo exit codes and mismatch details
  - S06-FINDINGS-REPORT.md contains structured per-repo error/warning counts
duration: 15m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Run external repo scans, capture output, and write findings report

**Executed real CLI scans against three external repos and documented all findings with verification script.**

## What Happened

Ran `uv run python -m skilllint.plugin_validator check` against all three external repos. Captured full output and exit codes:

- **claude-plugins-official**: Exit code 1 (7 hard failures: 3 FM005, 3 FM003)
- **skills**: Exit code 1 (3 hard failures: all FM003)
- **claude-code-plugins**: Exit code 0 (warnings only)

All exit codes matched the S04 baseline. Created `scripts/verify-s06.sh` to automate exit code verification. Created `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` with per-repo breakdown, hard failure list, and human review recommendations.

## Verification

- `bash scripts/verify-s06.sh` exits 0 ✓
- `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` exists ✓
- Report contains per-repo breakdown with error/warning counts ✓
- All 10 hard failures documented with rule codes and file paths ✓

## Diagnostics

- Run `bash scripts/verify-s06.sh` to re-verify exit codes
- Read `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` for detailed findings
- Scan stdout shows full rule violation details (captured in task execution logs)

## Deviations

None. Task plan executed as specified.

## Known Issues

None. All remaining hard failures are legitimate upstream issues that require human review.

## Files Created/Modified

- `scripts/verify-s06.sh` — Executable bash script that runs all three external scans and asserts exit codes
- `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` — Structured findings report with per-repo breakdown and human review recommendations
