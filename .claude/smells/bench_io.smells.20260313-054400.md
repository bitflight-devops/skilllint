# Code Smell Report: scripts/bench_io.py

**Generated**: 2026-03-13 05:44:00

## Static Analysis

- **ruff check**: All checks passed
- **pyright**: 0 errors, 0 warnings

## Code Smells Identified

### MEDIUM: `_count_files` Uses Legacy `os.walk` Instead of `pathlib`

**Location**: Lines 24-36

**Problem**: The function uses `os.walk()` with a manual counter, while the rest of the codebase uses `pathlib.Path` consistently. This is a style inconsistency. A more idiomatic approach:

```python
def _count_files(directory: Path) -> int:
    return sum(1 for _ in directory.rglob("*") if _.is_file())
```

### LOW: Shebang / PEP 723 Compliance

**Current shebang**: None
**Execute bit**: Not set (-rw-r--r--)
**Rule applied**: Rule 4 (non-executable, invoked via `python scripts/bench_io.py`)
**Verdict**: CORRECT
