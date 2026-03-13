# Code Smell Report: bench_cpu.py

**File**: `/home/user/agentskills-linter/scripts/bench_cpu.py`
**Date**: 2026-03-13T05:45:22Z

## Issues Found

### HIGH: Duplicated benchmark logic (lines 90-115)

`test_cpu_linting_large_yaml()` completely rebuilds the YAML document and re-runs the
full timing loop instead of calling the existing `_run_cpu_benchmark()` helper that
does the exact same work. This is ~20 lines of duplicated code that will drift.

- **Lines**: 90-115 duplicate lines 58-87
- **Impact**: Wasted CPU work if both paths execute in the same session; maintenance
  burden from duplicated logic.
- **Fix**: Rewrite `test_cpu_linting_large_yaml()` to call `_run_cpu_benchmark()` and
  assert on the returned `total_ms` value.

### LOW: No issues beyond the duplication above

Static analysis (ruff, mypy) passed cleanly for this file. The `AssertionError`
usage on line 112 is the correct Python built-in.
