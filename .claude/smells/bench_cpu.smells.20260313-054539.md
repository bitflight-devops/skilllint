# Code Smell Report: bench_cpu.py

**File**: `/home/user/agentskills-linter/scripts/bench_cpu.py`
**Date**: 2026-03-13T05:45:39Z

## Issues Found

### SMELL-1: Copy-paste duplication between `test_cpu_linting_large_yaml` and `_run_cpu_benchmark` [HIGH]

**Location**: Lines 58-87 (`_run_cpu_benchmark`) vs Lines 90-115 (`test_cpu_linting_large_yaml`)

Both functions contain nearly identical logic:
- Build the same document with `_build_large_yaml_document(num_keys=50, value_length=100)`
- Run the same loop calling `loads_frontmatter` for `_ITERATIONS` iterations
- Measure elapsed time with `time.perf_counter()`
- Compute `mean_ms` the same way: `(elapsed / _ITERATIONS) * 1000.0`
- Include the same `if post is None: raise RuntimeError(...)` guard

The test function duplicates the entire benchmark loop instead of calling `_run_cpu_benchmark()` and asserting on its return value.

**Impact**: Any future change to benchmark methodology must be applied in two places. Risk of behavioral drift between the pytest path and the CLI path.

**Fix**: Rewrite `test_cpu_linting_large_yaml` to delegate to `_run_cpu_benchmark()`:
```python
def test_cpu_linting_large_yaml() -> None:
    timing = _run_cpu_benchmark()
    total_s = timing["total_ms"] / 1000.0
    assert total_s < _TIME_LIMIT_SECONDS, (
        f"CPU benchmark exceeded {_TIME_LIMIT_SECONDS}s: {total_s:.3f}s"
    )
```

### SMELL-2: Shebang / PEP 723 compliance [LOW]

**Status**: No shebang, not executable. File is invoked via `python scripts/bench_cpu.py` or `pytest`. Rule 4 (non-executable module) applies. Acceptable as-is.

## Summary

| Priority | Count |
|----------|-------|
| HIGH     | 1     |
| LOW      | 1     |
