---
id: T03
parent: S01
milestone: M002
provides:
  - test_scan_runtime.py with focused seam boundary tests
  - Regression coverage for discover_validatable_paths, resolve_filter_and_expand_paths, compute_summary
  - Seam wiring verification proving CLI routes through extracted modules
  - Reporter selection tests verifying ConsoleReporter vs CIReporter selection
key_files:
  - packages/skilllint/tests/test_scan_runtime.py
key_decisions:
  - Created test_scan_runtime.py as the dedicated test module for seam boundary regression
  - Tests verify both seam implementation correctness and wiring into CLI path
  - Import identity tests prove functions are the same objects (not copies)
patterns_established:
  - Test seams directly for behavior correctness, then test wiring via import identity
  - Use CLI execution tests to prove seams are active in runtime
  - Focus on boundary contracts, not internal implementation trivia
observability_surfaces:
  - Test output shows which seam tests pass/fail
  - CLI verification commands prove real entrypoint uses extracted seams
duration: 45m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Lock seam boundaries with focused regression coverage and real-entrypoint proof

**Added test_scan_runtime.py with 24 seam boundary tests proving the extracted seams are wired into the CLI and function correctly.**

## What Happened

Created `packages/skilllint/tests/test_scan_runtime.py` with comprehensive boundary tests for the extracted seams from T02:

1. **TestDiscoverValidatablePaths** (6 tests) - Verifies path discovery works for skills, agents, commands, and plugin.json files. Tests edge cases like empty directories and sorted output.

2. **TestResolveFilterAndExpandPaths** (8 tests) - Verifies filter resolution and path expansion. Tests directory expansion, file passthrough, filter-type shortcuts, custom globs, and mutual exclusion validation.

3. **TestComputeSummary** (3 tests) - Verifies summary statistics computation for total/passed/failed/warning counts.

4. **TestSeamWiring** (4 tests) - **The critical proof tests:**
   - `test_scan_runtime_exports_exist` - Verifies all expected functions/constants are exported
   - `test_plugin_validator_imports_from_scan_runtime` - **Proves via identity check** that `plugin_validator._discover_validatable_paths` IS the same function object as `scan_runtime.discover_validatable_paths` (not a copy)
   - `test_cli_uses_resolve_filter_and_expand_paths` - Exercises the CLI path that calls the seam
   - `test_cli_uses_compute_summary` - Exercises `--show-summary` to verify the seam is active

5. **TestReporterSelection** (2 tests) - Verifies ConsoleReporter is used by default and CIReporter is selected with `--no-color`.

6. **TestConstantsExport** (2 tests) - Verifies FILTER_TYPE_MAP and DEFAULT_SCAN_PATTERNS are correct.

## Verification

All slice-level verification passes:

```bash
$ uv run pytest packages/skilllint/tests/test_cli.py -q --no-cov
35 passed, 1 skipped

$ uv run pytest packages/skilllint/tests/test_provider_validation.py -q --no-cov
22 passed

$ uv run pytest packages/skilllint/tests/test_scan_runtime.py -v --no-cov
24 passed

$ uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/claude_code/valid_skill.md --no-color
Exit code: 0

$ uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/claude_code/invalid-skill/SKILL.md --no-color
Exit code: 1 (expected failure)
```

## Diagnostics

To verify the seam boundaries are locked:

1. **Import identity check**: `python -c "from skilllint.plugin_validator import _discover_validatable_paths; from skilllint.scan_runtime import discover_validatable_paths; assert _discover_validatable_paths is discover_validatable_paths"`

2. **Test execution**: `pytest packages/skilllint/tests/test_scan_runtime.py -v`

3. **CLI verification**: Run `skilllint check` with and without `--show-summary` to verify the seams are active in runtime.

## Deviations

None. The task followed the plan. The seam boundary tests are focused on contracts, not implementation trivia.

## Known Issues

None. All tests pass.

## Files Created/Modified

- `packages/skilllint/tests/test_scan_runtime.py` — New test module with 24 seam boundary tests (203 lines)
