---
estimated_steps: 4
estimated_files: 3
---

# T02: Verify official-repo scan behavior and produce findings report

**Slice:** S04 — Official-repo hard-failure truth pass
**Milestone:** M002

## Description

Run real CLI scans against the three official repos to verify that severity downgrades work correctly, then produce a findings report documenting remaining hard failures and downgraded warnings for human review.

## Steps

1. Run `uv run python -m skilllint.plugin_validator check /home/ubuntulinuxqa2/repos/claude-plugins-official --no-color` and capture full output + exit code. Do the same for `/home/ubuntulinuxqa2/repos/skills` and `/home/ubuntulinuxqa2/repos/claude-code-plugins`.

2. Analyze results:
   - FM004, FM007, AS004 findings should now appear as WARN, not ERROR
   - FM003 findings should remain as ERROR (agents without frontmatter)
   - Check exit codes — repos should exit 0 if only warnings remain, or exit 1 only if justified errors (FM003, FM005) remain

3. Write `.gsd/milestones/M002/slices/S04/S04-FINDINGS.md` documenting:
   - Per-repo summary: total findings, errors vs warnings, exit code
   - Remaining justified hard failures (FM003 instances — list the files)
   - Downgraded warnings (FM004, FM007, AS004 — count by rule)
   - Any unexpected results or edge cases discovered
   - Recommendation for human review of remaining errors

4. Add an integration-level test to `packages/skilllint/tests/test_rule_truth.py` that validates severity routing using an existing fixture file (e.g., `packages/skilllint/tests/fixtures/claude_code/valid_skill.md` should produce no errors). If a fixture with FM004/FM007 patterns exists, verify it produces warnings not errors.

## Must-Haves

- [ ] All three official repos scanned with real CLI
- [ ] FM004/FM007/AS004 appear as warnings in output
- [ ] Exit codes reflect only justified errors
- [ ] S04-FINDINGS.md written with per-repo breakdown
- [ ] Integration test added verifying severity routing with fixtures

## Verification

- `uv run python -m skilllint.plugin_validator check /home/ubuntulinuxqa2/repos/claude-plugins-official --no-color; echo "exit: $?"` — exit code matches expectations
- `uv run pytest packages/skilllint/tests/test_rule_truth.py -v --no-cov` — all tests pass

## Inputs

- T01 output: `packages/skilllint/plugin_validator.py` with severity downgrades applied
- T01 output: `packages/skilllint/tests/test_rule_truth.py` with classification tests
- Official repos at: `/home/ubuntulinuxqa2/repos/claude-plugins-official`, `/home/ubuntulinuxqa2/repos/skills`, `/home/ubuntulinuxqa2/repos/claude-code-plugins`

## Expected Output

- `.gsd/milestones/M002/slices/S04/S04-FINDINGS.md` — evidence-based findings report for human review
- `packages/skilllint/tests/test_rule_truth.py` — extended with integration test
