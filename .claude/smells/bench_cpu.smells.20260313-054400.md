# Code Smell Report: scripts/bench_cpu.py

**Generated**: 2026-03-13 05:44:00

## Static Analysis

- **ruff check**: All checks passed
- **pyright**: 0 errors, 0 warnings
- **mypy**: No errors in this file (errors in other files are unrelated third-party stub issues)

## Code Smells Identified

### HIGH: Copy-Paste Duplication Between `test_cpu_linting_large_yaml()` and `_run_cpu_benchmark()`

**Location**: Lines 58-87 (`_run_cpu_benchmark`) vs. Lines 90-115 (`test_cpu_linting_large_yaml`)

**Problem**: The benchmark loop (build document, run N iterations of `loads_frontmatter`, measure elapsed time, compute mean) is duplicated almost verbatim between these two functions. The only differences are:
1. `test_cpu_linting_large_yaml` prints output and raises `AssertionError` on timeout
2. `_run_cpu_benchmark` returns a dict

This is a textbook copy-paste smell. Any change to the benchmark methodology must be applied in two places, and they can silently diverge.

**Fix**: Have `test_cpu_linting_large_yaml` call `_run_cpu_benchmark()` and then apply its assertion/print logic to the returned dict:

```python
def test_cpu_linting_large_yaml() -> None:
    timing = _run_cpu_benchmark()
    elapsed_s = timing["total_ms"] / 1000.0
    print(f"\nCPU BENCHMARK: {_ITERATIONS} iterations in {elapsed_s:.3f}s (mean {timing['mean_ms']:.3f} ms/iter)")
    if elapsed_s >= _TIME_LIMIT_SECONDS:
        raise AssertionError(...)
```

### MEDIUM: Typo in Exception Class Name

**Location**: Line 112

**Problem**: `AssertionError` is raised, but this is not a built-in Python exception. The correct name is `AssertionError` -- wait, actually Python's built-in is `AssertionError`. Let me verify: Python's built-in is `AssertionError`. Actually the correct name is `AssertionError`. No -- the correct built-in is **`AssertionError`**.

Correction: The built-in is `AssertionError`. The code uses `AssertionError` which matches. This is a non-issue if `AssertionError` is indeed `AssertionError`. Let me re-check: Python built-in is `AssertionError`. The code spells it `AssertionError`. These match.

**Status**: False alarm -- spelling is correct.

### LOW: Shebang / PEP 723 Compliance

**Current shebang**: None
**Execute bit**: Not set (-rw-r--r--)
**Imports**: `skilllint.frontmatter_utils` (external, part of this project's package)
**Rule applied**: Rule 4 (non-executable library module) -- no shebang needed
**Verdict**: CORRECT -- this file is invoked via `python scripts/bench_cpu.py` or `pytest`, not directly executed.
