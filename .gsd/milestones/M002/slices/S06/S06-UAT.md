# S06 UAT: External scan proof and findings report

**Milestone:** M002
**Slice:** S06
**UAT Type:** live-runtime + artifact-driven
**Why this mode is sufficient:** This slice requires proving that the real CLI produces correct exit codes and produces a human-reviewable findings report. We verify both the command execution (live-runtime) and the report contents (artifact-driven).

## Preconditions

1. The skilllint package must be installed or runnable via `uv run`
2. External repos must be present at expected paths relative to the linter repo:
   - `../claude-plugins-official` — exists and contains plugins
   - `../skills` — exists and contains skills
   - `../claude-code-plugins` — exists and contains plugins

## Smoke Test

Quick verification that the verification script runs without error:

```bash
bash scripts/verify-s06.sh
```

**Expected:** All three repos report "✓ OK" and final message says "All exit codes match expected values."

## Test Cases

### 1. External scan verification script runs successfully

1. Run `bash scripts/verify-s06.sh`
2. **Expected:** Script exits with code 0, output shows:
   - `claude-plugins-official: Exit code: 1 (expected: 1) ✓ OK`
   - `skills: Exit code: 1 (expected: 1) ✓ OK`
   - `claude-code-plugins: Exit code: 0 (expected: 0) ✓ OK`

### 2. Regression tests pass

1. Run `uv run pytest packages/skilllint/tests/test_external_scan_proof.py -v --no-cov`
2. **Expected:** All 9 tests pass (3 test classes × 3 tests each)

### 3. Findings report exists and is structured

1. Check that `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` exists
2. Open the file and verify it contains:
   - Executive summary table with exit codes
   - Per-repo breakdown sections
   - Hard failures table with rule codes and file paths
   - Human review recommendations
3. **Expected:** Report exists, is non-empty, and contains all expected sections

### 4. Exit code 1 for repos with hard failures

1. Run `uv run python -m skilllint.plugin_validator check ../claude-plugins-official; echo "Exit: $?"`
2. Run `uv run python -m skilllint.plugin_validator check ../skills; echo "Exit: $?"`
3. **Expected:** Both exit with code 1 (hard failures present)

### 5. Exit code 0 for clean repo

1. Run `uv run python -m skilllint.plugin_validator check ../claude-code-plugins; echo "Exit: $?"`
2. **Expected:** Exit with code 0 (warnings only, no hard failures)

### 6. Hard failures are correctly classified

1. Scan output for claude-plugins-official contains `FM003` or `FM005` errors
2. Scan output for skills contains `FM003` errors
3. Scan output for claude-code-plugins contains NO error-level rules
4. **Expected:** Error classification matches S04 baseline (FM003/FM005 = error, FM004/FM007/AS004 = warning)

### 7. Warning-level findings are present in output

1. Run scan against any repo and check output contains warning-level rule codes (FM004, FM007, SK004, AS004, etc.)
2. **Expected:** Warnings appear in output as expected per S04 classification

## Edge Cases

### External repo not present

If an external repo is not present at the expected path, tests should skip gracefully:

1. Run `uv run pytest packages/skilllint/tests/test_external_scan_proof.py -v --no-cov`
2. **Expected:** Tests skip rather than fail if external repos are missing (uses `pytest.mark.skipif`)

### Unexpected exit code mismatch

If exit codes don't match expected values:

1. Run `bash scripts/verify-s06.sh`
2. Check which repo has mismatch (script prints "expected: X vs actual: Y")
3. Investigate whether the linter behavior changed or upstream content changed

## Failure Signals

- `verify-s06.sh` exits 1 → Exit code mismatch detected
- `pytest` shows failed tests → Regression test caught behavioral change
- Findings report missing or empty → Task T01 did not complete properly
- Hard failures appear for previously clean repos → Linter may be adding false positives

## Requirements Proved By This UAT

- **R024** — Prove behavior through real CLI scans on external repos: Verified by test cases 1, 2, 4, 5
- **R025** — Preserve user-facing CLI scan behavior while refactoring internals: Verified by test cases 1, 2, 4, 5 (exit codes match baseline)
- **R018** — Detect official-repo content without unjustified schema/frontmatter hard failures: Verified by test case 6 (hard failures are FM003/FM005 only, no unjustified errors)

## Not Proven By This UAT

- Autofix behavior correctness (R029) — explicitly out of scope per D010
- Codex or OpenCode compatibility (R026, R027) — deferred to later milestones

## Notes for Tester

1. The verification script suppresses stdout to focus on exit code validation — this is intentional to keep output clean
2. Regression tests include ANSI escape code stripping because Rich-formatted output contains color codes
3. The 10 remaining hard failures are documented findings, not linter bugs — they require upstream fixes in the external repos
4. If tests fail after this UAT passes, the most likely cause is upstream content changes in external repos (new violations added or fixed)
