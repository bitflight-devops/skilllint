# S04-UAT: Official-repo hard-failure truth pass

**Milestone:** M002
**Slice:** S04
**Written:** 2026-03-15

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: This slice modifies severity routing and exit code behavior — both require real CLI execution against actual external repos to verify. Unit tests alone cannot prove runtime behavior.

## Preconditions

```bash
# Must have the three official repos available
ls -la /home/ubuntulinuxqa2/repos/claude-plugins-official
ls -la /home/ubuntulinuxqa2/repos/skills
ls -la /home/ubuntulinuxqa2/repos/claude-code-plugins
```

## Smoke Test

```bash
# Quick check that skilllint runs without crashing
uv run python -m skilllint.plugin_validator check /home/ubuntulinuxqa2/repos/claude-code-plugins --no-color; echo "exit: $?"
# Expected: exit 0 (no blocking errors)
```

## Test Cases

### 1. Verify FM004 (multiline YAML) is WARNING, not ERROR

1. Run: `uv run python -m skilllint.plugin_validator check /home/ubuntulinuxqa2/repos/claude-plugins-official --no-color`
2. Search output for "FM004" 
3. **Expected:** Lines contain "⚠ WARN [FM004]" not "✗ ERROR [FM004]"
4. **Expected:** Exit code is 1 (due to FM003/FM005), not blocked by FM004

### 2. Verify FM007 (YAML array tools) is WARNING, not ERROR

1. Run: `uv run python -m skilllint.plugin_validator check /home/ubuntulinuxqa2/repos/claude-plugins-official --no-color`
2. Search output for "FM007"
3. **Expected:** Lines contain "⚠ WARN [FM007]" not "✗ ERROR [FM007]"

### 3. Verify AS004 (unquoted colons) is WARNING, not ERROR

1. Run: `uv run python -m skilllint.plugin_validator check /home/ubuntulinuxqa2/repos/claude-plugins-official --no-color`
2. Search output for "AS004"
3. **Expected:** Lines contain "⚠ WARN [AS004]" not "✗ ERROR [AS004]"

### 4. Verify FM003 (missing frontmatter) remains ERROR

1. Run: `uv run python -m skilllint.plugin_validator check /home/ubuntulinuxqa2/repos/skills --no-color`
2. Search output for "FM003"
3. **Expected:** Lines contain "✗ ERROR [FM003]"
4. **Expected:** Exit code is 1 (blocked by FM003)

### 5. Verify FM005 (type mismatch) remains ERROR

1. Run: `uv run python -m skilllint.plugin_validator check /home/ubuntulinuxqa2/repos/claude-plugins-official --no-color`
2. Search output for "FM005"
3. **Expected:** Lines contain "✗ ERROR [FM005]"
4. **Expected:** Exit code is 1 (blocked by FM005)

### 6. Verify claude-code-plugins exits 0 (only warnings)

1. Run: `uv run python -m skilllint.plugin_validator check /home/ubuntulinuxqa2/repos/claude-code-plugins --no-color; echo "exit: $?"`
2. **Expected:** exit code is 0 (no genuine errors)
3. **Expected:** Output contains warnings but no errors

### 7. Verify severity routing in test suite

1. Run: `uv run pytest packages/skilllint/tests/test_rule_truth.py -v --no-cov`
2. **Expected:** 11 tests pass
3. **Expected:** No skipped tests

### 8. Verify no regressions in full test suite

1. Run: `uv run pytest packages/skilllint/tests/ -q --no-cov`
2. **Expected:** 708 passed, 1 skipped

## Edge Cases

### Edge Case: Multiple errors in same file

1. Create a test file with both FM003 (missing frontmatter) and FM007 (YAML array)
2. Run: `uv run python -m skilllint.plugin_validator check <test-file> --no-color`
3. **Expected:** FM003 shows as ERROR, FM007 shows as WARNING
4. **Expected:** Exit code is 1 (blocked by FM003 error)

### Edge Case: Only warnings present

1. Create a test file with only FM004 (multiline YAML) or FM007 (YAML array)
2. Run: `uv run python -m skilllint.plugin_validator check <test-file> --no-color`
3. **Expected:** Only WARNING icons shown
4. **Expected:** Exit code is 0 (no blocking errors)

## Failure Signals

- Exit code 1 when only FM004/FM007/AS004 warnings present → regression in severity routing
- Exit code 0 when FM003/FM005 errors present → regression in error detection
- test_rule_truth.py failures → regression in severity classification
- Any crashes or exceptions → bug in validation logic

## Requirements Proved By This UAT

- **R018** — Exit codes correctly reflect only genuine schema violations after downgrade
- **R019** — Evidence-based classification visible in CLI output (WARN vs ERROR)

## Not Proven By This UAT

- **S05 docs** — This UAT doesn't prove documentation exists
- **S06 full external scan proof** — S06 will run additional external repo scans
- Whether upstream repos fix the FM003/FM005 errors — that's upstream work

## Notes for Tester

- The three official repos must be accessible for this UAT to run
- FM004/FM007/AS004 warnings appear frequently (dozens) — this is expected behavior
- FM003/FM005 errors are genuine issues that need upstream fixes (documented in findings report)
- The exit code difference between repos is intentional: some have genuine errors, others only warnings
