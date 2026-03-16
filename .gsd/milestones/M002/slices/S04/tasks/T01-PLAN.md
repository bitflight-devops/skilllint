---
estimated_steps: 6
estimated_files: 2
---

# T01: Classify hard-failure rules and downgrade unjustified ones

**Slice:** S04 — Official-repo hard-failure truth pass
**Milestone:** M002

## Description

Classify every hard-failure rule family found in official repo scans (FM003, FM004, FM005, FM007, AS004) with evidence, then downgrade unjustified ones from error to warning severity. Create tests locking these classification decisions.

## Steps

1. Open `packages/skilllint/plugin_validator.py`. Locate where FM004, FM007, and AS004 findings are created with `severity="error"`. For each:
   - **FM004** (forbidden multiline YAML `|`, `>`, `|-`, `>-`): Claude Code runtime accepts multiline YAML. This is a style recommendation, not a schema requirement. Change severity from `"error"` to `"warning"`.
   - **FM007** (tools field is YAML array instead of CSV string): Claude Code runtime accepts YAML arrays for tools fields. This is a format preference, not a hard requirement. Change severity from `"error"` to `"warning"`.
   - **AS004** (unquoted colons in description): YAML colons are only ambiguous in specific contexts. Descriptions with colons are valid YAML when properly quoted by the YAML parser. Change severity from `"error"` to `"warning"`.
   - **FM003** (no frontmatter found): Keep as `"error"` — agents/skills/commands genuinely require frontmatter to function.
   - **FM005** (field type mismatch): Keep as `"error"` — type mismatches are genuine schema violations.

2. Add a classification comment block near the top of the file (after the ownership model) documenting the evidence-based truth classification:
   ```python
   # Rule Truth Classification (S04 — M002)
   # Justified errors: FM003 (frontmatter required), FM005 (type mismatch)
   # Downgraded to warning: FM004 (multiline YAML accepted by runtime),
   #   FM007 (YAML arrays accepted by runtime), AS004 (colons valid in context)
   # Evidence: Official repos (claude-plugins-official, skills, claude-code-plugins)
   #   contain these patterns and Claude Code runtime accepts them.
   ```

3. Create `packages/skilllint/tests/test_rule_truth.py`:
   - Test that FM004 findings have severity "warning"
   - Test that FM007 findings have severity "warning"
   - Test that AS004 findings have severity "warning"
   - Test that FM003 findings have severity "error"
   - Test that FM005 findings have severity "error"
   - Use existing test fixtures or create minimal inline frontmatter strings that trigger each rule.

4. Run existing tests to check for regressions: `uv run pytest packages/skilllint/tests/ -q --no-cov`. Fix any tests that assert on the old severity values.

## Must-Haves

- [ ] FM004 severity changed from error to warning
- [ ] FM007 severity changed from error to warning
- [ ] AS004 severity changed from error to warning
- [ ] FM003 and FM005 remain as errors
- [ ] Classification evidence documented in code
- [ ] test_rule_truth.py created with severity assertions
- [ ] All existing tests pass (fix any that asserted on old severities)

## Verification

- `uv run pytest packages/skilllint/tests/test_rule_truth.py -v --no-cov` — all new tests pass
- `uv run pytest packages/skilllint/tests/ -q --no-cov` — no regressions

## Inputs

- `packages/skilllint/plugin_validator.py` — contains all FM/AS rule enforcement with `severity="error"` for the rules being reclassified
- S02 ownership model: ValidatorOwnership.SCHEMA vs LINT (FrontmatterValidator is SCHEMA — but individual rules within it can have different severities)
- Research finding: FM004 (13 hits), FM007 (20 hits), AS004 (6 hits) across official repos

## Expected Output

- `packages/skilllint/plugin_validator.py` — FM004/FM007/AS004 severity changed to "warning"; classification comment added
- `packages/skilllint/tests/test_rule_truth.py` — new test file locking severity classifications

## Observability Impact

### Signals Changed
- **ValidationResult.passed**: Now returns `True` for files with only FM004/FM007/AS004 violations (previously `False`)
- **ValidationResult.warnings**: Contains FM004/FM007/AS004 issues (previously in `errors`)
- **ValidationResult.errors**: Only contains FM003/FM005 and other genuine schema violations
- **CLI output**: Shows `⚠ WARN` for FM004/FM007/AS004 instead of `✗ ERROR`
- **Exit code**: Returns 0 for files with only downgraded warnings, 1 only when genuine errors remain

### Inspection Methods
- Run `skilllint check <path> --no-color` to see WARN vs ERROR classification
- Check `result.warnings` list for FM004/FM007/AS004 issues in code
- Run `uv run pytest packages/skilllint/tests/test_rule_truth.py -v` to verify severity assertions

### Failure Visibility
- Files with FM004/FM007/AS004 now show warnings but pass validation
- Files with FM003/FM005 still fail validation with exit code 1
