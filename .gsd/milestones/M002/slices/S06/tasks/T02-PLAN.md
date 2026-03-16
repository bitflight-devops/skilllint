---
estimated_steps: 4
estimated_files: 1
---

# T02: Add regression integration test for external scan proof

**Slice:** S06 — External scan proof and findings report
**Milestone:** M002

## Description

Create a pytest integration test that exercises `skilllint check` via subprocess against external repos, asserting exit codes and output patterns match the S04 truth classification. Tests skip gracefully when repos are absent.

## Steps

1. Create `packages/skilllint/tests/test_external_scan_proof.py`
2. Add a helper that runs `sys.executable -m skilllint.plugin_validator check <path>` via subprocess with `PYTHONPATH` cleared (per D009)
3. Add three test functions — one per repo — each asserting:
   - Expected exit code (claude-plugins-official=1, skills=1, claude-code-plugins=0)
   - Warning-level rule codes (FM004, FM007, AS004) appear in stdout for repos that have them
   - No unexpected error-level codes beyond FM003/FM005 appear
4. Add `pytest.mark.skipif` on each test checking `os.path.isdir(repo_path)` so tests skip cleanly in CI or environments without the repos

## Must-Haves

- [ ] Tests run via `uv run pytest packages/skilllint/tests/test_external_scan_proof.py -v --no-cov`
- [ ] Exit code assertions match S04 baseline
- [ ] Tests skip gracefully when external repos are absent
- [ ] No unexpected error-level rules beyond FM003/FM005

## Verification

- `uv run pytest packages/skilllint/tests/test_external_scan_proof.py -v --no-cov` — all tests pass or skip

## Inputs

- S04 exit code baseline: claude-plugins-official=1, skills=1, claude-code-plugins=0
- S04 severity: FM003/FM005 = error, FM004/FM007/AS004 = warning
- D009: clear PYTHONPATH in subprocess for installed package isolation
- D006: use `skilllint.plugin_validator` module path for CLI entry
- T01 scan output confirms exit codes are still correct

## Expected Output

- `packages/skilllint/tests/test_external_scan_proof.py` — regression test file with 3 test functions
