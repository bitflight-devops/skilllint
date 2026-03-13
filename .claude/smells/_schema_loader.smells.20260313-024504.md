# Code Smell Report: _schema_loader.py

**File**: `/home/user/agentskills-linter/packages/skilllint/_schema_loader.py`
**Date**: 2026-03-13

## Ruff Findings
All checks passed. No issues found.

## Mypy Findings
Only `import-not-found` for `msgspec` (missing type stubs). No logic errors.

## Shebang Analysis
- **Current shebang**: None
- **Execute bit**: Not set
- **Rule**: Rule 4 (non-executable library module).
- **Verdict**: CORRECT.

## Code Quality Assessment
This is a clean, focused module. At 21 lines it does exactly one thing: load a bundled JSON schema using `importlib.resources` and decode it with `msgspec.json`. No smells detected.

## Minor Observations
- Return type is `dict` -- could be more specific (e.g., `dict[str, Any]`) but given schema shapes vary, `dict` is pragmatic here.
- No error handling for missing schema files. `files(...).joinpath(...)` will raise `FileNotFoundError` if the schema does not exist. Consider whether a friendlier error message is warranted.
