# Code Smell Report: tests/test_frontmatter_utils.py

**File**: `/home/user/agentskills-linter/packages/skilllint/tests/test_frontmatter_utils.py`
**Date**: 2026-03-13

## Ruff Findings
All checks passed. No issues found.

## Shebang Analysis
- **Current shebang**: None
- **Execute bit**: Not set
- **Rule**: Rule 4 (non-executable test module -- run by pytest).
- **Verdict**: CORRECT.

## Code Quality Observations

### Repeated Imports Inside Test Methods (LOW)
Every test method imports `loads_frontmatter`, `dump_frontmatter`, etc. at function scope (e.g., lines 21, 30, 39, 49, 75). While this is a valid pattern for lazy imports in test files, it adds noise. Consider moving imports to module level since tests always need these functions.

### Good Practices Observed
- Tests are well-organized into logical classes: `TestRuamelYAMLHandler`, `TestConvenienceAPI`, `TestEdgeCases`.
- Each test has a clear docstring explaining what it validates.
- Edge cases are well-covered: empty files, unicode, booleans, list values, code blocks.
- Uses `tmp_path` fixture correctly for file-writing tests.
- Uses `TYPE_CHECKING` guard for `Path` import.
