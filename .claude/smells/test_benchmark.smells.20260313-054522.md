# Code Smell Report: test_benchmark.py

**File**: `/home/user/agentskills-linter/tests/benchmarks/test_benchmark.py`
**Date**: 2026-03-13T05:45:22Z

## Issues Found

### MEDIUM: TOCTOU on results file (lines 52-61)

`_write_result()` checks `results_path.exists()` then reads the file. Between the
check and the read, another process could modify or delete the file. The
`try/except` on line 53 partially mitigates this for the read, but the subsequent
`.write_text()` on line 61 could clobber a concurrent write.

- **Lines**: 52-61
- **Impact**: Low in practice (benchmarks rarely run concurrently), but the pattern
  is fragile.
- **Fix**: Use file locking (`fcntl.flock`) or accept the race as tolerable for
  benchmark-only code.

### MEDIUM: Two sequential subprocess calls for git info (lines 22-36)

`_get_git_info()` spawns two separate `git` subprocesses. These could be combined
into a single call or run concurrently.

- **Lines**: 22-36
- **Fix**: Use a single subprocess call:
  `git log -1 --format="%h %D"` and parse, or accept the minor overhead since
  this runs once per test.

### LOW: plugin_file_count fixture not session-scoped (conftest.py line 51)

The `plugin_file_count` fixture in conftest.py uses default (function) scope while
`extracted_plugin_dir` is session-scoped. This means `rglob("SKILL.md")` runs on
every test function that uses it, re-counting the same files.

- **File**: `tests/benchmarks/conftest.py:51`
- **Fix**: Change to `@pytest.fixture(scope="session")`.
