# Code Smell Report: frontmatter.py

**File**: `/home/user/agentskills-linter/packages/skilllint/frontmatter.py`
**Date**: 2026-03-13T05:45:39Z

## Issues Found

### SMELL-1: `lint_and_fix()` is dead stub code [HIGH]

**Location**: Lines 74-91

```python
def lint_and_fix(raw_yaml: bytes) -> tuple[bool, bytes | None]:
    # Dummy implementation: Replace with actual YAML loading/dumping
    # Return (True, fixed_bytes) if errors found, else (False, None)
    return False, None
```

This function always returns `(False, None)`, meaning `process_markdown_file` can never apply any fix. The entire write path (lines 54-68, the temp file creation and atomic replace) is unreachable dead code.

**Impact**: The module appears functional but does nothing. Any caller relying on `process_markdown_file` to lint or fix frontmatter gets silent no-ops. This is a correctness issue because the code creates a false sense of capability.

**Fix**: Either implement the actual linting logic or remove the module entirely if it is not in use. If it is intended as a placeholder, it should raise `NotImplementedError` so callers fail loudly rather than silently succeeding.

### SMELL-2: Unreachable code path after `lint_and_fix` stub [MEDIUM]

**Location**: Lines 54-71

Because `lint_and_fix` always returns `(False, None)`, the following code is unreachable:
- Line 55: `if new_yaml_bytes is None: return`
- Lines 57-68: temp file write logic
- Line 71: `pathlib.Path(temp_path).replace(file_path)` (atomic replace)

This dead code path also has a latent bug: `temp_path` (line 57) is constructed as `file_path + ".tmp"` but `file_path` is typed as `str`. If this code were ever reached with a `Path` object, string concatenation would fail with a `TypeError`.

### SMELL-3: Line 71 `temp_path` may be referenced before assignment [MEDIUM]

**Location**: Line 71

`temp_path` is assigned on line 57 inside the `with` block. Line 71 (`pathlib.Path(temp_path).replace(file_path)`) is outside the `with` block. If the code path that skips the `with` body were ever taken (e.g., `needs_fix` is True but `new_yaml_bytes` is None), `temp_path` would be an `UnboundLocalError`.

Currently this is masked by `lint_and_fix` always returning `(False, None)`, but it would surface if the stub were replaced with real logic.

### SMELL-4: Redundant `pathlib.Path()` construction [LOW]

**Location**: Lines 31, 34

`pathlib.Path(file_path)` is constructed twice (lines 31 and 34) for the same string. Should be assigned once.

### SMELL-5: Shebang / PEP 723 compliance [LOW]

**Status**: No shebang, not executable. This is a library module (Rule 4). Correct as-is.

## Summary

| Priority | Count |
|----------|-------|
| HIGH     | 1     |
| MEDIUM   | 2     |
| LOW      | 2     |
