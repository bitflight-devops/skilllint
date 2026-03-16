# S06: External scan proof and findings report

**Milestone:** M002 — Validator Decomposition and Scan-Truth Hardening
**Slice:** S06 — External scan proof and findings report
**Completed:** 2026-03-16

## One-Liner

Real CLI scans against external repos serve as regression proof for correct detection, with a findings report documenting all remaining hard failures for human review.

## What Happened

S06 completed the milestone by proving that all the architectural refactoring and rule classification from S01-S05 works correctly when invoked through the real CLI path. Two tasks executed:

**T01: External repo scans and findings report**
- Ran `uv run python -m skilllint.plugin_validator check` against three external repos:
  - `../claude-plugins-official`: Exit code 1 (7 hard failures: 3 FM005, 3 FM003)
  - `../skills`: Exit code 1 (3 hard failures: all FM003)
  - `../claude-code-plugins`: Exit code 0 (warnings only)
- All exit codes matched S04 baseline expectations
- Created `scripts/verify-s06.sh` to automate exit code verification
- Created `S06-FINDINGS-REPORT.md` with structured per-repo breakdown

**T02: Regression integration tests**
- Created `packages/skilllint/tests/test_external_scan_proof.py` with 9 test functions
- Tests verify exit codes match baseline, error-level rules present, warning-level rules present
- Initial test run failed due to ANSI escape codes in Rich output — fixed by stripping color codes before parsing
- All 9 tests now pass

## Verification

- `bash scripts/verify-s06.sh` exits 0 ✓
- `uv run pytest packages/skilllint/tests/test_external_scan_proof.py -v --no-cov` — 9 passed ✓
- Findings report exists with all 10 hard failures documented ✓
- No unjustified schema/frontmatter hard failures (per S04 classification) ✓

## Requirements Advanced

- **R024** — Prove behavior through real CLI scans on external repos: Validated with real `uv run skilllint check ...` against three external repos
- **R025** — Preserve user-facing CLI scan behavior while refactoring internals: Proved with exit code assertions matching baseline

## Requirements Validated

- **R018** — Detect official-repo content without unjustified schema/frontmatter hard failures: Verified — all 10 hard failures are justified (FM003 missing frontmatter, FM005 invalid argument-hint format)
- **R019** — Provide evidence-driven rule-truth evaluation for disputed constraints: Findings report documents each hard failure with rule code, file path, and upstream action recommendation

## New Requirements Surfaced

None. The findings are consistent with S04 classification.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None. Task plans executed as specified.

## Known Limitations

The remaining 10 hard failures are legitimate upstream issues requiring human review:

- **6 FM003 violations**: Missing YAML frontmatter in skill-creator agent files (both repos)
- **3 FM005 violations**: Invalid `argument-hint` format in stripe and agent-sdk-dev commands

These are genuine schema violations that prevent files from functioning correctly as Claude Code skills/commands.

## Follow-ups

None. This is the final slice of M002. The remaining hard failures should be addressed by upstream maintainers of the external repos.

## Files Created/Modified

- `scripts/verify-s06.sh` — Executable bash script that runs all three external scans and asserts exit codes match expected values
- `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` — Structured findings report with per-repo breakdown, hard failure list with file paths, and human review recommendations
- `packages/skilllint/tests/test_external_scan_proof.py` — Regression integration test with 9 test functions covering all three external repos
- `.gsd/milestones/M002/slices/S06/S06-PLAN.md` — Updated to mark T01 and T02 as complete

## Forward Intelligence

### What the next slice should know

This is the final slice of M002. The milestone is complete when this slice passes verification. All remaining hard failures are documented findings that require human review — they are not bugs in the linter.

### What's fragile

- The external repo paths are hardcoded as relative paths from the linter repo (`../claude-plugins-official`, `../skills`, `../claude-code-plugins`). If these repos move, the verification script and tests will need updates.

### Authoritative diagnostics

- `bash scripts/verify-s06.sh` — Exit code validation (exits 0 on success)
- `uv run pytest packages/skilllint/tests/test_external_scan_proof.py -v --no-cov` — Full regression test suite
- `S06-FINDINGS-REPORT.md` — Human-readable breakdown of all findings

### What assumptions changed

None. The S04 classification held up under real-world scanning.
