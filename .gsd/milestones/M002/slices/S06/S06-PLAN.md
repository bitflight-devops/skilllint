# S06: External scan proof and findings report

**Goal:** Real CLI scans against official external repos serve as regression proof for correct detection, and remaining findings are clearly reported for human review.
**Demo:** `uv run python -m skilllint.plugin_validator check ../claude-plugins-official`, `../skills`, and `../claude-code-plugins` produce expected exit codes and a reviewable findings report exists.

## Must-Haves

- Real `uv run skilllint check` executions against all three external repos with correct exit codes
- A findings report documenting per-repo results, remaining hard failures, and warning-level findings
- A regression integration test that exercises the real CLI path against external repos
- No unjustified schema/frontmatter hard failures (per S04 classification)

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes
- Human/UAT required: yes — human reviews the findings report to decide on remaining upstream issues

## Verification

- `uv run pytest packages/skilllint/tests/test_external_scan_proof.py -v --no-cov` — regression tests pass
- `bash scripts/verify-s06.sh` — runs all three external scans and checks exit codes
- Findings report exists at `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md`
- `bash scripts/verify-s06.sh` prints per-repo exit codes to stdout for diagnostic inspection; on failure, outputs mismatched repo and expected vs actual code

## Observability / Diagnostics

- **Runtime signals:** Each scan writes stdout to console; verify-s06.sh echoes per-repo exit code
- **Inspection surfaces:** Findings report (`.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md`) contains structured per-repo error/warning counts, file paths, and rule codes
- **Failure visibility:** If verify-s06.sh fails, it prints which repo had unexpected exit code (expected vs actual) and exits 1
- **Redaction constraints:** No secrets involved; file paths and rule codes are non-sensitive

## Integration Closure

- Upstream surfaces consumed: S04 severity classification (FM003/FM005 = error, FM004/FM007/AS004 = warning), S05 maintainer docs
- New wiring introduced in this slice: regression test file, verification script
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [x] **T01: Run external repo scans, capture output, and write findings report** `est:30m`
  - Why: Provides the empirical proof that the refactored linter produces correct detection on real ecosystem content
  - Files: `scripts/verify-s06.sh`, `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md`
  - Do: Run `uv run python -m skilllint.plugin_validator check` against all three external repos. Capture full output. Verify exit codes match S04 baseline (claude-plugins-official=1, skills=1, claude-code-plugins=0). Write findings report with per-repo breakdown of errors vs warnings. Create `scripts/verify-s06.sh` that automates the exit code checks.
  - Verify: `bash scripts/verify-s06.sh` exits 0
  - Done when: All three scans produce expected exit codes and findings report documents every remaining hard failure with its rule code

- [x] **T02: Add regression integration test for external scan proof** `est:20m`
  - Why: Locks the external scan behavior as a regression test so future changes cannot silently break detection
  - Files: `packages/skilllint/tests/test_external_scan_proof.py`
  - Do: Create pytest test file that runs `skilllint check` via subprocess against each external repo. Assert exit codes match S04 classification. Assert warning-level rules (FM004/FM007/AS004) appear in output. Assert no unexpected error-level rules beyond FM003/FM005. Skip tests gracefully if external repos are not present.
  - Verify: `uv run pytest packages/skilllint/tests/test_external_scan_proof.py -v --no-cov`
  - Done when: All tests pass and cover all three external repos

## Files Likely Touched

- `scripts/verify-s06.sh`
- `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md`
- `packages/skilllint/tests/test_external_scan_proof.py`
