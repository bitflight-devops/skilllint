# Code Smell Report: bench_io.py

**File**: `/home/user/agentskills-linter/scripts/bench_io.py`
**Date**: 2026-03-13T05:45:22Z

## Issues Found

### MEDIUM: shutil.which called inside every iteration (line 53)

`_run_once()` calls `shutil.which("skilllint")` on every invocation. In
`run_benchmark()` this is called `runs` times (default 3). The executable path
does not change between iterations.

- **Lines**: 53-55 (called from line 79 loop)
- **Fix**: Resolve the path once in `run_benchmark()` and pass it to `_run_once()`.

### LOW: Manual file counting with os.walk (lines 24-36)

`_count_files()` manually walks the directory tree with `os.walk`. This works but
could use `sum(1 for _ in Path(directory).rglob("*") if _.is_file())` for clarity,
or even just count after the benchmark run since the data is stable.

- **Lines**: 24-36
- **Impact**: Negligible performance difference but adds code surface.
