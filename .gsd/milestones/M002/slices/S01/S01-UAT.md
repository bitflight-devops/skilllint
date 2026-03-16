---
id: S01
parent: M002
milestone: M002
written: 2026-03-15
---

# S01: Validator seam map and boundary extraction — UAT

**Milestone:** M002
**Written:** 2026-03-15

## UAT Type

- UAT mode: artifact-driven + live-runtime
- Why this mode is sufficient: This slice extracted internal seams and locked them with regression tests. The primary verification is through test execution proving the seams work correctly and the CLI still functions. No human-experience testing is needed for internal refactoring.

## Preconditions

- `uv` is installed and available
- Project is at `.gsd/worktrees/M002`
- All Python dependencies installed via `uv sync`

## Smoke Test

```bash
uv run pytest packages/skilllint/tests/test_scan_runtime.py -q --no-cov
```

Expected: 24 passed. This confirms the extracted seams are wired correctly.

## Test Cases

### 1. Scan runtime module exports exist

1. Run: `python -c "from skilllint.scan_runtime import discover_validatable_paths, resolve_filter_and_expand_paths, compute_summary, FILTER_TYPE_MAP, DEFAULT_SCAN_PATTERNS"`
2. **Expected:** No import error

### 2. Backwards-compatible aliases work

1. Run: `python -c "from skilllint.plugin_validator import _discover_validatable_paths, _resolve_filter_and_expand_paths, _compute_summary"`
2. **Expected:** No import error

### 3. Import identity proves seam is active

1. Run: `python -c "from skilllint.plugin_validator import _discover_validatable_paths; from skilllint.scan_runtime import discover_validatable_paths; print('SAME' if _discover_validatable_paths is discover_validatable_paths else 'DIFFERENT')"`
2. **Expected:** Prints "SAME"

### 4. CLI validates valid skill file

1. Run: `uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/claude_code/valid_skill.md --no-color; echo "Exit: $?"`
2. **Expected:** Exit code 0

### 5. CLI fails on invalid skill file

1. Run: `uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/claude_code/invalid-skill/SKILL.md --no-color; echo "Exit: $?"`
2. **Expected:** Exit code 1 (validation errors present)

### 6. CLI validates directory with --show-summary

1. Run: `uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/claude_code/valid_skill.md --no-color --show-summary`
2. **Expected:** Summary output includes "Total: X, Passed: Y, Failed: Z"

### 7. Path discovery finds skills in plugin directory

1. Run: `python -c "from skilllint.scan_runtime import discover_validatable_paths; paths = discover_validatable_paths('packages/skilllint/tests/fixtures/claude_code'); print([p for p in paths if 'SKILL.md' in p][:3])"`
2. **Expected:** List of paths containing SKILL.md

### 8. Filter resolution works

1. Run: `python -c "from skilllint.scan_runtime import resolve_filter_and_expand_paths; result = resolve_filter_and_expand_paths('packages/skilllint/tests/fixtures/claude_code', filter_type='skills'); print(len(result['paths']))"`
2. **Expected:** Positive integer (skills found)

### 9. Reporter selection defaults to ConsoleReporter

1. Run: `python -c "from skilllint.plugin_validator import ConsoleReporter; import inspect; print(inspect.getfile(ConsoleReporter))"`
2. **Expected:** Path contains `plugin_validator.py`

### 10. CIReporter is selected with --no-color

1. Run: `uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/claude_code/valid_skill.md --no-color 2>&1 | head -5`
2. **Expected:** Output does NOT contain ANSI color codes (plain text)

### 11. All CLI tests pass

1. Run: `uv run pytest packages/skilllint/tests/test_cli.py -q --no-cov`
2. **Expected:** 35 passed, 1 skipped

### 12. All provider validation tests pass

1. Run: `uv run pytest packages/skilllint/tests/test_provider_validation.py -q --no-cov`
2. **Expected:** 22 passed

### 13. Summary computation works

1. Run: `python -c "from skilllint.scan_runtime import compute_summary; from skilllint.plugin_validator import ValidationResult; results = [ValidationResult(path='a.md', passed=True, errors=[], warnings=[]), ValidationResult(path='b.md', passed=False, errors=['err'], warnings=[])]; summary = compute_summary(results); print(summary['total'], summary['passed'], summary['failed'])"`
2. **Expected:** "2 1 1"

### 14. Empty directory returns empty list

1. Run: `python -c "import tempfile, os; from skilllint.scan_runtime import discover_validatable_paths; d = tempfile.mkdtemp(); print(len(discover_validatable_paths(d))); os.rmdir(d)"`
2. **Expected:** 0

## Edge Cases

### Invalid filter type

1. Run: `uv run python -m skilllint.plugin_validator check . --filter-type=invalid 2>&1; echo "Exit: $?"`
2. **Expected:** Exit code 2 (invalid arguments)

### Non-existent path

1. Run: `uv run python -m skilllint.plugin_validator check /nonexistent/path 2>&1; echo "Exit: $?"`
2. **Expected:** Exit code 2 (path does not exist)

### Directory with no validatable files

1. Run: `python -c "import tempfile, os; from skilllint.scan_runtime import discover_validatable_paths; d = tempfile.mkdtemp(); open(os.path.join(d, 'README.txt'), 'w').write('x'); print(len(discover_validatable_paths(d))); os.unlink(os.path.join(d, 'README.txt')); os.rmdir(d)"`
2. **Expected:** 0 (no .md, .json, .yaml, etc. files)

## Failure Signals

- **Any test in test_scan_runtime.py fails** — The extracted seams are broken or not wired correctly
- **Exit code changes for valid/invalid files** — The refactoring altered user-facing behavior
- **Import errors for backwards-compatible aliases** — Internal callers will break
- **Import identity assertion fails** — The seam is dead code (not actually used by CLI)

## Requirements Proved By This UAT

- R012 (partial) — The validator monolith is partially decomposed; seams exist and are wired. S02 must complete the ownership model.
- R025 — The real CLI entrypoint still works correctly after refactoring.

## Not Proven By This UAT

- R013, R014 — Schema vs rule ownership not yet implemented (S02)
- R015, R016, R017 — Scan target discovery semantics not yet hardened (S03)
- R018-R024 — Official repo truth pass and documentation (S04-S06)

## Notes for Tester

1. **T01 gap**: The reporting extraction was marked complete in the plan but wasn't actually done. Reporters remain in `plugin_validator.py`. This is a known limitation.

2. **Import identity is critical**: The test `test_plugin_validator_imports_from_scan_runtime` proves the extracted functions are the same objects used by the CLI. This is how we know the seams are active, not dead code.

3. **Exit codes must be preserved**: The slice verified that exit code 0 (success), 1 (validation errors), and 2 (invalid args) all work correctly. Don't accept any changes that alter these.
